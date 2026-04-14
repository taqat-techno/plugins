---
name: ragtools-ops
description: Operational console for the ragtools local RAG product. Use when the user mentions "ragtools", "rag tools", "rag service", "rag doctor", "rag-mcp", "Qdrant lock", "knowledge base setup", "MCP server for rag", "local rag", "markdown_kb", "rag.exe", "RAGTools", "127.0.0.1:21420", "service.log", or asks to install / configure / diagnose / repair / upgrade / reset / monitor a local RAG product. Also activates on error messages like "Storage folder data/qdrant is already accessed", "Permission denied: 'ragtools.toml'", "Collection NOT FOUND", "Startup sync skipped", "Application startup failed". Routes to the right reference file. Never re-implements search.
version: 0.1.0
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

## Phase 3 — Answer or hand off to a command

After loading the right reference, decide:

- **Pure information question** → answer from the reference, in compact form. Cite the reference filename so the user can re-read it.
- **Status / diagnostic question** → suggest `/rag-doctor` (default mode is a fast state probe; `--full` runs the deep `rag doctor` wrap).
- **Setup / install / upgrade** → suggest `/rag-setup` (smart state-aware — branches to install, start-service, upgrade, or verify depending on detected state).
- **Repair walkthrough** → suggest `/rag-doctor <symptom>` or `/rag-doctor --symptom F-NNN --fix` (playbook walker is built in).
- **Project management** → suggest `/rag-projects <subcommand>` (list/add/remove/enable/disable/rebuild).
- **Destructive reset** → suggest `/rag-reset --soft | --data | --nuclear`.
- **Plugin-layer config** → suggest `/rag-config` (telemetry, claude-md rule, mcp-dedupe, hook-observability).

**Command consolidation note (v0.4.0):** the plugin now has 6 user-facing commands (down from 8). `/rag-status`, `/rag-repair`, and `/rag-upgrade` were absorbed into `/rag-doctor` and `/rag-setup` respectively. All state detection is centralized in `rules/state-detection.md`.

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
- `../../docs/decisions.md` — D-001..D-013 binding decisions
