// Bridge tests (milestone B1): a fake Google Workspace MCP server stands in for the network. Nothing here talks to Google.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { PassThrough } from "node:stream";
import { createInterface } from "node:readline";
import { TOKEN, ctxFor, json } from "./_helpers.mjs";
import { ALL_TOOLS, filterTools } from "../server/tools/index.mjs";
import { CLASSES, MAX_DESCRIPTION, SNAPSHOT, snapshotTools, capResult } from "../server/tools/bridge.mjs";
import { resolveConfig } from "../server/config.mjs";
import { PROTOCOL, CLIENT_INFO } from "../server/remote.mjs";
import { serveStdio } from "../server/mcp.mjs";
import { runGrant, grantSteps } from "../server/grant.mjs";
import { diffModule } from "../server/schema.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const MCP = /^POST https:\/\/(gmail|calendar|drive)mcp\.googleapis\.com\/mcp\/v1$/;
const parse = (c) => JSON.parse(c.result?.content?.[0]?.text ?? c.content[0].text);
const mcpCalls = (c) => c.fetch.calls.filter((x) => MCP.test(`${x.method} ${x.url}`)).map((x) => ({ ...x, json: JSON.parse(x.body) }));

/** A fake Google MCP server: handler(rpc, url) returns a JSON-RPC result, or a Response for HTTP-level replies. */
function google(handler) {
  return [MCP, async ({ url, body }) => {
    const rpc = JSON.parse(body);
    const r = await handler(rpc, url);
    return r instanceof Response ? r : json({ jsonrpc: "2.0", id: rpc.id, result: r });
  }];
}
const ok = (data) => ({ content: [{ type: "text", text: JSON.stringify(data) }], structuredContent: data });
const FORM = {
  resultType: "input_required",
  requestState: "opaque-state-1",
  inputRequests: {
    approval_choice: {
      method: "elicitation/create",
      params: {
        mode: "form",
        message: "This agent wants to read an email from an external user. Do you want to allow this?",
        requestedSchema: { type: "object", required: ["approval_choice"], properties: { approval_choice: { type: "string", title: "Allow?", enum: ["ALLOW_ONCE", "ALLOW_TOOL_ALWAYS", "DENY_ONCE"], enumNames: ["Allow once", "Always allow this tool", "Don't allow"] } } },
      },
    },
  },
};
/** Asks once (FORM), then returns data when the retry carries an inputResponses answer. */
const asksOnce = (data = { id: "t1", messages: [] }) => google((rpc) => (rpc.params.inputResponses ? ok(data) : FORM));

// ------------------------------------------------------------------------------------------------ classification

test("every Google tool in the snapshot is classified exactly once (read/write/confirm) or hidden with a reason", () => {
  const snap = [...snapshotTools().keys()].sort();
  const own = new Set(CLASSES.plugin_tools);
  const classified = ["read", "write", "confirm"].flatMap((k) => CLASSES[k]).filter((n) => !own.has(n));
  const hidden = Object.keys(CLASSES.hidden ?? {});
  const all = [...classified, ...hidden];
  assert.equal(new Set(all).size, all.length, "a tool is listed twice");
  assert.deepEqual([...all].sort(), snap, "tools.json and the snapshot disagree: classify or hide every Google tool");
  for (const [n, why] of Object.entries(CLASSES.hidden)) assert.ok(why.trim(), `${n} is hidden without a reason`);
  assert.ok(classified.every((n) => /^(gmail|calendar|drive)_/.test(n)));
});

test("exposed tools carry the snapshot's input schema unchanged, and every description fits 1024 characters", () => {
  const snap = snapshotTools();
  const own = new Set(CLASSES.plugin_tools);
  const bridged = ALL_TOOLS.filter((t) => t.module !== "auth" && !own.has(t.name));
  assert.equal(bridged.length, ["read", "write", "confirm"].flatMap((k) => CLASSES[k]).filter((n) => !own.has(n)).length);
  assert.ok(CLASSES.plugin_tools.every((n) => ALL_TOOLS.some((t) => t.name === n)), "every plugin_tools entry is implemented");
  for (const t of bridged) {
    assert.deepEqual(t.inputSchema, snap.get(t.name).inputSchema, t.name);
    assert.equal(t.remote, snap.get(t.name).name);
    assert.ok(t.description.length <= MAX_DESCRIPTION, `${t.name}: ${t.description.length}`);
    // A Google description over the limit must have a written rewrite, never the cut fallback.
    if ((snap.get(t.name).description ?? "").length > MAX_DESCRIPTION) assert.ok(CLASSES.descriptions[t.name], `${t.name} needs a description rewrite`);
  }
  for (const n of Object.keys(CLASSES.descriptions)) assert.ok(bridged.some((t) => t.name === n), `rewrite for an unexposed tool: ${n}`);
  assert.equal(SNAPSHOT.servers.gmail.tools.some((t) => t.name === "get_message"), true);
});

