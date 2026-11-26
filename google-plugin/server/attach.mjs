// attach.mjs - local files onto REST drafts. Which files can be attached is the PERSON's choice: only files inside the
// folders in GOOGLE_ATTACH_DIRS (separated like PATH: ';' on Windows, ':' elsewhere; default: GOOGLE_DOWNLOAD_DIR).
// Files that look like keys, tokens or sign-ins, and the plugin's own folder and client file, are refused even there.
// Rules carried over from the m365 plugin's attach.mjs:
//   1) the path is checked as TEXT before any file-system call (on Windows, even resolving \\host\share makes the machine
//      connect and offer its login): absolute only; no network, device, extended-length or drive-relative paths and no
//      alternate data streams; it must lie inside an allowed folder;
//   2) only then the real path (links, junctions, '..' and 8.3 short names resolved) is checked again.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { basename, extname, isAbsolute, relative, resolve, sep } from "node:path";
import { GoogleError } from "./util.mjs";

export const MAX_ATTACH_BYTES = 25 * 1024 * 1024;

const TYPES = {
  ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
  ".txt": "text/plain", ".csv": "text/csv", ".md": "text/markdown", ".html": "text/html", ".htm": "text/html", ".json": "application/json",
  ".zip": "application/zip", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ".doc": "application/msword", ".xls": "application/vnd.ms-excel", ".ppt": "application/vnd.ms-powerpoint", ".mp4": "video/mp4", ".mp3": "audio/mpeg",
};
export const contentTypeOf = (name) => TYPES[extname(String(name)).toLowerCase()] ?? "application/octet-stream";

const fold = (s) => (process.platform === "win32" || process.platform === "darwin" ? s.toLowerCase() : s);
const norm = (s) => fold(s).replace(/\\/g, "/").replace(/\/$/, "");
const realOf = (p) => (realpathSync.native ?? realpathSync)(p);
const realOrSelf = (p) => { try { return realOf(p); } catch { return resolve(p); } };
const inside = (root, real) => { const rel = relative(root, real); return rel !== "" && !rel.startsWith("..") && !isAbsolute(rel) && !rel.split(sep).includes(".."); };
const spellings = (p) => [...new Set([norm(resolve(p)), norm(realOrSelf(p))])];

const ANY_DIRS = [".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker", "credentials", "secrets", ".password-store",
  ".mozilla", ".local/share/keyrings", "library/keychains", "appdata/roaming/microsoft/credentials", "appdata/roaming/microsoft/protect",
  "appdata/local/microsoft/credentials", "appdata/local/google/chrome/user data", "appdata/local/microsoft/edge/user data", "appdata/roaming/mozilla/firefox/profiles"];
const HOME_DIRS = [".claude", ".config"];
const SECRET_FILE = /^(\.env(\..*)?|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|\.?credentials(\.json)?|client_secret[^/\\]*\.json|\.git-credentials|[._]netrc|\.npmrc|\.pypirc|\.htpasswd|token[-_]cache(\.json|\.bin)?|.*\.(pem|key|pfx|p12|kdbx|ppk|jks|keystore|asc))$/i;

function secret(cfg, p) {
  const f = norm(p);
  const lf = f.toLowerCase();
  if (ANY_DIRS.some((d) => lf.includes(`/${d}/`))) return true;
  for (const home of spellings(homedir())) if (HOME_DIRS.some((d) => f.startsWith(`${home}/${d}/`))) return true;
  for (const own of spellings(cfg.home)) if (f.startsWith(`${own}/`)) return true;
  if (cfg.clientSecretFile && spellings(cfg.clientSecretFile).includes(f)) return true;
  return SECRET_FILE.test(basename(p));
}

/** The folders files may be attached from. */
export const attachDirs = (cfg) => (cfg.attachDirs?.length ? cfg.attachDirs : cfg.downloadDir ? [cfg.downloadDir] : []);

