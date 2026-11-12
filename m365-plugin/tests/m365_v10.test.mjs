// 0.10.0: Teams completeness - start a chat, post / reply in a channel, @mention, quote, edit and delete your own message.
// Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";

const CHAT = "19:a@unq.v2";
const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const ME = [/^GET .*\/me\?\$select=id/, () => json({ id: "me-1", displayName: "Me Myself" })];
const MEMBERS = [/^GET .*\/chats\/[^/]+\/members/, () => json({ value: [
  { displayName: "Me Myself", email: "me@contoso.example", userId: "me-1" },
  { displayName: "Sara", email: "sara@contoso.example", userId: "u-2" },
  { displayName: "Omar", email: "omar@contoso.example", userId: "u-3" }] })];
const CHATINFO = [/^GET .*\/chats\/[^/?]+\?/, () => json({ topic: "Project", chatType: "group" })];
const USERS = [/^GET .*\/users\?\$filter=/, ({ url }) => {
  const q = decodeURIComponent(url);
  const dir = { "sara@contoso.example": { id: "u-2", displayName: "Sara" }, "omar@contoso.example": { id: "u-3", displayName: "Omar" }, "me@contoso.example": { id: "me-1", displayName: "Me Myself" } };
  const hit = Object.entries(dir).find(([e]) => q.includes(`'${e}'`));
  return json({ value: hit ? [{ ...hit[1], mail: hit[0] }] : [] });
}];
const ctx = (routes = [], env = {}) => ctxFor([TOK, ME, MEMBERS, CHATINFO, USERS, ...routes], { M365_ATTACH_SCOPE: "anywhere", ...env });
const commit = (c, s) => call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest });

test("exactly one destination", async () => {
  const c = ctx();
  for (const a of [{ text: "x" }, { chat_id: CHAT, to: ["sara@contoso.example"], text: "x" }, { chat_id: CHAT, team_id: "t", channel_id: "c", text: "x" }]) {
    await assert.rejects(call(c, "teams_stage", a), (e) => e.code === "INVALID_ARGUMENT", JSON.stringify(a));
  }
});

test("new 1:1 chat: resolves the address, creates the chat at commit (not stage), then posts", async () => {
  const c = ctx([[/^POST .*\/v1\.0\/chats$/, () => json({ id: "19:new@unq.gbl.spaces" }, 201)], [/^POST .*\/chats\/19%3Anew%40unq\.gbl\.spaces\/messages$/, () => json({ id: "m9" }, 201)]]);
  const s = await call(c, "teams_stage", { to: ["Sara@Contoso.example"], text: "Hi Sara" });
  assert.match(s.preview.action, /1:1/); assert.deepEqual(s.preview.members.map((m) => m.email), ["you", "sara@contoso.example"]);
  assert.equal(calls(c, "POST", /\/chats$/).length, 0, "nothing created at stage");
  const r = await commit(c, s);
  assert.equal(r.sent, true); assert.equal(r.new_chat, true); assert.equal(r.chat_id, "19:new@unq.gbl.spaces");
  const body = calls(c, "POST", /\/v1\.0\/chats$/)[0].json;
  assert.equal(body.chatType, "oneOnOne");
  assert.deepEqual(body.members.map((m) => m["user@odata.bind"]), ["https://graph.microsoft.com/v1.0/users('me-1')", "https://graph.microsoft.com/v1.0/users('u-2')"]);
  assert.equal(body.topic, undefined, "a 1:1 chat has no topic");
});

