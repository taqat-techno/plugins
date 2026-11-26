// Milestone 1: one Google sign-in for Gmail, Calendar and Drive, the token cache, status and the error contract. No
// network: Google is a fake fetch, and the browser is a function that calls the plugin's own loopback listener.
import test from "node:test";
import assert from "node:assert/strict";
import { get } from "node:http";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { FORBIDDEN_SCOPE, MODULES, SCOPES, moduleScopes, resolveConfig } from "../server/config.mjs";
import { createAuth, scopeString } from "../server/auth.mjs";
import { createHandler } from "../server/mcp.mjs";
import { ALL_TOOLS } from "../server/tools/index.mjs";
import { createContext } from "../server/context.mjs";
import { CLIENT_ID, FULL_GRANT, NOW, READ_GRANT, SECRET, TOKEN, USERINFO, clientFile, ctxFor, env, fakeFetch, home, idToken, json, seedCache, userinfoOk } from "./_helpers.mjs";

const cache = (h) => JSON.parse(readFileSync(join(h, "token-cache.json"), "utf8"));
const hit = (url) => new Promise((ok, bad) => get(url, (r) => { r.resume(); r.on("end", ok); }).on("error", bad));
const until = async (fn, ms = 3000) => { const end = Date.now() + ms; for (;;) { const v = await fn(); if (v) return v; if (Date.now() > end) throw new Error("timed out"); await new Promise((r) => setTimeout(r, 20)); } };
const subsets = (xs) => xs.reduce((acc, x) => acc.concat(acc.map((s) => [...s, x])), [[]]).filter((s) => s.length);

/** A browser stand-in: answers the authorize URL by calling the loopback redirect, like Google would after consent. */
const browser = (seen, answer = (u) => ({ code: "auth-code-1", state: u.searchParams.get("state") })) => (url) => {
  const u = new URL(url);
  seen.url = u;
  const q = new URLSearchParams(answer(u));
  setTimeout(() => hit(`${u.searchParams.get("redirect_uri")}/?${q}`).catch(() => {}), 10);
  return true;
};

async function signIn({ extraEnv = {}, grant, tokenBody, answer, seed = false } = {}) {
  const seen = {};
  const scope = (grant ?? (extraEnv.GOOGLE_READONLY ? READ_GRANT : FULL_GRANT)).join(" ");
  const reply = tokenBody ?? { access_token: "at-1", refresh_token: "rt-new", expires_in: 3599, scope, id_token: idToken(), token_type: "Bearer" };
  const c = ctxFor([[TOKEN, () => json(reply)], userinfoOk], { extraEnv, seed, deps: { open: browser(seen, answer) } });
  const started = await c.callTool("google_sign_in", {});
  const s = await until(async () => { const st = await c.ctx.auth.status({ verify: false }); return st.sign_in?.state !== "waiting" ? st : null; });
  return { c, seen, started, s };
}

// ---------------------------------------------------------------- scopes

test("scopes: every module/mode combination requests exactly its modules' scopes plus openid/email, never full mailbox", () => {
  const expected = {
    gmail: { false: [SCOPES.gmailModify], true: [SCOPES.gmailReadonly] },
    calendar: { false: [SCOPES.calendarEvents, SCOPES.calendarListReadonly], true: [SCOPES.calendarEventsReadonly, SCOPES.calendarListReadonly] },
    drive: { false: [SCOPES.drive], true: [SCOPES.driveReadonly] },
  };
  for (const mods of subsets(MODULES)) {
    for (const ro of [false, true]) {
      const cfg = resolveConfig({ GOOGLE_PLUGIN_HOME: home(), GOOGLE_MODULES: mods.join(","), ...(ro ? { GOOGLE_READONLY: "true" } : {}) });
      const want = ["openid", "email", ...new Set(mods.flatMap((m) => expected[m][ro]))];
      assert.deepEqual([...cfg.scopes].sort(), [...new Set(want)].sort(), `${mods} ro=${ro}`);
      const s = createAuth(cfg)._scope;
      assert.ok(!s.includes("mail.google.com"), `${mods} ro=${ro}: https://mail.google.com/ is never requested`);
      if (ro) for (const w of [SCOPES.gmailModify, SCOPES.calendarEvents, SCOPES.drive]) assert.ok(!s.split(" ").includes(w), `${mods}: read-only never asks for ${w}`);
    }
  }
  assert.deepEqual(resolveConfig({ GOOGLE_PLUGIN_HOME: home() }).modules, MODULES, "empty = all three modules");
  assert.deepEqual(resolveConfig({ GOOGLE_PLUGIN_HOME: home(), GOOGLE_PLUGIN_MODULES: "drive", GOOGLE_MODULES: "gmail" }).modules, ["drive"], "Claude Code setting wins");
  assert.throws(() => scopeString([FORBIDDEN_SCOPE]), (e) => e.code === "SCOPE_FORBIDDEN");
  assert.throws(() => createAuth({ ...resolveConfig({ GOOGLE_PLUGIN_HOME: home() }), scopes: [SCOPES.gmailModify, FORBIDDEN_SCOPE] }), (e) => e.code === "SCOPE_FORBIDDEN");
});

