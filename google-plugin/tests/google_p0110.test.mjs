// 0.11.0 tests: Gmail REST read twins (search threads / messages, get message / thread, labels, drafts, attachment),
// the RATE_LIMITED hint naming the twin, and gmail_message_identity falling back to REST. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { TOKEN, FULL_GRANT, ctxFor, json } from "./_helpers.mjs";
import { CLASSES } from "../server/tools/bridge.mjs";
import { METADATA_MAX } from "../server/tools/gmail_read.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const MCP = /^POST https:\/\/(gmail|calendar|drive)mcp\.googleapis\.com\/mcp\/v1$/;
const GMAIL = /^GET https:\/\/gmail\.googleapis\.com\/gmail\/v1\/users\/me\//;
const SEED = { account: { email: "me@mail.example" }, scopes_granted: FULL_GRANT };
const ON = { GOOGLE_REST_FALLBACK: "1" };
const NEW = ["gmail_rest_search_threads", "gmail_rest_search_messages", "gmail_rest_get_message", "gmail_rest_get_thread", "gmail_rest_list_labels", "gmail_rest_list_drafts", "gmail_rest_get_draft", "gmail_rest_get_attachment"];
const b64 = (s, enc = "utf8") => Buffer.from(s, enc).toString("base64url");
const dl = () => mkdtempSync(join(tmpdir(), "gp-dl-"));

/** Gmail REST fake: [path-regex, handler(url)]; records path and query (repeated keys as arrays). */
function gmail(routes, seen = []) {
  return [GMAIL, async ({ url }) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/gmail\/v1\/users\/me\//, "");
    const query = {};
    for (const [k, v] of u.searchParams) query[k] = k in query ? [].concat(query[k], v) : v;
    seen.push({ path, query });
    for (const [re, h] of routes) if (new RegExp(`^${re}$`).test(path)) return h(u);
    return json({ error: { code: 404, message: `no fake for ${path}` } }, 404);
  }];
}
const H = (o) => Object.entries(o).map(([name, value]) => ({ name, value }));
const META = (id, extra = {}) => ({ id, threadId: `t-${id}`, labelIds: ["INBOX"], snippet: `snip ${id}`, internalDate: "1764201600000",
  payload: { headers: H({ From: `Sender ${id} <s${id}@ext.example>`, To: 'me@mail.example, "Doe, Jane" <jane@x.example>', Subject: `Subject ${id}`, Date: "Thu, 27 Nov 2026 08:00:00 +0200" }) }, ...extra });
const FULL = {
  id: "m1", threadId: "t1", labelIds: ["INBOX", "UNREAD"], snippet: "hello",
  payload: { mimeType: "multipart/mixed", headers: H({ From: "A <a@ext.example>", To: "me@mail.example", Cc: "c@x.example", Subject: "Invoice", Date: "Thu, 27 Nov 2026 08:00:00 +0200" }), parts: [
    { partId: "0", mimeType: "multipart/alternative", parts: [
      { partId: "0.0", mimeType: "text/plain", headers: H({ "Content-Type": "text/plain; charset=ISO-8859-1" }), body: { size: 5, data: b64("caf\xe9 ok", "latin1") } },
      { partId: "0.1", mimeType: "text/html", headers: H({ "Content-Type": "text/html; charset=UTF-8" }), body: { size: 9, data: b64("<b>café</b>") } },
    ] },
    { partId: "1", mimeType: "application/pdf", filename: "inv.pdf", headers: H({ "Content-Disposition": 'attachment; filename="inv.pdf"' }), body: { size: 4, attachmentId: "att-1" } },
    { partId: "2", mimeType: "image/png", filename: "", headers: H({ "Content-Disposition": "inline", "Content-ID": "<logo1>" }), body: { size: 3, attachmentId: "att-2" } },
  ] },
};

