// Teams writes: stage -> commit, with a double-send guard. 'sending' is saved BEFORE the request, so if the
// outcome is unknown (timeout, 5xx) a repeat is refused and the user is told to look at the chat instead.
//
// One stage tool covers every outward Teams write, so there is one preview format and one confirm-gated commit:
//   an existing chat (chat_id), a new chat (to: addresses), a channel post or thread reply (team_id + channel_id),
//   and an edit of the user's own chat message (edit_message_id). teams_delete_message is a separate confirm-gated call.
//
// Files: Microsoft Graph cannot attach bytes to a chat message. A file in a chat is a file in the sender's OneDrive
// (Teams' own folder "Microsoft Teams Chat Files"), shared with the chat's members, and referenced from the message.
// Small pictures travel inside the message instead (hostedContents) and show as pictures; they touch no OneDrive.
// Nothing is uploaded or shared at stage time: the stage records each file's real path, size and sha256 and the exact
// people it will be shared with, the digest covers all of it, and commit refuses if a file changed since.
//
// Mentions and quoted replies name people and messages by the ids Microsoft returned at stage time; the model never
// writes markup, and every person mentioned is shown in the preview.
import { createHash } from "node:crypto";
import { extname } from "node:path";
import { EMAIL_RE, M365Error, UNTRUSTED_FIELDS, clean, htmlToText, safeId, safeStr, seg, truncate } from "../util.mjs";
import { allowedFile, contentTypeOf, readAllowed } from "../attach.mjs";
import { formatText } from "../signature.mjs";

// Statuses that mean Microsoft did not accept the request. Anything else (408, 409, 5xx, a timeout) is an unknown outcome.
const REFUSED = new Set([400, 401, 403, 404, 405, 422, 429]);

const MAX_TEXT = 8000, MAX_FILES = 10, MAX_MENTIONS = 20, MAX_NEW_CHAT = 20;
const PICTURE_MAX = 2 * 1024 * 1024, PICTURES_TOTAL_MAX = 3 * 1024 * 1024;
const CHAT_FILES_FOLDER = "Microsoft Teams Chat Files";
const PICTURE_MAGIC = { ".png": [0x89, 0x50, 0x4e, 0x47], ".jpg": [0xff, 0xd8, 0xff], ".jpeg": [0xff, 0xd8, 0xff], ".gif": [0x47, 0x49, 0x46, 0x38] };

const FORMAT_HELP = "Plain text; never HTML. Marks the plugin turns into real formatting: **bold**, *italic*, __underline__, ==highlight==, ~~strike~~, lines starting \"- \" (bullets) or \"1. \" (numbered). Blank line = new paragraph.";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const lower = (s) => String(s ?? "").toLowerCase();

/** Message text: line breaks and tabs are fine (paragraphs, lists), other control characters are not. */
function messageText(v) {
  if (v === undefined || v === null) return "";
  const s = String(v).replace(/\r\n?/g, "\n");
  if (s.length > MAX_TEXT) throw new M365Error("INVALID_ARGUMENT", `text is too long (max ${MAX_TEXT})`);
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(s)) throw new M365Error("INVALID_ARGUMENT", "text contains control characters");
  return s.trim();
}

