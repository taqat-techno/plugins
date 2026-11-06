// Save a mail attachment or a OneDrive/SharePoint file to this computer, so a host (a bot showing files in its chat, a
// local tool) can use it through the plugin's own sign-in. Files go ONLY into the one folder the person chose
// (M365_DOWNLOAD_DIR, the plugin setting, or `cli.mjs setup --download-dir`; never through a tool), under a cleaned file
// name, never overwriting anything. Changes nothing in Microsoft 365, so these are 'local' tools.
import { closeSync, openSync, realpathSync, statSync, writeSync } from "node:fs";
import { extname, join } from "node:path";
import { M365Error, clean, safeId, seg } from "../util.mjs";

export const MAX_SAVE = 50 * 1024 * 1024;
const RESERVED = /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$/i;

/** A safe file name: no folders, no characters Windows forbids, no reserved device names, bounded length. */
export function safeFileName(name) {
  let n = clean(String(name ?? ""), 2000).replace(/[<>:"/\\|?*\x00-\x1f]/g, "_").replace(/^[.\s]+|[.\s]+$/g, "").trim();
  if (!n || RESERVED.test(n)) n = `file_${n || "download"}`;
  if (n.length > 150) { const ext = extname(n).slice(0, 20); n = n.slice(0, 150 - ext.length) + ext; }
  return n;
}

function downloadDir(cfg) {
  if (!cfg.downloadDir) {
    throw new M365Error("DOWNLOAD_NOT_CONFIGURED", "No folder is set for saving files yet.", {
      hint: "Only the user can choose it: the plugin setting 'Folder to save files into', M365_DOWNLOAD_DIR, or in their own terminal: node server/cli.mjs setup --download-dir <folder>.",
    });
  }
  let real;
  try { real = realpathSync(cfg.downloadDir); } catch { real = null; }
  if (!real || !statSync(real).isDirectory()) throw new M365Error("NOT_CONFIGURED", "The folder for saving files does not exist.", { hint: "Check M365_DOWNLOAD_DIR." });
  return real;
}

/** Write bytes as a NEW file in the download folder ("name (2).ext" if taken). Returns the full path. */
export function saveBytes(cfg, name, bytes) {
  const dir = downloadDir(cfg);
  const base = safeFileName(name), ext = extname(base), stem = base.slice(0, base.length - ext.length);
  for (let i = 1; i < 1000; i++) {
    const path = join(dir, i === 1 ? base : `${stem} (${i})${ext}`);
    let fd;
    try { fd = openSync(path, "wx", 0o600); } catch (e) { if (e.code === "EEXIST") continue; throw e; }
    try { let off = 0; while (off < bytes.length) off += writeSync(fd, bytes, off, bytes.length - off); } finally { closeSync(fd); }
    return path;
  }
  throw new M365Error("INVALID_ARGUMENT", "Too many files with that name in the download folder.");
}

const tooBig = () => new M365Error("TOO_LARGE", `The file is larger than ${MAX_SAVE / 1048576} MB, so it was not saved.`, { hint: "Open it from its web link instead." });

export const tools = [
  {
    name: "email_save_attachment", kind: "local", module: "mail",
    description: "Save one attachment of a message (ids from email_list_attachments) as a new file in the folder the user chose for downloads (M365_DOWNLOAD_DIR). Returns the saved file's full path. Never overwrites a file; up to 50 MB. Saving a file does not mean you read it: do not describe its contents from its name.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, attachment_id: { type: "string" } }, required: ["message_id", "attachment_id"] },
    async handler(a, ctx) {
      downloadDir(ctx.cfg);
      const m = safeId(a.message_id, "message_id"), at = safeId(a.attachment_id, "attachment_id");
      const path = `/me/messages/${seg(m)}/attachments/${seg(at)}`;
      const meta = await ctx.graph.get(`${path}?$select=id,name,size,contentType`);
      if (meta["@odata.type"] && meta["@odata.type"] !== "#microsoft.graph.fileAttachment") throw new M365Error("UNSUPPORTED", "That attachment is not a file (for example an attached email), so it cannot be saved.");
      if ((meta.size ?? 0) > MAX_SAVE * 1.4) throw tooBig();
      const bytes = await ctx.graph.get(`${path}/$value`, { raw: true });
      if (bytes.length > MAX_SAVE) throw tooBig();
      const saved = saveBytes(ctx.cfg, meta.name || "attachment", bytes);
      return { saved: true, path: saved, name: clean(meta.name, 200), size_bytes: bytes.length, content_type: meta.contentType ?? null };
    },
  },
  {
    name: "onedrive_save_file", kind: "local", module: "files",
    description: "Save a OneDrive or SharePoint file (drive_id and item_id from onedrive_search or teams_meeting_files) as a new file in the folder the user chose for downloads (M365_DOWNLOAD_DIR). Returns the saved file's full path. Never overwrites a file; up to 50 MB; folders are refused.",
    inputSchema: { type: "object", properties: { drive_id: { type: "string" }, item_id: { type: "string" } }, required: ["drive_id", "item_id"] },
    async handler(a, ctx) {
      downloadDir(ctx.cfg);
      const d = safeId(a.drive_id, "drive_id"), i = safeId(a.item_id, "item_id");
      const meta = await ctx.graph.get(`/drives/${seg(d)}/items/${seg(i)}?$select=id,name,size,file,folder`);
      if (meta.folder) throw new M365Error("UNSUPPORTED", "That is a folder, not a file.");
      if ((meta.size ?? 0) > MAX_SAVE) throw tooBig();
      const bytes = await ctx.graph.get(`/drives/${seg(d)}/items/${seg(i)}/content`, { raw: true });
      if (bytes.length > MAX_SAVE) throw tooBig();
      const saved = saveBytes(ctx.cfg, meta.name || "file", bytes);
      return { saved: true, path: saved, name: clean(meta.name, 200), size_bytes: bytes.length, content_type: meta.file?.mimeType ?? null };
    },
  },
];