test("the eight Gmail REST read tools are read class, exist only with the REST switch, and in read-only mode", () => {
  for (const n of NEW) {
    assert.ok(CLASSES.read.includes(n) && CLASSES.rest_tools.includes(n) && CLASSES.plugin_tools.includes(n), n);
    assert.ok(!ctxFor([], { seed: SEED }).listTools().some((t) => t.name === n), n);
    assert.ok(ctxFor([], { seed: SEED, extraEnv: { ...ON, GOOGLE_READONLY: "1" } }).listTools().some((t) => t.name === n), n);
  }
  const d = ctxFor([], { seed: SEED, extraEnv: ON }).listTools().find((t) => t.name === "gmail_rest_get_message").description;
  assert.match(d, /does not go through Google's confirmation/);
});

test("gmail_rest_search_threads: q, labelIds, capped maxResults, pageToken, includeSpamTrash; metadata for the first 25 only", async () => {
  const seen = [];
  const ids = Array.from({ length: 30 }, (_, i) => `x${i}`);
  const c = ctxFor([tokenOk, gmail([
    ["threads", () => json({ threads: ids.map((id) => ({ id, snippet: `s ${id}` })), nextPageToken: "p2", resultSizeEstimate: 99 })],
    ["threads/[^/]+", (u) => { const id = u.pathname.split("/").pop(); return json({ id, messages: [META(`${id}a`), META(`${id}b`, { labelIds: ["INBOX", "UNREAD"] })] }); }],
  ], seen)], { seed: SEED, extraEnv: ON });
  const r = await c.callTool("gmail_rest_search_threads", { q: "older_than:1y", labelIds: ["INBOX", "Label_7"], maxResults: 900, pageToken: "p1", includeSpamTrash: true, metadata: true });
  const q = seen[0].query;
  assert.equal(q.q, "older_than:1y");
  assert.deepEqual(q.labelIds, ["INBOX", "Label_7"]);
  assert.equal(q.maxResults, "500");
  assert.equal(q.pageToken, "p1");
  assert.equal(q.includeSpamTrash, "true");
  assert.equal(r.untrusted, true);
  assert.equal(r.nextPageToken, "p2");
  assert.equal(r.threads.length, 30);
  assert.equal(seen.filter((s) => s.path.startsWith("threads/")).length, METADATA_MAX);
  assert.equal(r.metadata_limited, METADATA_MAX);
  const t0 = r.threads[0];
  assert.equal(t0.subject, "Subject x0a");
  assert.equal(t0.sender, "Sender x0a <sx0a@ext.example>");
  assert.deepEqual(t0.toRecipients, ["me@mail.example", '"Doe, Jane" <jane@x.example>']);
  assert.equal(t0.messageCount, 2);
  assert.deepEqual(t0.labelIds.sort(), ["INBOX", "UNREAD"]);
  assert.equal(r.threads[29].subject, undefined);
  const metaCall = seen.find((s) => s.path.startsWith("threads/")).query;
  assert.equal(metaCall.format, "metadata");
  assert.ok(metaCall.metadataHeaders.includes("Subject") && metaCall.metadataHeaders.includes("From"));

  await c.callTool("gmail_rest_search_threads", {});
  assert.equal(seen.at(-1).query.maxResults, "20");
  assert.equal(seen.at(-1).query.includeSpamTrash, undefined);
});

test("gmail_rest_search_messages: message ids for the batch tools; metadata=true adds headers", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, gmail([
    ["messages", () => json({ messages: [{ id: "a", threadId: "ta" }, { id: "b", threadId: "tb" }] })],
    ["messages/[^/]+", (u) => json(META(u.pathname.split("/").pop()))],
  ], seen)], { seed: SEED, extraEnv: ON });
  const plain = await c.callTool("gmail_rest_search_messages", { q: "from:x" });
  assert.deepEqual(plain.messages, [{ id: "a", threadId: "ta" }, { id: "b", threadId: "tb" }]);
  assert.equal(seen.length, 1);
  const meta = await c.callTool("gmail_rest_search_messages", { q: "from:x", metadata: true });
  assert.equal(meta.messages[1].subject, "Subject b");
  assert.equal(meta.messages[1].id, "b");
});