test("filtering: modules, read-only mode (drops write/confirm) and allow / deny lists; auth tools always stay", () => {
  const fake = [
    { name: "google_auth_status", module: "auth", kind: "local" },
    { name: "gmail_a", module: "gmail", kind: "read" }, { name: "gmail_w", module: "gmail", kind: "write" },
    { name: "gmail_c", module: "gmail", kind: "confirm" }, { name: "drive_a", module: "drive", kind: "read" },
  ];
  const names = (env) => filterTools(fake, resolveConfig(env)).map((t) => t.name);
  assert.deepEqual(names({}), ["google_auth_status", "gmail_a", "gmail_w", "gmail_c", "drive_a"]);
  assert.deepEqual(names({ GOOGLE_MODULES: "gmail" }), ["google_auth_status", "gmail_a", "gmail_w", "gmail_c"]);
  assert.deepEqual(names({ GOOGLE_READONLY: "true" }), ["google_auth_status", "gmail_a", "drive_a"]);
  assert.deepEqual(names({ GOOGLE_TOOLS_ALLOW: "gmail_a,gmail_w", GOOGLE_TOOLS_DENY: "gmail_w" }), ["google_auth_status", "gmail_a"]);
  // Deny means deny, the sign-in tools included; an allow list does not drop them.
  assert.deepEqual(names({ GOOGLE_TOOLS_DENY: "google_auth_status" }), ["gmail_a", "gmail_w", "gmail_c", "drive_a"]);
  assert.deepEqual(names({ GOOGLE_TOOLS_ALLOW: "gmail_a" }), ["google_auth_status", "gmail_a"]);
});

// ------------------------------------------------------------------------------------------------ wire format + results

test("a bridged call goes to the module's Google MCP server in protocol 2026-07-28, with Google's own tool name", async () => {
  const c = ctxFor([tokenOk, google(() => ok({ labels: [{ id: "INBOX" }] }))]);
  const r = await c.callTool("gmail_list_labels", { x: 1 });
  assert.deepEqual(r, { tool: "gmail_list_labels", untrusted: true, data: { labels: [{ id: "INBOX" }] } });
  const [call] = mcpCalls(c);
  assert.equal(call.url, "https://gmailmcp.googleapis.com/mcp/v1");
  assert.equal(call.headers.Authorization, "Bearer at-live");
  assert.equal(call.headers["MCP-Protocol-Version"], PROTOCOL);
  assert.equal(call.headers["Mcp-Method"], "tools/call");
  assert.equal(call.headers["Mcp-Name"], "list_labels");
  assert.equal(call.json.method, "tools/call");
  assert.equal(call.json.params.name, "list_labels");
  assert.deepEqual(call.json.params.arguments, { x: 1 });
  const meta = call.json.params._meta;
  assert.equal(meta["io.modelcontextprotocol/protocolVersion"], "2026-07-28");
  assert.deepEqual(meta["io.modelcontextprotocol/clientCapabilities"], { elicitation: { form: {} } });
  assert.deepEqual(meta["io.modelcontextprotocol/clientInfo"], CLIENT_INFO);
  assert.equal(call.json.params.inputResponses, undefined);

  const cal = ctxFor([tokenOk, google(() => ok({ events: [] }))]);
  await cal.callTool("calendar_list_events", {});
  assert.equal(mcpCalls(cal)[0].url, "https://calendarmcp.googleapis.com/mcp/v1");
});

