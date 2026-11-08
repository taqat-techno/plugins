# One-time app registration (an admin does this once for the company)

The plugin signs each user in with their own work account through a Microsoft Entra **app registration**.
Users register nothing and need no admin rights; they only sign in. The app carries no secret.

## Create the app

1. Microsoft Entra admin center > App registrations > New registration.
2. Name: `Microsoft 365 plugin`. Supported account types: this organization only (or multi-tenant if you need it).
3. Redirect URI: platform **Mobile and desktop applications**, value `http://localhost`.
4. After creating: Authentication > **Allow public client flows = Yes**. Save.
5. Copy the **Application (client) ID**. Users enter it in the plugin setting "Microsoft app (client) ID"
   (or set `M365_CLIENT_ID`). It is not a secret. The **Directory (tenant) ID** is optional.

If your company already has an app that signs a bot in with a client secret, you can reuse it: turn on
"Allow public client flows" and add the `http://localhost` redirect. Its existing secret use is unaffected.

**No admin change possible?** If that app allows only one exact redirect (for example `http://localhost:8400/callback`)
and has a secret, the plugin can sign in with it as it is: set `M365_REDIRECT_URI` (plugin setting "Sign-in redirect
address") to exactly that address and `M365_CLIENT_SECRET_FILE` to the file holding the secret, then sign in with the
browser (`node server/cli.mjs sign-in --interactive`, or `m365_sign_in` with `mode: "interactive"`). The device code
flow often fails for such an app with AADSTS7000218 even when the secret is sent; use the browser flow instead.
Add `M365_SCOPE_MODE=app` so only the app's already-approved permissions are requested.

## API permissions (Microsoft Graph, **Delegated**)

Read permissions are requested for the modules a user enables. The write permissions are added unless the user turns
**read-only mode** on (then none of them is ever requested).

| Module | Read | Write (not in read-only mode) | Admin consent |
|---|---|---|---|
| always | `User.Read`, `MailboxSettings.Read`, `offline_access` | | no |
| mail | `Mail.Read` | `Mail.ReadWrite`, `Mail.Send` | no |
| calendar | `Calendars.Read` | `Calendars.ReadWrite` | no |
| teams (chats) | `Chat.Read` | `Chat.ReadWrite` | no (some tenants require it) |
| people | `People.Read`, `User.ReadBasic.All` | | no (some tenants require it) |
| files | `Files.Read.All` | `Files.ReadWrite` | no |
| channels (optional) | `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` | | **yes** |
| meetings (optional) | `Calendars.Read`, `Chat.Read`, `OnlineMeetingTranscript.Read.All`, `Files.Read.All` | | **yes** (transcripts) |

Use "Grant admin consent for <tenant>" once so users are not asked individually. If your company restricts what users
may consent to, grant these for the app up front.

After upgrading from a version that only read, each user is told `PERMISSIONS_CHANGED` and runs `m365_sign_in` again to
approve the added permissions.

## Reusing an app that is already approved (no new admin request)

If an admin already approved an app for another purpose (a bot, for example), the plugin can use exactly those
permissions instead of asking for its own list: set the plugin setting "Permissions to request" to `app`
(or `M365_SCOPE_MODE=app`). It then asks Microsoft for the app's existing approved permissions (Graph's `.default`),
so no new approval is needed. Tools whose permission the app does not have return `ACCESS_NEEDED` naming it; the rest work.
The app still needs "Allow public client flows" and the `http://localhost` redirect (above). Read-only mode still removes the
write tools, but in this mode it cannot narrow what the app is allowed to do, so it is a tool-level guard only.

## Reusing another tool's saved sign-in (advanced, bot owners only)

Users never need this: each user, on each computer, enters the client ID and signs in. If a bot already holds a refresh token for the app, the plugin can use it (`M365_REFRESH_TOKEN_FILE`, and
`M365_CLIENT_SECRET_FILE` if the app has a secret) instead of a new sign-in. No new approval is needed because that sign-in
was already approved. See the README section "Reusing another tool's sign-in".

## Test it

```
M365_CLIENT_ID=<id> node server/cli.mjs sign-in
```

A browser opens. On a machine without a browser use `node server/cli.mjs sign-in --device-code`.

## Errors you may see

| Code | Meaning | Fix |
|---|---|---|
| `CONSENT_NEEDED` | A permission needs admin consent | Grant consent (above) |
| `PUBLIC_CLIENT_NOT_ENABLED` | Public client flows are off, or the app has a secret and the device code flow is refused | Step 4, or the browser flow with `M365_REDIRECT_URI` (above) |
| `REDIRECT_URI_MISMATCH` | The redirect address is not registered | Step 3, or set `M365_REDIRECT_URI` to the app's exact registered address |
| `REDIRECT_PORT_BUSY` | Another program uses the redirect's port | Close it (often a sign-in still waiting) and retry |
| `CLIENT_ID_INVALID` | Wrong id or tenant | Check the id and the Tenant setting |
| `PERMISSIONS_CHANGED` | The saved sign-in lacks newly requested permissions | Sign in again, or enable read-only mode |
| `ACCESS_NEEDED` | A call was refused for a missing permission | The message names it; grant it for the app |