test("gmail_rest_get_message: headers, the text part decoded with its charset, attachments listed (no ids, no bytes); metadata format has no body", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, gmail([["messages/m1", (u) => json(u.searchParams.get("format") === "full" ? FULL : META("m1"))]], seen)], { seed: SEED, extraEnv: ON });
  const r = await c.callTool("gmail_rest_get_message", { messageId: "m1" });
  assert.equal(seen[0].query.format, "full");
  const m = r.message;
  assert.equal(r.untrusted, true);
  assert.equal(m.subject, "Invoice");
  assert.equal(m.sender, "A <a@ext.example>");
  assert.deepEqual(m.ccRecipients, ["c@x.example"]);
  assert.equal(m.plaintextBody, "café ok");
  assert.equal(m.body_source, "text");
  assert.deepEqual(m.attachments, [
    { index: 1, filename: "inv.pdf", mimeType: "application/pdf", size: 4, inline: false },
    { index: 2, filename: "part-2", mimeType: "image/png", size: 3, inline: true, contentId: "logo1" },
  ]);
  assert.doesNotMatch(JSON.stringify(r), /att-1/);
  const md = await c.callTool("gmail_rest_get_message", { messageId: "m1", format: "minimal" });
  assert.equal(seen[1].query.format, "metadata");
  assert.equal(md.message.plaintextBody, undefined);
  await assert.rejects(c.callTool("gmail_rest_get_message", { messageId: "m1", format: "raw" }), { code: "INVALID_ARGUMENT" });
});

test("gmail_rest_get_thread: messages in order; HTML-only bodies become text; long bodies are cut (truncated: true)", async () => {
  const html = { id: "h1", threadId: "t9", payload: { mimeType: "text/html", headers: H({ Subject: "Promo", "Content-Type": "text/html; charset=utf-8" }), body: { data: b64(`<p>Hi</p><script>evil()</script>${"x".repeat(300)}`) } } };
  const c = ctxFor([tokenOk, gmail([["threads/t9", () => json({ id: "t9", messages: [META("e1"), html] })]])], { seed: SEED, extraEnv: { ...ON, GOOGLE_MAX_STRING_CHARS: "100" } });
  const r = await c.callTool("gmail_rest_get_thread", { threadId: "t9" });
  assert.equal(r.thread.messages.length, 2);
  const m = r.thread.messages[1];
  assert.equal(m.body_source, "html");
  assert.match(m.plaintextBody, /^Hi\n?x/);
  assert.doesNotMatch(m.plaintextBody, /evil/);
  assert.equal(r.truncated, true);
  assert.equal(r.untrusted, true);
});

test("gmail_rest_list_labels (counts for the named labels only), gmail_rest_list_drafts and gmail_rest_get_draft", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, gmail([
    ["labels", () => json({ labels: [{ id: "INBOX", name: "INBOX", type: "system" }, { id: "Label_1", name: "Bills", type: "user" }] })],
    ["labels/INBOX", () => json({ id: "INBOX", messagesTotal: 10, messagesUnread: 3, threadsTotal: 8, threadsUnread: 2 })],
    ["drafts", () => json({ drafts: [{ id: "d1", message: { id: "dm1", threadId: "dt1" } }], nextPageToken: "n" })],
    ["drafts/d1", (u) => json({ id: "d1", message: u.searchParams.get("format") === "full" ? FULL : META("dm1") })],
  ], seen)], { seed: SEED, extraEnv: ON });
  const l = await c.callTool("gmail_rest_list_labels", {});
  assert.deepEqual(l.labels.map((x) => x.id), ["INBOX", "Label_1"]);
  assert.equal(l.labels[0].messagesTotal, undefined);
  const lc = await c.callTool("gmail_rest_list_labels", { counts: true, labelIds: ["INBOX"] });
  assert.deepEqual(lc.labels, [{ id: "INBOX", name: "INBOX", type: "system", messagesTotal: 10, messagesUnread: 3, threadsTotal: 8, threadsUnread: 2 }]);
  assert.ok(!seen.some((s) => s.path === "labels/Label_1"));
  const d = await c.callTool("gmail_rest_list_drafts", { q: "to:x", metadata: true });
  assert.deepEqual({ id: d.drafts[0].id, messageId: d.drafts[0].messageId, subject: d.drafts[0].subject }, { id: "d1", messageId: "dm1", subject: "Subject dm1" });
  assert.equal(d.nextPageToken, "n");
  await assert.rejects(c.callTool("gmail_rest_list_drafts", { labelIds: ["X"] }), { code: "INVALID_ARGUMENT" });
  const g = await c.callTool("gmail_rest_get_draft", { draftId: "d1" });
  assert.equal(g.draft.id, "d1");
  assert.equal(g.draft.message.plaintextBody, "café ok");
});

