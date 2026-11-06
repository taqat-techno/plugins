// mail tools that change the mailbox. The safe path for sending is draft -> preview -> send:
//   email_create_draft / email_create_reply_draft  -> a draft in Outlook Drafts (nothing leaves the mailbox)
//   email_preview_draft                            -> exactly what will be sent, plus a digest
//   email_send_draft(draft_id, digest)             -> refuses unless the draft is unchanged since that preview
// Recipients must be email addresses (resolve names with people_resolve); nothing is guessed from a name.
import { EMAIL_RE, M365Error, clean, fence, htmlToText, safeId, safeStr, seg, truncate } from "../util.mjs";
import { digestOf } from "../staging.mjs";

const FOLDERS = ["inbox", "archive", "deleteditems", "junkemail"];
const FLAGS = { flagged: "flagged", complete: "complete", none: "notFlagged" };
const DRAFT_SELECT = "id,subject,toRecipients,ccRecipients,bccRecipients,body,hasAttachments,isDraft,conversationId";
const ATTACH_PROMISE = /\b(attached|attachment|attachments|attaching|enclosed)\b|مرفق|المرفق|مرفقات|ارفقت|أرفقت|إرفاق|ارفاق/i;
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

function bodyOf(a) {
  const fmt = String(a.body_format || "text").toLowerCase();
  if (!["text", "html"].includes(fmt)) throw new M365Error("INVALID_ARGUMENT", "body_format must be text or html");
  const content = safeBody(a.body);
  return { contentType: fmt === "html" ? "HTML" : "Text", content };
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
/** What the user is shown and what the send is checked against. */
const draftDigest = (m) => digestOf({
  subject: m.subject ?? "", to: addrs(m.toRecipients), cc: addrs(m.ccRecipients), bcc: addrs(m.bccRecipients),
  body: m.body?.content ?? "", type: m.body?.contentType ?? "", attachments: !!m.hasAttachments,
});

const draftProps = {
  to: { type: "array", items: { type: "string" }, description: "Recipient email addresses." },
  cc: { type: "array", items: { type: "string" } }, bcc: { type: "array", items: { type: "string" } },
  subject: { type: "string" }, body: { type: "string" },
  body_format: { type: "string", description: "text (default) or html." },
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
      const m = await ctx.graph.post("/me/messages", { subject, body: bodyOf(a), toRecipients: to, ccRecipients: rcpts(a.cc, "cc"), bccRecipients: rcpts(a.bcc, "bcc") });
      return { draft_id: m.id, created: true, next_step: "Call email_preview_draft with this draft_id and show the user the preview before sending." };
    },
  },
  {
    name: "email_create_reply_draft", kind: "write", module: "mail",
    description: "Create a reply (or reply-all) to a message as a DRAFT, with your text above the quoted original. Nothing is sent. Use email_preview_draft next, show the user, and send only after approval.",
    inputSchema: { type: "object", properties: {
      message_id: { type: "string" }, comment: { type: "string", description: "Your reply text (plain text)." },
      reply_all: { type: "boolean", description: "Reply to everyone on the message. Default false." } }, required: ["message_id", "comment"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const m = await ctx.graph.post(`/me/messages/${seg(id)}/${a.reply_all ? "createReplyAll" : "createReply"}`, { comment: safeBody(a.comment) });
      return { draft_id: m.id, created: true, reply_all: !!a.reply_all, next_step: "Call email_preview_draft with this draft_id and show the user the preview before sending." };
    },
  },
  {
    name: "email_update_draft", kind: "write", module: "mail",
    description: "Change a draft: only the fields you pass are replaced (subject, body, to, cc, bcc). Any earlier preview becomes invalid, so preview it again before sending. Refuses a message that is not a draft.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" }, ...draftProps }, required: ["draft_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      await loadDraft(ctx, id);
      const patch = {};
      if (a.subject !== undefined) patch.subject = safeStr(a.subject, "subject", 255) ?? "";
      if (a.body !== undefined) patch.body = bodyOf(a);
      for (const [k, f] of [["to", "toRecipients"], ["cc", "ccRecipients"], ["bcc", "bccRecipients"]]) if (a[k] !== undefined) patch[f] = rcpts(a[k], k);
      if (!Object.keys(patch).length) throw new M365Error("INVALID_ARGUMENT", "give at least one of: subject, body, to, cc, bcc");
      await ctx.graph.patch(`/me/messages/${seg(id)}`, patch);
      ctx.staging.clearPreview(id);
      return { draft_id: id, updated: Object.keys(patch), next_step: "Preview again with email_preview_draft before sending." };
    },
  },
  {
    name: "email_preview_draft", kind: "write", module: "mail",
    description: "Show exactly what a draft will send: recipients, subject, body, whether it has attachments, and a digest. Always show this to the user and get their approval, then pass the digest to email_send_draft. The body is fenced because a reply draft quotes other people's text.",
    inputSchema: { type: "object", properties: { draft_id: { type: "string" } }, required: ["draft_id"] },
    async handler(a, ctx) {
      const id = safeId(a.draft_id, "draft_id");
      const m = await loadDraft(ctx, id);
      const digest = draftDigest(m);
      ctx.staging.setPreview(id, digest);
      const html = (m.body?.contentType ?? "").toLowerCase() === "html";
      const { text, truncated } = truncate(html ? htmlToText(m.body?.content) : String(m.body?.content ?? ""), 20_000);
      return {
        draft_id: id, to: addrs(m.toRecipients), cc: addrs(m.ccRecipients), bcc: addrs(m.bccRecipients),
        subject: clean(m.subject, 300), has_attachments: !!m.hasAttachments,
        body: fence(text, "draft body (may quote other people)", id), body_truncated: truncated, digest,
        next_step: "Show the user the recipients, subject and body. Send only after they approve: email_send_draft with this draft_id and digest.",
      };
    },
  },
  {
    name: "email_discard_draft", kind: "write", module: "mail",
    description: "Delete a draft from Outlook Drafts. Refuses a message that is not a draft.",
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
      if (ctx.staging.wasMailSent(id)) throw new M365Error("ALREADY_DONE", "This draft was already sent. Nothing was repeated.");
      const prev = ctx.staging.getPreview(id);
      if (!prev) throw new M365Error("NOT_PREVIEWED", "This draft has not been previewed (or it changed since). Call email_preview_draft, show the user, then send.");
      const m = await loadDraft(ctx, id);
      const now = draftDigest(m);
      if (String(a.digest ?? "") !== prev.digest) throw new M365Error("DIGEST_MISMATCH", "The digest is not the one from the last preview. Preview again and show the user.");
      if (now !== prev.digest) throw new M365Error("DRAFT_CHANGED", "The draft changed after it was previewed (for example in Outlook). Preview it again and show the user.");
      if (!addrs(m.toRecipients).length && !addrs(m.ccRecipients).length && !addrs(m.bccRecipients).length) throw new M365Error("NO_RECIPIENT", "The draft has no recipient.");
      if (!m.hasAttachments && !a.confirm_no_attachment) {
        const html = (m.body?.contentType ?? "").toLowerCase() === "html";
        const full = html ? htmlToText(m.body?.content) : String(m.body?.content ?? "");
        const mine = full.split(QUOTE_START)[0];
        if (ATTACH_PROMISE.test(mine)) throw new M365Error("ATTACHMENT_PROMISE", "The text mentions an attachment but the draft has none.", { hint: "Ask the user: remove the wording, or confirm sending without an attachment (confirm_no_attachment: true)." });
      }
      await ctx.graph.post(`/me/messages/${seg(id)}/send`);
      ctx.staging.markMailSent(id);
      return { sent: true, draft_id: id, to: addrs(m.toRecipients), subject: clean(m.subject, 300) };
    },
  },
  {
    name: "email_move", kind: "write", module: "mail",
    description: "Move a message to inbox, archive, deleteditems or junkemail.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, folder: { type: "string", description: "inbox, archive, deleteditems or junkemail." } }, required: ["message_id", "folder"] },
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