test("the browser request carries the configured scopes (default: all three modules)", async () => {
  for (const extraEnv of [{}, { GOOGLE_READONLY: "1" }, { GOOGLE_MODULES: "calendar" }]) {
    const { seen, c } = await signIn({ extraEnv });
    assert.deepEqual(seen.url.searchParams.get("scope").split(" ").sort(), [...c.ctx.cfg.scopes].sort());
    assert.ok(!seen.url.searchParams.get("scope").includes("mail.google.com"));
  }
});

test("the full-mailbox scope string appears in the server only as the guard constant", () => {
  const dir = new URL("../server/", import.meta.url);
  const files = ["auth.mjs", "config.mjs", "cli.mjs", "context.mjs", "index.mjs", "mcp.mjs", "util.mjs", "tools/auth.mjs", "tools/index.mjs"];
  const lines = files.flatMap((f) => readFileSync(new URL(f, dir), "utf8").split("\n").filter((l) => l.includes("mail.google.com")).map((l) => l.trim()));
  // Allowed: the constant itself, comments, and messages naming it in parentheses "(https://mail.google.com/)".
  const other = lines.filter((l) => !l.startsWith("//") && !l.startsWith("*") && !l.startsWith("/**")
    && !l.startsWith('export const FORBIDDEN_SCOPE = "https://mail.google.com/";') && !/\(https:\/\/mail\.google\.com\/\)/.test(l));
  assert.deepEqual(other, [], "only the FORBIDDEN_SCOPE constant and messages that name it may mention it");
  assert.equal(lines.filter((l) => l.startsWith("export const FORBIDDEN_SCOPE")).length, 1);
});

// ---------------------------------------------------------------- sign-in

test("sign-in: loopback on 127.0.0.1 + PKCE S256, endpoints fixed (not taken from the client file), token cached atomically", async () => {
  const { c, seen, started, s } = await signIn();
  assert.equal(started.status, "pending");
  assert.equal(seen.url.origin + seen.url.pathname, "https://accounts.google.com/o/oauth2/v2/auth", "a client file's auth_uri is ignored");
  const q = seen.url.searchParams;
  assert.match(q.get("redirect_uri"), /^http:\/\/127\.0\.0\.1:\d+$/);
  assert.equal(q.get("client_id"), CLIENT_ID);
  assert.equal(q.get("code_challenge_method"), "S256");
  assert.match(q.get("code_challenge"), /^[A-Za-z0-9_-]{43}$/);
  assert.equal(q.get("response_type"), "code");
  assert.equal(q.get("prompt"), "consent");
  assert.ok(!seen.url.href.includes(SECRET), "the client secret is never put in the browser URL");

  assert.equal(s.sign_in.state, "done", JSON.stringify(s.sign_in));
  assert.equal(s.signed_in, true);
  assert.equal(s.account, "owner@example.com", "the address comes from the ID token");
  assert.deepEqual(s.modules, { gmail: { usable: true }, calendar: { usable: true }, drive: { usable: true } });
  assert.deepEqual(s.scopes_missing, []);
  const ex = c.fetch.calls.find((x) => TOKEN.test(`${x.method} ${x.url}`));
  assert.equal(ex.url, "https://oauth2.googleapis.com/token", "a client file's token_uri is ignored");
  assert.equal(ex.form.get("grant_type"), "authorization_code");
  assert.equal(ex.form.get("code"), "auth-code-1");
  assert.equal(ex.form.get("redirect_uri"), q.get("redirect_uri"));
  assert.match(ex.form.get("code_verifier"), /^[A-Za-z0-9_-]{43}$/);
  assert.equal(ex.form.get("client_secret"), SECRET);

  const saved = cache(c.home);
  assert.equal(saved.refresh_token, "rt-new");
  assert.deepEqual(saved.scopes_granted, FULL_GRANT);
  assert.equal(saved.obtained_at, new Date(NOW).toISOString());
  assert.equal(saved.access_token, undefined, "the access token is never written to disk");
  assert.deepEqual(readdirSync(c.home).filter((f) => f.endsWith(".tmp")), [], "no temp file is left behind");
});

