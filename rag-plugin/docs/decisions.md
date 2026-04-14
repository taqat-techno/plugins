# rag-plugin Decisions Log

Early decisions that bind every later phase. Each entry is a single binding rule with a one-paragraph rationale. Update only by appending — never rewrite history.

---

## D-001 — Plugin scope: ops-only, never search

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin is a **support, operations, and diagnostics layer** for ragtools. It will not implement `/rag-search` or any retrieval wrapper in MVP. The ragtools MCP server already exposes `search_knowledge_base`, `list_projects`, and `index_status` to Claude Code, and Claude already calls them directly via MCP. Adding a plugin-side wrapper would duplicate the existing tool surface, fight the Qdrant single-process lock, and split the token-efficiency story between the product's compact mode and a plugin formatter.

**Reverse only if:** a clear formatting need emerges that the MCP server can't address from inside the product. Even then, fix it upstream first.

---

## D-002 — Transport mix: HTTP for state, CLI for diagnostics, MCP for search

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When the service is up:
- **Status, projects, watcher, config, index stats** → HTTP API on `127.0.0.1:21420`.
- **`rag doctor`, `rag version`, `rag service start/stop/status`, `rag rebuild`** → shell out to the CLI; these commands are designed to handle both modes.
- **Search** → strictly via the MCP server already running inside Claude Code; the plugin does not call MCP tools itself.

CLI for things the HTTP API also covers (e.g. listing projects) is an anti-pattern — HTTP returns structured JSON; CLI returns pretty text. Prefer the structured side.

**Reverse only if:** the HTTP API drops a critical endpoint or starts returning unstructured responses.

---

## D-003 — References are bundled inline, not fetched

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Phase 1 splits `ragtools_doc.md` into ~12–15 topic files under `skills/ragtools-ops/references/`, bundled with the plugin. The plugin does **not** fetch them at runtime from a known path. Bundling means no install discovery is needed for the references themselves and the plugin is fully self-contained inside the marketplace package.

A maintainer-only doc-sync command (Phase 9) keeps the bundled references aligned with the upstream `ragtools_doc.md` checkout. `references/_meta.md` records the source-doc commit hash.

**Reverse only if:** references grow large enough that bundling them inflates plugin install size noticeably (unlikely — pure markdown).

---

## D-004 — Install discovery order

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When the plugin needs to find ragtools, it resolves in this order — mirroring `src/ragtools/config.py`'s own logic:

1. `RAG_DATA_DIR` env var (if set)
2. `RAG_CONFIG_PATH` env var (if set)
3. `where rag` (Windows) / `which rag` (macOS/Linux)
4. Platform default install paths:
   - Windows: `%LOCALAPPDATA%\Programs\RAGTools\rag.exe`
   - macOS: typical extract dirs (`~/Applications/rag/`, `/usr/local/bin/rag`)
5. Dev-mode detection: `pyproject.toml` + `.venv` in the current working tree
6. **Not installed** → suggest `/rag-setup` (Phase 3+)

This list is the source of truth for any path-resolution helper. Commands must not invent their own order.

**Reverse only if:** ragtools changes its own resolution order in a future major version.

---

## D-005 — Service-down behavior: read OK, write refuse

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When `/health` is unreachable:
- **Read ops** (status, doctor, project list) — allowed, with a clear "service down → CLI direct mode → encoder will load (5–10s)" warning banner.
- **Write ops** (add/remove project, rebuild, watcher control) — **refused**, with a clear "service must be running for write operations — run `rag service start` first" message and an offer to start it.

The v2.4.1 data-loss bug is the justification: direct-mode writes are exactly where the data loss happened. Refusing them in service-down mode is the safest default.

**Reverse only if:** ragtools removes its dual-mode design and direct-mode writes become first-class.

---

## D-006 — Skill granularity: one skill, fat references

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin uses **exactly one skill** (`ragtools-ops`) with a fat `references/` library. Multiple skills (`ragtools-install`, `ragtools-diagnose`, `ragtools-search`) inflate the model's discovery surface for a tightly-scoped product, increase context cost on every turn, and risk routing collisions.

**Reverse only if:** references grow past ~25 files and routing inside the single skill becomes hard to follow.