test("results: SSE replies, text-only replies, size caps and non-text blocks are handled; data is marked untrusted", async () => {
  const sse = ctxFor([tokenOk, [MCP, ({ body }) => new Response(`event: message\ndata: ${JSON.stringify({ jsonrpc: "2.0", id: JSON.parse(body).id, result: ok({ a: 1 }) })}\n\n`, { headers: { "content-type": "text/event-stream" } })]]);
  assert.deepEqual((await sse.callTool("gmail_list_labels", {})).data, { a: 1 });

  const textOnly = ctxFor([tokenOk, google(() => ({ content: [{ type: "text", text: "{\"files\":[]}" }] }))]);
  assert.deepEqual((await textOnly.callTool("drive_search_files", {})).data, { files: [] });

  const big = ctxFor([tokenOk, google(() => ({ content: [{ type: "text", text: "{}" }, { type: "image", mimeType: "image/png", data: "QUJD" }], structuredContent: { raw: "x".repeat(30_000) } }))]);
  const r = await big.callTool("gmail_get_message", { messageId: "m1", messageFormat: "RAW" });
  assert.equal(r.untrusted, true);
  assert.equal(r.truncated, true);
  assert.ok(r.data.raw.length < 21_000 && r.data.raw.includes("[cut 10000 characters]"));
  assert.deepEqual(r.omitted_content, [{ type: "image", mimeType: "image/png", uri: undefined, approx_chars: 4 }]);

  const arr = capResult({ items: Array.from({ length: 1000 }, (_, i) => ({ i, s: "y".repeat(100) })) }, { maxString: 50, maxTotal: 5000 });
  assert.ok(JSON.stringify(arr.data).length <= 5000 && arr.truncated && arr.data.items.length >= 1);
});

test("errors are text-only and distinct: not signed in, 401, 403, 429, 5xx, JSON-RPC error, Google tool error", async () => {
  const notSigned = ctxFor([google(() => ok({}))], { seed: false });
  await assert.rejects(notSigned.callTool("gmail_list_labels", {}), { code: "AUTH_REQUIRED" });
  assert.equal(mcpCalls(notSigned).length, 0, "no call to Google without a sign-in");

  const cases = [
    [() => json({ jsonrpc: "2.0", id: 1, error: { code: -32001, message: "Unauthenticated" } }, 401), "AUTH_EXPIRED"],
    [() => json({ jsonrpc: "2.0", id: 1, error: { code: -32002, message: "Gmail MCP API has not been used in project 1 or it is disabled" } }, 403), "GOOGLE_FORBIDDEN"],
    [() => new Response("slow down", { status: 429 }), "RATE_LIMITED"],
    [() => new Response("oops", { status: 503 }), "GOOGLE_UNAVAILABLE"],
    [(rpc) => json({ jsonrpc: "2.0", id: rpc.id, error: { code: -32602, message: "Invalid params" } }), "GOOGLE_ERROR"],
    [() => ({ isError: true, content: [{ type: "text", text: "Thread not found" }] }), "TOOL_ERROR"],
  ];
  for (const [reply, code] of cases) {
    const c = ctxFor([tokenOk, google(reply)]);
    await assert.rejects(c.callTool("gmail_get_thread", { threadId: "t" }), (e) => {
      assert.equal(e.code, code);
      assert.doesNotMatch(e.message + (e.hint ?? ""), /at-live|rt-1|GOCSPX/);
      return true;
    });
  }
  const forbidden = ctxFor([tokenOk, google(() => json({ jsonrpc: "2.0", id: 1, error: { message: "Gmail MCP API has not been used in project 1 or it is disabled" } }, 403))]);
  await assert.rejects(forbidden.callTool("gmail_list_labels", {}), (e) => /disabled/.test(e.message) && /AI-powered agent/.test(e.hint));
});

// ------------------------------------------------------------------------------------------------ confirmations

