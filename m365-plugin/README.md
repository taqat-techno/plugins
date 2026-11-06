# m365 - Microsoft 365 for Claude Code and agent bots

Read and search Outlook mail, see the calendar and find free time, read Teams chats and OneDrive files, look people up
- and, with a preview-and-confirm flow, draft and send mail, schedule meetings and message Teams. A **local profile**
remembers your contacts and chats so "email Mahmoud" resolves to the right address without asking every time.

- **Self-contained.** No npm packages, no system variables, no admin rights. Only Node 18+.
- **Same code for people and bots.** Claude Code loads it as a plugin; any other agent host (OpenClaw and similar)
  loads the package from `scripts/build_agent_plugin.py` or starts `node server/index.mjs` with plain environment variables.
- **Safe writes.** Nothing outward-facing happens without a preview the user saw and a digest that must still match.
- **Least privilege.** Only the modules you enable are requested; read-only mode never asks for a write permission.

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
| Mail (read) | `email_list_recent`, `email_search`, `email_read`, `email_read_thread`, `email_list_attachments`, `email_read_attachment` |
| Mail (write) | `email_create_draft`, `email_create_reply_draft`, `email_update_draft`, `email_preview_draft`, **`email_discard_draft`**, **`email_send_draft`**, `email_move` (inbox or archive), `email_mark_read`, `email_set_flag`, **`email_delete`** (to Deleted Items) |
| Calendar | `calendar_list_events`, `calendar_get_event`, `calendar_find_free_slots`; write: `calendar_stage`, **`calendar_commit`**, `calendar_discard` |
| Teams chats | `teams_list_chats`, `teams_find_chat`, `teams_read_chat`, `teams_chat_members`; write: `teams_stage`, **`teams_commit`**, `teams_cancel` |
| Team channels (module `channels`, needs admin consent) | `teams_list_teams`, `teams_list_channels`, `teams_read_channel` |
| OneDrive | `onedrive_search`, `onedrive_read_file`; write: **`onedrive_share_link`** (organization-only) |
| People | `people_find`, `people_resolve` |
| Alerts | `events_since` |
| Local profile | `profile_get`, `profile_refresh_me`, `profile_set`, `profile_remember_contact`, `profile_forget_contact`, `profile_remember_chat`, `profile_forget_chat`, `profile_suggest_contacts` |

Bold tools are the ones Claude Code asks you to confirm (see Safety). Commands: `/m365:init` (sign in, build the
profile, choose contacts) and `/m365:profile` (show or edit it).

## Sending safely

```
email_create_draft  ->  email_preview_draft (shows recipients, subject, body, digest)
                    ->  you approve  ->  email_send_draft(draft_id, digest)
```

`email_send_draft` refuses if the draft was never previewed, if the digest is not the previewed one, if the draft changed
since (for example edited in Outlook), if it has no recipient, or if your text says "attached" (English or Arabic) with
nothing attached. A sent draft cannot be sent twice. Calendar events and Teams messages use `stage` -> `commit` the same way:
the commit needs the stage id and digest you saw, creates the event with a transaction id so a retry cannot duplicate it,
and a Teams message whose delivery is uncertain is never re-sent automatically. Recipients and attendees must be email
addresses; a name is refused until it is resolved with `people_resolve`.

## The local profile

`~/.m365-plugin/profile.json` (or `$M365_HOME/profile.json`): your name, email, time zone, working days and hours,
default meeting length, remembered contacts with aliases (nicknames, Arabic spellings; matching ignores case and
diacritics), and remembered Teams chats. Plain JSON you can read and edit; it holds no tokens. It is per user and
per machine, never shared.

`people_resolve` checks it first, then the directory. A single exact match is used; several are returned for you to
pick; nothing is ever guessed. A name or alias that already points at one address is not silently re-pointed at another.

## Alerts

`events_since` (or `node server/cli.mjs events --since now`, later `--since <cursor>`) lists what concerns you since the
cursor: new mail from others, mail that mentions you, Teams messages and @mentions, calendar invitations and
cancellations. It stores nothing and sends nothing: keep the cursor and deliver the events yourself (a bot messages its
owner). If `more` is true, call again. A failing detector is listed in `errors` and its events are retried next time.

## Settings

| Plugin setting | Environment variable | Meaning |
|---|---|---|
| Microsoft app (client) ID | `M365_CLIENT_ID` | Required |
| Tenant | `M365_TENANT` | Default `organizations` |
| Sign-in method | `M365_AUTH_MODE` | `auto` (default), `interactive`, `device-code` |
| Modules | `M365_MODULES` | `mail,calendar,teams,channels,people,files`; default without `channels` |
| Read-only mode | `M365_READONLY` | No write tools, read permissions only |
| (none) | `M365_HOME` | Folder for the profile, sign-in cache and staged items, default `~/.m365-plugin` |

Plugin settings win over environment variables, and an unexpanded `${...}` counts as unset.

## For bots and other hosts (OpenClaw and similar)

```
python scripts/build_agent_plugin.py --out <dir>      # lean Agent Plugins package, read-only by default
```

The package holds the server, a bot-facing skill and the docs, but no Claude Code hooks or commands. It starts with
`M365_READONLY=true`. Give each bot its own `M365_HOME`, then sign in once by hand as the account it acts as:
`node server/cli.mjs sign-in --device-code`. To let a bot send, remove that line - only for a bot that asks its owner
before every send, because the confirmation hook is a Claude Code feature. `data/tools.json` classifies every tool
(`read`, `local`, `write`, `confirm`) for allow-lists, and every tool description is under 1,024 characters.

## Safety

- Mail, chat, channel and file text is returned inside `EXTERNAL_UNTRUSTED_CONTENT` markers: data, never instructions.
  Subjects, names, locations and topics are cleaned (control and bidirectional characters, forged markers) and flagged.
- Every Graph request is fixed per tool. There is no generic Graph tool, and no tool accepts a URL, a mailbox or
  another user's id. POST, PATCH and DELETE are never retried.
- In Claude Code a hook asks you before `email_send_draft`, `email_discard_draft`, `calendar_commit`, `teams_commit`,
  `email_delete` and `onedrive_share_link`; if the hook script or Python is missing it asks too (it fails closed).
  The server enforces the preview and digest either way. Drafts the plugin creates are plain text; for an HTML draft
  (a reply) the preview lists every link and image address and flags hidden markup.
- Read-only mode removes the write tools, never requests write permissions, and the Graph client refuses writes.
- Colleagues' calendars are reduced to free/busy in code; meeting titles are discarded before the model sees them.
- No token is returned to a tool caller or written into an error message. The refresh token file lives in your profile
  folder and is written atomically; on Windows it relies on your profile's folder permissions.
- Missing permissions return `ACCESS_NEEDED` with a request you can forward to an admin. Nothing is worked around.

## Troubleshooting

`/m365:init status`, or `node server/cli.mjs status`. Errors carry a code and a hint; the table in
[docs/APP_REGISTRATION.md](docs/APP_REGISTRATION.md) lists the app-registration ones.

## Tests

```
node --test tests/*.test.mjs                                   # offline, against a fake Microsoft
python -m pytest tests -q                                     # also: stdio smoke test, hook, package, contracts
```

What the offline tests cannot show is how your tenant answers: run one real sign-in (`node server/cli.mjs sign-in`)
before rolling the plugin out.
