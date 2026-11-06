// mail tools that change the mailbox. The safe path for sending is draft -> preview -> send:
//   email_create_draft / email_create_reply_draft  -> a draft in Outlook Drafts (nothing leaves the mailbox)
//   email_preview_draft                            -> exactly what will be sent, plus a digest
//   email_send_draft(draft_id, digest)             -> refuses unless the draft is unchanged since that preview
// Recipients must be email addresses (resolve names with people_resolve); nothing is guessed from a name.
import { EMAIL_RE, M365Error, clean, decodeEntities, fence, htmlToText, safeId, safeStr, seg, truncate } from "../util.mjs";
import { digestOf } from "../staging.mjs";
import { allowedFile, attachBytes, readAllowed, contentTypeOf } from "../attach.mjs";
import { composeHtml, loadSignature, prependToReply } from "../signature.mjs";

const FOLDERS = ["inbox", "archive"]; // deleting goes through email_delete, which asks the human
const FLAGS = { flagged: "flagged", complete: "complete", none: "notFlagged" };
const DRAFT_SELECT = "id,subject,toRecipients,ccRecipients,bccRecipients,body,hasAttachments,isDraft,conversationId";
const ATTACH_PROMISE = /\b(attached|attachment|attachments|attaching|enclosed)\b|مرفق|المرفق|مرفقات|ارفقت|أرفقت|إرفاق|ارفاق/i;
const MAX_PREVIEW = 20_000;
// Statuses that mean Microsoft did not accept the send. Anything else (408, 409, 5xx, a timeout) is an unknown outcome.
const REFUSED = new Set([400, 401, 403, 404, 405, 422, 429]);
const SENT_HINT = "Look in Sent Items (email_list_recent with folder sentitems) before doing anything else. This draft will not be sent a second time from here.";
const MAX_LINKS = 200;

/** Every address an HTML body can point at or load: quoted and unquoted attributes, srcset, CSS url() and @import,
 *  meta refresh. Entities are decoded first, as a mail client would. Callers must check the count against MAX_LINKS. */
