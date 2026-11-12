// 0.9.0: files and pictures in Teams chat messages, and formatted Teams text. A file is uploaded to the sender's OneDrive
// at COMMIT time, shared read-only with exactly the members staged, and referenced from the message; a small picture
// travels inside the message. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";

const dir = () => mkdtempSync(join(tmpdir(), "m365-v09-"));
const CHAT = "19:a@unq.v2";
const GUID = "0f8fad5b-d9cb-469f-a165-70867728950e";
const PNG = Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), Buffer.from("picture-bytes")]);

function teamsCtx({ extraEnv = {}, members, invite = () => json({ value: [] }), post = () => json({ id: "msg1" }, 201), put } = {}) {
  const state = { deleted: [] };
  const c = ctxFor([TOK,
    [/^GET .*\/chats\/[^/]+\/members/, () => json({ value: members ?? [
      { displayName: "Me", email: "me@contoso.example", userId: "me-1" },
      { displayName: "Sara", email: "Sara@Contoso.example", userId: "u-2" },
      { displayName: "Omar", email: "omar@contoso.example", userId: "u-3" },
    ] })],
    [/^GET .*\/chats\/[^/]+\?/, () => json({ topic: "Project", chatType: "group" })],
    [/^GET .*\/me\?\$select=id/, () => json({ id: "me-1" })],
    [/^PUT .*\/me\/drive\/root:\/Microsoft%20Teams%20Chat%20Files\//, put ?? (() => json({ id: "item-1" }, 201))],
    [/^GET .*\/me\/drive\/items\/item-1\?/, () => json({ id: "item-1", name: "report 1.pdf", eTag: `"{${GUID.toUpperCase()}},2"`, webUrl: "https://contoso-my.example/x", webDavUrl: "https://contoso-my.example/personal/me/Documents/Microsoft Teams Chat Files/report 1.pdf" })],
    [/^POST .*\/me\/drive\/items\/item-1\/invite$/, invite],
    [/^DELETE .*\/me\/drive\/items\/item-1$/, () => { state.deleted.push("item-1"); return new Response(null, { status: 204 }); }],
    [/^POST .*\/chats\/[^/]+\/messages$/, post],
  ], { M365_ATTACH_SCOPE: "anywhere", ...extraEnv });
  c.state = state;
  return c;
}
const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const sent = (c) => calls(c, "POST", /\/messages$/)[0]?.json;

test("a file: nothing is uploaded at stage; commit uploads, shares with the staged members only, then posts a reference", async () => {
  const d = dir(); const file = join(d, "report.pdf"); writeFileSync(file, "%PDF-1.7 numbers");
  const c = teamsCtx();
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "Here is the **report**.", attachments: [{ path: file }] });
  assert.equal(calls(c, "PUT", /drive/).length, 0, "stage uploads nothing");
  assert.equal(s.preview.attachments[0].name, "report.pdf");
  assert.match(s.preview.attachments[0].sent_as, /OneDrive/);
  assert.deepEqual(s.preview.sharing.read_access_for, ["omar@contoso.example", "sara@contoso.example"], "everyone but me, lower-cased");
  const r = await call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest });
  assert.equal(r.sent, true); assert.deepEqual(r.attachments, ["report.pdf"]);
  const put = calls(c, "PUT", /drive/)[0];
  assert.match(put.url, /root:\/Microsoft%20Teams%20Chat%20Files\/report\.pdf:\/content\?@microsoft\.graph\.conflictBehavior=rename$/);
  assert.equal(put.body, "%PDF-1.7 numbers");
  const inv = calls(c, "POST", /\/invite$/)[0].json;
  assert.deepEqual(inv.recipients, [{ email: "omar@contoso.example" }, { email: "sara@contoso.example" }]);
  assert.deepEqual(inv.roles, ["read"]); assert.equal(inv.sendInvitation, false); assert.equal(inv.requireSignIn, true);
  const m = sent(c);
  assert.equal(m.body.contentType, "html");
  assert.ok(m.body.content.includes("<b>report</b>") && m.body.content.includes(`<attachment id="${GUID.toUpperCase()}"></attachment>`));
  assert.deepEqual(m.attachments, [{ id: GUID.toUpperCase(), contentType: "reference", contentUrl: "https://contoso-my.example/personal/me/Documents/Microsoft Teams Chat Files/report 1.pdf", name: "report 1.pdf" }]);
  const order = c.fetch.calls.filter((x) => /drive|messages$/.test(x.url) && x.method !== "GET").map((x) => x.method + (x.url.endsWith("/invite") ? " invite" : x.url.endsWith("/messages") ? " message" : " upload"));
  assert.deepEqual(order, ["PUT upload", "POST invite", "POST message"]);
});

