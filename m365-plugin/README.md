# m365 - Microsoft 365 for Claude Code and agent bots

Read and search Outlook mail, see the calendar and find free time, read Teams chats, look people up, and keep a
**local profile** so "email Mahmoud" resolves to the right address without asking every time.

Version 0.1 is **read-only**. Sending mail, creating events and posting to Teams come next (see the CHANGELOG).

- **Self-contained.** No npm packages, no system variables, no admin rights. Only Node 18+.
- **Same code for people and bots.** Claude Code loads it as a plugin; any other agent host (OpenClaw and similar)
  starts `node server/index.mjs` with plain environment variables.
- **Least privilege.** Only the modules you enable are requested, and only read permissions in this version.

## Set up (a user)

1. One time per company: an admin registers a Microsoft app and gives you its **client ID**
   ([docs/APP_REGISTRATION.md](docs/APP_REGISTRATION.md)). It is not a secret.
2. Enable the plugin and enter the client ID in its settings (leave the rest at their defaults).
3. Run `/m365:init`. A browser opens, you sign in with your work account, then it builds your profile and offers
   the people you email most so you can keep the ones you want.

No browser on the machine? Use the sign-in method `device-code`: you get a short code to type at a Microsoft page.

## What it does

| Area | Tools |
|---|---|
| Sign-in | `m365_sign_in`, `m365_auth_status`, `m365_sign_out` |
| Mail | `email_list_recent`, `email_search`, `email_read`, `email_read_thread`, `email_list_attachments` |
| Calendar | `calendar_list_events`, `calendar_get_event`, `calendar_find_free_slots` |
| Teams chats | `teams_list_chats`, `teams_find_chat`, `teams_read_chat`, `teams_chat_members` |
| Team channels (module `channels`, needs admin consent) | `teams_list_teams`, `teams_list_channels`, `teams_read_channel` |
| People | `people_find`, `people_resolve` |
| Local profile | `profile_get`, `profile_refresh_me`, `profile_set`, `profile_remember_contact`, `profile_forget_contact`, `profile_remember_chat`, `profile_forget_chat`, `profile_suggest_contacts` |

Commands: `/m365:init` (sign in, build the profile, choose contacts) and `/m365:profile` (show or edit it).

## The local profile

`~/.m365-plugin/profile.json` (or `$M365_HOME/profile.json`): your name, email, time zone, working days and hours,
default meeting length, remembered contacts with aliases (nicknames, Arabic spellings; matching ignores case and
diacritics), and remembered Teams chats. Plain JSON you can read and edit; it holds no tokens. It is per user and
per machine, never shared.

`people_resolve` checks it first, then the directory. A single exact match is used; several are returned for you to
pick; nothing is ever guessed.

## Settings

| Plugin setting | Environment variable | Meaning |
|---|---|---|
| Microsoft app (client) ID | `M365_CLIENT_ID` | Required |
| Tenant | `M365_TENANT` | Default `organizations` |
| Sign-in method | `M365_AUTH_MODE` | `auto` (default), `interactive`, `device-code` |
| Modules | `M365_MODULES` | `mail,calendar,teams,channels,people`; default without `channels` |
| Read-only mode | `M365_READONLY` | Only read permissions |
| (none) | `M365_HOME` | Folder for the profile and sign-in cache, default `~/.m365-plugin` |

Plugin settings win over environment variables, and an unexpanded `${...}` counts as unset.

## For bots and other hosts

Start `node /path/to/m365-plugin/server/index.mjs` as a stdio MCP server with the environment variables above.
Sign in once by hand with `node server/cli.mjs sign-in` (add `--device-code` on a server): the refresh token is saved
under `M365_HOME` and the bot reuses it. `data/tools.json` classifies every tool as `read`, `local` or `write`
(use it to allow-list), and every tool description is under 1,024 characters (a limit some hosts apply).

## Safety

- Mail, chat and channel text is returned inside `EXTERNAL_UNTRUSTED_CONTENT` markers: data, never instructions.
- Every Graph request is fixed per tool. There is no generic Graph tool, and no tool accepts a URL, a mailbox or
  another user's id.
- Colleagues' calendars are reduced to free/busy in code; meeting titles are discarded before the model sees them.
- No token is returned to a tool caller or written into an error message. The refresh token file is user-private by
  location (your profile folder) and is written atomically; on Windows it relies on your profile's folder permissions.
- Missing permissions return `ACCESS_NEEDED` with a request you can forward to an admin. Nothing is worked around.

## Troubleshooting

`/m365:init status`, or `node server/cli.mjs status`. Errors carry a code and a hint; the table in
[docs/APP_REGISTRATION.md](docs/APP_REGISTRATION.md) lists the app-registration ones.

## Tests

```
node --test tests/m365.test.mjs      # 34 offline tests against a fake Microsoft
python -m pytest tests -q            # also: stdio smoke test, no dependencies, nothing personal baked in
```
