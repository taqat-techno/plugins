// signature.mjs - a send-as address's Gmail signature (users.settings.sendAs[].signature, HTML) on a draft body, and the
// HTML snapshot of a draft for a human to look at before it is sent.
//
// Signature format (so it can be found again and never doubled):
//   HTML:  <!--gp-signature-start--><div class="gmail_signature">SIGNATURE</div><!--gp-signature-end-->
//   text:  "\n\n-- \n" + the signature reduced to text
import { htmlToText } from "./mime.mjs";

export const SIG_START = "<!--gp-signature-start-->";
export const SIG_END = "<!--gp-signature-end-->";
const SIG_BLOCK = /<!--gp-signature-start-->[\s\S]*?<!--gp-signature-end-->/;

const sizeText = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${Math.round(n / 1024)} KB` : `${n} bytes`);
export const escapeHtml = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/** Plain text as HTML that keeps its line breaks (dir=auto so Arabic and English both read right). */
export const textToHtml = (text) => `<div dir="auto">${escapeHtml(text).replace(/\r?\n/g, "<br>\n")}</div>`;

const sigHtmlBlock = (sig) => `${SIG_START}<div class="gmail_signature">${sig}</div>${SIG_END}`;
const sigTextBlock = (sig) => `\n\n-- \n${htmlToText(sig)}`;

/** Inserts into an HTML body: before </body> when it is a whole document, else at the end. */
function appendHtml(html, piece) {
  const i = html.search(/<\/body\s*>/i);
  return i >= 0 ? `${html.slice(0, i)}${piece}${html.slice(i)}` : `${html}${piece}`;
}

/**
 * Puts signature `sig` (HTML; empty = none) on a body, replacing an earlier plugin signature in place if there is one.
 * oldSig is the signature that may already be in the text version (to replace it there too).
 * Returns { text, html, added }. When a signature is added and the body had no HTML version, one is made from the text,
 * because signatures are HTML (links, images).
 */
export function putSignature({ text, html, sig, oldSig }) {
  if (!String(sig ?? "").trim()) {
    // No signature for this address: remove an earlier plugin signature, add nothing.
    return { text: removeTextSig(text, oldSig), html: html === undefined ? undefined : String(html).replace(SIG_BLOCK, ""), added: false };
  }
  const baseText = text ?? (html !== undefined ? htmlToText(html) : "");
  let outText;
  const oldBlock = oldSig ? sigTextBlock(oldSig) : null;
  if (oldBlock && baseText.includes(oldBlock)) outText = baseText.replace(oldBlock, sigTextBlock(sig));
  else outText = `${baseText}${sigTextBlock(sig)}`;
  const baseHtml = html ?? textToHtml(text ?? "");
  const outHtml = SIG_BLOCK.test(baseHtml) ? baseHtml.replace(SIG_BLOCK, sigHtmlBlock(sig)) : appendHtml(baseHtml, `<br>${sigHtmlBlock(sig)}`);
  return { text: outText, html: outHtml, added: true };
}

function removeTextSig(text, oldSig) {
  if (text === undefined || !oldSig) return text;
  return String(text).replace(sigTextBlock(oldSig), "");
}

// ------------------------------------------------------------------------------------------------ snapshot

/** Removes what could run or redirect: scripts, embedded objects, event attributes, javascript: links, refresh. */
export function sanitizeHtml(html) {
  let s = String(html ?? "");
  s = s.replace(/<script\b[\s\S]*?<\/script\s*>/gi, "").replace(/<script\b[^>]*>/gi, "");
  s = s.replace(/<(iframe|object|embed|frame|frameset|applet)\b[\s\S]*?<\/\1\s*>/gi, "").replace(/<(iframe|object|embed|frame|frameset|applet|base|link)\b[^>]*>/gi, "");
  s = s.replace(/<meta\b[^>]*http-equiv\s*=\s*["']?\s*refresh[^>]*>/gi, "");
  for (let i = 0; i < 5; i++) {
    const next = s.replace(/(<[^>]*?)\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, "$1");
    if (next === s) break;
    s = next;
  }
  s = s.replace(/\b(href|src|action|formaction|xlink:href)\s*=\s*(["']?)\s*(?:javascript|vbscript|data:text\/html)[^"'\s>]*\2/gi, '$1="#"');
  return s;
}

/**
 * One self-contained HTML page of a draft: a header block (From, To, Cc, Bcc, Subject, "DRAFT, not sent") and the body
 * as it will be sent, cid: images inlined as data: URIs, nothing that can run, and a content policy that blocks every
 * network request (remote images do not load, scripts cannot run) wherever the file is opened.
 */
export function draftSnapshot({ headers, html, text, inline, attachments = [] }) {
  const row = (k, v) => (v ? `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>` : "");
  let body;
  let styles = "";
  if (html !== null && html !== undefined) {
    let h = String(html);
    styles = (h.match(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi) ?? []).join("\n");
    const m = /<body\b[^>]*>([\s\S]*?)<\/body\s*>/i.exec(h);
    if (m) h = m[1];
    h = h.replace(/(\bsrc\s*=\s*)(["'])cid:([^"']+)\2/gi, (all, pre, q, cid) => {
      const part = inline.get(cid.trim().replace(/^<|>$/g, "").toLowerCase());
      return part ? `${pre}${q}data:${part.mimeType};base64,${part.bytes.toString("base64")}${q}` : all;
    });
    body = sanitizeHtml(h);
    styles = sanitizeHtml(styles);
  } else {
    body = `<pre style="white-space:pre-wrap;font-family:inherit">${escapeHtml(text ?? "")}</pre>`;
  }
  return `<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:">
<title>Draft: ${escapeHtml(headers.subject)}</title>
<style>.gp-draft-head{font-family:system-ui,Segoe UI,Arial,sans-serif;font-size:14px;border:1px solid #ccc;border-radius:6px;padding:10px 12px;margin:0 0 14px;background:#fafafa}.gp-draft-head th{text-align:left;padding:2px 10px 2px 0;color:#555;vertical-align:top;white-space:nowrap}.gp-draft-head td{padding:2px 0}.gp-att{color:#666}.gp-draft-tag{display:inline-block;background:#b00020;color:#fff;font-weight:600;border-radius:4px;padding:2px 8px;margin-bottom:6px}</style>
${styles}
</head><body>
<div class="gp-draft-head"><span class="gp-draft-tag">DRAFT, not sent</span><table>${row("From", headers.from)}${row("To", headers.to)}${row("Cc", headers.cc)}${row("Bcc", headers.bcc)}${row("Subject", headers.subject)}${attachments.length ? `<tr><th>Attachments</th><td>${attachments.map((a) => `${escapeHtml(a.filename)} <span class="gp-att">(${escapeHtml(a.mimeType)}, ${sizeText(a.size)}${a.inline ? ", inline in the body" : ""})</span>`).join("<br>")}</td></tr>` : ""}</table></div>
${body}
</body></html>
`;
}
