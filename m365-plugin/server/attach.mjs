// attach.mjs - local files onto Outlook drafts.
//
// Only files under the folders the PERSON listed (M365_ATTACH_DIRS, the plugin setting or `cli.mjs setup --attach-dirs`)
// can be attached: injected text cannot make the agent mail out ~/.ssh or a token file. The check uses the file's real
// path (symbolic links and '..' resolved) against each folder's real path. Up to 3 MB goes in one request; larger
// files (up to MAX_BYTES) use an Outlook upload session.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { basename, extname, isAbsolute, relative, resolve, sep } from "node:path";
import { M365Error, clean, seg } from "./util.mjs";

export const MAX_BYTES = 25 * 1024 * 1024;
const SMALL = 3 * 1024 * 1024;
const CHUNK = 320 * 1024 * 10; // 3.2 MB, a multiple of 320 KiB as Outlook requires

const TYPES = {
  ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
  ".txt": "text/plain", ".csv": "text/csv", ".md": "text/markdown", ".html": "text/html", ".htm": "text/html", ".json": "application/json",
  ".zip": "application/zip", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ".doc": "application/msword", ".xls": "application/vnd.ms-excel", ".ppt": "application/vnd.ms-powerpoint", ".mp4": "video/mp4", ".mp3": "audio/mpeg",
};
export const contentTypeOf = (name) => TYPES[extname(String(name)).toLowerCase()] ?? "application/octet-stream";

const inside = (root, real) => {
  const rel = relative(root, real);
  return rel !== "" && !rel.startsWith("..") && !isAbsolute(rel) && !rel.split(sep).includes("..");
};

/** The real path and size of a file the user allowed, or a clear refusal. */
export function allowedFile(cfg, path) {
  const roots = cfg.attachDirs ?? [];
  if (!roots.length) {
    throw new M365Error("ATTACH_NOT_CONFIGURED", "No folder is allowed for attachments yet.", {
      hint: "Only the user can choose them: the plugin setting 'Folders files may be attached from', M365_ATTACH_DIRS, or in their own terminal: node server/cli.mjs setup --attach-dirs <folder>. Never move a file into such a folder on your own to get around this.",
    });
  }
  const p = String(path ?? "").trim();
  if (!p || !isAbsolute(p)) throw new M365Error("INVALID_ARGUMENT", "path must be an absolute file path");
  const refuse = () => new M365Error("PATH_NOT_ALLOWED", "That file is outside the folders the user allowed for attachments.", { hint: "Ask the user to put the file in an allowed folder, or to add a folder themselves (M365_ATTACH_DIRS)." });
  // 1) Text only, before ANY file-system call: on Windows even resolving \\host\share\x makes the machine connect to that
  //    host and offer its login (an NTLM leak). Network, device and extended-length paths, drive-relative forms and
  //    alternate data streams (a ':' after the drive) are refused, and the path must lie inside an allowed folder.
  if (/^[\\/]{2}/.test(p) || (process.platform === "win32" && (/^[a-z]:(?![\\/])/i.test(p) || p.indexOf(":", 2) !== -1))) throw refuse();
  const lexical = resolve(p);
  const fold = (s) => (process.platform === "win32" ? s.toLowerCase() : s);
  if (!roots.some((r) => inside(fold(resolve(r)), fold(lexical)))) throw refuse();
  // 2) Only now touch the disk, and check the real path (links resolved) against the real folders as well.
  let real;
  try { real = realpathSync(lexical); } catch { throw new M365Error("NOT_FOUND", "No such file."); }
  const ok = roots.some((r) => { try { return inside(fold(realpathSync(r)), fold(real)); } catch { return false; } });
  if (!ok) throw refuse();
  const st = statSync(real);
  if (!st.isFile()) throw new M365Error("INVALID_ARGUMENT", "That is not a file.");
  if (st.size === 0) throw new M365Error("INVALID_ARGUMENT", "That file is empty.");
  if (st.size > MAX_BYTES) throw new M365Error("TOO_LARGE", `That file is larger than ${MAX_BYTES / 1048576} MB.`, { hint: "Share it from OneDrive instead (onedrive_share_link) and put the link in the email." });
  return { real, size: st.size, name: clean(basename(real), 200) };
}

/** Attach bytes to a draft: one request up to 3 MB, an upload session above. Returns { attachment_id, name, size }. */
export async function attachBytes(ctx, draftId, { name, bytes, contentType, inline = false, contentId }) {
  const base = `/me/messages/${seg(draftId)}/attachments`;
  if (bytes.length <= SMALL) {
    const r = await ctx.graph.post(base, {
      "@odata.type": "#microsoft.graph.fileAttachment", name, contentType: contentType ?? contentTypeOf(name),
      contentBytes: bytes.toString("base64"), ...(inline ? { isInline: true, contentId } : {}),
    });
    return { attachment_id: r.id ?? null, name, size: bytes.length };
  }
  const s = await ctx.graph.post(`${base}/createUploadSession`, {
    AttachmentItem: { attachmentType: "file", name, size: bytes.length, contentType: contentType ?? contentTypeOf(name), ...(inline ? { isInline: true, contentId } : {}) },
  });
  if (!s.uploadUrl) throw new M365Error("GRAPH_ERROR", "Outlook did not open an upload session.");
  let last = {};
  for (let start = 0; start < bytes.length; start += CHUNK) last = await ctx.graph.uploadChunk(s.uploadUrl, bytes.subarray(start, start + CHUNK), start, bytes.length);
  // The final chunk's answer names the new attachment in its Location header only; list it by name instead.
  const j = await ctx.graph.get(`${base}?$select=id,name,size`);
  const hit = (j.value ?? []).filter((x) => x.name === name && x.size >= bytes.length - 1024).pop();
  return { attachment_id: hit?.id ?? last.id ?? null, name, size: bytes.length };
}

export const readAllowed = (f) => readFileSync(f.real);
