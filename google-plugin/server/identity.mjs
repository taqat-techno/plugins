// identity.mjs - which of the user's own addresses a message was sent to, decided from the message's headers (never by
// the model). Generic: the identities are configuration.
//
// Config (GOOGLE_IDENTITIES_FILE = path to a JSON file, or GOOGLE_IDENTITIES = the JSON itself):
//   { "identities": [ { "id": "sales", "label": "Sales desk", "address": "info@example.com",
//                       "matchTo": ["info@example.com", "@example.com"], "default": false } ] }
//   (a bare array is accepted too). matchTo entries are exact addresses or "@domain" (any address at that domain);
//   matchTo defaults to [address]. At most one identity may be the default.
//
// Match order (first hit wins): every address in X-Forwarded-For, in order (forwarding services such as Cloudflare
// Email Routing put the original envelope recipient there, first, which also catches Bcc), then To, then Cc, then the
// default identity. Delivered-To is never used: after forwarding it holds the mailbox address, not the alias.
import { readFileSync } from "node:fs";
import { GoogleError } from "./util.mjs";

const EMAIL = /^[A-Za-z0-9._%+'!#$&*=?^`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
/** Header values come from senders. Each one is cut to this length before parsing, so a hostile header cannot make
 *  parsing slow; a real address list that long is rare, and X-Forwarded-For (checked first) is short. */
export const MAX_ADDRESS_HEADER = 8192;
/** Email addresses in a header value: split on separators, each token checked with an anchored pattern (linear time). */
export const addresses = (value) => String(value ?? "").slice(0, MAX_ADDRESS_HEADER)
  .split(/[\s,;<>()"[\]:]+/)
  .filter((t) => t.length <= 320 && EMAIL.test(t))
  .map((t) => t.toLowerCase());

/** Loads and checks the identity list. Returns [] when none is configured. */
export function loadIdentities(cfg) {
  let raw = cfg.identitiesJson;
  if (cfg.identitiesFile) {
    try { raw = readFileSync(cfg.identitiesFile, "utf8").replace(/^﻿/, ""); }
    catch { throw new GoogleError("CONFIG_INVALID", "The identities file cannot be read.", { hint: "Check the path in GOOGLE_IDENTITIES_FILE." }); }
  }
  if (!raw) return [];
  let j;
  try { j = JSON.parse(raw); } catch { throw new GoogleError("CONFIG_INVALID", "The identities configuration is not valid JSON."); }
  const list = Array.isArray(j) ? j : j?.identities;
  if (!Array.isArray(list)) throw new GoogleError("CONFIG_INVALID", "The identities configuration needs an \"identities\" array.");
  const seen = new Set();
  const out = list.map((x, i) => {
    const where = `identities[${i}]`;
    if (!x || typeof x !== "object") throw new GoogleError("CONFIG_INVALID", `${where} is not an object.`);
    const id = String(x.id ?? "").trim();
    if (!id) throw new GoogleError("CONFIG_INVALID", `${where} has no id.`);
    if (seen.has(id)) throw new GoogleError("CONFIG_INVALID", `Identity id ${id.slice(0, 40)} is used twice.`);
    seen.add(id);
    const address = addresses(x.address)[0];
    if (!address || addresses(x.address).length !== 1) throw new GoogleError("CONFIG_INVALID", `${where} needs one email address in "address".`);
    const matchTo = (x.matchTo === undefined ? [address] : x.matchTo);
    if (!Array.isArray(matchTo) || !matchTo.length) throw new GoogleError("CONFIG_INVALID", `${where}.matchTo must be a non-empty array.`);
    const rules = matchTo.map((m) => {
      const s = String(m ?? "").trim().toLowerCase();
      if (/^@[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(s)) return s;
      if (addresses(s).length === 1 && addresses(s)[0] === s) return s;
      throw new GoogleError("CONFIG_INVALID", `${where}.matchTo has an entry that is neither an address nor "@domain".`);
    });
    return { id, label: String(x.label ?? id), address, matchTo: rules, default: x.default === true };
  });
  if (out.filter((x) => x.default).length > 1) throw new GoogleError("CONFIG_INVALID", "More than one identity is marked default.");
  return out;
}

const hits = (rule, addr) => (rule.startsWith("@") ? addr.endsWith(rule) : addr === rule);

/** headers: { "x-forwarded-for": [..], to: [..], cc: [..] } (lowercase names, all values). */
export function matchIdentity(headers, identities) {
  const order = [["x-forwarded-for", headers["x-forwarded-for"]], ["to", headers.to], ["cc", headers.cc]];
  for (const [by, values] of order) {
    for (const addr of (values ?? []).flatMap(addresses)) {
      const id = identities.find((x) => x.matchTo.some((r) => hits(r, addr)));
      if (id) return { identity: id, matched_by: by, matched_address: addr };
    }
  }
  const def = identities.find((x) => x.default);
  return def ? { identity: def, matched_by: "default", matched_address: null } : { identity: null, matched_by: null, matched_address: null };
}

// ------------------------------------------------------------------------------------------------ raw MIME headers

/** How much of a RAW message is decoded to find the end of the headers. */
const HEAD_WINDOW = 256 * 1024;

/** The header block of a RAW message (plain MIME, or base64url as the Gmail API returns it). Never the body. */
export function headerBlock(raw) {
  let text = String(raw ?? "");
  if (!/\r?\n/.test(text.slice(0, 4000))) {
    const chunk = text.slice(0, HEAD_WINDOW - (HEAD_WINDOW % 4)).replace(/[^A-Za-z0-9_\-+/=]/g, "");
    text = Buffer.from(chunk, "base64url").toString("latin1");
  } else text = text.slice(0, HEAD_WINDOW);
  const end = text.search(/\r?\n\r?\n/);
  if (end < 0) throw new GoogleError("HEADERS_TOO_LARGE", "The message's headers could not be found in its first 256 KB.");
  return text.slice(0, end);
}

/** RFC 2047 encoded words (=?charset?B|Q?...?=) to text. Header bytes arrive as latin1 and are re-read as UTF-8. */
export function decodeHeader(value) {
  // Bytes read as latin1 (from base64url) are re-read as UTF-8; text that already holds wider characters is kept.
  const utf = /[^\x00-\xff]/.test(value) ? null : Buffer.from(value, "latin1").toString("utf8");
  const plain = utf === null || /\uFFFD/.test(utf) ? value : utf;
  return plain.replace(/=\?([^?]+)\?([BbQq])\?([^?]*)\?=(\s+(?==\?))?/g, (_m, cs, enc, data) => {
    try {
      const bytes = /b/i.test(enc) ? Buffer.from(data, "base64") : Buffer.from(data.replace(/_/g, " ").replace(/=([0-9A-Fa-f]{2})/g, (_x, h) => String.fromCharCode(parseInt(h, 16))), "latin1");
      return new TextDecoder(cs.toLowerCase().replace(/\*.*$/, "")).decode(bytes);
    } catch { return _m; }
  });
}

/** Parses the header block into lowercase name -> [values] (unfolded, decoded). */
export function parseHeaders(block) {
  const out = {};
  for (const line of block.replace(/\r?\n[ \t]+/g, " ").split(/\r?\n/)) {
    const i = line.indexOf(":");
    if (i <= 0) continue;
    const k = line.slice(0, i).trim().toLowerCase();
    (out[k] ??= []).push(decodeHeader(line.slice(i + 1).trim()));
  }
  return out;
}