export function extractLinks(raw) {
  const out = new Set();
  const add = (v) => { const t = decodeEntities(v ?? "").trim(); if (t) out.add(clean(t, 300)); };
  // The whole body is scanned, not just what a regex thinks are tags: a tag splitter can disagree with how a mail client
  // tokenizes odd markup and so hide a link. Listing an inert one (escaped text) is harmless; missing a live one is not.
  for (const x of raw.matchAll(/\b(?:href|src|background|action|formaction|poster|data|cite|longdesc|ping|manifest|xlink:href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/gi)) add(x[1] ?? x[2] ?? x[3]);
  for (const x of raw.matchAll(/\b(?:srcset|imagesrcset)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi)) for (const part of (x[1] ?? x[2]).split(",")) add(part.trim().split(/\s+/)[0]);
  for (const x of raw.matchAll(/url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s]+))\s*\)/gi)) add(x[1] ?? x[2] ?? x[3]);
  for (const x of raw.matchAll(/@import\s+(?:url\(\s*)?["']([^"']+)["']/gi)) add(x[1]);
  for (const x of raw.matchAll(/http-equiv\s*=\s*["']?refresh["']?[^>]*content\s*=\s*["'][^"']*url\s*=\s*([^"']+)/gi)) add(x[1]);
  return [...out];
}
const HIDDEN_MARKUP = /display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|opacity\s*:\s*0|mso-hide\s*:\s*all/i;
const QUOTE_START = /\n\s*(From:|On .{5,120} wrote:|-{3,}\s*Original Message|De\s?:|من:)/i;

function rcpts(list, field) {
  const arr = list === undefined || list === null ? [] : Array.isArray(list) ? list : [list];
  if (arr.length > 50) throw new M365Error("INVALID_ARGUMENT", `${field}: at most 50 recipients`);
  const out = [];
  for (const x of arr) {
    const e = String(x ?? "").trim().toLowerCase();
    if (!EMAIL_RE.test(e)) throw new M365Error("INVALID_ARGUMENT", `${field}: "${x}" is not an email address. Resolve names with people_resolve first; never guess an address.`);
    if (!out.includes(e)) out.push(e);
  }
  return out.map((address) => ({ emailAddress: { address } }));
}
const addrs = (l) => (l ?? []).map((r) => (r.emailAddress?.address ?? "").toLowerCase()).filter(Boolean);

/** Whether this call uses the user's signature: on by default when a signature file is set; signature:false skips it. */
const wantsSignature = (a, ctx) => Boolean(ctx.cfg.signatureFile) && a.signature !== false;

/** The body for a draft. The model only ever supplies plain text: HTML written by a model can hide links or text the
 *  human never sees in a preview. With a signature, the plugin itself builds the HTML from that text (signature.mjs). */
function bodyOf(a, ctx, field = "body") {
  if (a.body_format !== undefined && String(a.body_format).toLowerCase() !== "text") throw new M365Error("INVALID_ARGUMENT", "only plain-text bodies are supported (body_format must be text); the plugin adds the user's HTML signature itself");
  const text = safeBody(a[field]);
  const sig = wantsSignature(a, ctx) ? loadSignature(ctx.cfg) : null;
  return sig ? { body: { contentType: "HTML", content: composeHtml(text, sig) }, images: sig.images } : { body: { contentType: "Text", content: text }, images: [] };
}

/** Attach the signature's images inline, skipping any the draft already has (an update re-builds the body). */
async function attachSignatureImages(ctx, draftId, images) {
  if (!images.length) return;
  const j = await ctx.graph.get(`/me/messages/${seg(draftId)}/attachments?$select=id,name,isInline`);
  const have = new Set((j.value ?? []).filter((x) => x.isInline).map((x) => x.name));
  for (const img of images) if (!have.has(img.name)) await attachBytes(ctx, draftId, { name: img.name, bytes: img.bytes, contentType: img.contentType, inline: true, contentId: img.cid });
}

/** A reply or forward with the signature: Outlook builds the quoted original, then our text and signature go on top. */
async function topOfReply(ctx, draftId, text) {
  const sig = loadSignature(ctx.cfg);
  const d = await ctx.graph.get(`/me/messages/${seg(draftId)}?$select=body`);
  const existing = (d.body?.contentType ?? "").toLowerCase() === "html" ? d.body.content : `<html><body><pre>${String(d.body?.content ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")}</pre></body></html>`;
  await ctx.graph.patch(`/me/messages/${seg(draftId)}`, { body: { contentType: "HTML", content: prependToReply(existing, safeBody(text), sig) } });
  await attachSignatureImages(ctx, draftId, sig.images);
}
function safeBody(v) {
  const s = String(v ?? "");
  if (s.length > 100_000) throw new M365Error("INVALID_ARGUMENT", "body is too long (max 100000 characters)");
  return s;
}

async function loadDraft(ctx, id) {
  const m = await ctx.graph.get(`/me/messages/${seg(id)}?$select=${DRAFT_SELECT}`);
  if (!m.isDraft) throw new M365Error("NOT_A_DRAFT", "That message is not a draft, so it cannot be changed or sent from here.");
  return m;
}
/** The draft's attachments (file attachments and inline images), as shown in the preview and covered by the digest. */
async function draftAttachments(ctx, m) {
  if (!m.hasAttachments && !/cid:/i.test(String(m.body?.content ?? ""))) return [];
  const j = await ctx.graph.get(`/me/messages/${seg(m.id)}/attachments?$select=id,name,size,isInline,contentType`);
  return (j.value ?? []).map((x) => ({ attachment_id: x.id, name: clean(x.name, 200), size_bytes: x.size ?? null, inline: !!x.isInline, content_type: x.contentType ?? null }))
    .sort((x, y) => String(x.attachment_id).localeCompare(String(y.attachment_id)));
}
/** What the user is shown and what the send is checked against: adding or removing a file changes it. */
const draftDigest = (m, atts) => digestOf({
  subject: m.subject ?? "", to: addrs(m.toRecipients), cc: addrs(m.ccRecipients), bcc: addrs(m.bccRecipients),
  body: m.body?.content ?? "", type: m.body?.contentType ?? "", attachments: !!m.hasAttachments,
  files: atts.map((x) => [x.attachment_id, x.name, x.size_bytes]),
});

const draftProps = {
  to: { type: "array", items: { type: "string" }, description: "Recipient email addresses." },
  cc: { type: "array", items: { type: "string" } }, bcc: { type: "array", items: { type: "string" } },
  subject: { type: "string" }, body: { type: "string", description: "Plain text. **like this** is shown in bold when the user's signature (HTML) is used." },
  signature: { type: "boolean", description: "Add the user's email signature (default true when they set a signature file; false to leave it out)." },
};

export const tools = [
  {
    name: "email_create_draft", kind: "write", module: "mail",
    description: "Create a new email as a DRAFT in Outlook Drafts. Nothing is sent. Recipients must be email addresses (resolve names with people_resolve first). Then call email_preview_draft, show the user the preview, and only send with email_send_draft after they approve.",
    inputSchema: { type: "object", properties: draftProps, required: ["to", "subject", "body"] },
    async handler(a, ctx) {
      const to = rcpts(a.to, "to");
      if (!to.length) throw new M365Error("INVALID_ARGUMENT", "to needs at least one email address");
      const subject = safeStr(a.subject, "subject", 255) ?? "";
      const { body, images } = bodyOf(a, ctx);
      const m = await ctx.graph.post("/me/messages", { subject, body, toRecipients: to, ccRecipients: rcpts(a.cc, "cc"), bccRecipients: rcpts(a.bcc, "bcc") });
      await attachSignatureImages(ctx, m.id, images);
      return { draft_id: m.id, created: true, signature: images.length > 0 || body.contentType === "HTML", next_step: "Call email_preview_draft with this draft_id and show the user the preview before sending." };
    },
  },
  {
    name: "email_create_reply_draft", kind: "write", module: "mail",
    description: "Create a reply (or reply-all) to a message as a DRAFT, with your text above the quoted original. Nothing is sent. Use email_preview_draft next, show the user, and send only after approval.",
    inputSchema: { type: "object", properties: {
      message_id: { type: "string" }, comment: { type: "string", description: "Your reply text (plain text)." },
      reply_all: { type: "boolean", description: "Reply to everyone on the message. Default false." }, signature: draftProps.signature }, required: ["message_id", "comment"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const sig = wantsSignature(a, ctx);
      const m = await ctx.graph.post(`/me/messages/${seg(id)}/${a.reply_all ? "createReplyAll" : "createReply"}`, sig ? {} : { comment: safeBody(a.comment) });
      if (sig) await topOfReply(ctx, m.id, a.comment);
      return { draft_id: m.id, created: true, reply_all: !!a.reply_all, signature: sig, next_step: "Call email_preview_draft with this draft_id and show the user the preview before sending." };
    },
  },
  {
    name: "email_create_forward_draft", kind: "write", module: "mail",
    description: "Create a forward of a message as a DRAFT, with your note above the original and its attachments kept. Nothing is sent. Recipients must be email addresses (resolve names with people_resolve first). Then email_preview_draft, show the user, and send only after approval.",
    inputSchema: { type: "object", properties: {
      message_id: { type: "string" }, to: draftProps.to, cc: draftProps.cc,
      comment: { type: "string", description: "Your note above the forwarded message (plain text)." }, signature: draftProps.signature }, required: ["message_id", "to"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const to = rcpts(a.to, "to");
      if (!to.length) throw new M365Error("INVALID_ARGUMENT", "to needs at least one email address");
      const cc = rcpts(a.cc, "cc");
      const sig = wantsSignature(a, ctx);
      const m = await ctx.graph.post(`/me/messages/${seg(id)}/createForward`, { ...(sig ? {} : { comment: safeBody(a.comment) }), toRecipients: to, ...(cc.length ? { ccRecipients: cc } : {}) });
      if (sig) await topOfReply(ctx, m.id, a.comment ?? "");
      return { draft_id: m.id, created: true, forward: true, signature: sig, next_step: "Call email_preview_draft with this draft_id and show the user the preview (including has_attachments) before sending." };
    },
  },
  {
    name: "email_update_draft", kind: "write", module: "mail",
    description: "Change a draft: only the fields you pass are replaced (subject, body, to, cc, bcc). A new body replaces the WHOLE body, including any quoted original of a reply, and gets the user's signature again unless signature is false. Any earlier preview becomes invalid, so preview it again before sending. Refuses a message that is not a draft.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" }, ...draftProps }, required: ["draft_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      await loadDraft(ctx, id);
      const patch = {};
      if (a.subject !== undefined) patch.subject = safeStr(a.subject, "subject", 255) ?? "";
      let images = [];
      if (a.body !== undefined) ({ body: patch.body, images } = bodyOf(a, ctx));
      for (const [k, f] of [["to", "toRecipients"], ["cc", "ccRecipients"], ["bcc", "bccRecipients"]]) if (a[k] !== undefined) patch[f] = rcpts(a[k], k);
      if (!Object.keys(patch).length) throw new M365Error("INVALID_ARGUMENT", "give at least one of: subject, body, to, cc, bcc");
      ctx.staging.clearPreview(id);
      await ctx.graph.patch(`/me/messages/${seg(id)}`, patch);
      await attachSignatureImages(ctx, id, images);
      return { draft_id: id, updated: Object.keys(patch), next_step: "Preview again with email_preview_draft before sending." };
    },
  },
  {
    name: "email_preview_draft", kind: "write", module: "mail",
    description: "Show exactly what a draft will send: recipients, subject, body, the attached files (name and size) and inline images, and a digest. Always show this to the user and get their approval, then pass the digest to email_send_draft. The body is fenced because a reply draft quotes other people's text.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" } }, required: ["draft_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      const m = await loadDraft(ctx, id);
      const atts = await draftAttachments(ctx, m);
      const digest = draftDigest(m, atts);
      ctx.staging.setPreview(id, digest);
      const html = (m.body?.contentType ?? "").toLowerCase() === "html";
      const raw = String(m.body?.content ?? "");
      const { text, truncated } = truncate(html ? htmlToText(raw) : raw, MAX_PREVIEW);
      // A reply or a draft edited in Outlook is HTML: the text below is only a rendering of it, so say what else is in it.
      const all = html ? extractLinks(raw) : [];
      const links = all.slice(0, MAX_LINKS);
      const hidden = html && HIDDEN_MARKUP.test(raw);
      return {
        draft_id: id, to: addrs(m.toRecipients), cc: addrs(m.ccRecipients), bcc: addrs(m.bccRecipients),
        subject: clean(m.subject, 300), has_attachments: !!m.hasAttachments,
        attachments: atts.filter((x) => !x.inline).map(({ attachment_id, name, size_bytes }) => ({ attachment_id, name, size_bytes })),
        inline_images: atts.filter((x) => x.inline).map((x) => x.name),
        body: fence(text, "draft body (may quote other people)", id), body_truncated: truncated,
        ...(html ? { html_draft: true, links_and_images: links, link_count: all.length, links_truncated: all.length > MAX_LINKS, hidden_markup_found: hidden,
          html_warning: "This draft is HTML; the body above is a plain-text rendering. Show the user every link and image address listed and say if hidden_markup_found is true." } : {}),
        digest,
        next_step: truncated || all.length > MAX_LINKS
          ? "This draft is too long or has too many links to preview in full, so it cannot be sent from here. Shorten it or send it from Outlook."
          : "Show the user the recipients, subject and body. Send only after they approve: email_send_draft with this draft_id and digest.",
      };
    },
  },
  {
    name: "email_discard_draft", kind: "write", module: "mail", confirm: true,
    description: "Delete a draft from Outlook Drafts (it may be one the user wrote by hand, so Claude Code asks for confirmation). Refuses a message that is not a draft.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" } }, required: ["draft_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      await loadDraft(ctx, id);
      await ctx.graph.del(`/me/messages/${seg(id)}`);
      ctx.staging.clearPreview(id);
      return { draft_id: id, discarded: true };
    },
  },
  {
    name: "email_send_draft", kind: "write", module: "mail", confirm: true,
    description: "SEND a draft. Sends the email for real and cannot be undone. Requires the digest from email_preview_draft: it refuses if the draft was never previewed, if it changed since the preview, if it has no recipient, or if the text says 'attached' but nothing is attached. Only call it after the user has seen the preview and approved sending.",
    inputSchema: { type: "object", properties: {
      draft_id: { type: "string" }, digest: { type: "string", description: "digest from email_preview_draft." },
      confirm_no_attachment: { type: "boolean", description: "Only if the user confirmed sending without an attachment although the text mentions one." } }, required: ["draft_id", "digest"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      const sendState = ctx.staging.mailSendState(id);
      if (sendState === "sent") throw new M365Error("ALREADY_DONE", "This draft was already sent. Nothing was repeated.");
      if (sendState === "sending") throw new M365Error("SEND_UNCERTAIN", "An earlier attempt to send this draft may or may not have gone through.", { hint: SENT_HINT });
      const prev = ctx.staging.getPreview(id);
      if (!prev) throw new M365Error("NOT_PREVIEWED", "This draft has not been previewed (or it changed since). Call email_preview_draft, show the user, then send.");
      const m = await loadDraft(ctx, id);
      const now = draftDigest(m, await draftAttachments(ctx, m));
      if (String(a.digest ?? "") !== prev.digest) throw new M365Error("DIGEST_MISMATCH", "The digest is not the one from the last preview. Preview again and show the user.");
      if (now !== prev.digest) throw new M365Error("DRAFT_CHANGED", "The draft changed after it was previewed (for example in Outlook). Preview it again and show the user.");
      if (!addrs(m.toRecipients).length && !addrs(m.ccRecipients).length && !addrs(m.bccRecipients).length) throw new M365Error("NO_RECIPIENT", "The draft has no recipient.");
      const isHtml = (m.body?.contentType ?? "").toLowerCase() === "html";
      const full = isHtml ? htmlToText(m.body?.content) : String(m.body?.content ?? "");
      if (full.length > MAX_PREVIEW) throw new M365Error("PREVIEW_TRUNCATED", "The body is longer than what a preview can show in full, so it cannot be sent from here.", { hint: "Shorten the draft, or send it from Outlook." });
      if (isHtml && extractLinks(String(m.body?.content ?? "")).length > MAX_LINKS) throw new M365Error("PREVIEW_TRUNCATED", `The draft has more than ${MAX_LINKS} links or images, more than a preview can list in full, so it cannot be sent from here.`, { hint: "Shorten the draft, or send it from Outlook." });
      if (!m.hasAttachments && !a.confirm_no_attachment) {
        const mine = full.split(QUOTE_START)[0];
        if (ATTACH_PROMISE.test(mine)) throw new M365Error("ATTACHMENT_PROMISE", "The text mentions an attachment but the draft has none.", { hint: "Ask the user: remove the wording, or confirm sending without an attachment (confirm_no_attachment: true)." });
      }
      ctx.staging.claimMailSend(id, prev.digest); // refuses if another process is already sending it
      try {
        await ctx.graph.post(`/me/messages/${seg(id)}/send`);
      } catch (e) {
        if (REFUSED.has(e.status)) { ctx.staging.releaseMailSend(id); throw e; } // a definite refusal: nothing was sent
        throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether the email was sent.", { hint: SENT_HINT });
      }
      ctx.staging.markMailSent(id);
      return { sent: true, draft_id: id, to: addrs(m.toRecipients), subject: clean(m.subject, 300) };
    },
  },
  {
    name: "email_move", kind: "write", module: "mail",
    description: "Move a message to the inbox or archive. To delete a message use email_delete, which asks for confirmation.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, folder: { type: "string", description: "inbox or archive." } }, required: ["message_id", "folder"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const f = String(a.folder ?? "").toLowerCase();
      if (!FOLDERS.includes(f)) throw new M365Error("INVALID_ARGUMENT", `folder must be one of ${FOLDERS.join(", ")}`);
      const m = await ctx.graph.post(`/me/messages/${seg(id)}/move`, { destinationId: f });
      return { moved: true, folder: f, message_id: m.id ?? id };
    },
  },
  {
    name: "email_mark_read", kind: "write", module: "mail",
    description: "Mark a message read or unread.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, is_read: { type: "boolean", description: "Default true." } }, required: ["message_id"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const isRead = a.is_read !== false;
      await ctx.graph.patch(`/me/messages/${seg(id)}`, { isRead });
      return { message_id: id, is_read: isRead };
    },
  },
  {
    name: "email_set_flag", kind: "write", module: "mail",
    description: "Set a message's follow-up flag: flagged, complete or none.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, flag: { type: "string", description: "flagged, complete or none." } }, required: ["message_id", "flag"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const f = FLAGS[String(a.flag ?? "").toLowerCase()];
      if (!f) throw new M365Error("INVALID_ARGUMENT", "flag must be flagged, complete or none");
      await ctx.graph.patch(`/me/messages/${seg(id)}`, { flag: { flagStatus: f } });
      return { message_id: id, flag: f };
    },
  },
  {
    name: "email_add_attachment", kind: "write", module: "mail",
    description: "Attach a file from this computer to a DRAFT. Only files inside the folders the user allowed (M365_ATTACH_DIRS) can be attached, up to 25 MB; anything else is refused, so never copy or move a file to get around that. Nothing is sent: the earlier preview becomes invalid, so call email_preview_draft again and show the user the attachment list before sending.",
    inputSchema: { type: "object", properties: {
      draft_id: { type: "string" }, path: { type: "string", description: "Absolute path of the file." },
      name: { type: "string", description: "Optional file name the recipient sees (default the file's own name)." } }, required: ["draft_id", "path"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      const f = allowedFile(ctx.cfg, a.path);
      await loadDraft(ctx, id);
      const name = a.name !== undefined ? clean(safeStr(a.name, "name", 200) ?? "", 200).trim() || f.name : f.name;
      if (/[\\/]/.test(name)) throw new M365Error("INVALID_ARGUMENT", "name must be a file name, not a path");
      ctx.staging.clearPreview(id);
      const r = await attachBytes(ctx, id, { name, bytes: readAllowed(f), contentType: contentTypeOf(name) });
      return { draft_id: id, attached: true, ...r, next_step: "Preview again with email_preview_draft and show the user the attachments before sending." };
    },
  },
  {
    name: "email_remove_attachment", kind: "write", module: "mail",
    description: "Remove one attachment from a DRAFT (attachment_id from email_preview_draft or email_list_attachments). The earlier preview becomes invalid; preview again before sending.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" }, attachment_id: { type: "string" } }, required: ["draft_id", "attachment_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id"), at = safeId(a.attachment_id, "attachment_id");
      await loadDraft(ctx, id);
      ctx.staging.clearPreview(id);
      await ctx.graph.del(`/me/messages/${seg(id)}/attachments/${seg(at)}`);
      return { draft_id: id, removed: at, next_step: "Preview again with email_preview_draft before sending." };
    },
  },
  {
    name: "email_set_categories", kind: "write", module: "mail",
    description: "Set the Outlook categories of a message (replaces its current list; an empty list clears them). Use names from email_list_categories so they keep their colour; a new name is created without a colour. Reversible, so no confirmation is needed.",
    inputSchema: { type: "object", properties: {
      message_id: { type: "string" },
      categories: { type: "array", items: { type: "string" }, description: "Category names, at most 25. [] clears." } }, required: ["message_id", "categories"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      if (!Array.isArray(a.categories)) throw new M365Error("INVALID_ARGUMENT", "categories must be a list of names ([] clears them)");
      const cats = [];
      for (const c of a.categories) {
        const name = clean(String(c ?? ""), 255).trim();
        if (!name) throw new M365Error("INVALID_ARGUMENT", "a category name is empty");
        if (!cats.some((x) => x.toLowerCase() === name.toLowerCase())) cats.push(name);
      }
      if (cats.length > 25) throw new M365Error("INVALID_ARGUMENT", "at most 25 categories");
      const m = await ctx.graph.patch(`/me/messages/${seg(id)}`, { categories: cats });
      return { message_id: id, categories: Array.isArray(m?.categories) ? m.categories.map((x) => clean(x, 255)) : cats };
    },
  },
  {
    name: "email_delete", kind: "write", module: "mail", confirm: true,
    description: "Delete a message by moving it to Deleted Items. It can be recovered from there; this never permanently deletes.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" } }, required: ["message_id"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      await ctx.graph.post(`/me/messages/${seg(id)}/move`, { destinationId: "deleteditems" });
      return { deleted: true, recoverable: "in Deleted Items", message_id: id };
    },
  },
];
