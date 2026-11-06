# Changelog

## [0.1.0] - 2026-11-06

First release (phase 1: read-only). Self-contained: no npm packages, no system variables, no admin rights.

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
- Least-privilege scopes: only the modules enabled are requested; phase 1 asks for read permissions only.
- `data/tools.json` classifies every tool as read, local or write (checked by tests); `docs/APP_REGISTRATION.md`
  is the one-time admin setup.
- Tests: 34 offline Node tests against a fake Microsoft, plus Python checks (stdio smoke test, no dependencies,
  nothing personal baked in, manifest and MCP config in step).

### Not yet (planned)
- Write tools (draft, send, calendar, Teams) with confirmation hooks and a read-only proxy; attachment contents;
  OneDrive; the OpenClaw package build; an events poller.
