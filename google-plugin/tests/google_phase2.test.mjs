// Phase 2 tests: attachments and Drive saving, the guest guard, the write limit, the REST fallback (off by default),
// MIME building, and schema-check hints. A fake Google (OAuth, MCP and REST) stands in for the network.
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, mkdtempSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { TOKEN, ctxFor, json } from "./_helpers.mjs";
import { buildMessage, parseMime, attachmentsOf, bodyText, bodyViews, encodeWords } from "../server/mime.mjs";
import { createHandler } from "../server/mcp.mjs";
import { restTwins } from "../server/schema.mjs";
import { CLASSES } from "../server/tools/bridge.mjs";
import { runGrant, WRITE_GRANT_PLAN } from "../server/grant.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const MCP = /^POST https:\/\/(gmail|calendar|drive)mcp\.googleapis\.com\/mcp\/v1$/;
const REST = /^(GET|POST|PUT|PATCH|DELETE) https:\/\/(gmail|www)\.googleapis\.com\//;
const ok = (data) => ({ content: [{ type: "text", text: JSON.stringify(data) }], structuredContent: data });
const mcpRoute = (fn) => [MCP, async ({ body }) => { const rpc = JSON.parse(body); const r = await fn(rpc.params); return r instanceof Response ? r : json({ jsonrpc: "2.0", id: rpc.id, result: r }); }];
const calls = (c, re) => c.fetch.calls.filter((x) => re.test(`${x.method} ${x.url}`));
const mcpCalls = (c) => calls(c, MCP).map((x) => ({ ...x, json: JSON.parse(x.body) }));
const dl = () => mkdtempSync(join(tmpdir(), "gp-dl-"));
const SEND_AS = { sendAs: [
  { sendAsEmail: "me@mail.example", isPrimary: true, isDefault: true },
  { sendAsEmail: "info@shop.example", displayName: "Shop", verificationStatus: "accepted" },
  { sendAsEmail: "sales@shop.example", verificationStatus: "pending" },
] };
const SEED = { account: { email: "me@mail.example" } };

/** A REST fake: routes keyed "METHOD path-regex" over the URL after the API base. */
function rest(routes) {
  return [REST, async ({ url, init, body }) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/gmail\/v1\/users\/me\//, "gmail:").replace(/^\/drive\/v3\//, "drive:");
    for (const [k, h] of routes) {
      const [m, re] = k.split(" ");
      if (m === (init.method || "GET") && new RegExp(`^${re}$`).test(path)) return h({ u, body: body ? JSON.parse(body) : undefined });
    }
    return json({ error: { code: 404, message: `no fake for ${init.method} ${path}` } }, 404);
  }];
}
const decodeRaw = (b64) => Buffer.from(b64, "base64url").toString("utf8");

// ------------------------------------------------------------------------------------------------ REST switch

test("REST fallback off (default): the REST tools are not listed, a call is refused, and no REST host is contacted", async () => {
  const c = ctxFor([tokenOk, rest([])], { seed: SEED });
  const names = c.listTools().map((t) => t.name);
  for (const n of CLASSES.rest_tools) assert.ok(!names.includes(n), n);
  for (const n of CLASSES.rest_tools) await assert.rejects(c.callTool(n, { draftId: "d", fileId: "f", messageId: "m", to: ["a@b.example"], email: "a@b.example", role: "reader", name: "x", folderId: "p" }), { code: "UNKNOWN_TOOL" });
  assert.equal(calls(c, REST).length, 0);
  // Listed only with the switch, all with "_rest_" in the name (no collision with <module>_<Google name>).
  const on = ctxFor([tokenOk], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } }).listTools().map((t) => t.name);
  for (const n of CLASSES.rest_tools) { assert.ok(on.includes(n), n); assert.match(n, /^(gmail|drive|calendar)_rest_/); }
  // Read-only mode drops the write and confirm ones even with the switch on.
  const ro = ctxFor([tokenOk], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_READONLY: "1" } }).listTools().map((t) => t.name);
  assert.ok(CLASSES.rest_tools.filter((n) => !CLASSES.read.includes(n)).every((n) => !ro.includes(n)));
  assert.ok(ro.includes("gmail_rest_preview_draft"), "the preview is a read");
});