function addresses(v, field, max) {
  if (v === undefined || v === null) return [];
  if (!Array.isArray(v) || v.length > max) throw new M365Error("INVALID_ARGUMENT", `${field} must be a list of at most ${max} email addresses`);
  const out = v.map((x) => lower(safeStr(x, field, 254)).trim());
  for (const e of out) if (!EMAIL_RE.test(e)) throw new M365Error("INVALID_ARGUMENT", `${field}: "${e}" is not an email address. Resolve names with people_resolve first.`);
  return [...new Set(out)];
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

/** Where a staged write goes, as the preview and the commit prompt describe it. */
function targetPath(p, chatId = p.chat_id) {
  if (p.channel) {
    const base = `/teams/${seg(p.channel.team_id)}/channels/${seg(p.channel.channel_id)}/messages`;
    return p.channel.reply_to ? `${base}/${seg(p.channel.reply_to)}/replies` : base;
  }
  return `/chats/${seg(chatId)}/messages`;
}

/** The message Graph receives. Text-only, unformatted messages without mentions or quotes stay plain text. */
async function buildMessage(ctx, p, uploaded) {
  const files = p.files ?? [];
  const mentions = p.mentions ?? [];
  const fmt = formatText(p.text);
  if (!files.length && !mentions.length && !p.quote && !fmt.formatted) return { body: { contentType: "text", content: p.text } };
  let html = "";
  const attachments = [], hostedContents = [];
  if (p.quote) {
    attachments.push({ id: p.quote.message_id, contentType: "messageReference", content: JSON.stringify({
      messageId: p.quote.message_id, messagePreview: p.quote.preview, messageSender: { user: { id: p.quote.from_id, displayName: p.quote.from_name, userIdentityType: "aadUser" } } }) });
    html += `<attachment id="${esc(p.quote.message_id)}"></attachment>`;
  }
  if (mentions.length) html += `<p>${mentions.map((m, i) => `<at id="${i}">${esc(m.name)}</at>`).join(" ")}</p>`;
  if (p.text) html += fmt.formatted ? fmt.html : `<p>${esc(p.text).replace(/\n/g, "<br>")}</p>`;
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
  return {
    body: { contentType: "html", content: html },
    ...(attachments.length ? { attachments } : {}),
    ...(hostedContents.length ? { hostedContents } : {}),
    ...(mentions.length ? { mentions: mentions.map((m, i) => ({ id: i, mentionText: m.name, mentioned: { user: { id: m.id, displayName: m.name, userIdentityType: "aadUser" } } })) } : {}),
  };
}

/** Nothing reached the chat: take back the files this attempt uploaded (to the recycle bin). Best effort. */
async function removeUploads(ctx, uploaded) {
  for (const id of uploaded) { try { await ctx.graph.del(`/me/drive/items/${seg(id)}`); } catch { /* left in the chat-files folder */ } }
}

const meOf = (ctx) => ctx.graph.get("/me?$select=id,displayName");

/** A directory user by email (mail or sign-in name). One exact match or a clear refusal: never a guess. */
async function userByEmail(ctx, email) {
  const q = email.replace(/'/g, "''");
  const j = await ctx.graph.get(`/users?$filter=${encodeURIComponent(`mail eq '${q}' or userPrincipalName eq '${q}'`)}&$select=id,displayName,mail,userPrincipalName&$top=2`);
  const hits = j.value ?? [];
  if (hits.length !== 1) throw new M365Error("NOT_FOUND", `${email} is not ${hits.length ? "a single" : "a"} person in your organization's directory.`, { hint: "Check the address with people_resolve. People outside the organization cannot be added to a new chat from here." });
  return { id: hits[0].id, name: clean(hits[0].displayName, 120) || email, email };
}

/** A message the signed-in user wrote, for edit / delete. */
async function ownMessage(ctx, chatId, messageId) {
  const [me, m] = await Promise.all([meOf(ctx), ctx.graph.get(`/chats/${seg(chatId)}/messages/${seg(messageId)}`)]);
  if (m.deletedDateTime) throw new M365Error("ALREADY_DONE", "That message is already deleted.");
  if (m.from?.user?.id !== me.id) throw new M365Error("NOT_YOUR_MESSAGE", "Only messages you wrote can be edited or deleted from here.");
  const html = lower(m.body?.contentType) === "html";
  return truncate(html ? htmlToText(m.body?.content) : String(m.body?.content ?? ""), 500).text;
}

/** Mentions: people who are members of the target (or, in a channel, people in the directory). */
function pickMentions(list, pool) {
  const want = addresses(list, "mentions", MAX_MENTIONS);
  return want.map((email) => {
    const hit = pool.find((m) => m.email === email);
    if (!hit) throw new M365Error("INVALID_ARGUMENT", `${email} is not a member of this chat, so they cannot be mentioned here.`);
    return { id: hit.id, name: hit.name, email };
  });
}

export const tools = [
  {
    name: "teams_stage", kind: "write", module: "teams",
    description: "Prepare a Teams message without sending it; returns a preview, stage_id and digest. Show the preview, then teams_commit after the user approves. Where: chat_id (teams_find_chat), or to (addresses: starts a 1:1 or group chat), or team_id + channel_id (a channel post; reply_to_message_id answers in that thread). edit_message_id changes the user's own chat message. Extras: attachments (path, or chat_image for an image pasted into this chat), mentions (member addresses to @mention), quote_message_id (quote a chat message). Small pictures show inside the message; other files are uploaded to the user's OneDrive at send time and shared read-only with exactly the people in the preview. Keys and token files are never sent; a refusal is final. Nothing is sent by this call.",
    inputSchema: { type: "object", properties: {
      chat_id: { type: "string", description: "An existing chat." },
      to: { type: "array", items: { type: "string" }, description: "Start a new chat with these email addresses (1 = a 1:1 chat)." },
      topic: { type: "string", description: "Name of a new group chat (optional)." },
      team_id: { type: "string" }, channel_id: { type: "string" },
      reply_to_message_id: { type: "string", description: "Channel only: the thread's first message, to reply in that thread." },
      edit_message_id: { type: "string", description: "Chat only: replace the text of a message you sent." },
      quote_message_id: { type: "string", description: "Chat only: quote this message above yours." },
      mentions: { type: "array", items: { type: "string" }, description: "Email addresses to @mention (members of the chat, or people in the organization for a channel)." },
      text: { type: "string", description: `Message text (max ${MAX_TEXT}; optional when there are attachments). ${FORMAT_HELP}` },
      attachments: { type: "array", maxItems: MAX_FILES, description: "Files to send with the message.", items: { type: "object", properties: {
        path: { type: "string", description: "Absolute path of a file on this computer. Give this or chat_image." },
        chat_image: { type: "number", description: "An image the user pasted into this chat: 1 = the most recent. Claude Code only." },
        name: { type: "string", description: "Optional file name the members see." } } } },
    } },
    async handler(a, ctx) {
      const text = messageText(a.text);
      const has = (k) => a[k] !== undefined && a[k] !== null && a[k] !== "" && !(Array.isArray(a[k]) && !a[k].length);
      const where = [has("chat_id"), has("to"), has("team_id") || has("channel_id")].filter(Boolean).length;
      if (where !== 1) throw new M365Error("INVALID_ARGUMENT", "give exactly one of: chat_id, to (a new chat), or team_id + channel_id");
      const payload = { text };
      const preview = { text };
      let pool = null; // people who may be mentioned / who get access to files

      if (has("edit_message_id")) {
        if (!has("chat_id")) throw new M365Error("INVALID_ARGUMENT", "edit_message_id works for chat messages only (give chat_id)");
        for (const k of ["attachments", "mentions", "quote_message_id"]) if (has(k)) throw new M365Error("INVALID_ARGUMENT", `${k} cannot be used when editing a message`);
        if (!text) throw new M365Error("INVALID_ARGUMENT", "give the new text");
        payload.chat_id = safeId(a.chat_id, "chat_id");
        payload.edit = { message_id: safeId(a.edit_message_id, "edit_message_id") };
        preview.action = "edit your message";
        preview.chat_id = payload.chat_id;
        preview.current_text = await ownMessage(ctx, payload.chat_id, payload.edit.message_id);
        const st = ctx.staging.create("teams", payload);
        return { stage_id: st.id, digest: st.digest, preview, note: UNTRUSTED_FIELDS,
          next_step: "Show the user the current and the new text. After they approve, call teams_commit with stage_id and digest." };
      }

      const files = stageFiles(ctx, a.attachments);
      if (!text && !files.length) throw new M365Error("INVALID_ARGUMENT", "give text, attachments, or both");
      if (files.length) payload.files = files;
      const toShare = files.some((f) => f.as === "file");
      if (toShare && !ctx.cfg.modules.includes("files")) {
        throw new M365Error("ACCESS_NEEDED", "Sending a file in Teams puts it in OneDrive, and the files module is off.", { hint: "Only the user can turn on the 'files' module in the plugin settings. Small pictures (PNG, JPEG, GIF up to 2 MB) can be sent without it." });
      }

      if (has("team_id") || has("channel_id")) {
        if (!ctx.cfg.modules.includes("channels")) throw new M365Error("ACCESS_NEEDED", "Posting in a team channel needs the channels module, which is off.", { hint: "Only the user can turn on the 'channels' module in the plugin settings (it needs an admin's consent once)." });
        if (toShare) throw new M365Error("INVALID_ARGUMENT", "Files cannot be posted in a channel from here yet; pictures can. Share the file with onedrive_share_link and put the link in the text.");
        if (has("quote_message_id")) throw new M365Error("INVALID_ARGUMENT", "In a channel, answer a message with reply_to_message_id (a thread reply) instead of quote_message_id.");
        const team = safeId(a.team_id, "team_id"), channel = safeId(a.channel_id, "channel_id");
        payload.channel = { team_id: team, channel_id: channel, ...(has("reply_to_message_id") ? { reply_to: safeId(a.reply_to_message_id, "reply_to_message_id") } : {}) };
        const [t, c] = await Promise.allSettled([ctx.graph.get(`/teams/${seg(team)}?$select=displayName`), ctx.graph.get(`/teams/${seg(team)}/channels/${seg(channel)}?$select=displayName,membershipType`)]);
        if (c.status === "rejected") throw c.reason;
        preview.action = payload.channel.reply_to ? "reply in a channel thread" : "post in a channel";
        preview.team = t.status === "fulfilled" ? clean(t.value.displayName, 200) : null;
        preview.channel = clean(c.value.displayName, 200);
        preview.visible_to = "everyone who can see this channel";
        if (payload.channel.reply_to) {
          const root = await ctx.graph.get(`/teams/${seg(team)}/channels/${seg(channel)}/messages/${seg(payload.channel.reply_to)}`);
          preview.replying_to = { from: clean(root.from?.user?.displayName, 120) || null, text: truncate(htmlToText(root.body?.content), 300).text };
        }
        if (has("mentions")) {
          const want = addresses(a.mentions, "mentions", MAX_MENTIONS);
          pool = [];
          for (const e of want) pool.push(await userByEmail(ctx, e));
        }
      } else if (has("to")) {
        const to = addresses(a.to, "to", MAX_NEW_CHAT);
        const me = await meOf(ctx);
        const people = [];
        for (const e of to) people.push(await userByEmail(ctx, e));
        const others = people.filter((p) => p.id !== me.id);
        if (!others.length) throw new M365Error("INVALID_ARGUMENT", "to must name at least one person other than you");
        if (has("quote_message_id")) throw new M365Error("INVALID_ARGUMENT", "quote_message_id needs an existing chat (chat_id)");
        const topic = others.length > 1 && has("topic") ? clean(safeStr(a.topic, "topic", 250), 250).trim() || null : null;
        payload.new_chat = { kind: others.length === 1 ? "oneOnOne" : "group", me: me.id, members: others.map((p) => ({ id: p.id, email: p.email })), ...(topic ? { topic } : {}) };
        preview.action = others.length === 1 ? "message this person (opens your 1:1 chat with them, or starts it)" : "start a NEW group chat";
        preview.members = [{ name: clean(me.displayName, 120), email: "you" }, ...others.map((p) => ({ name: p.name, email: p.email }))];
        if (topic) preview.topic = topic;
        pool = others;
      } else {
        const chatId = safeId(a.chat_id, "chat_id");
        payload.chat_id = chatId;
        const [members, chat] = await Promise.allSettled([ctx.graph.get(`/chats/${seg(chatId)}/members`), ctx.graph.get(`/chats/${seg(chatId)}?$select=topic,chatType`)]);
        if (members.status === "rejected" && chat.status === "rejected") throw members.reason;
        const list = members.status === "fulfilled" ? members.value.value ?? [] : null;
        preview.action = "send in this chat";
        preview.chat_id = chatId;
        preview.kind = chat.status === "fulfilled" ? chat.value.chatType ?? null : null;
        preview.topic = chat.status === "fulfilled" ? clean(chat.value.topic, 200) || null : null;
        preview.members = list ? list.map((m) => ({ name: clean(m.displayName, 120), email: lower(m.email) || null })) : "unavailable";
        if (toShare || has("mentions")) {
          if (!list) throw new M365Error("GRAPH_ERROR", "The chat's members could not be read.", { hint: "Try again, or send the text without files and mentions." });
          const me = await meOf(ctx);
          pool = list.filter((m) => m.userId !== me.id).map((m) => ({ id: m.userId, name: clean(m.displayName, 120), email: lower(m.email), noEmail: !m.email }));
        }
        if (has("quote_message_id")) {
          const q = await ctx.graph.get(`/chats/${seg(chatId)}/messages/${seg(safeId(a.quote_message_id, "quote_message_id"))}`);
          const qText = truncate(htmlToText(lower(q.body?.contentType) === "html" ? q.body?.content : esc(q.body?.content ?? "")), 300).text;
          payload.quote = { message_id: q.id, from_id: q.from?.user?.id ?? null, from_name: clean(q.from?.user?.displayName, 120) || "", preview: qText };
          preview.quoting = { from: payload.quote.from_name || null, text: qText };
        }
      }

      if (has("mentions")) {
        payload.mentions = pickMentions(a.mentions, pool ?? []);
        preview.mentions = payload.mentions.map((m) => ({ name: m.name, email: m.email }));
      }
      if (toShare) {
        // The people who get access are fixed now, shown in the preview and covered by the digest: a member added later gets nothing silently.
        payload.share_with = [...new Set((pool ?? []).map((m) => m.email).filter(Boolean))].sort();
        preview.sharing = {
          read_access_for: payload.share_with,
          no_access_for: (pool ?? []).filter((m) => m.noEmail).map((m) => m.name || "a member without an address"),
          where: `your OneDrive folder "${CHAT_FILES_FOLDER}"`,
        };
      }
      if (formatText(text).formatted) preview.formatted = true;
      if (files.length) preview.attachments = files.map((f) => ({ name: f.name, size_bytes: f.size, from: f.path, sent_as: f.as === "picture" ? "a picture inside the message" : "a file uploaded to OneDrive and shared" }));
      const st = ctx.staging.create("teams", payload);
      return {
        stage_id: st.id, digest: st.digest, preview, note: UNTRUSTED_FIELDS,
        next_step: "Show the user where it goes (the action, members or channel), the text, every mention and file, and who gets access. After they approve, call teams_commit with stage_id and digest.",
      };
    },
  },
  {
    name: "teams_commit", kind: "write", module: "teams", confirm: true,
    description: "SEND (or apply the edit) prepared by teams_stage. It is delivered at once and cannot be unsent. Needs the stage_id and digest the user saw. Refuses a repeat: if an earlier attempt may or may not have gone through, check teams_read_chat instead of retrying. Refuses if a file changed since the preview. Only call it after the user approved the preview.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" }, digest: { type: "string" } }, required: ["stage_id", "digest"] },
    async handler(a, ctx) {
      const st = ctx.staging.transition(a.stage_id, "teams", a.digest, "sending"); // check + claim in one locked step
      const p = st.payload;

      if (p.edit) {
        const msg = buildMessage(ctx, { text: p.text }, []);
        try { await ctx.graph.patch(`/chats/${seg(p.chat_id)}/messages/${seg(p.edit.message_id)}`, await msg); }
        catch (e) { ctx.staging.set(st.id, { state: "staged" }); throw e; } // an edit can safely be retried
        ctx.staging.set(st.id, { state: "sent" });
        return { edited: true, chat_id: p.chat_id, message_id: p.edit.message_id };
      }

      // A new chat is created first (so a failed chat leaves no uploaded files) and remembered, so a retry never makes a second one.
      let chatId = p.chat_id ?? st.created_chat_id ?? null;
      if (p.new_chat && !chatId) {
        const bind = (id) => `https://graph.microsoft.com/v1.0/users('${id}')`;
        const members = [p.new_chat.me, ...p.new_chat.members.map((m) => m.id)].map((id) => ({ "@odata.type": "#microsoft.graph.aadUserConversationMember", roles: ["owner"], "user@odata.bind": bind(id) }));
        try {
          const c = await ctx.graph.post("/chats", { chatType: p.new_chat.kind, members, ...(p.new_chat.topic ? { topic: p.new_chat.topic } : {}) });
          chatId = c.id;
        } catch (e) {
          if (REFUSED.has(e.status)) { ctx.staging.set(st.id, { state: "staged" }); throw e; }
          throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether the new chat was created.", { hint: "Look for it with teams_find_chat before trying again. This stage will not be sent a second time automatically." });
        }
        ctx.staging.set(st.id, { created_chat_id: chatId });
      }

      const uploaded = [];
      let message;
      try {
        message = await buildMessage(ctx, p, uploaded);
      } catch (e) {
        // Nothing was posted yet, so this is never an "unknown outcome": undo the uploads and allow a retry.
        await removeUploads(ctx, uploaded);
        ctx.staging.set(st.id, { state: "staged" });
        if (e instanceof M365Error) { e.message = `${e.message} Nothing was sent.`; throw e; }
        throw new M365Error("GRAPH_ERROR", "A file could not be prepared. Nothing was sent.");
      }
      let r;
      try {
        r = await ctx.graph.post(targetPath(p, chatId), message);
      } catch (e) {
        if (REFUSED.has(e.status)) { await removeUploads(ctx, uploaded); ctx.staging.set(st.id, { state: "staged" }); throw e; } // a definite refusal: nothing was sent
        throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether the message was sent.", { hint: `Check ${p.channel ? "the channel with teams_read_channel" : "the chat with teams_read_chat"} before trying again. This stage will not be sent a second time automatically.` });
      }
      ctx.staging.set(st.id, { state: "sent", message_id: r.id });
      const files = p.files ?? [];
      return {
        sent: true, message_id: r.id ?? null,
        ...(p.channel ? { team_id: p.channel.team_id, channel_id: p.channel.channel_id } : { chat_id: chatId }),
        ...(p.new_chat ? { new_chat: true } : {}),
        ...(files.length ? { attachments: files.map((f) => f.name) } : {}),
      };
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
  {
    name: "teams_delete_message", kind: "write", module: "teams", confirm: true,
    description: "Delete a chat message the signed-in user sent (Claude Code asks the user to confirm). Others then see 'This message has been deleted'. Refuses anyone else's message. Get message_id from teams_read_chat.",
    inputSchema: { type: "object", properties: { chat_id: { type: "string" }, message_id: { type: "string" } }, required: ["chat_id", "message_id"] },
    async handler(a, ctx) {
      const chatId = safeId(a.chat_id, "chat_id"), id = safeId(a.message_id, "message_id");
      const text = await ownMessage(ctx, chatId, id);
      const me = await meOf(ctx);
      await ctx.graph.post(`/users/${seg(me.id)}/chats/${seg(chatId)}/messages/${seg(id)}/softDelete`, {});
      return { deleted: true, chat_id: chatId, message_id: id, text_was: text };
    },
  },
];
