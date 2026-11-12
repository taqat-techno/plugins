// Teams writes: stage -> commit, with a double-send guard. 'sending' is saved BEFORE the request, so if the
// outcome is unknown (timeout, 5xx) a repeat is refused and the user is told to look at the chat instead.
//
// Files: Microsoft Graph cannot attach bytes to a chat message. A file in a chat is a file in the sender's OneDrive
// (Teams' own folder "Microsoft Teams Chat Files"), shared with the chat's members, and referenced from the message.
// Small pictures travel inside the message instead (hostedContents) and show as pictures; they touch no OneDrive.
// Nothing is uploaded or shared at stage time: the stage records each file's real path, size and sha256 and the exact
// people it will be shared with, the digest covers all of it, and commit refuses if a file changed since.
import { createHash } from "node:crypto";
import { extname } from "node:path";
import { M365Error, UNTRUSTED_FIELDS, clean, safeId, safeStr, seg } from "../util.mjs";
import { allowedFile, contentTypeOf, readAllowed } from "../attach.mjs";
import { formatText } from "../signature.mjs";

// Statuses that mean Microsoft did not accept the request. Anything else (408, 409, 5xx, a timeout) is an unknown outcome.
const REFUSED = new Set([400, 401, 403, 404, 405, 422, 429]);

const MAX_TEXT = 8000, MAX_FILES = 10;
const PICTURE_MAX = 2 * 1024 * 1024, PICTURES_TOTAL_MAX = 3 * 1024 * 1024;
const CHAT_FILES_FOLDER = "Microsoft Teams Chat Files";
const PICTURE_MAGIC = { ".png": [0x89, 0x50, 0x4e, 0x47], ".jpg": [0xff, 0xd8, 0xff], ".jpeg": [0xff, 0xd8, 0xff], ".gif": [0x47, 0x49, 0x46, 0x38] };

const FORMAT_HELP = "Plain text; never HTML. Marks the plugin turns into real formatting: **bold**, *italic*, __underline__, ==highlight==, ~~strike~~, lines starting \"- \" (bullets) or \"1. \" (numbered). Blank line = new paragraph.";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

/** Message text: line breaks and tabs are fine (paragraphs, lists), other control characters are not. */
function messageText(v) {
  if (v === undefined || v === null) return "";
  const s = String(v).replace(/\r\n?/g, "\n");
  if (s.length > MAX_TEXT) throw new M365Error("INVALID_ARGUMENT", `text is too long (max ${MAX_TEXT})`);
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(s)) throw new M365Error("INVALID_ARGUMENT", "text contains control characters");
  return s.trim();
}

