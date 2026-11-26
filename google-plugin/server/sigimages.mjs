// sigimages.mjs - fetches the remote images of the person's OWN Gmail signature, so a draft snapshot shows the logo the
// recipient will see. The only URLs ever fetched are those in the From address's signature as stored in Gmail settings
// (users.settings.sendAs[].signature), never URLs taken from the draft's body, so content written into a draft (for
// example on the prompting of a crafted email) cannot make the plugin fetch anything.
//
// Each fetch: https only; no redirects; no cookies or credentials; a short timeout; an image/* content type other than
// SVG; at most MAX_IMAGE_BYTES each and MAX_TOTAL_BYTES per snapshot. The host must be public: the address check runs
// INSIDE the DNS lookup the connection itself uses (so a second, different DNS answer cannot be connected to), the
// connected socket's address is checked again, and literal IPs are checked the same way. "Public" means a public IPv4
// address, or an IPv6 global unicast address (2000::/3) that does not embed an IPv4 address (6to4, Teredo) and is not a
// documentation range.
import { lookup as dnsLookupCb } from "node:dns";
import https from "node:https";
import { isIP } from "node:net";

export const MAX_IMAGE_BYTES = 1024 * 1024;
export const MAX_TOTAL_BYTES = 3 * 1024 * 1024;
const TIMEOUT_MS = 5000;
const OK_TYPES = /^image\/(png|jpe?g|gif|webp|bmp|x-icon|vnd\.microsoft\.icon)$/i;

/** The https image URLs in a signature's HTML (decoded &amp;), in order, without duplicates. */
export function signatureImageUrls(sigHtml) {
  const out = [];
  for (const m of String(sigHtml ?? "").matchAll(/<img\b[^>]*?\bsrc\s*=\s*(["'])(.*?)\1/gi)) {
    const url = m[2].replace(/&amp;/g, "&").trim();
    if (/^https:\/\//i.test(url) && !out.includes(url)) out.push(url);
  }
  return out;
}

/** An IPv6 address as 8 numbers (handles "::" and a trailing dotted IPv4), or null if it does not parse. */
export function ipv6Words(addr) {
  let s = String(addr).toLowerCase().replace(/%.*$/, "");
  const dotted = /(\d+\.\d+\.\d+\.\d+)$/.exec(s);
  if (dotted) {
    const p = dotted[1].split(".").map(Number);
    if (p.some((n) => n > 255)) return null;
    s = s.slice(0, -dotted[1].length) + `${((p[0] << 8) | p[1]).toString(16)}:${((p[2] << 8) | p[3]).toString(16)}`;
  }
  const halves = s.split("::");
  if (halves.length > 2) return null;
  const head = halves[0] ? halves[0].split(":") : [];
  const tail = halves.length === 2 && halves[1] ? halves[1].split(":") : [];
  const fill = halves.length === 2 ? 8 - head.length - tail.length : 0;
  if (fill < 0 || (halves.length === 1 && head.length !== 8)) return null;
  const words = [...head, ...Array(fill).fill("0"), ...tail];
  if (words.length !== 8 || words.some((w) => !/^[0-9a-f]{1,4}$/.test(w))) return null;
  return words.map((w) => parseInt(w, 16));
}

function privateV4(ip) {
  const [a, b] = ip.split(".").map(Number);
  return a === 0 || a === 10 || a === 127 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 192 && b === 0) || (a === 198 && (b === 18 || b === 19)) || a >= 224;
}

/** True for any address that is not a plain public internet address (see the file header). */
export function isPrivateAddress(ip) {
  const v = isIP(String(ip ?? "").replace(/%.*$/, ""));
  if (v === 4) return privateV4(ip);
  if (v !== 6) return true;
  const w = ipv6Words(ip);
  if (!w) return true;
  if ((w[0] & 0xe000) !== 0x2000) return true; // only global unicast 2000::/3 (refuses ::, ::1, ::ffff:*, 64:ff9b::, fc00::/7, fe80::/10, fec0::/10, ff00::/8)
  if (w[0] === 0x2002) return true; // 6to4: embeds an IPv4 address
  if (w[0] === 0x2001 && w[1] === 0x0000) return true; // Teredo: embeds an IPv4 address
  if (w[0] === 0x2001 && w[1] === 0x0db8) return true; // documentation
  return false;
}

/** A dns.lookup that only ever hands public addresses to the connection (so the checked address is the connected one). */
export function publicOnlyLookup(baseLookup = dnsLookupCb) {
  return (hostname, options, callback) => {
    if (typeof options === "function") { callback = options; options = {}; }
    baseLookup(hostname, { all: true }, (err, addrs) => {
      if (err) return callback(err);
      const list = Array.isArray(addrs) ? addrs : [{ address: addrs, family: isIP(addrs) }];
      if (!list.length || list.some((a) => isPrivateAddress(a.address))) {
        return callback(Object.assign(new Error("host is not a public address"), { code: "EPRIVATEHOST" }));
      }
      if (options?.all) return callback(null, list.map((a) => ({ address: a.address, family: a.family })));
      callback(null, list[0].address, list[0].family);
    });
  };
}

/** One GET over https with the public-only lookup, no redirects, a timeout and a size cap. Resolves { status, type, bytes }. */
export function pinnedGet(url, { cap, lookup = publicOnlyLookup(), timeoutMs = TIMEOUT_MS } = {}) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { lookup, headers: { Accept: "image/*" }, timeout: timeoutMs }, (res) => {
      const status = res.statusCode ?? 0;
      const type = String(res.headers["content-type"] ?? "");
      if (status < 200 || status >= 300) { res.resume(); return resolve({ status, type, bytes: Buffer.alloc(0) }); }
      const chunks = [];
      let n = 0;
      res.on("data", (c) => { n += c.length; if (n > cap) { req.destroy(Object.assign(new Error("too large"), { code: "ETOOLARGE" })); return; } chunks.push(c); });
      res.on("end", () => resolve({ status, type, bytes: Buffer.concat(chunks) }));
      res.on("error", reject);
    });
    req.on("socket", (sock) => sock.on("connect", () => { if (isPrivateAddress(sock.remoteAddress)) req.destroy(Object.assign(new Error("host is not a public address"), { code: "EPRIVATEHOST" })); }));
    req.on("timeout", () => req.destroy(Object.assign(new Error("timed out"), { code: "ETIMEDOUT" })));
    req.on("error", reject);
    setTimeout(() => req.destroy(Object.assign(new Error("timed out"), { code: "ETIMEDOUT" })), timeoutMs + 1000).unref();
  });
}