/** The real path, size and name of a file the person allowed, or a clear refusal. */
export function allowedFile(cfg, path) {
  const dirs = attachDirs(cfg);
  const p = String(path ?? "");
  // eslint-disable-next-line no-control-regex
  if (!p || p !== p.trim() || /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2066-\u2069]/.test(p)) {
    throw new GoogleError("INVALID_ARGUMENT", "path has leading or trailing spaces or hidden characters; give the plain absolute path.");
  }
  if (!isAbsolute(p)) throw new GoogleError("INVALID_ARGUMENT", "path must be an absolute file path.");
  if (!dirs.length) throw new GoogleError("ATTACH_NOT_CONFIGURED", "No folder is allowed for attachments.", { hint: "Only the person can choose: GOOGLE_ATTACH_DIRS (or GOOGLE_DOWNLOAD_DIR). Never copy a file elsewhere to get around this." });
  const outside = () => new GoogleError("PATH_NOT_ALLOWED", "That file is outside the folders allowed for attachments, or looks like a key, token or sign-in.", { hint: "Ask the person to put the file in an allowed folder; do not try another way to attach it." });
  // 1) Text only, before any file-system call.
  if (/^[\\/]{2}/.test(p) || (process.platform === "win32" && (/^[a-z]:(?![\\/])/i.test(p) || p.indexOf(":", 2) !== -1))) {
    throw new GoogleError("PATH_NOT_ALLOWED", "Network, device and stream paths cannot be attached.");
  }
  const lexical = resolve(p);
  if (!dirs.some((r) => inside(fold(resolve(r)), fold(lexical))) || secret(cfg, lexical)) throw outside();
  // 2) The real path.
  let real;
  try { real = realOf(lexical); } catch { throw new GoogleError("NOT_FOUND", "No such file."); }
  if (/^[\\/]{2}/.test(real)) throw new GoogleError("PATH_NOT_ALLOWED", "That path leads to a network or device location.");
  if (!dirs.some((r) => { try { return inside(fold(realOf(r)), fold(real)); } catch { return false; } }) || secret(cfg, real)) throw outside();
  const st = statSync(real);
  if (!st.isFile()) throw new GoogleError("INVALID_ARGUMENT", "That is not a file.");
  if (st.size === 0) throw new GoogleError("INVALID_ARGUMENT", "That file is empty.");
  if (st.size > MAX_ATTACH_BYTES) throw new GoogleError("TOO_LARGE", "That file is larger than 25 MB.", { hint: "Share it from Drive and put the link in the email." });
  return { real, size: st.size, name: basename(real) };
}

const CID = /^[A-Za-z0-9._@-]{1,100}$/;

/**
 * Reads the attachments a tool was given: [{ path, filename?, inline?, contentId? }] -> [{ filename, mimeType, bytes,
 * inline, contentId }]. inline needs a contentId (letters, digits, . _ @ -) for <img src="cid:ID"> in htmlBody.
 */
export function readAttachments(cfg, list) {
  if (list === undefined) return undefined;
  if (!Array.isArray(list)) throw new GoogleError("INVALID_ARGUMENT", "attachments must be an array.");
  const out = list.map((a, i) => {
    if (!a || typeof a !== "object") throw new GoogleError("INVALID_ARGUMENT", `attachments[${i}] must be an object with a path.`);
    const f = allowedFile(cfg, a.path);
    const filename = a.filename !== undefined ? String(a.filename).replace(/[\r\n"\\/]/g, "_").slice(0, 200) || f.name : f.name;
    const inline = a.inline === true;
    if (inline && !CID.test(String(a.contentId ?? ""))) throw new GoogleError("INVALID_ARGUMENT", `attachments[${i}]: an inline file needs contentId (letters, digits, . _ @ -), used as <img src="cid:ID">.`);
    return { filename, mimeType: contentTypeOf(filename), bytes: readFileSync(f.real), inline, ...(inline ? { contentId: String(a.contentId) } : {}) };
  });
  const total = out.reduce((n, a) => n + a.bytes.length, 0);
  if (total > MAX_ATTACH_BYTES) throw new GoogleError("TOO_LARGE", "The attachments are over 25 MB in all.", { hint: "Share large files from Drive and put the links in the email." });
  return out;
}
