// auth.mjs - delegated Microsoft sign-in with no dependencies and no admin rights.
//
//   interactive  - browser sign-in: authorization code + PKCE, redirect to http://localhost:<port>
//   device-code  - for machines with no usable browser (and first sign-in of a bot): a code to type
//   auto         - interactive; falls back to device code if a browser cannot be opened
//
// The app registration must be a PUBLIC client (no secret): docs/APP_REGISTRATION.md.
// The refresh token is cached per user in <M365_HOME>/token-cache.json (default ~/.m365-plugin),
// written atomically because several processes (agent, bot, poller) may share it. The access
// token is kept in memory only. No token is ever returned to a caller or put in an error message.
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { M365Error } from "./util.mjs";
import { NEEDS_CLIENT_ID } from "./config.mjs";

const LOGIN = "https://login.microsoftonline.com";
const b64url = (buf) => buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

/** Scope strings Graph wants: resource scopes get the Graph prefix, OIDC ones stay bare. */
export function scopeString(scopes) {
  const bare = new Set(["openid", "profile", "offline_access", "email"]);
  const list = [...scopes.map((s) => (bare.has(s) || s.startsWith("http") ? s : `https://graph.microsoft.com/${s}`))];
  for (const s of ["offline_access", "openid", "profile"]) if (!list.includes(s)) list.push(s);
  return list.join(" ");
}

/** Maps Microsoft's token errors to a code and a one-line action. */
export function classifyTokenError(j, status) {
  const code = String(j?.error ?? "unknown");
  const desc = String(j?.error_description ?? "");
  const aadsts = (/AADSTS(\d+)/.exec(desc) || [])[1];
  if (["65001", "90094", "650057", "65004"].includes(aadsts)) {
    return new M365Error("CONSENT_NEEDED", `Microsoft needs consent for the requested permissions (AADSTS${aadsts}).`,
      { hint: "Ask a tenant admin to grant consent for this app (see docs/APP_REGISTRATION.md), or sign in again and approve the prompt." });
  }
  if (aadsts === "700016") return new M365Error("CLIENT_ID_INVALID", "The client id is not an app in this tenant (AADSTS700016).", { hint: "Check the Client ID and Tenant settings." });
  if (aadsts === "7000218" || aadsts === "7000215") {
    return new M365Error("PUBLIC_CLIENT_NOT_ENABLED", "The app is not set up as a public client (AADSTS" + aadsts + ").",
      { hint: "In the app registration: Authentication > Allow public client flows = Yes, and add the redirect URI http://localhost." });
  }
  if (aadsts === "50011") return new M365Error("REDIRECT_URI_MISMATCH", "The app has no http://localhost redirect URI (AADSTS50011).", { hint: "Add the Mobile and desktop redirect URI http://localhost to the app registration." });
  if (code === "invalid_grant" || code === "interaction_required" || aadsts === "70043" || aadsts === "50173") {
    return new M365Error("SIGN_IN_EXPIRED", "The saved sign-in is no longer valid.", { hint: "Run m365_sign_in again." });
  }
  return new M365Error("AUTH_FAILED", `Sign-in failed (${status ?? "?"}: ${code}${aadsts ? ` AADSTS${aadsts}` : ""}).`);
}

