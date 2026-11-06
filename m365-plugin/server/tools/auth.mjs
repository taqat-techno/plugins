// sign-in and setup tools. Sign-in is asynchronous: m365_sign_in starts it and returns at once, so the agent
// can tell the user what to do; m365_auth_status shows when it has finished.
// m365_setup_save and m365_access_request are what /m365:init uses to set a user up, whatever their situation:
// they have a client id from their admin, they need to ask for one, or they reuse a sign-in another tool holds.
import { ADMIN_CONSENT_SCOPES, READ_SCOPES, WRITE_SCOPES } from "../config.mjs";
import { saveSettings } from "../setup.mjs";

const WHY = {
  "User.Read": "read your own name and email", "MailboxSettings.Read": "read your time zone and language",
  "Mail.Read": "read and search your mail", "Mail.ReadWrite": "create drafts and manage your mail", "Mail.Send": "send mail you approved",
  "Calendars.Read": "read your calendar", "Calendars.ReadWrite": "create events you approved",
  "Chat.Read": "read your Teams chats", "Chat.ReadWrite": "send Teams messages you approved",
  "People.Read": "find people you work with", "User.ReadBasic.All": "look colleagues up in the directory",
  "Files.Read.All": "find and read your OneDrive files", "Files.ReadWrite": "create view links for your files",
  "Team.ReadBasic.All": "list your teams", "Channel.ReadBasic.All": "list team channels", "ChannelMessage.Read.All": "read team channel messages",
};

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
    description: "Save the user's Microsoft 365 setup (used by /m365:init) and apply it at once: client_id (the Application ID their admin gave them), tenant, scope_mode ('app' = use the permissions already approved for the app) and auth_mode. Only for FIRST setup: once an app is configured its client_id and tenant cannot be changed from here. It can never point the plugin at a token or secret file: only the user can, in the plugin settings or by running 'node server/cli.mjs setup' themselves. Claude Code asks the user to confirm before this runs.",
    inputSchema: { type: "object", properties: {
      client_id: { type: "string", description: "Application (client) ID, a GUID." },
      tenant: { type: "string", description: "Tenant id or domain; default organizations." },
      scope_mode: { type: "string", description: "requested (default) or app." },
      auth_mode: { type: "string", description: "auto, interactive or device-code." },
      refresh_token_file: { type: "string", description: "Not accepted here (the user sets it themselves)." },
      client_secret_file: { type: "string", description: "Not accepted here (the user sets it themselves)." } } },
    async handler(a, ctx) {
      const r = saveSettings(ctx.cfg, a, { viaTool: true });
      ctx.reload();
      return { ...r, now: ctx.auth.status(), note: "Settings from the plugin's own settings page or environment variables still take priority over this file." };
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
