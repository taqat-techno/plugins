// 0.14.0: teams_meeting_attendance - real attendance from Teams attendance reports, for one meeting or a date range.
// Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";
import { onlineMeetingId } from "../server/tools/meetings.mjs";
import { resolveConfig } from "../server/config.mjs";

const CHAT = "19:meeting_abc123@thread.v2";
const JOIN = `https://teams.microsoft.com/l/meetup-join/${encodeURIComponent(CHAT)}/0?context=x`;
const MID = onlineMeetingId("org-1", CHAT);
const ME = [/^GET .*\/me\?\$select=id,mail/, () => json({ id: "me-1", mail: "Me@Contoso.example" })];
const CHATINFO = [/^GET .*\/chats\/19%3Ameeting_abc123%40thread\.v2\?/, () => json({ id: CHAT, onlineMeetingInfo: { organizer: { id: "org-1" } } })];
const EVENT = (over = {}) => ({ id: "ev1", subject: "Sprint review", start: { dateTime: "2026-11-20T08:00:00" }, end: { dateTime: "2026-11-20T09:00:00" },
  isOrganizer: true, organizer: { emailAddress: { name: "Me" } }, responseStatus: { response: "organizer" }, isOnlineMeeting: true, onlineMeeting: { joinUrl: JOIN }, ...over });
const REPORT = (id, start, end, records) => ({ id, meetingStartDateTime: start, meetingEndDateTime: end, totalParticipantCount: records.length, attendanceRecords: records });
const REC = (id, email, name, secs, role = "Attendee") => ({ identity: { id, displayName: name }, emailAddress: email, role, totalAttendanceInSeconds: secs,
  attendanceIntervals: [{ joinDateTime: "2026-11-20T08:01:00Z", leaveDateTime: "2026-11-20T08:41:00Z", durationInSeconds: secs }] });
const reportsRoutes = (reports) => [
  [new RegExp(`^GET .*/me/onlineMeetings/${encodeURIComponent(MID)}/attendanceReports$`), () => json({ value: reports.map(({ attendanceRecords, ...r }) => ({ ...r, attendanceRecords: [] })) })],
  [new RegExp(`^GET .*/me/onlineMeetings/${encodeURIComponent(MID)}/attendanceReports/([^/?]+)\\?\\$expand=attendanceRecords$`), ({ url }) => {
    const id = decodeURIComponent(/attendanceReports\/([^/?]+)\?/.exec(url)[1]);
    return json(reports.find((r) => r.id === id));
  }],
];
const ctx = (routes) => ctxFor([TOK, ME, CHATINFO, ...routes], { M365_MODULES: "calendar,teams,meetings" });
const calls = (c, re) => c.fetch.calls.filter((x) => re.test(x.url));

test("organizer: every session with every attendee, the user first, minutes and join/leave intervals", async () => {
  const c = ctx([[/^GET .*\/me\/events\/ev1\?/, () => json(EVENT())], ...reportsRoutes([
    REPORT("r1", "2026-11-20T08:00:00Z", "2026-11-20T09:00:00Z", [REC("u2", "sara@contoso.example", "Sara", 3000), REC("me-1", "me@contoso.example", "Me", 2400, "Organizer")]),
  ])]);
  const r = await call(c, "teams_meeting_attendance", { event_id: "ev1", timezone: "UTC" });
  assert.equal(r.status, "ok"); assert.equal(r.my_total_minutes, 40);
  const s = r.sessions[0];
  assert.equal(s.attended, true); assert.equal(s.participants, 2);
  assert.deepEqual(s.attendees.map((p) => [p.email, p.me, p.minutes, p.role]), [["me@contoso.example", true, 40, "Organizer"], ["sara@contoso.example", false, 50, "Attendee"]]);
  assert.deepEqual(s.attendees[0].intervals[0], { joined: "2026-11-20T08:01:00", left: "2026-11-20T08:41:00", seconds: 2400 });
  assert.match(r.note, /attendee names and emails/);
  assert.equal(calls(c, /\/me\/onlineMeetings\?/).length, 0, "the meeting id comes from the meeting chat, no join-link lookup needed");
});

test("attendee refused (403): a clear ATTENDANCE_NOT_AVAILABLE with the invitation, labelled as not proof", async () => {
  const c = ctx([[/^GET .*\/me\/events\/ev1\?/, () => json(EVENT({ isOrganizer: false, organizer: { emailAddress: { name: "Boss" } }, responseStatus: { response: "accepted" } }))],
    [/attendanceReports/, () => json({ error: { code: "Forbidden" } }, 403)]]);
  const r = await call(c, "teams_meeting_attendance", { event_id: "ev1" });
  assert.equal(r.status, "ATTENDANCE_NOT_AVAILABLE");
  assert.match(r.reason, /organizer/);
  assert.deepEqual(r.fallback, { invited: true, my_response: "accepted", organizer: "Boss", note: "Invitation and response only: this is not proof that the user joined." });
});

