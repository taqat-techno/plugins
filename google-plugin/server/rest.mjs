// rest.mjs - a small client for Google's REST APIs (Gmail v1, Drive v3), used ONLY by server/tools/rest.mjs, whose
// tools exist only when GOOGLE_REST_FALLBACK=1. Same sign-in as the bridge; the scopes it uses (gmail.modify, drive)
// are the ones the milestone-1 sign-in already requests. Failures are GoogleError with stable codes; no token in them.
//
// Note: Google's Workspace AI Tools Addendum says AI agents must use Google's MCP servers instead of REST from
// 2027-02-01. These tools are a stopgap for what the MCP servers lack; `cli.mjs schema-check` reports when Google adds
// such a tool, so the REST one can be removed.
import { GoogleError } from "./util.mjs";

export const REST_BASE = {
  gmail: "https://gmail.googleapis.com/gmail/v1/users/me/",
  drive: "https://www.googleapis.com/drive/v3/",
};

const short = (s, n = 300) => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, n);

export function restError(status, j, mod) {
  const msg = short(j?.error?.message ?? "");
  if (status === 401) return new GoogleError("AUTH_EXPIRED", `Google's ${mod} API did not accept the sign-in (401).`, { hint: "Run google_auth_status; if it reports AUTH_EXPIRED a human must sign in again. Do not retry in a loop." });
  if (status === 403) return new GoogleError("GOOGLE_FORBIDDEN", `Google's ${mod} API refused the request (403)${msg ? `: ${msg}` : ""}.`, { hint: "Check that the API is enabled in the Cloud project and that the sign-in covers it." });
  if (status === 404) return new GoogleError("NOT_FOUND", `Google's ${mod} API found nothing with that id (404).`);
  if (status === 429) return new GoogleError("RATE_LIMITED", `Google's ${mod} API is rate limiting requests (429).`, { hint: "Wait a minute before trying again." });
  if (status >= 500) return new GoogleError("GOOGLE_UNAVAILABLE", `Google's ${mod} API failed (${status}).`, { hint: "Try again later." });
  return new GoogleError(status === 400 ? "INVALID_ARGUMENT" : "GOOGLE_ERROR", `Google's ${mod} API refused the request (${status})${msg ? `: ${msg}` : ""}.`);
}

/** createRest(ctx).call(mod, method, path, { query, body }) -> parsed JSON ({} for an empty reply). */
export function createRest(ctx) {
  async function call(mod, method, path, { query, body } = {}) {
    if (!ctx.cfg.restFallback) throw new GoogleError("REST_DISABLED", "The REST fallback is off (GOOGLE_REST_FALLBACK).");
    const token = await ctx.auth.getAccessToken(mod);
    const url = new URL(path, REST_BASE[mod]);
    for (const [k, v] of Object.entries(query ?? {})) {
      if (v === undefined || v === null) continue;
      for (const x of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(x));
    }
    let res;
    try {
      res = await ctx.fetch(url.toString(), {
        method,
        headers: { Authorization: `Bearer ${token}`, ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
        signal: AbortSignal.timeout(ctx.cfg.timeoutMs),
      });
    } catch (e) {
      if (e?.name === "TimeoutError" || e?.name === "AbortError") throw new GoogleError("TIMEOUT", `Google's ${mod} API did not answer in time.`);
      throw new GoogleError("NETWORK_ERROR", `Cannot reach Google's ${mod} API: ${short(e?.message, 120)}.`);
    }
    const text = await res.text();
    let j = {};
    if (text) { try { j = JSON.parse(text); } catch { j = {}; } }
    if (!res.ok) throw restError(res.status, j, mod);
    return j;
  }
  return { call };
}
