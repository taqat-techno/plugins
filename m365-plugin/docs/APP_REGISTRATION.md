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

## API permissions (Microsoft Graph, **Delegated**)

| Module | Permissions | Admin consent |
|---|---|---|
| always | `User.Read`, `MailboxSettings.Read`, `offline_access` | no |
| mail | `Mail.Read` | no |
| calendar | `Calendars.Read` | no |
| teams (chats) | `Chat.Read` | no (some tenants require it) |
| people | `People.Read`, `User.ReadBasic.All` | no (some tenants require it) |
| channels (optional) | `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` | **yes** |

Use "Grant admin consent for <tenant>" once so users are not asked individually. Later versions that send mail or
create events add `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, `Chat.ReadWrite`; read-only mode never asks for them.

## Test it

```
M365_CLIENT_ID=<id> node server/cli.mjs sign-in
```

A browser opens. On a machine without a browser use `node server/cli.mjs sign-in --device-code`.

## Errors you may see

| Code | Meaning | Fix |
|---|---|---|
| `CONSENT_NEEDED` | A permission needs admin consent | Grant consent (above) |
| `PUBLIC_CLIENT_NOT_ENABLED` | Public client flows are off | Step 4 |
| `REDIRECT_URI_MISMATCH` | No `http://localhost` redirect | Step 3 |
| `CLIENT_ID_INVALID` | Wrong id or tenant | Check the id and the Tenant setting |