test("a confirmation is never answered by the plugin: without a form-capable client it is CONFIRMATION_NEEDED, sent once", async () => {
  const c = ctxFor([tokenOk, asksOnce()]);
  await assert.rejects(c.callTool("gmail_get_thread", { threadId: "t1" }), (e) => {
    assert.equal(e.code, "CONFIRMATION_NEEDED");
    assert.match(e.hint, /cli\.mjs" grant gmail_get_thread/);
    assert.doesNotMatch(e.message, /external user/, "Google's form text (which can quote an email subject) is not put in the error");
    return true;
  });
  assert.equal(mcpCalls(c).length, 1);
  assert.ok(mcpCalls(c).every((x) => x.json.params.inputResponses === undefined && x.json.params.requestState === undefined));

  // confirm mode "error" never forwards, even to a client that could show the form.
  let shown = 0;
  const strict = ctxFor([tokenOk, asksOnce()], { extraEnv: { GOOGLE_CONFIRM_MODE: "error" } });
  await assert.rejects(strict.callTool("gmail_get_thread", { threadId: "t1" }, { canElicit: true, elicit: async () => { shown++; return { action: "accept", content: { approval_choice: "ALLOW_ONCE" } }; } }), { code: "CONFIRMATION_NEEDED" });
  assert.equal(shown, 0);
  assert.equal(mcpCalls(strict).length, 1);
});

test("forwarded confirmation: the human's answer goes back with Google's requestState; nothing outside the form is sent", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, asksOnce({ id: "t1", messages: [{ id: "m1" }] })]);
  const r = await c.callTool("gmail_get_thread", { threadId: "t1" }, {
    canElicit: true,
    elicit: async (req) => { seen.push(req); return { action: "accept", content: { approval_choice: "ALLOW_TOOL_ALWAYS", extra: "dropped" } }; },
  });
  assert.equal(r.data.id, "t1");
  assert.equal(seen.length, 1);
  assert.equal(seen[0].tool, "gmail_get_thread");
  assert.equal(seen[0].params.message, FORM.inputRequests.approval_choice.params.message);
  const [first, second] = mcpCalls(c);
  assert.notEqual(first.json.id, second.json.id);
  assert.deepEqual(second.json.params.arguments, { threadId: "t1" });
  assert.equal(second.json.params.requestState, "opaque-state-1");
  assert.deepEqual(second.json.params.inputResponses, { approval_choice: { action: "accept", content: { approval_choice: "ALLOW_TOOL_ALWAYS" } } });

  // An answer that is not one of Google's choices is refused before anything is sent.
  const bad = ctxFor([tokenOk, asksOnce()]);
  await assert.rejects(bad.callTool("gmail_get_thread", { threadId: "t1" }, { canElicit: true, elicit: async () => ({ action: "accept", content: { approval_choice: "ALLOW_EVERYTHING" } }) }), { code: "INVALID_CONFIRMATION_ANSWER" });
  assert.equal(mcpCalls(bad).length, 1);

  // Decline is passed back as decline (no content).
  const dec = ctxFor([tokenOk, google((rpc) => (rpc.params.inputResponses ? { isError: true, content: [{ type: "text", text: "Denied by user" }] } : FORM))]);
  await assert.rejects(dec.callTool("gmail_get_thread", { threadId: "t1" }, { canElicit: true, elicit: async () => ({ action: "decline" }) }), { code: "TOOL_ERROR" });
  assert.deepEqual(mcpCalls(dec)[1].json.params.inputResponses, { approval_choice: { action: "decline" } });

  // A non-form request (e.g. a URL) is not passed on.
  const url = ctxFor([tokenOk, google(() => ({ ...FORM, inputRequests: { k: { method: "elicitation/create", params: { mode: "url", url: "https://example.com", message: "go" } } } }))]);
  await assert.rejects(url.callTool("gmail_get_thread", { threadId: "t1" }, { canElicit: true, elicit: async () => assert.fail("must not ask") }), { code: "UNSUPPORTED_CONFIRMATION" });
});

test("stdio: a client that declared elicitation gets Google's form as elicitation/create; one that did not gets CONFIRMATION_NEEDED", async () => {
  async function session(capabilities, answer) {
    const c = ctxFor([tokenOk, asksOnce({ id: "t1" })]);
    const input = new PassThrough(), output = new PassThrough();
    serveStdio({ info: { name: "google", version: "t" }, listTools: c.listTools, callTool: c.callTool, confirmTimeoutMs: 5000 }, { input, output });
    const lines = createInterface({ input: output });
    const msgs = [];
    const waitFor = (pred) => new Promise((resolve) => {
      const hit = msgs.find(pred); if (hit) return resolve(hit);
      const on = (l) => { const m = JSON.parse(l); msgs.push(m); if (pred(m)) { lines.off("line", on); resolve(m); } };
      lines.on("line", on);
    });
    const send = (m) => input.write(JSON.stringify(m) + "\n");
    send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities } });
    await waitFor((m) => m.id === 1);
    send({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "gmail_get_thread", arguments: { threadId: "t1" } } });
    const first = await waitFor((m) => m.id === 2 || m.method === "elicitation/create");
    let req = null;
    if (first.method) { req = first; send({ jsonrpc: "2.0", id: req.id, result: answer }); }
    const done = await waitFor((m) => m.id === 2);
    return { req, done, c };
  }
  const yes = await session({ elicitation: { form: {} } }, { action: "accept", content: { approval_choice: "ALLOW_ONCE" } });
  assert.equal(yes.req.params.mode, "form");
  assert.match(yes.req.params.message, /^Google gmail asks before gmail_get_thread runs: This agent wants/);
  assert.deepEqual(yes.req.params.requestedSchema, FORM.inputRequests.approval_choice.params.requestedSchema);
  assert.equal(parse(yes.done).ok, true);

  const old = await session({ elicitation: {} }, { action: "accept", content: { approval_choice: "ALLOW_ONCE" } });
  assert.equal(old.req.params.mode, undefined, "older clients get no mode field");

  const none = await session({}, null);
  assert.equal(none.req, null);
  assert.equal(none.done.result.isError, true);
  assert.deepEqual(none.done.result.content.map((b) => b.type), ["text"]);
  assert.equal(parse(none.done).error.code, "CONFIRMATION_NEEDED");
});