test("new group chat: topic kept; unknown people and names are refused; a retry after a failed post reuses the created chat", async () => {
  let posts = 0;
  const c = ctx([[/^POST .*\/v1\.0\/chats$/, () => json({ id: "19:grp@thread.v2" }, 201)],
    [/^POST .*\/chats\/19%3Agrp%40thread\.v2\/messages$/, () => (++posts === 1 ? json({ error: { code: "BadRequest" } }, 400) : json({ id: "m1" }, 201))]]);
  await assert.rejects(call(c, "teams_stage", { to: ["nobody@contoso.example"], text: "x" }), (e) => e.code === "NOT_FOUND");
  await assert.rejects(call(c, "teams_stage", { to: ["Sara"], text: "x" }), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(call(c, "teams_stage", { to: ["me@contoso.example"], text: "x" }), (e) => e.code === "INVALID_ARGUMENT");
  const s = await call(c, "teams_stage", { to: ["sara@contoso.example", "omar@contoso.example"], topic: "Launch", text: "Kick-off" });
  assert.match(s.preview.action, /NEW group chat/); assert.equal(s.preview.topic, "Launch");
  await assert.rejects(commit(c, s));
  const r = await commit(c, s);
  assert.equal(r.sent, true);
  assert.equal(calls(c, "POST", /\/v1\.0\/chats$/).length, 1, "the group chat was created once, not twice");
});

test("new chat whose creation outcome is unknown is never repeated", async () => {
  const c = ctx([[/^POST .*\/v1\.0\/chats$/, () => json({ error: { code: "x" } }, 504)]]);
  const s = await call(c, "teams_stage", { to: ["sara@contoso.example", "omar@contoso.example"], text: "x" });
  await assert.rejects(commit(c, s), (e) => e.code === "SEND_UNCERTAIN" && /teams_find_chat/.test(e.hint));
  await assert.rejects(commit(c, s), (e) => e.code === "STAGE_NOT_READY");
});

test("@mentions: only chat members; rendered as Teams mentions with their ids", async () => {
  const c = ctx([[/^POST .*\/chats\/[^/]+\/messages$/, () => json({ id: "m1" }, 201)]]);
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, text: "x", mentions: ["stranger@contoso.example"] }), (e) => e.code === "INVALID_ARGUMENT" && /not a member/.test(e.message));
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "please review", mentions: ["sara@contoso.example", "omar@contoso.example"] });
  assert.deepEqual(s.preview.mentions.map((m) => m.email), ["sara@contoso.example", "omar@contoso.example"]);
  await commit(c, s);
  const m = calls(c, "POST", /messages$/)[0].json;
  assert.equal(m.body.contentType, "html");
  assert.match(m.body.content, /^<p><at id="0">Sara<\/at> <at id="1">Omar<\/at><\/p><p>please review<\/p>$/);
  assert.deepEqual(m.mentions[1], { id: 1, mentionText: "Omar", mentioned: { user: { id: "u-3", displayName: "Omar", userIdentityType: "aadUser" } } });
});

test("quote a chat message: shown in the preview, sent as a message reference", async () => {
  const c = ctx([[/^GET .*\/chats\/[^/]+\/messages\/q1$/, () => json({ id: "q1", from: { user: { id: "u-2", displayName: "Sara" } }, body: { contentType: "html", content: "<p>Is it <b>done</b>?</p>" } })],
    [/^POST .*\/chats\/[^/]+\/messages$/, () => json({ id: "m1" }, 201)]]);
  const s = await call(c, "teams_stage", { chat_id: CHAT, text: "Yes", quote_message_id: "q1" });
  assert.deepEqual(s.preview.quoting, { from: "Sara", text: "Is it done?" });
  await commit(c, s);
  const m = calls(c, "POST", /messages$/)[0].json;
  assert.match(m.body.content, /^<attachment id="q1"><\/attachment><p>Yes<\/p>$/);
  assert.equal(m.attachments[0].contentType, "messageReference");
  assert.deepEqual(JSON.parse(m.attachments[0].content), { messageId: "q1", messagePreview: "Is it done?", messageSender: { user: { id: "u-2", displayName: "Sara", userIdentityType: "aadUser" } } });
});