/** A name OneDrive accepts, keeping the extension. */
function driveName(name) {
  const s = String(name).replace(/["*:<>?/\\|\u0000-\u001f]/g, "_").replace(/^[\s.]+|[\s.]+$/g, "").slice(0, 150);
  return s || "file";
}

const isPicture = (real, bytes) => {
  const want = PICTURE_MAGIC[extname(real).toLowerCase()];
  return Boolean(want) && bytes.length <= PICTURE_MAX && want.every((b, i) => bytes[i] === b);
};

/** Check every attachment now (same rules as email attachments) and record exactly what will be sent. */
function stageFiles(ctx, list) {
  if (list === undefined || list === null) return [];
  if (!Array.isArray(list) || list.length > MAX_FILES) throw new M365Error("INVALID_ARGUMENT", `attachments must be a list of at most ${MAX_FILES} files`);
  let pictures = 0;
  return list.map((item, i) => {
    if (!item || typeof item !== "object") throw new M365Error("INVALID_ARGUMENT", `attachments[${i}] must be an object with path or chat_image`);
    if ((item.path === undefined || item.path === "") && item.chat_image !== undefined) {
      // In Claude Code the plugin's hook saves the pasted image and fills in path before this runs.
      throw new M365Error("CHAT_IMAGE_UNAVAILABLE", "That pasted image could not be found or saved, so nothing was staged.",
        { hint: "Pasted images can be sent only in Claude Code with the plugin's hooks on. Otherwise ask the user to save the image as a file and give its path." });
    }
    if (item.path === undefined || item.path === "") throw new M365Error("INVALID_ARGUMENT", `attachments[${i}]: give path (a file) or chat_image (a pasted image)`);
    const f = allowedFile(ctx.cfg, item.path);
    const bytes = readAllowed(f);
    const given = item.name !== undefined ? clean(safeStr(item.name, "name", 200) ?? "", 200).trim() : "";
    let as = "file";
    if (isPicture(f.real, bytes) && pictures + bytes.length <= PICTURES_TOTAL_MAX) { as = "picture"; pictures += bytes.length; }
    return { path: f.real, name: driveName(given || f.name), size: bytes.length, sha256: sha256(bytes), as };
  });
}

/** Re-read a staged file at send time: still allowed, and byte-for-byte what the person approved. */
function staged(ctx, file) {
  const f = allowedFile(ctx.cfg, file.path);
  const bytes = readAllowed(f);
  if (bytes.length !== file.size || sha256(bytes) !== file.sha256) {
    throw new M365Error("FILE_CHANGED", `${file.name} changed after the preview, so nothing was sent.`, { hint: "Stage the message again and show the user the new preview." });
  }
  return bytes;
}

/** Upload one file to the chat-files folder, share it with exactly the staged people, and describe it for the message. */
async function uploadAndShare(ctx, file, bytes, shareWith, uploaded) {
  const path = `/me/drive/root:/${seg(CHAT_FILES_FOLDER)}/${seg(file.name)}:/content?@microsoft.graph.conflictBehavior=rename`;
  const put = await ctx.graph.putBytes(path, bytes, contentTypeOf(file.name));
  if (!put.id) throw new M365Error("GRAPH_ERROR", "OneDrive did not confirm the upload.");
  uploaded.push(put.id);
  const item = await ctx.graph.get(`/me/drive/items/${seg(put.id)}?$select=id,name,eTag,webUrl,webDavUrl`);
  const guid = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i.exec(String(item.eTag ?? ""))?.[1];
  const url = item.webDavUrl ?? item.webUrl;
  if (!guid || !url) throw new M365Error("GRAPH_ERROR", "OneDrive did not return what Teams needs to show the file.");
  if (shareWith.length) {
    await ctx.graph.post(`/me/drive/items/${seg(put.id)}/invite`, {
      recipients: shareWith.map((email) => ({ email })), requireSignIn: true, sendInvitation: false, roles: ["read"],
    });
  }
  return { id: guid, contentType: "reference", contentUrl: url, name: item.name ?? file.name };
}

/** The message Graph receives. Text-only, unformatted messages stay exactly as before (plain text). */
async function buildMessage(ctx, p, uploaded) {
  const files = p.files ?? [];
  const fmt = formatText(p.text);
  if (!files.length && !fmt.formatted) return { body: { contentType: "text", content: p.text } };
  let html = p.text ? fmt.html : "";
  const hostedContents = [], attachments = [];
  for (const file of files) {
    const bytes = staged(ctx, file);
    if (file.as === "picture") {
      const n = String(hostedContents.length + 1);
      hostedContents.push({ "@microsoft.graph.temporaryId": n, contentBytes: bytes.toString("base64"), contentType: contentTypeOf(file.path) });
      html += `<p><img src="../hostedContents/${n}/$value" alt="${esc(file.name)}"></p>`;
    } else {
      const att = await uploadAndShare(ctx, file, bytes, p.share_with ?? [], uploaded);
      attachments.push(att);
      html += `<attachment id="${att.id}"></attachment>`;
    }
  }
  return { body: { contentType: "html", content: html }, ...(attachments.length ? { attachments } : {}), ...(hostedContents.length ? { hostedContents } : {}) };
}

/** Nothing reached the chat: take back the files this attempt uploaded (to the recycle bin). Best effort. */
async function removeUploads(ctx, uploaded) {
  for (const id of uploaded) { try { await ctx.graph.del(`/me/drive/items/${seg(id)}`); } catch { /* left in the chat-files folder */ } }
}

export const tools = [
  {
    name: "teams_stage", kind: "write", module: "teams",
    description: "Prepare a Teams chat message without sending it: shows the chat's members, the exact text and any files, and returns a stage_id and digest. Show it to the user, then call teams_commit after they approve. Files: attachments with path (a file on this computer) or chat_image (an image the user pasted into this chat, 1 = the most recent). Small pictures show inside the message; other files are uploaded to the user's OneDrive at send time and shared read-only with exactly the chat members listed in the preview. Keys, tokens and sign-in files are never sent; a refusal is final. Nothing is uploaded or sent by this call. Get chat_id from teams_find_chat.",
    inputSchema: { type: "object", properties: {
      chat_id: { type: "string" },
      text: { type: "string", description: `Message text (max ${MAX_TEXT} characters; optional when there are attachments). ${FORMAT_HELP}` },
      attachments: { type: "array", maxItems: MAX_FILES, description: "Files to send with the message.", items: { type: "object", properties: {
        path: { type: "string", description: "Absolute path of a file on this computer. Give this or chat_image." },
        chat_image: { type: "number", description: "An image the user pasted into this chat: 1 = the most recent. Claude Code only." },
        name: { type: "string", description: "Optional file name the chat members see." } } } },
    }, required: ["chat_id"] },
    async handler(a, ctx) {
      const chatId = safeId(a.chat_id, "chat_id");
      const text = messageText(a.text);
      const files = stageFiles(ctx, a.attachments);
      if (!text && !files.length) throw new M365Error("INVALID_ARGUMENT", "give text, attachments, or both");
      const toShare = files.some((f) => f.as === "file");
      if (toShare && !ctx.cfg.modules.includes("files")) {
        throw new M365Error("ACCESS_NEEDED", "Sending a file in Teams puts it in OneDrive, and the files module is off.", { hint: "Only the user can turn on the 'files' module in the plugin settings. Small pictures (PNG, JPEG, GIF up to 2 MB) can be sent without it." });
      }
      const [members, chat] = await Promise.allSettled([ctx.graph.get(`/chats/${seg(chatId)}/members`), ctx.graph.get(`/chats/${seg(chatId)}?$select=topic,chatType`)]);
      if (members.status === "rejected" && chat.status === "rejected") throw members.reason;
      const list = members.status === "fulfilled" ? members.value.value ?? [] : null;
      const payload = { chat_id: chatId, text };
      let sharing;
      if (files.length) payload.files = files;
      if (toShare) {
        // The people who get access are fixed now, shown in the preview and covered by the digest: a member added later gets nothing silently.
        if (!list) throw new M365Error("GRAPH_ERROR", "The chat's members could not be read, so a file cannot be shared with them.", { hint: "Try again, or send the text without the file." });
        const me = await ctx.graph.get("/me?$select=id");
        const others = list.filter((m) => m.userId !== me.id);
        payload.share_with = [...new Set(others.map((m) => (m.email ?? "").toLowerCase()).filter(Boolean))].sort();
        sharing = {
          read_access_for: payload.share_with,
          no_access_for: others.filter((m) => !m.email).map((m) => clean(m.displayName, 120) || "a member without an address"),
          where: `your OneDrive folder "${CHAT_FILES_FOLDER}"`,
        };
      }
      const st = ctx.staging.create("teams", payload);
      return {
        stage_id: st.id, digest: st.digest,
        preview: {
          chat_id: chatId, kind: chat.status === "fulfilled" ? chat.value.chatType ?? null : null,
          topic: chat.status === "fulfilled" ? clean(chat.value.topic, 200) || null : null,
          members: list ? list.map((m) => ({ name: clean(m.displayName, 120), email: (m.email ?? "").toLowerCase() || null })) : "unavailable",
          text,
          ...(formatText(text).formatted ? { formatted: true } : {}),
          ...(files.length ? { attachments: files.map((f) => ({ name: f.name, size_bytes: f.size, from: f.path, sent_as: f.as === "picture" ? "a picture inside the message" : "a file uploaded to OneDrive and shared" })) } : {}),
          ...(sharing ? { sharing } : {}),
        },
        note: UNTRUSTED_FIELDS,
        next_step: files.length
          ? "Show the user the members, the text, every file (name, size, where it comes from) and who gets access. After they approve, call teams_commit with stage_id and digest."
          : "Show the user the members and the text. After they approve, call teams_commit with stage_id and digest.",
      };
    },
  },
  {
    name: "teams_commit", kind: "write", module: "teams", confirm: true,
    description: "SEND the Teams message prepared by teams_stage, with its files. It is delivered at once and cannot be unsent. Needs the stage_id and digest the user saw. Refuses a repeat: if an earlier attempt may or may not have gone through, check teams_read_chat instead of retrying. Refuses if a file changed since the preview. Only call it after the user approved the preview.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" }, digest: { type: "string" } }, required: ["stage_id", "digest"] },
    async handler(a, ctx) {
      const st = ctx.staging.transition(a.stage_id, "teams", a.digest, "sending"); // check + claim in one locked step
      const uploaded = [];
      let message;
      try {
        message = await buildMessage(ctx, st.payload, uploaded);
      } catch (e) {
        // Nothing was posted to the chat yet, so this is never an "unknown outcome": undo the uploads and allow a retry.
        await removeUploads(ctx, uploaded);
        ctx.staging.set(st.id, { state: "staged" });
        if (e instanceof M365Error) { e.message = `${e.message} Nothing was sent to the chat.`; throw e; }
        throw new M365Error("GRAPH_ERROR", "A file could not be prepared. Nothing was sent to the chat.");
      }
      let r;
      try {
        r = await ctx.graph.post(`/chats/${seg(st.payload.chat_id)}/messages`, message);
      } catch (e) {
        if (REFUSED.has(e.status)) { await removeUploads(ctx, uploaded); ctx.staging.set(st.id, { state: "staged" }); throw e; } // a definite refusal: nothing was sent
        throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether the message was sent.", { hint: "Check the chat with teams_read_chat before trying again. This stage will not be sent a second time automatically." });
      }
      ctx.staging.set(st.id, { state: "sent", message_id: r.id });
      const files = st.payload.files ?? [];
      return { sent: true, message_id: r.id ?? null, chat_id: st.payload.chat_id, ...(files.length ? { attachments: files.map((f) => f.name) } : {}) };
    },
  },
  {
    name: "teams_cancel", kind: "write", module: "teams",
    description: "Cancel a staged Teams message that has not been sent.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" } }, required: ["stage_id"] },
    async handler(a, ctx) {
      const st = ctx.staging.move(a.stage_id, "teams", "staged", "cancelled");
      return { cancelled: true, stage_id: st.id };
    },
  },
];
