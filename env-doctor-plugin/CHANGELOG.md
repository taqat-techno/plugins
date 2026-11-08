# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.3] - 2026-11-08

### Fixed
- `dev-env-cleanup/scripts/apply_files.sh` runs on macOS bash 3.2: no `mapfile`, and an empty array no longer trips `set -u`. Test fixture home renamed to a placeholder user.

## [0.9.2] - 2026-11-08

### Changed
- The 1 deprecated alias command now set `disable-model-invocation: true`. Typing the old name still works and still points to the new command, but Claude no longer sees these stubs in its skill listing, which leaves more of the shared listing budget for the descriptions of live skills and commands.

## [0.9.1] - 2026-11-06

**Security fix: the cleanup plan id did not cover the fields the apply step uses.** Found by an
automated security review of 0.9.0; nothing was applied.

### Security
- The plan id is now a hash of every field of every item (it covered only kind, target, size,
  reason, action and backup), so editing `db`, `port`, `conn`, `filestore`, `dest`,
  `depends_on`, `source` or `command` after approval is refused.
- `emit` refuses a database item whose `db@port` does not match the target shown in the plan.

### Tests
- `tests/test_cleanup_plan.py`: edits to each hidden apply field are refused; a db/target
  mismatch is refused even with a recomputed id.

## [0.9.0] - 2026-11-06

Three new capabilities for WSL-based development, from measured pain on a real machine: services
that are slow because code is read through `/mnt/c`, disks filled by forgotten databases and a WSL
image that never shrinks, and sessions blocked for 20-40 minutes on test runs.

**Identity change:** env-doctor's *diagnosis* stays read-only. Deleting lives in one separate skill,
`dev-env-cleanup`, behind its own inventory -> keep-list -> plan -> approved-plan-id gate.

### Added
- **WSL / local-service performance branch** (`env-doctor-router` -> `references/wsl-performance.md`).
  New router row and an eighth failure class, *performance / resource pressure*. Two read-only probe
  scripts print measured `PROBE <name>: <value> -> <verdict>` lines: `scripts/wsl_perf_probe.sh`
  (inside the distro: code location, ms per file on `/mnt/c` vs ext4, memory/OOM, CPU and test-process
  count, root filesystem) and `scripts/windows_perf_probe.ps1` (system drive, pagefile, commit,
  Defender / Defender for Endpoint and whether exclusions are readable, Windows-native ms per file,
  WSL version, `.wslconfig` keys and their section). Fix ladder: ext4 git mirror of read-only trees
  with a stale-mirror-safe selector, Defender exclusion request text for IT, memory/CPU caps,
  pagefile, `wsl --update`. `PoolError` is explained as a consequence of slow requests.
- **`dev-env-cleanup` skill + `/env-doctor:clean` command.** No arguments: a read-only inventory and
  a plan; nothing is deleted. `scripts/inventory.sh` (Postgres clusters and every database with size,
  connections and last activity; confs, data dirs, filestores, `~/tmp`, caches, logs, journal, Docker,
  running servers, tool state files, keep file; never prints a password), `scripts/host_probe.py`
  (Windows: drive free, `ext4.vhdx` per distro, WSL version; does not start WSL), `scripts/plan.py`
  (keep-list: open connections, canonical conf databases and their `dbfilter`, running servers,
  activity < 7 days, tool state files, `~/.config/env-doctor/keep.txt`; orphan detection only when
  every cluster was listed; content-hash plan id; `emit` refuses another id, an edited plan or one
  older than 24 h), `scripts/apply_files.sh` and `scripts/apply_dbs.sh` (`dry|run`; path allow-list,
  empty/relative/`..`/glob/prefix-root refusal, symlink-escape check, live `data_dir` protection,
  `rm -rf -- "${p:?}"`; `DROP DATABASE` without FORCE after a re-check for connections, name passed
  as a psql variable, `pg_dump -Fc` + TOC verification + filestore tarball first; confs archived,
  never deleted; every action logged), `scripts/idle_gate.sh` (IDLE / BUSY with reasons) and
  `scripts/compact-wsl.ps1` (dry by default; run mode is elevated and user-run: idle gate twice,
  no other `wsl.exe` clients, `wsl --shutdown`, wait for `vmmem`, diskpart readonly attach + compact;
  never `--set-sparse`). Merges the odoo plugin's `odoo-local` `local_cleanup_plan` output when that
  tool is present (its published contract: `<distro>:<port>/<db>` targets, `scratch_db` /
  `orphan_filestore` / `dead_conf` / `stale_log`, `{"plans": [...]}`); env-doctor's keep-list wins.
