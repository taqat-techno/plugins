# Changelog

## [0.7.1] - 2026-11-26

### Added
- `gmail_rest_save_draft_html` embeds the remote images of the From address's own Gmail signature (for example a
  logo), so the snapshot shows what recipients will see. Only URLs found in that address's signature in Gmail settings
  are fetched, and only where they appear inside the plugin's signature block; a URL that exists only in the draft is
  never fetched, so draft content cannot steer the plugin to a host. Each fetch: https only; the host must resolve only
  to public addresses (loopback, private, link-local, CGNAT and multicast refused, literal IPs too); no redirects; no
  credentials; 5 s timeout; image/* other than SVG; 1 MB per image, 3 MB per snapshot. Every other remote image stays
  blocked by the snapshot's content policy. The result adds `signature_images_inlined` (count) and
  `signature_images_failed` ([{host, reason}]).

## [0.7.0] - 2026-11-26

### Added
- Per-address Gmail signatures on REST drafts. `includeSignature` (default true) on `gmail_rest_create_draft` (new),
  `gmail_rest_create_reply_draft`, `gmail_rest_create_forward_draft` and `gmail_rest_update_draft` adds the From
  address's own signature from Gmail settings (`users.settings.sendAs[].signature`, already read for the send-as check;
  no new scope). It goes into the HTML version (wrapped in `<!--gp-signature-start-->` ... `<div class="gmail_signature">`
  ... `<!--gp-signature-end-->`) and, as text after "-- ", into the text version; above the quoted history for forwards.
  A text-only body gets an HTML version so the signature's links and formatting survive. Results report
  `signature_added` and `signature_from`. An address without a signature gets none (`signature_added: false`).
  `gmail_rest_update_draft` re-applies it when the body is replaced or From changes, replacing the old one in place
  (never doubled), and leaves it alone otherwise (`signature_added: null`).
- `gmail_rest_create_draft` (write, REST): a new draft from a chosen verified send-as address.
- `gmail_rest_save_draft_html` (read, REST): saves one self-contained .html file of a draft into
  `GOOGLE_DOWNLOAD_DIR` (never overwriting): a header block (From, To, Cc, Bcc, Subject, "DRAFT, not sent") above the
  draft's HTML body as it will be sent, cid: images inlined as data: URIs, or the escaped text in <pre>. Scripts,
  embeds, event attributes, javascript: links and refresh tags are removed, and a Content-Security-Policy blocks every
  network request (remote images do not load) wherever the file is opened. Returns path and the same digest
  `gmail_rest_preview_draft` / `gmail_rest_send_draft` use, so a picture of it is bound to what is sent.

### Not verified
- Which signature Google's own `gmail_create_draft` (`includeSignature`) uses: its description says "the user's
  configured Gmail web signature" and it takes no From.

## [0.6.3] - 2026-11-26

### Fixed (from the first live test)
- `gmail_rest_update_draft` with only `body` wiped To, Subject and the rest. Fields not given now keep their current
  values: to, cc, bcc, subject, From, In-Reply-To / References, the thread and the attachments. The body is one unit:
  body and/or htmlBody replace both versions; neither keeps both. to / cc / bcc replace that list ([] clears it).
- Google asks the human before `calendar_delete_event` even for the user's own event without guests, and `grant`
  covered read tools only. `grant <write tool> --target <id> [--calendar <id>]` now runs ONE write on an item the human
  names, after saying exactly what it does and getting a typed "yes", and shows Google's form for it. Tools:
  `calendar_delete_event` (notificationLevel NONE), `gmail_trash_message`, `gmail_trash_thread`,
  `gmail_mark_message_spam`, `gmail_mark_thread_spam`. The CONFIRMATION_NEEDED hint points to it for those tools and
  says plainly when grant cannot help.
- `grant` cancels after 5 answers that are not one of the form's choices, instead of asking forever.

## [0.6.2] - 2026-11-26

### Fixed (security review of 0.6.1)
- What is sent is now exactly what was checked: `gmail_rest_send_draft` sends the raw bytes it just verified against the
  preview digest as a new message in the draft's thread (Gmail `messages.send`, covered by gmail.modify), then
  deletes the draft (`draft_deleted` reports it). Before, it checked the draft and then asked Gmail to send the draft by
  id, leaving a window for a change.
- The preview shows everything that decides delivery and content: every value of From, Sender, Reply-To, To, Cc, Bcc and
  Subject, the plain-text body and the HTML body as text (each up to 20,000 characters), and
  `text_and_html_differ` when they do not match. It reports `sendable` and `blockers`.
- A draft the preview cannot show in full is refused at send: repeated address or subject headers
  (`MULTIPLE_HEADERS`), or a body over 20,000 characters or more than one text or HTML part (`PREVIEW_INCOMPLETE`).

## [0.6.1] - 2026-11-26

### Fixed (security review)
- `gmail_rest_send_draft` took only a draft id, so the approval prompt showed no content and the draft could change
  between the human's look and the send. New `gmail_rest_preview_draft` (read, REST) returns From, To, Cc, Bcc,
  subject, body, attachments, whether From is a verified send-as, and a digest of the raw draft; the send now requires
  that digest and refuses with `DRAFT_CHANGED` (nothing sent) if the draft differs. The draft is read and checked
  immediately before the send; a change in the instant between that check and Google's send is not covered.

## [0.6.0] - 2026-11-26

### Added
- `gmail_get_attachment` (read): lists a message's attachments, or saves one (by index or filename) into
  `GOOGLE_DOWNLOAD_DIR` and returns path, filename, mimeType and size; never the bytes. The message is read RAW
  through Google's MCP and parsed locally (nested multipart, base64 / quoted-printable, RFC 2231 / 2047 names).
- `drive_save_file` (read): Google's `download_file_content`, decoded and saved the same way. It replaces exposing
  `drive_download_file_content` (now hidden), whose base64 result the size cap would cut.
- Guest guard, off by default (`GOOGLE_REFUSE_GUEST_EVENTS=1`): calendar create/update naming attendees other than the
  signed-in person, and update/delete/respond on an event that has other attendees or another organiser (looked up
  first; a failed lookup refuses), fail with `GUESTS_NEED_APPROVAL` before Google is called.
- Write limit, off by default (`GOOGLE_WRITE_LIMIT_PER_HOUR=N`): trash / spam / sensitive-label / calendar delete /
  draft delete / Drive trash and move calls past N per rolling hour in one process fail with `WRITE_LIMIT_REACHED`.
- REST fallback, off by default (`GOOGLE_REST_FALLBACK=1`), for what Google's MCP servers lack; same sign-in, no new
  scope (gmail.modify and drive cover every call). Tools are named `*_rest_*` so they cannot collide with a Google
  tool, are absent from tools/list and refused when the switch is off, and are dropped in read-only mode:
  - confirm: `gmail_rest_send_draft` (sends an existing draft by id only; its From must be a verified send-as, else
    `IDENTITY_NOT_VERIFIED`), `drive_rest_trash_file`, `drive_rest_move_file`, `drive_rest_share_file` (a person or
    group, reader / commenter / writer only), `drive_rest_unshare_file` (never the owner);
  - write: `gmail_rest_update_draft`, `gmail_rest_delete_draft`, `gmail_rest_create_reply_draft` (in-thread, chosen
    or matching verified From), `gmail_rest_create_forward_draft` (with the original attachments, 25 MB max),
    `drive_rest_untrash_file`, `drive_rest_rename_file`.
- `schema-check` exits 4 when Google adds, removes or changes a tool (3 now means only that the check failed), with
  `drift` and per-module `may_replace_rest` hints in the JSON.
- Settings `GOOGLE_DOWNLOAD_DIR` (userConfig "Folder to save files into"), `GOOGLE_MAX_SAVE_MB` (default 25).
- New codes: `DOWNLOAD_NOT_CONFIGURED`, `TOO_LARGE`, `AMBIGUOUS`, `NOT_FOUND`, `MESSAGE_TOO_COMPLEX`,
  `GUESTS_NEED_APPROVAL`, `WRITE_LIMIT_REACHED`, `IDENTITY_NOT_VERIFIED`, `REST_DISABLED`.

### Found (A1)
- `download_file_content` works for files the signed-in person owns. For files owned by other people Google answers
  "requires user confirmation, which this client does not support" without offering a form, whether the client declares
  form or form+url elicitation, so neither the plugin nor `grant` can answer it (live check 2026-11-26).

## [0.5.5] - 2026-11-26

### Fixed (security review)
- Address parsing in `gmail_message_identity` ran an unanchored regex over sender-controlled header values (up to
  256 KB), which took quadratic time: about 2 s for 64 KB, about 30 s for 256 KB. Each header value is now cut to
  8 KB, split on separators, and each token checked with an anchored pattern: a 256 KB hostile header now parses in
  about 1 ms. A regression test covers it.

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
