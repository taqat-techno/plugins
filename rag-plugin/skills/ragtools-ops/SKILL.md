---
name: ragtools-ops
description: Operational console for the ragtools local RAG product. Activates on ragtools-related keywords ("ragtools", "rag tools", "rag service", "rag doctor", "rag-mcp", "Qdrant lock", "knowledge base setup", "MCP server for rag", "local rag", "markdown_kb", "rag.exe", "RAGTools", "127.0.0.1:21420", "service.log"), error messages ("Storage folder data/qdrant is already accessed", "Permission denied: 'ragtools.toml'", "Collection NOT FOUND", "Startup sync skipped", "Application startup failed"), AND operational user intents — "why isn't this file in search?", "why is my project missing results?", "add an ignore rule", "exclude node_modules", "reindex my project", "why didn't Claude find X in the KB?", "what MCP tools does rag have?", "show me recent crashes", "tail the service log", "check which projects are indexed". When the ragtools MCP is loaded in the session, the skill chains MCP ops tools directly; when the MCP is unavailable, it falls back to HTTP/CLI per rules/mcp-envelope.md. Never wraps or re-implements search_knowledge_base (D-001) — content retrieval is always Claude's direct call.
version: 0.5.0
---

# ragtools-ops

You are operating the **rag-plugin** plugin: an operations and support layer for the **ragtools** local RAG product. The product already exists at `https://github.com/taqat-techno/rag` and on the user's machine. Your job is to install, configure, diagnose, repair, upgrade, and run it — **not to re-implement it**.

## Critical boundary rules

These come from `../../ARCHITECTURE.md` and `../../docs/decisions.md`. They are binding:

1. **Never call `search_knowledge_base`, `list_projects`, or `index_status` yourself.** Claude Code already calls these MCP tools directly via the running ragtools MCP server. If the user asks to search, point them at the MCP — do not wrap it. (D-001)
2. **Never write `config.toml` from a CWD-relative path.** This caused the v2.4.1 data-loss bug. Always go through the HTTP API at `127.0.0.1:21420` for project edits. (D-002, F-001)
3. **Never open Qdrant directly.** The service is the sole owner of the file lock.
4. **Never recommend MPS or GPU device for the encoder.** The `device="cpu"` pinning is mandatory. (`references/risks-and-constraints.md`)
5. **Never auto-download installer artifacts.** Produce URLs and instructions; the user clicks. (D-003)

If you find yourself wanting to do any of these five things, **stop**.

## Phase 1 — Detect mode

Always do this first. Every operational answer depends on it.

**The canonical recipe lives in `rules/state-detection.md`** (v0.4.0). Do not re-implement it — reference it. The recipe produces a structured `state` object (`install_mode`, `service_mode`, `binary_path`, `version`, `config_path`, `data_path`, `log_path`) and the 6-line mode banner that every command prints at the top of its response.

If you are answering a pure knowledge question and do not need to dispatch a command, you still print the mode banner first — users rely on it for at-a-glance orientation. Compact-by-default does not allow dropping the banner.

**Dispatch summary:**
- `install_mode == not-installed` → recommend `/rag-setup`.
- `service_mode == BROKEN` → recommend `/rag-doctor --full --fix`.
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
| "Reindex everything" | List projects → offer incremental `run_index` per project; route to `/rag-reset --soft` for single-project destructive rebuild |
| "Is X in the ignore list?" / "What rules apply to X?" | `get_project_ignore_rules(project=X)` | Print built_in + config_global + config_project. |
| "What would happen if I ignored `*.tmp`?" | `preview_ignore_effect(project=X, pattern="*.tmp")` | Print would_exclude count and list; do not commit. |
| "Show recent errors in the log" / "Tail the service log" | `tail_logs(source="service", limit=50)` (filesystem fallback — works even in degraded mode) | Print filtered output. |
| "Show me recent crashes" / "Has the service crashed lately?" | `crash_history()` (filesystem fallback) | Print items with exception_type + traceback. |
| "Run rag doctor" / "Diagnose rag" / "Why is rag broken?" | `system_health()` + `crash_history()` + `service_status()` | Structured card; suggest `/rag-doctor --full` for richer output. |
| "Show me the admin-panel activity" / "Who/what is calling rag recently?" | `recent_activity(limit=50)` | Print events; note `source: "mcp:<sid>"` for MCP-attributed writes. |
| "What MCP tools does rag have?" / "Are all the rag tools enabled?" | Infer from available `mcp__plugin_rag_ragtools__*` in session; supplement with `get_config` if granted | 2.5.7 tool-grant audit |
| "Show me the config" / "Where does rag store data?" | `get_config()` + `get_paths()` (both filesystem fallback) | Summarized — not the whole dump unless --verbose. |

