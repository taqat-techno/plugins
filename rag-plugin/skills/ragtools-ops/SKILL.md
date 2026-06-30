---
name: ragtools-ops
description: Operational console for the ragtools local RAG product. Activates on ragtools-related keywords ("ragtools", "rag tools", "rag service", "rag doctor", "rag-mcp", "Qdrant lock", "knowledge base setup", "MCP server for rag", "local rag", "markdown_kb", "rag.exe", "RAGTools", "Code Knowledge Index", "project mode", "search_project_context", "find_definition", "secret_audit"). Covers Windows service launcher reliability (autostart, Scheduled Task, native-stderr pitfalls) and Code Knowledge Index awareness (per-project docs/code/general mode, secret-audit workflow).
version: 0.8.0
last_reviewed: 2026-07-01
---

# ragtools-ops

You are operating the **rag-plugin** plugin: an operations and support layer for the **ragtools** local RAG product. The product already exists at `https://github.com/taqat-techno/rag` and on the user's machine. Your job is to install, configure, diagnose, repair, upgrade, and run it — **not to re-implement it**.

## Critical boundary rules

These come from `../../ARCHITECTURE.md` and `../../docs/decisions.md`. They are binding:

1. **Never call `search_knowledge_base`, `search_project_context`, or `find_definition` yourself.** Claude Code already calls these content/discovery MCP tools directly via the running ragtools MCP server. If the user asks to search (docs or code), point them at the MCP — do not wrap it. (D-001, D-032 §1a) Ops tools like `list_projects`, `index_status`, `project_status`, `secret_audit`, etc. are different — the skill calls those freely per Phase 2.5/2.6 (D-022, D-032).
2. **Never write `config.toml` from a CWD-relative path.** This caused the v2.4.1 data-loss bug. Always go through the HTTP API at `127.0.0.1:21420` for project edits. (D-002, F-001)
3. **Never open Qdrant directly.** The service is the sole owner of the file lock.
4. **Never recommend MPS or GPU device for the encoder.** The `device="cpu"` pinning is mandatory. (`references/risks-and-constraints.md`)
5. **Never auto-download installer artifacts.** Produce URLs and instructions; the user clicks. (D-003)
6. **Never call `set_project_mode`.** It would change a project's indexing mode for real — that capability is intentionally not wired into the plugin yet, pending an app-side fix. Explain what it does if asked; do not invoke it. (D-032 §3)

If you find yourself wanting to do any of these six things, **stop**.

## Phase 1 — Detect mode

Always do this first. Every operational answer depends on it.

**The canonical recipe lives in `rules/state-detection.md`** (v0.4.0). Do not re-implement it — reference it. The recipe produces a structured `state` object (`install_mode`, `service_mode`, `binary_path`, `version`, `config_path`, `data_path`, `log_path`) and the 6-line mode banner that every command prints at the top of its response.

If you are answering a pure knowledge question and do not need to dispatch a command, you still print the mode banner first — users rely on it for at-a-glance orientation. Compact-by-default does not allow dropping the banner.

**Dispatch summary:**
- `install_mode == not-installed` → recommend `/setup`.
- `service_mode == BROKEN` → recommend `/doctor --full --fix`.
- `service_mode == DOWN` → offer `rag service start`; read ops still work in CLI direct mode with the "encoder will load" warning.
- `service_mode == UP` → proceed normally, defer to the running MCP for search.

## Phase 2 — Route to the right reference

Use `references/INDEX.md` to pick the smallest set of reference files for the user's concern. **Default to loading exactly one file** — multiple loads only when the INDEX says so.

### Quick routing table

