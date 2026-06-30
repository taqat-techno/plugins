# RAG Plugin Enhancement Recommendation Report

**Subject:** How `rag-plugin` (taqat-techno/plugins, currently v0.16.0) should evolve to consume the new ragtools Dev Mode / Code Knowledge Index capabilities (taqat-techno/rag, v2.7.0)
**Primary input:** `C:\MY-WorkSpace\rag\RAG_DEV_MODE_CODE_KNOWLEDGE_INDEX_DELIVERY_REPORT.md`
**Method:** This report is implementation-free. Findings below are tagged by source — **[from report]** (the delivery report's claims), **[from code]** (independently re-verified by reading `src/ragtools/*` directly), **[from plugin]** (current `rag-plugin` source), **[from KB]** (ragtools knowledge base / `rag/tasks/todo.md`) — so you can see what was trusted vs. independently confirmed.
**Date of analysis:** 2026-06-30.

---

## 1. Executive Summary

ragtools v2.7.0 shipped a real, working Code Knowledge Index: per-project `mode` (`docs`/`code`/`general`), AST-aware code chunking across 20+ languages, a layered code-first retrieval pipeline (`search_project_context`), a code-graph symbol lookup (`find_definition`), and a secret-scanning/audit surface (`secret_audit`, plus `set_project_mode` to flip a project's mode). **[from report]**

`rag-plugin` v0.16.0 has **zero** awareness of any of it. A repo-wide grep across every `.md`/`.py`/`.json` file in the plugin found no reference to `search_project_context`, `find_definition`, `secret_audit`, or `set_project_mode` anywhere — not in a hook, rule, skill, command, or decision record. **[from plugin]**

That gap is the easy part. The hard part, confirmed independently by reading the app's source rather than trusting the report's claim: **the production indexing write path does not redact secret values, full stop, for every project type that exists today — not just future code-mode ones.** `QdrantOwner.run_full_index()`/`run_incremental_index()` (`service/owner.py`), the code paths behind the file watcher, `/api/index`, project-add auto-indexing, and any mode-change-triggered reindex, call `chunk_file()` directly and never call `secret_scan.redact_text()`. Only the rare "drop everything and rebuild" action routes through the redacting path. **[from code, independently confirmed]** This means the plugin's 12 currently-indexed, docs-only projects have plausibly been storing unredacted secret *values* (not just unredacted filenames — the filename-pattern exclusion layer is fine and unaffected) in the local Qdrant index this entire time. This is bigger than a "don't expose Dev Mode yet" problem; it is a "tell users to audit what's already indexed, regardless of Dev Mode plans" problem.

Given that, this report's central recommendation is: **ship plugin awareness and documentation now (additive, read-only, zero new risk); do not wire `set_project_mode` into any command or skill workflow that actually changes a project's mode until the app-side redaction-bypass fix is confirmed shipped.** A safe, useful, fully scoped first increment exists and is detailed in §12.

---

## 2. Current Plugin Capability Snapshot

`rag-plugin` v0.16.0 (`.claude-plugin/plugin.json:3`; CHANGELOG top entry `## [0.16.0]`, 2026-06-29) is a single-purpose **Markdown RAG operator console**: ragtools indexes local Markdown into one Qdrant collection (`markdown_kb`), and the plugin's job is to wire/diagnose/operate that pipeline — never to mediate search itself. **[from plugin]**

- **Governance layer that matters for this work:** `docs/decisions.md` D-001 (binding, never reversed) — the plugin never wraps or re-implements `search_knowledge_base`; Claude calls content-search tools directly. D-022 (v0.5.0) refined this: once ragtools' MCP surface grew from 3 tools to ~22, the plugin was freed to call the 18 non-search "ops" tools freely, but `search_knowledge_base` stays off-limits to the plugin forever. `rules/mcp-envelope.md` is the single binding contract for *how* any command/skill calls an MCP tool (mode-first branching, 3-tier MCP→HTTP→CLI fallback, cooldown discipline, confirm-token discipline for destructive writes, typed-verbatim confirmation gates, injection defense, and a hard "non-goals" list of 5 tools the plugin must never expose: `add_project`, `remove_project`, `shutdown`, `backup_restore`, `set_active_project`). **[from plugin]**
- **Commands (6 user + 1 maintainer):** `/doctor`, `/projects`, `/reset`, `/config`, `/setup`, `/project-focus`, `/sync-docs` (maintainer-only), plus `/md-rag-enhance`. D-021 binds the plugin to "fewer, stronger, state-aware commands; new capability defaults to a skill workflow, not a new command" — this was the literal precedent followed when the MCP surface last expanded (v0.5.0). **[from plugin]**
- **MCP tools currently referenced anywhere in the plugin:** `search_knowledge_base`, `list_projects`, `index_status`, `project_status`, `project_summary`, `list_project_files`, `get_project_ignore_rules`, `preview_ignore_effect`, `add_project_ignore_rule`, `remove_project_ignore_rule`, `run_index`, `reindex_project`, plus 9 debug tools (`system_health`, `crash_history`, `service_status`, `recent_activity`, `tail_logs`, `get_config`, `get_ignore_rules`, `get_paths`, `list_indexed_paths`). That's it. **[from plugin]**
- **"Mode" vocabulary that already exists is unrelated:** `install_mode` ∈ {not-installed, packaged-windows, packaged-macos, **dev-mode**, unknown} — this describes how the ragtools *binary itself* is installed (source checkout vs. packaged), detected via `pyproject.toml` + `.venv`, used purely for path resolution (`rules/state-detection.md`). The string `"dev-mode"` appears 60+ times in the plugin, exclusively as this value. There is no per-project mode concept anywhere. **This is a real naming collision risk** — anyone searching the plugin for "dev mode" today finds the *install*-mode concept, not the new *project*-mode concept. **[from plugin]**
- **Docs-only / legacy-search-only evidence:** `skills/ragtools-ops/references/mcp-wiring.md` line 10 still asserts *"ragtools exposes **three MCP tools**"* — already stale against the plugin's own documented 22-tool surface, now off by 5+ more. `skills/ragtools-ops/SKILL.md`'s own cited source-of-truth, `../../../ragtools_mcp_doc.md`, **does not exist on disk**. Every search-shaped workflow in the skill terminates in a `search_knowledge_base` call; no code-search alternative is ever mentioned. `ARCHITECTURE.md`'s MCP-surface diagram and "Phase 9 closure inventory" are still pinned to v0.3.0. **[from plugin]**
- **Project mode/dev mode awareness:** None. **[from plugin]**
- **Safety/audit workflow:** Real, but narrowly scoped to two things that are *not* secret-scanning of indexed content: (1) hook-layer fail-open discipline (`rules/hook-failopen.md`, D-031) for advisory hooks; (2) `scripts/rag_report.py`'s own output-redaction layer, which scrubs secrets *found incidentally in the plugin's own diagnostic logs* before filing a GitHub issue via `/report` — this is the plugin auditing its own output text, unrelated to and not calling `secret_audit` against indexed project content. There is no workflow today that proactively checks indexed content for embedded secrets. **[from plugin]**

---

## 3. New RAG App Capabilities Relevant to Plugin

| Capability | Status | Detail |
|---|---|---|
| **Per-project Mode** | DONE, but interface drifted mid-release | `ProjectConfig.mode: Literal["docs","code","general"]` (default `"docs"`, no inherit state). CLI `rag project mode <id> docs\|code\|general`; MCP `set_project_mode(project, mode, confirm_token="")`; HTTP `POST /api/projects/{id}/mode`. **[from code, `config.py:33-34,72`]** |
| **Code Knowledge Index** | DONE | Source code (20+ languages) and config/data files become indexable when a project's mode is `code` or `general`; default stays markdown/text-only (`docs`), matching pre-2.6 behavior exactly. `mode_indexes()`: `docs`→documentation only, `code`→non-documentation only, `general`→both. **[from code, `config.py:37-51`]** |
| **`search_project_context`** | DONE, but always code-first in production | `search_project_context(query, project=None, projects=None, top_k=10) -> str`. Layered code/docs/config search, reranked by context priority. Both production callers (`GET /api/dev-search`, the MCP tool) hardcode `force_dev=True` — the documented "intent detector decides code-first vs. doc-first" behavior is dead code in production. **[from report, corroborated by code signature inspection]** |
| **`find_definition`** | DONE, explicitly framed as discovery not authority | `find_definition(symbol, project=None, top_k=25) -> str`. Lexical-first/semantic-fallback symbol lookup. Docstring explicitly says it's "semantic discovery, not an LSP replacement" — non-empty results are leads, empty results are not proof of absence. Runs as an **unindexed linear Qdrant scroll** (no `create_payload_index`) — a scale concern, not a correctness bug today. **[from code, `integration/mcp_server.py:390-415`]** |
| **`secret_audit`** | DONE as a tool; what it audits may already be tainted | `secret_audit(project=None) -> str`. Scans stored chunk payloads for secret-pattern hits, reports `file:line` + rule name only, never the value. Live test against the `rag` project itself found 3 real hits. **[from report + from code, `service/owner.py:325-375`]** |
| **`set_project_mode`** | DONE, with two gaps | Narrowing away from a code-including mode requires `confirm_token == project`; any actual change auto-triggers a background reindex. Two gaps: (a) the reindex it triggers goes through the **non-redacting** production path (§4); (b) the app's own `WriteCooldown` table has no entry for it, unlike its sibling `reindex_project` — a permanent no-op cooldown guard on the app side. **[from report]** |
| **Watcher / incremental indexing** | PARTIAL | The live-change accept filter correctly resolves nested project roots (fixed in `bd8ac7a`). The "which project do I reindex" routing loop a few lines below still uses first-match instead of the same deepest-match helper — a code-mode child project nested under a docs-mode parent can have edits silently dropped (indexed nowhere). **[from report — not independently re-verified in code by this analysis; treat as high-confidence but unverified by us]** |
| **Code-vs-docs retrieval routing** | Effectively disabled | `feature_intent.detect_dev_intent` exists but is dead code in production for the reason above; `search_knowledge_base` remains pure docs-first and is unaffected. **[from report]** |

**Naming drift (confirms the brief's premise, and independently confirmed in code — important, since it means an agent following old docs literally would call something that never shipped):**

| Old (P1–P7 design; still in CLAUDE.md/CHANGELOG.md) | Shipped (one commit later, `5fb10e8`) |
|---|---|
| `ProjectConfig.index_source_code: bool \| None` (tri-state) | `ProjectConfig.mode: Literal["docs","code","general"]` |
| `set_project_dev_mode(project, enabled: bool, confirm_token)` | `set_project_mode(project, mode: str, confirm_token)` |
| `rag project dev-mode <id> on/off/inherit` | `rag project mode <id> docs\|code\|general` |
| `POST /api/projects/{id}/dev-mode` | `POST /api/projects/{id}/mode` |

**[from code: confirmed zero matches for `dev_mode`/`dev-mode` anywhere in `src/ragtools`; the only live route is `routes.py:498-528`]**. `set_project_dev_mode` and `/dev-mode` are not legacy-but-still-working — they **never existed in shipped code**. Any plugin documentation must use only the shipped names.

---

## 4. Plugin Gap Analysis

Answering the brief's specific questions directly:

- **What does the plugin currently support?** Markdown-only retrieval operations, project administration (ignore rules, reindex, status), diagnostics, and a maintainer doc-drift checker. See §2.
- **What does it not support from the new app capabilities?** All four named tools, the entire concept of per-project mode, code-vs-docs routing, and any secret-auditing workflow against indexed content. **[from plugin]**
- **Where is the plugin still docs-only / legacy-search-only?** Everywhere. `mcp-wiring.md` actively asserts a stale "three MCP tools" fact; the SKILL.md's tool-catalog source-of-truth pointer is a dangling file reference; every search workflow in the skill terminates in `search_knowledge_base`. **[from plugin]**
- **Does it have any concept of project mode/dev mode?** No — only the unrelated `install_mode` enum (binary install state) and `/project-focus` (which markdown corpus to search, not a code/docs toggle). **[from plugin]**
- **Does it expose any safety/audit workflow?** Only for its own diagnostic output, not for indexed project content. No workflow calls or even mentions `secret_audit`. **[from plugin]**

**Two findings beyond what was asked, both materially relevant to scoping this work:**

1. **`add_project` is now live in the MCP tool registry**, despite `docs/decisions.md` D-022 and `rules/mcp-envelope.md` §8 both stating, as a binding "non-goal," that the MCP *intentionally excludes* `add_project` because "arbitrary filesystem path from agent is an injection vector." The upstream app has apparently added it since D-022 was written (2026-04-18), which falsifies the premise of a still-binding plugin rule. This needs its own decision before the plugin touches it — it is out of this report's explicit scope (the brief named 4 tools, not 5) but should not be ignored when scoping the actual implementation work. **[from plugin + from KB]**
2. **`set_project_mode` reintroduces the exact pattern the plugin previously rejected.** `rules/mcp-envelope.md` §8 excluded `set_active_project()` specifically because "stateful MCP = confusion vector." `set_project_mode` is a different kind of state (persistent per-project config, not session-scoped "active project" pointer), but the new governing decision should say so explicitly rather than silently wire the tool in without addressing the precedent. **[from KB]**

---

## 5. P0/P1/P2/P3 Recommendations

### P0 — Safety and Correctness

**P0-1. Reframe and escalate the redaction-bypass finding — it is not Dev-Mode-scoped.**
- **Why it matters:** Independently confirmed in code: `QdrantOwner.run_full_index()`/`run_incremental_index()` (the watcher, `/api/index`, project-add auto-index, mode-change reindex, service-startup sync — i.e. *all routine indexing, for every mode*) never call `secret_scan.redact_text()`. Only the rare full-rebuild path does. This affects the plugin's 12 existing docs-only projects today, not just future code-mode adoption.
- **Expected plugin behavior:** Add a one-time, prominent advisory (e.g. surfaced by `/doctor` or `/doctor --full`) telling users: "ragtools' content-level secret redaction does not run on the routine indexing path as of v2.7.0 — run `secret_audit` against your existing projects and rotate anything it flags, regardless of whether you plan to use Dev Mode." This requires zero new tool grants (`secret_audit` is already an MCP tool; the plugin just needs to call it via a Claude-directed workflow per D-022's ops-tool carve-out) and zero new risk — it's read-only.
- **Required RAG app dependency:** None for the advisory itself. The underlying fix (route `owner.py`'s indexing through `indexer.index_file()`, or otherwise wire `redact_text`/`classify_source_class` into the production path) is the app team's, tracked as report §8.1.
- **Likely plugin files/areas affected:** `skills/ragtools-ops/SKILL.md` (new Phase), `commands/doctor.md`, a new `docs/decisions.md` entry.
- **Suggested tests:** Doc-lint test (extend `scripts/md_analyzer.py` pattern) asserting the advisory text is present in the relevant SKILL.md/command file; a content test asserting `secret_audit`'s output is never presented without the bypass caveat until a fixed-version floor is met.
- **Risk level:** Low to ship (read-only, additive). High to *omit* (current users have an active, undisclosed exposure).
- **Wait for app-side fix?** No — this is read-only awareness, ship it now, independent of the fix timeline.

**P0-2. Block `set_project_mode` from any plugin-wired write workflow until the app fix is confirmed.**
- **Why it matters:** Calling `set_project_mode` to narrow/widen into `code`/`general` triggers a reindex through the same non-redacting path. Enabling Dev Mode today would, with high probability, index code/config files (a richer secret-shaped surface than markdown) through the unfixed pipeline.
- **Expected plugin behavior:** No command, skill workflow, or hook may call `set_project_mode` to actually change a project's mode. The tool may be *documented* (so Claude understands what it is when a user asks) but not *wired into an enablement workflow*.
- **Required RAG app dependency:** Confirmed fix for report §8.1, ideally surfaced as a checkable capability/version marker (see P0-4).
- **Likely plugin files/areas affected:** `rules/mcp-envelope.md` (new tool entry, explicitly marked "documented, write-gated"), any future `/projects mode` subcommand spec (write the spec now, gate the wiring).
- **Suggested tests:** A safety-gate unit test that asserts the (future) mode-change code path raises/refuses when the app capability check is unmet, using a fixture response simulating an unfixed app version.
- **Risk level:** N/A (this is a "don't build it yet" recommendation, not new code).
- **Wait for app-side fix?** Yes — this is the one item in the whole report that must wait.

**P0-3. Write a new `docs/decisions.md` entry classifying all 5 newly-visible tools against the D-001/D-022 ops-vs-content boundary, before any are wired in.**
- **Why it matters:** This is the plugin's own established pattern (D-022 did exactly this the last time the MCP surface expanded). Without it, future contributors have no documented basis for "why is `search_project_context` Claude-direct but `secret_audit` plugin-orchestrated."
- **Expected plugin behavior:** A `D-032` (or next free number) decision stating: `search_project_context` and `find_definition` are content/discovery tools and fall under D-001's "Claude calls directly, plugin never wraps" boundary (same as `search_knowledge_base`); `secret_audit` is an ops/audit tool and falls under D-022's carve-out (plugin may build skill workflows around it); `set_project_mode` is a write/ops tool requiring the same write-tool discipline as `reindex_project` (§6.3/6.4 of `mcp-envelope.md`), *plus* the P0-2 app-version gate; `add_project`'s reappearance gets its own explicit note that it is **not** addressed by this decision and remains excluded pending separate review.
- **Required RAG app dependency:** None.
- **Likely plugin files/areas affected:** `docs/decisions.md`, `rules/mcp-envelope.md` (§8 non-goals list, §9 grant-checklist table, mode/cooldown/write-gate tables).
- **Suggested tests:** None (a documentation artifact) — but `docs/issues/` precedent suggests linking this decision from the CHANGELOG entry that ships it.
- **Risk level:** Low.
- **Wait for app-side fix?** No.

**P0-4. Add an app-capability/version gate the plugin can check before ever wiring a code/general mode change.**
- **Why it matters:** Without this, "wait for the app fix" has no enforcement mechanism — it's just a promise in a markdown file.
- **Expected plugin behavior:** Extend `rules/state-detection.md`'s existing state probe (already MCP-first via `index_status`) to also read the running ragtools version/capability via an already-granted tool (`get_config` or `system_health`). Maintain a plugin-side "known-fixed" floor. Until the maintainer confirms the app fix shipped and sets that floor, any code path that would call `set_project_mode` for narrowing/widening hard-refuses with a clear message.
- **Required RAG app dependency:** Ideally the app exposes a boolean capability flag (e.g. `redaction_enforced: true`) rather than forcing the plugin to parse version strings — **recommend filing this as an explicit ask back to the app team**, since version-string gating is brittle and this plugin's own D-011 versioning rule already prefers compatibility-band declarations over ad hoc parsing.
- **Likely plugin files/areas affected:** `rules/state-detection.md`, `rules/mcp-envelope.md`.
- **Suggested tests:** Unit test simulating both an unfixed-version response and a fixed-version response, asserting the gate flips correctly; a regression test for "missing capability field" (older app) defaulting to the safe/refuse side.
- **Risk level:** Medium (new logic, but fails closed by design).
- **Wait for app-side fix?** The *gate* should be built now; it simply stays closed until the fix lands.

### P1 — Dev Mode Awareness

**P1-1. Fix the two actively-misleading stale references before adding anything new.**
- **Why it matters:** `mcp-wiring.md`'s "three MCP tools" claim and the dangling `ragtools_mcp_doc.md` pointer will mislead a user or Claude asking "what tools does ragtools have" *today*, independent of this whole initiative.
- **Expected plugin behavior:** Update `mcp-wiring.md` to the current tool count/list (or point at `rules/mcp-envelope.md` as sole source of truth and stop duplicating the list at all); fix or remove the dangling doc pointer in `SKILL.md`.
- **Required RAG app dependency:** None.
- **Likely plugin files/areas affected:** `skills/ragtools-ops/references/mcp-wiring.md`, `skills/ragtools-ops/SKILL.md`.
- **Suggested tests:** `/sync-docs` or `md_analyzer.py` check that the tool list referenced in `mcp-wiring.md` matches `mcp-envelope.md`'s canonical table (single source of truth, no drift class repeats).
- **Risk level:** Low. **Wait for app fix?** No.

**P1-2. Surface a project's existing `mode` field — zero new grants required.**
- **Why it matters:** `project_status` already returns `mode` in its response (confirmed live: `mode: 'docs', stale: true, ...`). The plugin can show "what mode is this project in" today with a tool it's already allowed to call.
- **Expected plugin behavior:** `/projects` (status/listing) surfaces the mode column; `/doctor` mentions it when relevant.
- **Required RAG app dependency:** None — already shipped and already an allowed tool.
- **Likely plugin files/areas affected:** `commands/projects.md`, `skills/ragtools-ops/SKILL.md` (status-rendering section).
- **Suggested tests:** Snapshot test of `/projects` output formatting including the new field; a back-compat test for a `project_status` response *missing* `mode` (older app), which must render gracefully, not error.
- **Risk level:** Low. **Wait for app fix?** No.

**P1-3. Add routing guidance for `search_project_context` and `find_definition` as Claude-direct calls — not plugin wrappers.**
- **Why it matters:** Per D-001, the plugin doesn't mediate content search; the gap today is that Claude has no instruction telling it *when* these tools exist and apply. This is a documentation/skill change, not new code.
- **Expected plugin behavior:** Extend `rules/claude-md-retrieval-rule.md` (next version, e.g. v0.5.0) and `skills/ragtools-ops/SKILL.md` with a routing table (detailed in §7) telling Claude to call `search_project_context` directly for implementation-location questions when the target project's mode is `code`/`general`, and `find_definition` directly for symbol lookups — explicitly carrying over the app's own "discovery, not authority" framing for `find_definition` so Claude doesn't over-trust an empty result.
- **Required RAG app dependency:** None.
- **Likely plugin files/areas affected:** `rules/claude-md-retrieval-rule.md`, `skills/ragtools-ops/SKILL.md`.
- **Suggested tests:** None mechanical (prompt content) — covered by the safety-net in P1-1's doc-lint extension (no legacy names, no overclaiming).
- **Risk level:** Low (read-only call, Claude already has these tools granted at the MCP layer regardless of plugin awareness — this just makes usage *correct* instead of *absent*). **Wait for app fix?** No — these are read tools, unaffected by the redaction-bypass gate.

**P1-4. Document `secret_audit` as a recommended/required step around any future mode change — write the spec now, even though P0-2 blocks the enablement workflow itself.**
- **Why it matters:** When P0-2's gate eventually opens, the workflow needs to already exist rather than being designed under time pressure.
- **Expected plugin behavior:** A documented skill workflow: before approving a `code`/`general` mode change, run `secret_audit` on the project; after the first post-change index completes, run it again; surface results with the P0-1 bypass caveat attached for as long as that caveat applies.
- **Required RAG app dependency:** None to *write*; P0-2's gate controls when it can *execute* a real mode change.
- **Likely plugin files/areas affected:** `skills/ragtools-ops/SKILL.md`.
- **Suggested tests:** Workflow-level test once P0-2's gate is open; until then, none.
- **Risk level:** Low. **Wait for app fix?** The spec — no. Execution — yes (inherits P0-2).

### P2 — UX and Workflow Improvements

**P2-1. "Explain indexing status" — make `mode_indexes()` semantics legible.**
Extend `/doctor`/`/projects` to explain, in plain language, what file types a project's current mode actually includes (derived from the already-returned `mode` field), e.g. "code mode: source + config, no markdown/docs." Files: `commands/doctor.md`, `commands/projects.md`. Risk: low. No app dependency. No wait.

**P2-2. Graceful fallback messaging for the docs-mode warning.**
The app returns an explicit "Docs mode; source code is not indexed" warning when `search_project_context` is called against a docs-mode project. The plugin's routing guidance (P1-3) should anticipate this and instruct Claude to fall back to `search_knowledge_base` automatically rather than retrying or surfacing a raw error. Files: `rules/claude-md-retrieval-rule.md`. Risk: low. No app dependency. No wait.

**P2-3. Surface the reindex-after-mode-change behavior so users aren't confused.**
A mode change auto-triggers a background reindex app-side. Once P0-2 opens, the plugin's response to a mode change should say "reindexing started automatically; check `index_status`/`project_status` for progress" rather than prompting a redundant manual `reindex_project` call. Files: `skills/ragtools-ops/SKILL.md` (reindex decision tree). Risk: low. Wait for app fix (inherits P0-2 timing, but the wording can be drafted now).

**P2-4. Persistent `/doctor` warning banner while the redaction floor is unmet.**
Tie P0-4's version/capability gate into `/doctor`'s output directly, so the bypass risk is visible on every diagnostic run, not just discoverable by reading a decision doc. Files: `commands/doctor.md`, `rules/state-detection.md`. Risk: low. No wait (the banner logic ships now; it just naturally stops firing once the floor is met).

### P3 — Future Integrations

**P3-1. LSP pairing for `find_definition`.** Once the app's own framing ("discovery, not LSP replacement") is something the plugin actively reinforces (P1-3), consider whether a future hook or skill step should nudge toward an actual LSP/`mcp__ide__getDiagnostics`-style check for anything touching renames or cross-reference safety, rather than trusting `find_definition`'s leads. No app dependency beyond what's shipped; purely a plugin-side judgment call to design later. Risk: low, speculative — do not start until P1-3 ships and is observed in real use.

**P3-2. Eval harness parity.** The app's `scripts/eval_retrieval.py` has no service-aware dual-mode and fails outright when a service is already running (app-side item, report §6/P2-12). Nothing for the plugin to do until the app exposes a service-aware eval path; track only.

**P3-3. Richer code-metadata UI.** Once `source_class` is reliably computed in production (currently always defaults to `"owned"` due to the same redaction-bypass root cause — see §11), consider a `/projects files` or `/doctor` view breaking down a project's indexed content by `source_class` (owned/vendored/generated/secret) for triage. Blocked on the same app fix as P0-2; do not design the UI until the underlying field is trustworthy.

**P3-4. Revisit code-vs-docs routing independence from the app's internal detector.** The app's own intent detector (`feature_intent.detect_dev_intent`) is currently dead code in production (force_dev=True hardcoded). If the app later makes it load-bearing again or removes it, the plugin's routing guidance (P1-3) should **not** assume parity with whatever the app does internally — keep the plugin's routing rule self-contained (keyword/heuristic-based, mirroring the app's own CLAUDE.md table) rather than trying to mirror an internal implementation detail the plugin doesn't control. No action needed now beyond keeping this principle in mind when P1-3 is written.

**P3-5. `add_project`'s reappearance.** Out of this report's explicit scope, but flagged because it surfaced during inspection: a dedicated decision (separate from P0-3's) is needed before the plugin does anything with `add_project`, given it directly contradicts a still-written "never add this" rule. Do not implement.

---

## 6. Recommended Tool/Command Surface

| User-facing surface | Internal RAG tool/endpoint | When Claude should use it | When Claude should avoid it | Expected output shape |
|---|---|---|---|---|
| **Project mode status** (extend `/projects` listing/status; no new command, per D-021) | `project_status(project=...)` / `list_projects()` — already-granted ops tools | Anytime a user asks "what mode is project X in," or as part of routine `/projects` output | N/A — read-only, always safe | Existing project status block + a `mode: docs\|code\|general` line, with graceful omission if the field is absent (older app) |
| **Set project mode** (new `/projects mode <id> <docs\|code\|general>` subcommand spec — gated, do not wire until P0-2 opens) | `set_project_mode(project, mode, confirm_token)` | Only on an explicit, unambiguous user request to enable/change code indexing for a named project, after the P0-4 capability gate passes and a typed-verbatim confirmation (mirroring `reindex_project`'s existing discipline) | Never inferred from a vague request like "can you search the code" — that should route to a *read* tool, not a mode change. Never while the P0-4 gate is closed. Never without `confirm_token == project` for narrowing transitions | Confirmation echo of old/new mode + "reindex started automatically, check status via `index_status`" |
| **Search project context** (no plugin wrapper — Claude calls the MCP tool directly, per D-001) | `search_project_context(query, project, top_k)` | Implementation-location questions ("where is X implemented," "how does module Y work") when the target project's mode is `code`/`general` | When the project is `docs`-mode (will return a docs-mode warning — fall back to `search_knowledge_base`, see P2-2) or for conceptual/process/decision questions (those stay on `search_knowledge_base` per D-029) | Layered Relevant Files / Existing Implementation sections, code-first ranked |
| **Find definition** (no plugin wrapper, Claude-direct) | `find_definition(symbol, project, top_k)` | "Find definition of X," "where is class/function Y declared" — as a first-pass lead | As the sole basis for a rename/refactor/reference-safety decision (must pair with `Read`/`Grep` or actual LSP); do not treat an empty result as proof the symbol doesn't exist | File:line lead(s), or an explicit "no definition found" — always followed by a verification step in Claude's own response, not surfaced as final |
| **Run secret audit** (new skill-workflow step / `/projects audit <id>` or a phase inside `/doctor --full`) | `secret_audit(project=...)` | Before approving any mode change to `code`/`general` (once P0-2 opens); periodically for any `code`/`general` project via `/doctor --full`; **immediately, for all existing docs-mode projects too**, per P0-1, independent of Dev Mode plans | Never present a "clean" result as an unconditional safety guarantee while the P0-1 bypass is unfixed — always carry the caveat | List of `file:line` + rule name hits, no values; explicit caveat line while the gate (P0-4) is unmet |
| **Explain indexing status** (extend `/doctor`/`/projects`, no new command) | Derived from `project_status`'s `mode` field + the plugin's own static knowledge of `mode_indexes()` semantics | "Why isn't my code searchable," "what does code mode actually index" | N/A | Plain-language explanation of what file types the current mode includes |
| **Trigger/recommend reindex** (existing `reindex_project` workflow, extended messaging only) | `reindex_project` (existing, already gated) | Manual reindex requests; after a mode change, just point at `index_status` instead of re-triggering | Don't issue a redundant manual reindex right after a mode change already auto-triggered one | Existing reindex-decision-tree output, plus a one-line note when a mode-change-triggered reindex is already in flight |
| **Fallback to docs-only search** (encoded in the P1-3 routing rule, not a separate command) | Automatic: on docs-mode warning or tool-not-granted, fall back to `search_knowledge_base` | Any time `search_project_context` signals it can't help (docs-mode project, ungranted tool, older app without the endpoint) | N/A — this *is* the avoidance path | Same as a normal `search_knowledge_base` call, with a one-line note on why the fallback happened |

---

## 7. Agent Routing Rules

Routing decisions stay **rule-based and Claude-direct**, not plugin-mediated — consistent with D-001's binding boundary that content/discovery tools are Claude's to call, never the plugin's to wrap.

1. **Internal process/decision/convention questions** ("How do I configure this project?", "what's our ignore policy?") → `search_knowledge_base`. Unaffected by any of this work (D-029's existing source-of-truth routing).
2. **Implementation-location questions** ("Where is auth implemented?", "show me the code that does X") → check the target project's `mode` (via `project_status`, already cheap and granted). If `code`/`general` → `search_project_context`. If `docs` or unknown → do **not** guess; either fall back to `search_knowledge_base` or surface "this project isn't code-indexed — want me to check about enabling it?" (which routes into the P0-2-gated mode-change path, never silently).
3. **Symbol/definition lookups** ("Find definition of X") → `find_definition` first as a cheap lead, always paired with a `Read`/`Grep` confirmation or an explicit "verify with your editor's LSP for anything safety-critical" caveat — never presented as sole authority, mirroring the app's own docstring framing.
4. **"Enable dev mode" / "turn on code search for this project"** → `set_project_mode`, but **only** after: (a) the P0-4 capability gate passes, (b) `secret_audit` has been run/recommended, (c) explicit typed-verbatim user confirmation with `confirm_token == project` for narrowing transitions (mirrors the existing `reindex_project` discipline in `rules/mcp-envelope.md` §6.3/6.4). Never inferred from an ambiguous "can you search my code" request.
5. **"Check whether indexed secrets exist"** → `secret_audit`, always available read-only, no gate on the *call* itself — only a gate on trusting a clean result as an unconditional guarantee while P0-1 is open.
6. **Ambiguous queries that could be either code-shaped or decision-shaped** → default to `search_knowledge_base` (the conservative, already-trusted path). Do not silently assume code search was wanted — this mirrors D-029's existing "don't over-trust retrieval" stance.
7. **The plugin itself (Python hook/script layer) never calls any search-shaped tool on Claude's behalf.** Its only role is (a) injecting the routing guidance above via the CLAUDE.md retrieval rule and SKILL.md, and (b) gating/auditing the one write tool in this set (`set_project_mode`) the same way it already gates `reindex_project`.

---

## 8. Safety Gate for Dev Mode

**Reframe first: the gate isn't really "Dev Mode is risky," it's "the indexing pipeline doesn't redact secrets today, for any project, and Dev Mode increases the blast radius by adding richer file types."** Both halves matter to the gate design.

- **Should Dev Mode be hidden, warned, guarded, or blocked?** **Guarded**, not hidden, not unconditionally blocked. Hidden-entirely defeats the purpose of D-001/D-022 (the plugin exists to wrap risk with guidance, not to pretend the underlying MCP tool doesn't exist — a user can already call `set_project_mode` directly with zero plugin awareness today, which is worse than guided friction). Unconditionally blocked is overly blunt — a project with no real secrets is harmless to switch to code mode, and engineering work shouldn't be frozen indefinitely on a maintainer-controlled timeline with no override path. **Guarded** means: P0-4's capability gate refuses by default, requires the maintainer to explicitly raise the floor once the app fix is confirmed, and even then requires the full confirmation ceremony in §7 rule 4.
- **Should the plugin require `secret_audit` before enabling Dev Mode?** Yes — both before (audit existing markdown content, which is *also* exposed by the same bypass) and immediately after the first post-change index (audit the newly-indexed code/config content). This is P1-4/§7 rule 4.
- **Should it display warnings when code indexing is enabled?** Yes, persistently, via `/doctor` (P2-4) for as long as the redaction-bypass floor is unmet — not a one-time confirmation dialog that's then forgotten.
- **Should it refuse to enable Dev Mode on unsafe app versions?** Yes — this is P0-4, and it should fail closed: any ambiguity (missing capability field, unparseable version, older app) defaults to refuse, not allow.
- **What app capability/version checks are needed?** Ideally a boolean capability flag from the app (e.g. via `get_config`/`system_health`) rather than version-string parsing — recommend this as an explicit ask back to the app team, since the plugin's own D-011 versioning convention already prefers compatibility-band declarations over brittle string matching. Until such a flag exists, the plugin must hard-block (no known-fixed version exists as of this report) rather than guess.
- **One more thing the gate must say explicitly, because it's true today and users deserve to know it regardless of Dev Mode adoption:** *existing* docs-mode projects are not exempt from the underlying bypass. The gate's warning copy should not imply "this only matters if you turn on Dev Mode."

---

## 9. Backward Compatibility Strategy

- **Preserve docs-only behavior:** D-001's "plugin never wraps `search_knowledge_base`" stays untouched. Every recommendation above is additive — a new SKILL.md phase/section, a new optional `/projects` subcommand spec, new advisory text — nothing changes behavior for a project that stays in `docs` mode (the default, and the mode all 12 currently-indexed projects are in today).
- **Avoid breaking existing users:** Version-gate all new commands/workflows behind a plugin version bump (e.g. `0.17.0`) with a CHANGELOG entry, per the plugin's own established convention (every prior capability expansion — v0.5.0 for D-022, v0.15.x for the hook-launcher rework, v0.16.0 for PL1 diagnostics — followed this pattern).
- **Projects/installs that don't support the new mode API** (an older self-hosted ragtools instance pre-2.7.0): the plugin must detect this via its existing MCP-mode-first probing in `rules/state-detection.md` (tool-not-found on `set_project_mode`/`search_project_context`/`find_definition`/`secret_audit`, or a `project_status` response missing the `mode` field) and degrade gracefully to today's behavior — never error hard. This is a direct extension of the plugin's existing tool-grant-awareness and 3-tier fallback philosophy, not new design.
- **Older app docs/CLAUDE.md referencing superseded names** (`set_project_dev_mode`, `/dev-mode`): the plugin's *own* new documentation must never introduce these names — they never shipped (§3). If useful, add a one-line aside that older ragtools docs/CLAUDE.md may still reference the superseded interface and should not be trusted over the live MCP tool signatures — this is the same "RAG is reference, not sole truth" principle the plugin already codified in D-029, applied reflexively to the app's own stale docs.

---

## 10. Suggested Tests

- **Doc-lint / drift checks** (extend `scripts/md_analyzer.py` / `/sync-docs` patterns): assert the P0-1 advisory text and bypass caveat are present in the relevant SKILL.md/command files; assert no occurrence of the legacy names `set_project_dev_mode` or `/dev-mode` exists anywhere in new plugin docs; assert `mcp-wiring.md`'s tool list matches `mcp-envelope.md`'s canonical table (single source of truth, no repeat of the staleness class found in §2).
- **State-detection / graceful-degradation tests:** simulate an older app (tool-not-found on the 4 new tools, or `mode` missing from `project_status`) and assert the plugin falls back to current behavior without error.
- **P0-4 capability-gate tests:** simulate both an unfixed-version response and a (future) fixed-version response and assert the gate flips correctly; simulate a missing/unparseable capability field and assert it defaults to refuse.
- **Write-discipline tests for the (future, gated) `set_project_mode` wiring:** typed-verbatim confirmation + `confirm_token == project` enforcement for narrowing transitions, mirroring whatever existing tests cover `reindex_project`'s confirm-token discipline today.
- **`/projects` status rendering tests:** snapshot test including the new `mode` column; back-compat test for a response missing the field.
- **Hook-matcher verification (open item, not yet a test):** confirm whether Claude Code's `PreToolUse` hook matcher syntax can target an MCP tool name (e.g. `mcp__plugin_rag_ragtools__set_project_mode`) before assuming a future hook-level gate on `set_project_mode` is even buildable — `hooks/hooks.json`'s only current `PreToolUse` matcher is the literal string `"Bash"`, and this report did not verify MCP-tool-name matcher support one way or the other. Resolve this before committing to any P3 hook-based enforcement design.

(App-side test gaps are out of this report's scope to fix, but worth naming since the plugin's safety gate depends on them eventually closing: `tests/test_owner.py` exercises `run_full_index`/`run_incremental_index` but asserts no redaction/`source_class` behavior — the app team should add a regression test asserting `redact_text` is actually invoked on the production write path before the plugin's P0-4 floor can be safely raised.)

---

## 11. Risks and Open Questions

- **The redaction bypass is broader than "a Dev Mode risk."** It is a live, present-tense exposure for every currently-indexed project, confirmed independently in code, not just claimed by the report. Treat P0-1 as urgent and decoupled from the rest of this initiative's timeline.
- **`source_class` is also silently broken in production** (always defaults to `"owned"`) for the same root cause as the redaction bypass — both are downstream of `owner.py` bypassing `indexer.index_file()`. Any future UI surfacing `source_class` (P3-3) inherits this risk and should stay blocked on the same fix.
- **A narrow secondary leak exists even in normal tool usage, not just direct DB/audit access:** `find_definition`'s `signature` field is sourced verbatim from the stored (potentially unredacted) payload without a `redact_text` pass — a function/class declaration line containing a secret-shaped default parameter value could leak through a completely ordinary `find_definition` call, not just through `secret_audit` or raw database access. Mitigating factor: serve-time redaction in `Searcher.search()` does cover everything routed through normal *search*, including `search_project_context`'s underlying pipeline — this gap is specific to `find_definition`'s direct-payload `signature` field.
- **The exposure is local-disk, not network-exposed by default** (the product is explicitly local-first, embedded Qdrant) — this lowers but does not eliminate severity; secrets baked into a local vector index are still a data-at-rest hygiene problem (backups, multi-user machines, embedding computation itself).
- **`add_project` is live but contradicts a written exclusion rule** — unresolved, out of this report's explicit scope, flagged in P3-5. Any implementation pass on this report's recommendations should audit the *full* live MCP tool list (not just the 4 named tools) before finalizing `mcp-envelope.md`'s updated tables, since the registry has already drifted further than the brief's scope.
- **`set_project_mode` reintroduces a previously-rejected pattern** (`set_active_project` was excluded for being a "confusion vector"); P0-3's new decision should explicitly address this precedent rather than silently proceeding.
- **Open question: does Claude Code's `PreToolUse` hook matcher support MCP tool-name targeting?** Unverified in this analysis (see §10) — relevant to whether any future hook-level enforcement on `set_project_mode` (beyond skill-level guidance) is even architecturally possible.
- **Open question: no committed timeline exists for the app-side §8.1 fix.** This report cannot commit the plugin to a ship date for P0-2/Increment 2 — only to the gate design that makes the eventual wiring safe whenever the fix lands.
- **Open question: will the app expose a clean capability flag, or will the plugin be forced into version-string parsing?** Recommend escalating this ask now rather than discovering the answer mid-implementation.
- **Watcher nested-project misrouting (§3 table)** was not independently re-verified in code by this analysis (only the redaction-bypass claim was independently traced) — treat as high-confidence per the report but flag it as report-sourced, not code-confirmed, if it later matters for a plugin-side recommendation (it doesn't directly today, since the plugin has no watcher-level logic of its own).

---

## 12. Final Recommendation

**Split into two increments. Implement Increment 1 now. Do not start Increment 2 until the app-side redaction-bypass fix (report §8.1) is confirmed shipped.**

### Increment 1 — ship now (target `v0.17.0`)
Documentation, governance, and read-only awareness only. Zero new write capability, zero new risk surface, closes the "stale docs actively mislead" gap immediately:
- P0-1 (secret-audit advisory for **all** existing projects, not just future Dev Mode ones — this is the most urgent item in the whole report)
- P0-3 (new `docs/decisions.md` entry classifying the 5 newly-visible tools)
- P0-4 (build the capability gate now; it simply stays closed)
- P1-1, P1-2, P1-3, P1-4 (fix stale docs, surface existing `mode` field, add Claude-direct routing guidance for `search_project_context`/`find_definition`, write — but don't yet execute — the `secret_audit`-around-mode-change spec)
- P2-1, P2-2, P2-4 (status explanation, fallback messaging, persistent `/doctor` banner)

### Increment 2 — only after P0-2's gate condition is met
- Wire `set_project_mode` into a guarded `/projects mode` subcommand with the full ceremony from §7 rule 4 and §8
- P2-3 (reindex-after-mode-change messaging)
- P3-3 (richer `source_class` UI), once that field is independently confirmed correct in production

### What must not be implemented yet, under any circumstance, until the gate opens
- Any code path that lets Claude or the plugin call `set_project_mode` to actually change a real project's mode
- Any plugin messaging stating or implying "secrets are safely redacted" or "your code is safe to index" in unconditional terms
- Any wiring of `add_project` (separate, even-less-vetted issue — P3-5)
- Any hook/automation that changes a project's mode without an explicit, typed user confirmation

This sequencing mirrors the brief's own instinct exactly: the plugin should become more aware now, but awareness must not outrun the app's actual safety guarantees. The single most important deliverable in Increment 1 is not a new command — it's telling existing users, today, that content already in their local index may not be redacted the way they were told it would be.
