# Changelog

## [0.3.0] - 2026-11-06

### Fixed (found by a live run against a real tenant)
- **Mail alerts always failed**: the query asked for a `mentionsPreview` property that does not exist in Microsoft's stable Graph (HTTP 400),
  which the offline fake could not reveal. Mail now arrives without it, and a mail mention is detected as an `@name` in the first part of the
  body (approximate, and documented as such). Tool results that mention a missing `People.Read` permission still work through the directory.

### Added
- **`/m365:init` is the first-run setup for every kind of user.** It asks one question: (1) "my admin gave me a client ID",
  (2) "I don't have one" (writes the message to send to the admin), (3) "reuse a sign-in another tool of mine holds", or
  (4) "an approved app exists". New tools: `m365_setup_save` (saves ids and file paths to `~/.m365-plugin/settings.json`, applies
  them without a restart; refuses a file that does not look like a token or secret; Claude Code asks the user first) and
  `m365_access_request` (a ready-to-send admin message built from the enabled modules, each permission explained, admin-consent
  ones marked). The settings file has the lowest priority, never holds a secret, and cannot change read-only mode or modules.
  A cancelled or refused sign-in (AADSTS700171 / AADSTS90135) is now `SIGN_IN_DECLINED` with a hint to ask the admin.
- **Credential files can only be chosen by the person.** The model-callable `m365_setup_save` refuses `refresh_token_file` and
  `client_secret_file` (`CREDENTIAL_SETTING_NOT_ALLOWED`) and refuses to change the client ID or tenant once an app is configured
  (`ALREADY_CONFIGURED`), so injected text cannot redirect the sign-in or point the plugin at a file. The person sets them in the
  plugin settings, in the environment, or by running `node server/cli.mjs setup ...` in their own terminal; a running agent picks
  the change up without a restart. The confirmation prompt shows the exact client ID, tenant and modes with control characters made
  visible, and is refused outright if an argument is too long to show in full.
- **Reuse another tool's saved sign-in.** `M365_REFRESH_TOKEN_FILE` (plugin setting "Shared token file") points at a file holding
  a refresh token that another tool, such as a bot, already obtained; `M365_CLIENT_SECRET_FILE` ("App secret file") points at
  the app's secret if the app has one. The plugin redeems that token (always with the app's approved permissions), so no
  new admin approval is needed, and writes a renewed token back to the same file atomically, as its owner does. `m365_sign_out`
  never deletes the file, `m365_sign_in` reports `MANAGED_EXTERNALLY`, and neither the token nor the secret is ever returned,
  logged or put in an error. `M365_REFRESH_TOKEN_WRITEBACK=false` leaves the file strictly untouched.

## [0.2.3] - 2026-11-06

### Added
- **Use an app's existing approved permissions.** The plugin setting "Permissions to request" (`M365_SCOPE_MODE=app`)
  asks Microsoft for the app's already-approved permissions (Graph `.default`) instead of the plugin's own list. An app an
  admin approved earlier for a bot then needs no new request; a tool whose permission the app lacks reports `ACCESS_NEEDED`.
  The default (`requested`) is unchanged. `m365_auth_status` shows `permissions`.

## [0.2.2] - 2026-11-06

### Security
- The HTML-draft preview now lists every address the body can point at or load, not just quoted `href`/`src`: unquoted
  attributes, `srcset`, `formaction`, `poster`, `xlink:href`, CSS `url()` and `@import`, meta refresh; entities are decoded
  first (`&#104;ttps://...`). The preview reports `link_count` and `links_truncated`, and a draft with more than 200 links
  cannot be sent from here (`PREVIEW_TRUNCATED`) instead of silently listing only some.

## [0.2.1] - 2026-11-06

Fixes from an automated security review of 0.2.0.

### Security
- **The confirmation hook now fails closed.** If the check script or Python is missing, or the script fails, the wrapper
  asks the human instead of allowing the call silently.
- **`email_move` can no longer delete.** It accepts only inbox and archive; deleting goes through `email_delete`, which asks.
  `email_discard_draft` (it can delete a draft the user wrote by hand) is now confirmation-gated as well.
- **What the user previews is what is sent.** Drafts created by the plugin are plain text only (HTML is refused). For an HTML
  draft (a reply, or one edited in Outlook) the preview lists every link and image address and flags hidden markup, and a
  draft too long to preview in full cannot be sent (`PREVIEW_TRUNCATED`).
- **Teams double-send guard is stricter.** Only definite refusals (400, 401, 403, 404, 405, 422, 429) make a message sendable
  again; 408, 409, 5xx and timeouts are an unknown outcome (`SEND_UNCERTAIN`) and are never repeated.

### Tests
- 60 offline Node tests and 30 Python checks, including regression tests for each fix and a test that runs the hook's shell
  command with the script missing, with no Python, and with failing interpreters (it must ask every time).

## [0.2.0] - 2026-11-06

