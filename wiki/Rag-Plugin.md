# Rag Plugin

**Package:** `rag` · **Version:** `0.7.0` · **Category:** productivity · **License:** MIT · **Source:** [`rag-plugin/`](../../rag-plugin/) · **MCP server:** `ragtools` (spawns `rag serve` directly)

> **Upstream application:** the **ragtools** product this plugin operates lives at **[github.com/taqat-techno/rag](https://github.com/taqat-techno/rag)**. Installers, source, CHANGELOG, release history, and product-level documentation all live in that repo — **not** in this plugin. This plugin is the operator console (install, diagnose, repair, configure); the upstream repo is the application.
>
> Install artifacts per platform (as of ragtools v2.5.1):
>
> | Platform / arch | Path | Artifact |
> |---|---|---|
> | Windows 10/11 (x64) | packaged installer | [`RAGTools-Setup-{version}.exe`](https://github.com/taqat-techno/rag/releases/latest) |
> | macOS 14+ (Apple Silicon) | packaged tarball | [`RAGTools-{version}-macos-arm64.tar.gz`](https://github.com/taqat-techno/rag/releases/latest) |
> | Linux ARM64 (v2.5.1+) | packaged tarball | [`RAGTools-{version}-linux-arm64.tar.gz`](https://github.com/taqat-techno/rag/releases/latest) |
> | **Anything else** (macOS Intel, Linux x86_64, Windows ARM, etc.) | **source install** — universal fallback | `git clone github.com/taqat-techno/rag` + `pip install -e ".[dev]"` |
>
> `/rag-setup` walks all four paths automatically.

## Purpose

Operations and support layer for the [**ragtools**](https://github.com/taqat-techno/rag) local-first RAG (Retrieval-Augmented Generation) product. The plugin installs, configures, diagnoses, repairs, upgrades, and runs ragtools. It **never re-implements search** — content retrieval is always Claude's direct call to `search_knowledge_base` via the registered MCP server (D-001 / D-022).

## What it does

| Job | How |
|---|---|
| **Register ragtools MCP** | Plugin-level `.mcp.json` spawns `rag serve` directly (D-020) — 22-tool MCP surface becomes available automatically |
| **Auto-install CLAUDE.md retrieval rule** | The v0.2.0 amendment (D-016): teaches Claude to call `search_knowledge_base` before saying "I don't have information" |
| **UserPromptSubmit retrieval-reminder hook** | Tier-2 harness-enforced reminder (D-017) that fires when the user's prompt likely has a knowledge-base match |
| **Detect install state** | `packaged-windows` / `packaged-macos` / `dev-mode` / `not-installed` via `rules/state-detection.md` |
| **Diagnose service health** | Via MCP `system_health` + `crash_history` + `service_status` (preferred) or `rag doctor` CLI (fallback) |
| **Walk repair playbooks** | 8 named playbooks for F-001..F-012 failures with typed confirmation gates |
| **Manage projects** | Project CRUD via HTTP API + MCP project-ops tools (status, summary, files, ignore rules, reindex) |
| **Guarded destructive reset** | 3 escalation levels with typed-DELETE gates (1×/2×/3×) and pre-v2.4.1 hard-block |
| **Plugin-layer observability** | Opt-in usage log, claude-md rule lifecycle, MCP dedupe, hook-observability |

## How it works (high level)

### Smart state-aware command design (D-021)

v0.4.0 consolidated 9 narrow commands into **6 smart state-aware commands + 1 maintainer-only**. Each command runs a shared state probe at Step 0 and branches on detected state (not-installed / service DOWN / service BROKEN / service UP but old / service UP and current / service UP but unhealthy).

### MCP envelope contract (D-022 + `rules/mcp-envelope.md`)

v0.5.0 integrated ragtools MCP v2.5.0's 22-tool surface. Every MCP-using path:
- Branches on **`error_code`** (not `error` string)
- Checks **`mode`** before calling proxy-only tools
- Uses the **MCP → HTTP → CLI** three-tier fallback chain
- Respects **cooldowns** (`run_index` 2s, `reindex_project` 30s, ignore-rule ops 1s)
- Sets **`confirm_token = project_id` programmatically** for `reindex_project` (defeats injection)
- Surfaces missing-tool errors with admin-UI toggle paths

### Layer ownership

Per [`rag-plugin/ARCHITECTURE.md`](../../rag-plugin/ARCHITECTURE.md):

```
commands/  →  skills/ragtools-ops/SKILL.md  →  references/  →  rules/  →  data
```

- Commands are thin dispatchers. Behavior lives in the skill's phased flow and the reference library.
- **23 reference files** under `skills/ragtools-ops/references/` slice the upstream `ragtools_doc.md` + platform specifics + failure catalog + repair playbooks.
- **3 rules**: `claude-md-retrieval-rule.md` (v0.2.0 shipped asset), `state-detection.md` (v0.4.0 shared probe), `mcp-envelope.md` (v0.5.0 binding contract).

## Commands (7 user + 1 maintainer)

All commands work **standalone** (no required args; sensible defaults) and accept optional parameters.

| Command | Default behavior | Key flags / subcommands |
|---|---|---|
| `/rag-doctor` | Fast state probe (replaces former `/rag-status`) | `--full` (deep diagnose), `--symptom F-NNN` (playbook), `--logs` (log scan), `--fix` (inline walker), free text (symptom classification), `--verbose` |
| `/rag-setup` | Smart install / upgrade / verify — branches on state | `--project <path>`, `--upgrade` (force upgrade branch), `--verify` (force idempotent verify) |
| `/rag-projects` | Lists projects (v0.5.0 — standalone = `list`) | `list` / `status <id>` / `summary <id> [n]` / `files <id> [n]` / `add <path>` / `remove <id>` / `enable <id>` / `disable <id>` / `rebuild <id>` |
| `/rag-reset` | Interactive picker (v0.5.0 — standalone = picker) | `--soft` / `--data` / `--nuclear` |
| `/rag-config` | Plugin-layer config dashboard | `telemetry {on\|off\|status}`, `claude-md {install\|remove\|status}`, `mcp-dedupe {status\|clean}`, `hook-observability {status\|on\|off\|analyze\|clear}` |
| `/rag-sync-docs` | **Maintainer-only** (`disable-model-invocation: true`) | Reports drift between bundled references and upstream `ragtools_doc.md` |
| `/md-rag-enhance` | Always-safe Markdown enhancer (v0.7.0) | No args → enhance every `.md` under CWD; optional positional file arg → one file. Only flags are `--verbose` and `--no-backup`. Applies two mechanical safe fixes (pseudo-heading → real heading, blank-line normalization); reports every structural finding for manual review |

## Skills (3)

The plugin ships **three skills** with no-overlap activation triggers:

| Skill | Audience | Activates on |
|---|---|---|
| [`ragtools-ops`](../../rag-plugin/skills/ragtools-ops/SKILL.md) | Operators (anyone using ragtools) | ragtools keywords, error messages, operational intents ("why isn't this file in search", "add an ignore rule", "reindex project X", "diagnose rag") |
| [`ragtools-release`](../../rag-plugin/skills/ragtools-release/SKILL.md) | **Maintainers only** | "pre-release check", "release checklist", "ready to ship ragtools", "v2.5.x pre-flight", "release go/no-go", "RELEASE_LIFECYCLE", "cutting a ragtools release" |
| [`markdown-authoring`](../../rag-plugin/skills/markdown-authoring/SKILL.md) | **Content authors** (v0.7.0+) | "write a README for X", "document component Y", "create a runbook for Z", "draft an SOP", "RAG-friendly markdown", "optimize for retrieval" — any Markdown creation intent for content that will be indexed by ragtools |

The three skills never overlap. Operators never see the release-gate or authoring skill; maintainers preparing a release get the six-invariant walk; authors creating Markdown get the 8 hard rules + 5 page templates automatically on the triggering phrasing.

### `markdown-authoring` — chunker-optimized Markdown creation (v0.7.0+)

Auto-activates when Claude is asked to create any `.md` file — READMEs, runbooks, SOPs, architecture pages, reference docs, concept pages. Loads three reference files:

- **`references/rag-md-guidelines.md`** — the full 359-line authoring standard reverse-engineered from `src/ragtools/chunking/markdown.py`. The 8 hard rules + 6 soft rules.
- **`references/page-templates.md`** — 5 copy-paste scaffolds (concept, SOP, reference, runbook, architecture) each designed to produce 3–6 clean heading-anchored chunks.
- **`references/anti-patterns.md`** — 9 anti-patterns with per-item chunker-mechanism rationale.

Emits Markdown that satisfies the §8 pre-commit checklist: opens with `# Title`, sections ≤ 300 words, leaf headings unique, no knowledge in YAML frontmatter, code blocks ≤ 60 lines, tables ≤ 15 rows, prose before code. **Never auto-saves** — Claude proposes content; the user accepts/edits/rejects.

Pairs with the `/md-rag-enhance` command (below) which handles **existing** Markdown.

### `ragtools-release` — release-gate workflow (v0.6.0+)

Walks six permanent invariants before an upstream ragtools release ships:

1. **No user data into install directory** — verifies `get_config_write_path()` is used, no `{app}\` writes.
2. **Schema changes bump version + ship migration** — `CONFIG_VERSION`, `PRAGMA user_version`, encoder dim, index schema.
3. **Dev-mode isolation** — `is_packaged()` guard in `run.py`; dev-mode never touches `{userdata}` or registers Startup task.
4. **Upgrade-path manual test** — downloaded installer exercised on a pre-upgraded machine. Ships as pre-release until manually validated.
5. **Uninstall opt-in prompt** — both full-wipe and keep-data branches tested when the uninstall code path is touched.
6. **`docs/RELEASE_LIFECYCLE.md` accuracy** — canonical doc matches reality, new platforms covered.

Output is a compact release-gate summary: `GREEN / PRE-RELEASE / BLOCKED` with required follow-ups and an optional JSONL ack log line for traceability. The skill **never tags, pushes, promotes, or builds** — pure gating.

Full rule text + source-of-truth files per invariant: [`skills/ragtools-release/references/release-checklist.md`](../../rag-plugin/skills/ragtools-release/references/release-checklist.md).

### `ragtools-ops` — auto-activating MCP workflows

`skills/ragtools-ops/SKILL.md` activates on ragtools keywords, error messages, AND operational user intents. Phase 2.5 (v0.5.0) defines 9 MCP workflows that chain tools **without needing a slash command**:

1. User intent → MCP tool mapping table
2. Project health (`list_projects` → `project_status`)
3. **Why-not-indexed** — `list_project_files` → `get_project_ignore_rules` → `preview_ignore_effect` → offer removal + reindex
4. **Add ignore rule** — preview → typed ADD gate → add → offer reindex
5. **Remove ignore rule** — refuses `built_in` rules, typed REMOVE gate for `config_project`
6. **Reindex decision tree** — incremental first (`run_index`), drift detection, destructive escalation (`reindex_project`) with typed DELETE + 30s cooldown
7. **Tool-grant audit** — shows which MCP tools are enabled/disabled and toggle paths
8. **Multi-project search prep** — builds the spec, Claude calls the tool (plugin never wraps)
9. **MCP failure handling** — uniform fallback chain

## Agent

| Agent | Model tier | Role |
|---|---|---|
| `rag-log-scanner` | haiku | Reads `service.log` lines (from MCP `tail_logs` or disk), classifies findings against the F-001..F-012 catalog, returns JSON — never diagnoses or invents F-IDs |

## Hooks

| Hook | Event | Posture |
|---|---|---|
| `lock_conflict_check.py` | PreToolUse (Bash) | Warns before commands that would fight the Qdrant single-process file lock (D-007: **ask, never deny**) |
| `prompt_retrieval_reminder.py` | UserPromptSubmit | Tier-2 guided enforcement — probes `/api/search?top_k=1` and injects a retrieval reminder when a MODERATE+ match is likely (D-017) |

## Configuration

- **Admin UI:** `http://127.0.0.1:21420/config` — toggle the 9 debug MCP tools on/off (all OFF by default), adjust chunk params, projects, ports.
- **Plugin-layer:**
  - `/rag-config telemetry` — opt-in local JSONL at `~/.claude/rag-plugin/usage.log` (default OFF).
  - `/rag-config claude-md` — install/remove the retrieval rule in `~/.claude/CLAUDE.md`.
  - `/rag-config mcp-dedupe` — detect and clean duplicate ragtools registrations.
  - `/rag-config hook-observability` — JSONL log of the UserPromptSubmit hook's decisions (default ON, opt-out via marker file).

## Dependencies

- **ragtools 2.5.x** installed and runnable (`rag` on PATH or `/rag-setup` writes a user-level `.mcp.json` with absolute binary path).
- **Python 3.10+** for plugin scripts.
- **Qdrant** (embedded; single-process lock — the plugin's PreToolUse hook exists to protect it).
- No cloud dependencies. Zero network egress (D-012).

## Inputs and outputs

**Inputs:**
- User intent (the skill activates on phrasing, no slash command needed for most workflows).
- Slash commands for deliberate dispatch (`/rag-doctor`, `/rag-setup`, etc.).
- Project IDs, paths, ignore patterns.

**Outputs:**
- Compact state tables, findings blocks, diagnostic cards.
- Playbook walks — one step at a time, typed gates on destructive steps.
- No synthesized content from search results; retrieval flows through Claude → MCP directly.

## Usage examples

### Skill activates automatically

```
"Why isn't my file runbook.md showing up in search?"
→ Skill runs workflow 2.5.3 (why-not-indexed):
  list_project_files → get_project_ignore_rules → preview_ignore_effect
  → offers to remove the matching rule + run_index (gated)

"Add an ignore rule for tmp/ in project alpha"
→ Skill runs workflow 2.5.4:
  preview_ignore_effect → typed ADD gate → add_project_ignore_rule
  → offers run_index (gated)

"Reindex project beta"
→ Skill runs workflow 2.5.6:
  run_index → inspect stats → drift detection → optional destructive reindex
```

### Commands for deliberate dispatch

```
/rag-doctor                  # fast state probe
/rag-doctor --full           # deep system_health + crash_history
/rag-doctor "service won't start"    # free-text symptom classification
/rag-doctor --symptom F-003 --fix    # walk the P-qdrant playbook with typed gates
/rag-projects                # defaults to list
/rag-projects status alpha   # rich per-project card
/rag-setup                   # state-aware install/upgrade/verify
/rag-reset                   # interactive picker: soft/data/nuclear
```

## Known limitations

- **Windows-first.** Commands have macOS and Linux branches, but Windows is the primary tested environment.
- **Intel macOS refused.** ragtools does not ship an Intel build (gap G-004); Apple Silicon required.
- **Linux packaged install unavailable.** ragtools does not ship a Linux artifact (G-001); Linux users follow the dev install path.
- **The UserPromptSubmit hook requires Python 3** on PATH and probes `127.0.0.1:21420` on every prompt (~30–50ms).
- **D-020 binary-name requirement:** `rag` (not `rag-mcp`) must be on PATH for the plugin-level `.mcp.json` to auto-wire. The RAGTools installer adds it by default; dev-mode `pip install -e .` exposes both.
- **MCP tool grants.** 9 debug tools default OFF; users must toggle them in the admin UI for `/rag-doctor --full`'s richer output.

## Related plugins and integrations

- **devops** — search runbooks/SOPs while triaging Azure DevOps PRs (the rag-plugin hook injects the reminder).
- Any plugin for long-running tasks — the `/rag-doctor --logs` agent workflow can be combined with other diagnostics.

## See also

- Source: [`rag-plugin/README.md`](../../rag-plugin/README.md)
- [`rag-plugin/ARCHITECTURE.md`](../../rag-plugin/ARCHITECTURE.md) — layer ownership, forbidden list, boundary self-test
- [`rag-plugin/CHANGELOG.md`](../../rag-plugin/CHANGELOG.md) — v0.1.0 → v0.5.0 evolution
- [`rag-plugin/docs/decisions.md`](../../rag-plugin/docs/decisions.md) — D-001 through D-022 binding decisions
- [`rag-plugin/rules/state-detection.md`](../../rag-plugin/rules/state-detection.md) — canonical state probe
- [`rag-plugin/rules/mcp-envelope.md`](../../rag-plugin/rules/mcp-envelope.md) — MCP envelope handling contract
- `ragtools_mcp_doc.md` at the workspace root — MCP v2.5.0 handoff (source-of-truth for the 22-tool surface)
