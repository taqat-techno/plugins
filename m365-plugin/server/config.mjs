// config.mjs - resolves settings from Claude Code's plugin settings (M365_PLUGIN_*) first, then plain
// environment variables (M365_*), so agent bots and any other host can configure it without
// Claude Code. An unexpanded "${...}" placeholder counts as unset. Nothing needs admin rights.
import { homedir } from "node:os";
import { join } from "node:path";

const unset = (v) => v === undefined || v === null || String(v).trim() === "" || /\$\{/.test(String(v));
const pick = (env, ...names) => {
  for (const n of names) if (!unset(env[n])) return String(env[n]).trim();
  return "";
};
const bool = (v) => /^(1|true|yes|on)$/i.test(String(v ?? "").trim());

export const MODULES = ["mail", "calendar", "teams", "channels", "people"];
export const DEFAULT_MODULES = ["mail", "calendar", "teams", "people"];

// Delegated Microsoft Graph permissions each module needs. Read-only mode asks for these only.
// `channels` is separate and off by default: reading channel messages needs admin consent.
export const READ_SCOPES = {
  base: ["User.Read", "MailboxSettings.Read"],
  mail: ["Mail.Read"],
  calendar: ["Calendars.Read"],
  teams: ["Chat.Read"],
  channels: ["Team.ReadBasic.All", "Channel.ReadBasic.All", "ChannelMessage.Read.All"],
  people: ["People.Read", "User.ReadBasic.All"],
};

export function resolveConfig(env = process.env) {
  const modules = pick(env, "M365_PLUGIN_MODULES", "M365_MODULES");
  const list = modules ? modules.split(/[,\s]+/).map((s) => s.toLowerCase()).filter((m) => MODULES.includes(m)) : DEFAULT_MODULES;
  const readOnly = bool(pick(env, "M365_PLUGIN_READONLY", "M365_READONLY"));
  const home = pick(env, "M365_HOME") || join(homedir(), ".m365-plugin");
  const scopeOverride = pick(env, "M365_SCOPES");
  const scopes = scopeOverride
    ? scopeOverride.split(/[,\s]+/).filter(Boolean)
    : [...new Set([...READ_SCOPES.base, ...list.flatMap((m) => READ_SCOPES[m] ?? [])])];
  return {
    clientId: pick(env, "M365_PLUGIN_CLIENT_ID", "M365_CLIENT_ID"),
    tenant: pick(env, "M365_PLUGIN_TENANT", "M365_TENANT") || "organizations",
    authMode: (pick(env, "M365_PLUGIN_AUTH_MODE", "M365_AUTH_MODE") || "auto").toLowerCase(),
    readOnly,
    modules: list,
    home,
    scopes,
    timeoutMs: Number(pick(env, "M365_TIMEOUT_MS")) || 30_000,
    attempts: Math.max(1, Number(pick(env, "M365_ATTEMPTS")) || 3),
  };
}

/** What a host should show when no app registration is configured yet. */
export const NEEDS_CLIENT_ID =
  "No Microsoft app (client id) is configured. Set the 'Client ID' plugin setting or the M365_CLIENT_ID " +
  "environment variable. See docs/APP_REGISTRATION.md for the one-time app registration an admin does.";
