// save.mjs - writes a downloaded file into the ONE folder the person chose (GOOGLE_DOWNLOAD_DIR, the plugin setting;
// never a tool argument), under a cleaned name, never overwriting anything. Bytes never go into a tool result.
import { closeSync, openSync, realpathSync, statSync, writeSync } from "node:fs";
import { extname, join } from "node:path";
import { GoogleError } from "./util.mjs";

const RESERVED = /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$/i;

/** A safe file name: no folders, no characters Windows forbids, no reserved device names, bounded length. */
export function safeFileName(name) {
  // eslint-disable-next-line no-control-regex
  let n = String(name ?? "").replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, "_").replace(/^[.\s]+|[.\s]+$/g, "").trim();
  if (!n || RESERVED.test(n)) n = `file_${n || "download"}`;
  if (n.length > 150) { const ext = extname(n).slice(0, 20); n = n.slice(0, 150 - ext.length) + ext; }
  return n;
}

/**
 * The standard extension for a MIME type, then other extensions that already count as right for it. A type that is
 * not listed (or is generic, like application/octet-stream) never changes a name.
 */
export const MIME_EXT = {
  "image/jpeg": [".jpg", ".jpeg", ".jpe", ".jfif"], "image/png": [".png"], "image/gif": [".gif"], "image/webp": [".webp"],
  "image/heic": [".heic"], "image/heif": [".heif"], "image/bmp": [".bmp"], "image/tiff": [".tif", ".tiff"], "image/svg+xml": [".svg"],
  "application/pdf": [".pdf"], "text/plain": [".txt", ".text", ".log"], "text/csv": [".csv"], "text/html": [".html", ".htm"],
  "text/markdown": [".md", ".markdown"], "text/tab-separated-values": [".tsv"], "text/calendar": [".ics"],
  "application/json": [".json"], "application/vnd.google-apps.script+json": [".json"], "application/zip": [".zip"],
  "application/rtf": [".rtf"], "application/epub+zip": [".epub"],
  "audio/mpeg": [".mp3"], "audio/mp4": [".m4a"], "audio/wav": [".wav"], "audio/ogg": [".ogg", ".oga", ".opus"],
  "video/mp4": [".mp4"], "video/quicktime": [".mov"], "video/webm": [".webm"],
  "application/msword": [".doc"], "application/vnd.ms-excel": [".xls"], "application/vnd.ms-powerpoint": [".ppt"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.oasis.opendocument.text": [".odt"], "application/vnd.oasis.opendocument.spreadsheet": [".ods"],
  "application/vnd.oasis.opendocument.presentation": [".odp"],
};

/**
 * The cleaned name with the standard extension for mimeType added when it has none or one that does not fit that type
 * ("photo" -> "photo.jpg", "a.png" sent as JPEG -> "a.png.jpg"); a fitting one (".JPEG" for image/jpeg) is kept as it is.
 */
export function withExtension(name, mimeType) {
  const base = safeFileName(name);
  const exts = MIME_EXT[String(mimeType ?? "").split(";")[0].trim().toLowerCase()];
  if (!exts || exts.includes(extname(base).toLowerCase())) return base;
  return safeFileName(base + exts[0]);
}

export const maxSaveBytes = (cfg) => (Number(cfg?.maxSaveMb) > 0 ? Number(cfg.maxSaveMb) : 25) * 1024 * 1024;

function downloadDir(cfg) {
  if (!cfg.downloadDir) {
    throw new GoogleError("DOWNLOAD_NOT_CONFIGURED", "No folder is set for saving files.", {
      hint: "Only the person can choose it: the plugin setting 'Folder to save files into' or GOOGLE_DOWNLOAD_DIR. Do not retry until they have.",
    });
  }
  let real = null;
  try { real = realpathSync(cfg.downloadDir); } catch { /* missing */ }
  if (!real || !statSync(real).isDirectory()) throw new GoogleError("DOWNLOAD_NOT_CONFIGURED", "The folder for saving files does not exist.", { hint: "Check GOOGLE_DOWNLOAD_DIR." });
  return real;
}

/**
 * Writes bytes as a NEW file ("name (2).ext" if taken). With mimeType, a missing or wrong extension is added first
 * (withExtension), so the numbering goes before it. Returns the full path.
 */
export function saveBytes(cfg, name, bytes, mimeType) {
  if (bytes.length > maxSaveBytes(cfg)) {
    throw new GoogleError("TOO_LARGE", `The file is ${Math.ceil(bytes.length / 1048576)} MB, over the ${Math.round(maxSaveBytes(cfg) / 1048576)} MB limit; nothing was saved.`, { hint: "The person can raise GOOGLE_MAX_SAVE_MB." });
  }
  const dir = downloadDir(cfg);
  const base = withExtension(name, mimeType), ext = extname(base), stem = base.slice(0, base.length - ext.length);
  for (let i = 1; i < 1000; i++) {
    const path = join(dir, i === 1 ? base : `${stem} (${i})${ext}`);
    let fd;
    try { fd = openSync(path, "wx", 0o600); } catch (e) { if (e.code === "EEXIST") continue; throw e; }
    try { let off = 0; while (off < bytes.length) off += writeSync(fd, bytes, off, bytes.length - off); } finally { closeSync(fd); }
    return path;
  }
  throw new GoogleError("INVALID_ARGUMENT", "Too many files with that name in the download folder.");
}
