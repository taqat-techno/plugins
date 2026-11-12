// 0.12.0: changing existing calendar events - reschedule / rename / move, cancel, accept / tentative / decline, propose
// a new time. Staged by calendar_change_stage, applied by the confirm-gated calendar_commit. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";

const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const EV = (over = {}) => ({
  id: "ev1", subject: "Design review", start: { dateTime: "2026-11-20T08:00:00.0000000" }, end: { dateTime: "2026-11-20T09:00:00.0000000" },
  isOrganizer: true, isCancelled: false, organizer: { emailAddress: { address: "me@contoso.example" } }, type: "singleInstance", changeKey: "ck1",
  attendees: [{ emailAddress: { address: "sara@contoso.example" } }, { emailAddress: { address: "omar@contoso.example" } }], allowNewTimeProposals: true,
  responseStatus: { response: "organizer" }, ...over,
});
function calCtx(ev, routes = [], keyAtCommit) {
  let reads = 0;
  const c = ctxFor([TOK, ...routes, // test-specific answers first: the first matching route wins
    [/^GET .*\/me\/events\/ev1\?\$select=id,changeKey,isCancelled/, () => json({ id: "ev1", changeKey: keyAtCommit ?? ev.changeKey, isCancelled: false })],
    [/^GET .*\/me\/events\/ev1\?/, () => { reads++; return json(ev); }],
    [/^GET .*\/me\/calendarView/, () => json({ value: [{ id: "other", subject: "Lunch", start: { dateTime: "2026-11-21T10:00:00" }, end: { dateTime: "2026-11-21T11:00:00" }, showAs: "busy" }, { id: "ev1", subject: "Design review", start: { dateTime: "2026-11-21T10:00:00" }, end: { dateTime: "2026-11-21T11:00:00" }, showAs: "busy" }] })],
    [/^PATCH .*\/me\/events\/ev1$/, () => json({ id: "ev1" })],
    [/^POST .*\/me\/events\/ev1\/(cancel|accept|tentativelyAccept|decline)$/, () => new Response(null, { status: 202 })],
    [/^DELETE .*\/me\/events\/ev1$/, () => new Response(null, { status: 204 })]]);
  return c;
}
const commit = (c, s) => call(c, "calendar_commit", { stage_id: s.stage_id, digest: s.digest });

test("reschedule your own meeting: preview with new time, conflicts (not the event itself), attendees notified", async () => {
  const c = calCtx(EV());
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "change", start: "2026-11-21T10:00:00Z", end: "2026-11-21T11:00:00Z", timezone: "UTC" });
  assert.match(s.stage_id, /^calchange_/);
  assert.deepEqual(s.preview.new_time, { start: "2026-11-21T10:00:00", end: "2026-11-21T11:00:00" });
  assert.deepEqual(s.conflicts.map((x) => x.subject), ["Lunch"], "the event never conflicts with itself");
  assert.match(s.preview.who_is_notified, /2 attendee/);
  assert.equal(calls(c, "PATCH", /events/).length, 0, "nothing changed at stage");
  const r = await commit(c, s);
  assert.equal(r.done, true);
  assert.deepEqual(calls(c, "PATCH", /events\/ev1$/)[0].json, { start: { dateTime: "2026-11-21T10:00:00", timeZone: "UTC" }, end: { dateTime: "2026-11-21T11:00:00", timeZone: "UTC" } });
  await assert.rejects(commit(c, s), (e) => e.code === "ALREADY_DONE");
});

