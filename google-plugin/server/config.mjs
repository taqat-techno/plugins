// config.mjs - resolves settings, highest priority first:
//   1. Claude Code's plugin settings (GOOGLE_PLUGIN_*)
//   2. plain environment variables (GOOGLE_*), so agent bots and any other host can configure it without Claude Code
// An unexpanded "${...}" placeholder counts as unset. Only PATHS and ids are settings: the client secret is read from
// the user's own client JSON file, and is never typed into a chat or a setting.
// The client id has no plain GOOGLE_CLIENT_ID fallback on purpose: that name is common in other projects' environments,
// and a stray value would make the plugin refuse a correct client file.
import { homedir } from "node:os";
import { delimiter, join } from "node:path";

const unset = (v) => v === undefined || v === null || String(v).trim() === "" || /\$\{/.test(String(v));
const pick = (env, ...names) => {
  for (const n of names) if (!unset(env[n])) return String(env[n]).trim();
  return "";
};
const bool = (v) => /^(1|true|yes|on)$/i.test(String(v ?? "").trim());
const list = (v) => [...new Set(String(v ?? "").split(/[,\s]+/).map((x) => x.trim()).filter(Boolean))];

/** Google's Workspace MCP servers (Streamable HTTP). */
export const MCP_URLS = {
  gmail: "https://gmailmcp.googleapis.com/mcp/v1",
  calendar: "https://calendarmcp.googleapis.com/mcp/v1",
  drive: "https://drivemcp.googleapis.com/mcp/v1",
};

const G = "https://www.googleapis.com/auth/";
export const SCOPES = {
  gmailModify: `${G}gmail.modify`,
  gmailReadonly: `${G}gmail.readonly`,
  calendarEvents: `${G}calendar.events`,
  calendarEventsReadonly: `${G}calendar.events.readonly`,
  calendarListReadonly: `${G}calendar.calendarlist.readonly`,
  drive: `${G}drive`,
  driveReadonly: `${G}drive.readonly`,
};
/** Full mailbox access, which includes permanent delete. The plugin must never request it: auth.mjs refuses to build a
 *  request that contains it, and a test asserts it. This constant exists only for that guard. */
export const FORBIDDEN_SCOPE = "https://mail.google.com/";
/** Sign-in identity only (non-sensitive): the account address comes from the ID token, whichever modules are on. */
export const IDENTITY_SCOPES = ["openid", "email"];

export const MODULES = ["gmail", "calendar", "drive"];
// What each module needs. "write" is used unless read-only mode is on.
//   gmail:    gmail.modify cannot permanently delete (Google's scope page says so); read-only uses gmail.readonly.
//   calendar: calendar.events covers events but not listing calendars (calendarList.list does not accept it), so the
//             narrow calendar.calendarlist.readonly is added instead of the broader calendar.readonly.
//   drive:    drive (all files: search needs to see existing files, which drive.file cannot); read-only uses drive.readonly.
export const MODULE_SCOPES = {
  gmail: { write: [SCOPES.gmailModify], read: [SCOPES.gmailReadonly] },
  calendar: { write: [SCOPES.calendarEvents, SCOPES.calendarListReadonly], read: [SCOPES.calendarEventsReadonly, SCOPES.calendarListReadonly] },
  drive: { write: [SCOPES.drive], read: [SCOPES.driveReadonly] },
};

export function moduleScopes(mod, readOnly) {
  return MODULE_SCOPES[mod][readOnly ? "read" : "write"];
}

export function resolveConfig(env = process.env) {
  const readOnly = bool(pick(env, "GOOGLE_PLUGIN_READONLY", "GOOGLE_READONLY"));
  const listed = pick(env, "GOOGLE_PLUGIN_MODULES", "GOOGLE_MODULES");
  const modules = listed ? [...new Set(listed.split(/[,\s]+/).map((s) => s.toLowerCase()).filter((m) => MODULES.includes(m)))] : [...MODULES];
  return {
    // Path to the client JSON downloaded from Google Cloud (OAuth client of type "Desktop app").
    clientSecretFile: pick(env, "GOOGLE_PLUGIN_CLIENT_SECRET_FILE", "GOOGLE_CLIENT_SECRET_FILE"),
    // Optional: the JSON already holds the client id. When set, it must match the file (a guard against a wrong file).
    clientId: pick(env, "GOOGLE_PLUGIN_CLIENT_ID"),
    readOnly,
    modules,
    // Every enabled module's scopes are requested at the first sign-in, so the human signs in once.
    scopes: [...new Set([...IDENTITY_SCOPES, ...modules.flatMap((m) => moduleScopes(m, readOnly))])],
    home: pick(env, "GOOGLE_PLUGIN_HOME") || join(homedir(), ".google-plugin"),
    timeoutMs: Number(pick(env, "GOOGLE_TIMEOUT_MS")) || 30_000,
    // Bridge to Google's Workspace MCP servers.
    mcpUrls: { ...MCP_URLS },
    // Optional allow / deny lists of tool names (deny wins). Empty allow = every classified tool.
    toolsAllow: list(pick(env, "GOOGLE_PLUGIN_TOOLS_ALLOW", "GOOGLE_TOOLS_ALLOW")),
    toolsDeny: list(pick(env, "GOOGLE_PLUGIN_TOOLS_DENY", "GOOGLE_TOOLS_DENY")),
    // forward (default): pass Google's confirmation form to the MCP client if it supports forms, else CONFIRMATION_NEEDED.
    // error: never forward; always CONFIRMATION_NEEDED (the human uses `cli.mjs grant`).
    confirmMode: /^error$/i.test(pick(env, "GOOGLE_PLUGIN_CONFIRM_MODE", "GOOGLE_CONFIRM_MODE")) ? "error" : "forward",
    // How long a forwarded confirmation form may wait for the human.
    confirmTimeoutMs: Number(pick(env, "GOOGLE_CONFIRM_TIMEOUT_MS")) || 600_000,
    // Result size caps (characters): any one string, and the whole result.
    maxStringChars: Number(pick(env, "GOOGLE_MAX_STRING_CHARS")) || 20_000,
    maxResultChars: Number(pick(env, "GOOGLE_MAX_RESULT_CHARS")) || 100_000,
    // Identities for gmail_message_identity (server/identity.mjs): a JSON file path, or the JSON itself.
    identitiesFile: pick(env, "GOOGLE_PLUGIN_IDENTITIES_FILE", "GOOGLE_IDENTITIES_FILE"),
    identitiesJson: pick(env, "GOOGLE_IDENTITIES"),
    // The ONE folder gmail_get_attachment / drive_save_file may write into. Set by the person only; no default.
    downloadDir: pick(env, "GOOGLE_PLUGIN_DOWNLOAD_DIR", "GOOGLE_DOWNLOAD_DIR"),
    // Largest file those tools save (MB).
    maxSaveMb: Number(pick(env, "GOOGLE_MAX_SAVE_MB")) || 25,
    // Off by default: refuse calendar changes that involve other people (server/guards.mjs).
    refuseGuestEvents: bool(pick(env, "GOOGLE_REFUSE_GUEST_EVENTS")),
    // Off by default (0): at most N trash / spam / delete / move calls per rolling hour in this process.
    writeLimitPerHour: Math.max(0, Math.floor(Number(pick(env, "GOOGLE_WRITE_LIMIT_PER_HOUR")) || 0)),
    // Off by default: Google REST API tools for what Google's MCP servers lack (server/tools/rest.mjs).
    restFallback: bool(pick(env, "GOOGLE_PLUGIN_REST_FALLBACK", "GOOGLE_REST_FALLBACK")),
    // Folders local files may be attached from (separated like PATH). Empty = GOOGLE_DOWNLOAD_DIR only.
    attachDirs: pick(env, "GOOGLE_PLUGIN_ATTACH_DIRS", "GOOGLE_ATTACH_DIRS").split(delimiter).map((x) => x.trim()).filter(Boolean),
    // After gmail_rest_send_draft, how long to look for a bounce (seconds, 0 = off, at most 30).
    bounceCheckSeconds: Math.min(30, Math.max(0, Number(pick(env, "GOOGLE_BOUNCE_CHECK_SECONDS") || 10))),
  };
}

/** What a host should show when no Google client is configured yet. */
export const NEEDS_CLIENT =
  "No Google OAuth client is configured yet. Create a Desktop app client in Google Cloud and set the path to its downloaded JSON " +
  "file in the plugin setting 'Google client JSON file' or the GOOGLE_CLIENT_SECRET_FILE environment variable. " +
  "See docs/GOOGLE_CLOUD_SETUP.md. Never paste the file's contents into a chat.";