test("a small picture travels inside the message: no OneDrive, no sharing", async () => {
  const d = dir(); const img = join(d, "shot.png"); writeFileSync(img, PNG);
  const c = teamsCtx();
  const s = await call(c, "teams_stage", { chat_id: CHAT, attachments: [{ path: img, name: "screenshot-1.png" }] });
  assert.equal(s.preview.sharing, undefined); assert.match(s.preview.attachments[0].sent_as, /picture/);
  await call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest });
  assert.equal(calls(c, "PUT", /drive/).length + calls(c, "POST", /invite/).length, 0);
  const m = sent(c);
  assert.equal(m.hostedContents[0].contentBytes, PNG.toString("base64")); assert.equal(m.hostedContents[0].contentType, "image/png");
  assert.match(m.body.content, /<img src="\.\.\/hostedContents\/1\/\$value" alt="screenshot-1\.png">/);
  assert.equal(m.attachments, undefined);
  const fake = join(d, "fake.png"); writeFileSync(fake, "not a png");
  const s2 = await call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: fake }] });
  assert.match(s2.preview.attachments[0].sent_as, /OneDrive/, "a file that only claims to be a picture goes as a file");
});

test("text only: plain stays plain text; marks become Teams formatting; line breaks are allowed", async () => {
  const c = teamsCtx();
  let s = await call(c, "teams_stage", { chat_id: CHAT, text: "On my way" });
  await call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest });
  assert.deepEqual(sent(c), { body: { contentType: "text", content: "On my way" } });
  const c2 = teamsCtx();
  s = await call(c2, "teams_stage", { chat_id: CHAT, text: "Status:\n\n- **done**\n- ==blocked==\n\n<b>raw</b>" });
  assert.equal(s.preview.formatted, true);
  await call(c2, "teams_commit", { stage_id: s.stage_id, digest: s.digest });
  const html = sent(c2).body.content;
  assert.match(html, /<ul[^>]*><li><b>done<\/b><\/li><li><span[^>]*>blocked<\/span><\/li><\/ul>/);
  assert.ok(html.includes("&lt;b&gt;raw&lt;/b&gt;") && !/<b>raw/.test(html));
  await assert.rejects(call(c2, "teams_stage", { chat_id: CHAT, text: "bell\u0007" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c2, "teams_stage", { chat_id: CHAT }), (e) => e.code === "INVALID_ARGUMENT");
});

test("the same file rules as email: secrets refused, folders mode refused, chat_image needs the hook", async () => {
  const d = dir(); writeFileSync(join(d, ".env"), "KEY=1"); writeFileSync(join(d, "ok.txt"), "fine");
  const c = teamsCtx();
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: join(d, ".env") }] }), (e) => e.code === "PATH_NOT_ALLOWED");
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ chat_image: 1 }] }), (e) => e.code === "CHAT_IMAGE_UNAVAILABLE");
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{}] }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: Array(11).fill({ path: join(d, "ok.txt") }) }), (e) => e.code === "INVALID_ARGUMENT");
  const bot = teamsCtx({ extraEnv: { M365_ATTACH_SCOPE: "folders" } });
  await assert.rejects(call(bot, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: join(d, "ok.txt") }] }), (e) => e.code === "ATTACH_NOT_CONFIGURED");
  const noFiles = teamsCtx({ extraEnv: { M365_MODULES: "teams" } });
  await assert.rejects(call(noFiles, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: join(d, "ok.txt") }] }), (e) => e.code === "ACCESS_NEEDED");
  assert.equal(calls(c, "PUT", /drive/).length, 0);
});