| User says... | Load |
|---|---|
| "what is ragtools / components / overview" | `references/overview.md` |
| "install / installer / how to download / dev install" | `references/install.md` |
| "verify / smoke test / did it install" | `references/post-install-verify.md` |
| "where is X / paths / data dir / log dir" | `references/paths-and-layout.md` |
| "config.toml / RAG_* env / .ragignore" | `references/configuration.md` |
| ".mcp.json / wire to Claude / proxy mode / direct mode" | `references/mcp-wiring.md` |
| "startup / how does it work / indexing flow" | `references/runtime-flow.md` |
| "logs / activity / health endpoints" | `references/logs-and-diagnostics.md` |
| an error message or symptom | `references/known-failures.md` first, classify, then `references/repair-playbooks.md` |
| "how do I fix X / X is broken" | `references/repair-playbooks.md` |
| "reset / rebuild / nuclear / recover" | `references/recovery-and-reset.md` |
| "version / compatibility / what changed" | `references/versioning.md` |
| "platform / macOS / Linux / single-process" | `references/risks-and-constraints.md` |
| "is X supported / does X work / unimplemented" | `references/gaps.md` first |
| triage / "where do I start" | `references/quick-checklist.md` |

For failure IDs (`F-001`..`F-012`), use the failure-ID → playbook table in `references/INDEX.md`.

### Routing rules (from INDEX.md)

1. **Default to the smallest viable load.** Most user questions need exactly one reference file.
2. **Never load `INDEX.md` itself for content** — routing only.
3. **For unknown symptoms**, load `known-failures.md` first to attempt classification before walking any playbook.
4. **For destructive operations**, always load `recovery-and-reset.md` (it has the gating language) before walking the user through a delete.
5. **For "is X supported" questions**, load `gaps.md` first — the answer may be "no, this is unimplemented".

## Phase 2.5 — MCP tool dispatch (v0.5.0+)

When the ragtools MCP (v2.5.0+) is loaded in the session, the skill **chains MCP tools directly** to answer operational questions, without requiring the user to type a slash command. This is the preferred path — it is faster, gives structured output, and honors the envelope contract (see `rules/mcp-envelope.md` for the binding error-code / mode / cooldown discipline).

Before calling any MCP tool, follow `rules/mcp-envelope.md` §1–§5: branch on `error_code` first, check `mode` before proxy-only tools, fall back to HTTP/CLI when the MCP is `failed` or the needed tool is disabled. Never reinvent the envelope handling.

### 2.5.1 User intent → MCP tool mapping

| User phrasing / intent | MCP tool chain | Workflow |
|---|---|---|
| "Is the service running?" / "What state is rag in?" | `index_status` (core, both modes) | Parse the string output for `Mode:` line. Done. |
| "Show me projects" / "List my indexed projects" | `list_projects` (core) | Print the result. |
| "Show status of project X" / "Is X healthy?" / "How many files in X?" | `list_projects` → verify X exists → `project_status(X)` | 2.5.2 |
| "What files are in project X?" / "List all indexed files for X" | `list_project_files(project=X)` | Print paged table. |
| "Show me the biggest files in X" / "What's dominating X's chunks?" | `project_summary(project=X, top_files=10)` | Print top-N table. |
| "Why isn't file F indexed?" / "File F is missing from search" / "Can't find X in the KB" | 2.5.3 why-not-indexed workflow | Multi-step chain. |
| "Add an ignore rule" / "Exclude `tmp/` from project X" / "How do I ignore node_modules?" | 2.5.4 ignore-rule workflow | Preview → confirm → add → reindex. |
| "Remove an ignore rule" / "Stop excluding X" | 2.5.5 remove-ignore-rule workflow | Preview impact → confirm → remove → reindex. |
| "Reindex project X" / "Re-run indexing" / "Project X is stale" | 2.5.6 reindex decision tree | Incremental first; destructive only on drift. |
| "Reindex everything" | List projects → offer incremental `run_index` per project; route to `/reset --soft` for single-project destructive rebuild |
| "Is X in the ignore list?" / "What rules apply to X?" | `get_project_ignore_rules(project=X)` | Print built_in + config_global + config_project. |
| "What would happen if I ignored `*.tmp`?" | `preview_ignore_effect(project=X, pattern="*.tmp")` | Print would_exclude count and list; do not commit. |
| "Show recent errors in the log" / "Tail the service log" | `tail_logs(source="service", limit=50)` (filesystem fallback — works even in degraded mode) | Print filtered output. |
| "Show me recent crashes" / "Has the service crashed lately?" | `crash_history()` (filesystem fallback) | Print items with exception_type + traceback. |
| "Run rag doctor" / "Diagnose rag" / "Why is rag broken?" | `system_health()` + `crash_history()` + `service_status()` | Structured card; suggest `/doctor --full` for richer output. |
| "Show me the admin-panel activity" / "Who/what is calling rag recently?" | `recent_activity(limit=50)` | Print events; note `source: "mcp:<sid>"` for MCP-attributed writes. |
| "What MCP tools does rag have?" / "Are all the rag tools enabled?" | Infer from available `mcp__plugin_rag_ragtools__*` in session; supplement with `get_config` if granted | 2.5.7 tool-grant audit |
| "Show me the config" / "Where does rag store data?" | `get_config()` + `get_paths()` (both filesystem fallback) | Summarized — not the whole dump unless --verbose. |
| "Where is X implemented in project P?" / "how does this module work?" / "show me the code that does Y" | `search_project_context` (Claude-direct, not a plugin call — D-032 §1a) | See CLAUDE.md retrieval rule §0b for the routing condition (project mode must be `code`/`general`). Not a skill workflow. |
| "Find the definition of X" / "where is class/function Y declared" | `find_definition` (Claude-direct, not a plugin call — D-032 §1a) | See CLAUDE.md retrieval rule §0b — treat as a lead, not authority. Not a skill workflow. |
| "Check project X for embedded secrets" / "audit X" / "is anything sensitive indexed" | `secret_audit(project=X)` | 2.6.1 secret-audit workflow |
| "Enable code search / dev mode / code indexing for project X" / "what mode is X in" / "what does code mode index" | `project_status` for the read question; **no tool for the write question — not yet wired** | 2.6.2 project-mode workflow |

