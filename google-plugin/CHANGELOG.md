# Changelog

## [0.5.4] - 2026-11-26

### Changed (security review)
- `drive_create_file` and `drive_copy_file` move from `write` to `confirm`: creating into a shared folder, or
  copying (Google puts a copy in the original's folder when no parentId is given), shows content to other people,
  the same reason `drive_upload_file_revision` is confirm. The Claude Code hook now asks before both; their
  descriptions say "Ask the human first" and where the file lands. write is now 11 tools, confirm 13.

## [0.5.3] - 2026-11-26

### Added
- `grant --fresh`: Google's "Always allow for this email / owner" answers mean the first item is often allowed already,
  so Google stops asking there. With --fresh the list tools (`gmail_search_threads`, `drive_list_recent_files`) read a
  page of 25, and the per-item tools (`gmail_get_thread`, `gmail_get_message`, `drive_get_file_metadata`,
  `drive_get_file_permissions`, `drive_read_file_content`) try those items one by one until Google asks. Nothing read
  is printed. If Google asks about none, the run says so.
- Google's form, when it offers "Always allow this tool", is preceded by a plain note: which option number that is,
  that it covers every item for the tool (the other "Always" option only this one), and that Google keeps it 90 days
  with no way for the user to revoke it.

## [0.5.2] - 2026-11-26

### Fixed
- `GOOGLE_TOOLS_DENY` now removes every named tool, the plugin's own sign-in tools included (`google_sign_in`,
  `google_sign_out`, `google_auth_status`): they are absent from tools/list and a call is refused with
  `UNKNOWN_TOOL`. `GOOGLE_TOOLS_ALLOW` still narrows only the module tools, so the sign-in tools stay unless denied.

## [0.5.1] - 2026-11-26

### Fixed (from the first live `grant` run)
- Google refused `drive_download_file_content` with "requires user confirmation, which this client does not support"
  instead of sending a form, although the plugin declares form support. That error is now
  `CONFIRMATION_UNSUPPORTED` (hint: `grant` does not help; use `drive_read_file_content`) instead of a generic
  `TOOL_ERROR`.
- `grant`: Ctrl+C at a prompt now stops the run instead of moving on to the next tool.

## [0.5.0] - 2026-11-26

### Added
- Milestone B4: `scripts/build_agent_plugin.py --out <dir>` builds a host-neutral Agent Plugins package (plugin.json,
  mcp.json, one bot-facing skill from `data/agent_skill.md`, `data/tools.json`, `data/google_mcp_snapshot.json`, the
  setup guide and `server/**/*.mjs`). Backups and non-`.mjs` files are never copied; the Claude Code hook is not in it
  (the host gates the `confirm` class itself). It does not force read-only mode, which would need a new sign-in.
- `data/agent_skill.md`: the bot-facing skill (untrusted content, `CONFIRMATION_NEEDED` → owner runs `grant`, which
  tool for what, write vs confirm, no sending).
- Setup guide: enable the Gmail, Calendar and Drive **MCP** APIs too, tick "Use this client for an AI-powered agent",
  answer Google's confirmations with `grant`, and what Google documents about them: saved approvals expire after
  90 days, and users can't view or revoke them (only Workspace admin controls exist). Optional identities file.

## [0.4.0] - 2026-11-26

### Added
- Milestone B3: Google's 24 write tools are classified; none is hidden any more.
  - write (13): `gmail_create_draft`, `gmail_create_label`, `gmail_label_thread`, `gmail_unlabel_thread`,
    `gmail_label_message`, `gmail_unlabel_message`, `gmail_update_message_labels`, `gmail_untrash_thread`,
    `gmail_untrash_message`, `gmail_unmark_thread_spam`, `gmail_unmark_message_spam`, `drive_create_file`,
    `drive_copy_file`.
  - confirm (11): `calendar_create_event`, `calendar_update_event`, `calendar_delete_event`,
    `calendar_respond_to_event` (whole tools: each can email other people), `gmail_trash_thread`,
    `gmail_trash_message`, `gmail_apply_sensitive_thread_label`, `gmail_apply_sensitive_message_label`,
    `gmail_mark_thread_spam`, `gmail_mark_message_spam`, `drive_upload_file_revision`.
- `hooks/hooks.json`: a Claude Code PreToolUse "ask" on every confirm-class tool. It is a fixed printf (no script, so
  nothing can fail open); a test keeps the matcher in step with `data/tools.json`.
- Write-class label tools refuse to add `TRASH` or `SPAM` (`NEEDS_CONFIRM_TOOL`), so the confirm-class tools cannot be
  bypassed through a plain label call.