function claims(idToken) {
  try { return JSON.parse(Buffer.from(String(idToken).split(".")[1], "base64url").toString("utf8")); } catch { return {}; }
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

export function createAuth(cfg, { fetch: fetchImpl = globalThis.fetch, open = openBrowser, now = () => Date.now(), sleep = (ms) => new Promise((r) => setTimeout(r, ms)) } = {}) {
  const cachePath = join(cfg.home, "token-cache.json");
  const scope = scopeString(cfg.scopes);
  let mem = { token: null, expiresAt: 0 };
  let pending = null; // one sign-in at a time: { mode, state, started, message, error, account }

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
    renameSync(tmp, cachePath);
  };

  async function tokenRequest(params) {
    const res = await fetchImpl(`${LOGIN}/${encodeURIComponent(cfg.tenant)}/oauth2/v2.0/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ client_id: cfg.clientId, ...params }),
      signal: AbortSignal.timeout(cfg.timeoutMs),
    });
    const j = await res.json().catch(() => ({}));
    return { res, j };
  }

  function needClientId() {
    if (!cfg.clientId) throw new M365Error("NOT_CONFIGURED", NEEDS_CLIENT_ID);
  }

  function store(j, prev) {
    const c = claims(j.id_token);
    const account = {
      name: c.name ?? prev?.account?.name ?? null,
      username: c.preferred_username ?? prev?.account?.username ?? null,
      oid: c.oid ?? prev?.account?.oid ?? null,
      tid: c.tid ?? prev?.account?.tid ?? null,
    };
    if (j.refresh_token) {
      writeCache({ v: 1, client_id: cfg.clientId, tenant: cfg.tenant, scope, refresh_token: j.refresh_token, account, saved_at: new Date(now()).toISOString() });
    }
    mem = { token: j.access_token, expiresAt: now() + (j.expires_in ?? 3600) * 1000 };
    return account;
  }

  async function getAccessToken() {
    needClientId();
    if (mem.token && now() < mem.expiresAt - 120_000) return mem.token;
    const cache = readCache();
    if (!cache || cache.client_id !== cfg.clientId || cache.tenant !== cfg.tenant) {
      throw new M365Error("NOT_SIGNED_IN", "Not signed in to Microsoft 365.", { hint: "Call m365_sign_in, or run: node server/cli.mjs sign-in" });
    }
    let { res, j } = await tokenRequest({ grant_type: "refresh_token", refresh_token: cache.refresh_token, scope });
    // Another process may have rotated the token between our read and our request.
    if ((!res.ok || !j.access_token) && j.error === "invalid_grant") {
      const latest = readCache();
      if (latest && latest.refresh_token !== cache.refresh_token) ({ res, j } = await tokenRequest({ grant_type: "refresh_token", refresh_token: latest.refresh_token, scope }));
    }
    if (!res.ok || !j.access_token) throw classifyTokenError(j, res.status);
    store(j, cache);
    return mem.token;
  }

  // ---------------------------------------------------------------- interactive (PKCE)

  async function interactive() {
    const verifier = b64url(randomBytes(32));
    const challenge = b64url(createHash("sha256").update(verifier).digest());
    const state = b64url(randomBytes(16));
    const srv = createServer();
    await new Promise((ok, bad) => { srv.once("error", bad); srv.listen(0, "127.0.0.1", ok); });
    const redirect = `http://localhost:${srv.address().port}`;
    const url = `${LOGIN}/${encodeURIComponent(cfg.tenant)}/oauth2/v2.0/authorize?` + new URLSearchParams({
      client_id: cfg.clientId, response_type: "code", redirect_uri: redirect, response_mode: "query",
      scope, state, code_challenge: challenge, code_challenge_method: "S256", prompt: "select_account",
    });
    const code = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new M365Error("SIGN_IN_TIMEOUT", "No sign-in was completed within 5 minutes.")), 300_000);
      srv.on("request", (req, resp) => {
        const q = new URL(req.url, redirect).searchParams;
        if (!q.has("code") && !q.has("error")) { resp.writeHead(404).end(); return; }
        const okState = q.get("state") === state;
        resp.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        resp.end(`<!doctype html><meta charset="utf-8"><title>Signed in</title><p style="font:16px sans-serif">${okState && q.get("code") ? "Signed in. You can close this tab and return to your agent." : "Sign-in was not completed. You can close this tab."}</p>`);
        clearTimeout(timer);
        if (!okState) reject(new M365Error("AUTH_FAILED", "Sign-in response did not match the request."));
        else if (q.get("error")) reject(new M365Error("AUTH_FAILED", `Sign-in refused: ${String(q.get("error_description") || q.get("error")).slice(0, 160)}`));
        else resolve(q.get("code"));
      });
    }).finally(() => srv.close());
    const opened = open(url);
    return { url, opened, redirect, verifier, code };
  }

  async function startInteractive() {
    const flow = await interactive();
    pending.url = flow.url;
    pending.message = flow.opened
      ? "A browser window opened. Sign in with your work account, then call m365_auth_status."
      : `Open this address in a browser and sign in: ${flow.url}`;
    flow.code.then(async (code) => {
      const { res, j } = await tokenRequest({ grant_type: "authorization_code", code, redirect_uri: flow.redirect, code_verifier: flow.verifier, scope });
      if (!res.ok || !j.access_token) throw classifyTokenError(j, res.status);
      pending.account = store(j, null);
      pending.state = "done";
    }).catch((e) => { pending.state = "failed"; pending.error = e; });
  }

  // ---------------------------------------------------------------- device code

  async function startDeviceCode() {
    const res = await fetchImpl(`${LOGIN}/${encodeURIComponent(cfg.tenant)}/oauth2/v2.0/devicecode`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ client_id: cfg.clientId, scope }),
      signal: AbortSignal.timeout(cfg.timeoutMs),
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok || !d.device_code) throw classifyTokenError(d, res.status);
    pending.url = d.verification_uri;
    pending.code = d.user_code;
    pending.message = `Open ${d.verification_uri} and enter the code ${d.user_code}, then sign in. Then call m365_auth_status.`;
    (async () => {
      let interval = Math.max(1, Number(d.interval) || 5);
      const deadline = now() + (Number(d.expires_in) || 900) * 1000;
      while (now() < deadline) {
        await sleep(interval * 1000);
        const { res: r, j } = await tokenRequest({ grant_type: "urn:ietf:params:oauth:grant-type:device_code", device_code: d.device_code });
        if (r.ok && j.access_token) { pending.account = store(j, null); pending.state = "done"; return; }
        if (j.error === "authorization_pending") continue;
        if (j.error === "slow_down") { interval += 5; continue; }
        throw classifyTokenError(j, r.status);
      }
      throw new M365Error("SIGN_IN_TIMEOUT", "The device code expired before sign-in was completed.");
    })().catch((e) => { pending.state = "failed"; pending.error = e; });
  }

  async function startSignIn({ mode } = {}) {
    needClientId();
    const want = (mode || cfg.authMode || "auto").toLowerCase();
    if (!["auto", "interactive", "device-code"].includes(want)) {
      throw new M365Error("INVALID_ARGUMENT", "mode must be auto, interactive or device-code");
    }
    if (pending && pending.state === "waiting") return { status: "pending", mode: pending.mode, message: pending.message, url: pending.url, code: pending.code };
    pending = { mode: want, state: "waiting", started: now() };
    try {
      if (want === "device-code") { await startDeviceCode(); pending.mode = "device-code"; }
      else {
        try { await startInteractive(); pending.mode = "interactive"; }
        catch (e) { if (want === "interactive") throw e; await startDeviceCode(); pending.mode = "device-code"; }
      }
    } catch (e) { pending = null; throw e; }
    return { status: "pending", mode: pending.mode, message: pending.message, url: pending.url, ...(pending.code ? { code: pending.code } : {}) };
  }

  function status() {
    const cache = readCache();
    const valid = cache && cache.client_id === cfg.clientId && cache.tenant === cfg.tenant;
    /** @type {any} */
    const out = {
      configured: Boolean(cfg.clientId),
      signed_in: Boolean(valid),
      account: valid ? { name: cache.account?.name ?? null, username: cache.account?.username ?? null } : null,
      tenant: cfg.tenant,
      read_only: cfg.readOnly,
      modules: cfg.modules,
    };
    if (pending) {
      out.sign_in = { state: pending.state, mode: pending.mode };
      if (pending.state === "waiting") { out.sign_in.message = pending.message; if (pending.url) out.sign_in.url = pending.url; if (pending.code) out.sign_in.code = pending.code; }
      if (pending.state === "failed") out.sign_in.error = { code: pending.error?.code ?? "AUTH_FAILED", message: String(pending.error?.message ?? "").slice(0, 300), hint: pending.error?.hint };
    }
    if (!cfg.clientId) out.hint = NEEDS_CLIENT_ID;
    else if (!valid && !(pending && pending.state === "waiting")) out.hint = "Not signed in. Call m365_sign_in.";
    return out;
  }

  function signOut() {
    mem = { token: null, expiresAt: 0 };
    pending = null;
    try { rmSync(cachePath, { force: true }); } catch { /* nothing to remove */ }
    return { signed_out: true };
  }

  return { getAccessToken, startSignIn, status, signOut, cachePath, _scope: scope };
}
