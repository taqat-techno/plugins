// Sign-in tools (class "local": they change only this computer's saved sign-in). Sign-in is asynchronous:
// google_sign_in starts it and returns at once so the agent can tell the human what to do; google_auth_status shows
// when it has finished. One sign-in covers every enabled module (gmail, calendar, drive).
export const tools = [
  {
    name: "google_sign_in", kind: "local", module: "auth",
    description: "Start signing in to Google (Gmail, Calendar and Drive, whichever modules are enabled) in a browser on this computer: the human signs in and allows access on Google's page, ticking every permission box. Returns at once with what the human must do; then call google_auth_status until signed_in is true. Use it when a tool reports AUTH_REQUIRED, AUTH_EXPIRED or SCOPE_NOT_GRANTED, and only when the human asks or agrees. No password, token or client secret passes through the agent: never ask for one.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return ctx.auth.startSignIn(); },
  },
  {
    name: "google_auth_status", kind: "local", module: "auth",
    description: "Show whether Google is configured and signed in: account address, enabled modules and which are usable, requested vs granted scopes, read-only flag, when the sign-in was obtained and its age in days, the last successful token refresh, and any sign-in in progress. Never returns a token. By default it refreshes the token live (verified=true proves the sign-in works now); verify=false skips contacting Google. auth_error.code AUTH_EXPIRED or AUTH_REQUIRED means a human must sign in again: tell them, do not retry in a loop.",
    inputSchema: { type: "object", properties: { verify: { type: "boolean", description: "Refresh the token live (default true)." } } },
    async handler(a, ctx) { return ctx.auth.status({ verify: a.verify !== false }); },
  },
  {
    name: "google_sign_out", kind: "local", module: "auth",
    description: "Forget the saved Google sign-in on this computer (deletes the local token cache). It does not remove the app's access at Google; the result says where the human can do that.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return ctx.auth.signOut(); },
  },
];