// ------------------------------------------------------------------------------------------------ grant

test("grant: shows Google's form, sends exactly the typed choice (or cancel), finds harmless targets, never prints the data", async () => {
  const PRIVATE = "PRIVATE-SUBJECT-LINE";
  const c = ctxFor([tokenOk, google((rpc) => {
    const n = rpc.params.name;
    if (!rpc.params.inputResponses && (n === "search_threads" || n === "get_thread")) return FORM;
    if (rpc.params.inputResponses && rpc.params.inputResponses.approval_choice.action !== "accept") return { isError: true, content: [{ type: "text", text: "The user did not allow this." }] };
    if (n === "search_threads") return ok({ threads: [{ id: "th-9", messages: [{ id: "m-9", subject: PRIVATE }] }] });
    if (n === "get_thread") return ok({ id: "th-9", messages: [{ id: "m-9", snippet: PRIVATE }] });
    if (n === "get_message") return ok({ id: "m-9", subject: PRIVATE });
    return ok({});
  })]);
  const answers = ["9", "2", "c"]; // an invalid choice, then "Always allow this tool", then cancel
  const printed = [];
  const available = c.tools.filter((t) => t.kind === "read").map((t) => t.name);
  const { steps } = await runGrant({ ctx: c.ctx, callTool: c.callTool, available, requested: ["gmail_get_thread", "gmail_get_message"], prompt: async () => answers.shift(), print: (s) => printed.push(s) });

  assert.deepEqual(steps.map((s) => [s.tool, !!s.helper, s.asked, s.result]), [
    ["gmail_search_threads", true, true, "ok"], ["gmail_get_thread", false, true, "error"], ["gmail_get_message", false, false, "ok"],
  ]);
  const calls = mcpCalls(c).map((x) => x.json.params);
  assert.deepEqual(calls[0].arguments, { pageSize: 1, view: "THREAD_VIEW_METADATA_ONLY" });
  assert.deepEqual(calls[1].inputResponses, { approval_choice: { action: "accept", content: { approval_choice: "ALLOW_TOOL_ALWAYS" } } });
  assert.deepEqual(calls[2].arguments, { threadId: "th-9", messageFormat: "METADATA_ONLY" });
  assert.deepEqual(calls[3].inputResponses, { approval_choice: { action: "cancel" } });
  assert.deepEqual(calls[4].arguments, { messageId: "m-9", messageFormat: "METADATA_ONLY" });
  const out = printed.join("\n");
  assert.match(out, /This agent wants to read an email/);
  assert.match(out, /2\) Always allow this tool/);
  assert.doesNotMatch(out, new RegExp(PRIVATE), "grant never prints what the calls read");
  assert.doesNotMatch(out, /th-9|m-9/);
});

test("grant: steps are ordered with helpers added; unknown tools and missing targets are skipped, not guessed", async () => {
  assert.deepEqual(grantSteps(["drive_read_file_content"], ["drive_list_recent_files", "drive_read_file_content"]), [{ name: "drive_list_recent_files", helper: true }, { name: "drive_read_file_content", helper: false }]);
  const c = ctxFor([tokenOk, google(() => ok({ drafts: [] }))]);
  const { steps } = await runGrant({ ctx: c.ctx, callTool: c.callTool, available: ["gmail_list_drafts", "gmail_get_draft"], requested: ["gmail_get_draft"], prompt: async () => assert.fail("no form"), print: () => {} });
  assert.deepEqual(steps.map((s) => [s.tool, s.result]), [["gmail_list_drafts", "ok"], ["gmail_get_draft", "skipped"]]);
  await assert.rejects(runGrant({ ctx: c.ctx, callTool: c.callTool, available: ["gmail_list_drafts"], requested: ["gmail_send_message"], prompt: async () => "", print: () => {} }), { code: "UNKNOWN_TOOL" });
});

