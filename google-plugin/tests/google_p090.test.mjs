// 0.9.0 tests: opt-in Gmail settings and full-mailbox scopes (and the guard both ways), tool visibility per option,
// SCOPE_MISSING before any call, and the mailbox / settings tools. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { TOKEN, FULL_GRANT, ctxFor, json, home } from "./_helpers.mjs";
import { FORBIDDEN_SCOPE, FULL_MAILBOX_SCOPE, SCOPES, resolveConfig } from "../server/config.mjs";
import { createAuth, scopeString } from "../server/auth.mjs";
import { CLASSES } from "../server/tools/bridge.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const REST = /^(GET|POST|PUT|PATCH|DELETE) https:\/\/gmail\.googleapis\.com\//;
const S_BASIC = SCOPES.gmailSettingsBasic, S_SHARING = SCOPES.gmailSettingsSharing;
const SEED = (extra = []) => ({ account: { email: "me@mail.example" }, scopes_granted: [...FULL_GRANT, ...extra] });
const ALL_ON = { GOOGLE_REST_FALLBACK: "1", GOOGLE_GMAIL_SETTINGS: "1", GOOGLE_FULL_MAILBOX: "1" };

function rest(routes, seen = []) {
  return [REST, async ({ url, init, body }) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/gmail\/v1\/users\/me\//, "");
    seen.push({ method: init.method || "GET", path, query: Object.fromEntries(u.searchParams), body: body ? JSON.parse(body) : undefined });
    for (const [k, h] of routes) {
      const [m, re] = k.split(" ");
      if (m === (init.method || "GET") && new RegExp(`^${re}$`).test(path)) return h({ u, body: body ? JSON.parse(body) : undefined });
    }
    return json({ error: { code: 404, message: `no fake for ${init.method} ${path}` } }, 404);
  }];
}

// ------------------------------------------------------------------------------------------------ scopes

test("scopes: defaults unchanged; GOOGLE_GMAIL_SETTINGS adds settings.basic + .sharing; GOOGLE_FULL_MAILBOX adds full mailbox; read-only or no gmail adds nothing", () => {
  const sc = (env) => resolveConfig(env).scopes;
  assert.ok(!sc({}).some((s) => s.includes("settings") || s === FORBIDDEN_SCOPE), "default: as before");
  assert.ok(sc({ GOOGLE_GMAIL_SETTINGS: "1" }).includes(S_BASIC) && sc({ GOOGLE_GMAIL_SETTINGS: "1" }).includes(S_SHARING));
  assert.ok(!sc({ GOOGLE_GMAIL_SETTINGS: "1" }).includes(FORBIDDEN_SCOPE));
  assert.ok(sc({ GOOGLE_FULL_MAILBOX: "1" }).includes(FULL_MAILBOX_SCOPE));
  for (const env of [{ GOOGLE_READONLY: "1" }, { GOOGLE_MODULES: "calendar,drive" }]) {
    const s = sc({ ...env, GOOGLE_GMAIL_SETTINGS: "1", GOOGLE_FULL_MAILBOX: "1" });
    assert.ok(!s.includes(FORBIDDEN_SCOPE) && !s.includes(S_BASIC), JSON.stringify(env));
    assert.equal(resolveConfig({ ...env, GOOGLE_FULL_MAILBOX: "1" }).fullMailbox, false);
  }
});

test("full-mailbox guard: refused exactly as before without GOOGLE_FULL_MAILBOX; requested on sign-in with it", () => {
  assert.throws(() => scopeString([SCOPES.gmailModify, FORBIDDEN_SCOPE]), { code: "SCOPE_FORBIDDEN" });
  assert.equal(scopeString([FORBIDDEN_SCOPE], { allowFullMailbox: true }), FORBIDDEN_SCOPE);
  const h = home();
  assert.throws(() => createAuth({ ...resolveConfig({ GOOGLE_PLUGIN_HOME: h }), scopes: [SCOPES.gmailModify, FORBIDDEN_SCOPE] }), { code: "SCOPE_FORBIDDEN" }, "only the opt-in, not a hand-built scope list, lifts the guard");
  const on = createAuth(resolveConfig({ GOOGLE_PLUGIN_HOME: h, GOOGLE_FULL_MAILBOX: "1", GOOGLE_GMAIL_SETTINGS: "1" }));
  for (const s of [FULL_MAILBOX_SCOPE, S_BASIC, S_SHARING, SCOPES.gmailModify]) assert.ok(on._scope.split(" ").includes(s), s);
});

