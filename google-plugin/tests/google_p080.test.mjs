// 0.8.0 tests: local attachments (inline and regular) on REST drafts, the attachment folder rules, the bounce check
// after send, and the attachment list in the draft snapshot. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { TOKEN, ctxFor, json, NOW as TEST_NOW } from "./_helpers.mjs";
import { parseMime, attachmentsOf, bodySources } from "../server/mime.mjs";
import { allowedFile, readAttachments } from "../server/attach.mjs";
import { resolveConfig } from "../server/config.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const REST = /^(GET|POST|PUT|PATCH|DELETE) https:\/\/(gmail|www)\.googleapis\.com\//;
const SEED = { account: { email: "me@mail.example" } };
const SEND_AS = { sendAs: [
  { sendAsEmail: "me@mail.example", isPrimary: true, isDefault: true, signature: "" },
  { sendAsEmail: "info@shop.example", displayName: "Shop", verificationStatus: "accepted", signature: "<div>Shop team</div>" },
] };
const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3]);

function rest(routes) {
  return [REST, async ({ url, init, body }) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/gmail\/v1\/users\/me\//, "gmail:");
    for (const [k, h] of routes) {
      const [m, re] = k.split(" ");
      if (m === (init.method || "GET") && new RegExp(`^${re}$`).test(path)) return h({ u, body: body ? JSON.parse(body) : undefined });
    }
    return json({ error: { code: 404, message: `no fake for ${init.method} ${path}` } }, 404);
  }];
}
const rawOf = (body) => parseMime(Buffer.from(Buffer.from(body.message.raw, "base64url").toString("latin1"), "latin1"));
function files() {
  const dir = mkdtempSync(join(tmpdir(), "gp-att-"));
  writeFileSync(join(dir, "logo.png"), PNG);
  writeFileSync(join(dir, "offer.pdf"), "%PDF-1.4 offer");
  writeFileSync(join(dir, "token-cache.json"), "{}");
  writeFileSync(join(dir, ".env"), "SECRET=1");
  return dir;
}

test("create_draft with attachments: inline image in multipart/related (cid), file in multipart/mixed, signature kept", async () => {
  const dir = files();
  let posted;
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => { posted = body; return json({ id: "d1", message: { id: "m1", threadId: "t1" } }); }],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_ATTACH_DIRS: dir } });
  const r = await c.callTool("gmail_rest_create_draft", {
    from: "info@shop.example", to: ["a@b.example"], subject: "Offer", htmlBody: '<p>See <img src="cid:logo1"></p>', body: "See logo",
    attachments: [{ path: join(dir, "logo.png"), inline: true, contentId: "logo1" }, { path: join(dir, "offer.pdf"), filename: "Offer 2026.pdf" }],
  });
  assert.equal(r.signature_added, true);
  assert.deepEqual(r.attachments, [{ filename: "logo.png", mimeType: "image/png", size: PNG.length, inline: true, contentId: "logo1" }, { filename: "Offer 2026.pdf", mimeType: "application/pdf", size: 14, inline: false }]);
  const m = rawOf(posted);
  assert.equal(m.mimeType, "multipart/mixed");
  assert.equal(m.children[0].mimeType, "multipart/related");
  const logo = m.children[0].children[1];
  assert.deepEqual([logo.mimeType, logo.headers["content-id"][0], logo.disposition], ["image/png", "<logo1>", "inline"]);
  assert.deepEqual([...logo.body], [...PNG]);
  assert.equal(m.children[1].filename, "Offer 2026.pdf");
  assert.match(bodySources(m).html, /cid:logo1[\s\S]*Shop team/, "the body and the signature are both there");
  assert.deepEqual(attachmentsOf(m).map((a) => [a.filename, a.inline, a.contentId ?? null]), [["logo.png", true, "logo1"], ["Offer 2026.pdf", false, null]]);
});