test("an event that is not a Teams meeting, and a bad join link, are refused plainly", async () => {
  const c = ctx([[/^GET .*\/me\/events\/ev1\?/, () => json(EVENT({ isOnlineMeeting: false, onlineMeeting: null }))]]);
  await assert.rejects(call(c, "teams_meeting_attendance", { event_id: "ev1" }), (e) => e.code === "NOT_A_MEETING");
  await assert.rejects(call(c, "teams_meeting_attendance", { join_url: "https://evil.example/x" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "teams_meeting_attendance", { event_id: "ev1", from: "2026-11-20", to: "2026-11-20" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "teams_meeting_attendance", { from: "2026-11-01", to: "2026-12-20" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("a join link whose chat is unknown falls back to the JoinWebUrl lookup", async () => {
  const other = "https://teams.microsoft.com/l/meetup-join/somethingelse";
  const c = ctx([[/^GET .*\/me\/onlineMeetings\?\$filter=/, () => json({ value: [{ id: MID }] })], ...reportsRoutes([
    REPORT("r1", "2026-11-20T08:00:00Z", "2026-11-20T09:00:00Z", [REC("me-1", "me@contoso.example", "Me", 600)])])]);
  const r = await call(c, "teams_meeting_attendance", { join_url: other });
  assert.equal(r.my_total_minutes, 10);
  assert.match(decodeURIComponent(calls(c, /\/me\/onlineMeetings\?\$filter=/)[0].url), /JoinWebUrl eq 'https:\/\/teams\.microsoft\.com\/l\/meetup-join\/somethingelse'/);
});

test("a date range: one row per Teams meeting with the user's minutes; a recurring meeting keeps only its own session", async () => {
  const OTHER_CHAT = "19:meeting_zzz@thread.v2";
  const OTHER_JOIN = `https://teams.microsoft.com/l/meetup-join/${encodeURIComponent(OTHER_CHAT)}/0`;
  const OTHER_MID = onlineMeetingId("boss-9", OTHER_CHAT);
  const evs = [
    EVENT({ id: "d1", subject: "Daily", start: { dateTime: "2026-11-19T07:00:00" }, end: { dateTime: "2026-11-19T07:15:00" } }),
    EVENT({ id: "d2", subject: "Daily", start: { dateTime: "2026-11-20T07:00:00" }, end: { dateTime: "2026-11-20T07:15:00" } }),
    EVENT({ id: "x1", subject: "Client call", isOrganizer: false, responseStatus: { response: "tentativelyAccepted" }, organizer: { emailAddress: { name: "Boss" } },
      start: { dateTime: "2026-11-20T10:00:00" }, end: { dateTime: "2026-11-20T11:00:00" }, onlineMeeting: { joinUrl: OTHER_JOIN } }),
    EVENT({ id: "n1", subject: "Lunch", isOnlineMeeting: false, onlineMeeting: null }),
    EVENT({ id: "c1", subject: "Cancelled", isCancelled: true }),
  ];
  const c = ctx([[/^GET .*\/me\/calendarView/, () => json({ value: evs })],
    [/^GET .*\/chats\/19%3Ameeting_zzz%40thread\.v2\?/, () => json({ id: OTHER_CHAT, onlineMeetingInfo: { organizer: { id: "boss-9" } } })],
    [new RegExp(`/me/onlineMeetings/${encodeURIComponent(OTHER_MID)}/attendanceReports`), () => json({ error: { code: "Forbidden" } }, 403)],
    ...reportsRoutes([
      REPORT("day19", "2026-11-19T07:00:00Z", "2026-11-19T07:16:00Z", [REC("me-1", "me@contoso.example", "Me", 900)]),
      REPORT("day20", "2026-11-20T07:01:00Z", "2026-11-20T07:20:00Z", [REC("me-1", "me@contoso.example", "Me", 1200), REC("u2", "s@contoso.example", "Sara", 1200)]),
    ])]);
  const r = await call(c, "teams_meeting_attendance", { from: "2026-11-19", to: "2026-11-20", timezone: "UTC" });
  assert.equal(r.meetings, 3, "cancelled and non-Teams events are left out");
  const by = Object.fromEntries(r.rows.map((x) => [x.event_id, x]));
  assert.deepEqual([by.d1.status, by.d1.my_minutes, by.d1.sessions], ["ok", 15, 1]);
  assert.deepEqual([by.d2.status, by.d2.my_minutes, by.d2.sessions], ["ok", 20, 1], "only that day's session, not the series' other days");
  assert.equal(by.x1.status, "ATTENDANCE_NOT_AVAILABLE"); assert.equal(by.x1.attended, null); assert.equal(by.x1.my_response, "tentativelyAccepted");
  assert.match(by.x1.note, /not proof/);
  assert.equal(r.my_total_minutes, 35);
  assert.equal(calls(c, new RegExp(`/me/onlineMeetings/${encodeURIComponent(MID)}/attendanceReports$`)).length, 1, "a recurring meeting's reports are fetched once");
});

test("permissions: attendance scopes only with the meetings module", () => {
  const base = { M365_HOME: "x", M365_CLIENT_ID: "c" };
  assert.ok(!resolveConfig(base).scopes.includes("OnlineMeetingArtifact.Read.All"));
  const s = resolveConfig({ ...base, M365_MODULES: "meetings" }).scopes;
  assert.ok(s.includes("OnlineMeetingArtifact.Read.All") && s.includes("OnlineMeetings.Read"));
});
