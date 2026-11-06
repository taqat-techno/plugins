// Shared test helpers: a fake Microsoft (sign-in + Graph) in place of the network.
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { READ_SCOPES, WRITE_SCOPES } from "../server/config.mjs";
import { scopeString } from "../server/auth.mjs";
import { createContext } from "../server/context.mjs";

export const home = () => mkdtempSync(join(tmpdir(), "m365-test-"));
export const env = (h, extra = {}) => ({ M365_CLIENT_ID: "cid-123", M365_TENANT: "contoso.com", M365_HOME: h, ...extra });
export const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
export const TOKEN = /^POST https:\/\/login\.microsoftonline\.com\/.+\/oauth2\/v2\.0\/token/;
export const TOK = [TOKEN, () => json({ access_token: "at-1", refresh_token: "rt-2", expires_in: 3600 })];
export const ALL_SCOPES = scopeString([...Object.values(READ_SCOPES).flat(), ...Object.values(WRITE_SCOPES).flat()]);

/** routes: [[regex over "METHOD url", handler({url, init, body}) -> Response | plain body]]; first match wins. */
export function fakeFetch(routes) {
  const calls = [];
  const fn = async (url, init = {}) => {
    const method = init.method || "GET";
    const body = typeof init.body === "string" ? init.body : init.body?.toString();
    calls.push({ url: String(url), method, headers: init.headers ?? {}, body, json: body && body.startsWith("{") ? JSON.parse(body) : undefined });
    for (const [re, h] of routes) {
      if (re.test(`${method} ${url}`)) {
        const r = typeof h === "function" ? await h({ url: String(url), init, body }) : h;
        return r instanceof Response ? r : json(r);
      }
    }
    return json({ error: { code: "NotFound", message: "no route" } }, 404);
  };
  fn.calls = calls;
  return fn;
}

export function seedCache(h, over = {}) {
  writeFileSync(join(h, "token-cache.json"), JSON.stringify({ v: 1, client_id: "cid-123", tenant: "contoso.com", scope: ALL_SCOPES, refresh_token: "rt-1", account: { name: "Ahmed", username: "a@contoso.com" }, ...over }));
}

export function ctxFor(routes, extraEnv = {}, deps = {}) {
  const h = deps.home ?? home();
  seedCache(h);
  const f = fakeFetch(routes);
  const c = createContext(env(h, extraEnv), { fetch: f, sleep: async () => {}, now: () => Date.parse("2026-11-02T00:00:00Z"), ...deps });
  c.fetch = f; c.home = h;
  return c;
}
export const call = (c, name, args = {}) => c.callTool(name, args);
export const g = (re, body) => [new RegExp(re), body];
