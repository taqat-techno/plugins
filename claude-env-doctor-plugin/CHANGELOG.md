# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-31 — Initial release

### Added

- **env-doctor skill** — diagnoses Claude Code environment problems with a strict diagnose-don't-mutate discipline: it inspects, classifies, and explains, but never edits config, installs packages, or changes machine state on the user's behalf. Includes a symptom router that maps an observed failure to the correct reference doc, and a standard report template (Symptom → Probes run → Findings → Recommended fix → Verification step) so every diagnosis is reproducible and evidence-backed.
- **6 reference docs** — focused troubleshooting guides loaded on demand by the symptom router:
  - `mcp-not-loading` — MCP servers that fail to start, register, or appear in the tool list.
  - `windows-wsl` — Windows and WSL interop friction (path translation, line endings, shell selection).
  - `login-auth` — login, token, and authentication failures.
  - `lsp-node-spawn` — language-server and Node process-spawn errors.
  - `python-encoding` — Python encoding and locale issues (UTF-8, code-page mismatches).
  - `playwright-browser` — Playwright and browser-driver launch and download problems.
- **/env-doctor command** — runs with a sensible no-argument default (full read-only environment sweep); flags are optional shortcuts that narrow the scope, never required.
- **env-probe-reporter agent** — a read-only subagent that gathers environment signals and reports findings. It has no write or mutate capability and never prints secrets, tokens, or environment-variable values.
- **SessionStart advisory hook** — non-blocking advisory that surfaces a brief environment hint at session start. It never blocks, delays, or fails the session; it only advises.

### Validation

- `python validate_plugin.py claude-env-doctor-plugin` -> 0 errors.
- Genericness sweep: no company, client, or project names; no business-domain terms; no absolute user paths, production/staging URLs, private repo names, or credentials. Any concrete example is clearly labeled illustrative and is not required for plugin behavior. No secrets, tokens, or environment values are printed anywhere.
