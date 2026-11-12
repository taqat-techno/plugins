// calendar writes: stage -> commit. Staging validates and previews (with conflicts) and creates nothing;
// the commit creates the event and, when there are attendees, Microsoft sends them invitations.
// The create call carries the stage id as its transactionId, so a retry can never create the event twice.
//
// Changes to an EXISTING event (reschedule / rename / move, cancel, accept / tentative / decline, propose a new time)
// are staged by calendar_change_stage and applied by the same confirm-gated calendar_commit. The preview says who is
// notified and whether a recurring series or one occurrence changes; the stage remembers the event's changeKey, and the
// commit refuses if the event changed in the meantime.
import { EMAIL_RE, M365Error, UNTRUSTED_FIELDS, clean, graphUtcMs, isValidZone, parseBound, safeId, safeStr, seg, systemZone, wallClock } from "../util.mjs";

const UTC = { headers: { Prefer: 'outlook.timezone="UTC"' } };
const iso = (ms) => new Date(ms).toISOString().slice(0, 19);
// Statuses that mean Microsoft did not accept the request. Anything else (408, 409, 5xx, a timeout) is an unknown outcome.
const REFUSED = new Set([400, 401, 403, 404, 405, 422, 429]);
const EVENT_SELECT = "id,subject,start,end,location,attendees,organizer,isOrganizer,isCancelled,responseStatus,responseRequested,allowNewTimeProposals,type,seriesMasterId,changeKey";
const ACTIONS = ["change", "cancel", "accept", "tentative", "decline"];
const RESPOND = { accept: "accept", tentative: "tentativelyAccept", decline: "decline" };

async function conflictsAt(ctx, s, e, iana, skipId) {
  const j = await ctx.graph.get(`/me/calendarView?startDateTime=${new Date(s).toISOString()}&endDateTime=${new Date(e).toISOString()}&$select=id,subject,start,end,showAs,isCancelled&$top=20`, UTC);
  return (j.value ?? []).filter((x) => x.id !== skipId && !x.isCancelled && ["busy", "tentative", "oof"].includes(x.showAs))
    .map((x) => ({ subject: clean(x.subject, 200), start: wallClock(Date.parse(`${x.start.dateTime.slice(0, 19)}Z`), iana), end: wallClock(Date.parse(`${x.end.dateTime.slice(0, 19)}Z`), iana), show_as: x.showAs }));
}

const seriesNote = (ev) => ev.type === "seriesMaster" ? "This is a RECURRING SERIES: the change applies to EVERY occurrence."
  : ev.type === "occurrence" || ev.type === "exception" ? "This is one occurrence of a recurring series: only this occurrence changes." : null;