---

## D-007 — Hook posture: ask, never silently deny

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The Phase 6 PreToolUse Bash hook fires **only when both conditions hold**:
1. The intended command matches a known Qdrant-lock-conflicting pattern (`rag index`, `rag rebuild`, `rag watch`, direct `rag-mcp` invocation, manual Qdrant access).
2. `GET /health` confirms the service is currently up.

When fired, it returns `hookSpecificOutput.permissionDecision: "ask"` with an explicit reason. It **never** returns `deny`. False positives on a hook that blocks would be worse than missed warnings — users would disable the hook and lose protection entirely.

**Reverse only if:** a class of operations emerges that is provably destructive and never-legitimate. Even then, prefer `ask` with strong language.

---

## D-008 — Output verbosity: compact by default, `--verbose` opt-in

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Every command outputs **at most one screen** (≤ 25 lines) by default. Tables, not paragraphs. Drill-down only on user request via `--verbose`. This mirrors the ragtools MCP server's own compact mode (§18.7) which already cuts context cost by 60–70%. Re-formatting MCP results in a verbose way undoes that work.

**Reverse only if:** a command genuinely needs more lines to be useful. Even then, the verbose case is opt-in.

---

## D-009 — macOS first-class by Phase 8, follower in MVP

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

ragtools itself calls macOS support "Phase 1" — tarball only, no `.app`, no `.dmg`, no LaunchAgent, no signing. The plugin will mirror that posture: Phases 0–7 are Windows-first; Phase 8 hardens macOS branches. The plugin will not invent macOS LaunchAgent support, will not pretend `.dmg` exists, and will explicitly fail Intel Macs early rather than letting users download an arm64 tarball that won't run.

**Reverse only if:** ragtools ships full macOS support in a future minor version.

---

## D-010 — Plugin name: `rag-plugin`

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

`rag-plugin` rather than `rag` (collides with the CLI binary), `ragtools` (collides with the package name), or `ragtools-ops` (longer with no benefit). Slash commands are namespaced: `/rag-status`, `/rag-doctor`, `/rag-setup`, `/rag-repair`, `/rag-projects`, `/rag-upgrade`, `/rag-reset`. The `rag-` prefix matches the user's mental model of "the rag tool" without colliding with the binary.

**Reverse only if:** a marketplace name conflict surfaces.

---

## D-011 — Versioning: major.minor compatibility band

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin declares "compatible with ragtools 2.4.x" and bumps on ragtools 2.5 / 3.0 / breaking changes to HTTP API or CLI surface. Exact-version pin is too brittle; "any ragtools" is too loose — references reflect a specific version's failure modes. The compatibility band is recorded in `references/_meta.md` (added in Phase 1).

**Reverse only if:** ragtools adopts strict per-patch breakage (unlikely).

---

## D-012 — Telemetry: none in MVP, opt-in local-only if added

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

No telemetry in MVP. If added in Phase 9, it must be:
- **Opt-in** via an explicit `/rag-config telemetry on` command. Default off.
- **Local-only** — single JSONL file at `~/.claude/rag-plugin/usage.log`. No network egress. Ever.
- **Inspectable** — the user can `cat` it.
- **Documented** in README under a "What we record" heading.

The product is local-first, no-cloud. Networked telemetry would betray the brand. If we can't meet all four bullets, we ship without telemetry.

**Reverse only if:** never. If you want telemetry that doesn't meet these bullets, build a different plugin.

---

## D-013 — Generic vs ragtools-specific helpers

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Path resolution, mode banner, and compact-output formatter are **kept ragtools-specific** in MVP. We do not factor them into a "local-tool ops framework". Premature abstraction is worse than duplication for the next 12 months. If a second plugin emerges that needs the same helpers, factor them out then — not before.

**Reverse only if:** a second consumer materializes.

---

## D-014 — Phase 9 closure

**Date:** 2026-04-14
**Phase:** 9
**Status:** binding (closure note)