test("a saved sign-in holding full mailbox access is refused without the opt-in (SCOPE_TOO_BROAD) and used with it", async () => {
  const route = rest([["GET labels", () => json({ labels: [] })], ["POST messages/m1/trash", () => json({ id: "m1", labelIds: ["TRASH"] })]]);
  const off = ctxFor([tokenOk, route], { seed: SEED([FULL_MAILBOX_SCOPE]), extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  await assert.rejects(off.callTool("gmail_rest_trash_message", { messageId: "m1" }), { code: "SCOPE_TOO_BROAD" });
  const on = ctxFor([tokenOk, route], { seed: SEED([FULL_MAILBOX_SCOPE]), extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_FULL_MAILBOX: "1" } });
  assert.equal((await on.callTool("gmail_rest_trash_message", { messageId: "m1" })).trashed, true);
  const st = await on.ctx.auth.status({ verify: false });
  assert.deepEqual(st.scopes_missing, [], "status: nothing missing once the full scope is granted");
  const missing = await ctxFor([tokenOk], { seed: SEED(), extraEnv: { GOOGLE_FULL_MAILBOX: "1", GOOGLE_GMAIL_SETTINGS: "1" } }).ctx.auth.status({ verify: false });
  for (const s of [FULL_MAILBOX_SCOPE, S_BASIC, S_SHARING]) assert.ok(missing.scopes_missing.includes(s), `status lists ${s} as missing`);
});

// ------------------------------------------------------------------------------------------------ visibility + SCOPE_MISSING

test("tool visibility: mailbox tools need the REST switch; settings tools need GOOGLE_GMAIL_SETTINGS; permanent delete needs GOOGLE_FULL_MAILBOX", () => {
  const names = (env) => ctxFor([tokenOk], { seed: SEED(), extraEnv: env }).listTools().map((t) => t.name);
  assert.ok(!names({}).includes("gmail_rest_trash_message"));
  const rest_ = names({ GOOGLE_REST_FALLBACK: "1" });
  assert.ok(rest_.includes("gmail_rest_batch_modify") && !rest_.includes("gmail_rest_list_filters") && !rest_.includes("gmail_rest_empty_trash"));
  const settings = names({ GOOGLE_REST_FALLBACK: "1", GOOGLE_GMAIL_SETTINGS: "1" });
  assert.ok(settings.includes("gmail_rest_update_auto_forwarding") && !settings.includes("gmail_rest_delete_message"));
  const full = names(ALL_ON);
  assert.ok(full.includes("gmail_rest_empty_spam") && full.includes("gmail_rest_create_send_as"));
  assert.ok(!names({ ...ALL_ON, GOOGLE_READONLY: "1" }).some((n) => /gmail_rest_(trash|empty|delete|create|update|batch)/.test(n)), "read-only drops them");
});

test("SCOPE_MISSING (with the sign-in hint) before any Google call when the saved sign-in lacks the option's scope", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, rest([], seen)], { seed: SEED(), extraEnv: ALL_ON });
  await assert.rejects(c.callTool("gmail_rest_create_filter", { criteria: { from: "a@b.example" }, action: { addLabelIds: ["X"] } }), (e) => e.code === "SCOPE_MISSING" && /GOOGLE_GMAIL_SETTINGS=1/.test(e.hint));
  await assert.rejects(c.callTool("gmail_rest_update_auto_forwarding", { enabled: false }), { code: "SCOPE_MISSING" });
  await assert.rejects(c.callTool("gmail_rest_empty_trash", {}), (e) => e.code === "SCOPE_MISSING" && /GOOGLE_FULL_MAILBOX=1/.test(e.hint));
  assert.equal(seen.length, 0);
  // Reading settings works with gmail.modify alone.
  const r = ctxFor([tokenOk, rest([["GET settings/filters", () => json({ filter: [{ id: "f1" }] })]])], { seed: SEED(), extraEnv: ALL_ON });
  assert.deepEqual((await r.callTool("gmail_rest_list_filters", {})).filters, [{ id: "f1" }]);
  // A REST 403 for missing scopes also becomes SCOPE_MISSING.
  const g = ctxFor([tokenOk, rest([["POST messages/m1/trash", () => json({ error: { code: 403, message: "Request had insufficient authentication scopes.", status: "PERMISSION_DENIED" } }, 403)]])], { seed: SEED(), extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  await assert.rejects(g.callTool("gmail_rest_trash_message", { messageId: "m1" }), { code: "SCOPE_MISSING" });
});