### 2.5.2 Project health workflow

```
1. list_projects() → verify X is in the result
   → not found: "Project X is not indexed. See /projects for the project list."
2. project_status(X) → envelope
3. Parse data: path_exists, enabled, files, chunks, last_indexed, ignore_patterns_count
4. Emit a compact card:
     Project X — ENABLED — healthy
       Path:  <path>  (exists: true)
       Files: 12  Chunks: 340
       Last indexed: <last_indexed>
       Ignore patterns: 0
   If path_exists=false: [WARN] path disappeared → offer to run diagnosis
   If enabled=false: [INFO] project is disabled → mention re-enable via admin panel
5. If user asked "why didn't search return anything" → chain into 2.5.3
```

### 2.5.3 Why-not-indexed workflow (new in v0.5.0)

Replaces the need for a separate `/rag-why-not-indexed` command. Activates automatically on "why isn't X indexed", "why is file F missing", "I can't find X in search results", "search returned nothing for X".

```
1. Derive project P from the path F (first path segment OR user-specified).
2. list_project_files(P, limit=1000) → search for F in results[].path
   → found: "F IS indexed (project P, as of <last_indexed>). If search isn't returning it, the issue is semantic — the chunk exists but your query doesn't match. Try rephrasing or widening scope."
   → not found: continue.
3. get_project_ignore_rules(P) → walk built_in + config_global + config_project
4. For each rule that could match F (fnmatch-style), preview_ignore_effect(P, rule) and check if F is in would_exclude[]
   → matched: "F is excluded by pattern '<rule>' from <source: built_in / config_project>"
      If source=config_project: offer remove_project_ignore_rule(P, rule) + run_index(P) (gated)
      If source=built_in: explain why built-in rules exist; refuse removal unless user overrides via admin UI
5. If no rule matches, the issue is either:
   a. project.path doesn't contain F (wrong project) → suggest list_projects and correct project
   b. project_status shows path_exists=false → route to /doctor
   c. File was added after last index → offer run_index(P) (gated)
6. Every destructive step (remove rule, reindex) goes through rules/mcp-envelope.md §6.3 gates.
```

### 2.5.4 Add-ignore-rule workflow (new in v0.5.0)

