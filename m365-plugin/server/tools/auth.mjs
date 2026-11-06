// sign-in and setup tools. Sign-in is asynchronous: m365_sign_in starts it and returns at once, so the agent
// can tell the user what to do; m365_auth_status shows when it has finished.
// m365_setup_save and m365_access_request are what /m365:init uses to set a user up, whatever their situation:
// they have a client id from their admin, they need to ask for one, or they reuse a sign-in another tool holds.
import { mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";
import { randomUUID } from "node:crypto";
import { ADMIN_CONSENT_SCOPES, READ_SCOPES, SETTINGS_KEYS, WRITE_SCOPES, settingsPath } from "../config.mjs";
import { M365Error } from "../util.mjs";

const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TENANT = /^([0-9a-f-]{36}|[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+|organizations|common|consumers)$/i;

const WHY = {
  "User.Read": "read your own name and email", "MailboxSettings.Read": "read your time zone and language",
  "Mail.Read": "read and search your mail", "Mail.ReadWrite": "create drafts and manage your mail", "Mail.Send": "send mail you approved",
  "Calendars.Read": "read your calendar", "Calendars.ReadWrite": "create events you approved",
  "Chat.Read": "read your Teams chats", "Chat.ReadWrite": "send Teams messages you approved",
  "People.Read": "find people you work with", "User.ReadBasic.All": "look colleagues up in the directory",
  "Files.Read.All": "find and read your OneDrive files", "Files.ReadWrite": "create view links for your files",
  "Team.ReadBasic.All": "list your teams", "Channel.ReadBasic.All": "list team channels", "ChannelMessage.Read.All": "read team channel messages",
};

/** Single-line, printable, no spaces: what a token or a secret looks like. Keeps a wrong file (a key, a document) out. */
function checkSecretFile(path, field) {
  if (!isAbsolute(path)) throw new M365Error("INVALID_ARGUMENT", `${field} must be an absolute path`);
  let st;
  try { st = statSync(path); } catch { throw new M365Error("INVALID_ARGUMENT", `${field}: no such file`); }
  if (!st.isFile() || st.size > 4096 || st.size < 8) throw new M365Error("INVALID_ARGUMENT", `${field} does not look like a token or secret file (it must be a small single-line file)`);
  const text = readFileSync(path, "utf8").trim();
  if (!/^[\x21-\x7E]{8,3000}$/.test(text)) throw new M365Error("INVALID_ARGUMENT", `${field} does not look like a token or secret file (one line, no spaces). Nothing was saved.`);
}

function readSaved(home) {
  try { return JSON.parse(readFileSync(settingsPath(home), "utf8")); } catch { return {}; }
}

export const tools = [
  {
    name: "m365_sign_in", kind: "local", module: "auth",
    description: "Start signing in to Microsoft 365 with the user's work account. mode 'interactive' opens a browser; 'device-code' returns a short code to type at a Microsoft page (for machines without a browser); 'auto' (default) tries the browser first. Returns what the user must do, at once; then call m365_auth_status until signed_in is true. No password or token passes through the agent.",
    inputSchema: { type: "object", properties: { mode: { type: "string", description: "auto (default), interactive or device-code." } } },
    async handler(a, ctx) { return ctx.auth.startSignIn({ mode: a.mode }); },
  },
  {
    name: "m365_auth_status", kind: "local", module: "auth",
    description: "Show whether Microsoft 365 is configured and signed in (account name, tenant, enabled modules, read-only flag, where the sign-in comes from) and the state of a sign-in in progress. Call it first when a tool reports NOT_SIGNED_IN, and at the start of /m365:init.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return { ...ctx.auth.status(), saved_setup: ctx.cfg.savedSettings }; },
  },
  {
    name: "m365_sign_out", kind: "local", module: "auth",
    description: "Forget the saved Microsoft sign-in on this computer. The local profile is kept. A sign-in shared with another tool (a token file) is never deleted.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return ctx.auth.signOut(); },
  },
  {
    name: "m365_setup_save", kind: "local", module: "auth", confirm: true,
    description: "Save the user's Microsoft 365 setup (used by /m365:init) in their local settings file, then apply it at once. Pass only what the user told you: client_id (from their admin), tenant, scope_mode ('app' = use the permissions already approved for the app), auth_mode, and, only if the user chose to reuse another tool's sign-in, refresh_token_file and client_secret_file as absolute PATHS (never the token or secret itself). Files are checked to look like a token or secret and are never shown. An empty string clears a field. Claude Code asks the user to confirm before this runs.",
    inputSchema: { type: "object", properties: {
      client_id: { type: "string", description: "Application (client) ID, a GUID." },
      tenant: { type: "string", description: "Tenant id or domain; default organizations." },
      scope_mode: { type: "string", description: "requested (default) or app." },
      auth_mode: { type: "string", description: "auto, interactive or device-code." },
      refresh_token_file: { type: "string", description: "Absolute path of a file holding another tool's refresh token." },
      client_secret_file: { type: "string", description: "Absolute path of a file holding the app's client secret." } } },
    async handler(a, ctx) {
      const next = { ...readSaved(ctx.cfg.home) };
      const changed = [];
      for (const k of SETTINGS_KEYS) {
        if (a[k] === undefined) continue;
        const v = String(a[k] ?? "").trim();
        if (v === "") { delete next[k]; changed.push(k); continue; }
        if (k === "client_id" && !GUID.test(v)) throw new M365Error("INVALID_ARGUMENT", "client_id must be the Application (client) ID, a GUID like 00000000-0000-0000-0000-000000000000");
        if (k === "tenant" && !TENANT.test(v)) throw new M365Error("INVALID_ARGUMENT", "tenant must be a tenant id, a domain such as contoso.com, or organizations");
        if (k === "scope_mode" && !["requested", "app"].includes(v.toLowerCase())) throw new M365Error("INVALID_ARGUMENT", "scope_mode must be requested or app");
        if (k === "auth_mode" && !["auto", "interactive", "device-code"].includes(v.toLowerCase())) throw new M365Error("INVALID_ARGUMENT", "auth_mode must be auto, interactive or device-code");
        if (k.endsWith("_file")) checkSecretFile(v, k);
        next[k] = k === "scope_mode" || k === "auth_mode" ? v.toLowerCase() : v;
        changed.push(k);
      }
      if (!changed.length) throw new M365Error("INVALID_ARGUMENT", `give at least one of: ${SETTINGS_KEYS.join(", ")}`);
      const out = {};
      for (const k of SETTINGS_KEYS) if (next[k]) out[k] = next[k];
      const path = settingsPath(ctx.cfg.home);
      mkdirSync(ctx.cfg.home, { recursive: true });
      const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
      writeFileSync(tmp, JSON.stringify(out, null, 2) + "\n", { mode: 0o600 });
      renameSync(tmp, path);
      ctx.reload();
      return { saved: changed, settings_file: join(ctx.cfg.home, "settings.json"), now: ctx.auth.status(),
        note: "Settings from the plugin's own settings page or environment variables still take priority over this file." };
    },
  },
  {
    name: "m365_access_request", kind: "local", module: "auth",
    description: "Write the message a user sends to their company admin to get Microsoft 365 access set up (an app registration with the right permissions, admin consent, and the client ID back). Built from the user's enabled modules and read-only setting, with each permission explained. Use it when the user has no client ID, or sign-in says CONSENT_NEEDED. Returns the message text to show the user; nothing is sent.",
    inputSchema: { type: "object", properties: { note: { type: "string", description: "Optional extra line to add, e.g. why it is needed." } } },
    async handler(a, ctx) {
      const cfg = ctx.cfg;
      const read = [...new Set([...READ_SCOPES.base, ...cfg.modules.flatMap((m) => READ_SCOPES[m] ?? [])])];
      const write = cfg.readOnly ? [] : [...new Set(cfg.modules.flatMap((m) => WRITE_SCOPES[m] ?? []))];
      const admin = [...read, ...write].filter((s) => ADMIN_CONSENT_SCOPES.includes(s));
      const line = (s) => `  - ${s}: ${WHY[s] ?? "needed by an enabled feature"}${ADMIN_CONSENT_SCOPES.includes(s) ? " (admin consent required)" : ""}`;
      const existing = cfg.clientId ? `\nThere is already an app (client ID ${cfg.clientId}). If you prefer to reuse it, please make sure the permissions below are approved for it and "Allow public client flows" is on.\n` : "";
      const message = [
        "Subject: Request: set up a Microsoft app for the Microsoft 365 plugin for Claude",
        "",
        "Hello,",
        "",
        "I would like to use the Microsoft 365 plugin for Claude Code with my work account. It signs me in as myself and works only with my own mail, calendar, Teams chats and files, through delegated Microsoft Graph permissions (it cannot act as anyone else or on the whole company).",
        existing,
        "Please do this once for the company (Microsoft Entra admin center):",
        "  1. App registrations > New registration. Name: Microsoft 365 plugin. Account type: this organization only.",
        "  2. Redirect URI: platform \"Mobile and desktop applications\", value http://localhost",
        "  3. Authentication > Allow public client flows = Yes.",
        "  4. API permissions > Microsoft Graph > Delegated permissions, add:",
        ...read.map(line),
        ...(write.length ? ["  Permissions for actions I approve myself (preview and confirm each time):", ...write.map(line)] : ["  (Read-only: no permission that can change anything is requested.)"]),
        `  5. Grant admin consent for the organization${admin.length ? ` (needed for: ${admin.join(", ")})` : ""}.`,
        "  6. Send me the Application (client) ID, and the Directory (tenant) ID if my sign-in needs it.",
        "",
        "Nothing needs to be installed on company machines, and the app has no secret.",
        ...(a.note ? ["", String(a.note).slice(0, 300)] : []),
        "",
        "Thank you.",
      ].join("\n");
      return { message, permissions: { read, write, admin_consent: admin }, redirect_uri: "http://localhost", public_client_flows: true, client_id_known: Boolean(cfg.clientId),
        next_step: "Show the user this message to send to their admin. When they get the client ID back, run /m365:init again (or m365_setup_save) with it." };
    },
  },
];