test("change only the end keeps the start; rename and move location", async () => {
  const c = calCtx(EV());
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "change", end: "2026-11-20T09:30:00Z", subject: "Design review (long)", location: "Room 4", timezone: "UTC" });
  await commit(c, s);
  const body = calls(c, "PATCH", /events\/ev1$/)[0].json;
  assert.equal(body.start.dateTime, "2026-11-20T08:00:00"); assert.equal(body.end.dateTime, "2026-11-20T09:30:00");
  assert.equal(body.subject, "Design review (long)"); assert.deepEqual(body.location, { displayName: "Room 4" });
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "change" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "change", end: "2026-11-20T07:00:00Z" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("only the organizer can change or cancel; an attendee is pointed to decline / propose", async () => {
  const c = calCtx(EV({ isOrganizer: false, organizer: { emailAddress: { address: "boss@contoso.example" } } }));
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "change", subject: "x" }), (e) => e.code === "NOT_ORGANIZER" && /propose_start/.test(e.hint));
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" }), (e) => e.code === "NOT_ORGANIZER" && /decline/.test(e.hint));
  const own = calCtx(EV());
  await assert.rejects(call(own, "calendar_change_stage", { event_id: "ev1", action: "accept" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("cancel a meeting sends a cancellation; an event without attendees is just removed", async () => {
  const c = calCtx(EV());
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel", comment: "Moving to next week" });
  assert.match(s.preview.who_is_notified, /cancellation to 2 attendee/);
  await commit(c, s);
  assert.deepEqual(calls(c, "POST", /\/cancel$/)[0].json, { comment: "Moving to next week" });
  const solo = calCtx(EV({ attendees: [] }));
  const s2 = await call(solo, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  assert.match(s2.preview.who_is_notified, /just removed/);
  assert.equal((await commit(solo, s2)).removed, true);
  assert.equal(calls(solo, "DELETE", /events\/ev1$/).length, 1);
  assert.equal(calls(solo, "POST", /\/cancel$/).length, 0);
});

test("answer an invitation: accept, tentative with a proposed time, silent decline", async () => {
  const inv = EV({ isOrganizer: false, organizer: { emailAddress: { address: "boss@contoso.example" } }, responseStatus: { response: "notResponded" } });
  const c = calCtx(inv);
  let s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "accept", comment: "See you there" });
  assert.match(s.preview.who_is_notified, /boss@contoso\.example/);
  await commit(c, s);
  assert.deepEqual(calls(c, "POST", /\/accept$/)[0].json, { sendResponse: true, comment: "See you there" });
  s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "tentative", propose_start: "2026-11-20T12:00:00Z", propose_end: "2026-11-20T13:00:00Z", timezone: "UTC" });
  assert.deepEqual(s.preview.proposed_time, { start: "2026-11-20T12:00:00", end: "2026-11-20T13:00:00" });
  await commit(c, s);
  assert.deepEqual(calls(c, "POST", /\/tentativelyAccept$/)[0].json.proposedNewTime, { start: { dateTime: "2026-11-20T12:00:00", timeZone: "UTC" }, end: { dateTime: "2026-11-20T13:00:00", timeZone: "UTC" } });
  s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "decline", send_response: false });
  assert.match(s.preview.who_is_notified, /Nobody is told/);
  await commit(c, s);
  assert.deepEqual(calls(c, "POST", /\/decline$/)[0].json, { sendResponse: false });
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "accept", propose_start: "2026-11-20T12:00:00Z", propose_end: "2026-11-20T13:00:00Z" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "calendar_change_stage", { event_id: "ev1", action: "decline", send_response: false, propose_start: "2026-11-20T12:00:00Z", propose_end: "2026-11-20T13:00:00Z" }), (e) => e.code === "INVALID_ARGUMENT");
  const closed = calCtx({ ...inv, allowNewTimeProposals: false });
  await assert.rejects(call(closed, "calendar_change_stage", { event_id: "ev1", action: "decline", propose_start: "2026-11-20T12:00:00Z", propose_end: "2026-11-20T13:00:00Z" }), (e) => e.code === "NOT_ALLOWED");
});