test("sign-in: a partial grant keeps the sign-in and reports which modules are usable and what is missing", async () => {
  const grant = ["openid", SCOPES.gmailModify, SCOPES.calendarEvents]; // Drive and the calendar list left unticked
  const { c, s } = await signIn({ grant });
  assert.equal(s.signed_in, true);
  assert.deepEqual(s.modules.gmail, { usable: true });
  assert.deepEqual(s.modules.calendar, { usable: false, missing_scopes: [SCOPES.calendarListReadonly] });
  assert.deepEqual(s.modules.drive, { usable: false, missing_scopes: [SCOPES.drive] });
  assert.deepEqual(s.scopes_missing.sort(), [SCOPES.calendarListReadonly, SCOPES.drive].sort());
  assert.match(s.hint, /tick every box/);
  const routes = fakeFetch([[TOKEN, () => json({ access_token: "at-2", expires_in: 3599 })]]);
  const a = createAuth(c.ctx.cfg, { fetch: routes, now: () => NOW });
  assert.equal(await a.getAccessToken("gmail"), "at-2");
  await assert.rejects(a.getAccessToken("drive"), (e) => e.code === "SCOPE_NOT_GRANTED" && /do not retry/i.test(e.hint));
});

test("sign-in: nothing granted for any module is SCOPE_NOT_GRANTED and nothing is saved", async () => {
  const { c, s } = await signIn({ grant: ["openid", "https://www.googleapis.com/auth/userinfo.email"] });
  assert.equal(s.sign_in.state, "failed");
  assert.equal(s.sign_in.error.code, "SCOPE_NOT_GRANTED");
  assert.equal(existsSync(join(c.home, "token-cache.json")), false);
});

test("sign-in: a client that already holds full mailbox access is refused (SCOPE_TOO_BROAD)", async () => {
  const { s } = await signIn({ grant: [...FULL_GRANT, FORBIDDEN_SCOPE] });
  assert.equal(s.sign_in.error.code, "SCOPE_TOO_BROAD");
});

test("sign-in: Cancel on Google's page is SIGN_IN_DECLINED; a forged state is refused", async () => {
  const declined = await signIn({ answer: (u) => ({ error: "access_denied", state: u.searchParams.get("state") }) });
  assert.equal(declined.s.sign_in.error.code, "SIGN_IN_DECLINED");
  const forged = await signIn({ answer: () => ({ code: "x", state: "not-the-state" }) });
  assert.equal(forged.s.sign_in.error.code, "AUTH_FAILED");
  assert.equal(forged.c.fetch.calls.length, 0, "no code is exchanged after a state mismatch");
});

// ---------------------------------------------------------------- client file and modules config

test("client file: missing, unreadable, Web-type and mismatching ids are distinct, secret-free errors", async () => {
  const h = home();
  const run = async (e) => {
    const c = createContext(e, { fetch: fakeFetch([]), open: () => true });
    const r = await createHandler({ info: {}, ...c })({ method: "tools/call", params: { name: "google_sign_in", arguments: {} } });
    return JSON.parse(r.content[0].text);
  };
  assert.equal((await run({ GOOGLE_PLUGIN_HOME: h })).error.code, "NOT_CONFIGURED");
  assert.equal((await run({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_SECRET_FILE: join(h, "nope.json") })).error.code, "NOT_CONFIGURED");
  const web = clientFile(h, { web: { client_id: CLIENT_ID, client_secret: SECRET } });
  const w = await run({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_SECRET_FILE: web });
  assert.equal(w.error.code, "CLIENT_TYPE_WRONG");
  const ok = clientFile(h);
  const mm = await run({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_SECRET_FILE: ok, GOOGLE_PLUGIN_CLIENT_ID: "other.apps.googleusercontent.com" });
  assert.equal(mm.error.code, "CLIENT_MISMATCH");
  for (const r of [w, mm]) assert.ok(!JSON.stringify(r).includes(SECRET), "the secret never appears in an error");
  const none = await run({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_SECRET_FILE: ok, GOOGLE_MODULES: "nothing-real" });
  assert.equal(none.error.code, "NOT_CONFIGURED");
  assert.match(none.error.message, /No module/);
  // A plain GOOGLE_CLIENT_ID from another project's environment is ignored (no false CLIENT_MISMATCH).
  assert.equal(resolveConfig({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_ID: "unrelated" }).clientId, "");
  // An unexpanded ${user_config...} placeholder counts as unset (falls back to the plain variable).
  assert.equal(resolveConfig({ GOOGLE_PLUGIN_HOME: h, GOOGLE_PLUGIN_CLIENT_SECRET_FILE: "${user_config.google_client_secret_file}", GOOGLE_CLIENT_SECRET_FILE: ok }).clientSecretFile, ok);
});

