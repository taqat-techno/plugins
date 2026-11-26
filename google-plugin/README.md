# google

Gmail, Google Calendar and Google Drive for Claude Code and agent bots. It is a **local bridge to Google's own Workspace
MCP servers**, signed in with **your own** Google Cloud OAuth client, and it is built the same way as `m365`:

- plain Node ESM with no npm packages;
- a minimal MCP stdio server and a CLI;
- one file, `data/tools.json`, that classifies every tool;
- modules that you switch on or off in config.

**Status: milestones B1–B4 done (bridge, identity, write and confirm classes, agent package).** One sign-in covers
every enabled module. Google's read, write and confirm tools for Gmail, Calendar and Drive are exposed, plus the
plugin's own identity tools.

## Setup

1. Create a Google Cloud OAuth client of type **Desktop app**, enable the Gmail, Calendar and Drive APIs **and their MCP
   APIs**, tick **Use this client for an AI-powered agent**, and download the client's JSON. [docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md) walks through this and is written for
   non-developers.
2. Set the path to that file, either in the plugin setting **Google client JSON file** or in `GOOGLE_CLIENT_SECRET_FILE`.
3. Sign in with `node server/cli.mjs sign-in`, or ask the assistant to call `google_sign_in`.
4. Check it with `node server/cli.mjs status`.
5. Answer Google's confirmation questions once: `node server/cli.mjs grant` (Google keeps the answers 90 days).

## Settings

| Setting (Claude Code) | Environment variable | Meaning |
|---|---|---|
| Google client JSON file | `GOOGLE_CLIENT_SECRET_FILE` | Path to the Desktop app client JSON. Only a path: the plugin never shows or logs the contents. |
| Client ID (optional) | `GOOGLE_PLUGIN_CLIENT_ID` | If set, it must match the file, which already holds the client ID. There is deliberately no plain `GOOGLE_CLIENT_ID` fallback, because that name is common in other projects' environments. |
| Modules (optional) | `GOOGLE_MODULES` | `gmail`, `calendar`, `drive`, comma-separated. Empty means all three. |
| Read-only mode | `GOOGLE_READONLY` | Read scopes only. Write tools are not listed. Switching it needs a new sign-in. |
| (none) | `GOOGLE_PLUGIN_HOME` | Where the sign-in is kept (`token-cache.json`). Default: `~/.google-plugin`. |
| (none) | `GOOGLE_TIMEOUT_MS` | Timeout for each call to Google. Default: 30000. |
| (none) | `GOOGLE_TOOLS_ALLOW` / `GOOGLE_TOOLS_DENY` | Comma-separated tool names. Allow empty = every classified tool; deny wins and applies to every tool, the sign-in tools included. The allow list does not drop the sign-in tools. |
| (none) | `GOOGLE_CONFIRM_MODE` | `forward` (default): pass Google's confirmation form to the MCP client if it supports forms, else fail with `CONFIRMATION_NEEDED`. `error`: never forward. |
| (none) | `GOOGLE_CONFIRM_TIMEOUT_MS` | How long a forwarded form may wait for the human. Default: 600000. |
| Identities file (optional) | `GOOGLE_IDENTITIES_FILE` | Path to the identities JSON (below). `GOOGLE_IDENTITIES` can hold the JSON itself instead. |
| Folder to save files into (optional) | `GOOGLE_DOWNLOAD_DIR` | The one folder `gmail_get_attachment` and `drive_save_file` save into. No default: without it they refuse. |
| (none) | `GOOGLE_MAX_SAVE_MB` | Largest file they save. Default: 25. |
| (none) | `GOOGLE_REFUSE_GUEST_EVENTS` | `1`: calendar changes that involve other people fail with `GUESTS_NEED_APPROVAL` (see Guards). Default off. |
| (none) | `GOOGLE_WRITE_LIMIT_PER_HOUR` | `N`: trash / spam / delete / move calls past N per rolling hour fail with `WRITE_LIMIT_REACHED`. Default off. |
| (none) | `GOOGLE_ATTACH_DIRS` | Folders local files may be attached from (separated like PATH). Default: `GOOGLE_DOWNLOAD_DIR`. Keys, tokens and the plugin's own files are refused even there. |
| (none) | `GOOGLE_BOUNCE_CHECK_SECONDS` | After `gmail_rest_send_draft`, how long to look for a bounce. Default 10, 0 = off, max 30. |
| (none) | `GOOGLE_REST_FALLBACK` | `1`: adds the REST tools (see REST fallback). Default off. |
| (none) | `GOOGLE_MAX_STRING_CHARS` / `GOOGLE_MAX_RESULT_CHARS` | Result size caps. Defaults: 20000 per string, 100000 per result. |