- **`long-running-jobs` skill** — the 3-minute rule (longer jobs go to the background while work
  continues; act on the completion notification), durable launches inside WSL (`systemd-run --user`,
  not `nohup`/`setsid` under `wsl --`), waiting without polling or `pgrep -f`, wrapper vs job exit
  codes, concurrency and CPU/memory caps.
- **PreToolUse advisory hook** `hooks/long_job_advisory.py` on `Bash|PowerShell`: when a command is
  a long-job shape (`--test-enable`/`--test-tags` wider than one method, `-i`/`-u --stop-after-init`,
  whole-tree `pytest`, label-less `manage.py test`, `test:e2e`, full `playwright test`,
  `pg_dump`/`pg_restore`, including inside `wsl ... bash -lc "..."`) and would run in the foreground
  (no `run_in_background`, timeout above 180000 ms or none), it adds a reminder. Also flags foreground
  `while/until … sleep` loops and `pgrep -f`/`pkill -f`. Never blocks (exit 0, `additionalContext`
  only). UTF-8 stdin. Off with `ENV_DOCTOR_LONG_JOBS=off` or the new `long_job_advice` option.
- **SessionStart host-pressure checks** (`hooks/host_pressure.py`, Windows only, ~0.2 s): system drive
  under 10% free, a *running* distro's `ext4.vhdx` over 1.5x its used space and 10 GiB larger, and a
  WSL version with a known crash (2.6.3). Never starts the VM: the image check runs only for distros
  `wsl --list --running` reports. Off with `ENV_DOCTOR_HOST_CHECKS=off`.
- `references/windows-wsl.md`: WSL restart protocol (user decides, other sessions told, idle gate
  twice, no attached clients, snapshot/relaunch servers), `Wsl/0x8007000e` = memory pressure (drive ->
  pagefile -> commit chain), WSL version / `wsl --update` semantics, VM stop after the last client.
- `env-probe-reporter`: performance and disk-pressure probes in its sweep (WSL probe only when the
  distro is already running, or when asked).
- Evals: `fires-on-odoo-slow-in-wsl` (router), `fires-on-wsl-disk-full-cleanup`
  (`dev-env-cleanup`), `fires-on-long-test-suite-blocking` (`long-running-jobs`), and
  `ignores-slow-sql-query-tuning`, `ignores-git-clean-flags-question`, `ignores-write-small-unit-test`.
- Tests: `test_long_job_advisory.py` (matcher shapes, timeouts, background, UTF-8, opt-outs),
  `test_cleanup_plan.py` (every keep rule, orphan brake, odoo-local merge incl. the published
  shape, plan-id tamper/age, emit), `test_cleanup_scripts.py` (apply_files guards on a throwaway HOME;
  opt-in integration that creates, dumps and drops an `envdoc_test_*` database), host-check cases
  in `test_session_start_env_advisory.py`.

### Changed
- `env-doctor-router` 0.5.0: description names the slow-WSL / PoolError / `0x8007000e` symptoms;
  taxonomy has eight classes; cross-references to the two new skills.

### Eval results
- Not measured yet. The six new cases pass `validate_evals.py`. The pilot
  (`claude plugin eval --runs 2 --model claude-sonnet-5-5`) stopped before any model call because
  the eval CLI was not logged in, so it gives no fire rates or Δ. Re-run after `claude /login`.

## [0.8.2] - 2026-10-19

Skill triggering tuned against real eval results. Measured with `claude plugin eval --runs 1 --model claude-sonnet-5-5`; the no-plugin baseline is the 2026-10-19 run, and Δ counts the criteria grader only.

### Changed
- `env-doctor-router` description names the most common MCP case first: a server that was just added or edited never shows up in the session while other servers work. Builds on the 0.8.1 folder rename.

