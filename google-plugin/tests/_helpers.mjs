// Shared test helpers: a fake Google (token endpoint + user info) in place of the network.
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { MODULES, moduleScopes } from "../server/config.mjs";
import { createContext } from "../server/context.mjs";

export const CLIENT_ID = "123-test.apps.googleusercontent.com";
export const SECRET = "GOCSPX-test-secret-value";
export const home = () => mkdtempSync(join(tmpdir(), "google-test-"));
export const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

/** Every module's write scopes, as a full grant returns them (Google reports "email" as userinfo.email). */
export const FULL_GRANT = ["openid", "https://www.googleapis.com/auth/userinfo.email", ...MODULES.flatMap((m) => moduleScopes(m, false))];
export const READ_GRANT = ["openid", "https://www.googleapis.com/auth/userinfo.email", ...MODULES.flatMap((m) => moduleScopes(m, true))];

/** An unsigned ID token carrying an email claim (the plugin reads it straight from the token endpoint over TLS). */
export const idToken = (email = "owner@example.com") => `h.${Buffer.from(JSON.stringify({ email, sub: "1" })).toString("base64url")}.s`;

/** Writes a Desktop-app client JSON (as Google's console downloads it) and returns its path. */
export function clientFile(h, body) {
  const p = join(h, "client.json");
  writeFileSync(p, JSON.stringify(body ?? { installed: { client_id: CLIENT_ID, client_secret: SECRET, project_id: "p", auth_uri: "https://evil.example/auth", token_uri: "https://evil.example/token", redirect_uris: ["http://localhost"] } }));
  return p;
}

export const env = (h, extra = {}) => ({ GOOGLE_PLUGIN_HOME: h, GOOGLE_CLIENT_SECRET_FILE: clientFile(h), ...extra });

export function seedCache(h, over = {}) {
  writeFileSync(join(h, "token-cache.json"), JSON.stringify({
    v: 1, client_id: CLIENT_ID, scope_requested: FULL_GRANT.join(" "), scopes_granted: FULL_GRANT, refresh_token: "rt-1",
    account: { email: "owner@example.com" }, obtained_at: "2026-11-20T00:00:00.000Z", last_refresh_at: "2026-11-20T00:00:00.000Z", ...over,
  }));
}

export const TOKEN = /^POST https:\/\/oauth2\.googleapis\.com\/token$/;
export const USERINFO = /^GET https:\/\/openidconnect\.googleapis\.com\/v1\/userinfo$/;
export const userinfoOk = [USERINFO, () => json({ sub: "1", email: "owner@example.com", email_verified: true })];

/** routes: [[regex over "METHOD url", handler({url, init, body}) -> Response | plain body]]; first match wins. */
export function fakeFetch(routes) {
  const calls = [];
  const fn = async (url, init = {}) => {
    const method = init.method || "GET";
    const body = init.body === undefined ? undefined : String(init.body);
    calls.push({ url: String(url), method, headers: init.headers ?? {}, body, form: body ? new URLSearchParams(body) : undefined });
    for (const [re, h] of routes) {
      if (re.test(`${method} ${url}`)) {
        const r = typeof h === "function" ? await h({ url: String(url), init, body }) : h;
        return r instanceof Response ? r : json(r);
      }
    }
    throw new Error(`unexpected network call in a test: ${method} ${url}`);
  };
  fn.calls = calls;
  return fn;
}

export const NOW = Date.parse("2026-11-25T00:00:00Z");

export function ctxFor(routes, { extraEnv = {}, seed = true, deps = {} } = {}) {
  const h = home();
  if (seed) seedCache(h, typeof seed === "object" ? seed : {});
  const f = fakeFetch(routes);
  const c = createContext(env(h, extraEnv), { fetch: f, open: () => true, now: () => NOW, ...deps });
  c.fetch = f; c.home = h;
  return c;
}