The Claude Code setting (`GOOGLE_PLUGIN_*`) wins over the environment variable.

## Scopes

Every enabled module's scopes are requested at the first sign-in, together with `openid email`, which identify the
account.

| Module | Normal | Read-only |
|---|---|---|
| gmail | `gmail.modify` | `gmail.readonly` |
| calendar | `calendar.events` + `calendar.calendarlist.readonly` | `calendar.events.readonly` + `calendar.calendarlist.readonly` |
| drive | `drive` | `drive.readonly` |

**The plugin never requests `https://mail.google.com/`.** That scope grants full mailbox access, including permanent
delete. Three checks enforce this:

- the request builder refuses it;
- a sign-in whose granted scopes include it is refused with `SCOPE_TOO_BROAD`;
- a test asserts both, for every module and mode combination.

Google's sensitivity class for each scope, with links, is in the setup guide. Google's Calendar scope page gives no
class, so the Calendar entries are marked unverified there.

Google lets the user untick individual permissions at sign-in, so each module's usability comes from the scopes actually
granted:

- If at least one enabled module is usable, the sign-in is kept, and status lists the `missing_scopes` per module.
- A call for a module that wasn't granted gets `SCOPE_NOT_GRANTED`.
- In read-only mode, a sign-in that can change a module's data is not used for that module (`too_broad`).

## Tools

Bridged tools are Google's own, named `<module>_<Google tool name>`. Only those classified in `data/tools.json` are
exposed, with the input schema recorded in `data/google_mcp_snapshot.json`.

| Module | Read tools |
|---|---|
| gmail | `gmail_search_threads`, `gmail_get_thread`, `gmail_get_message`, `gmail_list_labels`, `gmail_list_drafts`, `gmail_get_draft` |
| calendar | `calendar_list_calendars`, `calendar_list_events`, `calendar_get_event`, `calendar_search_events`, `calendar_suggest_time` |
| drive | `drive_search_files`, `drive_list_recent_files`, `drive_get_file_metadata`, `drive_get_file_permissions`, `drive_read_file_content`, `drive_download_file_content` |

| Module | Write tools (removed in read-only mode) | Confirm tools (ask the human first; removed in read-only mode) |
|---|---|---|
| gmail | `gmail_create_draft`, `gmail_create_label`, `gmail_label_thread`, `gmail_unlabel_thread`, `gmail_label_message`, `gmail_unlabel_message`, `gmail_update_message_labels`, `gmail_untrash_thread`, `gmail_untrash_message`, `gmail_unmark_thread_spam`, `gmail_unmark_message_spam` | `gmail_trash_thread`, `gmail_trash_message`, `gmail_apply_sensitive_thread_label`, `gmail_apply_sensitive_message_label`, `gmail_mark_thread_spam`, `gmail_mark_message_spam` |
| calendar | (none) | `calendar_create_event`, `calendar_update_event`, `calendar_delete_event`, `calendar_respond_to_event` |
| drive | (none) | `drive_create_file`, `drive_copy_file`, `drive_upload_file_revision` |

**Confirm class.** Every calendar change is confirm as a whole tool, because each can email other people (invitations,
cancellations, replies to the organiser), and once the human has told Google "Always allow", Google no longer asks. In
Claude Code, `hooks/hooks.json` makes Claude Code ask before any confirm tool runs. Drive create and copy are confirm too: a file created in, or copied
into, a shared folder is visible to everyone who can open it (a copy without parentId lands next to the original). Other hosts read the confirm list
from `data/tools.json` and gate it themselves. The write-class label tools refuse to add `TRASH` or `SPAM`
(`NEEDS_CONFIRM_TOOL`), so that gate cannot be bypassed.