- Rewritten descriptions for the confirm tools (each says who is emailed and the `notificationLevel` default) and for
  `drive_create_file` (Google's was over 1,024 characters).
- CLI `identity <messageId>`: runs `gmail_message_identity` from the human's terminal, with Google's form shown there.

### Not added (Google's servers do not offer them; no REST fallback, by decision)
- Sending mail, editing or deleting drafts, Drive share / move / trash, permanent delete of anything.
- No HTML conversion for drafts: Google's `create_draft` takes `htmlBody` itself.

## [0.3.0] - 2026-11-26

### Added
- Milestone B2: `gmail_message_identity` (read): which configured identity a message was sent to, decided from its
  headers. It reads the message RAW through Google (same confirmation handling as the bridged tools) and parses the
  headers locally. It returns only identity, `matched_by`, `matched_address` and From/To/Cc/Date/Subject/X-Forwarded-For,
  never the body. Match order: X-Forwarded-For (each address, in order), then To, then Cc, then the default identity.
  Delivered-To is never used. RFC 2047 encoded words are decoded.
- `gmail_identities` (local): lists the configured identities.
- Configuration: `GOOGLE_IDENTITIES_FILE` (userConfig "Identities file") or `GOOGLE_IDENTITIES` (inline JSON):
  `{ "identities": [ { id, label, address, matchTo: [address | "@domain"], default } ] }`. A bad configuration is
  `CONFIG_INVALID`, reported before Google is called.
- `data/tools.json` gains `plugin_tools` (tools the plugin implements itself, not looked up in the snapshot).
- New error codes: `CONFIG_INVALID`, `HEADERS_TOO_LARGE`, `INVALID_ARGUMENT`.

### Not added
- An `identity` filter on `gmail_search_threads`: Gmail's `to:`/`cc:` search cannot see a Bcc'd alias, so the filter
  would silently miss mail; use `gmail_message_identity` per message instead.

## [0.2.0] - 2026-11-26

### Added
- Milestone B1: the plugin is now a local bridge to Google's own Workspace MCP servers
  (`gmailmcp` / `calendarmcp` / `drivemcp` `.googleapis.com/mcp/v1`, MCP protocol 2026-07-28, stateless), signed in with
  the milestone-1 sign-in (scopes unchanged).
- 17 read tools re-exposed as `gmail_*`, `calendar_*`, `drive_*`. What is exposed comes from `data/tools.json`
  (classes, description rewrites) and `data/google_mcp_snapshot.json` (Google's recorded tool list), never from the
  live list, so a tool Google adds or changes never appears silently. Google's write tools are listed as `hidden` until
  milestone B3.
- Google's confirmation forms are never answered by the plugin: they are forwarded as `elicitation/create` to an MCP
  client that declared form support, or the call fails with `CONFIRMATION_NEEDED` (text only). `GOOGLE_CONFIRM_MODE=error`
  never forwards.
- CLI `grant [tool ...]`: the human answers Google's forms in their own terminal, once per read tool, on harmless test
  calls; it prints only whether Google asked and what was chosen.
- CLI `schema-check [--update]`: Google's live tool list compared with the snapshot.
- Results are marked `untrusted: true` and size-capped (`GOOGLE_MAX_STRING_CHARS`, `GOOGLE_MAX_RESULT_CHARS`);
  non-text blocks are described, not passed on.
- Settings `GOOGLE_TOOLS_ALLOW` / `GOOGLE_TOOLS_DENY`, `GOOGLE_CONFIRM_MODE`, `GOOGLE_CONFIRM_TIMEOUT_MS`.
- New error codes: `CONFIRMATION_NEEDED`, `CONFIRMATION_NOT_ANSWERED`, `INVALID_CONFIRMATION_ANSWER`,
  `UNSUPPORTED_CONFIRMATION`, `CONFIRMATION_LOOP`, `GOOGLE_FORBIDDEN`, `RATE_LIMITED`, `GOOGLE_UNAVAILABLE`,
  `GOOGLE_ERROR`, `TOOL_ERROR`, `UNKNOWN_TOOL`.

## [0.1.0] - 2026-11-25

### Added
- Milestone 1: one Google sign-in for the enabled modules `gmail`, `calendar` and `drive`, each switchable by config
  (`GOOGLE_MODULES`). It is a Desktop app OAuth client on a `127.0.0.1` loopback with PKCE S256, using the user's own
  client JSON (`GOOGLE_CLIENT_SECRET_FILE`).
- `google_sign_in`, `google_auth_status` and `google_sign_out` (class `local`), and the CLI commands `sign-in`,
  `status [--offline]` and `sign-out`.
- Scopes, all requested at the first sign-in together with `openid email`:
  - gmail: `gmail.modify`;
  - calendar: `calendar.events` + `calendar.calendarlist.readonly`;
  - drive: `drive`;
  - read-only mode swaps in `gmail.readonly`, `calendar.events.readonly` and `drive.readonly`.
- `https://mail.google.com/` is refused by construction, and a test covers every module and mode combination.
- Per-module usability is worked out from the granted scopes, because Google lets the user untick individual
  permissions.
- `google_auth_status` refreshes the token live by default. It reports the account, the usable modules, requested vs
  granted vs missing scopes, the token age and the last refresh time. It never returns a token.
- Atomic token cache with write-back of a rotated refresh token.
- Distinct `AUTH_REQUIRED` and `AUTH_EXPIRED` errors. Error results contain text only:
  `{ ok:false, error:{ code, message } }`.
- `docs/GOOGLE_CLOUD_SETUP.md` for non-developers, covering:
  - turning on the Gmail, Calendar and Drive APIs;
  - each scope's class as Google's scope pages state it, with links (Calendar marked unverified: its page gives none);
  - Google's documented 7-day refresh-token rule for External apps in Testing.
- Offline test suite with a fake Google HTTP layer.
