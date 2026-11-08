# Changelog

## [0.8.1] - 2026-11-08

### Fixed
- Attachment guard: the never-attachable OS credential and browser-profile folders now match case-insensitively on Linux too (a copied Windows profile keeps `AppData/Roaming/Microsoft/Protect`). Test fixtures use reserved `.example` domains.

## [0.8.0] - 2026-11-08

### Added
- **Formatted emails.** Draft, reply and forward text can use `**bold**`, `*italic*`, `__underline__`, `==highlight==`
  (yellow), `~~strike~~`, and lines starting `- ` (bullets) or `1. ` (numbered list). The plugin turns only these marks
  into fixed HTML tags, on fully escaped text, so the model still never writes HTML and no link, image, colour or hidden
  text can come from it. Works with or without a signature file; text without marks stays a plain-text email as before.
  A mark inside a word (`a==b`, `snake__case__x`, `2*3*4`) is left as typed.
- The preview shows the same marks (also for `<b>`, `<strong>`, `<em>`, `<u>`, `<s>`, highlights and lists in a draft
  edited in Outlook), so the person sees exactly which words are formatted. `email_create_*` answers `formatted`.

### Changed
- `email_create_draft` answers `signature` as whether the user's signature was added (it used to mean "the body is HTML").

## [0.7.2] - 2026-11-08

### Security
- **Hook and server act on the same path, always.** The server no longer trims a path: leading or trailing spaces,
  control and hidden (zero-width, bidirectional) characters are refused. The hook offers an attachment for approval only
  when the path resolves to an existing local file, and always hands the tool that resolved path; anything else is
  refused before a prompt appears.
- **Folder checks compare like with like.** The home folder, the plugin's own folder and the configured token files are
  matched in both their configured and their resolved spelling. OS credential/DPAPI folders and browser-profile folders
  are refused wherever they appear in a path again (0.7.1 had narrowed them to the current home); only `~/.claude` and
  `~/.config` stay home-anchored.

## [0.7.1] - 2026-11-08

### Security
- **The confirmation shows the file that is really sent.** For a path that is a link, junction or short name, the hook
  shows where it really points and hands that resolved path to the tool, so re-pointing the link after approval changes
  nothing. A path that resolves to a network or device location is refused by the server.
- **chat-files is no longer a free folder.** A file there is accepted only if it is exactly what the hook writes
  (`<session>/pasted-<its own sha256 prefix>.<png|jpg|gif|webp>` with real image bytes), in both modes, so a file put there
  by anything else is refused.
- **Path aliases cannot dodge the deny-list.** Real paths come from the native realpath (8.3 short names expanded, on-disk
  case), and comparisons ignore case on macOS as well as Windows.