### 2.5.2 Project health workflow

```
1. list_projects() → verify X is in the result
   → not found: "Project X is not indexed. See /rag-projects for the project list."
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
   b. project_status shows path_exists=false → route to /rag-doctor
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
     /rag-doctor default       | index_status        | ✅ (core)
     /rag-doctor --full        | system_health       | ❌  ← toggle in admin UI
     /rag-doctor --full        | crash_history       | ❌  ← toggle in admin UI
     /rag-doctor --logs        | tail_logs           | ✅
     /rag-projects status      | project_status      | ✅ (default ON)
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
3. Suggest: "/rag-doctor --full" (which itself handles failed mode).
4. Do not retry the MCP call in the same session — settings are read once at startup.
```

When an optional tool is needed but not registered (disabled in admin UI):

```
1. Name the tool and its toggle path (see 2.5.7).
2. Fall back to HTTP API equivalent (where one exists) or CLI command (for debug tools without HTTP equivalent).
3. Print one info line about the degraded path — do not pretend the richer data is available.
```

## Phase 3 — Answer or hand off to a command

After loading the right reference, decide:

- **Pure information question** → answer from the reference, in compact form. Cite the reference filename so the user can re-read it.
- **Operational question answerable via MCP ops tools** → chain MCP tools per Phase 2.5, in the current conversation — no slash command needed. This is the default for "why isn't X indexed", "add an ignore rule", "reindex X", "show me crashes", etc.
- **Status / diagnostic question (deep)** → suggest `/rag-doctor` (default mode is a fast state probe; `--full` runs the deep `system_health` + `crash_history` + CLI fallback wrap).
- **Setup / install / upgrade** → suggest `/rag-setup` (smart state-aware — branches to install, start-service, upgrade, or verify depending on detected state).
- **Repair walkthrough** → `/rag-doctor <symptom>` or `/rag-doctor --symptom F-NNN --fix` (playbook walker is built in).
- **Project management (interactive)** → `/rag-projects` with no args defaults to `list`; subcommands `status <id>`, `summary <id>`, `files <id>`, `add <path>`, `remove <id>`, `enable <id>`, `disable <id>`, `rebuild <id>`.
- **Destructive reset** → `/rag-reset` with no args enters an interactive picker; `/rag-reset --soft | --data | --nuclear` jumps straight to a level.
- **Plugin-layer config** → `/rag-config` (telemetry, claude-md rule, mcp-dedupe, hook-observability).

**Command surface (v0.5.0):** 6 user-facing commands + 1 maintainer-only (`/rag-sync-docs`). Every command works standalone (no required args) AND accepts parameters. New capabilities ship as **skill workflows** (Phase 2.5), not new commands — preferred route per D-021 and the v0.5.0 direction.

## Output discipline (D-008)

- **Compact by default.** ≤ 25 lines unless the user asks for verbose.
- Tables, not paragraphs.
- Cite the reference file you loaded so the user can re-read it.
- Show the mode banner first, then the answer, then a one-line "see also" if relevant.

## Service-down behavior (D-005)

- **Read ops** (status, doctor, project list) — allowed in CLI direct mode with a clear "service down → encoder will load (5–10 s)" warning.
- **Write ops** (add/remove project, rebuild, watcher control) — refused with "service must be running for write operations — run `rag service start` first".

## When the user asks something the references don't cover

If the answer isn't in the references, say so. Check `references/gaps.md` to see if it's a known unverified item. **Never invent product behavior.** Refer the user to the upstream repo `https://github.com/taqat-techno/rag` if they need behavior the doc doesn't describe.

## See also

- `references/INDEX.md` — full routing table
- `references/_meta.md` — source doc identity, version compat band
- `../../ARCHITECTURE.md` — boundary rules (forbidden list)
- `../../docs/decisions.md` — D-001..D-022 binding decisions
- `../../rules/state-detection.md` — canonical state-detection recipe
- `../../rules/mcp-envelope.md` — MCP envelope / error-code / cooldown / confirm-token discipline (v0.5.0+)
- `../../../ragtools_mcp_doc.md` — MCP v2.5.0 handoff doc (source-of-truth for the 22-tool surface)