Replaces a separate `/rag-ignore add` command. Activates on "exclude", "ignore", "don't index", "skip" in combination with a path pattern.

```
1. If pattern unclear or not provided, ask the user for the exact glob pattern.
2. preview_ignore_effect(project=X, pattern=<pat>) → shows would_exclude[] and count
3. Present to user:
     "This would exclude N files from project X:
       - file1.md
       - file2.md
       - ... (plus <N-10> more)"
4. If N > 0: typed gate — "type ADD to confirm adding this rule"
   If N == 0: warn — "this pattern excludes nothing. add anyway? (yes/no)"
5. add_project_ignore_rule(project=X, pattern=<pat>) → envelope
   On COOLDOWN: wait retry_after_seconds, retry once
   On success: print `status` + `note` ("Run reindex to propagate" — the MCP reminds us)
6. Offer run_index(X) to propagate — gated `(yes/no)`
7. If yes: run_index(X) → envelope; on COOLDOWN wait + retry once
8. Echo stats (indexed, skipped, deleted, chunks_indexed)
```

### 2.5.5 Remove-ignore-rule workflow (new in v0.5.0)

Activates on "remove ignore", "stop excluding", "unexclude", "index this after all".

```
1. get_project_ignore_rules(X) → confirm pattern exists in config_project (not built_in)
   → pattern in built_in: "'<pat>' is a built-in rule. Built-in rules exist for a reason (binary files, VCS metadata). To override, use the ragtools admin UI."
   → pattern not present: "'<pat>' is not in the ignore list. Nothing to remove."
   → pattern in config_project: continue
2. Typed gate — "type REMOVE to confirm removing rule '<pat>' from project X"
3. remove_project_ignore_rule(X, pat) → envelope; cooldown 1s
4. Offer run_index(X) to pick up previously excluded files — gated `(yes/no)`
5. Echo stats.
```

### 2.5.6 Reindex decision tree (new in v0.5.0)

Replaces the need for a separate `/rag-reindex` command. Activates on "reindex", "re-run index", "project X is stale", "my search misses new files".

```
1. list_projects() → confirm X exists
2. run_index(X) → incremental, idempotent, 2s cooldown
   On COOLDOWN: wait retry_after_seconds, retry once
3. Inspect stats: {indexed, skipped, deleted, chunks_indexed}
4. Drift-detection heuristic (from ragtools_mcp_doc.md §12.5):
   if stats.deleted > 5 AND stats.indexed < 2:
       "Incremental index detected significant drift (deleted=<N>, added=<M>).
        A full reindex would recover a clean state. This is destructive:
        the Qdrant collection is dropped and rebuilt. Auto-backup of the
        state DB is taken first."
       Typed gate — "type DELETE to confirm full reindex"
       reindex_project(X, confirm_token=X) ← plugin ALWAYS sets token = project_id programmatically
       30s cooldown — honor retry_after_seconds
       Echo stats (deleted_files, files_indexed, chunks_indexed)
5. Else: report the incremental stats and stop.
```

### 2.5.7 Tool-grant audit (new in v0.5.0)

Activates on "what tools are enabled", "why isn't tool X working", "do I have tool Y granted".

```
1. Infer from session: which mcp__plugin_rag_ragtools__* tools appear in the deferred tool registry?
   (All 3 core + N optional based on ragtools.toml [mcp.tools])
2. Map to plugin command dependencies per rules/mcp-envelope.md §9 grant checklist.
3. Emit a table:
     Required by               | Tool                | Granted?
     --------------------------|---------------------|---------
     /doctor default       | index_status        | ✅ (core)
     /doctor --full        | system_health       | ❌  ← toggle in admin UI
     /doctor --full        | crash_history       | ❌  ← toggle in admin UI
     /doctor --logs        | tail_logs           | ✅
     /projects status      | project_status      | ✅ (default ON)
     Skill: why-not-indexed    | list_project_files  | ✅ (default ON)
     Skill: ignore rules       | preview_ignore_eff. | ✅ (default ON)
     Skill: reindex            | run_index           | ✅ (default ON)
     Skill: reindex            | reindex_project     | ✅ (default ON)
4. If any are disabled: one-line toggle path for each —
     "Enable in admin panel → http://127.0.0.1:21420/config → MCP Tool Access → toggle <name> → Save → restart Claude Code"
```