test("attachment folder rules: absolute paths inside the allowed folders only; no network/stream paths; keys, tokens and the plugin's files refused", () => {
  const dir = files();
  const other = mkdtempSync(join(tmpdir(), "gp-other-"));
  writeFileSync(join(other, "x.txt"), "x");
  const home = mkdtempSync(join(tmpdir(), "gp-home-"));
  const cfg = resolveConfig({ GOOGLE_ATTACH_DIRS: `${dir}`, GOOGLE_PLUGIN_HOME: home });
  assert.equal(allowedFile(cfg, join(dir, "offer.pdf")).size, 14);
  const code = (p, c = cfg) => { try { allowedFile(c, p); return "ok"; } catch (e) { return e.code; } };
  assert.equal(code(join(other, "x.txt")), "PATH_NOT_ALLOWED");
  assert.equal(code("offer.pdf"), "INVALID_ARGUMENT");
  assert.equal(code(` ${join(dir, "offer.pdf")}`), "INVALID_ARGUMENT");
  assert.equal(code("\\\\evil-host\\share\\offer.pdf"), "PATH_NOT_ALLOWED");
  assert.equal(code(join(dir, "..", "x.txt")), "PATH_NOT_ALLOWED");
  assert.equal(code(join(dir, "token-cache.json")), "PATH_NOT_ALLOWED");
  assert.equal(code(join(dir, ".env")), "PATH_NOT_ALLOWED");
  assert.equal(code(join(dir, "missing.pdf")), "NOT_FOUND");
  mkdirSync(join(dir, "inner"));
  writeFileSync(join(dir, "inner", "a.txt"), "a");
  assert.equal(code(join(dir, "inner", "a.txt")), "ok");
  // The plugin's own folder is refused even when it is inside an allowed folder.
  const nestedHome = join(dir, "plugin-home");
  mkdirSync(nestedHome);
  writeFileSync(join(nestedHome, "notes.txt"), "n");
  assert.equal(code(join(nestedHome, "notes.txt"), resolveConfig({ GOOGLE_ATTACH_DIRS: dir, GOOGLE_PLUGIN_HOME: nestedHome })), "PATH_NOT_ALLOWED");
  // Default: the download folder; nothing configured: ATTACH_NOT_CONFIGURED.
  assert.equal(code(join(dir, "offer.pdf"), resolveConfig({ GOOGLE_DOWNLOAD_DIR: dir, GOOGLE_PLUGIN_HOME: home })), "ok");
  assert.equal(code(join(dir, "offer.pdf"), resolveConfig({ GOOGLE_PLUGIN_HOME: home })), "ATTACH_NOT_CONFIGURED");
  // inline needs a safe contentId; 25 MB in all.
  assert.throws(() => readAttachments(cfg, [{ path: join(dir, "logo.png"), inline: true }]), { code: "INVALID_ARGUMENT" });
  assert.throws(() => readAttachments(cfg, [{ path: join(dir, "logo.png"), inline: true, contentId: "a b>" }]), { code: "INVALID_ARGUMENT" });
  writeFileSync(join(dir, "big1.bin"), Buffer.alloc(13 * 1024 * 1024));
  writeFileSync(join(dir, "big2.bin"), Buffer.alloc(13 * 1024 * 1024));
  assert.throws(() => readAttachments(cfg, [{ path: join(dir, "big1.bin") }, { path: join(dir, "big2.bin") }]), { code: "TOO_LARGE" });
});

