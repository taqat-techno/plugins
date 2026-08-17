# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Resolved a name collision: `commands/env-doctor.md` and `skills/env-doctor/SKILL.md` both resolved to `claude-env-doctor:env-doctor`, so one shadowed the other even though the command explicitly delegates to the skill. The skill is now `env-doctor-router` and the command's delegation target was updated; the `/env-doctor` entry point is unchanged. Also fixed `user_invocable` -> `user-invocable` on 2 skills.

## [Unreleased]

### Changed

- **`windows-wsl`** — the WSL2 sshd section now covers all three reasons sshd does not listen where expected: socket activation makes **both** `Port` and `ListenAddress` in `sshd_config` inert (and recent distributions ship openssh-server socket-activated by default, so it is the expected starting state), the fix is to disable **and stop** `ssh.socket` before enabling `ssh.service` and to verify with `ss -tlnp` rather than with the config file, and a fresh install fails `sshd -t` with "Missing privilege separation directory: /run/sshd" because systemd's `RuntimeDirectory=sshd` only creates it at first service start — a valid config that only appears to be rejected. Added a new section on background/pin processes that "won't die": `pkill` silently skips processes owned by another user (root-owned pins survive a user-run kill and the exit code says nothing), and `pgrep -f <pattern>` self-matches the measuring shell — enumerate with `ps -eo pid,user,args`, count with `pgrep -xa`, and never widen or escalate a pattern-based kill. Summary table extended with the four new rows.
- **env-doctor skill** — gotchas table gained the two capability-registration mechanics: only a directory `.claude/skills/<name>/SKILL.md` registers (a loose `.md` in the skills directory never does, so nothing can invoke it), and a `description` is advisory — deterministic firing comes from a hook (`SessionStart` / `Stop`), so validate that a capability actually registered before diagnosing its behavior. Router trigger signs, when-to-use list, anti-patterns table (kill-reported-success, config-vs-live-listener, assumed registration), and the `windows-wsl` cross-reference extended to match. No version bump — content additions only.

## [0.4.0] — 2026-07-23 — Syncthing, Windows-shell, and rendering branches

Supersedes the unreleased 0.3.0 skill review bump; plugin and skill versions are realigned at 0.4.0.

### Added

- **3 new reference docs**, wired into the env-doctor symptom router:
  - `syncthing` (EN-1) — Syncthing dev-folder sync operations: resolve conflicts by diff→dated-backup or receive-only+revert (there is no per-conflict "prefer remote" toggle); the venv/`node_modules` directory-delete deadlock is broken with a `(?d)`-prefixed ignore, not a hand-delete; `.stignore` does **not** sync (apply on every peer); a folder's error list is cached until a pull (pause/resume, not a rescan); an encryption-type mismatch on one shared folder drops the whole device link; "95% synced, 0 bytes pending" is a pending deletion, not a stall. Diagnosis is read-only via the REST API (`/rest/db/status`, `/rest/db/file`).
  - `windows-powershell` (EN-2) — Windows shell & native-exe argument traps: PowerShell 5.1 strips embedded double-quotes to a native exe and stdin-pipes prepend a UTF-8 BOM; `Copy-Item -Recurse -Exclude` does not filter directories; `kubectl exec -- <interp> -c` mangles payloads and `port-forward` races startup (poll TCP-listen, don't fixed-sleep); piping a running server / long test into `head`/`tail` SIGPIPE-kills or buffers it and the pipe's exit 0 masks the real status; `node C:\path` and `git <rev>:<path>` break under Git-Bash path conversion; `manage.py test --parallel` pickles on Windows (run serially).
  - `ide-mermaid-rendering` (EN-5) — an IDE/editor may simply lack a Mermaid **renderer**: JetBrains renders Mermaid only via a Marketplace plugin (not a Markdown-settings checkbox), VS Code preview needs an extension, GitHub/GitLab render natively; jsdom cannot lay out SVG (`getBBox`) — rasterize with headless Chrome, not jsdom. Cross-references docs-wiki `wiki-mermaid` for authoring.

### Changed

- **`windows-wsl`** — added (EN-3) Windows git "dubious ownership" = the repo dir is owned by `BUILTIN\Administrators`; prefer the scoped, non-mutating `git -c safe.directory=<dir> …` over the global `--add safe.directory` write. Added (EN-4) session-0 (`LocalSystem`) service pitfalls — `\\wsl.localhost` 9P shares appear empty and the WSL2 VM idle-stops ~30s unless pinned; WSL2 sshd socket-activation ignores `Port` and a Windows-side listener blocks the Linux bind (`EADDRINUSE`); the `/mnt/c` root is read-only and the Windows Desktop may be OneDrive-redirected.
- **`playwright-browser`** — named the Playwright-MCP `--isolated` flag as the way to sidestep the persistent-profile singleton-lock class entirely (EN-6).
- **env-doctor skill** — router table, gotchas table (added: `.claude/settings.json` is strict JSON not JSONC so a trailing comma breaks it; an auto-invoked capability is a directory `SKILL.md` + hooks, not a slash command — EN-6), when-to-use list, `owns`/`defers_to`, and cross-references extended to the three new branches; `version` bumped to 0.4.0 and `last_reviewed` to 2026-07-23.
- **README** — reference-doc list updated to the actual eleven filenames.

### Validation

- `python validate_plugin.py claude-env-doctor-plugin` -> 0 errors.
- Genericness sweep: no company, client, product, repo, host, URL, credential, or machine-specific identifier; all concrete folder IDs, ports, and paths are generic placeholders or clearly labeled illustrative. No secrets, tokens, or environment values printed anywhere; the REST API key is read for the probe but never echoed. The diagnose-don't-mutate discipline is preserved in every new section (mutating steps are gated behind a confirmed diagnosis and left for the user to apply).

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