test("channel post and thread reply; the channels module is required; files refused, pictures fine", async () => {
  const routes = [[/^GET .*\/teams\/t1\?/, () => json({ displayName: "Engineering" })], [/^GET .*\/teams\/t1\/channels\/c1\?/, () => json({ displayName: "General", membershipType: "standard" })],
    [/^GET .*\/teams\/t1\/channels\/c1\/messages\/root1$/, () => json({ id: "root1", from: { user: { displayName: "Sara" } }, body: { contentType: "html", content: "<p>Release notes?</p>" } })],
    [/^POST .*\/teams\/t1\/channels\/c1\/messages(\/root1\/replies)?$/, () => json({ id: "cm1" }, 201)]];
  const off = ctx(routes);
  await assert.rejects(call(off, "teams_stage", { team_id: "t1", channel_id: "c1", text: "x" }), (e) => e.code === "ACCESS_NEEDED" && /channels module/.test(e.message));
  const c = ctx(routes, { M365_MODULES: "teams,channels,files,people" });
  const s = await call(c, "teams_stage", { team_id: "t1", channel_id: "c1", text: "Deployed **v2**", mentions: ["omar@contoso.example"] });
  assert.equal(s.preview.channel, "General"); assert.equal(s.preview.team, "Engineering"); assert.match(s.preview.visible_to, /everyone/);
  let r = await commit(c, s);
  assert.equal(r.channel_id, "c1");
  assert.equal(calls(c, "POST", /\/channels\/c1\/messages$/).length, 1);
  const s2 = await call(c, "teams_stage", { team_id: "t1", channel_id: "c1", reply_to_message_id: "root1", text: "Here they are" });
  assert.deepEqual(s2.preview.replying_to, { from: "Sara", text: "Release notes?" });
  r = await commit(c, s2);
  assert.equal(calls(c, "POST", /\/messages\/root1\/replies$/).length, 1);
  await assert.rejects(call(c, "teams_stage", { team_id: "t1", channel_id: "c1", text: "x", quote_message_id: "q" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("edit your own message: preview shows current and new text; someone else's message is refused", async () => {
  const c = ctx([[/^GET .*\/chats\/[^/]+\/messages\/mine$/, () => json({ id: "mine", from: { user: { id: "me-1" } }, body: { contentType: "text", content: "Meeting at 3" } })],
    [/^GET .*\/chats\/[^/]+\/messages\/theirs$/, () => json({ id: "theirs", from: { user: { id: "u-2" } }, body: { contentType: "text", content: "hi" } })],
    [/^PATCH .*\/chats\/[^/]+\/messages\/mine$/, () => new Response(null, { status: 204 })]]);
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, edit_message_id: "theirs", text: "x" }), (e) => e.code === "NOT_YOUR_MESSAGE");
  await assert.rejects(call(c, "teams_stage", { chat_id: CHAT, edit_message_id: "mine", text: "x", mentions: ["sara@contoso.example"] }), (e) => e.code === "INVALID_ARGUMENT");
  const s = await call(c, "teams_stage", { chat_id: CHAT, edit_message_id: "mine", text: "Meeting at **4**" });
  assert.equal(s.preview.current_text, "Meeting at 3"); assert.equal(s.preview.text, "Meeting at **4**");
  const r = await commit(c, s);
  assert.equal(r.edited, true);
  const patch = calls(c, "PATCH", /messages\/mine$/)[0].json;
  assert.equal(patch.body.contentType, "html"); assert.match(patch.body.content, /<b>4<\/b>/);
});

test("edit refused for a missing permission says exactly which one", async () => {
  const c = ctx([[/^GET .*\/chats\/[^/]+\/messages\/mine$/, () => json({ id: "mine", from: { user: { id: "me-1" } }, body: { contentType: "text", content: "a" } })],
    [/^PATCH .*\/chats\/[^/]+\/messages\/mine$/, () => json({ error: { code: "Forbidden" } }, 403)]]);
  const s = await call(c, "teams_stage", { chat_id: CHAT, edit_message_id: "mine", text: "b" });
  await assert.rejects(commit(c, s), (e) => e.code === "ACCESS_NEEDED" && /Chat\.ReadWrite/.test(e.message));
  await assert.rejects(commit(c, s), (e) => e.code === "ACCESS_NEEDED", "an edit can be retried after the permission is added");
});

test("delete your own message only, via softDelete", async () => {
  const c = ctx([[/^GET .*\/chats\/[^/]+\/messages\/mine$/, () => json({ id: "mine", from: { user: { id: "me-1" } }, body: { contentType: "text", content: "oops" } })],
    [/^GET .*\/chats\/[^/]+\/messages\/theirs$/, () => json({ id: "theirs", from: { user: { id: "u-2" } }, body: { contentType: "text", content: "hi" } })],
    [/^POST .*\/users\/me-1\/chats\/[^/]+\/messages\/mine\/softDelete$/, () => new Response(null, { status: 204 })]]);
  await assert.rejects(call(c, "teams_delete_message", { chat_id: CHAT, message_id: "theirs" }), (e) => e.code === "NOT_YOUR_MESSAGE");
  const r = await call(c, "teams_delete_message", { chat_id: CHAT, message_id: "mine" });
  assert.equal(r.deleted, true); assert.equal(r.text_was, "oops");
  assert.equal(calls(c, "POST", /softDelete$/).length, 1);
});

test("files in a new chat are shared with exactly the new chat's members", async () => {
  const { mkdtempSync, writeFileSync } = await import("node:fs");
  const { tmpdir } = await import("node:os"); const { join } = await import("node:path");
  const d = mkdtempSync(join(tmpdir(), "m365-v10-")); const f = join(d, "plan.pdf"); writeFileSync(f, "%PDF");
  const c = ctx([[/^POST .*\/v1\.0\/chats$/, () => json({ id: "19:new@thread.v2" }, 201)],
    [/^PUT .*\/me\/drive\/root:/, () => json({ id: "item-1" }, 201)],
    [/^GET .*\/me\/drive\/items\/item-1\?/, () => json({ id: "item-1", name: "plan.pdf", eTag: '"{0F8FAD5B-D9CB-469F-A165-70867728950E},1"', webDavUrl: "https://x.example/plan.pdf" })],
    [/^POST .*\/invite$/, () => json({ value: [] })], [/^POST .*\/messages$/, () => json({ id: "m1" }, 201)]]);
  const s = await call(c, "teams_stage", { to: ["sara@contoso.example", "omar@contoso.example"], text: "plan", attachments: [{ path: f }] });
  assert.deepEqual(s.preview.sharing.read_access_for, ["omar@contoso.example", "sara@contoso.example"]);
  await commit(c, s);
  const order = c.fetch.calls.filter((x) => x.method !== "GET" && !/oauth2/.test(x.url)).map((x) => x.method + " " + x.url.replace(/^.*v1\.0/, "").replace(/\?.*$/, ""));
  assert.deepEqual(order.map((o) => o.split(" ")[0] + " " + (o.includes("/chats/19") ? "message" : o.includes("/chats") ? "chat" : o.includes("invite") ? "invite" : "upload")), ["POST chat", "PUT upload", "POST invite", "POST message"]);
});

test("permissions: channel posting is requested only with the channels module", async () => {
  const { resolveConfig } = await import("../server/config.mjs");
  assert.ok(!resolveConfig({ M365_HOME: "x", M365_CLIENT_ID: "c" }).scopes.includes("ChannelMessage.Send"));
  assert.ok(resolveConfig({ M365_HOME: "x", M365_CLIENT_ID: "c", M365_MODULES: "teams,channels" }).scopes.includes("ChannelMessage.Send"));
  assert.ok(!resolveConfig({ M365_HOME: "x", M365_CLIENT_ID: "c", M365_MODULES: "teams,channels", M365_READONLY: "true" }).scopes.includes("ChannelMessage.Send"));
});