export const tools = [
  {
    name: "calendar_change_stage", kind: "write", module: "calendar",
    description: "Prepare a change to an EXISTING event without making it; returns a preview, stage_id and digest, then calendar_commit after the user approves. action: change (new start/end, subject or location; only for events the user organizes; attendees are notified), cancel (organizer: cancels it for everyone with an optional comment; an event without attendees is just removed), accept / tentative / decline (an invitation from someone else; comment optional; send_response false answers silently; propose_start + propose_end suggest a new time with tentative or decline). event_id from calendar_list_events: an occurrence id changes only that occurrence, a series id the whole series. Times are in the user's time zone unless they carry one.",
    inputSchema: { type: "object", properties: {
      event_id: { type: "string" }, action: { type: "string", enum: ACTIONS },
      start: { type: "string" }, end: { type: "string" }, subject: { type: "string" }, location: { type: "string" },
      comment: { type: "string", description: "Message to the organizer (answers) or to the attendees (cancel)." },
      send_response: { type: "boolean", description: "accept / tentative / decline: tell the organizer. Default true." },
      propose_start: { type: "string" }, propose_end: { type: "string" },
      timezone: { type: "string", description: "IANA zone, default the profile's." } }, required: ["event_id", "action"] },
    async handler(a, ctx) {
      const iana = a.timezone || ctx.profile.load().me.timezone || systemZone();
      if (!isValidZone(iana)) throw new M365Error("INVALID_ARGUMENT", `timezone must be an IANA name such as Africa/Cairo (got "${iana}")`);
      const id = safeId(a.event_id, "event_id");
      const action = String(a.action ?? "");
      if (!ACTIONS.includes(action)) throw new M365Error("INVALID_ARGUMENT", `action must be one of: ${ACTIONS.join(", ")}`);
      const ev = await ctx.graph.get(`/me/events/${seg(id)}?$select=${EVENT_SELECT}`, UTC);
      if (ev.isCancelled) throw new M365Error("ALREADY_DONE", "That event is already cancelled.");
      const attendees = (ev.attendees ?? []).map((x) => (x.emailAddress?.address ?? "").toLowerCase()).filter(Boolean);
      const organizer = (ev.organizer?.emailAddress?.address ?? "").toLowerCase() || null;
      const comment = a.comment === undefined ? "" : (safeStr(a.comment, "comment", 2000) ?? "").trim();
      const nowMs = { start: graphUtcMs(ev.start?.dateTime), end: graphUtcMs(ev.end?.dateTime) };
      const now = { start: wallClock(nowMs.start, iana), end: wallClock(nowMs.end, iana) };
      const payload = { event_id: id, action, change_key: ev.changeKey ?? null };
      const preview = { event: clean(ev.subject, 255) || "(no subject)", timezone: iana, currently: now, organizer, you_organize: !!ev.isOrganizer, attendees_count: attendees.length };
      const series = seriesNote(ev);
      if (series) preview.recurrence = series;
      let conflicts = [], notified;

      if (action === "change") {
        if (!ev.isOrganizer) throw new M365Error("NOT_ORGANIZER", "Only the organizer can change this event.", { hint: "To ask for another time, use action tentative or decline with propose_start and propose_end." });
        const patch = {};
        if (a.start !== undefined || a.end !== undefined) {
          const s = a.start !== undefined ? parseBound(a.start, "start", iana) : nowMs.start;
          const e = a.end !== undefined ? parseBound(a.end, "end", iana) : nowMs.end;
          if (!(e > s)) throw new M365Error("INVALID_ARGUMENT", "end must be after start");
          if (e - s > 14 * 864e5) throw new M365Error("INVALID_ARGUMENT", "an event cannot be longer than 14 days");
          patch.start = iso(s); patch.end = iso(e);
          preview.new_time = { start: wallClock(s, iana), end: wallClock(e, iana) };
          conflicts = await conflictsAt(ctx, s, e, iana, id);
        }
        if (a.subject !== undefined) {
          const t = (safeStr(a.subject, "subject", 255) ?? "").trim();
          if (!t) throw new M365Error("INVALID_ARGUMENT", "subject cannot be empty");
          patch.subject = t; preview.new_subject = clean(t, 255);
        }
        if (a.location !== undefined) { patch.location = (safeStr(a.location, "location", 200) ?? "").trim(); preview.new_location = clean(patch.location, 200) || "(none)"; }
        if (!Object.keys(patch).length) throw new M365Error("INVALID_ARGUMENT", "give start/end, subject or location to change");
        payload.patch = patch;
        notified = attendees.length ? `Microsoft sends the updated invitation to ${attendees.length} attendee(s).` : "No attendees: only your calendar changes.";
      } else if (action === "cancel") {
        if (!ev.isOrganizer) throw new M365Error("NOT_ORGANIZER", "Only the organizer can cancel this event for everyone.", { hint: "Use action decline to say you will not attend." });
        payload.mode = attendees.length ? "cancel" : "delete";
        if (comment) payload.comment = comment;
        notified = attendees.length ? `Microsoft sends a cancellation to ${attendees.length} attendee(s)${comment ? " with your comment" : ""}.` : "No attendees: the event is just removed from your calendar (to Deleted Items).";
      } else {
        if (ev.isOrganizer) throw new M365Error("INVALID_ARGUMENT", "You organize this event; there is no invitation to answer. Use change or cancel.");
        payload.send_response = a.send_response !== false;
        if (comment) payload.comment = comment;
        if (a.propose_start !== undefined || a.propose_end !== undefined) {
          if (action === "accept") throw new M365Error("INVALID_ARGUMENT", "A new time can be proposed only with tentative or decline.");
          if (!payload.send_response) throw new M365Error("INVALID_ARGUMENT", "A new time can be proposed only when the answer is sent.");
          if (ev.allowNewTimeProposals === false) throw new M365Error("NOT_ALLOWED", "The organizer does not accept new time proposals for this event.");
          const s = parseBound(a.propose_start, "propose_start", iana), e = parseBound(a.propose_end, "propose_end", iana);
          if (!s || !e || !(e > s)) throw new M365Error("INVALID_ARGUMENT", "give propose_start and propose_end, with end after start");
          payload.propose = { start: iso(s), end: iso(e) };
          preview.proposed_time = { start: wallClock(s, iana), end: wallClock(e, iana) };
        }
        preview.your_current_response = ev.responseStatus?.response ?? null;
        notified = payload.send_response
          ? `Your answer${comment ? " and comment" : ""}${payload.propose ? " and the proposed time" : ""} go to the organizer (${organizer ?? "unknown"}).`
          : "Nobody is told: the answer is only recorded in your calendar.";
      }
      preview.action = action;
      if (comment && (action === "cancel" || payload.send_response)) preview.comment = comment;
      preview.who_is_notified = notified;
      const st = ctx.staging.create("calchange", payload);
      return {
        stage_id: st.id, digest: st.digest, preview, conflicts, note: UNTRUSTED_FIELDS,
        next_step: "Show the user the event, the change, who is notified and any recurrence note or conflicts. After they approve, call calendar_commit with stage_id and digest.",
      };
    },
  },
  {
    name: "calendar_stage", kind: "write", module: "calendar",
    description: "Prepare a calendar event without creating it: validates the details, shows the local times, lists conflicts with the user's own events, and returns a stage_id and digest. Attendees (verified email addresses; use people_resolve) will receive invitations when the event is committed. Show the preview to the user, then call calendar_commit after they approve. Times are in the user's time zone unless they carry one.",
    inputSchema: { type: "object", properties: {
      subject: { type: "string" }, start: { type: "string", description: "e.g. 2026-11-10T14:00:00" }, end: { type: "string" },
      attendees: { type: "array", items: { type: "string" }, description: "Attendee email addresses." },
      location: { type: "string" }, body: { type: "string", description: "Plain-text description." },
      teams_meeting: { type: "boolean", description: "Add a Teams meeting link. Default true when there are attendees." },
      timezone: { type: "string", description: "IANA zone, default the profile's." } }, required: ["subject", "start", "end"] },
    async handler(a, ctx) {
      const iana = a.timezone || ctx.profile.load().me.timezone || systemZone();
      if (!isValidZone(iana)) throw new M365Error("INVALID_ARGUMENT", `timezone must be an IANA name such as Africa/Cairo (got "${iana}")`);
      const subject = safeStr(a.subject, "subject", 255);
      if (!subject?.trim()) throw new M365Error("INVALID_ARGUMENT", "subject is required");
      const s = parseBound(a.start, "start", iana), e = parseBound(a.end, "end", iana);
      if (!(e > s)) throw new M365Error("INVALID_ARGUMENT", "end must be after start");
      if (e - s > 14 * 864e5) throw new M365Error("INVALID_ARGUMENT", "an event cannot be longer than 14 days");
      const attendees = [];
      for (const x of a.attendees ?? []) {
        const em = String(x ?? "").trim().toLowerCase();
        if (!EMAIL_RE.test(em)) throw new M365Error("INVALID_ARGUMENT", `"${x}" is not an email address. Resolve names with people_resolve first; never guess an address.`);
        if (!attendees.includes(em)) attendees.push(em);
      }
      if (attendees.length > 50) throw new M365Error("INVALID_ARGUMENT", "at most 50 attendees");
      const payload = {
        subject, start: iso(s), end: iso(e), attendees,
        location: safeStr(a.location, "location", 200) ?? "", body: safeStr(a.body, "body", 20_000) ?? "",
        teams_meeting: a.teams_meeting ?? attendees.length > 0,
      };
      const j = await ctx.graph.get(`/me/calendarView?startDateTime=${new Date(s).toISOString()}&endDateTime=${new Date(e).toISOString()}&$select=subject,start,end,showAs,isCancelled&$top=20`, UTC);
      const conflicts = (j.value ?? []).filter((x) => !x.isCancelled && ["busy", "tentative", "oof"].includes(x.showAs))
        .map((x) => ({ subject: clean(x.subject, 200), start: wallClock(Date.parse(`${x.start.dateTime.slice(0, 19)}Z`), iana), end: wallClock(Date.parse(`${x.end.dateTime.slice(0, 19)}Z`), iana), show_as: x.showAs }));
      const st = ctx.staging.create("calendar", payload);
      return {
        stage_id: st.id, digest: st.digest,
        preview: { subject: clean(subject, 255), start: wallClock(s, iana), end: wallClock(e, iana), timezone: iana, attendees, location: clean(payload.location, 200), teams_meeting: payload.teams_meeting },
        conflicts, note: UNTRUSTED_FIELDS,
        warning: attendees.length ? `Committing sends invitations to ${attendees.length} people.` : "No attendees: only the user's own calendar changes.",
        next_step: "Show the user this preview (mention conflicts). After they approve, call calendar_commit with stage_id and digest.",
      };
    },
  },
  {
    name: "calendar_commit", kind: "write", module: "calendar", confirm: true,
    description: "Apply what calendar_stage or calendar_change_stage prepared: create the event (invitations go out), or change, cancel or answer an existing one (attendees / the organizer are notified as the preview said). Needs the stage_id and digest the user saw; refuses if the stage is unknown, already done, the digest differs, or the event changed since the preview. Only call it after the user approved the preview.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" }, digest: { type: "string" } }, required: ["stage_id", "digest"] },
    async handler(a, ctx) {
      if (String(a.stage_id ?? "").startsWith("calchange_")) return commitChange(a, ctx);
      const st = ctx.staging.transition(a.stage_id, "calendar", a.digest, "committing");
      const p = st.payload;
      const body = {
        subject: p.subject, start: { dateTime: p.start, timeZone: "UTC" }, end: { dateTime: p.end, timeZone: "UTC" },
        attendees: p.attendees.map((address) => ({ emailAddress: { address }, type: "required" })),
        transactionId: st.id,
      };
      if (p.location) body.location = { displayName: p.location };
      if (p.body) body.body = { contentType: "Text", content: p.body };
      if (p.teams_meeting) { body.isOnlineMeeting = true; body.onlineMeetingProvider = "teamsForBusiness"; }
      let ev;
      // A failed or timed-out create goes back to 'staged': retrying is safe because Microsoft matches the transactionId.
      try { ev = await ctx.graph.post("/me/events", body); } catch (e) { ctx.staging.set(st.id, { state: "staged" }); throw e; }
      ctx.staging.set(st.id, { state: "committed", event_id: ev.id });
      return { created: true, event_id: ev.id, join_url: ev.onlineMeeting?.joinUrl ?? null, web_link: ev.webLink ?? null, invitations_sent_to: p.attendees };
    },
  },
  {
    name: "calendar_discard", kind: "write", module: "calendar",
    description: "Drop a staged calendar event or change that has not been committed. Nothing was created or changed, so nothing is sent.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" } }, required: ["stage_id"] },
    async handler(a, ctx) {
      const st = ctx.staging.move(a.stage_id, String(a.stage_id ?? "").startsWith("calchange_") ? "calchange" : "calendar", "staged", "discarded");
      return { discarded: true, stage_id: st.id };
    },
  },
];

