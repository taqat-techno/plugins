// signature.mjs - HTML drafts the plugin builds itself, never HTML a model wrote.
//
// The model always writes plain text. When the user has set a signature file (M365_SIGNATURE_FILE, an HTML file only the
// person can choose), or when the text uses one of the formatting marks below, drafts become HTML: the text is escaped,
// only those marks become fixed tags, paragraphs and line breaks are kept, and the user's own signature (if any) follows. Images the signature references by a plain file name next to
// the signature file (src="logo.png") are attached inline, so they show without loading anything from the internet.
// The preview still lists every link and image address of the result.
import { existsSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { createHash } from "node:crypto";
import { M365Error } from "./util.mjs";
import { contentTypeOf } from "./attach.mjs";

const MAX_SIG = 100 * 1024, MAX_IMG = 1024 * 1024, MAX_IMGS = 10;
const UNSAFE = /<\s*(script|iframe|object|embed|form|input|button|meta|link|base)\b|\bon[a-z]+\s*=|javascript:|vbscript:|data:text\/html/i;

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// The only formatting a draft can carry: a fixed set of plain-text marks, each turned into one fixed tag AFTER the text
// is escaped. No link, image, colour or style can be written by the model; the marks are visible in the preview too.
//   **bold**  *italic*  __underline__  ==highlight==  ~~strike~~   lines "- item" / "* item"  "1. item"
// A mark must sit against a word on both inner sides and not inside a word (so a==b, snake__case__x, 2*3*4 stay as typed).
const HIGHLIGHT = '<span style="background-color:#ffff00;mso-highlight:yellow">';
const INLINE = [
  [/(^|[^\w*])\*\*(?=\S)([^*\n]*?\S)\*\*(?![\w*])/g, "$1<b>$2</b>"],
  [/(^|[^\w_])__(?=\S)([^_\n]*?\S)__(?![\w_])/g, "$1<u>$2</u>"],
  [/(^|[^\w=])==(?=\S)([^=\n]*?\S)==(?![\w=])/g, `$1${HIGHLIGHT}$2</span>`],
  [/(^|[^\w~])~~(?=\S)([^~\n]*?\S)~~(?![\w~])/g, "$1<s>$2</s>"],
  [/(^|[^\w*])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?![\w*])/g, "$1<i>$2</i>"],
];
const BULLET = /^\s*[-*•]\s+(.+)$/, NUMBERED = /^\s*\d{1,3}[.)]\s+(.+)$/;
const P = '<p style="margin:0 0 10px 0">';

function inline(line) {
  let s = esc(line);
  for (const [re, to] of INLINE) s = s.replace(re, to);
  return s;
}

/** Plain text to safe HTML. Returns { html, formatted }: formatted is true when any mark or list was used. */
export function formatText(text) {
  let formatted = false;
  const out = [];
  for (const block of String(text ?? "").replace(/\r\n?/g, "\n").split(/\n{2,}/)) {
    let lines = [], list = null, items = [];
    const flushLines = () => { if (lines.length) out.push(`${P}${lines.join("<br>")}</p>`); lines = []; };
    const flushList = () => { if (items.length) out.push(`<${list} style="margin:0 0 10px 0">${items.map((i) => `<li>${i}</li>`).join("")}</${list}>`); items = []; list = null; };
    for (const line of block.split("\n")) {
      const b = BULLET.exec(line), n = b ? null : NUMBERED.exec(line);
      const kind = b ? "ul" : n ? "ol" : null;
      if (kind) {
        flushLines();
        if (list !== kind) flushList();
        list = kind; formatted = true;
        items.push(inline((b ?? n)[1]));
      } else {
        flushList();
        lines.push(inline(line));
      }
    }
    flushLines(); flushList();
  }
  const html = out.join("");
  if (!formatted) formatted = /<(b|i|u|s)>|<span style="background-color/.test(html);
  return { html, formatted };
}

export const textToHtml = (text) => formatText(text).html;

/** The user's signature, checked, with its local images. null when no signature file is set. */
export function loadSignature(cfg) {
  if (!cfg.signatureFile) return null;
  let st;
  try { st = statSync(cfg.signatureFile); } catch { throw new M365Error("NOT_CONFIGURED", "The signature file cannot be read.", { hint: "Check the signature file setting (M365_SIGNATURE_FILE)." }); }
  if (!st.isFile() || st.size > MAX_SIG) throw new M365Error("NOT_CONFIGURED", `The signature file must be an HTML file under ${MAX_SIG / 1024} KB.`);
  let html = readFileSync(cfg.signatureFile, "utf8");
  if (UNSAFE.test(html)) throw new M365Error("NOT_CONFIGURED", "The signature file contains scripts, forms or event handlers, which are not allowed in an email signature.", { hint: "Use a plain HTML signature (text, links, images)." });
  html = html.replace(/^[\s\S]*?<body[^>]*>/i, "").replace(/<\/body>[\s\S]*$/i, "");
  // Local images: a bare file name next to the signature file becomes an inline attachment.
  const images = [];
  html = html.replace(/(<img\b[^>]*?\bsrc\s*=\s*)(["'])([^"']+)\2/gi, (all, pre, q, src) => {
    if (/^[a-z][a-z0-9+.-]*:/i.test(src) || src.includes("/") || src.includes("\\") || src.startsWith(".")) return all;
    const file = join(dirname(cfg.signatureFile), src);
    if (!existsSync(file) || images.length >= MAX_IMGS) return all;
    const bytes = readFileSync(file);
    if (bytes.length > MAX_IMG) return all;
    const cid = `sig-${createHash("sha256").update(bytes).digest("hex").slice(0, 12)}@m365-plugin`;
    if (!images.some((i) => i.cid === cid)) images.push({ cid, name: basename(file), bytes, contentType: contentTypeOf(file) });
    return `${pre}${q}cid:${cid}${q}`;
  });
  return { html, images };
}

/** The full HTML body for a plugin-built draft. */
export const composeHtml = (text, sig) =>
  `<html><body><div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">${textToHtml(text)}${sig ? `<div>${sig.html}</div>` : ""}</div></body></html>`;

/** Insert our text and signature at the top of an Outlook reply/forward body (keeping the quoted original below). */
export function prependToReply(existingHtml, text, sig) {
  const block = `<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">${textToHtml(text)}${sig ? `<div>${sig.html}</div>` : ""}</div>`;
  const s = String(existingHtml ?? "");
  const m = /<body[^>]*>/i.exec(s);
  return m ? s.slice(0, m.index + m[0].length) + block + s.slice(m.index + m[0].length) : block + s;
}
