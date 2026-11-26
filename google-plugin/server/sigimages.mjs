// sigimages.mjs - fetches the remote images of the person's OWN Gmail signature, so a draft snapshot shows the logo the
// recipient will see. The only URLs ever fetched are those in the From address's signature as stored in Gmail settings
// (users.settings.sendAs[].signature), never URLs taken from the draft's body, so content written into a draft (for
// example on the prompting of a crafted email) cannot make the plugin fetch anything.
//
// Each fetch: https only; the host must resolve only to public addresses (no loopback, private, link-local, CGNAT or
// multicast; literal IPs checked the same way); no redirects; no cookies or credentials; a short timeout; an image/*
// content type other than SVG; at most MAX_IMAGE_BYTES each and MAX_TOTAL_BYTES per snapshot.
import { lookup as dnsLookup } from "node:dns/promises";
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

/** True for an address that is not on the public internet. */
export function isPrivateAddress(ip) {
  const v = isIP(ip);
  if (v === 4) {
    const [a, b] = ip.split(".").map(Number);
    return a === 0 || a === 10 || a === 127 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 192 && b === 0) || (a === 198 && (b === 18 || b === 19)) || a >= 224;
  }
  if (v === 6) {
    const s = ip.toLowerCase();
    if (s === "::" || s === "::1") return true;
    const mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/.exec(s);
    if (mapped) return isPrivateAddress(mapped[1]);
    return /^(fc|fd|fe8|fe9|fea|feb|ff)/.test(s);
  }
  return true;
}

async function readCapped(res, cap) {
  const reader = res.body?.getReader?.();
  if (!reader) { const b = Buffer.from(await res.arrayBuffer()); if (b.length > cap) throw new Error("too large"); return b; }
  const chunks = [];
  let n = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    n += value.length;
    if (n > cap) { try { await reader.cancel(); } catch { /* ignore */ } throw new Error("too large"); }
    chunks.push(value);
  }
  return Buffer.concat(chunks.map((c) => Buffer.from(c)));
}

/**
 * fetchSignatureImages(urls, { fetch, lookup }) -> { images: Map(url -> data URI), failed: [{ host, reason }] }
 * Failures never throw; the snapshot keeps the original <img> (blocked by its content policy) for those.
 */
export async function fetchSignatureImages(urls, { fetch: fetchImpl = globalThis.fetch, lookup = dnsLookup } = {}) {
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
    try {
      const addrs = isIP(host) ? [{ address: host }] : await lookup(host, { all: true });
      if (!addrs.length || addrs.some((a) => isPrivateAddress(a.address))) { fail("host is not a public address"); continue; }
    } catch { fail("host does not resolve"); continue; }
    let res;
    try {
      res = await fetchImpl(u.toString(), { method: "GET", redirect: "manual", credentials: "omit", headers: { Accept: "image/*" }, signal: AbortSignal.timeout(TIMEOUT_MS) });
    } catch { fail("fetch failed or timed out"); continue; }
    if (res.status >= 300 && res.status < 400) { fail("redirects are not followed"); continue; }
    if (!res.ok) { fail(`HTTP ${res.status}`); continue; }
    const type = String(res.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
    if (!OK_TYPES.test(type)) { fail(`not an allowed image type (${type || "none"})`); continue; }
    let bytes;
    try { bytes = await readCapped(res, Math.min(MAX_IMAGE_BYTES, MAX_TOTAL_BYTES - total)); }
    catch { fail(total + MAX_IMAGE_BYTES > MAX_TOTAL_BYTES ? "over the total size limit" : "over the 1 MB limit"); continue; }
    total += bytes.length;
    images.set(url, `data:${type};base64,${bytes.toString("base64")}`);
  }
  return { images, failed };
}