// ---------------------------------------------------------------- refresh, expiry, write-back

test("refresh: AUTH_REQUIRED without a sign-in, AUTH_EXPIRED on invalid_grant, and the two are distinct", async () => {
  const none = ctxFor([], { seed: false });
  await assert.rejects(none.ctx.auth.getAccessToken(), (e) => e.code === "AUTH_REQUIRED" && /sign in/i.test(e.hint));
  const dead = ctxFor([[TOKEN, () => json({ error: "invalid_grant", error_description: "Token has been expired or revoked." }, 400)]]);
  await assert.rejects(dead.ctx.auth.getAccessToken(), (e) => e.code === "AUTH_EXPIRED" && /do not retry/i.test(e.hint));
  assert.equal(cache(dead.home).last_refresh_error.code, "AUTH_EXPIRED", "the failure is recorded for an offline status");
  const other = ctxFor([], { seed: { client_id: "someone-else.apps.googleusercontent.com" } });
  await assert.rejects(other.ctx.auth.getAccessToken(), (e) => e.code === "AUTH_REQUIRED", "a sign-in for another client is not used");
  const off = ctxFor([], { extraEnv: { GOOGLE_MODULES: "gmail" } });
  await assert.rejects(off.ctx.auth.getAccessToken("drive"), (e) => e.code === "MODULE_DISABLED");
});

test("refresh: a rotated refresh token is written back atomically; a token another process saved meanwhile is retried once", async () => {
  const c = ctxFor([[TOKEN, () => json({ access_token: "at-2", refresh_token: "rt-rotated", expires_in: 3599, scope: FULL_GRANT.join(" ") })]]);
  assert.equal(await c.ctx.auth.getAccessToken(), "at-2");
  assert.equal(cache(c.home).refresh_token, "rt-rotated");
  assert.equal(cache(c.home).last_refresh_at, new Date(NOW).toISOString());
  assert.deepEqual(readdirSync(c.home).filter((f) => f.endsWith(".tmp")), []);
  assert.equal(await c.ctx.auth.getAccessToken("calendar"), "at-2", "a valid access token is reused from memory");
  assert.equal(c.fetch.calls.length, 1);

  const h = home();
  seedCache(h);
  let n = 0;
  const f = fakeFetch([[TOKEN, ({ body }) => {
    n++;
    const rt = new URLSearchParams(body).get("refresh_token");
    if (rt === "rt-1") { seedCache(h, { refresh_token: "rt-from-other-process" }); return json({ error: "invalid_grant" }, 400); }
    return json({ access_token: "at-3", expires_in: 3599 });
  }]]);
  const a = createAuth(resolveConfig(env(h)), { fetch: f, now: () => NOW });
  assert.equal(await a.getAccessToken(), "at-3");
  assert.equal(n, 2);
  assert.equal(cache(h).refresh_token, "rt-from-other-process", "Google sent no new token, so the newer one on file is kept");
});

test("read-only mode will not use a sign-in that can change data, and accepts a read-only one", async () => {
  const c = ctxFor([], { extraEnv: { GOOGLE_READONLY: "true" } });
  await assert.rejects(c.ctx.auth.getAccessToken(), (e) => e.code === "AUTH_REQUIRED");
  const s = await c.ctx.auth.status();
  assert.equal(s.signed_in, false);
  assert.equal(s.auth_error.code, "AUTH_REQUIRED");
  assert.equal(s.modules.drive.too_broad, true);
  assert.equal(c.fetch.calls.length, 0);
  const ro = ctxFor([[TOKEN, () => json({ access_token: "at-ro", expires_in: 3599 })]], { extraEnv: { GOOGLE_READONLY: "true" }, seed: { scopes_granted: READ_GRANT } });
  assert.equal(await ro.ctx.auth.getAccessToken("drive"), "at-ro");
});

// ---------------------------------------------------------------- status