### 2.5.8 Multi-project search preparation (does NOT call search)

When the user asks to search across multiple projects (e.g. "search docs, notes, and references for X"), the skill helps **prepare the query spec** — it does not call `search_knowledge_base` itself (D-001 / D-022).

```
1. list_projects() → verify all named projects exist
2. For any missing name, correct (substring match) or ask the user.
3. Construct the query spec and show it back:
     search_knowledge_base(
       query="<the user's question>",
       projects=["docs", "notes", "references"],
       top_k=10,
       structured=True
     )
4. Claude then calls that tool directly — the skill does not mediate.
```

### 2.5.9 MCP failure handling (fallback chain)

When `index_status` returns a string starting with `[RAG ERROR]` or any optional tool returns `STARTUP_FAILED`:

```
1. Surface the error verbatim — do not bury it.
2. State which fallback path is being taken:
     "[info] MCP in failed mode; falling back to CLI (rag doctor) + HTTP (/api/status)."
3. Suggest: "/doctor --full" (which itself handles failed mode).
4. Do not retry the MCP call in the same session — settings are read once at startup.
```

When an optional tool is needed but not registered (disabled in admin UI):

```
1. Name the tool and its toggle path (see 2.5.7).
2. Fall back to HTTP API equivalent (where one exists) or CLI command (for debug tools without HTTP equivalent).
3. Print one info line about the degraded path — do not pretend the richer data is available.
```

## Phase 2.6 — Code Knowledge Index awareness (new in v0.8.0)

ragtools v2.7.0+ adds a Code Knowledge Index: a project's `mode` (`docs` / `code` / `general`, default `docs`) controls whether source code and config files are indexed alongside (or instead of) Markdown. Four MCP tools are involved: `search_project_context`, `find_definition`, `secret_audit`, `set_project_mode`. **`docs/decisions.md` D-032 governs how the plugin treats each one — read it before changing anything in this phase.**

**Routing for the two read/discovery tools lives in the CLAUDE.md retrieval rule §0b, not here** — same "Claude calls directly, plugin never wraps" principle as `search_knowledge_base` (D-001, D-032 §1a). This phase covers only the two workflows that *are* plugin-mediated: auditing for secrets, and explaining — never executing — a mode change.

### 2.6.1 — Secret-audit workflow (new in v0.8.0)

Activates on "check project X for secrets", "audit X", "is anything sensitive indexed", or as a recommendation `/doctor --full` itself surfaces (see `commands/doctor.md`).

```
1. list_projects() → verify the project exists; if not, offer closest matches.
2. mcp__plugin_rag_ragtools__secret_audit(project=<id>)
   → envelope; on success, data is a list of {file, line, rule} hits — never the secret value itself.
3. Render:
     Secret audit — project <id>
       <N> potential hit(s):
         <file>:<line>  rule=<rule>
         ...
   If N == 0: "no secret-pattern hits found in indexed content for <id>."
4. ALWAYS append this caveat, regardless of the result, until a plugin maintainer confirms
   (state.redaction_fix_status == fixed, see rules/state-detection.md) that the app-side fix has shipped:

     "Note: ragtools' content-level secret redaction does not run on the routine indexing
      path as of the version checked. A clean result here does not guarantee no secret
      VALUES are stored — it means no value currently matches a known secret pattern.
      If anything above looks like a real credential, rotate it and re-run this audit
      after the next indexing pass."

   Once state.redaction_fix_status == fixed, drop this caveat — a clean result is then a
   real guarantee, not a partial one.
5. This is a read-only call — no confirmation gate (rules/mcp-envelope.md §6.3: reads need no gate).
6. Envelope handling per rules/mcp-envelope.md: SERVICE_DOWN/DEGRADED_MODE → "secret_audit requires
   proxy mode. start: rag service start". Tool not granted → name it + admin-UI toggle path (2.5.7
   pattern), no fallback exists (secret_audit has no HTTP-only or CLI equivalent).
```