// ------------------------------------------------------------------------------------------------ schema drift + no REST

test("schema-check diff: added, removed and changed tools are reported, and changes to exposed tools are flagged", () => {
  const live = SNAPSHOT.servers.gmail.tools.filter((t) => t.name !== "list_labels").map((t) => ({ ...t, outputSchema: undefined }));
  const getThread = live.find((t) => t.name === "get_thread");
  getThread.inputSchema = { ...getThread.inputSchema, properties: { ...getThread.inputSchema.properties, newField: { type: "string" } } };
  live.push({ name: "send_message", description: "Send", inputSchema: { type: "object" }, annotations: {} });
  const d = diffModule("gmail", live);
  assert.deepEqual(d.added, ["send_message"]);
  assert.deepEqual(d.removed, ["list_labels"]);
  assert.ok(d.changed.find((x) => x.name === "get_thread").fields.includes("inputSchema"));
  assert.ok(d.exposed_affected.includes("gmail_list_labels") && d.exposed_affected.includes("gmail_get_thread"));
});

test("hosts: Google's MCP servers and OAuth endpoints only; the REST hosts appear in server/rest.mjs alone", () => {
  const dir = new URL("../server/", import.meta.url);
  const files = [...readdirSync(dir).filter((f) => f.endsWith(".mjs")).map((f) => new URL(f, dir)), ...readdirSync(new URL("tools/", dir)).filter((f) => f.endsWith(".mjs")).map((f) => new URL(`tools/${f}`, dir))];
  const hosts = new Set();
  for (const f of files) {
    const found = [...readFileSync(f, "utf8").matchAll(/https:\/\/([a-z0-9.-]+\.(?:googleapis|google)\.com)/g)].map((m) => m[1]);
    if (f.pathname.endsWith("/server/rest.mjs")) { assert.deepEqual([...new Set(found)].sort(), ["gmail.googleapis.com", "www.googleapis.com"]); continue; }
    for (const h of found) hosts.add(h);
  }
  assert.deepEqual([...hosts].sort(), ["accounts.google.com", "calendarmcp.googleapis.com", "drivemcp.googleapis.com", "gmailmcp.googleapis.com", "oauth2.googleapis.com", "openidconnect.googleapis.com", "www.googleapis.com",
    // only as the refused-scope guard constant (google_auth.test.mjs checks that it appears nowhere else)
    "mail.google.com"].sort());
});

// ------------------------------------------------------------------------------------------------ B3: write + confirm

test("B3 classes: no Google tool is hidden; calendar create/update/delete/respond are confirm (whole tool); read-only drops every write", () => {
  assert.deepEqual(Object.keys(CLASSES.hidden), ["drive_download_file_content"], "only the tool drive_save_file replaces is hidden");
  for (const n of ["calendar_create_event", "calendar_update_event", "calendar_delete_event", "calendar_respond_to_event"]) assert.ok(CLASSES.confirm.includes(n), n);
  for (const n of ["gmail_trash_thread", "gmail_trash_message", "gmail_mark_thread_spam", "gmail_mark_message_spam", "gmail_apply_sensitive_thread_label", "gmail_apply_sensitive_message_label", "drive_upload_file_revision", "drive_create_file", "drive_copy_file"]) assert.ok(CLASSES.confirm.includes(n), n);
  for (const n of CLASSES.confirm) assert.match(ALL_TOOLS.find((t) => t.name === n).description, /Ask the human first/, n);
  const ro = filterTools(ALL_TOOLS, resolveConfig({ GOOGLE_READONLY: "1" })).map((t) => t.name);
  assert.ok([...CLASSES.write, ...CLASSES.confirm].every((n) => !ro.includes(n)));
  assert.ok(CLASSES.read.every((n) => ro.includes(n)));
  // With the REST switch off (default): no send, no draft edit or delete, no Drive share/move/trash, no permanent delete.
  const all = filterTools(ALL_TOOLS, resolveConfig({})).map((t) => t.name).join(" "); // REST switch off (default)
  assert.doesNotMatch(all, /send|update_draft|delete_draft|share|move_file|trash_file|delete_message|delete_thread/);
});

