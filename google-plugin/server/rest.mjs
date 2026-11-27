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
  calendar: "https://www.googleapis.com/calendar/v3/",
  photos: "https://photoslibrary.googleapis.com/v1/",
  picker: "https://photospicker.googleapis.com/v1/",
};
/** Google Photos is not a Workspace API and has no MCP server: its calls do not need GOOGLE_REST_FALLBACK. */
const OWN_SWITCH = new Set(["photos", "picker"]);
const WORKSPACE = new Set(["gmail", "calendar", "drive"]);

const short = (s, n = 300) => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, n);

export function restError(status, j, mod, cli) {
  const msg = short(j?.error?.message ?? "");
  if (status === 401) return new GoogleError("AUTH_EXPIRED", `Google's ${mod} API did not accept the sign-in (401).`, { hint: "Run google_auth_status; if it reports AUTH_EXPIRED a human must sign in again. Do not retry in a loop." });
  if (status === 403 && /insufficient (authentication )?scopes?|ACCESS_TOKEN_SCOPE_INSUFFICIENT|insufficientPermissions/i.test(`${msg} ${JSON.stringify(j?.error?.details ?? j?.error?.errors ?? "")}`)) {
    return new GoogleError("SCOPE_MISSING", `The saved sign-in does not include the permission this ${mod} call needs.`, { hint: `The person signs in again with the matching option on (GOOGLE_GMAIL_SETTINGS=1 for settings, GOOGLE_FULL_MAILBOX=1 for permanent delete): ${cli || "node server/cli.mjs"} sign-in.` });
  }
  if (status === 403 && /delegated domain-wide authority/i.test(msg)) {
    return new GoogleError("GOOGLE_LIMITATION", `Google allows this ${mod} change only for Google Workspace admins using domain-wide delegation, not for this account: ${msg}`, { hint: "Do it in Gmail itself (Settings > See all settings > Accounts). Retrying will not help." });
  }
  if (status === 403) return new GoogleError("GOOGLE_FORBIDDEN", `Google's ${mod} API refused the request (403)${msg ? `: ${msg}` : ""}.`, { hint: "Check that the API is enabled in the Cloud project and that the sign-in covers it." });
  if (status === 404) return new GoogleError("NOT_FOUND", `Google's ${mod} API found nothing with that id (404).`);
  if (status === 429) return new GoogleError("RATE_LIMITED", `Google's ${mod} API is rate limiting requests (429).`, { hint: "Wait a minute before trying again." });
  if (status >= 500) return new GoogleError("GOOGLE_UNAVAILABLE", `Google's ${mod} API failed (${status}).`, { hint: "Try again later." });
  return new GoogleError(status === 400 ? "INVALID_ARGUMENT" : "GOOGLE_ERROR", `Google's ${mod} API refused the request (${status})${msg ? `: ${msg}` : ""}.`);
}

/**
 * createRest(ctx).call(mod, method, path, { query, body }) -> parsed JSON ({} for an empty reply).
 * createRest(ctx).bytes(mod, path, { query, maxBytes }) -> { bytes, contentType }: a GET whose reply is a file. Stops
 * reading past maxBytes and throws TOO_LARGE, so an oversized file never fills memory.
 */
export function createRest(ctx) {
  async function send(mod, method, path, { query, body, raw, headers: extraHeaders } = {}) {
    if (!ctx.cfg.restFallback && !OWN_SWITCH.has(mod)) throw new GoogleError("REST_DISABLED", "The REST fallback is off (GOOGLE_REST_FALLBACK).");
    if (OWN_SWITCH.has(mod) && !ctx.cfg.photos) throw new GoogleError("PHOTOS_DISABLED", "Google Photos is off (GOOGLE_PHOTOS).");
    const token = await ctx.auth.getAccessToken(WORKSPACE.has(mod) ? mod : undefined);
    // "./" keeps a path like "mediaItems:batchCreate" relative (otherwise "mediaItems:" would parse as a URL scheme).
    const url = /^https:\/\//.test(path) ? new URL(path) : new URL(`./${path}`, REST_BASE[mod]);
    for (const [k, v] of Object.entries(query ?? {})) {
      if (v === undefined || v === null) continue;
      for (const x of Array.isArray(v) ? v : [v]) url.searchParams.append(k, String(x));
    }
    let res;
    try {
      res = await ctx.fetch(url.toString(), {
        method,
        headers: { Authorization: `Bearer ${token}`, ...(raw !== undefined ? { "Content-Type": "application/octet-stream" } : body !== undefined ? { "Content-Type": "application/json" } : {}), ...(extraHeaders ?? {}) },
        ...(raw !== undefined ? { body: raw } : body !== undefined ? { body: JSON.stringify(body) } : {}),
        signal: AbortSignal.timeout(ctx.cfg.timeoutMs),
      });
    } catch (e) {
      if (e?.name === "TimeoutError" || e?.name === "AbortError") throw new GoogleError("TIMEOUT", `Google's ${mod} API did not answer in time.`);
      throw new GoogleError("NETWORK_ERROR", `Cannot reach Google's ${mod} API: ${short(e?.message, 120)}.`);
    }
    return res;
  }
  async function failure(res, mod) {
    const text = await res.text();
    let j = {};
    if (text) { try { j = JSON.parse(text); } catch { j = {}; } }
    return restError(res.status, j, mod, ctx.cfg.cliCommand);
  }
  async function call(mod, method, path, opts = {}) {
    const res = await send(mod, method, path, opts);
    const text = await res.text();
    let j = {};
    if (text) { try { j = JSON.parse(text); } catch { j = {}; } }
    if (!res.ok) throw restError(res.status, j, mod, ctx.cfg.cliCommand);
    return j;
  }
  async function bytes(mod, path, { query, maxBytes } = {}) {
    const res = await send(mod, "GET", path, { query });
    if (!res.ok) throw await failure(res, mod);
    const tooLarge = () => new GoogleError("TOO_LARGE", `The file is over the ${Math.round(maxBytes / 1048576)} MB limit; nothing was saved.`, { hint: "The person can raise GOOGLE_MAX_SAVE_MB." });
    const declared = Number(res.headers.get("content-length"));
    if (maxBytes && declared > maxBytes) { try { await res.body?.cancel(); } catch { /* ignore */ } throw tooLarge(); }
    const parts = [];
    let total = 0;
    try {
      for await (const chunk of res.body ?? []) {
        total += chunk.length;
        if (maxBytes && total > maxBytes) throw tooLarge();
        parts.push(Buffer.from(chunk));
      }
    } catch (e) {
      if (e instanceof GoogleError) { try { await res.body?.cancel(); } catch { /* ignore */ } throw e; }
      if (e?.name === "TimeoutError" || e?.name === "AbortError") throw new GoogleError("TIMEOUT", `Google's ${mod} API did not finish sending the file in time.`);
      throw new GoogleError("NETWORK_ERROR", `The download from Google's ${mod} API broke off: ${short(e?.message, 120)}.`);
    }
    return { bytes: Buffer.concat(parts, total), contentType: String(res.headers.get("content-type") ?? "").split(";")[0].trim() };
  }
  /** POST raw bytes; Google answers with plain text (the Photos upload token). */
  async function upload(mod, path, raw, headers = {}) {
    const res = await send(mod, "POST", path, { raw, headers });
    if (!res.ok) throw await failure(res, mod);
    const text = (await res.text()).trim();
    if (!text) throw new GoogleError("GOOGLE_ERROR", `Google's ${mod} API returned no upload token.`);
    return text;
  }
  return { call, bytes, upload };
}