**This workflow is what `/projects audit <id>` calls.** It is intentionally a one-time, explicitly-invoked action (a command surface, per D-021) — not something the skill runs automatically on every project status check, and not a hook. The skill *recommends* it (via `/doctor --full`'s D-032 finding); it does not run it unprompted.

### 2.6.2 — Project mode: explain, do not change (new in v0.8.0)

Activates on "what mode is project X in", "enable code search for X", "turn on dev mode", "what does code mode index".

```
1. "What mode is X in?" → project_status(X) already returns a `mode` field (docs/code/general) —
   render it as part of the existing 2.5.2 project-health card. No new tool call needed.
2. "What does <mode> actually index?" → explain from this static rule, no tool call:
     docs    → Markdown / text content only (the historical default — nothing changes for these projects)
     code    → source code + config files, no Markdown
     general → both
3. "Enable code search / turn on dev mode for X" →
   a. Explain what set_project_mode(project=X, mode=<...>) would do.
   b. State plainly that this plugin does not call it yet (D-032 §3) — the production indexing
      write path has a known gap where content-level secret redaction does not run, and that
      isn't scoped to Dev Mode; it's safest to run 2.6.1's secret-audit workflow first
      regardless of what the user ultimately decides.
   c. If the user wants to proceed anyway, point them at the ragtools admin panel
      (http://127.0.0.1:21420/config) where the equivalent setting exists today, outside the
      plugin's gated path — make clear this is the user's own informed choice, not a
      plugin-endorsed action.
4. Never call set_project_mode from this skill. If you find yourself about to, stop — see
   "Critical boundary rules" at the top of this file.
```

## Phase 3 — Answer or hand off to a command

After loading the right reference, decide:

- **Pure information question** → answer from the reference, in compact form. Cite the reference filename so the user can re-read it.
- **Operational question answerable via MCP ops tools** → chain MCP tools per Phase 2.5, in the current conversation — no slash command needed. This is the default for "why isn't X indexed", "add an ignore rule", "reindex X", "show me crashes", etc.
- **Status / diagnostic question (deep)** → suggest `/doctor` (default mode is a fast state probe; `--full` runs the deep `system_health` + `crash_history` + CLI fallback wrap).
- **Setup / install / upgrade** → suggest `/setup` (smart state-aware — branches to install, start-service, upgrade, or verify depending on detected state).
- **Repair walkthrough** → `/doctor <symptom>` or `/doctor --symptom F-NNN --fix` (playbook walker is built in).
- **Project management (interactive)** → `/projects` with no args defaults to `list`; subcommands `status <id>`, `summary <id>`, `files <id>`, `add <path>`, `remove <id>`, `enable <id>`, `disable <id>`, `rebuild <id>`.
- **Destructive reset** → `/reset` with no args enters an interactive picker; `/reset --soft | --data | --nuclear` jumps straight to a level.
- **Plugin-layer config** → `/config` (telemetry, claude-md rule, mcp-dedupe, hook-observability).

**Command surface (v0.7.0, unchanged in v0.8.0):** 7 user-facing commands + 1 maintainer-only (`/sync-docs`). Every command works standalone (no required args) AND accepts parameters. New capabilities ship as **skill workflows** (Phase 2.5/2.6), not new commands — preferred route per D-021 and the v0.5.0 direction. The Code Knowledge Index work (D-032) added one subcommand (`/projects audit`) to an existing command, not a new command — consistent with this rule.

**Sibling skill — `markdown-authoring` (v0.7.0):** when the user asks Claude to **create** any Markdown file (README, runbook, SOP, concept page, architecture doc, design notes), the `markdown-authoring` skill at `${CLAUDE_PLUGIN_ROOT}/skills/markdown-authoring/SKILL.md` is the right entry point — it loads the RAG-optimized authoring standard and the 5 page templates. When the user asks to **improve existing** Markdown, route to `/md-rag-enhance` (the always-safe improver command). The two are complementary: the skill shapes new content, the command enhances old content. Neither overlaps with `ragtools-ops`' operator-of-ragtools scope.

## Output discipline (D-008)

- **Compact by default.** ≤ 25 lines unless the user asks for verbose.
- Tables, not paragraphs.
- Cite the reference file you loaded so the user can re-read it.
- Show the mode banner first, then the answer, then a one-line "see also" if relevant.

## Service-down behavior (D-005)

- **Read ops** (status, doctor, project list) — allowed in CLI direct mode with a clear "service down → encoder will load (5–10 s)" warning.
- **Write ops** (add/remove project, rebuild, watcher control) — refused with "service must be running for write operations — run `rag service start` first".

## Windows service launcher reliability

When you set up or repair autostart for the long-lived ragtools service (Scheduled Task, login launcher, or a hand-rolled wrapper), these are the failure modes that silently kill the process ~1 min after launch. Prefer the product's own first-party `rag service install / start / status` tooling over hand-rolled task mechanics; only reach for the patterns below when wiring autostart yourself.

| Anti-pattern (and why it kills the service) | Do instead |
|---|---|
| In PowerShell 5.1, redirecting a **native exe's** stderr (`rag.exe ... 2>$log`) while `$ErrorActionPreference='Stop'`. PS 5.1 wraps every native stderr line in a `NativeCommandError` record and **throws on the first write**, terminating PowerShell and its child. One harmless stderr warning kills the service ~1 min in. | Capture native stderr with `Start-Process -RedirectStandardError <file>` (does not wrap) plus `WaitForExit()`. |
| A **Scheduled Task action pointing at a `.cmd` wrapper** that runs the service. The spawned `cmd.exe` shares console handles and receives `CTRL_BREAK_EVENT` when the launch context tears down — propagating to the child as `0xC000013A` (STATUS_CONTROL_C_EXIT) ~1 min in. | Action = `powershell.exe -File launcher.ps1` directly (no cmd wrapper); spawn the service via `Start-Process -WindowStyle Hidden` so it **detaches**. If the Ctrl+C exit persists, wrap the launcher in a `wscript` VBS shim so PowerShell runs fully orphaned and exits 0. |
| A non-idempotent launcher that **spawns a duplicate** every time autostart re-fires — duplicates then fight for the Qdrant lock (F-003). | Probe the target port first and `exit 0` if the service is already listening, so re-running never spawns a duplicate. |

Before swapping any task XML or config, keep a rollback backup of both (task XML + config) so a bad launcher change is reversible.

## Source discipline (defer to the live product)

The bundled `references/` are a point-in-time snapshot and can drift from the installed build — that is why `/sync-docs` exists. When a reference disagrees with the **live product** — `rag --help`, the running service's `/health` + `/api/*`, `get_config()` / `get_paths()`, or the upstream repo `https://github.com/taqat-techno/rag` — **the live source wins.** Surface the conflict ("the bundled doc says X, but `rag --help` shows Y") rather than silently trusting the doc, and state which source you used. This mirrors the source-routing discipline in `~/.claude/CLAUDE.md` Section 0: bundled notes and KB hits are *leads*; code, runtime, and official docs are *truth*.

## When the user asks something the references don't cover

If the answer isn't in the references, say so. Check `references/gaps.md` to see if it's a known unverified item. **Never invent product behavior.** Refer the user to the upstream repo `https://github.com/taqat-techno/rag` if they need behavior the doc doesn't describe.

## See also

- `references/INDEX.md` — full routing table
- `references/_meta.md` — source doc identity, version compat band
- `../../ARCHITECTURE.md` — boundary rules (forbidden list)
- `../../docs/decisions.md` — D-001..D-022 binding decisions
- `../../rules/state-detection.md` — canonical state-detection recipe
- `../../rules/mcp-envelope.md` — MCP envelope / error-code / cooldown / confirm-token discipline (v0.5.0+); also the single source of truth for the current tool inventory (no external handoff doc — see that file's own note on why)
- `../../docs/decisions.md` — D-001..D-032 binding decisions