/** Apply a staged change to an existing event. */
async function commitChange(a, ctx) {
  const st = ctx.staging.transition(a.stage_id, "calchange", a.digest, "committing");
  const p = st.payload;
  const back = () => ctx.staging.set(st.id, { state: "staged" });
  let ev;
  try { ev = await ctx.graph.get(`/me/events/${seg(p.event_id)}?$select=id,changeKey,isCancelled`); } catch (e) { back(); throw e; }
  if (ev.isCancelled || (p.change_key && ev.changeKey !== p.change_key)) {
    back();
    throw new M365Error("EVENT_CHANGED", "The event changed after the preview (or was cancelled), so nothing was done.", { hint: "Stage the change again and show the user the new preview." });
  }
  const path = `/me/events/${seg(p.event_id)}`;
  try {
    if (p.action === "change") {
      const body = {};
      if (p.patch.start) { body.start = { dateTime: p.patch.start, timeZone: "UTC" }; body.end = { dateTime: p.patch.end, timeZone: "UTC" }; }
      if (p.patch.subject !== undefined) body.subject = p.patch.subject;
      if (p.patch.location !== undefined) body.location = { displayName: p.patch.location };
      await ctx.graph.patch(path, body);
    } else if (p.action === "cancel") {
      if (p.mode === "delete") await ctx.graph.del(path);
      else await ctx.graph.post(`${path}/cancel`, p.comment ? { comment: p.comment } : {});
    } else {
      const body = { sendResponse: p.send_response, ...(p.comment ? { comment: p.comment } : {}) };
      if (p.propose) body.proposedNewTime = { start: { dateTime: p.propose.start, timeZone: "UTC" }, end: { dateTime: p.propose.end, timeZone: "UTC" } };
      await ctx.graph.post(`${path}/${RESPOND[p.action]}`, body);
    }
  } catch (e) {
    // A change is safe to repeat; a cancellation or an answer that may have gone out is not.
    if (p.action === "change" || REFUSED.has(e.status)) { back(); throw e; }
    throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether this went through.", { hint: "Check the event with calendar_get_event before trying again. This stage will not be applied a second time automatically." });
  }
  ctx.staging.set(st.id, { state: "committed" });
  return { done: true, action: p.action, event_id: p.event_id, ...(p.action === "cancel" ? { removed: p.mode === "delete" } : {}), ...(p.propose ? { proposed_new_time: true } : {}) };
}