test("update_draft: attachments not given are kept (inline stays inline); given ones replace the list; reply drafts take attachments", async () => {
  const dir = files();
  let current, putBody;
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => { current = body.message.raw; putBody = body; return json({ id: "d1", message: { id: "m1", threadId: "t1" } }); }],
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: current } })],
    ["PUT gmail:drafts/d1", ({ body }) => { putBody = body; current = body.message.raw; return json({ id: "d1", message: { id: "m2", threadId: "t1" } }); }],
    ["GET gmail:messages/q1", () => json({ id: "q1", threadId: "t5", payload: { headers: [{ name: "From", value: "c@x.example" }, { name: "To", value: "info@shop.example" }, { name: "Subject", value: "Q" }, { name: "Message-ID", value: "<q1@x>" }] } })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_ATTACH_DIRS: dir } });
  await c.callTool("gmail_rest_create_draft", { from: "info@shop.example", to: ["a@b.example"], htmlBody: '<img src="cid:L">', attachments: [{ path: join(dir, "logo.png"), inline: true, contentId: "L" }, { path: join(dir, "offer.pdf") }] });

  const u1 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", subject: "New" });
  assert.deepEqual(u1.attachments.map((a) => [a.filename, a.inline, a.contentId ?? null]), [["logo.png", true, "L"], ["offer.pdf", false, null]]);
  const m1 = rawOf(putBody);
  assert.equal(m1.children[0].children[1].headers["content-id"][0], "<L>");

  const u2 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", attachments: [{ path: join(dir, "offer.pdf"), filename: "only.pdf" }] });
  assert.deepEqual(u2.attachments.map((a) => a.filename), ["only.pdf"]);
  assert.ok(u2.changed.includes("attachments"));
  assert.deepEqual(attachmentsOf(rawOf(putBody)).map((a) => a.filename), ["only.pdf"]);

  const rr = await c.callTool("gmail_rest_create_reply_draft", { messageId: "q1", body: "Here", attachments: [{ path: join(dir, "offer.pdf") }] });
  assert.deepEqual(rr.attachments.map((a) => a.filename), ["offer.pdf"]);
  assert.equal(putBody.message.threadId, "t5");
  await assert.rejects(c.callTool("gmail_rest_create_draft", { to: ["a@b.example"], body: "x", attachments: [{ path: join(dir, "token-cache.json") }] }), { code: "PATH_NOT_ALLOWED" });
});

// ------------------------------------------------------------------------------------------------ bounce check

function sendCtx({ thread = [], search = [], seconds = "4" } = {}) {
  const NOW = TEST_NOW;
  const draft = Buffer.from(["From: Shop <info@shop.example>", "To: smsm@x.example", "Subject: Hi", "Content-Type: text/plain", "", "Body"].join("\r\n")).toString("base64url");
  const sleeps = [];
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: draft } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:messages/send", () => json({ id: "sent-1", threadId: "t1" })],
    ["DELETE gmail:drafts/d1", () => new Response(null, { status: 204 })],
    ["GET gmail:threads/t1", () => json({ id: "t1", messages: [{ id: "sent-1", internalDate: String(NOW), payload: { headers: [{ name: "From", value: "info@shop.example" }] } }, ...thread] })],
    ["GET gmail:messages", () => json({ messages: search.map((m) => ({ id: m.id })) })],
    ...search.map((m) => [`GET gmail:messages/${m.id}`, () => json(m)]),
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_BOUNCE_CHECK_SECONDS: seconds }, deps: { sleep: async (ms) => { sleeps.push(ms); } } });
  return { c, sleeps, NOW };
}
const daemon = (id, when, snippet) => ({ id, internalDate: String(when), snippet, payload: { headers: [{ name: "From", value: "Mail Delivery Subsystem <mailer-daemon@googlemail.com>" }, { name: "Subject", value: "Delivery Status Notification (Failure)" }] } });
async function sendIt(c) {
  const pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d1" });
  return c.callTool("gmail_rest_send_draft", { draftId: "d1", digest: pv.digest });
}

test("bounce check: a mailer-daemon message in the sent thread after the send is reported as delivery_failed with a hint", async () => {
  const NOW = TEST_NOW;
  const { c } = sendCtx({ thread: [daemon("b1", NOW + 1000, "Send mail as SMTP: 535 5.7.8 Username and Password not accepted &lt;x&gt;")] });
  const r = await sendIt(c);
  assert.deepEqual([r.sent, r.delivery_failed, r.bounce_message_id], [true, true, "b1"]);
  assert.equal(r.bounce_reason, "Send mail as SMTP: 535 5.7.8 Username and Password not accepted <x>");
  assert.match(r.hint, /Gmail could not send as info@shop\.example[\s\S]*Send mail as/);
  assert.equal(r.untrusted, true);
});

