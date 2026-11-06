// calendar writes: stage -> commit. Staging validates and previews (with conflicts) and creates nothing;
// the commit creates the event and, when there are attendees, Microsoft sends them invitations.
// The create call carries the stage id as its transactionId, so a retry can never create the event twice.
import { EMAIL_RE, M365Error, UNTRUSTED_FIELDS, clean, isValidZone, parseBound, safeStr, systemZone, wallClock } from "../util.mjs";

const UTC = { headers: { Prefer: 'outlook.timezone="UTC"' } };
const iso = (ms) => new Date(ms).toISOString().slice(0, 19);

export const tools = [
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
    description: "Create the event prepared by calendar_stage. Sends invitations to the attendees. Needs the stage_id and digest the user saw; refuses if the stage is unknown, already committed, or the digest differs. Only call it after the user approved the preview.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" }, digest: { type: "string" } }, required: ["stage_id", "digest"] },
    async handler(a, ctx) {
      const st = ctx.staging.require(a.stage_id, "calendar", a.digest);
      const p = st.payload;
      const body = {
        subject: p.subject, start: { dateTime: p.start, timeZone: "UTC" }, end: { dateTime: p.end, timeZone: "UTC" },
        attendees: p.attendees.map((address) => ({ emailAddress: { address }, type: "required" })),
        transactionId: st.id,
      };
      if (p.location) body.location = { displayName: p.location };
      if (p.body) body.body = { contentType: "Text", content: p.body };
      if (p.teams_meeting) { body.isOnlineMeeting = true; body.onlineMeetingProvider = "teamsForBusiness"; }
      const ev = await ctx.graph.post("/me/events", body);
      ctx.staging.set(st.id, { state: "committed", event_id: ev.id });
      return { created: true, event_id: ev.id, join_url: ev.onlineMeeting?.joinUrl ?? null, web_link: ev.webLink ?? null, invitations_sent_to: p.attendees };
    },
  },
  {
    name: "calendar_discard", kind: "write", module: "calendar",
    description: "Cancel a staged calendar event that has not been committed. Nothing was created, so nothing is sent.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" } }, required: ["stage_id"] },
    async handler(a, ctx) {
      const st = ctx.staging.get(a.stage_id);
      if (!st || st.kind !== "calendar") throw new M365Error("STAGE_NOT_FOUND", "No staged event with that id.");
      if (st.state !== "staged") throw new M365Error("ALREADY_DONE", `This event is already ${st.state}; it cannot be discarded here.`);
      ctx.staging.set(st.id, { state: "discarded" });
      return { discarded: true, stage_id: st.id };
    },
  },
];