Write path, files, alerts and the OpenClaw package. Because the plugin now asks for write permissions
(`Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, `Chat.ReadWrite`, `Files.ReadWrite`) unless read-only mode is on,
an existing sign-in reports `PERMISSIONS_CHANGED`: run `m365_sign_in` again to approve them (or turn read-only on).

### Added
- **Mail writes:** `email_create_draft`, `email_create_reply_draft`, `email_update_draft`, `email_preview_draft`,
  `email_discard_draft`, `email_send_draft`, `email_move`, `email_mark_read`, `email_set_flag`, `email_delete`
  (to Deleted Items only). Sending is draft -> preview -> `email_send_draft(draft_id, digest)`: refused if never
  previewed, if the digest is wrong, if the draft changed since the preview, if there is no recipient, or if the
  user's text says "attached" (English or Arabic) with nothing attached. A sent draft cannot be sent again.
  Recipients must be email addresses; a name is refused.
- **Calendar writes:** `calendar_stage` (validates, shows local times and conflicts, creates nothing),
  `calendar_commit` (creates the event; the stage id is the Graph `transactionId`, so a retry cannot create it twice),
  `calendar_discard`.
- **Teams writes:** `teams_stage`, `teams_commit`, `teams_cancel`, with a double-send guard: `sending` is saved
  before the request, a refusal (4xx) can be retried, an unknown outcome is never repeated (`SEND_UNCERTAIN`).
- **OneDrive:** `onedrive_search`, `onedrive_read_file` (text-like files up to 200 KB, fenced), `onedrive_share_link`
  (view-only, organization-only). `email_read_attachment` reads text-like attachments; other types are reported as
  not read.
- **Alerts:** `events_since` and `node server/cli.mjs events --since now|<cursor>`: new mail from others, mail that
  mentions the user, Teams messages and @mentions, calendar invitations and cancellations. Stateless (the caller keeps
  the cursor), de-duplicated by id, oldest-first paging with `more`, a failing detector is reported in `errors` and
  holds the cursor time.
- **Confirmation hook** (`hooks/`): Claude Code asks the human before `email_send_draft`, `calendar_commit`,
  `teams_commit`, `email_delete` and `onedrive_share_link`. `data/tools.json` classifies every tool (`read`, `local`,
  `write`, `confirm`); a test keeps the hook matcher in step with it.
- **Read-only mode** is structural: write tools are not listed or callable, only read permissions are requested,
  and the Graph client refuses POST/PATCH/DELETE.
- **OpenClaw / agent package:** `python scripts/build_agent_plugin.py --out <dir>` builds a lean Agent Plugins package
  (read-only by default, bot-facing skill with write rules). Built on demand, not committed.
- `docs/APP_REGISTRATION.md` lists the write permissions.

### Security
- Third-party text in envelopes (subjects, sender and attendee names, locations, chat topics, previews) has control
  and bidirectional characters and forged fence markers removed, is length-capped, and every such result carries a
  note that it is data, never instructions.
- `profile_remember_contact` refuses a name or alias that already belongs to a different address (a poisoned contact
  could otherwise redirect mail); two people sharing a name need the user's explicit `allow_same_name`.

### Tests
- 54 offline Node tests (fake Microsoft) and Python checks for the hook, the package, and cross-file contracts.

## [0.1.0] - 2026-11-06

First release (read-only). Self-contained: no npm packages, no system variables, no admin rights.

### Added
- **MCP server** (`server/index.mjs`), a minimal stdio JSON-RPC implementation on Node 18+ built-ins only.
- **Sign-in** without a secret: browser sign-in (authorization code + PKCE on `http://localhost`) or device code,
  `auto` tries the browser first. The refresh token is cached per user in `~/.m365-plugin/token-cache.json`
  (atomic writes, shared safely by several processes); the access token stays in memory. `server/cli.mjs` signs in
  outside an agent (a bot's first login). Errors map to a code and a fix (`CONSENT_NEEDED`,
  `PUBLIC_CLIENT_NOT_ENABLED`, `REDIRECT_URI_MISMATCH`, `SIGN_IN_EXPIRED`, ...).
- **Read tools:** `email_list_recent`, `email_search`, `email_read`, `email_read_thread`, `email_list_attachments`;
  `calendar_list_events`, `calendar_get_event`, `calendar_find_free_slots` (colleagues' meeting titles are discarded
  in code); `teams_list_chats`, `teams_find_chat`, `teams_read_chat`, `teams_chat_members`; optional `channels` module
  (`teams_list_teams`, `teams_list_channels`, `teams_read_channel`, needs admin consent); `people_find`, `people_resolve`.
- **Local profile** (`~/.m365-plugin/profile.json`, no secrets): identity, time zone, working hours, remembered
  contacts with aliases (Arabic-aware matching), remembered Teams chats. `profile_*` tools, `/m365:init` and `/m365:profile`.
- Message and chat text is returned fenced as untrusted data. Every Graph path is fixed per tool; there is no generic
  Graph request tool and no URL, mailbox or id-of-another-user argument. GET is retried on throttling, POST never.
- Least-privilege scopes: only the modules enabled are requested.
- `data/tools.json` classifies every tool; `docs/APP_REGISTRATION.md` is the one-time admin setup.
