// attach.mjs - local files onto Outlook drafts.
//
// Which files can be attached is the PERSON's choice (attach_scope, attach_dirs: plugin settings or `cli.mjs setup`):
//   folders  (default; what a bot gets) only files under attach_dirs.
//   anywhere (the Claude Code plugin's default) any local file except keys, tokens and sign-in folders. Every attach is
//            then shown to the human with its full path first (hooks/pre_write_confirm.py asks), so injected text cannot
//            quietly mail out a file.
// Images the user pasted into the chat are saved by that hook under <home>/chat-files and are allowed in both modes.
// The checks use the file's real path (symbolic links and '..' resolved) as well as the text of the path. Up to 3 MB goes in one request; larger
// files (up to MAX_BYTES) use an Outlook upload session.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { basename, extname, isAbsolute, join, relative, resolve, sep } from "node:path";
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
/** Where the Claude Code hook saves images the user pasted into the chat (one folder per session). */
export const chatFilesDir = (cfg) => join(cfg.home, "chat-files");

// Never attachable, even in "anywhere" mode: folders that hold keys, tokens and sign-ins, and files that look like them.
const SECRET_DIRS = [".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker", ".config/gcloud", "credentials", "secrets",
  "appdata/roaming/microsoft/credentials", "appdata/roaming/microsoft/protect", "appdata/local/microsoft/credentials"];
const SECRET_FILE = /^(\.env(\..*)?|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|credentials(\.json)?|token-cache\.json|.*\.(pem|key|pfx|p12|kdbx|ppk|jks|keystore|asc))$/i;

function secret(cfg, p, fold) {
  const f = fold(p).replace(/\\/g, "/");
  const home = fold(homedir()).replace(/\\/g, "/").replace(/\/$/, "");
  if (SECRET_DIRS.some((d) => f.startsWith(`${home}/${d}/`) || f.includes(`/${d}/`))) return true;
  // the plugin's own folder (sign-in cache, settings) except the pasted images it saved
  const own = fold(cfg.home).replace(/\\/g, "/").replace(/\/$/, "");
  if (f.startsWith(`${own}/`) && !f.startsWith(`${own}/chat-files/`)) return true;
  for (const c of [cfg.refreshTokenFile, cfg.clientSecretFile].filter(Boolean)) if (fold(resolve(c)).replace(/\\/g, "/") === f) return true;
  return SECRET_FILE.test(basename(p));
}

export function allowedFile(cfg, path) {
  const anywhere = cfg.attachScope === "anywhere";
  const roots = [...(cfg.attachDirs ?? []), chatFilesDir(cfg)];
  const p = String(path ?? "").trim();
  if (!p || !isAbsolute(p)) throw new M365Error("INVALID_ARGUMENT", "path must be an absolute file path");
  const refuse = () => (!anywhere && !(cfg.attachDirs ?? []).length)
    ? new M365Error("ATTACH_NOT_CONFIGURED", "No folder is allowed for attachments yet.", {
      hint: "Only the user can choose: the plugin setting 'Files that may be attached' (anywhere) or 'Folders files may be attached from', or in their own terminal: node server/cli.mjs setup --attach-scope anywhere. Images pasted into the chat can be attached with chat_image. Never copy a file somewhere else to get around this." })
    : new M365Error("PATH_NOT_ALLOWED", anywhere ? "That file looks like a key, token or sign-in, so it is never attached." : "That file is outside the folders the user allowed for attachments.",
      { hint: anywhere ? "Do not try another way to send it." : "Ask the user to put the file in an allowed folder, or to change the setting themselves." });
  const fold = (s) => (process.platform === "win32" ? s.toLowerCase() : s);
  // 1) Text only, before ANY file-system call: on Windows even resolving \\host\share\x makes the machine connect to that
  //    host and offer its login (an NTLM leak). Network, device and extended-length paths, drive-relative forms and
  //    alternate data streams (a ':' after the drive) are refused, and the path must lie inside an allowed folder.
  if (/^[\\/]{2}/.test(p) || (process.platform === "win32" && (/^[a-z]:(?![\\/])/i.test(p) || p.indexOf(":", 2) !== -1))) {
    throw new M365Error("PATH_NOT_ALLOWED", "Network, device and stream paths cannot be attached.", { hint: "Copy nothing; ask the user for a local file." });
  }
  const lexical = resolve(p);
  const okLexical = anywhere ? !secret(cfg, lexical, fold) : roots.some((r) => inside(fold(resolve(r)), fold(lexical)));
  if (!okLexical) throw refuse();
  // 2) Only now touch the disk, and check the real path (links resolved) as well.
  let real;
  try { real = realpathSync(lexical); } catch { throw new M365Error("NOT_FOUND", "No such file."); }
  const ok = anywhere ? !secret(cfg, real, fold) : roots.some((r) => { try { return inside(fold(realpathSync(r)), fold(real)); } catch { return false; } });
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