- **Broader deny-list in `anywhere` mode:** `.credentials.json`, `.git-credentials`, `.netrc`/`_netrc`, `.npmrc`,
  `.pypirc`, `.htpasswd`, `msal_token_cache.*`, `.password-store`, and, under the home folder, `~/.claude`, `~/.config`,
  keyrings and browser profile folders (a project's own `.claude/docs` stays attachable).

## [0.7.0] - 2026-11-08

### Added
- **Attach any file, and screenshots pasted into the chat.** `email_add_attachment` takes `chat_image` (1 = the image the
  user pasted most recently): the Claude Code hook finds it in the session transcript (only the user's own pastes, never an
  image a tool or web page returned), checks it really is a PNG/JPEG/GIF/WebP, saves it under
  `<M365_HOME>/chat-files/<session>/` and hands that path to the tool. New setting **attach_scope** ("Files that may be
  attached", human-only): `anywhere`, the Claude Code default, allows any local file except keys, tokens, `.env`,
  credential folders (`.ssh`, `.aws`, `.azure`, any `credentials`/`secrets` folder ...), the configured token files and
  the plugin's own folder; `folders` (the server default, so bots keep the old rule) allows only `attach_dirs`. Pasted
  images are allowed in both. Network, device and stream paths stay refused before any disk access.
- `email_add_attachment` is now confirm-gated: the hook shows the full path (or the pasted image's type and size) and the
  name recipients see, before anything is added.

### Changed
- **First-run setup no longer offers a bot's token.** `/m365:init` used to list "reuse a sign-in another tool holds"
  (a refresh token file and an app secret) as one of four equal choices, so an agent setting up a second computer asked a
  normal user for their bot's token. Setup now asks one question, "Do you have the client ID from your admin?", then signs
  the user in with the browser; another computer is set up the same way (same client ID, sign in again there). Agents are
  told never to ask for, mention or suggest a token, a token file, an app secret, or copying a sign-in. The bot-owner
  options (shared token file, one exact redirect, `scope_mode: app`) moved to an "Advanced" section used only when the user
  brings them up.
- A sign-in refused for an app setting (`PUBLIC_CLIENT_NOT_ENABLED`, `REDIRECT_URI_MISMATCH`) now leads to the admin message
  (`m365_access_request`), not to a token or secret workaround. The `PUBLIC_CLIENT_NOT_ENABLED` and
  `CREDENTIAL_SETTING_NOT_ALLOWED` hints say the same.
- README and APP_REGISTRATION mark token reuse as advanced, for bot owners only.

## [0.6.1] - 2026-11-07

### Security
- **`email_move` / `email_create_folder` fail closed.** If one of the forbidden folders (Deleted Items, Junk, Outbox, Drafts) could
  not be looked up, the check went on with an incomplete list; it now stops with `FOLDER_CHECK_FAILED` and moves nothing. A folder
  given by id is accepted only if its parents reach the visible folder root (`msgfolderroot`) within the depth limit without passing
  a forbidden folder; a failed parent lookup, a loop or running out of depth is a refusal (it used to count as "reached the top").
  Recoverable Items and other system folders sit outside that root, so they can never qualify; their names
  (`recoverableitemsroot`, `...deletions`, `...purges`, `...versions`) are also refused before any lookup. Verified live: every
  ordinary folder still resolves by id, the forbidden ones and Recoverable Items are refused.
- `teams_meeting_transcript` marks its topic and speaker names (outside the fenced transcript) as untrusted third-party data.

## [0.6.0] - 2026-11-06

The last Microsoft 365 gaps Teqo still used his old tools for.

### Added
- **Mail folders.** `email_list_folders` (the tree with id, path such as `Inbox/Projects/NAFLA`, counts). `email_move` now takes
  `inbox`, `archive`, a folder path (case-insensitive; folder names containing `/` resolve as listed) or a folder id. Unknown paths
  are refused and nothing is created implicitly. Deleted Items, Junk, Recoverable Items, Outbox and Drafts, and every folder inside
  them (checked by walking the path, or by climbing an id's parents), are refused, so deleting still goes through `email_delete`.
  `email_create_folder` (class write) creates a folder under a path, id or the top level.
- **Teams meetings** (module `meetings`, off by default; transcripts need `OnlineMeetingTranscript.Read.All`, admin consent):
  `teams_meeting_find` (calendar meetings by subject word or attendee, each with its meeting `chat_id` taken from the join link, so
  `teams_read_chat` reads the chat), `teams_meeting_transcript` (VTT turned into `[hh:mm:ss] Speaker: text`, paged on line
  boundaries, fenced; several transcripts selectable) and `teams_meeting_files` (files shared in the meeting chat, resolved through
  Graph `/shares` to drive and item ids for `onedrive_read_file` / `onedrive_save_file`). The online-meeting id is derived from the
  chat (organizer + thread), so `OnlineMeetings.Read` is not needed. A refused transcript is `ACCESS_NEEDED` naming who can help.
- **Saving files to this computer:** `email_save_attachment` and `onedrive_save_file` (class local) write a NEW file, under a
  cleaned name, into the one folder the person chose (`M365_DOWNLOAD_DIR`, plugin setting "Folder to save files into",
  `cli.mjs setup --download-dir`; never through a tool), up to 50 MB, and return its path, so a host can use files through the
  plugin's own sign-in.

## [0.5.2] - 2026-11-06

### Security
- **The preview's link list can no longer be fooled by a fake attribute inside another value.** In
  `<a title="x href=" href="https://evil">`, the whole-body scan used the fake `href=` and its match swallowed the real one,
  so the live link was not listed. The list is now the union of three scans: an attribute tokenizer that follows HTML's
  quoting rules (comments skipped), every URL-looking string anywhere in the body with entities decoded (`https:`, `javascript:`,
  `data:`, `mailto:`, `cid:`, `//host` ...), and the earlier whole-body scan. Over-reporting is harmless; missing a live link is not.

## [0.5.1] - 2026-11-06

### Security
- **`email_add_attachment` no longer touches the disk before the path is checked.** Resolving a path such as
  `\\host\share\x` makes Windows connect to that host and offer the user's login (an NTLM leak), and that happened before the
  allowed-folder check. The path text is now checked first: network, device and extended-length paths (`\\`, `//`, `\\?\`,
  `\\.\`), drive-relative forms and alternate data streams are refused, and the path must lie inside an allowed folder
  (case-insensitive on Windows). Only then is the real path resolved and checked again against the real folders (links).
- **The preview's link list scans the whole body again.** 0.5.0 counted attributes only inside what a regex took for tags; markup
  a mail client tokenizes differently (a stray quote in an unquoted value) could hide a link from the list. Listing an inert,
  escaped one is harmless; missing a live one is not.

## [0.5.0] - 2026-11-06

From Teqo's first trial notes (F-mw5gmowd, F-mw5gmwnw).

### Added
- **The profile fills itself from Outlook.** On the first tool call after sign-in (and with `profile_refresh_me`), name, email,
  id, language, **time zone and working days/hours come from Outlook's own settings** (`/me/mailboxSettings`), not from the
  computer and a Monday-Friday default. Windows zone names are converted to IANA (a built-in table, then Outlook's own zone list by
  city name). When Outlook's display zone and working-hours zone disagree, the one matching this computer wins and the result says
  so. Every value records its source; a value the user set with `profile_set` is never overwritten. Without the
  MailboxSettings permission it falls back to the computer's zone and says so. Status polls never trigger it.
- **`email_set_categories`** (set or clear a message's Outlook categories, reversible, no confirmation) and **`email_list_categories`**.
- **`email_add_attachment` / `email_remove_attachment`**: attach a local file to a draft, only from folders the **person** allowed
  (`M365_ATTACH_DIRS`, plugin setting "Folders files may be attached from", `cli.mjs setup --attach-dirs`; never through a tool).
  The file's real path is checked (links and `..` resolved), up to 25 MB, over 3 MB through an Outlook upload session (the upload URL
  must be Microsoft's Outlook host and gets no Graph token). The preview now lists every file and inline image, the digest covers
  them, and adding or removing one invalidates the preview.
- **HTML drafts with the user's signature, built by the plugin.** With `M365_SIGNATURE_FILE` (plugin setting "Email signature file",
  `cli.mjs setup --signature-file`, person only), new drafts, replies and forwards become HTML: the model's plain text is escaped
  (only `**bold**` becomes bold), the user's signature follows, and images next to the signature file are embedded inline. Replies
  and forwards keep Outlook's quoted original below. A signature with scripts, forms or event handlers is refused. The model can
  still never supply HTML. `signature: false` leaves it out.

### Fixed
- **Windows: atomic file replacement no longer fails while another process or a virus scanner has the file open**
  (EPERM/EACCES/EBUSY are retried briefly), and the shared-state lock treats Windows' EPERM on a lock being deleted as "held".
  Seen as a rare failure with Claude Code and a bot using the same `~/.m365-plugin`.
- The preview's link list counts attributes only inside real HTML tags (escaped text is inert), with a quote-aware tag match so a
  `>` inside a quoted value cannot hide a later link.

## [0.4.1] - 2026-11-06

### Added
- **A fixed sign-in redirect for apps that allow only one address** (first Teqo trial blocker, F-mw5fbnz8). Some apps, often a
  bot's confidential app with a secret, register exactly one redirect such as `http://localhost:8400/callback` and cannot be
  changed. `M365_REDIRECT_URI` (plugin setting "Sign-in redirect address", `settings.json` key `redirect_uri`,
  `cli.mjs setup --redirect-uri`) makes the browser sign-in listen on that port, accept only that path, and send exactly that
  `redirect_uri` in the authorize and token requests (with the secret from `M365_CLIENT_SECRET_FILE`). Only
  `http://localhost|127.0.0.1:<port 1024-65535>[/path]` is accepted. With it set, `auto` no longer falls back to a device code
  (which only fails with a misleading AADSTS7000218 for such apps); a port in use is `REDIRECT_PORT_BUSY`. Unset, nothing changes.
- `node server/cli.mjs sign-in --interactive`: browser only, and prints the address in case no browser opens.

### Fixed
- The `AADSTS7000218` hint no longer says only "allow public client flows": it explains that an app with a secret needs the browser
  flow with its registered redirect (`M365_REDIRECT_URI`). The `AADSTS50011` hint points to the same setting.
- An error Microsoft sends back to the redirect (for example consent needed) is classified like a token error, with its hint.

## [0.4.0] - 2026-11-06

Phase A of the review in `.claude/docs/2026-11-06_m365-plugin-review.md`: fixes and small additions, no new permissions.

### Fixed
- **Shared state is locked.** `staged.json` is used by every process on the computer (Claude Code and a bot such as OpenClaw share
  `~/.m365-plugin`). Every change now runs under a lock file, and "check the stage, then mark it sending/committing" is one locked
  step, so two processes can never both send the same Teams message, email or event, and one cannot overwrite the other's state.
- **Email send can no longer go out twice after a timeout.** Like Teams, a send is marked `sending` before the request. A definite
  refusal (400/401/403/404/405/422/429) makes the draft sendable again; anything else (a timeout, 5xx) is `SEND_UNCERTAIN` and points to
  Sent Items, and the draft is not sent a second time from here.
- **`onedrive_search` finds shared and SharePoint files.** It searched only the user's own OneDrive (`/root/search`) while promising
  shared files (live: `/me/drive/search` returned no shared items either). It now uses the Microsoft Search API (`/search/query`,
  `driveItem`, same `Files.Read.All` permission): each result says `location: own_onedrive | shared` and carries its owner's drive and
  item ids, so `onedrive_read_file` opens it (verified on a real tenant). If that search is refused, it falls back to the own OneDrive
  and says `search: onedrive_only`, so the model does not claim a file does not exist. KQL/OData syntax is stripped from the query.
- **`email_read_attachment` checks size and type before downloading.** A large or unreadable attachment is refused from its metadata,
  without pulling its bytes into memory.
- **`events_since` no longer drops events on a busy day.** A full calendar page now holds the cursor like a full mail page
  (`more: true`, invitations read oldest change first), and Teams chats are paged (up to 100) while they are still newer than the cursor,
  instead of only the 20 most recent.
- Config tests no longer read the real `~/.m365-plugin` of the person running them.

### Added
- `email_create_forward_draft`: forward a message as a draft (note on top, attachments kept), through the same preview and send gate.
- `email_list_recent` `unread_only`.
- `calendar_get_event` returns the event's description/agenda as fenced plain text.

### Changed
- `calendar_list_events`, `teams_list_chats` and `teams_find_chat` show at most 10 attendees/members per item, plus `attendees_total` /
  `members_total`; `calendar_get_event` and `teams_chat_members` still give the full list.

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
  visible, and is refused outright if an argument is too long to show in full. The "first setup only" lock is decided on the saved
  file as it is now (not what the process read at start-up), and every tool call reloads the settings if the file changed.
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