test("bounce check: none seen means delivery_failed false and 'no bounce seen within N s' (never 'delivered'); unrelated or old bounces are ignored", async () => {
  const NOW = TEST_NOW;
  const { c, sleeps } = sendCtx({ search: [daemon("u1", NOW + 500, "Your message to someone@else.example could not be delivered"), daemon("old", NOW - 3_600_000, "smsm@x.example failed")] });
  const r = await sendIt(c);
  assert.equal(r.delivery_failed, false);
  assert.match(r.bounce_check, /^no bounce seen within 4 s \(this does not prove delivery\)$/);
  assert.deepEqual(sleeps, [2000, 2000], "checks at 0, 2 and 4 s");
  assert.equal(JSON.stringify(r).includes("delivered\""), false);

  const hit = sendCtx({ search: [daemon("s1", NOW + 800, "Address not found: smsm@x.example")] });
  const r2 = await sendIt(hit.c);
  assert.deepEqual([r2.delivery_failed, r2.bounce_message_id], [true, "s1"], "a search hit counts only when it names an address of this message");

  const off = sendCtx({ seconds: "0" });
  const r3 = await sendIt(off.c);
  assert.deepEqual([r3.delivery_failed, off.sleeps.length], [null, 0]);
  assert.match(r3.bounce_check, /skipped/);
});

test("snapshot lists the attachments (name, type, size, inline marked) in the header block and the result", async () => {
  const dir = files();
  let current;
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => { current = body.message.raw; return json({ id: "d1", message: { id: "m1", threadId: "t1" } }); }],
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: current } })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_ATTACH_DIRS: dir, GOOGLE_DOWNLOAD_DIR: dir } });
  await c.callTool("gmail_rest_create_draft", { to: ["a@b.example"], htmlBody: '<img src="cid:L">', attachments: [{ path: join(dir, "logo.png"), inline: true, contentId: "L" }, { path: join(dir, "offer.pdf"), filename: "<b>x</b>.pdf" }] });
  const r = await c.callTool("gmail_rest_save_draft_html", { draftId: "d1" });
  assert.deepEqual(r.attachments.map((a) => [a.filename, a.inline]), [["logo.png", true], ["<b>x<_b>.pdf", false]]);
  const page = readFileSync(r.path, "utf8");
  assert.match(page, /<th>Attachments<\/th><td>logo\.png <span class="gp-att">\(image\/png, 11 bytes, inline in the body\)<\/span><br>&lt;b&gt;x&lt;_b&gt;\.pdf <span class="gp-att">\(application\/pdf, 14 bytes\)<\/span>/);
  assert.match(page, /src="data:image\/png;base64,/, "the inline image is shown in the body");
});

// ------------------------------------------------------------------------------------------------ 0.8.1 calendar_rest_delete_event

function calCtx(event, env = {}, { lookupFails = false, lookupStatus = 404 } = {}) {
  const seen = [];
  const c = ctxFor([tokenOk, [/^(GET|DELETE) https:\/\/www\.googleapis\.com\/calendar\/v3\//, ({ url, init }) => {
    const u = new URL(url);
    seen.push(`${init.method || "GET"} ${u.pathname} ${u.search}`);
    if ((init.method || "GET") === "GET") return lookupFails ? json({ error: { code: lookupStatus, message: lookupStatus === 403 ? "Google Calendar API has not been used in project 1 before or it is disabled" : "Not Found" } }, lookupStatus) : json(event);
    return new Response(null, { status: 204 });
  }]], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", ...env } });
  return { c, seen };
}
const SOLO = { id: "e1", summary: "Dentist", start: { dateTime: "2026-11-27T23:00:00+02:00" }, organizer: { email: "me@mail.example", self: true } };
const GROUP = { ...SOLO, attendees: [{ email: "me@mail.example", self: true }, { email: "pal@x.example" }] };