All 10 phases of the rag-plugin roadmap are shipped. The plugin has reached its planned scope: 7 user-facing commands + 1 user-facing config command + 1 maintainer-only command + 1 skill + 1 PreToolUse hook + 1 Haiku agent + 23 reference files. The validator reports structure as clean except for 2 known false-positive warnings about hooks.json top-level keys (stale `valid_events` list in `validate_plugin_simple.py` line 267 — same warnings would fire on the official `security-guidance` plugin).

Phase 9 added:
- **README.md finalization** — full command catalog, troubleshooting table, limitations table (G-001..G-010), telemetry posture, architecture diagram
- **CHANGELOG.md** — phase-by-phase deliverables for Phases 0–9
- **`/rag-config`** — local-only opt-in usage-log toggle. Default off. JSONL at `~/.claude/rag-plugin/usage.log`. No paths, no project names, no search queries, no log contents recorded. Zero network egress. Honors D-012 strictly.
- **`/rag-sync-docs`** — maintainer-only with `disable-model-invocation: true`. Reads upstream `ragtools_doc.md` and reports drift. Never auto-rewrites. Out of the user surface.
- **ARCHITECTURE.md** — appended a Phase 9 closure section with the final inventory and the "how to extend the plugin" steps for future contributors

The plugin is **roadmap-complete**. Future work is maintenance:
- Apply `/rag-sync-docs` when ragtools releases a new version
- Update the compatibility band in `_meta.md` and `plugin.json` when ragtools 2.5.x or 3.x ships
- Extend the failure catalog and gap register as the upstream product evolves
- Add new commands only after a new binding decision is recorded here

**Reverse only if:** never. This is a closure entry. Any future scope expansion appends new D-NNN entries.

---

## D-015 — Plugin-level `.mcp.json` ships ragtools MCP automatically

**Date:** 2026-04-14 (post-roadmap amendment)
**Phase:** Post-9
**Status:** binding

The plugin ships its own `.mcp.json` at the plugin root (`plugins/rag-plugin/.mcp.json`), following the `devops-plugin` pattern. When the user installs `rag-plugin` via `/plugins`, Claude Code auto-registers the ragtools MCP server — no manual wiring required, assuming `rag-mcp` is on `PATH`.

**The wired command** is `rag-mcp` with empty args. This is the pip console-script entry from ragtools' `pyproject.toml` and works in both:
- **Dev mode** via `pip install -e .` (active venv = `rag-mcp` on PATH)
- **Packaged Windows** if the installer was run with "Add to PATH" checked (default)

Packaged macOS users must manually add the extract directory to PATH (no installer PATH-registration step yet — macOS is Phase 1 in the upstream product).

**This does NOT violate D-001** (ops-only, never search). The plugin is not implementing search — it is *registering* the pre-existing ragtools MCP server so Claude can call `search_knowledge_base` / `list_projects` / `index_status` directly. Exactly the same pattern as `devops-plugin` registering the Azure DevOps MCP server without re-implementing work items. The plugin is the convenient delivery mechanism for the registration, not the tool implementation.

**Fallback paths remain unchanged:**
- `/rag-setup` branch C.1 still reads `GET /api/mcp-config` and writes a project-level or user-level `.mcp.json` with the exact binary path. Required for packaged installs without PATH integration.
- `references/mcp-wiring.md` documents all three registration options (Option A plugin-level auto, Option B project-level manual, Option C user-level manual) so users on any install mode can get MCP working.

**Placement:** `.mcp.json` lives at the **plugin root**, NOT under `.claude-plugin/`. Matches `devops-plugin/.mcp.json` exactly. Claude Code auto-discovers plugin-level `.mcp.json` files at the root when the plugin is enabled.

**Format:** the plugin-level `.mcp.json` uses the **flat shape** `{"serverName": {...}}` without a `mcpServers` wrapper — matches `devops-plugin/.mcp.json` exactly. Project-level and user-level `.mcp.json` files still use the `mcpServers` wrapper per the standard Claude Code schema. This format difference is plugin-level-specific and documented in `references/mcp-wiring.md` Option A vs Option B/C.

**Reverse only if:** the upstream ragtools product changes the `rag-mcp` entry-point name or removes the pip console script. In that case, update `.mcp.json` to use whatever the new canonical command is.

---

*Append new decisions below. Never rewrite or delete an entry — supersede with a new dated entry that references the old one.*