test("the Claude Code hook asks before exactly the confirm-class tools, and its output is a fixed, valid 'ask'", () => {
  const hooks = JSON.parse(readFileSync(new URL("../hooks/hooks.json", import.meta.url), "utf8"));
  const [entry] = hooks.hooks.PreToolUse;
  const re = new RegExp(entry.matcher);
  for (const n of CLASSES.confirm) {
    assert.ok(re.test(`mcp__plugin_google_google__${n}`), n);
    assert.ok(re.test(`mcp__google__${n}`), n);
  }
  for (const t of ALL_TOOLS.filter((x) => !CLASSES.confirm.includes(x.name))) assert.equal(re.test(`mcp__plugin_google_google__${t.name}`), false, t.name);
  assert.equal(re.test("mcp__plugin_google_google__calendar_create_event_x"), false);
  const cmd = entry.hooks[0].command;
  const m = cmd.match(/^printf '%s' '([^']*)'$/);
  assert.ok(m, "the hook is a fixed printf (nothing to fail open)");
  const out = JSON.parse(m[1]);
  assert.equal(out.hookSpecificOutput.hookEventName, "PreToolUse");
  assert.equal(out.hookSpecificOutput.permissionDecision, "ask");
});

test("write-class label tools refuse Trash and Spam (the confirm tools exist for that) before calling Google", async () => {
  const c = ctxFor([tokenOk, google(() => ok({ id: "m1" }))]);
  for (const [tool, args] of [["gmail_label_message", { messageId: "m1", labelIds: ["trash"] }], ["gmail_label_thread", { threadId: "t1", labelIds: ["STARRED", "SPAM"] }], ["gmail_update_message_labels", { messageId: "m1", addLabelIds: [" Trash "] }]]) {
    await assert.rejects(c.callTool(tool, args), (e) => e.code === "NEEDS_CONFIRM_TOOL" && /ask the human first/.test(e.hint));
  }
  assert.equal(mcpCalls(c).length, 0);
  const r = await c.callTool("gmail_update_message_labels", { messageId: "m1", removeLabelIds: ["INBOX", "TRASH"], addLabelIds: ["STARRED"] });
  assert.equal(r.untrusted, true);
  assert.equal(mcpCalls(c)[0].json.params.name, "update_message_labels");
});

test("live finding: Google's 'requires user confirmation, which this client does not support' is CONFIRMATION_UNSUPPORTED, not a grant prompt", async () => {
  const c = ctxFor([tokenOk, google(() => ({ isError: true, content: [{ type: "text", text: "Action could not be completed. This action requires user confirmation, which this client does not support. Use a client that supports form elicitation to perform this action." }] }))]);
  await assert.rejects(c.callTool("drive_save_file", { fileId: "f" }), (e) => e.code === "CONFIRMATION_UNSUPPORTED" && !/grant drive/.test(e.hint) && /drive_read_file_content/.test(e.hint));
});

test("grant: Ctrl+C at a prompt stops the run instead of going on to the next tool", async () => {
  const FORM1 = { resultType: "input_required", requestState: "s", inputRequests: { k: { method: "elicitation/create", params: { mode: "form", message: "Allow?", requestedSchema: { type: "object", properties: { k: { type: "string", enum: ["ALLOW_ONCE"] } } } } } } };
  const c = ctxFor([tokenOk, google(() => FORM1)]);
  const abort = Object.assign(new Error("Aborted with Ctrl+C"), { code: "ABORT_ERR" });
  const { steps } = await runGrant({ ctx: c.ctx, callTool: c.callTool, available: ["gmail_list_labels", "drive_search_files"], prompt: async () => { throw abort; }, print: () => {} });
  assert.deepEqual(steps.map((s) => [s.tool, s.result]), [["gmail_list_labels", "stopped"]]);
});

