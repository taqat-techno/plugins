# rag-plugin

Operations console and retrieval guide for **ragtools**, a local-first RAG service that
indexes Markdown and code into an embedded Qdrant database and serves it to Claude Code
through its own MCP server.

## What it does

The plugin installs, configures, diagnoses, repairs, upgrades and resets ragtools, and
registers its MCP server. It also teaches Claude to use the knowledge base correctly:
every search carries a project scope (ragtools refuses unscoped calls), a project's
docs/code indexing mode is checked before an empty result is read as "absent", the right
service is chosen when several run, and citation paths are verified. It never
re-implements search.

It is for developers who run ragtools on their own machine. Without ragtools installed
the plugin has nothing to operate: the commands explain how to install it, and the hooks
stay silent.

What it is not: not a search wrapper (Claude calls the ragtools MCP tools directly), not
an installer (it gives you the download link; you run it), not a config editor (project
changes go through the ragtools HTTP API), and never a Qdrant client.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install rag@taqat-techno-plugins
```

Then run `/rag:setup`. It detects whether ragtools is missing, stopped, outdated or
healthy and walks the matching path.

## Requirements

| Requirement | Why | How to check |
|---|---|---|
| **ragtools** 2.5.0 to 3.5.x (target 3.5.1) | the product this plugin operates | `rag version` |
| `rag` on `PATH` | the bundled `.mcp.json` starts `rag serve` | `where rag` (Windows) / `which rag` |
| **Python 3.10+** as `python3`, `python` or `py` | the hooks and helper scripts (stdlib only) | `python3 --version` |
| bash | Claude Code runs hook commands with bash (Git Bash on Windows) | `bash --version` |
| `curl` | `/doctor`, `/setup`, `/projects` probe the HTTP API | `curl --version` |
| GitHub CLI `gh` (optional) | only `/report`, to file issues | `gh auth status` |

ragtools downloads are published at
[github.com/taqat-techno/rag/releases](https://github.com/taqat-techno/rag/releases):
a Windows x64 installer, a macOS 14+ Apple Silicon tarball and a Linux arm64 tarball.
Other platforms install from source (`pip install -e ".[dev]"` in a clone).

**ragtools licence.** ragtools is a separate project and this plugin does not include
it. As of 2026-10-19 the `taqat-techno/rag` repository does not yet declare a licence. An
MIT licence for it is proposed in [taqat-techno/rag#11](https://github.com/taqat-techno/rag/pull/11),
which is open and pending review, not merged. Until that pull request lands, check the
repository for its current licence before you depend on it.

## Commands

All commands run with no arguments.

| Command | Bare invocation | Purpose |
|---|---|---|
| `/rag:doctor` | fast state probe | Diagnose, status and repair. `--full` wraps `rag doctor`; a free-text symptom or `--symptom F-NNN` classifies and walks a playbook; `--logs` scans `service.log`; `--fix` walks the playbook with typed confirmations. |
| `/rag:setup` | detect and branch | Install walkthrough, start the service, upgrade (`--upgrade`), or verify MCP wiring, the CLAUDE.md rule and duplicate registrations. |
| `/rag:projects` | `list` | Project list, status, summary, files, add, remove, enable, disable, rebuild and `audit` (secret audit), all through the HTTP API or MCP. |
| `/rag:project-focus` | `set` (auto-detect) | Pin retrieval to one project for this workspace (`--global` for all), `status`, `clear`. |
| `/rag:reset` | asks for a level | `--soft` (rebuild with backup), `--data`, `--nuclear`. Prints the commands and needs typed `DELETE` (1x/2x/3x); the plugin never deletes anything itself. |
| `/rag:config` | `status` | Telemetry toggle, CLAUDE.md retrieval rule (install / remove, always confirmed unless you type `--yes`), MCP duplicate cleanup, hook decision log. |
| `/rag:report` | generate locally | Local diagnostic reports. Public issue bodies are counts-only by default; you see each full body before filing with `gh`. `--dry-run` never files. |
| `/rag:md-rag-enhance` | preview, then ask | Two always-safe Markdown fixes for better chunking. Recursive runs preview first and ask before writing; `--dry-run` writes nothing. User-invoked only. |
| `/rag:sync-docs` | compare | Maintainer-only drift check of bundled references against the upstream doc. User-invoked only. |

## Skills

| Skill | Loads when |
|---|---|
| `ragtools-ops` | You install, run, diagnose, repair, upgrade or reset ragtools, or ask about its MCP wiring, a Qdrant lock, indexing mode or `secret_audit`. |
| `ragtools-retrieval` | You answer from a ragtools knowledge base, or a ragtools search came back empty, weak or conflicting. Not for repositories ragtools does not index. |
| `markdown-authoring` | You write Markdown that a ragtools project will index. If the docs-wiki plugin is installed, wiki pages follow its `wiki-authoring` skill and this one adds only chunking rules. |
| `ragtools-release` | A maintainer prepares a release of ragtools itself. It does not load for release checklists in other projects. |

## Agents

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `rag-log-scanner` | haiku | Read, Bash | Matches `service.log` against the F-001..F-012 catalog and returns JSON. Never diagnoses; log text is treated as data. |

## Hooks

| Event | Matcher | What it does | Can it block? |
|---|---|---|---|
| `PreToolUse` | `Bash\|PowerShell` | If a command that will run is `rag index` / `rebuild` / `watch`, a standalone `rag-mcp`, or Python opening Qdrant directly, and a ragtools service answers `/health`, it asks you to confirm (the two would fight over the Qdrant lock). Text in `echo`, `grep`, commit messages, comments and quotes is ignored. | It asks; it never denies. 10 s timeout. |
| `UserPromptSubmit` | all prompts | For question-shaped prompts about your project, resolves the ragtools project for the directory and adds a short note: the scope to pass, the project's mode and freshness, and whether a scoped probe found a match. Silent for other prompts. | No: every exit is normalised to 0. 10 s timeout. |

Both run `hooks/hook_launcher.py` through the marketplace's portable launcher: a missing
or unexpanded path exits 0, and `python3`, `python` and `py -3` are tried in turn.

When no service answers, the prompt hook remembers that for 60 seconds
(`RAG_PLUGIN_HOOK_DOWN_TTL`), so a machine without ragtools running pays the health
probes about once a minute rather than on every prompt.

## Configuration

**Plugin options** (set when you enable the plugin, or later in its settings):

| Option | Type | Default | Effect |
|---|---|---|---|
| `service_port` | number | `0` | ragtools port for the hooks. `0` probes 21420 (installed) then 21421 (source install). |
| `hook_decision_log` | boolean | `true` | Write the hook decision log (see Data & privacy). |

**Environment variables** (fallbacks and tuning):

| Variable | Default | Effect |
|---|---|---|
| `RAG_PLUGIN_SERVICE_PORT` / `RAG_SERVICE_PORT` | unset | Port override when `service_port` is 0. |
| `RAG_PLUGIN_HOOK_HEALTH_TIMEOUT` / `RAG_PLUGIN_HOOK_SEARCH_TIMEOUT` | 0.5 / 1.5 s | Prompt-hook request timeouts. |
| `RAG_PLUGIN_HOOK_PROBE_THRESHOLD` | 0.65 | Score at which the probe reports a match. |
| `RAG_PLUGIN_HOOK_DOWN_TTL` | 60 s | How long a "service down" verdict is trusted. `0` disables the cache. |
| `RAG_PLUGIN_HOOK_LOG_MAX_BYTES` | 1048576 | Size at which the decision log rotates. |
| `RAG_PLUGIN_DATA_DIR` | unset | Override the data directory (tests). |
| `RAG_PLUGIN_HOOK_DEBUG` | unset | Launcher diagnostics on stderr. |

**Files** in the plugin data directory `${CLAUDE_PLUGIN_DATA}`:

| File | Written by |
|---|---|
| `config.json` | you, optionally: `/report` routing (`report.repos.application`, `report.repos.plugin`, `report.github_account`) |
| `state/project-focus.json` | `/project-focus` |
| `state/context-cache.json`, `state/service-down.json` | the prompt hook |
| `hook-decisions.log` (+ `.1`) | the prompt hook |
| `usage.log`, `.telemetry-enabled`, `.hook-observability-disabled` | `/config` |
| `reports/<timestamp>/` | `/report` |

Versions up to 0.19.x kept these files in `~/.claude/rag-plugin/`. They are still read
from there as a fallback and copied forward the first time they are needed.

`/config claude-md install` writes a marker-delimited block into `~/.claude/CLAUDE.md`
(or `./CLAUDE.md` with `--project`), and `/config mcp-dedupe clean` edits
`~/.claude.json` / `~/.claude/.mcp.json` after a backup and a typed `CLEAN`.

## Platform support

| Platform | Status |
|---|---|
| Windows 10/11 x64 | Primary. Packaged ragtools with autostart. Hooks run under Git Bash; the lock guard also covers the PowerShell tool. |
| macOS 14+ Apple Silicon | Supported. No LaunchAgent autostart in ragtools (G-002); Intel Macs are not built (G-004). |
| Linux | arm64 tarball, or a source install on x86_64 (`references/linux-dev-mode.md`). |
| WSL | Works when ragtools runs inside the same WSL instance (loopback ports). Not specifically tested. |

## Data & privacy

- **Network:** the hooks and scripts talk only to ragtools on `127.0.0.1`. The only
  traffic that leaves the machine is `/report` filing a GitHub issue with `gh`, after
  you have read and approved that exact body.
- **Hook decision log:** on by default. One JSON line per prompt the hook sees, in
  `${CLAUDE_PLUGIN_DATA}/hook-decisions.log`: timestamp, action tag, prompt length,
  whether the shape gate matched, the resolved ragtools project id, mode and state,
  probe score or error, and the number of HTTP calls. It never holds the prompt text.
  It rotates at 1 MB with one backup, so it stays under about 2 MB. Turn it off with the
  `hook_decision_log` option or `/config hook-observability off`; delete it with
  `/config hook-observability clear`.
- **Telemetry:** off by default. `/config telemetry on` creates `usage.log` and a marker.
  No command records events in this version, so the file stays empty.
- **`/report`:** reads ragtools state, the hook decision log and, unless you pass
  `--no-sessions`, recent Claude Code session transcripts under `~/.claude/projects/`,
  and writes reports to `${CLAUDE_PLUGIN_DATA}/reports/`. Public issue bodies contain
  counts only; snippets are opt-in (`--include-snippets`) and scrubbed. Redaction is
  pattern-based, so read the body before you approve it.
- **On screen:** the prompt hook adds a few lines of context to Claude (project id, mode,
  freshness). The lock guard shows the matched command, with secret-shaped values
  masked.
- **Uninstall:** Claude Code removes `${CLAUDE_PLUGIN_DATA}`. Files in the legacy
  `~/.claude/rag-plugin/` and the CLAUDE.md block (`/config claude-md remove`) stay until
  you remove them.

## Limitations

- The plugin is only as capable as the installed ragtools. Known product gaps G-001 to
  G-010 are listed in `skills/ragtools-ops/references/gaps.md`; the plugin refuses
  cleanly instead of working around them.
- The prompt hook's shape and intent rules are English-only; prompts in other languages
  usually pass through with no note.
- Commands pass `${CLAUDE_PLUGIN_DATA}` to the scripts they run. A script you run by hand
  without that variable uses the legacy `~/.claude/rag-plugin/` directory.
- `/report` redaction is pattern-based and cannot recognise every secret or client name.
- The service-down cache can hide a just-started service from the prompt hook for up to
  60 seconds.

Troubleshooting starts with `/rag:doctor`; failure IDs F-001..F-012 are in
`skills/ragtools-ops/references/known-failures.md`. Design rules are in `ARCHITECTURE.md`
and binding decisions in `docs/decisions.md`.

## License

MIT (`LICENSE`). ragtools itself is a separate project with its own terms; see the
Requirements section for its licence status.
