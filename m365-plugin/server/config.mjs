// config.mjs - resolves settings, highest priority first:
//   1. Claude Code's plugin settings (M365_PLUGIN_*)
//   2. plain environment variables (M365_*), so agent bots and any other host can configure it without Claude Code
//   3. <M365_HOME>/settings.json, written by /m365:init (m365_setup_save): paths and ids only, never a secret
// An unexpanded "${...}" placeholder counts as unset. Nothing needs admin rights.
import { homedir } from "node:os";
import { delimiter, join } from "node:path";
import { readFileSync } from "node:fs";

const unset = (v) => v === undefined || v === null || String(v).trim() === "" || /\$\{/.test(String(v));
const pick = (env, ...names) => {
  for (const n of names) if (!unset(env[n])) return String(env[n]).trim();
  return "";
};
const bool = (v) => /^(1|true|yes|on)$/i.test(String(v ?? "").trim());

export const MODULES = ["mail", "calendar", "teams", "channels", "meetings", "people", "files"];
export const DEFAULT_MODULES = ["mail", "calendar", "teams", "people", "files"];

// Delegated Microsoft Graph permissions each module needs. Read-only mode asks for these only.
// `channels` and `meetings` are separate and off by default: channel messages and meeting transcripts need admin consent.
export const READ_SCOPES = {
  base: ["User.Read", "MailboxSettings.Read"],
  mail: ["Mail.Read"],
  calendar: ["Calendars.Read"],
  teams: ["Chat.Read"],
  channels: ["Team.ReadBasic.All", "Channel.ReadBasic.All", "ChannelMessage.Read.All"],
  meetings: ["Calendars.Read", "Chat.Read", "OnlineMeetingTranscript.Read.All", "Files.Read.All"],
  people: ["People.Read", "User.ReadBasic.All"],
  files: ["Files.Read.All"],
};

// Added only when read-only mode is off. All are user-consentable in a default tenant.
export const WRITE_SCOPES = {
  mail: ["Mail.ReadWrite", "Mail.Send"],
  calendar: ["Calendars.ReadWrite"],
  teams: ["Chat.ReadWrite"],
  files: ["Files.ReadWrite"],
};

/** Permissions that always need a tenant admin's consent. */
export const ADMIN_CONSENT_SCOPES = ["Team.ReadBasic.All", "Channel.ReadBasic.All", "ChannelMessage.Read.All", "OnlineMeetingTranscript.Read.All"];

/** What /m365:init may save: ids and file PATHS only. Read-only mode and modules are deliberately not here. */
export const SETTINGS_KEYS = ["client_id", "tenant", "auth_mode", "scope_mode", "refresh_token_file", "client_secret_file", "redirect_uri", "attach_dirs", "attach_scope", "signature_file", "download_dir"];

/** A sign-in redirect the plugin can listen on itself: http on localhost/127.0.0.1, a fixed port, an optional path.
 *  Returns { uri, host, port, path } (uri exactly as given, minus a trailing space) or throws INVALID_ARGUMENT. */
export function parseRedirectUri(v) {
  const uri = String(v ?? "").trim();
  let u;
  try { u = new URL(uri); } catch { u = null; }
  const ok = u && u.protocol === "http:" && ["localhost", "127.0.0.1"].includes(u.hostname) && u.port && !u.search && !u.hash && !u.username && !u.password
    && Number(u.port) >= 1024 && Number(u.port) <= 65535;
  if (!ok) {
    const err = new Error(`redirect_uri must be an http://localhost:<port>[/path] address the plugin can listen on (got "${uri.slice(0, 120)}")`);
    err.code = "INVALID_ARGUMENT";
    throw err;
  }
  return { uri, host: u.hostname, port: Number(u.port), path: u.pathname || "/" };
}
export const settingsPath = (home) => join(home, "settings.json");

function readSettings(home) {
  try {
    const j = JSON.parse(readFileSync(settingsPath(home), "utf8"));
    const out = {};
    for (const k of SETTINGS_KEYS) if (typeof j[k] === "string" && j[k].trim()) out[k] = j[k].trim();
    return out;
  } catch { return {}; }
}

export function resolveConfig(env = process.env) {
  const home = pick(env, "M365_HOME") || join(homedir(), ".m365-plugin");
  const file = readSettings(home);
  const get = (key, ...names) => pick(env, ...names) || file[key] || "";
  const modules = pick(env, "M365_PLUGIN_MODULES", "M365_MODULES");
  const list = modules ? modules.split(/[,\s]+/).map((s) => s.toLowerCase()).filter((m) => MODULES.includes(m)) : DEFAULT_MODULES;
  const readOnly = bool(pick(env, "M365_PLUGIN_READONLY", "M365_READONLY"));
  const scopeOverride = pick(env, "M365_SCOPES");
  // Shared sign-in: use an existing refresh token (and the app's secret) that another tool already holds, e.g. a bot's.
  // Such a token was issued for the app's approved permissions, so this always means "app" mode.
  const refreshTokenFile = get("refresh_token_file", "M365_PLUGIN_REFRESH_TOKEN_FILE", "M365_REFRESH_TOKEN_FILE");
  const clientSecretFile = get("client_secret_file", "M365_PLUGIN_CLIENT_SECRET_FILE", "M365_CLIENT_SECRET_FILE");
  // "app": use whatever permissions are already approved for the app (Graph's .default), so an app that an admin
  // approved earlier (for example one a bot already uses) needs no new approval. "requested" (default): ask only for
  // what the enabled modules need, which may need an admin to approve new permissions.
  const scopeMode = get("scope_mode", "M365_PLUGIN_SCOPE_MODE", "M365_SCOPE_MODE").toLowerCase() === "app" || refreshTokenFile ? "app" : "requested";
  const scopes = scopeOverride
    ? scopeOverride.split(/[,\s]+/).filter(Boolean)
    : scopeMode === "app"
      ? [".default"]
      : [...new Set([
        ...READ_SCOPES.base,
        ...list.flatMap((m) => READ_SCOPES[m] ?? []),
        ...(readOnly ? [] : list.flatMap((m) => WRITE_SCOPES[m] ?? [])),
      ])];
  return {
    clientId: get("client_id", "M365_PLUGIN_CLIENT_ID", "M365_CLIENT_ID"),
    tenant: get("tenant", "M365_PLUGIN_TENANT", "M365_TENANT") || "organizations",
    authMode: (get("auth_mode", "M365_PLUGIN_AUTH_MODE", "M365_AUTH_MODE") || "auto").toLowerCase(),
    readOnly,
    scopeMode,
    refreshTokenFile,
    clientSecretFile,
    // The app's registered sign-in redirect, for an app (often a bot's) that allows only one exact address such as
    // http://localhost:8400/callback. Empty: a free port on http://localhost, which a "Mobile and desktop" http://localhost
    // registration accepts.
    redirectUri: get("redirect_uri", "M365_PLUGIN_REDIRECT_URI", "M365_REDIRECT_URI"),
    // Folders files may be attached from (separated by ';' on Windows, ':' elsewhere). Set only by the person.
    attachDirs: get("attach_dirs", "M365_PLUGIN_ATTACH_DIRS", "M365_ATTACH_DIRS").split(delimiter).map((s) => s.trim()).filter(Boolean),
    // "anywhere": any file on this computer except secrets (keys, tokens, credential folders) may be attached; each attach
    // is then shown to the human with its full path (the Claude Code hook asks). "folders" (default, and what a bot gets):
    // only attach_dirs. Images the user pasted into the chat are saved under <home>/chat-files and allowed in both modes.
    attachScope: get("attach_scope", "M365_PLUGIN_ATTACH_SCOPE", "M365_ATTACH_SCOPE").toLowerCase() === "anywhere" ? "anywhere" : "folders",
    // The user's HTML email signature (a file only the person chooses). Set: drafts are HTML built by the plugin.
    signatureFile: get("signature_file", "M365_PLUGIN_SIGNATURE_FILE", "M365_SIGNATURE_FILE"),
    // The one folder files may be saved into (email_save_attachment, onedrive_save_file). Set only by the person.
    downloadDir: get("download_dir", "M365_PLUGIN_DOWNLOAD_DIR", "M365_DOWNLOAD_DIR"),
    // A rotated refresh token is written back to the shared file (atomically), exactly as the tool that owns it does,
    // so the other tool never holds a stale one. Turn off only to leave the file strictly untouched.
    refreshTokenWriteback: !/^(0|false|no|off)$/i.test(pick(env, "M365_REFRESH_TOKEN_WRITEBACK")),
    modules: list,
    home,
    scopes,
    savedSettings: Object.keys(file),
    timeoutMs: Number(pick(env, "M365_TIMEOUT_MS")) || 30_000,
    attempts: Math.max(1, Number(pick(env, "M365_ATTEMPTS")) || 3),
  };
}

/** What a host should show when no app registration is configured yet. */
export const NEEDS_CLIENT_ID =
  "No Microsoft app (client id) is configured yet. Run /m365:init (or call m365_setup_save with the client id your admin gave you, " +
  "or m365_access_request to get a message to send to your admin). See docs/APP_REGISTRATION.md for the one-time app registration.";
