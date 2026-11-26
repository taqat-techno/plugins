// auth.mjs - Google sign-in for an installed ("Desktop app") OAuth client, with no dependencies.
//
// Flow: authorization code + PKCE (S256) with a loopback redirect to http://127.0.0.1:<free port>, the mechanism Google
// recommends for desktop apps. Google's device-code flow does not allow Gmail, Calendar or Drive scopes and the
// copy-paste (OOB) flow is no longer supported, so sign-in needs a browser on the machine that runs the plugin.
//
// One sign-in covers every enabled module (gmail, calendar, drive): all their scopes are requested at once. Google lets
// the human untick individual permissions, so each module's usability is worked out from the scopes actually granted.
//
// Each user brings their own Google Cloud client: the path to its downloaded client JSON (GOOGLE_CLIENT_SECRET_FILE).
// The file is read on each use and its contents are never returned, logged or put in an error. Only the client id and
// secret are taken from it: the endpoints are fixed here, so an edited file cannot send a code or token elsewhere.
//
// The refresh token is cached in <GOOGLE_PLUGIN_HOME>/token-cache.json (default ~/.google-plugin), written atomically
// (temp file + rename) because several processes (an agent, a bot, a scheduled check) may share it. The access token is
// kept in memory only. No token is ever returned to a caller or put in an error message.
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { FORBIDDEN_SCOPE, MODULE_SCOPES, NEEDS_CLIENT, moduleScopes } from "./config.mjs";
import { GoogleError, replaceFile } from "./util.mjs";

export const AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
export const TOKEN_URL = "https://oauth2.googleapis.com/token";
export const USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo";
const SIGN_IN_WINDOW_MS = 300_000;

const b64url = (buf) => buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const DAY = 86_400_000;

/** The scope string sent to Google. Refuses the full-mailbox scope by construction. */
export function scopeString(scopes) {
  const list = [...new Set(scopes)];
  if (list.some((s) => s === FORBIDDEN_SCOPE || s.startsWith(FORBIDDEN_SCOPE))) {
    throw new GoogleError("SCOPE_FORBIDDEN", "Refusing to request full mailbox access (https://mail.google.com/): it allows permanent delete.");
  }
  return list.join(" ");
}

export function openBrowser(url) {
  try {
    const p = process.platform;
    const [cmd, args] = p === "win32" ? ["rundll32", ["url.dll,FileProtocolHandler", url]]
      : p === "darwin" ? ["open", [url]] : ["xdg-open", [url]];
    const c = spawn(cmd, args, { stdio: "ignore", detached: true });
    c.on("error", () => {});
    c.unref();
    return true;
  } catch { return false; }
}

const EXPIRED_HINT = "Ask the human to sign in again (google_sign_in, or run: node server/cli.mjs sign-in). Do not retry this call in a loop: it will keep failing until they do.";
const REQUIRED_HINT = "Ask the human to sign in (google_sign_in, or run: node server/cli.mjs sign-in). Do not retry until they have.";

/** Maps Google's token-endpoint errors to a code. `refreshing`: a refresh-token grant (invalid_grant = the sign-in is dead). */
export function classifyTokenError(j, status, { refreshing = false } = {}) {
  const code = String(j?.error ?? "unknown");
  if (refreshing && code === "invalid_grant") {
    return new GoogleError("AUTH_EXPIRED", "The saved Google sign-in no longer works (expired or revoked). A human has to sign in again.", { hint: EXPIRED_HINT });
  }
  if (code === "invalid_client" || code === "unauthorized_client") {
    return new GoogleError("CLIENT_INVALID", `Google rejected the OAuth client (${code}).`, { hint: "Check that the client JSON file is the current one for a Desktop app client and that the client was not deleted. See docs/GOOGLE_CLOUD_SETUP.md." });
  }
  if (code === "admin_policy_enforced") {
    return new GoogleError("AUTH_BLOCKED", "A Google Workspace admin policy blocks this app's access.", { hint: "Only the account's admin can change this." });
  }
  return new GoogleError("AUTH_FAILED", `Google sign-in failed (${status ?? "?"}: ${code.slice(0, 60)}).`);
}

function idTokenEmail(idToken) {
  try {
    const c = JSON.parse(Buffer.from(String(idToken).split(".")[1], "base64url").toString("utf8"));
    return typeof c.email === "string" ? c.email : null;
  } catch { return null; }
}