test("recurring: a series and an occurrence are told apart in the preview", async () => {
  const series = await call(calCtx(EV({ type: "seriesMaster" })), "calendar_change_stage", { event_id: "ev1", action: "change", subject: "Weekly sync" });
  assert.match(series.preview.recurrence, /EVERY occurrence/);
  const one = await call(calCtx(EV({ type: "occurrence" })), "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  assert.match(one.preview.recurrence, /only this occurrence/);
});

test("the event changed after the preview: nothing is done, the stage can be redone", async () => {
  const c = calCtx(EV(), [], "ck2-someone-edited-it");
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  await assert.rejects(commit(c, s), (e) => e.code === "EVENT_CHANGED");
  assert.equal(calls(c, "POST", /\/cancel$/).length, 0);
  await assert.rejects(commit(c, s), (e) => e.code === "EVENT_CHANGED", "still staged, not stuck in 'committing'");
});

test("an uncertain cancellation or answer is never repeated; a failed change can be retried", async () => {
  const c = calCtx(EV(), [[/^POST .*\/cancel$/, () => json({ error: { code: "x" } }, 503)]]);
  let s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  await assert.rejects(commit(c, s), (e) => e.code === "SEND_UNCERTAIN" && /calendar_get_event/.test(e.hint));
  await assert.rejects(commit(c, s), (e) => e.code === "STAGE_NOT_READY");
  let tries = 0;
  const p = calCtx(EV(), [[/^PATCH .*\/me\/events\/ev1$/, () => (++tries === 1 ? json({ error: { code: "x" } }, 503) : json({ id: "ev1" }))]]);
  s = await call(p, "calendar_change_stage", { event_id: "ev1", action: "change", subject: "New" });
  await assert.rejects(commit(p, s));
  assert.equal((await commit(p, s)).done, true);
});

test("discard works for a staged change; an already-cancelled event cannot be staged", async () => {
  const c = calCtx(EV());
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  assert.equal((await call(c, "calendar_discard", { stage_id: s.stage_id })).discarded, true);
  await assert.rejects(commit(c, s), (e) => e.code === "STAGE_NOT_READY" || e.code === "ALREADY_DONE");
  await assert.rejects(call(calCtx(EV({ isCancelled: true })), "calendar_change_stage", { event_id: "ev1", action: "cancel" }), (e) => e.code === "ALREADY_DONE");
});

test("0.13.0: stage ids and digests must be strings everywhere (no parser differential with the hook)", async () => {
  const c = calCtx(EV());
  const s = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  for (const bad of [{ stage_id: [s.stage_id], digest: s.digest }, { stage_id: s.stage_id, digest: [s.digest] }]) {
    await assert.rejects(call(c, "calendar_commit", bad), (e) => e.code === "INVALID_ARGUMENT", JSON.stringify(bad));
  }
  await assert.rejects(call(c, "calendar_discard", { stage_id: [s.stage_id] }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "teams_commit", { stage_id: ["teams_x"], digest: "d" }), (e) => e.code === "INVALID_ARGUMENT");
  assert.equal(calls(c, "POST", /\/cancel$/).length, 0);
});

test("0.13.0: the stage binds the event's identity (shown in the confirmation) into the digest", async () => {
  const s = await call(calCtx(EV({ type: "seriesMaster" })), "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  const { createStaging } = await import("../server/staging.mjs");
  const c = calCtx(EV({ type: "seriesMaster" }));
  const s2 = await call(c, "calendar_change_stage", { event_id: "ev1", action: "cancel" });
  const st = createStaging(c.ctx.cfg).get(s2.stage_id);
  assert.deepEqual(st.payload.shown, { subject: "Design review", start: "2026-11-20T08:00:00", end: "2026-11-20T09:00:00", organizer: "me@contoso.example", attendees: 2, series: "series" });
  assert.ok(s.digest);
});

test("0.13.1: confirm mode is read only from the Claude Code plugin setting, never settings.json, the CLI or a tool", async () => {
  const { mkdtempSync } = await import("node:fs"); const { tmpdir } = await import("node:os"); const { join } = await import("node:path");
  const { saveSettings } = await import("../server/setup.mjs"); const { resolveConfig, SETTINGS_KEYS } = await import("../server/config.mjs");
  assert.ok(!SETTINGS_KEYS.includes("confirm_mode"), "not a settings.json key");
  const h = mkdtempSync(join(tmpdir(), "m365-v131-"));
  assert.throws(() => saveSettings(resolveConfig({ M365_HOME: h }), { confirm_mode: "chat" }, { viaTool: false }));
  assert.equal(resolveConfig({ M365_HOME: h, M365_CONFIRM_MODE: "chat" }).confirmMode, "always", "a plain env var does not count");
  assert.equal(resolveConfig({ M365_HOME: h, M365_PLUGIN_CONFIRM_MODE: "chat" }).confirmMode, "chat", "the plugin setting, passed by .mcp.json, is shown in status");
  const c = calCtx(EV());
  await assert.rejects(call(c, "m365_setup_save", { confirm_mode: "chat" }));
  assert.equal((await call(c, "m365_auth_status", {})).confirm_mode, "always");
});

test("0.13.2: the yes/no switch 'Approve sends in the chat' sets chat mode; the old text value still counts", async () => {
  const { resolveConfig } = await import("../server/config.mjs");
  const mode = (env) => resolveConfig({ M365_HOME: "x", ...env }).confirmMode;
  assert.equal(mode({ M365_PLUGIN_CHAT_APPROVAL: "true" }), "chat");
  assert.equal(mode({ M365_PLUGIN_CHAT_APPROVAL: "false" }), "always");
  assert.equal(mode({ M365_PLUGIN_CHAT_APPROVAL: "${user_config.m365_chat_approval}" }), "always");
  assert.equal(mode({ M365_PLUGIN_CONFIRM_MODE: "chat" }), "chat", "0.13.1 text value");
  assert.equal(mode({}), "always");
});

test("0.13.2: chat search matches every word in any order, and lists the 1:1 chat first", async () => {
  const { ctxFor, call: call2, json: j2, TOK: T2 } = await import("./_helpers.mjs");
  const chats = [
    { id: "g1", chatType: "group", topic: "RC - Account Manager (Amr Shabara)", members: [{ displayName: "Mahmoud", email: "m@contoso.example" }], lastMessagePreview: { createdDateTime: "2026-11-12T10:00:00Z" } },
    { id: "o1", chatType: "oneOnOne", topic: null, members: [{ displayName: "Amr Mohamed Shabara", email: "ashabara@contoso.example" }, { displayName: "Me", email: "me@contoso.example" }], lastMessagePreview: { createdDateTime: "2026-11-11T10:00:00Z" } },
    { id: "o2", chatType: "oneOnOne", topic: null, members: [{ displayName: "Amr Atya", email: "aatya@contoso.example" }], lastMessagePreview: { createdDateTime: "2026-11-10T10:00:00Z" } },
  ];
  const c = ctxFor([T2, [/^GET .*\/me\/chats\?/, () => j2({ value: chats })]]);
  const ids = async (q) => (await call2(c, "teams_find_chat", { query: q })).chats.map((x) => x.chat_id);
  assert.deepEqual(await ids("Amr Shabara"), ["o1", "g1"], "the 1:1 chat with him first, then the group named after him");
  assert.deepEqual(await ids("shabara amr"), ["o1", "g1"]);
  assert.deepEqual(await ids("Amr"), ["o1", "o2", "g1"]);
  assert.deepEqual(await ids("ashabara@contoso.example"), ["o1"]);
});

test("0.13.3: the chat reader says when a message carries pictures (emoji are not counted)", async () => {
  const { ctxFor, call: call3, json: j3, TOK: T3 } = await import("./_helpers.mjs");
  const msgs = [
    { id: "p1", messageType: "message", from: { user: { id: "u1", displayName: "Me" } }, body: { contentType: "html", content: '<p><img src="https://graph.microsoft.com/v1.0/chats/x/messages/p1/hostedContents/aW1n/$value" alt="screenshot-1.png"></p>' } },
    { id: "e1", messageType: "message", from: { user: { id: "u2", displayName: "Amr" } }, body: { contentType: "html", content: '<p>haha <img itemtype="http://schema.skype.com/Emoji" alt="😂" src="x"></p>' } },
    { id: "t1", messageType: "message", from: { user: { id: "u2", displayName: "Amr" } }, body: { contentType: "text", content: "<img src=x>" } },
  ];
  const c = ctxFor([T3, [/^GET .*\/chats\/c1\/messages\?/, () => j3({ value: msgs })]]);
  const out = (await call3(c, "teams_read_chat", { chat_id: "c1" })).messages;
  assert.equal(out[0].pictures, 1); assert.match(out[0].pictures_note, /never describe it/);
  assert.equal(out[1].pictures, undefined, "an emoji is not a picture");
  assert.equal(out[2].pictures, undefined, "plain text that looks like a tag is not a picture");
});