test("calendar_rest_delete_event: looks up, deletes with sendUpdates (default none), and says what it deleted", async () => {
  const { c, seen } = calCtx(SOLO);
  const r = await c.callTool("calendar_rest_delete_event", { eventId: "e1" });
  assert.deepEqual([r.deleted, r.eventId, r.calendarId, r.summary, r.start, r.recurring, r.sendUpdates], [true, "e1", "primary", "Dentist", "2026-11-27T23:00:00+02:00", "single", "none"]);
  assert.deepEqual(seen, ["GET /calendar/v3/calendars/primary/events/e1 ", "DELETE /calendar/v3/calendars/primary/events/e1 ?sendUpdates=none"]);
  const inst = calCtx({ ...SOLO, id: "e1_20261127", recurringEventId: "e1" });
  const ri = await inst.c.callTool("calendar_rest_delete_event", { eventId: "e1_20261127", calendarId: "work@group.example", sendUpdates: "all" });
  assert.deepEqual([ri.recurring, ri.recurringEventId, ri.calendarId], ["instance", "e1", "work@group.example"]);
  assert.match(inst.seen[1], /calendars\/work%40group\.example\/events\/e1_20261127 \?sendUpdates=all$/);
  const series = calCtx({ ...SOLO, recurrence: ["RRULE:FREQ=WEEKLY"] });
  assert.equal((await series.c.callTool("calendar_rest_delete_event", { eventId: "e1" })).recurring, "series");
  await assert.rejects(calCtx(SOLO).c.callTool("calendar_rest_delete_event", { eventId: "e1", sendUpdates: "everyone" }), { code: "INVALID_ARGUMENT" });
  const nf = calCtx(SOLO, {}, { lookupFails: true });
  await assert.rejects(nf.c.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "NOT_FOUND" });
  assert.equal(nf.seen.filter((x) => x.startsWith("DELETE")).length, 0, "nothing deleted when the lookup fails");
  // Off by default: not listed, refused.
  const off = ctxFor([tokenOk], { seed: SEED });
  await assert.rejects(off.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "UNKNOWN_TOOL" });
});

test("calendar_rest_delete_event with GOOGLE_REFUSE_GUEST_EVENTS=1: other attendees refuse (GUESTS_NEED_APPROVAL); a failed lookup refuses with its own code; nothing is deleted", async () => {
  const ON = { GOOGLE_REFUSE_GUEST_EVENTS: "1" };
  const g = calCtx(GROUP, ON);
  await assert.rejects(g.c.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "GUESTS_NEED_APPROVAL" });
  const o = calCtx({ ...SOLO, organizer: { email: "boss@x.example" } }, ON);
  await assert.rejects(o.c.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "GUESTS_NEED_APPROVAL" });
  const f = calCtx(SOLO, ON, { lookupFails: true });
  await assert.rejects(f.c.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "NOT_FOUND" });
  const forbidden = calCtx(SOLO, ON, { lookupFails: true, lookupStatus: 403 });
  await assert.rejects(forbidden.c.callTool("calendar_rest_delete_event", { eventId: "e1" }), (e) => e.code === "GOOGLE_FORBIDDEN" && /Calendar API has not been used/.test(e.message), "a setup error is not reported as needing approval");
  for (const x of [g, o, f, forbidden]) assert.equal(x.seen.filter((s) => s.startsWith("DELETE")).length, 0);
  // An error without a code is still refused as GUESTS_NEED_APPROVAL (fails closed).
  const { guestGuard } = await import("../server/guards.mjs");
  const ctx = { cfg: { refuseGuestEvents: true }, auth: { cachedAccount: () => "me@mail.example" } };
  await assert.rejects(guestGuard("calendar_delete_event", { eventId: "e1" }, ctx, async () => { throw new Error("boom"); }), { code: "GUESTS_NEED_APPROVAL" });
  assert.equal((await calCtx(SOLO, ON).c.callTool("calendar_rest_delete_event", { eventId: "e1" })).deleted, true);
  assert.equal((await calCtx(GROUP).c.callTool("calendar_rest_delete_event", { eventId: "e1" })).deleted, true, "guard off: guest events can be deleted");
});

test("calendar_rest_delete_event counts toward the hourly write limit; a guard refusal does not use a slot", async () => {
  const env = { GOOGLE_WRITE_LIMIT_PER_HOUR: "1", GOOGLE_REFUSE_GUEST_EVENTS: "1" };
  let event = GROUP;
  const c = ctxFor([tokenOk, [/^(GET|DELETE) https:\/\/www\.googleapis\.com\/calendar\/v3\//, ({ init }) => ((init.method || "GET") === "GET" ? json(event) : new Response(null, { status: 204 }))]], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", ...env } });
  await assert.rejects(c.callTool("calendar_rest_delete_event", { eventId: "e1" }), { code: "GUESTS_NEED_APPROVAL" });
  event = SOLO;
  await c.callTool("calendar_rest_delete_event", { eventId: "e1" });
  await assert.rejects(c.callTool("calendar_rest_delete_event", { eventId: "e2" }), { code: "WRITE_LIMIT_REACHED" });
});