test("status: account, modules, requested vs granted scopes, token age and last refresh; a live check by default; never a token", async () => {
  const c = ctxFor([[TOKEN, () => json({ access_token: "at-secret-1", expires_in: 3599, scope: FULL_GRANT.join(" ") })], userinfoOk]);
  const r = await createHandler({ info: {}, ...c })({ method: "tools/call", params: { name: "google_auth_status", arguments: {} } });
  assert.equal(r.isError, undefined);
  const s = JSON.parse(r.content[0].text);
  assert.equal(s.ok, true);
  assert.equal(s.signed_in, true);
  assert.equal(s.verified, true);
  assert.equal(s.account, "owner@example.com");
  assert.deepEqual(s.modules_enabled, MODULES);
  assert.deepEqual(Object.keys(s.modules), MODULES);
  assert.deepEqual(s.scopes_requested.sort(), [...c.ctx.cfg.scopes].sort());
  assert.deepEqual(s.scopes_granted, FULL_GRANT);
  assert.deepEqual(s.scopes_missing, [], "Google's userinfo.email for the requested 'email' is not reported missing");
  assert.equal(s.token_obtained_at, "2026-11-20T00:00:00.000Z");
  assert.equal(s.token_age_days, 5);
  assert.equal(s.last_refresh_at, new Date(NOW).toISOString());
  assert.equal(cache(c.home).last_refresh_at, new Date(NOW).toISOString(), "the live refresh time is saved");
  assert.match(s.note, /7 days/);
  const text = r.content[0].text;
  for (const secret of ["at-secret-1", "rt-1", SECRET]) assert.ok(!text.includes(secret), `status leaks ${secret}`);
  assert.ok(c.fetch.calls.some((x) => USERINFO.test(`${x.method} ${x.url}`)), "the live check reads the user info");
});

test("status: verify=false does not contact Google; a dead sign-in shows AUTH_EXPIRED and signed_in false", async () => {
  const quick = ctxFor([]);
  const q = await quick.callTool("google_auth_status", { verify: false });
  assert.equal(q.signed_in, true);
  assert.equal(q.verified, null);
  assert.equal(quick.fetch.calls.length, 0);

  const dead = ctxFor([[TOKEN, () => json({ error: "invalid_grant" }, 400)]]);
  const d = await dead.callTool("google_auth_status", {});
  assert.equal(d.signed_in, false);
  assert.equal(d.verified, false);
  assert.equal(d.auth_error.code, "AUTH_EXPIRED");
  assert.match(d.hint, /sign in again/i);
});

test("status: not configured is reported, not thrown", async () => {
  const c = createContext({ GOOGLE_PLUGIN_HOME: home() }, { fetch: fakeFetch([]) });
  const s = await c.callTool("google_auth_status", {});
  assert.equal(s.configured, false);
  assert.equal(s.client_error.code, "NOT_CONFIGURED");
  assert.match(s.hint, /GOOGLE_CLOUD_SETUP/);
});

test("sign-out deletes only the local cache", async () => {
  const c = ctxFor([]);
  const r = await c.callTool("google_sign_out", {});
  assert.equal(r.signed_out, true);
  assert.equal(existsSync(join(c.home, "token-cache.json")), false);
  assert.equal(c.fetch.calls.length, 0);
});

// ---------------------------------------------------------------- MCP contract

test("errors are text blocks only, shaped { ok:false, error:{ code, message } }", async () => {
  const c = ctxFor([[TOKEN, () => json({ error: "invalid_grant" }, 400)]]);
  const probe = async () => { await c.ctx.auth.getAccessToken("gmail"); return {}; };
  const r = await createHandler({ info: {}, listTools: c.listTools, callTool: (n, a) => (n === "probe" ? probe() : c.callTool(n, a)) })({ method: "tools/call", params: { name: "probe", arguments: {} } });
  assert.equal(r.isError, true);
  assert.ok(r.content.every((b) => b.type === "text"), "no image or other block in an error");
  assert.deepEqual(Object.keys(JSON.parse(r.content[0].text)), ["ok", "error"]);
  assert.equal(JSON.parse(r.content[0].text).error.code, "AUTH_EXPIRED");
  const unknown = await createHandler({ info: {}, ...c })({ method: "tools/call", params: { name: "nope", arguments: {} } });
  assert.equal(JSON.parse(unknown.content[0].text).error.code, "UNKNOWN_TOOL");
});

test("every tool description is at most 1024 characters, and data/tools.json matches the tools' classes", () => {
  for (const t of ALL_TOOLS) assert.ok(t.description.length <= 1024, `${t.name}: ${t.description.length} chars`);
  const data = JSON.parse(readFileSync(new URL("../data/tools.json", import.meta.url), "utf8"));
  const byClass = (k) => ALL_TOOLS.filter((t) => (k === "confirm" ? t.confirm : t.kind === k)).map((t) => t.name).sort();
  for (const k of ["read", "local", "write", "confirm"]) assert.deepEqual([...data[k]].sort(), byClass(k), k);
  assert.deepEqual(byClass("local"), ["gmail_identities", "google_auth_status", "google_sign_in", "google_sign_out"]);
  assert.ok(MODULES.every((m) => moduleScopes(m, false).length && moduleScopes(m, true).length));
});
