# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-06-13 — Expanded diagnostic coverage

### Added

- **2 new reference docs**, wired into the env-doctor symptom router:
  - `ide-remote-dev` — a JetBrains-style remote-dev "Connecting" hang or mid-session "No connection" is usually a backend JVM heap OOM, not networking. Read the backend log; raise `-Xmx`, exclude generated/i18n trees from the index, and add `-XX:+ExitOnOutOfMemoryError` so a dead backend fails fast instead of keeping ports open and re-attaching the client to a wedged process.
  - `doctor-command-ambiguity` — disambiguates the literal `/doctor` (a React-doctor-style skill) from Claude Code health; use the read-only CLI `mcp list` / `--version` checks, never the interactive doctor TUI that hangs in a non-interactive shell; managed cloud connectors authorize only via the interactive MCP menu; plus permissions-allowlist hygiene (exclude auto-allowed basics, never wildcard a shell/interpreter).

### Changed

- **`windows-wsl`** — added: Git-Bash `/tmp` maps to the Windows LocalAppData temp dir (write artifacts to an explicit path); confirm an empty content-search with a direct Read on an absolute path; mirrored-mode + a persisted IDE port-forward creates a squat/feedback loop (clear the forward); mirrored-mode DNS can hang when a VPN mesh's DNS overlaps; nat-mode idle-stops the VM.
- **`mcp-not-loading`** — added: user MCP servers live in the user-level Claude JSON config (not a separate `mcp.json`); concurrent Claude Code instances race-write that file and drop each other's `mcpServers`; a plugin MCP `-32000` almost always means its spawned CLI is not runnable — read the configured command and run it manually.
- **`login-auth`** — added: pin `forceLoginMethod` to the org billing type to break a 401 loop; env vars in `settings.json` can silently override OAuth login; one Claude Code process is single-tenant, so mixing providers needs an external routing proxy.
- **`lsp-node-spawn`** — added a Windows-specific section: LSP plugins cannot launch npm `.cmd`-shim language servers under `shell: false`; point the command at `node` + the package JS entrypoint.
- **`python-encoding`** — added a Windows non-ASCII/emoji diagnosis quick-path reinforcing `PYTHONIOENCODING=utf-8` plus the in-script stream reconfigure.
- **env-doctor skill** — router table, cross-references, and when-to-use list extended to the two new branches; `version` bumped to 0.2.0 and `last_reviewed` to 2026-06-13.
- **README** — corrected the reference-doc list to the actual eight filenames.

### Validation

- `python validate_plugin.py claude-env-doctor-plugin` -> 0 errors.
- Genericness sweep: no company, client, product, repo, host, URL, credential, or machine-specific identifier. All concrete commands/paths are generic or clearly labeled illustrative. No secrets, tokens, or environment values printed anywhere; the diagnose-don't-mutate discipline is preserved in every new section.

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