// ------------------------------------------------------------------------------------------------ tools

const allScopes = SEED([S_BASIC, S_SHARING, FULL_MAILBOX_SCOPE]);

test("mailbox tools: label modify, batch modify (1000 max), batch trash counts failures, labels CRUD", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, rest([
    ["POST messages/m1/modify", ({ body }) => json({ id: "m1", labelIds: body.addLabelIds })],
    ["POST messages/batchModify", () => new Response(null, { status: 204 })],
    ["POST messages/ok\\d/trash", () => json({ id: "x" })],
    ["POST labels", ({ body }) => json({ id: "Label_1", ...body })],
    ["PATCH labels/Label_1", ({ body }) => json({ id: "Label_1", ...body })],
    ["DELETE labels/Label_1", () => new Response(null, { status: 204 })],
  ], seen)], { seed: allScopes, extraEnv: ALL_ON });
  assert.deepEqual((await c.callTool("gmail_rest_modify_message", { messageId: "m1", addLabelIds: ["SPAM"], removeLabelIds: ["INBOX"] })).labelIds, ["SPAM"]);
  const bm = await c.callTool("gmail_rest_batch_modify", { messageIds: ["a", "b", "a"], removeLabelIds: ["UNREAD"] });
  assert.deepEqual([bm.modified, seen.at(-1).body], [2, { ids: ["a", "b"], addLabelIds: [], removeLabelIds: ["UNREAD"] }]);
  await assert.rejects(c.callTool("gmail_rest_batch_modify", { messageIds: Array.from({ length: 1001 }, (_, i) => `m${i}`) }), { code: "INVALID_ARGUMENT" });
  const bt = await c.callTool("gmail_rest_batch_trash", { messageIds: ["ok1", "bad", "ok2"] });
  assert.deepEqual([bt.trashed, bt.failed.map((f) => f.id)], [2, ["bad"]]);
  assert.equal((await c.callTool("gmail_rest_create_label", { name: "Clients/Acme", color: { textColor: "#000000", backgroundColor: "#ffffff" } })).label.name, "Clients/Acme");
  assert.equal((await c.callTool("gmail_rest_update_label", { labelId: "Label_1", name: "Acme" })).label.name, "Acme");
  assert.equal((await c.callTool("gmail_rest_delete_label", { labelId: "Label_1" })).deleted, true);
});

test("permanent delete: empty Trash pages through every id and deletes in chunks of 1000, returning the count", async () => {
  const seen = [];
  const pages = { "": { messages: Array.from({ length: 500 }, (_, i) => ({ id: `t${i}` })), nextPageToken: "p2" }, p2: { messages: Array.from({ length: 700 }, (_, i) => ({ id: `u${i}` })) } };
  const c = ctxFor([tokenOk, rest([
    ["GET messages", ({ u }) => json(pages[u.searchParams.get("pageToken") ?? ""])],
    ["POST messages/batchDelete", () => new Response(null, { status: 204 })],
    ["DELETE messages/m9", () => new Response(null, { status: 204 })],
  ], seen)], { seed: allScopes, extraEnv: ALL_ON });
  const r = await c.callTool("gmail_rest_empty_trash", {});
  assert.deepEqual([r.deleted_permanently, r.folder], [1200, "TRASH"]);
  const deletes = seen.filter((x) => x.path === "messages/batchDelete");
  assert.deepEqual(deletes.map((d) => d.body.ids.length), [1000, 200]);
  assert.equal(seen.find((x) => x.path === "messages").query.labelIds, "TRASH");
  assert.equal((await c.callTool("gmail_rest_delete_message", { messageId: "m9" })).deleted_permanently, true);
});