test("GOOGLE_TOOLS_DENY removes the plugin's own local tools too: absent from tools/list, and a call is refused", async () => {
  const c = ctxFor([tokenOk], { extraEnv: { GOOGLE_TOOLS_DENY: "google_sign_in,google_sign_out,gmail_identities" } });
  const listed = c.listTools().map((t) => t.name);
  for (const n of ["google_sign_in", "google_sign_out", "gmail_identities"]) assert.ok(!listed.includes(n), n);
  assert.ok(listed.includes("google_auth_status"));
  assert.equal(listed.length, ctxFor([tokenOk]).listTools().length - 3);
  await assert.rejects(c.callTool("google_sign_out", {}), { code: "UNKNOWN_TOOL" });
  await assert.rejects(c.callTool("google_sign_in", {}), { code: "UNKNOWN_TOOL" });
});

test("grant --fresh: list tools read a larger page; per-item tools skip already-allowed items until Google asks", async () => {
  // Google asks only for message m3 and file f2 (the others count as already allowed).
  const FORMX = (tool) => ({ resultType: "input_required", requestState: "s", inputRequests: { approval_choice: { method: "elicitation/create", params: { mode: "form", message: `Allow ${tool}?`,
    requestedSchema: { type: "object", properties: { approval_choice: { type: "string", enum: ["ALLOW_ONCE", "ALLOW_RESOURCE_ALWAYS", "ALLOW_TOOL_ALWAYS", "DENY_ONCE"], enumNames: ["Allow once", "Always allow for this email", "Always allow this tool", "Don't allow"] } } } } } } });
  const c = ctxFor([tokenOk, google((rpc) => {
    const { name, arguments: a, inputResponses } = rpc.params;
    if (name === "search_threads") return ok({ threads: [1, 2, 3, 4].map((i) => ({ id: `t${i}`, messages: [{ id: `m${i}` }] })) });
    if (name === "list_recent_files") return ok({ files: [{ id: "f1" }, { id: "f2" }, { id: "f3" }] });
    if (name === "get_message" && a.messageId === "m3" && !inputResponses) return FORMX(name);
    if (name === "get_file_metadata" && a.fileId === "f2" && !inputResponses) return FORMX(name);
    return ok({ id: "x" });
  })]);
  const printed = [];
  const answers = ["3", "3"];
  const available = c.tools.filter((t) => t.kind === "read").map((t) => t.name);
  const { steps } = await runGrant({ ctx: c.ctx, callTool: c.callTool, available, requested: ["gmail_get_message", "drive_get_file_metadata"], fresh: true, prompt: async () => answers.shift(), print: (s) => printed.push(s) });
  assert.deepEqual(steps.map((s) => [s.tool, s.result, s.asked, s.tried]), [
    ["gmail_search_threads", "ok", false, undefined], ["gmail_get_message", "ok", true, 3],
    ["drive_list_recent_files", "ok", false, undefined], ["drive_get_file_metadata", "ok", true, 2],
  ]);
  const calls = mcpCalls(c).map((x) => x.json.params);
  assert.equal(calls.find((p) => p.name === "search_threads").arguments.pageSize, 25);
  assert.equal(calls.find((p) => p.name === "list_recent_files").arguments.pageSize, 25);
  assert.deepEqual(calls.filter((p) => p.name === "get_message" && !p.inputResponses).map((p) => p.arguments.messageId), ["m1", "m2", "m3"]);
  assert.deepEqual(calls.find((p) => p.name === "get_message" && p.inputResponses).inputResponses, { approval_choice: { action: "accept", content: { approval_choice: "ALLOW_TOOL_ALWAYS" } } });
  const out = printed.join("\n");
  assert.match(out, /Note: option 3 \("Always allow this tool"\) covers every item for this tool/);
  assert.match(out, /cannot revoke it yourself/);
  assert.doesNotMatch(out, /\bm[1-4]\b|\bf[1-3]\b/, "ids are not printed");

  // Nothing asks anywhere: the run says so instead of claiming a grant.
  const quiet = ctxFor([tokenOk, google((rpc) => (rpc.params.name === "list_recent_files" ? ok({ files: [{ id: "f1" }, { id: "f2" }] }) : ok({})))]);
  const lines = [];
  const r2 = await runGrant({ ctx: quiet.ctx, callTool: quiet.callTool, available: ["drive_list_recent_files", "drive_get_file_permissions"], requested: ["drive_get_file_permissions"], fresh: true, prompt: async () => assert.fail("no form"), print: (s) => lines.push(s) });
  assert.deepEqual(r2.steps.map((s) => [s.tool, s.asked, s.tried]), [["drive_list_recent_files", false, undefined], ["drive_get_file_permissions", false, 2]]);
  assert.match(lines.join("\n"), /asked about none of the 2 items tried/);
});