export function createAuth(cfg, { fetch: fetchImpl = globalThis.fetch, open = openBrowser, now = () => Date.now() } = {}) {
  const cachePath = join(cfg.home, "token-cache.json");
  const scope = scopeString(cfg.scopes);
  let mem = { token: null, expiresAt: 0 };
  let pending = null; // one sign-in at a time: { state, started, url, message, error, account }

  // ---------------------------------------------------------------- client JSON (the user's own Google Cloud client)

  function loadClient() {
    if (!cfg.clientSecretFile) throw new GoogleError("NOT_CONFIGURED", NEEDS_CLIENT);
    let raw;
    try { raw = readFileSync(cfg.clientSecretFile, "utf8"); }
    catch { throw new GoogleError("NOT_CONFIGURED", "The Google client JSON file cannot be read.", { hint: "Check the path in the 'Google client JSON file' setting (GOOGLE_CLIENT_SECRET_FILE)." }); }
    let j;
    try { j = JSON.parse(raw.replace(/^﻿/, "")); } catch { throw new GoogleError("NOT_CONFIGURED", "The Google client JSON file is not valid JSON.", { hint: "Download it again from Google Cloud > Credentials (the download button of the Desktop client)." }); }
    if (!j?.installed && j?.web) {
      throw new GoogleError("CLIENT_TYPE_WRONG", "The client JSON is for a 'Web application' client; this plugin needs a 'Desktop app' client.", { hint: "Create an OAuth client of type Desktop app and download its JSON. See docs/GOOGLE_CLOUD_SETUP.md." });
    }
    const id = j?.installed?.client_id;
    if (typeof id !== "string" || !id.trim()) throw new GoogleError("NOT_CONFIGURED", "The Google client JSON file has no installed.client_id.", { hint: "Download the JSON of a Desktop app client from Google Cloud > Credentials." });
    if (cfg.clientId && cfg.clientId !== id.trim()) {
      throw new GoogleError("CLIENT_MISMATCH", "The client id setting does not match the client JSON file.", { hint: "Clear the client id setting (the file already holds it) or point the file setting at the right JSON." });
    }
    if (!cfg.modules.length) throw new GoogleError("NOT_CONFIGURED", "No module is enabled.", { hint: "Set the modules setting (GOOGLE_MODULES) to any of: gmail, calendar, drive; or leave it empty for all three." });
    const secret = typeof j.installed.client_secret === "string" && j.installed.client_secret.trim() ? j.installed.client_secret.trim() : undefined;
    return { id: id.trim(), secret };
  }

  // ---------------------------------------------------------------- token cache

  const readCache = () => {
    try {
      const c = JSON.parse(readFileSync(cachePath, "utf8"));
      return c && c.v === 1 && c.refresh_token ? c : null;
    } catch { return null; }
  };
  const writeCache = (c) => {
    mkdirSync(cfg.home, { recursive: true });
    const tmp = `${cachePath}.${process.pid}.${randomUUID()}.tmp`;
    writeFileSync(tmp, JSON.stringify(c, null, 2), { mode: 0o600 });
    replaceFile(tmp, cachePath);
  };
  const granted = (s) => String(s ?? "").split(/\s+/).filter(Boolean);
  const iso = (ms) => new Date(ms).toISOString();

  async function post(url, params) {
    let res;
    try {
      res = await fetchImpl(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams(params),
        signal: AbortSignal.timeout(cfg.timeoutMs),
      });
    } catch (e) {
      const timedOut = e?.name === "TimeoutError" || e?.name === "AbortError";
      throw new GoogleError(timedOut ? "TIMEOUT" : "NETWORK_ERROR", `Google ${timedOut ? "did not answer in time" : "could not be reached"}.`);
    }
    const j = await res.json().catch(() => ({}));
    return { res, j };
  }

  const tokenRequest = (client, params) => post(TOKEN_URL, { client_id: client.id, ...(client.secret ? { client_secret: client.secret } : {}), ...params });

  async function fetchUserinfo(token) {
    let res;
    try { res = await fetchImpl(USERINFO_URL, { headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }, signal: AbortSignal.timeout(cfg.timeoutMs) }); }
    catch (e) { throw new GoogleError(e?.name === "TimeoutError" ? "TIMEOUT" : "NETWORK_ERROR", "Google could not be reached."); }
    const j = await res.json().catch(() => ({}));
    if (res.status === 401) throw new GoogleError("AUTH_EXPIRED", "Google did not accept the sign-in.", { hint: EXPIRED_HINT });
    if (!res.ok) throw new GoogleError("GOOGLE_ERROR", `Google user-info request failed (${res.status}).`);
    return { email: typeof j.email === "string" ? j.email : null };
  }

  /** Per enabled module: usable, the scopes still missing, and whether the grant is broader than read-only mode allows. */
  function moduleState(list) {
    const out = {};
    for (const m of cfg.modules) {
      const missing = moduleScopes(m, cfg.readOnly).filter((s) => !list.includes(s));
      // In read-only mode, a sign-in that can change this module's data is not used (least privilege).
      const tooBroad = cfg.readOnly && MODULE_SCOPES[m].write.some((s) => list.includes(s) && !MODULE_SCOPES[m].read.includes(s));
      out[m] = { usable: !missing.length && !tooBroad, ...(missing.length ? { missing_scopes: missing } : {}), ...(tooBroad ? { too_broad: true } : {}) };
    }
    return out;
  }
  const usableModules = (list) => Object.entries(moduleState(list)).filter(([, s]) => s.usable).map(([m]) => m);

  function grantProblem(list) {
    if (list.includes(FORBIDDEN_SCOPE)) return new GoogleError("SCOPE_TOO_BROAD", "This client already holds full mailbox access (https://mail.google.com/) for the account; the plugin will not use such a sign-in.", { hint: "Remove the app's access in your Google Account > Security > Third-party connections, then sign in again." });
    if (!usableModules(list).length) {
      const broad = Object.values(moduleState(list)).some((s) => s.too_broad);
      return broad
        ? new GoogleError("AUTH_REQUIRED", "Read-only mode is on but the saved sign-in can change data. Sign in again for a read-only sign-in.", { hint: REQUIRED_HINT })
        : new GoogleError("SCOPE_NOT_GRANTED", "None of the enabled modules' permissions were granted at sign-in (their boxes on Google's consent page were left unticked).", { hint: "Sign in again and tick the permissions on Google's page." });
    }
    return null;
  }

  // ---------------------------------------------------------------- access token

  async function refresh(client, cache) {
    let used = cache;
    let { res, j } = await tokenRequest(client, { grant_type: "refresh_token", refresh_token: used.refresh_token });
    // Another process may have signed in again (new refresh token) between our read and our request.
    if ((!res.ok || !j.access_token) && j.error === "invalid_grant") {
      const latest = readCache();
      if (latest && latest.refresh_token !== used.refresh_token && latest.client_id === client.id) {
        used = latest;
        ({ res, j } = await tokenRequest(client, { grant_type: "refresh_token", refresh_token: used.refresh_token }));
      }
    }
    if (!res.ok || !j.access_token) {
      const err = classifyTokenError(j, res.status, { refreshing: true });
      try { writeCache({ ...used, last_refresh_error: { code: err.code, at: iso(now()) } }); } catch { /* status still reports the live error */ }
      throw err;
    }
    // Google normally keeps the same refresh token; if it sends a new one, write it back (atomically) at once.
    const next = { ...used, refresh_token: j.refresh_token || used.refresh_token, last_refresh_at: iso(now()) };
    if (j.scope) next.scopes_granted = granted(j.scope);
    delete next.last_refresh_error;
    writeCache(next);
    mem = { token: j.access_token, expiresAt: now() + (Number(j.expires_in) || 3600) * 1000 };
    return { token: mem.token, cache: next };
  }

  function usableCache(client, mod) {
    const cache = readCache();
    if (!cache || cache.client_id !== client.id) throw new GoogleError("AUTH_REQUIRED", "Not signed in to Google.", { hint: REQUIRED_HINT });
    const list = cache.scopes_granted ?? [];
    const problem = grantProblem(list);
    if (problem) throw problem.code === "SCOPE_NOT_GRANTED" ? new GoogleError("AUTH_REQUIRED", "The saved sign-in does not cover any enabled module.", { hint: REQUIRED_HINT }) : problem;
    if (mod) {
      const s = moduleState(list)[mod];
      if (!s) throw new GoogleError("MODULE_DISABLED", `The ${mod} module is not enabled.`, { hint: "Enable it in the modules setting (GOOGLE_MODULES), then sign in again." });
      if (!s.usable) throw new GoogleError(s.too_broad ? "AUTH_REQUIRED" : "SCOPE_NOT_GRANTED", s.too_broad ? `Read-only mode is on but the saved sign-in can change ${mod} data.` : `The ${mod} permission was not granted at sign-in.`, { hint: "Ask the human to sign in again and tick that permission on Google's page. Do not retry until they have." });
    }
    return cache;
  }

  /** An access token, refreshed when needed. `mod` (gmail | calendar | drive): also require that module to be usable. */
  async function getAccessToken(mod) {
    const client = loadClient();
    const cache = usableCache(client, mod);
    if (mem.token && now() < mem.expiresAt - 120_000) return mem.token;
    return (await refresh(client, cache)).token;
  }

  /** A live check: refresh the token now and read the account's user info with it. Records the time of the refresh. */
  async function verify() {
    const client = loadClient();
    const { token, cache } = await refresh(client, usableCache(client));
    const info = await fetchUserinfo(token);
    const account = { email: info.email ?? cache.account?.email ?? null };
    if (account.email !== cache.account?.email) writeCache({ ...cache, account });
    return { ok: true, at: iso(now()), account };
  }

  // ---------------------------------------------------------------- interactive sign-in (loopback + PKCE)

  async function startInteractive(client) {
    const verifier = b64url(randomBytes(32));
    const challenge = b64url(createHash("sha256").update(verifier).digest());
    const state = b64url(randomBytes(16));
    const srv = createServer();
    await new Promise((ok, bad) => { srv.once("error", bad); srv.listen(0, "127.0.0.1", ok); });
    const redirect = `http://127.0.0.1:${srv.address().port}`;
    const url = `${AUTH_URL}?` + new URLSearchParams({
      client_id: client.id, redirect_uri: redirect, response_type: "code", scope, state,
      code_challenge: challenge, code_challenge_method: "S256",
      // consent: Google shows the permission page and issues a fresh refresh token even if the app was approved before.
      prompt: "consent",
    });
    const code = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new GoogleError("SIGN_IN_TIMEOUT", "No sign-in was completed within 5 minutes.")), SIGN_IN_WINDOW_MS);
      srv.on("request", (req, resp) => {
        const q = new URL(req.url, redirect).searchParams;
        if (!q.has("code") && !q.has("error")) { resp.writeHead(404).end(); return; }
        const okState = q.get("state") === state;
        resp.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        resp.end(`<!doctype html><meta charset="utf-8"><title>Google sign-in</title><p style="font:16px sans-serif">${okState && q.get("code") ? "Signed in. You can close this tab and return to your agent." : "Sign-in was not completed. You can close this tab."}</p>`);
        clearTimeout(timer);
        if (!okState) reject(new GoogleError("AUTH_FAILED", "The sign-in response did not match the request."));
        else if (q.get("error") === "access_denied") reject(new GoogleError("SIGN_IN_DECLINED", "The sign-in was cancelled or refused on Google's page.", { hint: "Run the sign-in again and allow access. If Google said the app is blocked or in testing, see docs/GOOGLE_CLOUD_SETUP.md (test users / publishing status)." }));
        else if (q.get("error")) reject(new GoogleError("AUTH_FAILED", `Google refused the sign-in (${String(q.get("error")).slice(0, 60)}).`));
        else resolve(q.get("code"));
      });
    }).finally(() => srv.close());
    const opened = open(url);
    pending.url = url;
    pending.message = opened
      ? "A browser window opened at Google's sign-in page. Sign in with the Google account and allow access (tick every permission box), then check google_auth_status."
      : `Open this address in a browser on this computer and sign in: ${url}`;
    code.then(async (c) => {
      const { res, j } = await tokenRequest(client, { grant_type: "authorization_code", code: c, redirect_uri: redirect, code_verifier: verifier });
      if (!res.ok || !j.access_token) throw classifyTokenError(j, res.status);
      const list = granted(j.scope);
      const problem = grantProblem(list);
      if (problem) throw problem;
      const prev = readCache();
      const refreshToken = j.refresh_token || (prev && prev.client_id === client.id ? prev.refresh_token : null);
      if (!refreshToken) throw new GoogleError("AUTH_FAILED", "Google returned no refresh token, so the sign-in cannot be kept.", { hint: "Remove the app's access in your Google Account > Security > Third-party connections, then sign in again." });
      const email = idTokenEmail(j.id_token) ?? (await fetchUserinfo(j.access_token)).email;
      const account = { email };
      const at = iso(now());
      writeCache({ v: 1, client_id: client.id, scope_requested: scope, scopes_granted: list, refresh_token: refreshToken, account, obtained_at: at, last_refresh_at: at });
      mem = { token: j.access_token, expiresAt: now() + (Number(j.expires_in) || 3600) * 1000 };
      pending.account = account;
      pending.state = "done";
    }).catch((e) => { pending.state = "failed"; pending.error = e; });
  }

  async function startSignIn() {
    const client = loadClient();
    if (pending && pending.state === "waiting") return { status: "pending", message: pending.message, url: pending.url };
    pending = { state: "waiting", started: now() };
    try { await startInteractive(client); } catch (e) { pending = null; throw e; }
    return { status: "pending", message: pending.message, url: pending.url };
  }

  // ---------------------------------------------------------------- status and sign-out

  /** Never contains a token. `verify` (default true) refreshes the token live and reads the user info, which is the only
   *  real proof the sign-in still works (a cached file says nothing about whether Google still honours it). */
  async function status({ verify: doVerify = true } = {}) {
    /** @type {any} */
    const out = { configured: false, signed_in: false, account: null, read_only: cfg.readOnly, modules_enabled: cfg.modules, scopes_requested: scope.split(" ") };
    let client = null;
    try { client = loadClient(); out.configured = true; out.client_id = client.id; }
    catch (e) { out.client_error = { code: e.code, message: e.message }; out.hint = e.hint ?? e.message; }
    const cache = client ? readCache() : null;
    if (cache && cache.client_id === client.id) {
      const list = cache.scopes_granted ?? [];
      const t = Date.parse(cache.obtained_at);
      Object.assign(out, {
        account: cache.account?.email ?? null,
        scopes_granted: list,
        scopes_missing: out.scopes_requested.filter((s) => !list.includes(s) && s !== "openid" && s !== "email"),
        modules: moduleState(list),
        token_obtained_at: cache.obtained_at ?? null,
        token_age_days: Number.isFinite(t) ? Math.round(((now() - t) / DAY) * 100) / 100 : null,
        last_refresh_at: cache.last_refresh_at ?? null,
        ...(cache.last_refresh_error ? { last_refresh_error: cache.last_refresh_error } : {}),
      });
      const problem = grantProblem(list);
      out.signed_in = !problem;
      if (problem) out.auth_error = { code: problem.code === "SCOPE_NOT_GRANTED" ? "AUTH_REQUIRED" : problem.code, message: problem.message };
    }
    const waiting = pending && pending.state === "waiting";
    if (out.signed_in && doVerify && !waiting) {
      try {
        const v = await verify();
        out.verified = true; out.verified_at = v.at; out.account = v.account.email; out.last_refresh_at = v.at;
        delete out.last_refresh_error;
      } catch (e) {
        out.verified = false;
        out.auth_error = { code: e.code ?? "AUTH_FAILED", message: String(e.message ?? "").slice(0, 300) };
        if (e.code === "AUTH_EXPIRED" || e.code === "AUTH_REQUIRED") out.signed_in = false;
      }
    } else out.verified = null; // not checked live
    if (pending) {
      out.sign_in = { state: pending.state };
      if (waiting) { out.sign_in.message = pending.message; if (pending.url) out.sign_in.url = pending.url; }
      if (pending.state === "failed") out.sign_in.error = { code: pending.error?.code ?? "AUTH_FAILED", message: String(pending.error?.message ?? "").slice(0, 300), ...(pending.error?.hint ? { hint: pending.error.hint } : {}) };
    }
    if (out.configured && !out.signed_in && !waiting) out.hint = out.auth_error?.code === "AUTH_EXPIRED" ? EXPIRED_HINT : REQUIRED_HINT;
    else if (out.signed_in && out.scopes_missing?.length) out.hint = "Some modules lack permissions (see modules). To use them, sign in again and tick every box on Google's page.";
    if (out.signed_in) out.note = "Google documents that an External app in 'Testing' publishing status gets refresh tokens that expire after 7 days. This status refreshes the token live, so verified=true means it still works now.";
    return out;
  }

  function signOut() {
    mem = { token: null, expiresAt: 0 };
    pending = null;
    try { rmSync(cachePath, { force: true }); } catch { /* nothing to remove */ }
    return { signed_out: true, note: "The saved sign-in on this computer was deleted. To also remove the app's access at Google: Google Account > Security > Third-party connections." };
  }

  return { getAccessToken, startSignIn, status, signOut, verify, cachePath, _scope: scope };
}