test("settings: plain filters cannot forward or trash (NEEDS_CONFIRM_TOOL); the confirm variant can; SMTP passwords are never returned", async () => {
  const seen = [];
  const sendAs = { sendAsEmail: "info@shop.example", displayName: "Shop", smtpMsa: { host: "smtp.shop.example", port: 587, username: "info", password: "S3CRET-PW", securityMode: "starttls" } };
  const c = ctxFor([tokenOk, rest([
    ["POST settings/filters", ({ body }) => json({ id: "f9", ...body })],
    ["GET settings/sendAs", () => json({ sendAs: [sendAs] })],
    ["PATCH settings/sendAs/info%40shop\\.example", ({ body }) => json({ ...sendAs, ...body })],
    ["PUT settings/autoForwarding", ({ body }) => json(body)],
  ], seen)], { seed: allScopes, extraEnv: ALL_ON });
  for (const action of [{ forward: "x@evil.example" }, { addLabelIds: ["trash"] }]) {
    await assert.rejects(c.callTool("gmail_rest_create_filter", { criteria: { from: "a@b.example" }, action }), { code: "NEEDS_CONFIRM_TOOL" });
  }
  assert.equal(seen.filter((x) => x.path === "settings/filters").length, 0);
  assert.equal((await c.callTool("gmail_rest_create_filter_forward_or_delete", { criteria: { from: "a@b.example" }, action: { forward: "me2@mail.example" } })).filter.id, "f9");
  const list = await c.callTool("gmail_rest_list_send_as", {});
  await assert.rejects(c.callTool("gmail_rest_update_send_as", { sendAsEmail: "info@shop.example", replyToAddress: "x@evil.example" }), { code: "NEEDS_CONFIRM_TOOL" }, "reply-to needs the confirm tool");
  await assert.rejects(c.callTool("gmail_rest_update_send_as", { sendAsEmail: "info@shop.example", smtpMsa: { host: "smtp.evil.example" } }), { code: "NEEDS_CONFIRM_TOOL" });
  assert.equal(seen.filter((x) => x.method === "PATCH").length, 0, "nothing was changed");
  assert.equal((await c.callTool("gmail_rest_update_send_as", { sendAsEmail: "info@shop.example", signature: "<b>Shop</b>" })).send_as.signature, "<b>Shop</b>");
  const up = await c.callTool("gmail_rest_update_send_as_routing", { sendAsEmail: "info@shop.example", smtpMsa: { host: "smtp.shop.example", port: 587, username: "info", password: "NEW-PW", securityMode: "starttls" } });
  assert.equal(seen.at(-1).body.smtpMsa.password, "NEW-PW", "the password is sent to Google");
  assert.doesNotMatch(JSON.stringify([list, up]), /S3CRET-PW|NEW-PW|password/i, "and never returned");
  assert.deepEqual((await c.callTool("gmail_rest_update_auto_forwarding", { enabled: true, emailAddress: "me2@mail.example", disposition: "archive" })).auto_forwarding, { enabled: true, emailAddress: "me2@mail.example", disposition: "archive" });
});

test("classes: the takeover and destruction tools are confirm (hook asks), the rest write/read; permanent ones say so; the write limit counts them when set", async () => {
  const expectConfirm = ["gmail_rest_delete_message", "gmail_rest_delete_thread", "gmail_rest_batch_delete", "gmail_rest_empty_trash", "gmail_rest_empty_spam",
    "gmail_rest_create_filter_forward_or_delete", "gmail_rest_update_auto_forwarding", "gmail_rest_create_forwarding_address", "gmail_rest_delete_forwarding_address",
    "gmail_rest_create_send_as", "gmail_rest_delete_send_as", "gmail_rest_update_send_as_routing", "gmail_rest_set_auto_reply"];
  for (const n of expectConfirm) assert.ok(CLASSES.confirm.includes(n), n);
  for (const n of ["gmail_rest_trash_message", "gmail_rest_batch_modify", "gmail_rest_create_filter", "gmail_rest_update_vacation", "gmail_rest_update_send_as", "gmail_rest_delete_label"]) assert.ok(CLASSES.write.includes(n), n);
  const hook = JSON.parse(readFileSync(new URL("../hooks/hooks.json", import.meta.url), "utf8")).hooks.PreToolUse[0].matcher;
  for (const n of expectConfirm) assert.ok(new RegExp(hook).test(`mcp__plugin_google_google__${n}`), n);
  const tools = ctxFor([tokenOk], { seed: allScopes, extraEnv: ALL_ON }).listTools();
  for (const n of ["gmail_rest_delete_message", "gmail_rest_empty_trash", "gmail_rest_batch_delete"]) assert.match(tools.find((t) => t.name === n).description, /PERMANENT: it cannot be undone/);
  const c = ctxFor([tokenOk, rest([["POST messages/m\\d/trash", () => json({ id: "x" })]])], { seed: allScopes, extraEnv: { ...ALL_ON, GOOGLE_WRITE_LIMIT_PER_HOUR: "2" } });
  await c.callTool("gmail_rest_trash_message", { messageId: "m1" });
  await c.callTool("gmail_rest_trash_message", { messageId: "m2" });
  await assert.rejects(c.callTool("gmail_rest_trash_message", { messageId: "m3" }), { code: "WRITE_LIMIT_REACHED" });
});

