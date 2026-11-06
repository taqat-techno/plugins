// sign-in tools. Sign-in is asynchronous: m365_sign_in starts it and returns at once, so the agent
// can tell the user what to do; m365_auth_status shows when it has finished.
export const tools = [
  {
    name: "m365_sign_in", kind: "local", module: "auth",
    description: "Start signing in to Microsoft 365 with the user's work account. mode 'interactive' opens a browser; 'device-code' returns a short code to type at a Microsoft page (for machines without a browser); 'auto' (default) tries the browser first. Returns what the user must do, at once; then call m365_auth_status until signed_in is true. No password or token passes through the agent.",
    inputSchema: { type: "object", properties: { mode: { type: "string", description: "auto (default), interactive or device-code." } } },
    async handler(a, ctx) { return ctx.auth.startSignIn({ mode: a.mode }); },
  },
  {
    name: "m365_auth_status", kind: "local", module: "auth",
    description: "Show whether Microsoft 365 is configured and signed in (account name, tenant, enabled modules, read-only flag) and the state of a sign-in in progress. Call it first when a tool reports NOT_SIGNED_IN.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return ctx.auth.status(); },
  },
  {
    name: "m365_sign_out", kind: "local", module: "auth",
    description: "Forget the saved Microsoft sign-in on this computer. The local profile is kept.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return ctx.auth.signOut(); },
  },
];
