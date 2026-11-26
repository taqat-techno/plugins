// mime.mjs - just enough MIME for the plugin's own tools, with no dependencies:
//   parseMime(raw)        the parts of a RAW message (nested multipart, base64 / quoted-printable, RFC 2231 / 2047 names)
//   attachmentsOf(root)   the file parts, in message order, with index, filename, mimeType and size
//   bodyText(root)        the plain-text body (or the HTML body reduced to text)
//   buildMessage(spec)    a new RFC 5322 message for a draft (UTF-8, base64 bodies, attachments)
// Every header value written is refused if it holds a line break, so no caller can inject a header.
import { randomBytes } from "node:crypto";
import { decodeHeader } from "./identity.mjs";
import { GoogleError } from "./util.mjs";

const MAX_DEPTH = 20;
const MAX_PARTS = 500;

/** RAW as Gmail returns it (base64url, or plain MIME text) to bytes. */
export function rawToBuffer(raw) {
  const s = String(raw ?? "");
  if (!/\r?\n/.test(s.slice(0, 4000))) return Buffer.from(s.replace(/[^A-Za-z0-9_\-+/=]/g, ""), "base64url");
  return Buffer.from(s, "utf8");
}

function splitHead(s) {
  const m = /\r?\n\r?\n/.exec(s);
  return m ? [s.slice(0, m.index), s.slice(m.index + m[0].length)] : [s, ""];
}

function headerMap(block) {
  const out = {};
  for (const line of block.replace(/\r?\n[ \t]+/g, " ").split(/\r?\n/)) {
    const i = line.indexOf(":");
    if (i > 0) (out[line.slice(0, i).trim().toLowerCase()] ??= []).push(line.slice(i + 1).trim());
  }
  return out;
}

/** "type/sub; a=b; c=\"d\"" -> { value, params } (param names lowercased, quotes removed). */
export function parseParams(value) {
  const s = String(value ?? "");
  const semi = s.indexOf(";");
  const out = { value: (semi < 0 ? s : s.slice(0, semi)).trim().toLowerCase(), params: {} };
  const re = /;\s*([^=\s;]+)\s*=\s*("(?:[^"\\]|\\.)*"|[^;]*)/g;
  let m;
  while ((m = re.exec(s))) {
    let v = m[2].trim();
    if (v.startsWith('"')) v = v.slice(1, -1).replace(/\\(.)/g, "$1");
    out.params[m[1].toLowerCase()] = v;
  }
  return out;
}