test("a file changed after the preview is not sent, and the stage can be redone", async () => {
  const d = dir(); const file = join(d, "report.pdf"); writeFileSync(file, "v1");
  const c = teamsCtx();
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: file }] });
  writeFileSync(file, "v2 - swapped");
  await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "FILE_CHANGED" && /Nothing was sent/.test(e.message));
  assert.equal(calls(c, "PUT", /drive/).length + calls(c, "POST", /messages$/).length, 0);
  writeFileSync(file, "v1");
  assert.equal((await call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest })).sent, true, "back to staged, so the unchanged file can still go");
});

test("sharing refused: the upload is taken back, nothing is posted, retry is allowed", async () => {
  const d = dir(); const file = join(d, "report.pdf"); writeFileSync(file, "v1");
  const c = teamsCtx({ invite: () => json({ error: { code: "accessDenied" } }, 403) });
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: file }] });
  await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "ACCESS_NEEDED" && /Nothing was sent/.test(e.message));
  assert.deepEqual(c.state.deleted, ["item-1"]); assert.equal(calls(c, "POST", /messages$/).length, 0);
  await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "ACCESS_NEEDED", "still staged, not blocked as 'sending'");
});

test("the post itself: a refusal takes the upload back; an unknown outcome keeps it and blocks a repeat", async () => {
  const d = dir(); const file = join(d, "report.pdf"); writeFileSync(file, "v1");
  const refused = teamsCtx({ post: () => json({ error: { code: "BadRequest" } }, 400) });
  let s = await call(refused, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: file }] });
  await assert.rejects(call(refused, "teams_commit", { stage_id: s.stage_id, digest: s.digest }));
  assert.deepEqual(refused.state.deleted, ["item-1"]);
  const unknown = teamsCtx({ post: () => json({ error: { code: "x" } }, 503) });
  s = await call(unknown, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: file }] });
  await assert.rejects(call(unknown, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "SEND_UNCERTAIN");
  assert.deepEqual(unknown.state.deleted, [], "the message may be in the chat: its file must stay");
  await assert.rejects(call(unknown, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "STAGE_NOT_READY");
});

test("who gets access is fixed at stage time and members without an address are named", async () => {
  const d = dir(); const file = join(d, "report.pdf"); writeFileSync(file, "v1");
  const c = teamsCtx({ members: [{ displayName: "Me", email: "me@contoso.example", userId: "me-1" }, { displayName: "Guest Person", email: null, userId: "g-9" }] });
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "x", attachments: [{ path: file }] });
  assert.deepEqual(s.preview.sharing.read_access_for, []); assert.deepEqual(s.preview.sharing.no_access_for, ["Guest Person"]);
  await call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest });
  assert.equal(calls(c, "POST", /invite/).length, 0, "nobody to share with: no invite call");
  await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: "0".repeat(16) }), (e) => ["DIGEST_MISMATCH", "ALREADY_DONE"].includes(e.code));
});

test("read-only mode has no Teams send tools and the Graph door refuses an upload", async () => {
  const c = teamsCtx({ extraEnv: { M365_READONLY: "true" } });
  assert.ok(!c.tools.some((t) => t.name === "teams_stage" || t.name === "teams_commit"));
  assert.throws(() => c.ctx.graph.putBytes("/me/drive/root:/x:/content", Buffer.from("x")), (e) => e.code === "READ_ONLY");
});