**Not offered.** Google's servers have no tool to send mail, edit or delete a draft, share, move or trash a Drive file,
or delete anything permanently, and the plugin adds no fallback: mail is sent by the human from Gmail. Drafts take
Google's own `htmlBody` for formatting.

Every bridged result is `{ ok: true, tool, untrusted: true, data, truncated?, omitted_content? }`.

### Identities

The plugin's own tools, for a mailbox that receives mail for several addresses (aliases, forwarded domains):

| Tool | Class | What it does |
|---|---|---|
| `gmail_message_identity` | read | Reads one message RAW through Google, parses the headers here and returns `identity`, `matched_by`, `matched_address` and From/To/Cc/Date/Subject/X-Forwarded-For. Never the body. |
| `gmail_identities` | local | Lists the configured identities. Contacts nobody. |

```json
{ "identities": [
  { "id": "sales", "label": "Sales desk", "address": "info@shop.example" },
  { "id": "school", "label": "School", "address": "admin@school.example", "matchTo": ["@school.example"] },
  { "id": "personal", "label": "Personal", "address": "me@mail.example", "default": true }
] }
```

`matchTo` entries are exact addresses or `@domain`; it defaults to `[address]`. At most one identity is the default.
Match order, first hit wins: each address in **X-Forwarded-For** (forwarding services such as Cloudflare Email Routing
put the original recipient there first, so a Bcc'd alias is found too), then To, then Cc, then the default.
**Delivered-To is never used**: after forwarding it names the mailbox, not the alias. There is deliberately no identity
filter on search: Gmail's `to:`/`cc:` cannot see a Bcc'd alias.

### Google's confirmations

Google's servers may ask the human to allow a read (in a test on 2026-11-26, Gmail asked once per tool, and once per
email from an external sender; Calendar and Drive did not ask). **The plugin never answers such a form itself.** It
forwards the form to its MCP client as `elicitation/create` when the client declared form support, and passes back only
an answer that is one of the form's choices; otherwise the call fails with `CONFIRMATION_NEEDED` and the hint tells the
human to run `grant`. Google documents that saved approvals expire after 90 days and that users can't view or revoke
them; only Google Workspace admin controls exist (see the setup guide).

| Tool | Class | What it does |
|---|---|---|
| `google_sign_in` | local | Starts a browser sign-in (loopback `http://127.0.0.1:<port>` + PKCE S256) and returns at once. |
| `google_auth_status` | local | Reports the account, enabled modules and which are usable, requested vs granted vs missing scopes, `token_obtained_at`, `token_age_days`, `last_refresh_at` and `auth_error`. It refreshes the token live by default; pass `verify: false` to skip that. It never returns a token. |
| `google_sign_out` | local | Deletes the local token cache. |

## CLI

```
node server/cli.mjs sign-in
node server/cli.mjs status [--offline]
node server/cli.mjs sign-out
node server/cli.mjs grant [--fresh] [tool ...] # answer Google's forms yourself, once per read tool
                                             # --fresh looks past items already allowed per email / owner
node server/cli.mjs schema-check [--update] # Google's live tool list vs the recorded snapshot
node server/cli.mjs identity <messageId>    # gmail_message_identity from your terminal (headers only)
```

`grant <write tool> --target <id>` (for `calendar_delete_event`, `gmail_trash_message`, `gmail_trash_thread`,
`gmail_mark_message_spam`, `gmail_mark_thread_spam`) runs that ONE write for real on the item you name, after you type
"yes", so Google's question for a write can be answered. Use an item you are happy to change.

`grant` calls each read tool once on a harmless target (the first thread, draft, event or file it finds;
`METADATA_ONLY` where offered), shows Google's form as sent and sends only the number you type (`c` cancels). It prints
whether Google asked and your answer, never the data. `schema-check` exits 3 when Google added tools or changed or removed
an exposed one; `--update` records the live list (the tests then require a class for any new tool).