test("gmail_rest_get_attachment: lists, saves by index or name through attachments.get with the extension rule, TOO_LARGE before any download", async () => {
  const dir = dl(), seen = [];
  const c = ctxFor([tokenOk, gmail([
    ["messages/m1", () => json(FULL)],
    ["messages/m1/attachments/att-1", () => json({ size: 4, data: b64("%PDF") })],
    ["messages/m1/attachments/att-2", () => json({ size: 3, data: b64("PNG") })],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const list = await c.callTool("gmail_rest_get_attachment", { messageId: "m1" });
  assert.deepEqual(list.attachments.map((a) => a.filename), ["inv.pdf", "part-2"]);
  const a = await c.callTool("gmail_rest_get_attachment", { messageId: "m1", attachment: "inv.pdf" });
  assert.equal(readFileSync(a.saved.path, "utf8"), "%PDF");
  assert.equal(basename(a.saved.path), "inv.pdf");
  const b = await c.callTool("gmail_rest_get_attachment", { messageId: "m1", attachment: "2" });
  assert.equal(basename(b.saved.path), "part-2.png", "extension from the MIME type");
  assert.doesNotMatch(JSON.stringify([a, b]), /JVBER|UE5H/);
  await assert.rejects(c.callTool("gmail_rest_get_attachment", { messageId: "m1", attachment: "9" }), { code: "NOT_FOUND" });
  const small = ctxFor([tokenOk, gmail([["messages/m1", () => json(FULL)]], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir, GOOGLE_MAX_SAVE_MB: String(2 / 1048576) } });
  const before = seen.length;
  await assert.rejects(small.callTool("gmail_rest_get_attachment", { messageId: "m1", attachment: "1" }), { code: "TOO_LARGE" });
  assert.ok(!seen.slice(before).some((s) => s.path.includes("/attachments/")));
});

test("RATE_LIMITED from a Gmail MCP tool names its REST twin (or the REST switch); other modules keep the old hint", async () => {
  const limited = [MCP, () => json({ error: { code: 429, message: "quota" } }, 429)];
  const on = ctxFor([tokenOk, limited], { seed: SEED, extraEnv: ON });
  await assert.rejects(on.callTool("gmail_search_threads", {}), (e) => e.code === "RATE_LIMITED" && /Use gmail_rest_search_threads instead/.test(e.hint) && /separate/.test(e.hint));
  await assert.rejects(on.callTool("gmail_get_message", { messageId: "m" }), (e) => /gmail_rest_get_message/.test(e.hint));
  const off = ctxFor([tokenOk, limited], { seed: SEED });
  await assert.rejects(off.callTool("gmail_list_labels", {}), (e) => e.code === "RATE_LIMITED" && /GOOGLE_REST_FALLBACK=1/.test(e.hint) && /gmail_rest_list_labels/.test(e.hint));
  await assert.rejects(off.callTool("calendar_list_events", {}), (e) => e.code === "RATE_LIMITED" && /Wait a minute/.test(e.hint));
});

test("gmail_message_identity: a RATE_LIMITED MCP call falls back to REST headers (via: rest) when switched on; stays RATE_LIMITED otherwise", async () => {
  const IDS = JSON.stringify({ identities: [{ id: "shop", address: "info@shop.example" }, { id: "me", address: "me@mail.example", default: true }] });
  const limited = [MCP, () => json({ error: { code: 429, message: "quota" } }, 429)];
  const seen = [];
  const rest = gmail([["messages/m7", () => json({ id: "m7", threadId: "t7", payload: { headers: H({ From: "x@ext.example", To: "me@mail.example", "X-Forwarded-For": "info@shop.example me@mail.example", Subject: "Order" }) } })]], seen);
  const c = ctxFor([tokenOk, limited, rest], { seed: SEED, extraEnv: { ...ON, GOOGLE_IDENTITIES: IDS } });
  const r = await c.callTool("gmail_message_identity", { messageId: "m7" });
  assert.equal(r.via, "rest");
  assert.equal(r.identity.id, "shop");
  assert.equal(r.matched_by, "x-forwarded-for");
  assert.equal(r.thread_id, "t7");
  assert.equal(seen[0].query.format, "metadata");
  assert.equal(r.headers.subject, "Order");
  const off = ctxFor([tokenOk, limited, rest], { seed: SEED, extraEnv: { GOOGLE_IDENTITIES: IDS } });
  await assert.rejects(off.callTool("gmail_message_identity", { messageId: "m7" }), { code: "RATE_LIMITED" });
});