### Eval results
- Must-fire: 1/2 -> 2/2. Must-not-fire: 2/2 quiet before and after. Mean Δ: +0.25 -> +0.25.

## [0.8.1] - 2026-10-19

### Fixed
- The skill folder is renamed `skills/env-doctor/` → `skills/env-doctor-router/` to match its frontmatter name. Claude Code identifies plugin skills by folder, so `/env-doctor:diagnose`'s "load `env-doctor-router`" step now resolves by its primary name (re-audit RA-CED-01).

## [0.8.0] - 2026-10-19

### Added
- **The SessionStart hook runs real checks and is silent otherwise (CED-P1-01, default behaviour change).** It used to print the same reminder in every session. It now speaks only when a cheap read-only check fails: the project `.mcp.json` is invalid JSON, or uses `${NAME}` with no default while `NAME` is unset (environment and settings `env` blocks), or the project sits in a Syncthing folder with `node_modules` / `.venv` / `venv` missing from `.stignore`. Output is SessionStart `additionalContext` JSON and names variables, never values. Silence it with the new `session_checks` option or `ENV_DOCTOR_HINT=off`.
- `/env-doctor:diagnose`, the same entry point under a name that does not repeat the plugin name.
- `env-doctor-router` gained a "Which branches apply on which OS" table, so macOS and Linux users are not walked through Windows-only probes, with POSIX equivalents for Windows probe commands.
- `tests/test_session_start_env_advisory.py` (CED-P2-06): healthy project silent, each finding, settings `env` counted, Syncthing ignore forms, opt-outs, garbage stdin.
- Evals: `fires-on-mcp-server-not-loading-after-edit` (targets `env-doctor-router`) and `ignores-explain-environment-variables-concept`.

### Changed
- **No closed list of hook events (CED-P1-03).** The gotcha row claiming `PostToolUseFailure` is not a valid event was wrong (the current hooks reference lists it, with `TaskCompleted`, `StopFailure` and others). The row now tells the reader to compare an event name with the official hooks reference for the installed version.
- `/env-doctor:env-doctor` is a deprecated stub that forwards to `/env-doctor:diagnose`; it will be removed in a later minor version.
- The hook uses the vendored `hooks/_vendor/hooklib.py`.
- Skill descriptions rewritten to start with "Use when"; `windows-script-and-task-authoring` trimmed from 1,640 to 820 characters. Cross-references to `git-safety`, `agent-safety-guards`, `docs-wiki` and consuming plugins are conditional.
- README restructured to the marketplace template, generated from the actual command, skills, agent and hook.
- CHANGELOG sections put back in version order (CED-P3-08).

### Security
- **The probe agent reveals no characters of a secret (CED-P2-04).** The "first 2 / last 2 characters" fingerprint allowance is gone; secrets are reported by name, length and character class only.
- The agent, the router skill and the command treat config files, logs, error messages and tool output as data: instructions found there are quoted, never followed.
- Removed `evals/results/`, which held an empty run with absolute machine paths.