function rfc2231(v) {
  const m = /^([^']*)'[^']*'(.*)$/.exec(v);
  const [cs, data] = m ? [m[1] || "utf-8", m[2]] : ["utf-8", v];
  const bytes = Buffer.from(data.replace(/%([0-9A-Fa-f]{2})/g, (_x, h) => String.fromCharCode(parseInt(h, 16))), "latin1");
  try { return new TextDecoder(cs.toLowerCase()).decode(bytes); } catch { return bytes.toString("utf8"); }
}

/** A parameter value with RFC 2231 (name*, name*0*, ...) and RFC 2047 handled. */
export function paramValue(params, name) {
  if (params[`${name}*`] !== undefined) return rfc2231(params[`${name}*`]);
  if (params[`${name}*0*`] !== undefined || params[`${name}*0`] !== undefined) {
    let joined = "", encoded = false;
    for (let i = 0; i < 100; i++) {
      if (params[`${name}*${i}*`] !== undefined) { joined += params[`${name}*${i}*`]; encoded = true; }
      else if (params[`${name}*${i}`] !== undefined) joined += params[`${name}*${i}`];
      else break;
    }
    return encoded ? rfc2231(joined) : decodeHeader(joined);
  }
  return params[name] !== undefined ? decodeHeader(params[name]) : undefined;
}

function qpDecode(s) {
  return Buffer.from(s.replace(/=\r?\n/g, "").replace(/=([0-9A-Fa-f]{2})/g, (_x, h) => String.fromCharCode(parseInt(h, 16))), "latin1");
}

function decodeBody(body, encoding) {
  const e = String(encoding ?? "").trim().toLowerCase();
  if (e === "base64") return Buffer.from(body.replace(/[^A-Za-z0-9+/=]/g, ""), "base64");
  if (e === "quoted-printable") return qpDecode(body);
  return Buffer.from(body, "latin1");
}

/** Parses bytes into a part tree. Works on a latin1 view, so binary bodies keep their exact bytes. */
export function parseMime(raw) {
  const buf = Buffer.isBuffer(raw) ? raw : rawToBuffer(raw);
  let count = 0;
  const part = (s, depth) => {
    if (++count > MAX_PARTS) throw new GoogleError("MESSAGE_TOO_COMPLEX", "The message has too many parts to read.");
    const [head, body] = splitHead(s);
    const headers = headerMap(head);
    const ct = parseParams(headers["content-type"]?.[0] ?? "text/plain");
    const cd = parseParams(headers["content-disposition"]?.[0] ?? "");
    const node = { headers, mimeType: ct.value || "text/plain", disposition: cd.value, children: [] };
    node.filename = paramValue(cd.params, "filename") ?? paramValue(ct.params, "name");
    const boundary = ct.params.boundary;
    if (node.mimeType.startsWith("multipart/") && boundary && depth < MAX_DEPTH) {
      const delim = `--${boundary}`;
      const pieces = body.split(new RegExp(`(?:^|\\r?\\n)${delim.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`));
      for (const p of pieces.slice(1)) {
        if (p.startsWith("--")) break;
        node.children.push(part(p.replace(/^[ \t]*\r?\n/, ""), depth + 1));
      }
    } else {
      node.body = decodeBody(body, headers["content-transfer-encoding"]?.[0]);
    }
    return node;
  };
  return part(buf.toString("latin1"), 0);
}

function walk(node, fn) { fn(node); for (const c of node.children) walk(c, fn); }

/** File parts in message order: a disposition of attachment, or any leaf with a file name. */
export function attachmentsOf(root) {
  const out = [];
  walk(root, (n) => {
    if (n.children.length || !n.body) return;
    const cid = n.headers["content-id"]?.[0]?.trim().replace(/^<|>$/g, "");
    const inlineImage = Boolean(cid) && !/^text\/(plain|html)$/.test(n.mimeType);
    const isFile = n.disposition === "attachment" || Boolean(n.filename) || n.mimeType === "message/rfc822" || inlineImage;
    if (!isFile) return;
    const inline = Boolean(cid) && n.disposition !== "attachment";
    out.push({ index: out.length + 1, filename: n.filename || (n.mimeType === "message/rfc822" ? "message.eml" : `attachment-${out.length + 1}`), mimeType: n.mimeType, size: n.body.length, bytes: n.body, inline, ...(cid ? { contentId: cid } : {}) });
  });
  return out;
}

const charsetOf = (n) => parseParams(n.headers["content-type"]?.[0] ?? "").params.charset ?? "utf-8";
const asText = (n) => { try { return new TextDecoder(charsetOf(n).toLowerCase()).decode(n.body); } catch { return n.body.toString("utf8"); } };

/** HTML reduced to readable text (tags dropped, common entities decoded). */
export function htmlToText(html) {
  return String(html).replace(/<(script|style)[\s\S]*?<\/\1>/gi, "").replace(/<br\s*\/?>|<\/p>|<\/div>|<\/tr>|<\/li>|<\/h[1-6]>/gi, "\n").replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&")
    .replace(/\n{3,}/g, "\n\n").trim();
}

/** Every text body of the message: the plain parts and the HTML parts reduced to text (not attachments). */
export function bodyViews(root) {
  const plain = [], html = [];
  walk(root, (n) => {
    if (n.children.length || !n.body || n.disposition === "attachment" || n.filename) return;
    if (n.mimeType === "text/plain") plain.push(asText(n));
    else if (n.mimeType === "text/html") html.push(htmlToText(asText(n)));
  });
  return { text: plain.join("\n\n"), html: html.join("\n\n"), textParts: plain.length, htmlParts: html.length };
}

/** Parts with a Content-ID (inline images), keyed by the id without angle brackets, lowercased. */
export function inlineParts(root) {
  const out = new Map();
  walk(root, (n) => {
    if (n.children.length || !n.body) return;
    const id = n.headers["content-id"]?.[0];
    if (id) out.set(id.trim().replace(/^<|>$/g, "").toLowerCase(), { mimeType: /^[\w.+-]+\/[\w.+-]+$/.test(n.mimeType) ? n.mimeType : "application/octet-stream", bytes: n.body });
  });
  return out;
}

/** The first plain-text and the first HTML body as written (not reduced), or null. */
export function bodySources(root) {
  let text = null, html = null;
  walk(root, (n) => {
    if (n.children.length || !n.body || n.disposition === "attachment" || n.filename) return;
    if (n.mimeType === "text/plain" && text === null) text = asText(n);
    else if (n.mimeType === "text/html" && html === null) html = asText(n);
  });
  return { text, html };
}

/** The plain-text body; an HTML-only message is reduced to text. */
export function bodyText(root) {
  const v = bodyViews(root);
  return v.textParts ? v.text : v.html;
}

// ------------------------------------------------------------------------------------------------ building

const EMAIL = /^[A-Za-z0-9._%+'!#$&*=?^`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
export const isEmail = (s) => typeof s === "string" && s.length <= 320 && EMAIL.test(s);

function noBreak(v, what) {
  if (/[\r\n]/.test(String(v))) throw new GoogleError("INVALID_ARGUMENT", `${what} must not contain a line break.`);
  return String(v);
}

/** RFC 2047 encoded words (UTF-8, base64) for a header text that is not plain ASCII. */
export function encodeWords(text) {
  const s = noBreak(text, "A header");
  // eslint-disable-next-line no-control-regex
  if (/^[\x20-\x7e]*$/.test(s)) return s;
  const words = [];
  let cur = "";
  for (const ch of s) {
    if (Buffer.byteLength(cur + ch) > 45) { words.push(cur); cur = ""; }
    cur += ch;
  }
  if (cur) words.push(cur);
  return words.map((w) => `=?UTF-8?B?${Buffer.from(w, "utf8").toString("base64")}?=`).join(" ");
}

const b64lines = (buf) => buf.toString("base64").replace(/.{1,76}/g, "$&\r\n").trimEnd();
const boundary = () => `=_gp_${randomBytes(12).toString("hex")}`;

function addressList(list, what) {
  const arr = (Array.isArray(list) ? list : list ? [list] : []).map((a) => String(a).trim()).filter(Boolean);
  for (const a of arr) if (!isEmail(a)) throw new GoogleError("INVALID_ARGUMENT", `${what} has an entry that is not a plain email address.`);
  return arr;
}

/** The address of a header value such as "Name <a@b.c>" or "a@b.c". */
export function addressOf(value) {
  const m = /<([^<>\s]+)>/.exec(String(value ?? "")) ?? /([^\s<>",;]+@[^\s<>",;]+)/.exec(String(value ?? ""));
  return m && isEmail(m[1]) ? m[1].toLowerCase() : null;
}

/**
 * buildMessage({ from, fromName, to, cc, bcc, subject, text, html, inReplyTo, references, attachments }) -> string (CRLF).
 * to/cc/bcc are plain email addresses. attachments: [{ filename, mimeType, bytes }]. At least one body or attachment.
 */
export function buildMessage(spec) {
  const to = addressList(spec.to, "to"), cc = addressList(spec.cc, "cc"), bcc = addressList(spec.bcc, "bcc");
  if (!isEmail(spec.from)) throw new GoogleError("INVALID_ARGUMENT", "from must be a plain email address.");
  const head = [];
  head.push(`From: ${spec.fromName ? `${encodeWords(spec.fromName)} <${spec.from}>` : spec.from}`);
  if (to.length) head.push(`To: ${to.join(", ")}`);
  if (cc.length) head.push(`Cc: ${cc.join(", ")}`);
  if (bcc.length) head.push(`Bcc: ${bcc.join(", ")}`);
  head.push(`Subject: ${encodeWords(spec.subject ?? "")}`);
  head.push(`Date: ${new Date().toUTCString().replace("GMT", "+0000")}`);
  if (spec.inReplyTo) head.push(`In-Reply-To: ${noBreak(spec.inReplyTo, "In-Reply-To")}`);
  if (spec.references) head.push(`References: ${noBreak(spec.references, "References")}`);
  head.push("MIME-Version: 1.0");

  const textPart = (type, body) => [`Content-Type: ${type}; charset=UTF-8`, "Content-Transfer-Encoding: base64", "", b64lines(Buffer.from(body, "utf8"))].join("\r\n");
  let body;
  if (spec.html && spec.text !== undefined) {
    const b = boundary();
    body = [`Content-Type: multipart/alternative; boundary="${b}"`, "", `--${b}`, textPart("text/plain", spec.text), `--${b}`, textPart("text/html", spec.html), `--${b}--`].join("\r\n");
  } else if (spec.html) body = textPart("text/html", spec.html);
  else body = textPart("text/plain", spec.text ?? "");

  // Inline files (shown in the HTML body through <img src="cid:ID">) go with the body in multipart/related; the others
  // are ordinary attachments in multipart/mixed around it.
  const atts = spec.attachments ?? [];
  const filePart = (a, disposition) => {
    const name = String(a.filename ?? "attachment").replace(/[\r\n"\\]/g, "_");
    const encName = encodeURIComponent(name).replace(/['()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
    const type = /^[\w.+-]+\/[\w.+-]+$/.test(String(a.mimeType ?? "")) ? a.mimeType : "application/octet-stream";
    const cid = disposition === "inline" ? String(a.contentId ?? "") : "";
    if (cid && !/^[A-Za-z0-9._@-]{1,100}$/.test(cid)) throw new GoogleError("INVALID_ARGUMENT", "contentId may hold only letters, digits and . _ @ -.");
    return [`Content-Type: ${type}; name="${encodeWords(name)}"`, `Content-Disposition: ${disposition}; filename*=UTF-8''${encName}`, ...(cid ? [`Content-ID: <${cid}>`, `X-Attachment-Id: ${cid}`] : []), "Content-Transfer-Encoding: base64", "", b64lines(a.bytes)].join("\r\n");
  };
  const inlines = atts.filter((a) => a.inline && a.contentId);
  const files = atts.filter((a) => !(a.inline && a.contentId));
  if (inlines.length) {
    const b = boundary();
    body = [`Content-Type: multipart/related; boundary="${b}"`, "", `--${b}`, body, ...inlines.flatMap((a) => [`--${b}`, filePart(a, "inline")]), `--${b}--`].join("\r\n");
  }
  if (files.length) {
    const b = boundary();
    body = [`Content-Type: multipart/mixed; boundary="${b}"`, "", `--${b}`, body, ...files.flatMap((a) => [`--${b}`, filePart(a, "attachment")]), `--${b}--`].join("\r\n");
  }
  return `${head.join("\r\n")}\r\n${body}\r\n`;
}