test("auto-reply: the write tool can only turn it off; turning it on or setting text needs the confirm tool", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, rest([["PUT settings/vacation", ({ body }) => json(body)]], seen)], { seed: allScopes, extraEnv: ALL_ON });
  for (const args of [{ enableAutoReply: true }, { enableAutoReply: false, responseBodyPlainText: "Pay to account X" }]) {
    await assert.rejects(c.callTool("gmail_rest_update_vacation", args), { code: "NEEDS_CONFIRM_TOOL" });
  }
  assert.equal(seen.length, 0, "nothing was changed");
  assert.deepEqual((await c.callTool("gmail_rest_update_vacation", { enableAutoReply: false })).vacation, { enableAutoReply: false });
  const on = await c.callTool("gmail_rest_set_auto_reply", { enableAutoReply: true, responseSubject: "Away", responseBodyPlainText: "Back Monday" });
  assert.deepEqual(on.vacation, { enableAutoReply: true, responseSubject: "Away", responseBodyPlainText: "Back Monday" });
  assert.ok(CLASSES.confirm.includes("gmail_rest_set_auto_reply") && CLASSES.write.includes("gmail_rest_update_vacation"));
});

test("write limit counts every item of a batch and of an empty-Trash run; filter actions are rebuilt from checked fields only", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, rest([
    ["POST messages/[a-z0-9]+/trash", () => json({ id: "x" })],
    ["GET messages", () => json({ messages: Array.from({ length: 5 }, (_, i) => ({ id: `t${i}` })) })],
    ["POST messages/batchDelete", () => new Response(null, { status: 204 })],
    ["POST settings/filters", ({ body }) => json({ id: "f1", ...body })],
  ], seen)], { seed: allScopes, extraEnv: { ...ALL_ON, GOOGLE_WRITE_LIMIT_PER_HOUR: "4" } });
  await assert.rejects(c.callTool("gmail_rest_batch_trash", { messageIds: ["a", "b", "c", "d", "e"] }), (e) => e.code === "WRITE_LIMIT_REACHED" && /affect 5 item/.test(e.message));
  assert.equal(seen.filter((x) => x.path.endsWith("/trash")).length, 0, "nothing trashed when the batch is over the limit");
  assert.equal((await c.callTool("gmail_rest_batch_trash", { messageIds: ["a", "b", "c"] })).trashed, 3);
  await assert.rejects(c.callTool("gmail_rest_empty_trash", {}), { code: "WRITE_LIMIT_REACHED" }, "5 messages in Trash, 1 left in the budget");
  assert.equal(seen.filter((x) => x.path === "messages/batchDelete").length, 0);

  for (const action of [{ addLabelIds: "TRASH" }, { addLabelIds: ["X"], forwardTo: "x@evil.example" }, { forward: ["x@evil.example"] }]) {
    await assert.rejects(c.callTool("gmail_rest_create_filter", { criteria: { from: "a@b.example" }, action }), { code: "INVALID_ARGUMENT" }, JSON.stringify(action));
  }
  const ok = await c.callTool("gmail_rest_create_filter", { criteria: { from: "a@b.example" }, action: { addLabelIds: [" Label_1 "], removeLabelIds: ["INBOX"] } });
  assert.deepEqual(seen.at(-1).body.action, { addLabelIds: ["Label_1"], removeLabelIds: ["INBOX"] }, "only the checked, normalised fields are sent");
  assert.equal(ok.filter.id, "f1");
});

test("Google's domain-wide-delegation refusal is GOOGLE_LIMITATION (do it in Gmail settings), not the generic 403", async () => {
  const c = ctxFor([tokenOk, rest([["PATCH settings/sendAs/info%40shop\\.example", () => json({ error: { code: 403, message: "Access restricted to service accounts that have been delegated domain-wide authority", status: "PERMISSION_DENIED" } }, 403)]])], { seed: allScopes, extraEnv: ALL_ON });
  await assert.rejects(c.callTool("gmail_rest_update_send_as", { sendAsEmail: "info@shop.example", signature: "x" }), (e) => e.code === "GOOGLE_LIMITATION" && /Gmail itself/.test(e.hint));
  const tools = c.listTools();
  for (const n of ["gmail_rest_create_send_as", "gmail_rest_delete_send_as", "gmail_rest_update_send_as"]) assert.match(tools.find((t) => t.name === n).description, /GOOGLE_LIMITATION/, n);
  assert.match(tools.find((t) => t.name === "gmail_rest_untrash_message").description, /add INBOX/);
});
