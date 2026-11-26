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

/** Writes bytes as a NEW file ("name (2).ext" if taken). Returns the full path. */
export function saveBytes(cfg, name, bytes) {
  if (bytes.length > maxSaveBytes(cfg)) {
    throw new GoogleError("TOO_LARGE", `The file is ${Math.ceil(bytes.length / 1048576)} MB, over the ${Math.round(maxSaveBytes(cfg) / 1048576)} MB limit; nothing was saved.`, { hint: "The person can raise GOOGLE_MAX_SAVE_MB." });
  }
  const dir = downloadDir(cfg);
  const base = safeFileName(name), ext = extname(base), stem = base.slice(0, base.length - ext.length);
  for (let i = 1; i < 1000; i++) {
    const path = join(dir, i === 1 ? base : `${stem} (${i})${ext}`);
    let fd;
    try { fd = openSync(path, "wx", 0o600); } catch (e) { if (e.code === "EEXIST") continue; throw e; }
    try { let off = 0; while (off < bytes.length) off += writeSync(fd, bytes, off, bytes.length - off); } finally { closeSync(fd); }
    return path;
  }
  throw new GoogleError("INVALID_ARGUMENT", "Too many files with that name in the download folder.");
}