test("send: the previewed digest is required, the checked bytes are what is sent, and the draft is then deleted", async () => {
  const mime = (lines, body = "Body text") => Buffer.from([...lines, "Content-Type: text/plain", "", body].join("\r\n")).toString("base64url");
  let current = mime(["From: Shop <info@shop.example>", "To: x@y.example", "Subject: Hi"]);
  const mk = () => ctxFor([tokenOk, rest([
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: current } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:messages/send", () => json({ id: "sent-1", threadId: "t1" })],
    ["DELETE gmail:drafts/d1", () => new Response(null, { status: 204 })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  const sends = (c) => calls(c, REST).filter((x) => /\/(messages|drafts)\/send$/.test(x.url));

  const c = mk();
  const pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d1" });
  assert.deepEqual([pv.from, pv.from_verified, pv.to, pv.subject, pv.body_text, pv.sendable], ["Shop <info@shop.example>", true, "x@y.example", "Hi", "Body text", true]);
  assert.match(pv.digest, /^[0-9a-f]{32}$/);
  await assert.rejects(c.callTool("gmail_rest_send_draft", { draftId: "d1" }), { code: "INVALID_ARGUMENT" }, "a digest is required");
  await assert.rejects(c.callTool("gmail_rest_send_draft", { draftId: "d1", digest: "0".repeat(32) }), { code: "DRAFT_CHANGED" });
  assert.equal(sends(c).length, 0);
  const r = await c.callTool("gmail_rest_send_draft", { draftId: "d1", digest: pv.digest, to: ["evil@x.example"], body: "ignored" });
  assert.deepEqual([r.sent, r.message_id, r.thread_id, r.from, r.draft_deleted], [true, "sent-1", "t1", "info@shop.example", true]);
  const posted = JSON.parse(sends(c)[0].body);
  assert.deepEqual(posted, { raw: current, threadId: "t1" }, "exactly the checked bytes are sent; extra arguments are ignored");
  assert.ok(calls(c, REST).some((x) => x.method === "DELETE" && x.url.endsWith("/drafts/d1")));

  // Changed after the preview: nothing is sent.
  current = mime(["From: Shop <info@shop.example>", "To: x@y.example", "Subject: Changed after approval"]);
  const c2 = mk();
  await assert.rejects(c2.callTool("gmail_rest_send_draft", { draftId: "d1", digest: pv.digest }), { code: "DRAFT_CHANGED" });
  assert.equal(sends(c2).length, 0);

  // Unverified From.
  for (const bad of ["sales@shop.example", "stranger@other.example"]) {
    current = mime([`From: ${bad}`, "To: x@y.example", "Subject: Hi"]);
    const b = mk();
    const p2 = await b.callTool("gmail_rest_preview_draft", { draftId: "d1" });
    assert.equal(p2.from_verified, false);
    await assert.rejects(b.callTool("gmail_rest_send_draft", { draftId: "d1", digest: p2.digest }), { code: "IDENTITY_NOT_VERIFIED" });
    assert.equal(sends(b).length, 0, `${bad}: nothing sent`);
  }
});

test("send: what the preview cannot show fully is not sendable (repeated address headers, overlong body); text vs HTML differences are flagged", async () => {
  let current;
  const mk = () => ctxFor([tokenOk, rest([
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: current } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:messages/send", () => json({ id: "x" })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  const raw = (s) => Buffer.from(s.join("\r\n")).toString("base64url");

  current = raw(["From: info@shop.example", "To: a@b.example", "To: hidden@evil.example", "Subject: Hi", "Content-Type: text/plain", "", "x"]);
  let c = mk();
  let pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d1" });
  assert.equal(pv.sendable, false);
  assert.equal(pv.to, "a@b.example, hidden@evil.example", "every value of a repeated header is shown");
  await assert.rejects(c.callTool("gmail_rest_send_draft", { draftId: "d1", digest: pv.digest }), { code: "MULTIPLE_HEADERS" });

  current = raw(["From: info@shop.example", "To: a@b.example", "Subject: Hi", "Content-Type: text/plain", "", "y".repeat(20_001)]);
  c = mk();
  pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d1" });
  assert.equal(pv.sendable, false);
  await assert.rejects(c.callTool("gmail_rest_send_draft", { draftId: "d1", digest: pv.digest }), { code: "PREVIEW_INCOMPLETE" });

  current = raw(["From: info@shop.example", "To: a@b.example", "Reply-To: other@evil.example", "Subject: Hi", 'Content-Type: multipart/alternative; boundary="b"', "", "--b", "Content-Type: text/plain", "", "Pay invoice 1", "--b", "Content-Type: text/html", "", "<p>Pay to account <b>EVIL</b></p>", "--b--", ""]);
  c = mk();
  pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d1" });
  assert.deepEqual([pv.sendable, pv.text_and_html_differ, pv.reply_to, pv.body_html_as_text], [true, true, "other@evil.example", "Pay to account EVIL"]);
  assert.equal(calls(c, REST).filter((x) => x.url.endsWith("/messages/send")).length, 0);
});

test("reply draft: in the thread with In-Reply-To / References, from the alias the mail was sent to; header injection is flattened", async () => {
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:messages/m1", () => json({ id: "m1", threadId: "t9", payload: { headers: [
      { name: "From", value: "Customer <cust@buyer.example>" }, { name: "To", value: "info@shop.example" }, { name: "Cc", value: "boss@buyer.example, me@mail.example" },
      { name: "Subject", value: "=?UTF-8?B?" + Buffer.from("Order\r\nBcc: spy@evil.example").toString("base64") + "?=" },
      { name: "Message-ID", value: "<abc@buyer.example>" }, { name: "References", value: "<root@buyer.example>" },
      { name: "X-Forwarded-For", value: "info@shop.example me@mail.example" },
    ] } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => json({ id: "dr1", message: { id: "mm", threadId: body.message.threadId }, _raw: body.message.raw })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  const r = await c.callTool("gmail_rest_create_reply_draft", { messageId: "m1", body: "Thanks!", replyAll: true });
  assert.equal(r.from, "info@shop.example");
  assert.deepEqual(r.to, ["cust@buyer.example"]);
  assert.deepEqual(r.cc, ["boss@buyer.example"], "the account's own addresses are never added");
  const post = JSON.parse(calls(c, REST).find((x) => /\/drafts$/.test(x.url)).body);
  assert.equal(post.message.threadId, "t9");
  const raw = decodeRaw(post.message.raw);
  assert.match(raw, /^From: Shop <info@shop\.example>\r\n/m);
  assert.match(raw, /^In-Reply-To: <abc@buyer\.example>\r\n/m);
  assert.match(raw, /^References: <root@buyer\.example> <abc@buyer\.example>\r\n/m);
  assert.doesNotMatch(raw, /^Bcc:/m, "a line break hidden in the original subject cannot add a header");
  assert.equal(parseMime(Buffer.from(raw)).headers.subject.length, 1);

  await assert.rejects(c.callTool("gmail_rest_create_reply_draft", { messageId: "m1", body: "x", from: "sales@shop.example" }), { code: "IDENTITY_NOT_VERIFIED" });
});

test("forward draft: carries the original attachments and text; from picks the verified alias", async () => {
  const original = [
    "From: A <a@x.example>", "To: info@shop.example", "Subject: Invoice", "Date: Mon, 1 Jan 2026 10:00:00 +0000",
    'Content-Type: multipart/mixed; boundary="b1"', "", "--b1", "Content-Type: text/plain; charset=UTF-8", "", "See attached.",
    "--b1", 'Content-Type: application/pdf; name="inv.pdf"', 'Content-Disposition: attachment; filename="inv.pdf"', "Content-Transfer-Encoding: base64", "", Buffer.from("%PDF-1.4 fake").toString("base64"), "--b1--", "",
  ].join("\r\n");
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:messages/m2", () => json({ id: "m2", threadId: "t2", raw: Buffer.from(original).toString("base64url") })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => json({ id: "dr2", message: { id: "m3", threadId: body.message.threadId } })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  const r = await c.callTool("gmail_rest_create_forward_draft", { messageId: "m2", to: ["acct@firm.example"], body: "FYI" });
  assert.deepEqual([r.from, r.subject, r.attachments], ["info@shop.example", "Fwd: Invoice", ["inv.pdf"]]);
  const sent = parseMime(Buffer.from(decodeRaw(JSON.parse(calls(c, REST).find((x) => /\/drafts$/.test(x.url)).body).message.raw)));
  const atts = attachmentsOf(sent);
  assert.equal(atts.length, 1);
  assert.equal(atts[0].bytes.toString(), "%PDF-1.4 fake");
  assert.match(bodyText(sent), /FYI[\s\S]*---------- Forwarded message ---------[\s\S]*Subject: Invoice[\s\S]*See attached\./);
});

test("Drive REST: trash and move shapes; share only to a person or group with a fixed role set; owner access cannot be removed", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, rest([
    ["PATCH drive:files/f1", ({ u, body }) => { seen.push({ q: Object.fromEntries(u.searchParams), body }); return json({ id: "f1", name: "Doc", trashed: body.trashed, parents: ["new"] }); }],
    ["GET drive:files/f1", () => json({ id: "f1", name: "Doc", parents: ["old1", "old2"] })],
    ["POST drive:files/f1/permissions", ({ u, body }) => { seen.push({ q: Object.fromEntries(u.searchParams), body }); return json({ id: "p9", role: body.role, type: body.type, emailAddress: body.emailAddress }); }],
    ["GET drive:files/f1/permissions", () => json({ permissions: [{ id: "own", role: "owner", emailAddress: "me@mail.example" }, { id: "p9", role: "reader", emailAddress: "pal@x.example" }] })],
    ["DELETE drive:files/f1/permissions/p9", () => new Response(null, { status: 204 })],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  assert.equal((await c.callTool("drive_rest_trash_file", { fileId: "f1" })).trashed, true);
  assert.deepEqual(seen.pop().body, { trashed: true });
  await c.callTool("drive_rest_move_file", { fileId: "f1", folderId: "new" });
  assert.deepEqual([seen.at(-1).q.addParents, seen.at(-1).q.removeParents], ["new", "old1,old2"]);
  const s = await c.callTool("drive_rest_share_file", { fileId: "f1", email: "Pal@X.example", role: "reader", notify: false });
  assert.deepEqual([s.permission_id, s.notified], ["p9", false]);
  assert.deepEqual(seen.at(-1).body, { type: "user", role: "reader", emailAddress: "pal@x.example" });
  assert.equal(seen.at(-1).q.sendNotificationEmail, "false");
  for (const bad of [{ role: "owner" }, { role: "reader", email: "not-an-email" }]) await assert.rejects(c.callTool("drive_rest_share_file", { fileId: "f1", email: "pal@x.example", ...bad }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("drive_rest_unshare_file", { fileId: "f1", email: "me@mail.example" }), { code: "INVALID_ARGUMENT" });
  assert.equal((await c.callTool("drive_rest_unshare_file", { fileId: "f1", email: "pal@x.example" })).removed.permission_id, "p9");
});

// ------------------------------------------------------------------------------------------------ guards

test("guest guard (GOOGLE_REFUSE_GUEST_EVENTS=1): other attendees are refused before Google is called; off by default", async () => {
  const mk = (env, event) => ctxFor([tokenOk, mcpRoute((p) => (p.name === "get_event" ? (event instanceof Error ? { isError: true, content: [{ type: "text", text: "boom" }] } : ok(event)) : ok({ id: "e1" })))], { seed: SEED, extraEnv: env });
  const ON = { GOOGLE_REFUSE_GUEST_EVENTS: "1" };
  const solo = { id: "e1", attendees: [{ email: "me@mail.example", self: true }], organizer: { email: "me@mail.example", self: true } };
  const group = { id: "e1", attendees: [{ email: "me@mail.example", self: true }, { email: "pal@x.example" }], organizer: { email: "me@mail.example", self: true } };

  const c1 = mk(ON, solo);
  await assert.rejects(c1.callTool("calendar_create_event", { summary: "x", startTime: "a", endTime: "b", attendees: [{ email: "pal@x.example" }] }), (e) => e.code === "GUESTS_NEED_APPROVAL");
  await assert.rejects(c1.callTool("calendar_update_event", { eventId: "e1", addedAttendeeEmails: ["pal@x.example"] }), { code: "GUESTS_NEED_APPROVAL" });
  assert.equal(calls(c1, MCP).length, 0, "refused before any Google call");
  await c1.callTool("calendar_create_event", { summary: "x", startTime: "a", endTime: "b", attendees: [{ email: "ME@mail.example" }] });
  await c1.callTool("calendar_delete_event", { eventId: "e1" });

  const c2 = mk(ON, group);
  for (const n of ["calendar_update_event", "calendar_delete_event", "calendar_respond_to_event"]) await assert.rejects(c2.callTool(n, { eventId: "e1", responseStatus: "accepted" }), { code: "GUESTS_NEED_APPROVAL" }, n);
  assert.ok(calls(c2, MCP).every((x) => JSON.parse(x.body).params.name === "get_event"), "only the lookup reached Google");

  await assert.rejects(mk(ON, new Error("x")).callTool("calendar_delete_event", { eventId: "e1" }), { code: "TOOL_ERROR" }, "a failed lookup refuses (fails closed), with its own code");
  await mk({}, group).callTool("calendar_delete_event", { eventId: "e1" });
});

test("write limit (GOOGLE_WRITE_LIMIT_PER_HOUR): trash / spam / delete / move past N per rolling hour is refused; other tools are not counted", async () => {
  let t = Date.parse("2026-11-26T10:00:00Z");
  const c = ctxFor([tokenOk, mcpRoute(() => ok({ ok: 1 }))], { seed: SEED, extraEnv: { GOOGLE_WRITE_LIMIT_PER_HOUR: "2" }, deps: { now: () => t } });
  await c.callTool("gmail_trash_message", { messageId: "1" });
  await c.callTool("gmail_list_labels", {});
  await c.callTool("gmail_mark_thread_spam", { threadId: "2" });
  await assert.rejects(c.callTool("calendar_delete_event", { eventId: "3" }), (e) => e.code === "WRITE_LIMIT_REACHED" && /minute/.test(e.hint));
  assert.equal(calls(c, MCP).filter((x) => JSON.parse(x.body).params.name === "delete_event").length, 0);
  t += 3_600_000;
  await c.callTool("calendar_delete_event", { eventId: "3" });
  const free = ctxFor([tokenOk, mcpRoute(() => ok({}))], { seed: SEED });
  for (let i = 0; i < 5; i++) await free.callTool("gmail_trash_message", { messageId: String(i) });
});

test("refusals are text-only error results (an image in an error result breaks some hosts)", async () => {
  const c = ctxFor([tokenOk], { seed: SEED, extraEnv: { GOOGLE_REFUSE_GUEST_EVENTS: "1" } });
  const handle = createHandler({ info: { name: "g", version: "t" }, listTools: c.listTools, callTool: c.callTool });
  const r = await handle({ method: "tools/call", params: { name: "calendar_create_event", arguments: { summary: "x", startTime: "a", endTime: "b", attendees: ["pal@x.example"] } } });
  assert.equal(r.isError, true);
  assert.deepEqual(r.content.map((b) => b.type), ["text"]);
  assert.equal(JSON.parse(r.content[0].text).error.code, "GUESTS_NEED_APPROVAL");
});

// ------------------------------------------------------------------------------------------------ files

const RAW_WITH_FILES = [
  "From: a@x.example", "To: me@mail.example", "Subject: files", 'Content-Type: multipart/mixed; boundary="outer"', "",
  "--outer", 'Content-Type: multipart/alternative; boundary="inner"', "", "--inner", "Content-Type: text/plain", "", "hello", "--inner", "Content-Type: text/html", "", "<p>hello</p>", "--inner--",
  "--outer", "Content-Type: application/pdf", "Content-Disposition: attachment; filename*=UTF-8''%D9%81%D8%A7%D8%AA%D9%88%D8%B1%D8%A9.pdf", "Content-Transfer-Encoding: base64", "", Buffer.from("PDFBYTES").toString("base64"),
  "--outer", 'Content-Type: image/png; name="../../evil.png"', "Content-Transfer-Encoding: base64", "", Buffer.from([0, 1, 2, 255]).toString("base64"),
  "--outer--", "",
].join("\r\n");

test("gmail_get_attachment: lists, saves by index or filename into the download folder only, never returns bytes", async () => {
  const dir = dl();
  const c = ctxFor([tokenOk, mcpRoute(() => ok({ id: "m1", raw: Buffer.from(RAW_WITH_FILES).toString("base64url") }))], { seed: SEED, extraEnv: { GOOGLE_DOWNLOAD_DIR: dir } });
  const list = await c.callTool("gmail_get_attachment", { messageId: "m1" });
  assert.deepEqual(list.attachments.map((a) => [a.index, a.filename, a.mimeType, a.size]), [[1, "فاتورة.pdf", "application/pdf", 8], [2, "../../evil.png", "image/png", 4]]);
  const a = await c.callTool("gmail_get_attachment", { messageId: "m1", attachment: "فاتورة.pdf" });
  assert.equal(readFileSync(a.saved.path, "utf8"), "PDFBYTES");
  const b = await c.callTool("gmail_get_attachment", { messageId: "m1", attachment: "2" });
  assert.equal(dirname(b.saved.path), realpathSync(dir), "a path in the filename cannot leave the folder");
  assert.deepEqual([...readFileSync(b.saved.path)], [0, 1, 2, 255]);
  const again = await c.callTool("gmail_get_attachment", { messageId: "m1", attachment: "1" });
  assert.notEqual(again.saved.path, a.saved.path, "never overwrites");
  assert.equal(readdirSync(dir).length, 3);
  assert.doesNotMatch(JSON.stringify([list, a, b]), /UERGQllURVM|PDFBYTES/, "no file bytes in results");
  await assert.rejects(c.callTool("gmail_get_attachment", { messageId: "m1", attachment: "9" }), { code: "NOT_FOUND" });

  const noDir = ctxFor([tokenOk, mcpRoute(() => ok({ raw: Buffer.from(RAW_WITH_FILES).toString("base64url") }))], { seed: SEED });
  await assert.rejects(noDir.callTool("gmail_get_attachment", { messageId: "m1", attachment: "1" }), { code: "DOWNLOAD_NOT_CONFIGURED" });
  const small = ctxFor([tokenOk, mcpRoute(() => ok({ raw: Buffer.from(RAW_WITH_FILES).toString("base64url") }))], { seed: SEED, extraEnv: { GOOGLE_DOWNLOAD_DIR: dl(), GOOGLE_MAX_SAVE_MB: "0.000001" } });
  await assert.rejects(small.callTool("gmail_get_attachment", { messageId: "m1", attachment: "1" }), { code: "TOO_LARGE" });
});

test("drive_save_file: decodes Google's download and saves it with an extension; other people's files are CONFIRMATION_UNSUPPORTED", async () => {
  const dir = dl();
  const c = ctxFor([tokenOk, mcpRoute((p) => (p.arguments.fileId === "ext"
    ? { isError: true, content: [{ type: "text", text: "Action could not be completed. This action requires user confirmation, which this client does not support." }] }
    : ok({ id: p.arguments.fileId, title: "Notes", mimeType: "text/plain", content: Buffer.from("hello drive").toString("base64") })))], { seed: SEED, extraEnv: { GOOGLE_DOWNLOAD_DIR: dir } });
  const r = await c.callTool("drive_save_file", { fileId: "own" });
  assert.equal(r.saved.filename, "Notes.txt");
  assert.equal(readFileSync(r.saved.path, "utf8"), "hello drive");
  assert.doesNotMatch(JSON.stringify(r), /aGVsbG8gZHJpdmU/);
  await assert.rejects(c.callTool("drive_save_file", { fileId: "ext" }), { code: "CONFIRMATION_UNSUPPORTED" });
  assert.ok(!existsSync(join(dir, "ext")));
});

// ------------------------------------------------------------------------------------------------ MIME + schema

test("MIME building: line breaks in header values are refused, non-ASCII is encoded, and the result parses back", () => {
  assert.throws(() => buildMessage({ from: "me@mail.example", to: ["a@b.example"], subject: "x\r\nBcc: spy@evil.example", text: "t" }), { code: "INVALID_ARGUMENT" });
  assert.throws(() => buildMessage({ from: "me@mail.example", to: ["a@b.example\r\nBcc: spy@evil.example"], text: "t" }), { code: "INVALID_ARGUMENT" });
  assert.throws(() => buildMessage({ from: "not an address", to: ["a@b.example"], text: "t" }), { code: "INVALID_ARGUMENT" });
  assert.match(encodeWords("مرحبا"), /^=\?UTF-8\?B\?/);
  const raw = buildMessage({ from: "me@mail.example", fromName: "أحمد", to: ["a@b.example"], subject: "طلب رقم 42", text: "نص", html: "<b>نص</b>", attachments: [{ filename: "تقرير.pdf", mimeType: "application/pdf", bytes: Buffer.from("X") }] });
  const back = parseMime(Buffer.from(raw));
  assert.equal(bodyText(back), "نص");
  assert.deepEqual(attachmentsOf(back).map((a) => [a.filename, a.bytes.toString()]), [["تقرير.pdf", "X"]]);
});

test("schema-check names the REST tools a new Google tool may replace", () => {
  assert.deepEqual(restTwins("gmail", ["send_message"]), [{ google_tool: "gmail_send_message", may_replace: "gmail_rest_send_draft" }]);
  assert.ok(restTwins("drive", ["share_file"]).some((x) => x.may_replace === "drive_rest_share_file"));
  assert.deepEqual(restTwins("calendar", ["send_invite"]), []);
});

// ------------------------------------------------------------------------------------------------ 0.6.3 fixes from the live test

test("update_draft: only the fields given change; recipients, subject, From, reply headers, thread and attachments are kept", async () => {
  const original = [
    "From: Shop <info@shop.example>", "To: Jobs <jobs@board.example>", "Cc: cc1@x.example", "Subject: Re: Purchase Specialist",
    "In-Reply-To: <orig@board.example>", "References: <root@board.example> <orig@board.example>",
    'Content-Type: multipart/mixed; boundary="m"', "", "--m", 'Content-Type: multipart/alternative; boundary="a"', "",
    "--a", "Content-Type: text/plain", "", "old text", "--a", "Content-Type: text/html", "", "<p>old html</p>", "--a--",
    "--m", 'Content-Type: application/pdf; name="cv.pdf"', 'Content-Disposition: attachment; filename="cv.pdf"', "Content-Transfer-Encoding: base64", "", Buffer.from("CV").toString("base64"), "--m--", "",
  ].join("\r\n");
  let putBody = null;
  const mk = () => ctxFor([tokenOk, rest([
    ["GET gmail:drafts/r1", () => json({ id: "r1", message: { id: "m1", threadId: "t7", raw: Buffer.from(original).toString("base64url") } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["PUT gmail:drafts/r1", ({ body }) => { putBody = body; return json({ id: "r1", message: { id: "m2", threadId: body.message.threadId } }); }],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });

  const r = await mk().callTool("gmail_rest_update_draft", { draftId: "r1", body: "new text" });
  assert.deepEqual(r.changed, ["body"]);
  assert.equal(putBody.message.threadId, "t7");
  const m = parseMime(Buffer.from(Buffer.from(putBody.message.raw, "base64url").toString("utf8")));
  const hv = (n) => m.headers[n.toLowerCase()]?.[0];
  assert.deepEqual([hv("From"), hv("To"), hv("Cc"), hv("Subject"), hv("In-Reply-To"), hv("References")],
    ["Shop <info@shop.example>", "jobs@board.example", "cc1@x.example", "Re: Purchase Specialist", "<orig@board.example>", "<root@board.example> <orig@board.example>"]);
  assert.equal(bodyText(m), "new text");
  assert.equal(bodyViews(m).htmlParts, 0, "a new body replaces the HTML version too");
  assert.deepEqual(attachmentsOf(m).map((a) => [a.filename, a.bytes.toString()]), [["cv.pdf", "CV"]]);

  await mk().callTool("gmail_rest_update_draft", { draftId: "r1", subject: "Changed", cc: [] });
  const m2 = parseMime(Buffer.from(Buffer.from(putBody.message.raw, "base64url").toString("utf8")));
  assert.deepEqual([m2.headers.subject?.[0], m2.headers.cc, m2.headers.to?.[0]], ["Changed", undefined, "jobs@board.example"]);
  assert.deepEqual([bodyViews(m2).text, bodyViews(m2).html], ["old text", "old html"], "no body given: both old versions are kept");
  await assert.rejects(mk().callTool("gmail_rest_update_draft", { draftId: "r1", from: "sales@shop.example" }), { code: "IDENTITY_NOT_VERIFIED" });
});

test("grant for a write tool: one tool, a named target, a typed yes; then Google's form is shown and the answer passed back", async () => {
  const FORMW = { resultType: "input_required", requestState: "s", inputRequests: { approval_choice: { method: "elicitation/create", params: { mode: "form", message: "Allow deleting this event?", requestedSchema: { type: "object", properties: { approval_choice: { type: "string", enum: ["ALLOW_ONCE", "ALLOW_TOOL_ALWAYS", "DENY_ONCE"], enumNames: ["Allow once", "Always allow this tool", "Don't allow"] } } } } } } };
  const c = ctxFor([tokenOk, mcpRoute((p) => (p.inputResponses ? ok({ deleted: true }) : FORMW))], { seed: SEED });
  const availableWrites = c.tools.filter((t) => WRITE_GRANT_PLAN[t.name]).map((t) => t.name);
  const base = { ctx: c.ctx, callTool: c.callTool, available: [], availableWrites, print: () => {} };
  await assert.rejects(runGrant({ ...base, requested: ["calendar_delete_event"], prompt: async () => "yes" }), { code: "INVALID_ARGUMENT" }, "needs --target");
  await assert.rejects(runGrant({ ...base, requested: ["calendar_delete_event", "gmail_list_labels"], target: "e1", prompt: async () => "yes" }), { code: "INVALID_ARGUMENT" }, "one write tool alone");
  const no = await runGrant({ ...base, requested: ["calendar_delete_event"], target: "e1", prompt: async () => "no" });
  assert.equal(no.steps[0].result, "skipped");
  assert.equal(mcpCalls(c).length, 0, "nothing runs without a typed yes");

  const answers = ["yes", "2"];
  const printed = [];
  const r = await runGrant({ ...base, requested: ["calendar_delete_event"], target: "evt-9", calendarId: "primary", prompt: async () => answers.shift(), print: (s) => printed.push(s) });
  assert.deepEqual([r.steps[0].result, r.steps[0].asked], ["ok", true]);
  const sent = mcpCalls(c).map((x) => x.json.params);
  assert.deepEqual(sent[0].arguments, { eventId: "evt-9", notificationLevel: "NONE", calendarId: "primary" });
  assert.deepEqual(sent[1].inputResponses, { approval_choice: { action: "accept", content: { approval_choice: "ALLOW_TOOL_ALWAYS" } } });
  assert.match(printed.join("\n"), /This RUNS calendar_delete_event for real: it DELETES this calendar event/);
});

test("CONFIRMATION_NEEDED hints: a write tool grant can run points to --target; one it cannot run says so", async () => {
  const FORM1 = { resultType: "input_required", requestState: "s", inputRequests: { k: { method: "elicitation/create", params: { mode: "form", message: "?", requestedSchema: { type: "object", properties: {} } } } } };
  const c = ctxFor([tokenOk, mcpRoute(() => FORM1)], { seed: SEED });
  await assert.rejects(c.callTool("calendar_delete_event", { eventId: "e" }), (e) => e.code === "CONFIRMATION_NEEDED" && /grant calendar_delete_event --target <id>/.test(e.hint) && /really performs/.test(e.hint));
  await assert.rejects(c.callTool("calendar_create_event", { summary: "x", startTime: "a", endTime: "b" }), (e) => e.code === "CONFIRMATION_NEEDED" && /grant cannot ask/.test(e.hint));
  await assert.rejects(c.callTool("gmail_get_thread", { threadId: "t" }), (e) => /grant gmail_get_thread \./.test(e.hint));
});