Not done: running the evals (CED-P2-06's Δ measurement) costs money and is left to the maintainer. Moving tables out of the two 33 KB skill bodies into references (CED-P3-07, effort M) was not done in this pass: it is a large content move with a recall risk that should be measured with the evals first.

## [0.7.0] - 2026-10-19

### Changed
- **Renamed from `claude-env-doctor` to `env-doctor`.** Names starting with `claude-` are reserved for Anthropic, and `claude plugin validate` rejected the marketplace. The marketplace `renames` map migrates existing installs automatically. The plugin directory is now `env-doctor-plugin/`, and the command is `/env-doctor:env-doctor`.

## [0.6.3] - 2026-10-19

### Fixed
- **Hook launch is portable and space-safe (Wave 1, QW #2/#3).** `hooks/hooks.json` now runs each python hook through one POSIX-sh launcher: the `${CLAUDE_PLUGIN_ROOT}` path is quoted (a plugin root containing a space no longer hands python a truncated path, which exited 2 and blocked the call), the interpreter is picked from `python3` -> `python` -> `py -3` with the `command -v` builtin (guards no longer fail open where `python3` is not the name), a missing script or unresolved root exits 0, and the hook's own exit code is propagated unchanged. Known limit: on Windows without Git Bash, Claude Code runs shell-form hooks in PowerShell, where the launcher does not parse and the hook fails open (non-blocking).
- **README matches the shipped plugin (QW #15, CED-P1-02).** The SessionStart hook prints one fixed reminder line and performs no check; the README claimed a check that stays silent when nothing is wrong. `/env-doctor` takes an optional free-text `[symptom]` only; the advertised scope flags never existed. The routing skill is `env-doctor-router` (renamed in 0.5.0), not `env-doctor`.

### Tests
- `tests/test_hook_launcher.py` proves quoting, exit-2 propagation from a root with a space, unresolved root -> 0, and no python on PATH -> 0.

## [0.6.2] - 2026-09-12

Absorbs two recorded lessons into `windows-script-and-task-authoring`, split across the two layers so neither rule is stated twice.

### Authoring side - `SKILL.md` rule 8

**A script that writes a file for another tool must pin `newline="\n"`.** Python's text-mode `open(p, "w")` translates `\n` to CRLF on Windows, so every value a shell later reads back carries a trailing `\r`. Nothing errors - a CR is a legal argument character - and the symptoms are silent: a `case`/`[[ ]]` membership test that should obviously match does not, and a CLI called with the value rejects it as unknown. The diagnostic tell is an **n-1 failure count**: every line fails except the last, which has no trailing newline and therefore no CR. Pipe through `tr -d '\r'` and re-test before theorising about quoting or stdin.

### Verification side - `references/shell-boundary-hazards.md`

**Verify every byte-level claim in Python, not with a shell regex.** Git Bash `grep -E` mishandles an `\x`-range character class, so a search built to prove "this file is pure ASCII" reports non-ASCII content in files that are pure ASCII with no CR bytes. The engine is wrong, not the files - and the false positive matters because encoding claims are exactly what gets written into a validator and enforced against a whole corpus. Read the bytes and count them. Placed beside the existing CRLF-grep trap it extends.

## [0.6.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (1 must-fire case + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-scheduled-task-shows-console-window` targets `windows-script-and-task-authoring`
- `ignores-macos-bash-config-append` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.6.0] - 2026-08-22

Three rules promoted from recorded session lessons via `/lessons-to-plugins`. All land in existing
reference files; no skill `description` changed and nothing was removed.

### Added

- `windows-script-and-task-authoring/references/shell-boundary-hazards.md` - **do not test for CRLF
  with `grep` on an escape sequence.** `grep -c $'
'` collapses to an empty pattern in Git Bash and
  matches every line, reporting a file as 100% CRLF when it is pure LF; the resulting line-ending
  "defect" is an artifact of the test. Count raw bytes with `tr -dc '
' | wc -c`, and be explicit
  about whether the working tree or the staged blob is being measured, since `core.autocrlf=true`
  makes them legitimately differ.
- Same file - **never deliver multi-line content through a heredoc**: quoting misbehaves at the
  boundary and long content hits the command-length limit, both of which fail by writing something
  subtly different rather than by erroring.
- `env-doctor/references/syncthing.md` - **`.stignore` comments are `//`.** A bare `#` line is parsed
  as an ordinary *pattern*, not a comment (`#include` remains a real directive), so `# vendored deps`
  silently becomes a rule. Adds the `(?d)` prefix for deletable trees and the rule that a
  workspace-root `.stignore` governs every project beneath it, making an edit a cross-project change
  that needs a backup and approval.

### Changed

- `shell-boundary-hazards.md` workaround #3 ("relative paths after `cd`") is now qualified as holding
  **within a single invocation only**. Across calls the inherited working directory can drift, and a
  relative path then resolves somewhere unintended - creating a stray file instead of editing the
  target, with a success status either way. The guidance was not wrong about path translation; it was
  silent about cwd drift.

## [0.5.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Resolved a name collision: `commands/env-doctor.md` and `skills/env-doctor/SKILL.md` both resolved to `claude-env-doctor:env-doctor`, so one shadowed the other even though the command explicitly delegates to the skill. The skill is now `env-doctor-router` and the command's delegation target was updated; the `/env-doctor` entry point is unchanged. Also fixed `user_invocable` -> `user-invocable` on 2 skills.

## Undated notes between 0.4.0 and 0.5.0

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