Exit codes:

- `0`: signed in, and for `status` the live refresh also worked;
- `3`: not signed in, the sign-in failed, or the live check failed;
- `1`: unexpected error;
- `2`: wrong usage.

## Contract

**Results.** A success is `{ ok: true, ... }`. An error is returned with `isError`, contains **text blocks only**, and is
shaped `{ ok: false, error: { code, message, hint? } }`.

**Sign-in error codes.** `AUTH_REQUIRED` means there is no usable sign-in. `AUTH_EXPIRED` means Google refused the
saved sign-in because it expired or was revoked. In both cases, ask the human to sign in and don't retry. The other codes
are:

- `NOT_CONFIGURED`, `CLIENT_TYPE_WRONG`, `CLIENT_MISMATCH`, `CLIENT_INVALID`
- `SCOPE_NOT_GRANTED`, `SCOPE_TOO_BROAD`, `MODULE_DISABLED`
- `SIGN_IN_DECLINED`, `SIGN_IN_TIMEOUT`
- `AUTH_BLOCKED`, `AUTH_FAILED`
- `NETWORK_ERROR`, `TIMEOUT`

**Bridge error codes.** `CONFIRMATION_NEEDED` (the human runs `grant`), `CONFIRMATION_NOT_ANSWERED`,
`INVALID_CONFIRMATION_ANSWER`, `UNSUPPORTED_CONFIRMATION`, `CONFIRMATION_UNSUPPORTED` (Google refuses without offering a form; `grant` cannot help), `CONFIRMATION_LOOP`, `CONFIG_INVALID` (identities), `NEEDS_CONFIRM_TOOL`, `HEADERS_TOO_LARGE`, `INVALID_ARGUMENT`, `GOOGLE_FORBIDDEN` (API/MCP API not
enabled, or the client not marked for AI agents), `RATE_LIMITED`, `GOOGLE_UNAVAILABLE`, `GOOGLE_ERROR`, `TOOL_ERROR`
(Google's own tool error), `UNKNOWN_TOOL`.

**Token cache.** The cache is `<GOOGLE_PLUGIN_HOME>/token-cache.json`, written atomically (temp file + rename) with mode
0600. It holds the refresh token, the granted scopes, the account address, `obtained_at` and `last_refresh_at`.

- The access token is kept in memory only.
- If Google sends a new refresh token, it is written back at once.
- If a refresh fails with `invalid_grant` and another process has saved a newer token, the plugin retries once with that
  token.

**Account address.** It comes from the ID token at sign-in, and the live check reads it from Google's OpenID user-info
endpoint. That way it works whichever modules are on.

**Fixed endpoints.** The endpoints are fixed in the code: `accounts.google.com`, `oauth2.googleapis.com` and
`openidconnect.googleapis.com`. Only `client_id` and `client_secret` are read from the client JSON, so an edited file
cannot redirect a code or token.

**No device-code sign-in.** Google's device flow does not allow these scopes, and the copy-paste (OOB) flow is no longer
supported. Sign-in needs a browser on the machine that runs the plugin.

## Files

| Tool | Class | What it does |
|---|---|---|
| `gmail_get_attachment` | read | Without `attachment`: lists the message's attachments. With an index or exact filename: saves it into `GOOGLE_DOWNLOAD_DIR` and returns path, filename, mimeType, size. |
| `drive_save_file` | read | Saves a Drive file there (Google files exported, `exportMimeType` optional). Google refuses it for files owned by other people (`CONFIRMATION_UNSUPPORTED`); `drive_read_file_content` still reads those. |

Files are never returned as bytes, never overwrite an existing file, and get a cleaned name inside that folder only.

## Guards (off by default)

- `GOOGLE_REFUSE_GUEST_EVENTS=1`: `calendar_create_event` / `calendar_update_event` naming anyone other than the
  signed-in person, and `calendar_update_event` / `calendar_delete_event` / `calendar_respond_to_event` on an event
  with other attendees or another organiser (looked up first; a failed lookup refuses), fail with
  `GUESTS_NEED_APPROVAL`. A host can run one server with it on for direct use and a second, behind its own approval
  step, with it off.
- `GOOGLE_WRITE_LIMIT_PER_HOUR=N`: at most N calls per rolling hour, per server process, of Gmail trash, spam and
  sensitive labels, `calendar_delete_event`, `gmail_rest_delete_draft`, `drive_rest_trash_file` and
  `drive_rest_move_file`; then `WRITE_LIMIT_REACHED`.

## REST fallback (off by default)

`GOOGLE_REST_FALLBACK=1` adds tools for what Google's MCP servers lack, through Google's REST APIs with the same
sign-in (no new scope). With the switch off they are not listed and are refused; read-only mode drops them.

| Tool | Class | What it does |
|---|---|---|
| `gmail_rest_preview_draft` | read | The draft as it would be sent: every From, Sender, Reply-To, To, Cc, Bcc and Subject value, the text body and the HTML body as text (`text_and_html_differ`), attachments, From verified or not, `sendable` / `blockers`, and a digest. |
| `gmail_rest_send_draft` | confirm | Re-reads the draft, checks the preview's digest (`DRAFT_CHANGED`), the blockers (`MULTIPLE_HEADERS`, `PREVIEW_INCOMPLETE`) and a verified From (`IDENTITY_NOT_VERIFIED`), sends exactly those checked bytes in the draft's thread, then deletes the draft. |
| `gmail_rest_create_reply_draft` | write | Reply draft in the thread (In-Reply-To, References, "Re:"), From = chosen or the verified alias the mail was sent to. |
| `gmail_rest_create_forward_draft` | write | Forward draft with the original text and attachments (25 MB max). |
| `gmail_rest_create_draft` | write | New draft from a chosen verified send-as address, with that address's Gmail signature (`includeSignature`, default true) and local `attachments` (inline with `contentId` for `<img src="cid:ID">`). |
| `gmail_rest_save_draft_html` | read | One safe, self-contained .html file of a draft in the download folder (header block + body as sent, inline images, no scripts or network), with the send digest. The From address's own signature images are fetched and embedded (only URLs from that signature in Gmail settings; https, public hosts, images up to 1 MB). |
| `gmail_rest_update_draft` / `gmail_rest_delete_draft` | write | Change only the given fields of a draft (the rest, threading and attachments are kept) / delete a draft. |
| `drive_rest_trash_file` / `drive_rest_move_file` | confirm | Trash (recoverable about 30 days) / move into another folder. |
| `drive_rest_untrash_file` / `drive_rest_rename_file` | write | Restore / rename. |
| `drive_rest_share_file` / `drive_rest_unshare_file` | confirm | Share with one person or group (reader, commenter, writer; no public links, never ownership) / remove access (never the owner's). |

Signatures: the REST draft tools add the From address's own Gmail signature (Settings > See all settings > Signature,
per address) unless `includeSignature` is false, and report `signature_added`.

Google's Workspace AI Tools Addendum says AI agents must use Google's MCP servers instead of REST from 2027-02-01.
What Google does with a client that keeps using REST after that is not documented. `schema-check` exits 4 and lists
`may_replace_rest` when Google adds a tool that may replace one of these, so the REST tool can be removed.

## Agent package (OpenClaw and other hosts)

```
python scripts/build_agent_plugin.py --out <dir>
```

builds a host-neutral Agent Plugins package: `plugin.json`, `mcp.json` (starts `node ${PLUGIN_ROOT}/server/index.mjs`),
one bot-facing skill, `data/tools.json`, the tool snapshot, the setup guide and the server. It has no Claude Code hook:
the host must gate the `confirm` class itself. It does not force read-only mode (that would need a new sign-in); use
`GOOGLE_TOOLS_DENY` / `GOOGLE_TOOLS_ALLOW` to narrow the tools. The package's own README lists the environment variables.

## Tests

```
node --test tests/*.test.mjs   # offline: a fake Google OAuth and MCP layer, no network
python -m pytest tests -q      # adds the Node suite, a stdio smoke test, and wiring and no-personal-values checks
```