/**
 * fetchSignatureImages(urls, { get, lookup }) -> { images: Map(url -> data URI), failed: [{ host, reason }] }
 * get(url, { cap }) defaults to pinnedGet; lookup (callback style, like dns.lookup) is the base resolver it guards.
 * Failures never throw; the snapshot keeps the original <img> (blocked by its content policy) for those.
 */
export async function fetchSignatureImages(urls, { get, lookup } = {}) {
  const guarded = publicOnlyLookup(lookup ?? dnsLookupCb);
  const doGet = get ?? ((url, o) => pinnedGet(url, { ...o, lookup: guarded }));
  const images = new Map();
  const failed = [];
  let total = 0;
  for (const url of urls) {
    let u;
    try { u = new URL(url); } catch { failed.push({ host: null, reason: "not a valid URL" }); continue; }
    const host = u.hostname.replace(/^\[|\]$/g, "");
    const fail = (reason) => failed.push({ host, reason });
    if (u.protocol !== "https:") { fail("not https"); continue; }
    if (u.username || u.password) { fail("credentials in URL"); continue; }
    if (isIP(host)) { if (isPrivateAddress(host)) { fail("host is not a public address"); continue; } }
    else {
      // Early, readable refusal; the connection's own lookup checks again (guarded), so a changed answer cannot pass.
      const verdict = await new Promise((r) => guarded(host, { all: true }, (err) => r(err)));
      if (verdict) { fail(verdict.code === "EPRIVATEHOST" ? "host is not a public address" : "host does not resolve"); continue; }
    }
    const cap = Math.min(MAX_IMAGE_BYTES, MAX_TOTAL_BYTES - total);
    if (cap <= 0) { fail("over the total size limit"); continue; }
    let res;
    try { res = await doGet(u.toString(), { cap }); }
    catch (e) {
      if (e?.code === "ETOOLARGE") fail(cap < MAX_IMAGE_BYTES ? "over the total size limit" : "over the 1 MB limit");
      else if (e?.code === "EPRIVATEHOST") fail("host is not a public address");
      else fail("fetch failed or timed out");
      continue;
    }
    if (res.status >= 300 && res.status < 400) { fail("redirects are not followed"); continue; }
    if (res.status < 200 || res.status >= 300) { fail(`HTTP ${res.status}`); continue; }
    const type = String(res.type ?? "").split(";")[0].trim().toLowerCase();
    if (!OK_TYPES.test(type)) { fail(`not an allowed image type (${type || "none"})`); continue; }
    if (res.bytes.length > cap) { fail(cap < MAX_IMAGE_BYTES ? "over the total size limit" : "over the 1 MB limit"); continue; }
    total += res.bytes.length;
    images.set(url, `data:${type};base64,${res.bytes.toString("base64")}`);
  }
  return { images, failed };
}
