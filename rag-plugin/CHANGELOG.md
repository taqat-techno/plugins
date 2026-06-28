# Changelog

All notable changes to `rag-plugin` are documented here. Format is loosely based on [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.15.0] — 2026-06-29 — `/report` files GitHub issues automatically after one yes/no confirmation (D-030)

`/report` no longer stops at copy-paste issue bodies. By default it now generates the local artifacts, shows the routed issue plan (repo + title), asks **one** confirmation — `Create GitHub issue(s) now? [yes/no]` — and on `yes` files the issues via the GitHub CLI. Default behavior with no confirmation is unchanged for `--dry-run`, and creation falls back to local-only when `gh` is unavailable. **No hooks; no changes to `/doctor` or any destructive command; local artifacts preserved; redaction unchanged.**

### Added

- **`scripts/rag_report.py`** — a deterministic, unit-tested GitHub-issue layer (all `gh` calls funnel through one mockable `_run_gh`):
  - `issue_fingerprint()` — stable SHA-256(sorted non-info finding IDs)[:12]; embedded in each body as `<!-- rag-plugin-report:fingerprint:<hash> -->`.
  - `build_issue_meta()` — single source of truth for repo/title/labels/fingerprint (used by both the body renderer and the plan, so they can't drift).
  - `route_findings()` — routes every finding to its issue **by `target`, merging both source lists**, and surfaces any unroutable finding instead of silently dropping it (fixes the old end-of-pipeline silent-drop).
  - `build_issue_plan()` — writes `issue-plan.json` + clean `_issue-body-<target>.md` bodies (copy-paste preamble stripped, marker retained).
  - `gh_available()`, `find_existing_open_issue()` (duplicate search), `create_issue()`, `do_create()` — dedup-then-create with a graceful local-only fallback.
  - New flags: `--create` (file from the plan via `gh`), `--from <dir>` (create from an existing report dir without re-scanning), `--dry-run` (legacy local-only; always wins over `--create`).
- **Two new local artifacts** per run: `issue-plan.json` and `_issue-body-{rag,plugins}.md` (9 files total, was 6).
- **`scripts/test_rag_report.py`** — 16 new tests: rag→`taqat-techno/rag` / plugin→`taqat-techno/plugins` routing, cause-based re-route, fingerprint stability/uniqueness, dedup-prevents-duplicate, create-when-`gh`-available (mocked), `gh`-unavailable→local-only fallback, and **dry-run / default generation create no issue**. No test ever touches real GitHub (mocked `_run_gh`).
- **`docs/decisions.md`** — D-030.

### Changed

- **`commands/report.md`** — documents the confirmation flow, `--dry-run`, the fallback, duplicate prevention, and the `taqat-techno/*` account-switch around creation; `argument-hint` gains `--dry-run`; `allowed-tools` gains `Bash(gh:*)` (the single change that enables creation). Updated the "What it does NOT do" boundaries (no silent/un-confirmed creation; dedup; redaction unchanged).
- **`README.md`** — brought current to v0.15.0: status block, the CLAUDE.md-rule (v0.4.0 source-of-truth routing) and retrieval-hook (≥0.65 + source-of-truth reminder) descriptions, the command catalog (`/report` auto-filing + the previously-missing `/md-rag-enhance` row), the Quick-start / Troubleshooting command names (the absorbed `/rag-status`, `/rag-repair`, `/rag-upgrade` now map to `/doctor` and `/setup`), and the D-001..D-030 / 3-skills references.

### Fixed (low-risk routing)

- **Cause-based routing for transport faults** (`synthesize_findings`): `P-012` (MCP-error phrases) re-targets to the **rag** app when `service_mode ∈ {DOWN, BROKEN}` (the `rag serve` MCP server is the app, not plugin wiring); `P-010` (skipped retrieval) re-targets to **rag** when the service was not UP at scan time (retrieval was impossible because the app was down) — no longer blamed on the plugin.

### Validation

- `python validate_plugin.py rag-plugin` → 0 errors.
- `python scripts/rag_report.py --self-test` → pass.
- `python scripts/test_rag_report.py` → 40 tests OK (24 existing + 16 new).
- `python -m py_compile scripts/rag_report.py scripts/test_rag_report.py` → OK.

## [0.14.1] — 2026-06-28 — Command-surface clarity & source-of-truth consistency (docs/metadata only)

Documentation and metadata consistency pass from the command-surface review. **No behavioral or control-flow changes** — every command behaves exactly as before; only descriptions, illustrative examples, and version strings were corrected.

### Fixed

- **`commands/report.md`** — the frontmatter `description` was truncated mid-sentence (`"… (target repo..."`), which both misrepresented the command and risked poor auto-invocation matching. Replaced with a complete, accurate description that states it produces local reports + copy-paste issue bodies routed to `taqat-techno/rag` (application) and `taqat-techno/plugins` (plugin), and **never uploads or creates issues**.
- **`commands/config.md`** — corrected three internal inconsistencies surfaced by the review: (1) the `mcp-dedupe status` example showed the canonical plugin-level entry as `python …/rag_mcp_launcher.py [launcher present]`, contradicting the command's own DIRECT-SPAWN assertion and the real `.mcp.json` — now shows `rag serve [direct-spawn]`; (2) the `status` dashboard mock-up hardcoded `rag-plugin v0.3.0` / `CLAUDE.md rule: INSTALLED v0.2.0` — bumped to `v0.14.1` / `v0.4.0` to match reality; (3) the telemetry-era `## Behavior` and `## Required steps` sections read as if `/config` only had three telemetry subcommands — added a scope note clarifying they detail the `telemetry` group only and that the other three groups dispatch to their own sections (the parse table now lists the dispatch row instead of implying `claude-md`/`mcp-dedupe`/`hook-observability` are rejected).
- **`scripts/rag_report.py`** — version drift: the module docstring and HTTP `User-Agent` said `0.8.0` while `REPORT_VERSION` was `0.9.0`. Docstring corrected to `0.9.0`; the `User-Agent` now derives from `REPORT_VERSION` (`f"rag-plugin-report/{REPORT_VERSION}"`) so it can never drift again — single source of truth.

### Notes

- Higher-risk items from the command-surface review (e.g. `/report` auto-issue-creation hybrid mode, routing-classification disambiguation for MCP/transport faults, redaction hardening, DRY extraction of the shared state-detection / F-001 version gate) are intentionally **deferred as recommendations**, not implemented here.

### Validation

- `python validate_plugin.py rag-plugin` → 0 errors.
- `python scripts/rag_report.py --self-test` → pass.

## [0.14.0] — 2026-06-28 — Retrieval rule routes by source of truth (RAG is reference, not sole truth)

The always-loaded retrieval rule was RAG-first and one-directional: it told Claude to search the knowledge base before saying "I don't have information," but treated a HIGH-confidence (≥0.7) hit as terminal truth, routed implementation questions to indexed code snapshots, and sent current vendor/API/pricing/security questions to "answer directly" from memory with no verification lane. This release reframes the KB as **project memory/reference, not the sole source of truth** and routes each question to the source that actually owns its answer. Internal RAG-first behavior is preserved.

### Changed

- **`rules/claude-md-retrieval-rule.md`** — managed block bumped `v=0.3.0` → `v=0.4.0`. The KB is reframed as a point-in-time internal snapshot ("one source, not the final word"); the hard search-first rule is scoped to **internal** questions (process / decision / convention / requirement / prior research). The "When to call the MCP" table is replaced with a **route-by-source-of-truth** table adding two lanes: code/runtime/tests for implementation behavior, and official docs/web (context7 / WebFetch) for current vendor/API/pricing/security. Answering discipline is now source-type-aware with a HIGH-band freshness gate, an explicit **KB-vs-code/docs conflict-surfacing** rule (code/docs win), and per-claim **source-type tagging** (`[from KB]` / `[from code]` / `[from official docs]` / `[assumption]`). Section 0a (operational/machine-state override) is preserved byte-for-byte. Frontmatter `version` and the injection-logic version reference bumped to `0.4.0`.

### Fixed

- Corrected the MCP tool namespace from the non-existent `mcp__plugin_rag-plugin_ragtools__*` to the actual `mcp__plugin_rag_ragtools__*` (the plugin's `name` in `plugin.json` is `rag`) in **both** the injected block (wildcard fallback `mcp__*__ragtools__*` retained) and the retrieval-reminder hook's injected reminder string (`hooks/prompt_retrieval_reminder.py`), which had no fallback and therefore named a tool that could not resolve.
- **`hooks/prompt_retrieval_reminder.py`** — reworded the injected reminder (string-only; **no logic, gating, or behavior change**) to match the v0.4.0 source-of-truth routing: the KB is project memory/reference, not sole truth; search first for *internal* questions, but verify current vendor/API/pricing/security facts against official docs/web, inspect live code/runtime for actual behavior, surface KB-vs-code/docs conflicts, and report each claim's source type. Dropped the prior one-sided "search-first / harness-enforced layer" framing.
- Refreshed stale illustrative `v=0.2.0` marker strings in `commands/config.md` to `v=0.4.0` (illustrative only; install reads the real marker dynamically from the bundled rule).

### Added

- **`skills/ragtools-ops/SKILL.md`** — a "Source discipline (defer to the live product)" section: bundled references are leads; the live product (`rag --help`, running service, upstream repo) is truth; surface doc-vs-product conflicts and state which source was used. Mirrors the rule's Section 0 routing.
- **`docs/decisions.md`** — D-029 records "RAG is reference, not sole truth," the first decision treating **over-trust** of retrieval as a failure mode (D-016 / D-017 / D-027 only addressed under-retrieval).

### Upgrade note

- Existing installs do **not** auto-upgrade. Run **`/config claude-md install`** once (or `/setup` / `/doctor`) to splice the `v0.4.0` block over the `v0.3.0` one in `~/.claude/CLAUDE.md`. The marker version bumped, so install performs an upgrade splice instead of a version-matched no-op.

### Out of scope (deferred)

- Making the `doctor.md` P-RULE and `report.md` "missed-retrieval" / "skipped-retrieval" heuristics source-aware so a correct code/docs-sourced non-retrieval isn't flagged as a miss.
- Optional `skills/knowledge-routing/SKILL.md` (a trigger-gated richer-detail router that references this rule); not needed for the always-on guarantee.

### Validation

- `python validate_plugin.py rag-plugin` → 0 errors.

## [0.13.2] — 2026-05-31 — Defer generic MCP diagnosis to claude-env-doctor

### Added

- `commands/doctor.md` now defers GENERIC "MCP not loading" diagnosis (user-dotfile config location, concurrent-session clobber, spawn/version ladder) to the claude-env-doctor plugin; ragtools-specific checks stay local. Avoids duplicated environment docs.

### Validation

- `python validate_plugin.py rag-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [0.13.1] — 2026-05-08 — Report-engine fixes for `scale.level="over"` and false-positive session signals

Patch release surfacing two P0 issues found in external user diagnostics (2026-05-06).

### Fixed

- **`scale.level="over"` no longer reported as A-OK / healthy** (`scripts/rag_report.py`). The synthesizer recognized `approaching` (A-012 medium) and `warning|critical|near-limit` (A-013 high) but treated `over` (collection past the hard limit) as unrecognized and fell through to the A-OK info-only verdict. A real user's report on 2026-05-08 had `scale.level="over"` with 26,242 points (31% past the 20k hard limit) and the banner read "ragtools application looks healthy on this device." Fix introduces **A-014 (high)** — `local Qdrant collection over hard limit` — emitted whenever `scale.level ∈ {over, exceeded, past-limit}`. Recommendation lists the three-step remediation order from `skills/ragtools-ops/references/risks-and-constraints.md`: (1) tighten `ignore_patterns`, (2) remove unnecessary indexed projects, (3) migrate to Qdrant server mode if the large index is intentional.
- **Session-scan classifier no longer matches generic shell output as `mcp-error` / `port-in-use` / `connect-refused`** (`scripts/rag_report.py:_SIGNAL_PATTERNS`). Verified false positives in the 2026-05-06 diagnostics: `imPORT was in use of ...` was matching `port-in-use`; `Exit code 2\ntotal 12\ndrwxr-xr-x` was matching `mcp-error`; ordinary `ls -la` listings were matching `connect-refused`. Patterns are tightened to require concrete failure idioms:
  - `port-in-use` requires `EADDRINUSE`, `Address already in use`, or `port <2-5 digits> ... is/already in use`.
  - `connect-refused` requires `ECONNREFUSED`, `Connection refused`, or `HTTPConnectionPool ... refused/Failed to establish/Max retries`.
  - `mcp-error` requires `MCP server failed/crashed/disconnected/not responding`, `STARTUP_FAILED`, `Failed to (re)connect to plugin:rag`, `MCP tools/list failed/timeout`, or `[MCP] error/failed`. Generic shell prose no longer matches.

### Added

- `scripts/test_rag_report.py` (new): 24 unit tests covering scale-band classification (including `over`), classifier false-positive regressions (using verbatim snippets from the 2026-05-06 user report), and classifier positive-match coverage for `EADDRINUSE`, `ECONNREFUSED`, `[RAG ERROR]`, `MCP server failed`, `Failed to reconnect to plugin:rag`, `tools/list timeout`, and `STARTUP_FAILED`.
- `skills/ragtools-ops/references/risks-and-constraints.md`: new "Qdrant local-mode `scale.level=\"over\"`" subsection documenting what the band means, why local-mode degrades there, and the three-step remediation order with rationale for the ordering.

### Verification

- `python rag-plugin/scripts/test_rag_report.py` → 24/24 OK.
- `python rag-plugin/scripts/test_project_focus.py` → 30/30 OK (existing v0.13.0 tests).
- `python rag-plugin/scripts/project_focus.py self-test` → all checks pass.
- `python plugins/validate_plugin_simple.py rag-plugin` → 0 errors.

### Out of scope (deferred)

- `--json` flag on plugin commands.
- `--ci` flag on `/rag:report`.
- `project_focus` block in diagnostics.
- App-side findings about `/health` JSON shape, `rag service status` exit codes, or `rag doctor --json`. These remain backend concerns to file at `https://github.com/taqat-techno/rag`.
- Snippet-locality fix (showing the matched substring in session-scan examples instead of the buffer head). Tracked separately.

## [0.13.0] — 2026-05-08 — Per-workspace project focus (D-028, supersedes D-025 §1)

**Breaking (auto-migrated):** the `~/.claude/rag-plugin/state/project-focus.json` state file format changed from v1 single-record to v2 workspace-keyed map. Migration runs automatically on first read; the original v1 file is backed up to `project-focus.v1.bak.json` for manual rollback.

### Why this exists

In v0.9.x → v0.12.x, focus was a single global record. Setting `/project-focus` in workspace A meant every other workspace silently inherited that focus — every prompt in workspace B injected a "search only project A" reminder, and Claude would dutifully filter out B's own knowledge. The leak was documented in `LESSONS.md` (2026-05-08) and the prior D-025 design depended on it.

v0.13.0 closes the leak by storing focus as a **map keyed by the normalized workspace root** (git root or cwd) plus an optional explicit **global** record. Workspace records do not affect other workspaces. Global is opt-in via `--global`, never inherited.

### What changed

- `scripts/project_focus.py`
  - New v2 state schema: `{schema_version: 2, workspaces: {<key>: <record>}, global: <record>|null}`.
  - New `resolve_workspace_key(cwd)` — git root or cwd, normalized.
  - New `resolve_effective_focus(bundle, key)` returning `(record, source)` where source ∈ `{workspace, global, other-workspace-only, none}`.
  - New `clear_workspace`, `clear_global`, `clear_all` with corresponding subcommand variants.
  - New `set --global <name>` flag — explicit global focus. Auto-detect is rejected for global (must name a project).
  - v1 → v2 auto-migration on read: prefers `_norm(git_root_at_set)` → falls back to `_norm(cwd_at_set)`. If neither exists or resolves to a real directory, focus is **disabled** during migration and the user is prompted to rerun `/rag:project-focus`. v1 records are never auto-promoted to global.
  - One-time backup at `project-focus.v1.bak.json` before first migration; never overwritten.
  - `cmd_status` now prints `workspace_key`, `workspace_focus`, `global_focus`, `effective_focus`, `effective_source`, all known workspaces, and `migrated_from_v1_at` / `migration_log`.
- `hooks/project_focus_inject.py`
  - Reads v2 state via the script's loader (so migration runs on first hook fire).
  - Resolves effective focus by current cwd.
  - **Workspace source** → standard reminder.
  - **Global source** → reminder begins with `EXPLICIT GLOBAL FOCUS` and tells Claude the focus applies because of `--global`, not because of cwd match.
  - **Other-workspace-only source** → injects a neutral notice that does NOT include the foreign project's name. Phrases like "not applied here" are literal so Claude cannot accidentally use foreign focus.
  - Honors `RAG_PLUGIN_FOCUS_STATE_FILE` env var for test harnesses.
- `scripts/test_project_focus.py` (NEW)
  - 30 unit tests covering migration, workspace key resolution, CRUD, effective-focus resolver, hook injection paths, and a regression test for the cross-workspace leak.
- `commands/project-focus.md`
  - Rewritten subcommand table.
  - Replaced "Cross-project leak warning" with "Per-workspace focus model".
  - New machine-local + Syncthing guidance.
  - Manual validation checklist updated with leak-regression and explicit-global tests.
- `docs/decisions.md`
  - Added **D-028** (per-workspace focus + explicit global, supersedes D-025 §1).
  - Added **RFC-001** placeholder for future MCP-level enforcement (out of scope for this release).

### Migration notes

Existing v1 state files migrate cleanly:

```
v1 record  →  workspaces[_norm(git_root_at_set or cwd_at_set)]
```

If you used the old global behavior intentionally and want to keep it, run `/rag:project-focus set --global <name>` after the upgrade. v1 records are not auto-promoted to global by design — auto-promotion would recreate the leak.

If migration disables your focus (because the v1 record had no usable cwd anchor), `/rag:project-focus status` will show `migration_log` explaining why. Rerun `/rag:project-focus` to re-establish.

### Rollback

```
cp ~/.claude/rag-plugin/state/project-focus.v1.bak.json \
   ~/.claude/rag-plugin/state/project-focus.json
```

then downgrade the plugin to v0.12.x. The `.bak` is never overwritten so this is safe.

### Verification

- `python rag-plugin/scripts/test_project_focus.py` → 30/30 OK.
- `python rag-plugin/scripts/project_focus.py self-test` → all checks pass.
- `python plugins/validate_plugin_simple.py rag-plugin` → 0 errors.

### Out of scope (not in this release)

- Auto-detect-on-prompt (deferred to potential Phase 2).
- MCP server-side default `project=` enforcement (RFC-001).
- `clear --workspace <key>` for explicit cleanup of stale Syncthing entries.

## [0.12.0] — 2026-05-01 — `/rag:report` becomes maintainer-issue-ready

The `/rag:report` command was producing thin reports because the report engine had three latent bugs against ragtools v2.5.x and the GitHub-ready issue body it emitted was too sparse for a maintainer to triage without follow-up. v0.12.0 fixes all three bugs and rewrites the issue-body renderer to be ready-to-paste from any user's machine — which is the point of the command: **anyone running rag-plugin should be able to file a useful issue back to the maintainer with one copy-paste**.

### Bug fixes in `scripts/rag_report.py`

- **`/api/projects` parser** now handles both shapes: bare list `[...]` (older builds) and modern wrapped object `{"projects": [...]}`. Each project record is hydrated via `/api/projects/<id>/status` to pull path, last_indexed, and enabled — the list endpoint returns lean records (`{project_id, files, chunks}`) which is why the report previously showed "No project list available" despite 14 projects being configured.
- **`/api/status` excerpt key list** updated to ragtools v2.5.x fields: `points_count`, `total_files`, `total_chunks`, `last_indexed`, `scale`, `collection`, `embedding_model`, `score_threshold`, `projects`. The previous list referenced fields that the running build doesn't expose, so §3 emitted `{}`.
- **Scale-band findings (A-012, A-013)** added to the application-side synthesizer. ragtools v2.5.x exposes a `scale` block with `level ∈ {none, approaching, warning, critical}` and human-readable `message`. The synthesizer now emits A-012 (medium) on `approaching` and A-013 (high) on `warning`/`critical`/`near-limit`, so collection-size pressure is visible in the report instead of silently ignored.
- **A-008 false-positive fix**: "no projects configured" is no longer emitted when `/api/projects` parser fell through but `/api/status.projects` is non-empty. The synthesizer now cross-checks both sources.
- **§5 Data/index state** in the application report now also shows aggregate index totals (`points`, `total_files`, `total_chunks`, `last_indexed`, `scale.level`) when available.

### Issue-body renderer rewrite

`render_github_issue()` now produces a substantively bigger body (~135 lines vs ~40 before), structured for collection across many users:

- **Symptom-driven title** — derived from the highest-severity finding (e.g. `[ragtools] medium: local Qdrant collection approaching scale limit`) so issues collected across multiple users cluster by symptom, not by user.
- **Auto-derived labels** — `severity:<level>`, `install-mode:<mode>`, `service:<state>` (rag target only) added alongside the static `diagnostic` and `source:rag-plugin-report` labels.
- **Environment block** — rich and ready-to-paste: install mode, binary path, version, service mode, host:port, data path, log path, plus generator metadata.
- **Findings table + per-finding detail** — both rendered.
- **Target-specific evidence dump:**
  - rag target gets `/health` body, `/api/status` key fields, watcher status, and a project inventory table — all redacted.
  - plugins target gets plugin layout inventory, Claude config state (CLAUDE.md retrieval rule version, MCP wiring), full hook-decisions breakdown with percentages, session-behavior signal counts, and up to 6 redacted single-line snippet examples.
- **Reproduction steps** — concrete commands the maintainer can ask any user to run.
- **Privacy notice** — explicit list of what was redacted (secrets, tokens, cookies, PEM keys, GitHub PATs, AWS keys, Slack tokens, home-path normalization, hostname masking, snippet clipping) + a manual scrub reminder for project-specific names that may slip through.

The report engine version is now `v0.9.0` (was `v0.8.0`); plugin version `0.11.0 → 0.12.0`.

### Verification

- `python scripts/rag_report.py --self-test` — all redaction + render checks pass.
- Live run against the production ragtools service at `127.0.0.1:21420` (v2.5.2, packaged-windows, 14 projects, 16,510 points, scale.level=approaching) correctly:
  - Surfaces A-012 (Qdrant scale approaching) instead of silently ignoring it.
  - Lists all 14 projects with files/chunks/enabled/path (was "No project list available").
  - Emits a `/api/status` excerpt with the structured `scale` block (was `{}`).
  - Generates a 137-line `github-rag-issue.md` ready to paste, including a symptom-driven title and auto-labels.
- `python validate_plugin_simple.py rag-plugin` — 9 commands, 3 skills, 1 hooks file, all OK.

### Why this matters for the maintainer feedback loop

Before v0.12.0, anyone running `/rag:report` got an issue file that lacked the scale-band signal, missed the project inventory, and had a generic title. Collecting issues across many users was hard because: (a) the most-actionable signals weren't surfaced, and (b) the body was too thin to triage without follow-up questions. v0.12.0 makes the issue body self-contained — environment, runtime evidence, hook-injection rate, session signals, severity-ranked findings — so the maintainer can read once, triage, and route improvements back to the plugin.

## [0.11.0] — 2026-05-01

Closes the LESSONS.md TODO "rag-plugin enhancement (future work)" — the retrieval-reminder hook now distinguishes operational/inspection questions from knowledge questions and silent-passes the former. Source: `~/.claude/LESSONS.md` "Inspect the machine before asking clarifying questions" (2026-04-28).

### Added

- **`hooks/prompt_retrieval_reminder.py`** — new Phase A.5 **operational-intent classifier** (`is_operational_intent()`). Matches imperative operational verbs near the start of the prompt (`start|stop|restart|run|launch|kill|fix|set up|install|configure|where is|what's running|why is X failing|...`) and silent-passes with a new action tag `silent-pass:operational-intent`. Anchored to first 120 chars + word boundaries so trailing operational verbs in long knowledge questions don't trip it. Also accepts "how do I X" / "how can I X" / "how to X" lead-ins followed by an action verb.
- **`scripts/hook_classifier_smoke.py`** — new smoke test harness. 12 operational fixtures + 8 knowledge fixtures, asserts the classifier's decision on each. Importable from the plugin root; `--self-test` exits non-zero on any misclassification; `--verbose` prints every fixture's decision.
- **D-027** in `docs/decisions.md` — binding decision capturing the classifier list, the threshold change, and the single-source-of-truth principle (regex lives in the hook; smoke script imports it).
- **`/doctor --classify`** — new read-only flag in `commands/doctor.md`. Invokes the smoke test in verbose mode so users can see exactly how each fixture is classified by the gate.

### Changed

- **`hooks/prompt_retrieval_reminder.py`** — `HOOK_VERSION` bumped `0.3.0 → 0.4.0`. Default `RAG_PLUGIN_HOOK_PROBE_THRESHOLD` raised from `0.5 → 0.65` per LESSONS.md TODO #2 — MODERATE-tier (0.5–0.7) was too noisy; HIGH-tier (≥0.65) keeps the hook helpful without nagging. Override via env var still supported.
- **`rules/claude-md-retrieval-rule.md`** — version bumped `0.2.0 → 0.3.0`. Marker now reads `<!-- rag-plugin:retrieval-rule:begin v=0.3.0 -->`. **Section 0a "Override: Operational / Inspection Questions Skip the MCP"** added inside the managed block per LESSONS.md TODO #3 — every install of rag-plugin now ships with the operational/inspection skip baked in. The user no longer needs to hand-roll Section 0a outside the markers. (Existing user-managed Section 0a outside the markers is left intact by the install logic — no overwrite.)
- **`commands/doctor.md`** — new `--classify` flag documented.
- **`.claude-plugin/plugin.json`** — version `0.10.0 → 0.11.0`.

### Migration

Run `/rag:config claude-md install` once to upgrade the managed block to v0.3.0. The install logic detects the marker version, locates the begin→end range, and replaces the enclosed block atomically with backup. Users who manually added Section 0a outside the markers can remove their hand-rolled copy after the upgrade — the canonical version now ships with the plugin.

### Verification

- `python scripts/hook_classifier_smoke.py --self-test` — **20/20 fixtures pass** (12 operational + 8 knowledge).
- `python validate_plugin_simple.py rag-plugin` — 9 commands, 3 skills, 1 hooks file, all OK.
- Real-world test: feed `"how do I start the bot in WSL?"` to the hook → silent-passes with `operational-intent`. Feed `"what's our process for handling token rotation?"` → reaches the probe phase (correctly).

### Why this matters

Before v0.11.0, the hook fired on probe-score similarity alone and could not distinguish "how do I start X" (answer is on disk) from "how do we handle X" (answer is in notes). The classifier closes that gap. After v0.11.0, the user-side workaround in `~/.claude/CLAUDE.md` Section 0a (added 2026-04-28) is no longer needed for new installs — Section 0a now ships inside the managed block.

LESSONS.md TODO items #1, #2, #3 fully addressed. Item #4 (`/setup` smoke test integration during first-time install) deferred to a future amendment — the smoke script is shipped and runnable today as `python scripts/hook_classifier_smoke.py`; wiring it into the `/setup` verify branch happens when the next setup-flow refactor lands.

## [0.10.0] — 2026-05-01 — BREAKING command rename

All seven `/rag-*` commands renamed to drop the redundant `rag-` prefix. The plugin namespace `/rag:` already provides the prefix when commands are invoked through Claude Code's plugin command surface, so the file-name prefix duplicated information. Plugin-namespaced invocations are now shorter and cleaner.

### Renamed (file → new file → invocation form)

| Before | After | Plugin-namespaced |
|---|---|---|
| `commands/rag-bug-report.md` | `commands/report.md` | `/rag:report` |
| `commands/rag-config.md` | `commands/config.md` | `/rag:config` |
| `commands/rag-doctor.md` | `commands/doctor.md` | `/rag:doctor` |
| `commands/rag-projects.md` | `commands/projects.md` | `/rag:projects` |
| `commands/rag-reset.md` | `commands/reset.md` | `/rag:reset` |
| `commands/rag-setup.md` | `commands/setup.md` | `/rag:setup` |
| `commands/rag-sync-docs.md` | `commands/sync-docs.md` | `/rag:sync-docs` |

Untouched (already namespace-clean):

- `commands/md-rag-enhance.md` → `/rag:md-rag-enhance` (the `rag` here refers to the RAG pipeline, not the plugin name)
- `commands/project-focus.md` → `/rag:project-focus`

### Changed

- All cross-references to renamed commands across the plugin source (commands, skills, agents, hooks, scripts, rules, README, ARCHITECTURE, decisions log) rewritten in one pass — 397 replacements across 30 files. Both bare-slash forms (`/rag-doctor` → `/doctor`) and plugin-namespaced forms (`/rag:rag-doctor` → `/rag:doctor`) updated.
- `.claude-plugin/plugin.json` — version `0.9.0` → `0.10.0`.
- **D-026** in `docs/decisions.md` — binding decision capturing the rename + migration guidance for users with muscle memory.

### Migration notes for users

If you typed `/rag:rag-doctor` before, type `/rag:doctor` now. The plugin name on the left of the colon stays the same; only the command-name suffix changed. With the rename, plugin-namespaced is the canonical form.

Older CHANGELOG entries' command-invocation tokens have been rewritten for textual consistency; the file-path references inside those entries still point at the historical filenames at the time of release. Treat the CHANGELOG as a current-day reading guide, not a forensic record of historical syntax.

### Verification

- `python validate_plugin_simple.py rag-plugin` — 9 commands, 3 skills, 1 hooks file, all OK.
- `python scripts/project_focus.py self-test` — 5/5 checks pass.
- `python scripts/rag_report.py --self-test` — all redaction + render checks pass.
- No `/rag-doctor` / `/rag-config` / `/rag-projects` / `/rag-reset` / `/rag-setup` / `/rag-sync-docs` / `/rag-bug-report` references remain in source.

### Reasoning for `report` (not `bug-report`)

The diagnostic command captures evidence for the maintainers across the full health spectrum — install state, runtime, performance signals, configuration drift, missed retrievals, manual workarounds, improvement opportunities. "Bug-report" implied a defect-focused tool; the actual scope is broader. `/rag:report` reads naturally for "give me a diagnostic report".

## [0.9.0] — 2026-05-01

Project-focus mode. Ships `/project-focus`, a command that scopes ragtools retrieval to the user's current project so Claude does not pull context from unrelated indexed projects. Persists focus state in a single local JSON file and injects scope-this-to-X context on every UserPromptSubmit via a new bundled hook.

### Added

- **`commands/project-focus.md`** — new user-facing command, ninth in the catalog. Subcommands: `set` (auto-detect from CWD + git root, default), `<name>` (manual focus), `status`, `clear`. Refuses to mutate ragtools project config — if the focused project isn't indexed, it tells the user which `/projects` invocation to run.
- **`scripts/project_focus.py`** — stdlib-only Python matcher + state CRUD engine. Resolves CWD + git root, calls `GET /api/projects` to enumerate configured projects, scores matches by exact-path / ancestor-path / descendant-path / name, persists `~/.claude/rag-plugin/state/project-focus.json` atomically. Built-in `self-test` covers exact-match, ancestor-match, manual-name-match, no-match, and state file round-trip.
- **`hooks/project_focus_inject.py`** — new UserPromptSubmit hook that reads the focus state file and injects a strict-mode reminder when focus is active. Silent-passes on missing/malformed state. Composes alongside the existing retrieval-reminder hook (Claude Code supports multiple UserPromptSubmit entries). Never reads or logs the prompt.
- **D-025** in `docs/decisions.md` — binding decision covering the focus state-file contract, the filter-fallback policy (try project parameter → post-filter results → warn if neither possible), the cross-project retrieval gate (explicit phrase required), and the no-auto-mutation rule.

### Changed

- **`.claude-plugin/plugin.json`** — version `0.8.0` → `0.9.0`.
- **`hooks/hooks.json`** — second UserPromptSubmit entry registered for `project_focus_inject.py`. Top-level `description` updated to enumerate three hooks.

### Behavior while focus is active

Every UserPromptSubmit injects a system reminder telling Claude to:

1. Pass `project="<name>"` to `search_knowledge_base` if the tool supports the parameter.
2. Otherwise, post-filter result metadata (source/path/name) to keep only entries matching the focused project.
3. Warn if neither path can guarantee strict focus for a given query — never silently fall back.
4. Allow cross-project retrieval only when the user explicitly asks ("across all projects", "compare projects", "global knowledge").

### Safety invariants

- Never auto-mutates ragtools project config (no auto `add_project`, no auto `reindex_project`).
- Atomic state writes (tmp + `os.replace`).
- Single source of truth — the hook reads only the state file; no env vars, no second config location.
- Hook silent-passes on every error; the retrieval-reminder hook continues to fire independently.
- Cross-project retrieval gated on explicit user phrase.

### Verification

- **Self-test:** `python scripts/project_focus.py self-test` passes (exact, ancestor, manual, no-match, round-trip).
- **Hook smoke test:** with a synthetic state file and a fake stdin payload, the injector emits valid `hookSpecificOutput.additionalContext` JSON; with no state file, it silent-passes.
- **Validator:** `python validate_plugin_simple.py rag-plugin` passes — 9 commands, 3 skills, 4 hook files.

## [0.8.0] — 2026-05-01

Maintainer-feedback diagnostic command. Ships `/report`, an evidence-collection command that produces two reports — one targeted at the upstream `ragtools` product (github.com/taqat-techno/rag) and one targeted at this plugin (github.com/taqat-techno/plugins). The reports are designed to be copy-pasted into a maintainer issue without follow-up questions about environment, install state, or repro context.

### Added

- **`commands/rag-report.md`** — new user-facing command, eighth in the catalog. State-aware: produces both reports even when ragtools is not installed (the app report simply leads with that as the top finding). Privacy-safe by design — no auto-upload, no config mutation, secrets redacted, home paths normalized, session snippets clipped to 220 chars.
- **`scripts/rag_report.py`** — stdlib-only Python report engine (~700 lines, Python 3.10+). Probes install state, service runtime, MCP wiring, plugin layout, Claude configuration, hook-decisions log, recent service log tails, and recent Claude session JSONL files for RAC/RAG-related signals only. Redaction layer covers bearer tokens, API keys, GitHub PATs (`ghp_*`, `github_pat_*`), AWS keys, Slack tokens, cookies, and PEM private keys. `--self-test` mode runs lightweight stdlib unit-style checks. `--no-sessions` opts out of session scanning entirely. `--max-sessions N` caps the scan budget. Output is six files in a timestamped directory.
- **D-024** in `docs/decisions.md` — binding decision covering the dual-report architecture, the privacy invariants, the no-upload posture, the redaction surface, and the session-scan signal taxonomy.

### Changed

- **`.claude-plugin/plugin.json`** — version `0.7.0` → `0.8.0`.

### Reports produced

Each invocation creates `~/.claude/rag-plugin/reports/YYYY-MM-DD-HHMMSS/` containing:

1. `rag-application-setup-report.md` — RAC/RAG install / runtime / config / data / logs health, with severity-ranked `A-NNN` findings.
2. `rag-plugin-behavior-report.md` — plugin install state, Claude configuration, MCP wiring, hook behavior, session-behavior analysis with severity-ranked `P-NNN` findings.
3. `summary.md` — top-level executive summary.
4. `github-rag-issue.md` — copy-pasteable issue body for the rag repo.
5. `github-plugins-issue.md` — copy-pasteable issue body for the plugins repo.
6. `redacted-diagnostics.json` — machine-readable structured findings.

### Privacy properties

- Secrets, tokens, bearer headers, cookies, and private keys are redacted before any text reaches a report.
- Home directory paths are normalized to `~/...`.
- Hostname is partially masked (first 2 + last 2 chars).
- Session JSONL snippets are clipped to 220 characters and stripped of newlines.
- Only RAC/RAG-related signals are extracted from sessions — no unrelated user activity is summarized.
- The command never uploads anything; the user copies into GitHub manually.

### Verification

- **Self-test:** `python scripts/rag_report.py --self-test` passes (redaction samples, snippet scrubbing, home normalization, finding render, severity sort).
- **Live run:** `python scripts/rag_report.py --max-sessions 8` produces six files in `~/.claude/rag-plugin/reports/<ts>/` with correct state detection (packaged-windows / UP / v2.5.2 / plugin v0.8.0) and surfaces a real session-side `MCP error phrases` signal at medium severity.
- **Cross-platform:** stdout is forced to UTF-8 with `errors='replace'` so the script is safe on Windows cp1252 consoles.
- **Validator:** `python validate_plugin.py rag-plugin` passes (pre-existing SKILL.md YAML false-positive unchanged).

## [0.7.0] — 2026-04-19

Markdown authoring standard + always-safe Markdown enhancer. Ships a third skill (`markdown-authoring`) and a seventh user-facing command (`/md-rag-enhance`) that together optimize any Markdown-heavy project for the ragtools chunker + MiniLM-L6-v2 embedder.

The work is grounded in a reverse-engineered 359-line authoring standard derived from `src/ragtools/chunking/markdown.py`, `src/ragtools/retrieval/formatter.py`, and the embedder's 256-token window. The plugin now knows both how to **create** RAG-friendly Markdown (the skill) and how to **enhance** existing files toward the standard without corrupting their meaning (the command).

### Added

- **`skills/markdown-authoring/SKILL.md`** — new skill, third on the plugin's skill surface. Auto-activates on Markdown creation intent ("write a README", "document this component", "create a runbook", "draft an SOP for Z", "RAG-friendly markdown", "optimize for retrieval"). Loads the 8 hard rules + 5 page templates + 9 anti-patterns from `references/`. Never auto-saves files — Claude proposes content; the user accepts/edits/rejects.
- **`skills/markdown-authoring/references/rag-md-guidelines.md`** — the full 359-line authoring standard, copied verbatim from the source-of-truth. Used as the canonical reference by the skill.
- **`skills/markdown-authoring/references/page-templates.md`** — 5 copy-paste scaffolds (concept page, SOP page, reference page, runbook page, architecture page) each designed to produce 3–6 clean heading-anchored chunks.
- **`skills/markdown-authoring/references/anti-patterns.md`** — the 9 anti-patterns with per-item chunker-mechanism rationale (why each specifically hurts this RAG pipeline with file:line references to `markdown.py`).
- **`commands/md-rag-enhance.md`** — new command, always-safe by design. No args → enhance every `.md` under CWD. Optional positional file arg → enhance just that file. `--verbose` and `--no-backup` are the only flags. Generic and standalone per D-021.
- **`scripts/md_analyzer.py`** — stdlib-only Python analyzer and safe-fix engine (~500 lines, Python 3.10+). 10 check functions (`GL-01..GL-10`), two safe-fix categories (pseudo-heading conversion + blank-line normalization), atomic+backup writes, `--self-test` with built-in unit-like tests, `--dry-run` for development preview, `--json` for programmatic use, Windows-safe stdout (force UTF-8).
- **D-023** in `docs/decisions.md` — binding decision covering the authoring standard, the always-safe command boundary, the five-flag parameter surface, the two fix categories that are safe by construction, the report-only list that requires human judgment, non-violation checks against D-001/D-005/D-007/D-008/D-012/D-015/D-020/D-021/D-022, and the "Reverse only if" criteria for future expansion.

### Changed

- **`skills/ragtools-ops/SKILL.md`** — command surface description bumped to 7 user-facing + 1 maintainer. Routing note added for Markdown creation (→ `markdown-authoring` skill) and Markdown improvement (→ `/md-rag-enhance`). No other behavior change.
- **`.claude-plugin/plugin.json`** — version `0.6.1` → `0.7.0`.

### Safety properties of the new command

Applied on every invocation (always-safe is the only mode):

1. **Never modify content inside fenced code blocks.** Even blank-line normalization skips code-fence interiors.
2. **Never change commands, URLs, file paths, config keys, version numbers, or numeric values.** The safe-fix categories operate on structure, not flowing text.
3. **Never delete content.** The two safe fixes only ADD structure (headings, blank lines) or CONVERT pseudo-headings to real headings.
4. **Atomic writes.** Load → modify in-memory → write to `<file>.tmp` → `os.replace()`. Never in-place edit.
5. **Backup before every write.** `<file>.bak-pre-md-rag-enhance` sibling. `--no-backup` opts out for git users.
6. **Skip standard dirs** (`.git/`, `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`) and respect `.gitignore`. Skip binary files, symlinks, files > 1 MB.
7. **Hardcoded 500-file safety cap** for whole-project scans. Exceeded → clear error asking for a specific file path.

### Rationale

Two user-reported needs:

1. **Newly-created Markdown should follow the guideline by default.** Before v0.7.0, any documentation Claude wrote would land in whatever shape the conversation produced — sometimes excellent, sometimes an anti-pattern. The skill makes "good chunks" the default shape.
2. **Existing Markdown-heavy projects need a safe way to migrate toward the standard.** Before v0.7.0, the user had to manually apply the 8 hard rules to hundreds of files. The command automates the two categories that are mechanically safe, and reports the rest for manual review.

The always-safe posture (no mode switching) is deliberate. A command with flags for "analyze" vs "safe-fix" vs "aggressive" invites the wrong invocation at the wrong time. Simplicity is the safety property; the single mode eliminates a whole class of mis-invocations. Structural rewrites that require judgment are REPORT-ONLY — the tool surfaces them; the human decides.

The two safe-fix categories were chosen because they **cannot change semantic meaning by construction**:
- Pseudo-headings (`**Text**`) are bold text with no chunker-visible effect; converting to `## Text` adds chunking structure without touching any flowing text.
- Blank-line normalization is purely typographical; it inserts `\n` characters and never touches any non-blank content.

Every other guideline violation (content-before-first-heading, oversized sections, vague headings, mixed-topic sections, duplicate leaf headings, oversized code blocks, oversized tables, YAML frontmatter carrying knowledge, code block without prose intro, skipped heading levels) requires **semantic judgment** to fix — splitting a section needs topic decomposition, renaming a heading needs understanding what it's about, moving knowledge out of frontmatter needs deciding where it belongs. These are reported, not auto-applied.

### Verification

- **Self-test:** `python scripts/md_analyzer.py --self-test` passes on Windows (cp1252-safe with forced UTF-8 stdout).
- **Dry-run against the plugin's own README:** `python scripts/md_analyzer.py README.md --dry-run` correctly identifies missing blank lines around code fences; applies no other changes; never touches code-fence interiors.
- **Validator:** `python validate_plugin.py rag-plugin` passes (pre-existing SKILL.md YAML false-positive and documented hooks.json warnings unchanged).
- **Cross-platform:** `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` called at `main()` entry so the script is safe on Windows cp1252 consoles when printing Markdown content containing arrows, em-dashes, or non-ASCII.
- **Command surface audit:** 7 user-facing commands (was 6) + 1 maintainer-only = 8 total commands. 3 skills (was 2) — `ragtools-ops`, `ragtools-release`, `markdown-authoring`.

### Known follow-ups

- **Frontmatter-to-`## Tags` migration as a safe-fix** — promoted from report-only to auto-applied in v0.8.0 after field evidence that the migration is clean on real-world files with mixed frontmatter (dates, authors, license fields mixed with tags/keywords).
- **Diff-review mode** (`--review` or equivalent) for users who want to preview changes before the safe-fix is applied. The analyzer already supports `--dry-run` internally; surfacing it through the command requires UX work and a binding decision on whether "preview then commit" constitutes a second mode that violates D-023's simplicity property. Deferred to v0.8.0.
- **Integration with the `ragtools-release` skill** — when a ragtools release ships, documentation updates could be gated on `/md-rag-enhance` passing with no HIGH findings. Would need a new invariant in `skills/ragtools-release/references/release-checklist.md`.

## [0.6.1] — 2026-04-19

Install-path clarity patch. Restructures `/setup` Branch A so all three packaged platforms (Windows, macOS Apple Silicon, Linux ARM64) are first-class paths with a universal source-install fallback explicitly documented for every other platform. Picks up the ragtools v2.5.1 Linux-ARM64 release. Links the upstream ragtools product repo prominently throughout the plugin.

### Changed
- **`commands/rag-setup.md`** — Branch A rewritten:
  - New header calls out the upstream repo [`github.com/taqat-techno/rag`](https://github.com/taqat-techno/rag) as the source of truth for all installers.
  - Three packaged platforms documented equally: A.2 Windows installer, A.3 macOS Apple Silicon tarball, **A.4 (new) Linux ARM64 tarball** (v2.5.1+).
  - **A.5 source install is promoted to a universal fallback** — documented as available for *any* platform (macOS Intel, Linux x86_64, Windows ARM, anything exotic), not just Linux. Extended with prerequisite list, platform-specific venv activation commands, and explicit dev-mode-vs-packaged differences (config path, data path, auto-startup, PATH scope).
  - Platform/arch detection table (A.1) now has a row per arch instead of per OS — distinguishes Linux aarch64 (A.4) from Linux x86_64 (A.5), macOS arm64 (A.3) from macOS Intel (A.5), Windows x64 (A.2) from Windows ARM (A.5).
- **`skills/ragtools-ops/references/install.md`** — Sources table gains the Linux ARM64 artifact row; Supported platforms table gains rows per architecture with clear "packaged" vs "source-only" support tier.
- **`skills/ragtools-ops/references/gaps.md`** — **G-001 partially superseded** by ragtools v2.5.1: Linux ARM64 is now packaged. Linux x86_64 is still source-only. Plugin behavior clause updated to detect arch and route accordingly.
- **`.claude-plugin/plugin.json`** — version `0.6.0` → `0.6.1` (patch — UX clarity + upstream linkage; no new capability added).
- **`README.md`** — status badge bumped; added a prominent upstream-product link at the top so anyone arriving at the plugin can reach the ragtools repo directly.
- **Wiki (`plugins/wiki/Home.md`, `Rag-Plugin.md`, `Marketplace-Overview.md`, `Installation-and-Usage.md`, `Plugin-Catalog.md`)** — upstream product link surfaced prominently; Linux ARM64 reflected in relevant tables.

### Rationale
Two user-reported gaps:

1. **Wiki → product linkage was thin.** Anyone reading the plugin wiki had no obvious path to the ragtools application repo itself. Fixed by adding a prominent [`github.com/taqat-techno/rag`](https://github.com/taqat-techno/rag) link at the top of Home.md, Rag-Plugin.md, and the install walkthrough.
2. **Install command was implicitly Windows-first.** `/setup`'s Branch A detected three platforms but treated Linux as a dev-install-only path and buried the source-install fallback as "A.4 Linux dev install". ragtools v2.5.1 actually ships Linux ARM64 packaged. The rewrite makes all three packaged paths (A.2/A.3/A.4) equally first-class and elevates the source install (A.5) as the documented universal fallback for any platform — not just Linux.

### Verification
- Validator passes (pre-existing SKILL.md YAML false-positive and documented hooks.json warnings unchanged).
- All 3 packaged platforms have a dedicated section in Branch A with platform-specific commands.
- A.5 source install documents the venv activation commands per-shell (bash/zsh, CMD, PowerShell) and explicitly states the dev-mode-vs-packaged path differences.
- Upstream repo link (`github.com/taqat-techno/rag`) appears in: `rag-plugin/README.md`, `commands/rag-setup.md`, `references/install.md`, `wiki/Home.md`, `wiki/Rag-Plugin.md`, `wiki/Marketplace-Overview.md`, `wiki/Installation-and-Usage.md`.

## [0.6.0] — 2026-04-18

Maintainer release-gate capability. Adds a second skill (`ragtools-release`) that walks the six permanent release invariants before an upstream ragtools version ships. Does not affect operator-facing workflows.

### Added
- **`skills/ragtools-release/SKILL.md`** — new skill, auto-activating on maintainer release phrasing ("pre-release check", "release checklist", "ready to ship ragtools", "v2.5.x pre-flight", "release go/no-go", "RELEASE_LIFECYCLE", "cutting a ragtools release"). Gating-only — walks the six invariants one at a time, gathers explicit ack or hold per item, summarizes as green / pre-release / blocked. Never tags, pushes, promotes, or builds.
- **`skills/ragtools-release/references/release-checklist.md`** — the six permanent invariants with statement, rationale, source-of-truth files, pre-check heuristics, and red flags:
  - **Invariant 1** — no user data into install directory (`get_config_write_path()` vs `{app}\`)
  - **Invariant 2** — schema changes bump version + ship migration (`CONFIG_VERSION`, `PRAGMA user_version`, encoder dim, index schema)
  - **Invariant 3** — dev-mode startup isolation (`is_packaged()` guard in `run.py`)
  - **Invariant 4** — upgrade-path manual test (downloaded installer on previous-version machine)
  - **Invariant 5** — uninstall opt-in prompt (full wipe / keep data)
  - **Invariant 6** — `docs/RELEASE_LIFECYCLE.md` accuracy
- Two-skill surface: `ragtools-ops` (operator-facing) + `ragtools-release` (maintainer-facing). Different activation triggers, no overlap.

### Changed
- **`.claude-plugin/plugin.json`** — version `0.5.0` → `0.6.0`. Minor bump (new skill surface is user-visible).

### Rationale
The ragtools v2.5.1 release checklist the upstream maintainer had been running manually (the six-item "Claude says: yes. Your ack?" ritual) was load-bearing enough to promote into the plugin as a skill. Shipping it as a skill rather than a new command follows the house direction — skills over commands, commands stay generic. The skill auto-activates on maintainer phrasing; the operator-facing `ragtools-ops` skill is untouched.

The six invariants derive from actual release incidents and boundary-safety rules:
- Invariants 1 + 3 + 5 exist because ragtools has both replaceable-app (`{app}\`) and persistent-user-data (`{userdata}\`) locations, and historic bugs have written user state into `{app}\` where upgrades silently wiped it.
- Invariant 2 exists because silent schema mismatches across versions are a class of data-loss bug that version constants + migrations prevent.
- Invariant 4 exists because CI installs on clean machines, but the v2.5.0 → v2.5.1 `ForceKillRagProcesses` fix only manifests as a bug when the previous version is already installed *and running*. Manual test of the downloaded installer on a pre-upgraded machine is the only coverage.
- Invariant 6 exists because the canonical release-lifecycle doc is downstream of the invariants — if the doc doesn't match reality, future maintainers get wrong answers.

### Verification
- Validator passes (pre-existing SKILL.md YAML false-positive and documented hooks.json warnings unchanged).
- Two skills now present: `ragtools-ops/SKILL.md` + `ragtools-release/SKILL.md`.
- References file at `skills/ragtools-release/references/release-checklist.md` — ~180 lines, stdlib-only content, no external refs required at read-time.
- Activation triggers in the `ragtools-release` skill description are explicitly maintainer-only (no overlap with `ragtools-ops` operational triggers).

### Known follow-ups
- A "release ack log" at `~/.claude/rag-plugin/release-acks.jsonl` (opt-in, same pattern as `usage.log` and `hook-decisions.log`) — the skill mentions this as a future capability but it is not yet wired into `/config`.
- When ragtools v2.6.0 ships with new invariants (new platforms, new schema), append a new D-NNN in `docs/decisions.md` + extend `references/release-checklist.md`.

## [0.5.0] — 2026-04-18

MCP v2.5.0 integration. The plugin now uses the full 22-tool MCP surface — 3 core + 9 project ops (default ON) + 9 debug (default OFF, user-granted) — for diagnostics, project introspection, ignore-rule management, and guarded writes. **Command count stays at 6 user-facing commands + 1 maintainer-only**; every new capability is delivered as a skill workflow that auto-activates on user intent, rather than as a new slash command. Every existing command is now **generic** (works standalone without required arguments, accepts optional parameters).

### Added
- **`rules/mcp-envelope.md`** — new shared rule codifying the MCP envelope contract: error-code-first branching, mode-based dispatch, three-tier fallback chain (MCP → HTTP → CLI), tool-grant awareness, cooldown discipline, confirm-token guard for `reindex_project`. Referenced by every MCP-using command and by the `ragtools-ops` skill. Single source of truth for envelope handling; commands do not inline the discipline.
- **Skill workflows 2.5.1–2.5.9** in `skills/ragtools-ops/SKILL.md` — auto-activating MCP workflows, each triggered by user-intent phrasing:
  - **2.5.2 Project health** — `list_projects` → `project_status` for a rich per-project card on "is project X healthy?".
  - **2.5.3 Why-not-indexed workflow** — `list_project_files` → `get_project_ignore_rules` → `preview_ignore_effect` → offer `remove_project_ignore_rule` + `run_index`. Activates on "why isn't file F in search?", "file F is missing", etc. Entirely new capability.
  - **2.5.4 Add-ignore-rule workflow** — preview → typed `ADD` gate → `add_project_ignore_rule` → offer `run_index`. Activates on "exclude X", "ignore tmp/", "don't index node_modules".
  - **2.5.5 Remove-ignore-rule workflow** — refuses to remove `built_in` rules (explains why); typed `REMOVE` gate for `config_project` rules.
  - **2.5.6 Reindex decision tree** — `run_index` incremental first (2s cooldown), drift detection (deleted > 5 AND indexed < 2), escalation to `reindex_project` with typed `DELETE` and 30s cooldown only on drift.
  - **2.5.7 Tool-grant audit** — shows which MCP tools are enabled vs disabled, names the toggle path for each. Activates on "what tools are enabled?".
  - **2.5.8 Multi-project search preparation** — constructs the `projects=[...]` spec but does NOT call `search_knowledge_base` (D-001 preserved).
  - **2.5.9 MCP failure handling** — uniform fallback-chain discipline across all workflows.
- **D-022** in `docs/decisions.md` — binding decision refining D-001. Plugin uses MCP **ops tools** freely (all 18 non-search tools across core, project-ops, debug tiers); plugin still never wraps `search_knowledge_base`. Explicit table of what's allowed vs forbidden. Non-violation notes against D-001, D-005, D-007, D-008, D-012, D-015, D-017, D-020, D-021.
- **New `/projects` subcommands (v0.5.0)** — `status <id>` (uses `project_status`), `summary <id> [<top_n>]` (uses `project_summary`), `files <id> [<limit>]` (uses `list_project_files`). All read-only; envelope handling per `rules/mcp-envelope.md`.

### Changed
- **`commands/rag-doctor.md`** — Mode E (default fast probe) now prefers `mcp__plugin_rag_ragtools__index_status` + `list_projects` (+ optional `service_status`), with HTTP `/api/status` + `/api/projects` + `/api/watcher/status` as fallback when the MCP is in failed mode or not loaded. Mode D (`--full`) prefers `system_health` + `crash_history` for structured diagnostic output, falls back to wrapping `rag doctor` CLI when the debug tools aren't granted (with an admin-UI toggle hint). Mode B (`--logs`) prefers `tail_logs` (has filesystem fallback — works even in degraded mode) and supplements with `recent_activity` when granted. The `rag-log-scanner` Haiku agent contract is unchanged — still classifies findings — but now receives log content from the MCP tool rather than a direct disk read.
- **`commands/rag-projects.md`** — now **generic and standalone**: running `/projects` with no arguments defaults to `list`. Subcommand whitelist updated to document which MCP tool each subcommand uses (`list` → core, `status`/`summary`/`files` → project-ops, `rebuild` → `reindex_project` with confirm_token + 30s cooldown + auto-backup). `add` / `remove` documented as MCP-excluded-for-safety; plugin keeps HTTP paths for them but flags them as weaker than MCP-guarded alternatives. `rebuild <id>` now routes through MCP `reindex_project` (typed `DELETE` gate + confirm_token = project_id programmatic); global rebuild (no id) stays on HTTP because the MCP has no global equivalent.
- **`commands/rag-reset.md`** — now **generic and standalone**: running `/reset` with no flag enters an **interactive picker** showing the 3 escalation levels with their auto-backup / service-state / gate requirements. `--soft` routes single-project rebuilds through MCP `reindex_project` for the auto-backup + cooldown benefits; global `--soft` stays on HTTP with an explicit warning that auto-backup is not taken on that path. `--data` and `--nuclear` branches unchanged.
- **`rules/state-detection.md`** — now describes an MCP-first probe (`index_status` core tool, works in both proxy and direct mode) as the preferred Step 1, with HTTP `/health` and CLI `rag version` as Steps 2–3 fallbacks. State object gains `mcp_available: bool` and `mcp_mode: proxy|direct|degraded|failed|N/A` fields. Path resolution (Step 5) prefers MCP `get_paths` when the debug tool is granted; falls back to HTTP `/api/status` parsing.
- **`skills/ragtools-ops/SKILL.md`** — frontmatter `description` expanded with operational intent phrases ("why isn't this file in search", "add an ignore rule", etc.) so the skill auto-activates when users describe intents rather than ragtools keywords. Phase 1 (mode detection) now defers to `rules/state-detection.md` + `rules/mcp-envelope.md`. Phase 2.5 is new — MCP tool dispatch with 9 workflow sections. Phase 3 routing rewritten: operational questions default to **skill-chained MCP tool calls** (no slash command needed); only deep diagnosis, setup/install/upgrade, destructive reset, and plugin-layer config still route to slash commands.
- **`.claude-plugin/plugin.json`** — version `0.4.0` → `0.5.0`.

### Rationale
ragtools v2.5.0 expanded the MCP from 3 content tools to 22 total (3 core + 9 project ops + 9 debug). The v0.4.0 plugin used only the 3 core content tools via Claude's direct calls (D-001); everything operational was done via HTTP API or CLI. D-022 refines D-001 to keep the content-tool boundary (plugin never wraps `search_knowledge_base`) while unlocking the 18 non-search tools for plugin use. The MCP's own safety model — envelope contract, error-code enum, mode detection, cooldowns, confirm-token guard, auto-backup, intentionally-excluded tools (`add_project`, `remove_project`, `shutdown`, `backup_restore`, `set_active_project`) — is stronger than the ad-hoc HTTP paths the plugin previously used. Routing through the MCP means the plugin inherits those guarantees instead of duplicating (and drifting from) the logic.

Every net-new capability ships as a **skill workflow**, not a new command. The skill auto-activates on user intent (e.g. "why isn't file X indexed?") and chains the MCP tools without requiring a slash-command interface. This matches the user's directional guidance ("decrease commands, increase skills"), preserves D-021's "fewer, stronger, smarter commands" posture, and fills the 22-tool surface without growing the command count.

Every surviving command is now **generic / standalone** — `/projects` defaults to `list` with no args, `/reset` defaults to an interactive picker. Previously they printed usage and stopped; now they do the most common thing automatically.

### Verification
- Validator passes: `python validate_plugin.py rag-plugin` (pre-existing SKILL.md YAML and hooks.json false positives unchanged).
- Schema sanity: no change to `.mcp.json`, `.claude-plugin/plugin.json` manifest still valid.
- Command count: exactly 6 files under `commands/` (`rag-config.md`, `rag-doctor.md`, `rag-projects.md`, `rag-reset.md`, `rag-setup.md`, `rag-sync-docs.md`) — no growth.
- Rules: 3 files under `rules/` (`claude-md-retrieval-rule.md`, `state-detection.md`, `mcp-envelope.md`).
- Decisions: D-001 through D-022 — D-022 is the one new binding entry.
- All four envelope assertions in `rules/mcp-envelope.md` are testable against live MCP output once a session has the tools loaded: envelope shape, `error_code` enum, `mode` enum, fallback chain.

### Known follow-ups (later phases)
- **v0.6.0:** `/setup` Branch D adds a grant-check sub-step that audits which debug tools are granted vs which plugin workflows need them; offers the toggle path as a one-shot remediation list.
- **v0.7.0:** session-ID correlation in `/config hook-observability` — log the MCP session ID (`mcp:<sid>`) alongside hook decisions so multi-window users can diff.
- **Deferred:** migrate `/projects add` and `/projects remove` off HTTP toward CLI/admin-UI-only handoffs, matching the MCP's intentional-exclusion posture (D-022 §8).

## [0.4.0] — 2026-04-14

Command surface consolidation. Collapses 9 commands (8 user-facing + 1 maintainer) into 7 (6 user-facing + 1 maintainer) by folding `/rag-status` and `/rag-repair` into a smart `/doctor` and folding `/rag-upgrade` into a smart `/setup`. Every surviving command is now **state-aware at the top** — it runs a shared state-detection preamble, branches on the detected state, and refuses gracefully when the state is wrong instead of failing with a generic error.

The user complaint that drove this: commands assumed an already-installed, already-healthy state and fragmented the "get ragtools working" mental model across too many entry points.

### Added
- **`rules/state-detection.md`** — new shared contract file. Documents the canonical state-detection recipe (install mode + service mode + version + paths) and the exact 6-line mode banner format. Every command references it via `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md` in its Step 0 instead of re-documenting the probe. Single-owner layering per `ARCHITECTURE.md`.
- **D-021** in `docs/decisions.md` — binding decision. "Each command is a smart entry point that detects state and branches; commands do not assume an ideal state. State detection lives in `rules/state-detection.md` and is referenced, not re-implemented."

### Changed
- **`commands/rag-doctor.md`** — rewritten as the unified diagnose+status+repair command. Default mode is the fast state probe the former `/rag-status` did. `--full` is the deep `rag doctor` wrap the former standalone `/doctor` did. A free-text positional argument runs the F-001..F-012 + P-RULE/P-DEDUPE classification rubric the former `/rag-repair` did. `--symptom F-NNN` walks the named playbook. `--logs` runs the `rag-log-scanner` Haiku agent. `--fix` composes with any of the above to walk the repair playbook inline after classification. All 8 repair playbooks (P-svc, P-qdrant, P-perm, P-empty, P-slow, P-port, P-watcher, P-mcp) are preserved verbatim with their existing confirmation-gate discipline.
- **`commands/rag-setup.md`** — rewritten as the unified install+upgrade+verify command. Branches: A install (not-installed), B start-service (DOWN), C upgrade (UP but old, absorbs the former `/rag-upgrade`), D verify (UP and current — idempotent plugin-layer checks for MCP wiring, CLAUDE.md rule, dedupe). All other branches fall through to D on completion so the user always ends in a known-good state.
- **`commands/rag-projects.md`** — added an explicit state-gate preamble at Step 0. Refuses writes when the service is DOWN or BROKEN with a clear pointer at `/doctor` and `rag service start`. Refuses all ops when `install_mode == not-installed`. Cross-references updated (`/rag-status` → `/doctor`, `/rag-repair` → `/doctor --symptom`).
- **`commands/rag-reset.md`** — added an explicit state-gate preamble. Now checks `install_mode == not-installed` and `service_mode == BROKEN` **before** showing any typed-DELETE prompt, so destructive gates are never surfaced for an install that cannot be reset. Pre-v2.4.1 warning now routes users to `/setup` (which walks the upgrade flow) instead of the removed `/rag-upgrade`.
- **`commands/rag-config.md`** — cross-reference fixes only. No behavior change. Pointers to `/rag-status` / `/rag-repair` remapped to `/doctor` and to `/rag-upgrade` remapped to `/setup`.
- **`skills/ragtools-ops/SKILL.md`** — Phase 1 (mode detection) now references `rules/state-detection.md` instead of inlining the probe. Phase 3 (command routing) rewritten for the new 6-command surface with the consolidation note explaining where `/rag-status`, `/rag-repair`, and `/rag-upgrade` went.
- **`.claude-plugin/plugin.json`** — version `0.3.3` → `0.4.0`.

### Removed
- **`commands/rag-status.md`** — absorbed into `/doctor` default mode.
- **`commands/rag-repair.md`** — absorbed into `/doctor` via free-text symptom classification, `--symptom F-NNN`, `--logs`, and `--fix` flags.
- **`commands/rag-upgrade.md`** — absorbed into `/setup` Branch C.

Deletion rather than stub-redirects because stubs would create dead entries in the slash-command catalog and confuse users about what is still supported.

### Rationale
The current 3-file split `/rag-status + /doctor + /rag-repair` forced users to pick a hammer before they knew what was wrong. Every one of those files started with the same mode-detection block and ended with a footer pointing at the other two. The new `/doctor` lets the user just ask "what's wrong?" and branches based on state: default is a fast probe, `--full` goes deep, `--symptom` jumps to a playbook, `--fix` walks it. Same reasoning for `/setup + /rag-upgrade`: the user's mental model is "get ragtools working" regardless of whether that means "install it" or "upgrade it," and a single smart command handles both based on the detected version.

The destructive commands `/reset` and `/projects` **stay separate** because destructive/write operations benefit from their own namespace — they should not be hidden behind an innocuous command name. Instead, they get the state-gate preamble so they fail fast and safely on bad states.

`/config` stays because it operates on a genuinely different scope (plugin-layer config: telemetry, claude-md rule, mcp-dedupe, hook-observability) rather than the ragtools product layer.

`/sync-docs` stays because it is maintainer-only with `disable-model-invocation: true` and is invisible to the user surface.

### Verification
- `python validate_plugin.py rag-plugin` passes (commands: 6, skill: 1, agent: 1, hooks: 1; only the pre-existing SKILL.md YAML false-positive remains).
- Shape: `ls commands/` shows exactly 6 files — `rag-config.md`, `rag-doctor.md`, `rag-projects.md`, `rag-reset.md`, `rag-setup.md`, `rag-sync-docs.md`.
- `rules/state-detection.md` exists and is referenced by both rewritten command files.
- Grep confirms no live operational references to the deleted commands remain — all remaining mentions of `/rag-status`, `/rag-repair`, `/rag-upgrade` are in historical "absorbs the former X" documentation strings.
- CHANGELOG, decisions.md D-021, README catalog, ARCHITECTURE inventory, and SKILL routing all updated to the new surface.

## [0.3.3] — 2026-04-14

Second retraction in the v0.3.x MCP-wiring saga. Drops the Python launcher (`scripts/rag_mcp_launcher.py`) introduced in v0.3.1 and calls `rag serve` directly from `.mcp.json`, matching the pattern every other working plugin in `~/.claude/plugins/cache/` uses (`chrome-devtools`/`context7`/`playwright`/`azure-devops` all call `npx` directly — no Python wrapper in the middle).

### The bug v0.3.2 left behind

v0.3.2 shipped the correct **flat shape** `.mcp.json` and kept the launcher. Symptom: `ListMcpResourcesTool` showed `plugin:rag:ragtools` registered, `/reload-plugins` counted the server, but `ToolSearch` found zero ragtools tools and the model could not call `search_knowledge_base`. The MCP handshake was failing.

Root cause: **Python's `os.execvp` on Windows does not preserve stdio pipe inheritance.** On POSIX, `execvp` atomically replaces the current process image, so the stdin/stdout/stderr pipes that Claude Code opened to the Python launcher transfer cleanly to the spawned `rag.exe`. On Windows, `os.execvp` is a thin wrapper over `_spawnv(_P_OVERLAY, ...)` — the Python parent exits and a new process is started, but the inherited pipe handles are not guaranteed to survive that transition. The spawned `rag.exe` never receives the `tools/list` RPC that Claude Code is already waiting on, the call silently times out, and no tool schemas reach the deferred-tool registry.

The launcher worked when probed directly via `python rag_mcp_launcher.py --dry-run` (that path doesn't exec), and the underlying `rag.exe serve` worked when invoked directly over stdio. Both parts were fine in isolation. The handoff between them was the bug.

### Fixed
- **`rag-plugin/.mcp.json`** — rewritten to spawn `rag` directly. Final canonical form:
  ```json
  {
    "ragtools": {
      "type": "stdio",
      "command": "rag",
      "args": ["serve"]
    }
  }
  ```
  Same shape as `devops-plugin/.mcp.json`, same pattern as every working plugin on disk. No Python middleman, no `os.execvp`, no launcher script.
- **`scripts/rag_mcp_launcher.py`** — **deleted**. No longer needed. The service-query → PATH-probe cleverness it provided was solving a problem that doesn't actually exist: every supported install mode already puts `rag` on PATH (packaged Windows installer adds `C:\Users\<you>\AppData\Local\Programs\RAGTools` by default — verified on the reporter's machine via `where rag`; packaged macOS requires the user to add the tarball directory per upstream docs; dev `pip install -e .` exposes `rag` as a pyproject console-script). The v0.3.0 bug was **hardcoding the wrong binary name** (`rag-mcp` instead of `rag`), not "no binary on PATH." Fixing the name removes the need for the runtime-resolution launcher entirely.

### Changed
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` schema assertions updated. Direct-spawn is now the rule: any `command` that is `python` / `python3` / `py` with an arg referencing `rag_mcp_launcher.py` is surfaced as a distinct `ERROR — plugin .mcp.json uses the legacy Python launcher which breaks stdio on Windows. Upgrade to v0.3.3+`. The PATH-resolution check remains; the launcher-file check is dropped.
- **`rag-plugin/commands/rag-doctor.md`** — MCP registrations row error documentation rewritten for direct-spawn. The launcher error state is kept as a diagnostic for users still on v0.3.1/v0.3.2, with the upgrade remediation.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.2` → `0.3.3`.
- **`rag-plugin/README.md`** — status badge and auto-wire bullet updated.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A simplified. No more launcher explanation — just the direct-spawn snippet and a Prerequisites bullet: `rag` must be on PATH. Legacy section retained with three version entries (v0.2.0/v0.3.0 wrong command, v0.3.1 wrong schema, v0.3.2 launcher stdio bug).
- **`rag-plugin/docs/decisions.md`** — new **D-020**: "plugin-level `.mcp.json` spawns the target binary directly; Python wrapper scripts are an anti-pattern because of `os.execvp` stdio-pipe semantics on Windows." Supersedes the launcher portion of D-018 (D-019 already superseded the schema portion). D-015's original flat-shape + direct-spawn posture is fully restored.

### Rationale
The v0.3.x series has now cycled through three wiring strategies: (1) flat shape + wrong command name (v0.3.0, broken on packaged Windows), (2) wrapped shape + Python launcher (v0.3.1, tool schemas never loaded), (3) flat shape + Python launcher (v0.3.2, stdio pipe handoff broken on Windows). v0.3.3 is strategy (4): flat shape + direct spawn of the correct binary. This matches the empirical ground truth of what every other MCP plugin on the reporter's machine actually does, and it eliminates the entire class of "Python wrapper middleman" failure modes at once.

The lesson that justifies D-020 is worth stating plainly: **when wiring a stdio MCP server, your `.mcp.json` command should be the real binary. Not a script that spawns it, not a launcher, not a shim. If no single literal command works, fix the command at install time or via a user-level `.mcp.json` fallback — do not wrap it in another process.** Wrappers add a pipe-handoff hazard on Windows for no practical benefit.

### Edge case: user-level fallback

For the rare install where `rag` is genuinely not on PATH (user skipped the installer's "Add to PATH" option on Windows, or did not set up PATH on macOS), `/setup` branch C.1–C.2 still works: it reads `GET http://127.0.0.1:21420/api/mcp-config` to get the absolute binary path from the running service, then writes a user-level `~/.claude/.mcp.json` with the **wrapped** shape and that absolute path. Duplicate-registration cleanup via `/config mcp-dedupe` handles the plugin-level-vs-user-level coexistence. This flow is unchanged from v0.1.0 and is the documented fallback.

### Verification
- `where rag` on the reporter's Windows machine returns `C:\Users\ahmed\AppData\Local\Programs\RAGTools\rag.exe` — confirming `rag` is on PATH by default after the installer runs (the reporter's screenshot also shows `C:\Users\ahmed\AppData\Local\Programs\RAGTools` in the user Path env var).
- `where rag-mcp` returns nothing on packaged Windows — this is why hardcoding `rag-mcp` in v0.2.0/v0.3.0 was broken, and also why `rag` is the correct choice (not `rag-mcp`).
- `python plugins/validate_plugin.py rag-plugin` passes.
- JSON sanity: `python -c "import json; d=json.load(open('plugins/rag-plugin/.mcp.json')); assert d['ragtools']['command']=='rag' and d['ragtools']['args']==['serve']"` exits 0.
- After Claude Code restart: `/mcp` shows `plugin:rag:ragtools` with tools enumerated; `ToolSearch query="+ragtools"` returns `mcp__plugin_rag-plugin_ragtools__search_knowledge_base` and siblings; the retrieval-reminder hook's recommended call is actually invocable.

## [0.3.2] — 2026-04-14

Hotfix retraction. v0.3.1 over-corrected the v0.3.0 bug and shipped a `.mcp.json` in the **wrapped** shape (`{"mcpServers": {"ragtools": {...}}}`). This turned out to be wrong for plugin-level `.mcp.json` files. Claude Code's plugin loader expects the **flat** shape (`{"ragtools": {...}}` with no wrapper) for plugin-level registrations. `/mcp` reported the server as "present" and `/reload-plugins` counted it among the loaded servers, but `ToolSearch` could not find any ragtools tool by name and the model could not call `search_knowledge_base`.

Empirical confirmation from `~/.claude/plugins/cache/`: every working plugin ships the flat shape. Checked: `chrome-devtools-mcp`, `context7`, `playwright`, `azure-devops` (from `devops-plugin`), and rag-plugin v0.2.0 / v0.3.0 itself. Only v0.3.1 shipped the wrapped shape, and only v0.3.1 was broken. The wrapped shape is for user-level (`~/.claude/.mcp.json`) and project-level (`<repo>/.mcp.json`) files, not plugin-level.

### Fixed
- **`rag-plugin/.mcp.json`** — reverted to the flat shape while **keeping the launcher**:
  ```json
  {
    "ragtools": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]
    }
  }
  ```
  The launcher (`scripts/rag_mcp_launcher.py`) was the right idea and stays — it still resolves the canonical ragtools binary at runtime via `GET /api/mcp-config` → `rag` on PATH → `rag-mcp` on PATH → fail loud, which is what makes the plugin work across dev and packaged installs without hardcoding a binary name that only exists in one of them.

### Changed
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` schema assertion inverted. It now asserts the **flat shape** (top-level `ragtools` key) for plugin-level `.mcp.json`, not the wrapped shape. If a `mcpServers` wrapper is detected in a plugin-level file, surfaces a distinct `ERROR — plugin .mcp.json uses wrapped shape (mcpServers); plugin-level files require the flat shape — unwrap it`. User-level and project-level files continue to use the wrapped shape — the two scopes have different schemas.
- **`rag-plugin/commands/rag-doctor.md`** — the MCP registrations row's error documentation rewritten to describe the correct flat-shape rule and the wrapped-shape footgun.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.1` → `0.3.2`.
- **`rag-plugin/README.md`** — status badge updated.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A snippet reverted to the flat shape with the launcher. The D-018 wrapped-shape recommendation is explicitly retracted in the reference text.
- **`rag-plugin/docs/decisions.md`** — new **D-019** records the retraction: D-018's schema change was wrong, D-015's original flat-shape claim was correct all along. The launcher portion of D-018 stands (it fixes the real bug — the cross-install-mode command resolution). Only the schema portion is retracted.

### Rationale
The v0.3.0 bug was **one** bug (command `rag-mcp` not on PATH in packaged Windows installs), not two. My v0.3.1 changelog claimed it was also a schema bug and cited the workspace `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md` which documents the wrapped shape. That reference applies to user/project-level `.mcp.json` files, not plugin-level files. I missed the distinction and introduced a differently-broken schema on top of the fix for the command bug. The fix for v0.3.2 is simple: keep the launcher, revert the schema, document the scope rule so it does not happen again.

### Verification
- Before-and-after: `cat ~/.claude/plugins/cache/taqat-techno-plugins/rag/0.3.2/.mcp.json` shows flat shape with launcher.
- `python plugins/rag-plugin/scripts/rag_mcp_launcher.py --dry-run` resolves to `C:\Users\ahmed\AppData\Local\Programs\RAGTools\rag.exe serve` via the running service.
- Compared against `~/.claude/plugins/cache/claude-plugins-official/chrome-devtools-mcp/latest/.mcp.json` byte-for-byte structure — both use identical flat shape.
- `/mcp` after restart: `plugin:rag:ragtools` should now expose `search_knowledge_base`, `list_projects`, `index_status` to the model (requires Claude Code session restart so the deferred-tool registry re-indexes).

## [0.3.1] — 2026-04-14

Hotfix for a broken plugin-level MCP auto-wiring. Two compounding bugs in v0.3.0's `.mcp.json` prevented Claude Code from ever loading the `ragtools` MCP server on packaged Windows installs: the file shipped the flat shape without the `mcpServers` wrapper (which the plugin loader rejects for stdio servers), and it hardcoded `command: "rag-mcp"` which only exists on dev pip installs — packaged Windows ships `rag.exe` only. `/mcp` reported *"Failed to reconnect to plugin:rag:ragtools"* and the doctor `mcp-dedupe status` row did not catch either bug because it only counted duplicates. Closes the gap.

### Added
- **`scripts/rag_mcp_launcher.py`** — new cross-mode Python launcher (stdlib only, ~100 lines). Resolves the canonical ragtools binary at runtime and `os.execvp`-replaces itself with it so Claude Code's stdio pipe connects to the real MCP server directly. Resolution order: (1) `GET http://127.0.0.1:21420/api/mcp-config` with a 1-second timeout — the running service is the authoritative source for this install mode; (2) `rag` on PATH → exec `rag serve` (packaged Windows/macOS/Linux); (3) `rag-mcp` on PATH → exec `rag-mcp` (dev pip install); (4) fail loudly to stderr with exit code 127 so `/mcp` surfaces the failure. Supports `--dry-run` for smoke-testing (prints the resolved `{command, args}` as JSON and returns without exec).
- **D-018** in `docs/decisions.md` — binding decision. Plugin-level `.mcp.json` uses the wrapped shape (`{"mcpServers": {...}}`) and delegates command resolution to the cross-mode launcher. Overrides the flat-shape claim in D-015 for stdio servers, which was based on the `devops-plugin` pattern but empirically does not work for `rag-plugin` (confirmed by `/mcp` failure; corroborated by every stdio example in `claude-plugins-official-main/` using the wrapped shape). Does not touch SSE/HTTP plugins — flat shape remains acceptable there.

### Changed
- **`rag-plugin/.mcp.json`** — rewritten. Now uses `{"mcpServers": {"ragtools": {"type": "stdio", "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]}}}`. The `${CLAUDE_PLUGIN_ROOT}` variable is expanded by Claude Code's plugin loader at registration time.
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` hardened. No longer just counts duplicates. Now parses the plugin-level `.mcp.json` and asserts four invariants: file exists and is valid JSON; top-level `mcpServers.ragtools` key is present (catches the v0.3.0 schema bug); `command` resolves on PATH via `shutil.which` (catches the wrong-command bug); and when the launcher pattern is detected, the launcher script file is readable. Plugin-level failures are surfaced before duplicate-count issues because a broken plugin-level registration means ragtools will not load at all.
- **`rag-plugin/commands/rag-doctor.md`** — MCP registrations row documents the five new error states produced by the hardened `mcp-dedupe status`: schema bug, missing wrapper, command-not-on-PATH, launcher-missing, and the original missing-file case. Each maps to a clear remediation.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.0` → `0.3.1`.
- **`rag-plugin/README.md`** — the "Auto-wire" bullet now reflects the cross-mode launcher pattern and no longer assumes `rag-mcp` is on PATH.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A rewritten to document the wrapped shape + launcher. The old flat-shape snippet is retained as "legacy (v0.3.0 and earlier)" with a note explaining why it stopped working.

### Rationale
This is a shipped bug, not a feature. The v0.3.0 plugin was demonstrably broken for the primary install target (packaged Windows) and the doctor check that was supposed to catch MCP-wiring regressions did not parse the file it was checking. The fix has to be generic (no single command name works across every supported install mode), so command resolution is delegated to a launcher script that asks the running service first and falls through to PATH probing. The schema fix is the canonical Claude Code plugin shape documented in `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`. The doctor hardening is the regression-prevention layer the original bug report explicitly called out as missing.

### Verification
- Static validation: `python plugins/validate_plugin.py rag-plugin` passes.
- Schema sanity: `python -c "import json; d=json.load(open('plugins/rag-plugin/.mcp.json')); assert 'ragtools' in d['mcpServers']"` exits 0.
- Launcher dry-run: `python plugins/rag-plugin/scripts/rag_mcp_launcher.py --dry-run` prints `{"command": "<resolved path>", "args": ["serve"]}` on packaged Windows install where `rag.exe` is on PATH.
- Live MCP: after a Claude Code restart, `/mcp` reports `plugin:rag:ragtools connected` and `mcp__plugin_rag-plugin_ragtools__search_knowledge_base(query=...)` returns results instead of `Failed to reconnect`.

## [0.3.0] — 2026-04-14

Post-roadmap amendment #3. Ships the **Tier-2 guided-enforcement UserPromptSubmit retrieval-reminder hook** with lightweight observability. Closes the advisory-only gap in the D-016 CLAUDE.md rule by adding a harness-enforced layer that injects a system reminder at the moment of answering, not just at session start. Also includes the canonical marker-wrapped upgrade to `~/.claude/CLAUDE.md` on the development machine.

### Added
- **`rag-plugin/hooks/prompt_retrieval_reminder.py`** — new `UserPromptSubmit` hook script, ~230 lines. Python 3 stdlib only (`json`, `os`, `re`, `sys`, `time`, `urllib.*`). Two-phase decision: Phase A shape gate (question-like OR possessive-domain, NOT current-context), Phase B domain probe via `GET /api/search?top_k=1&compact=true` with a 1-second timeout. Injects a ~10-line reminder via `hookSpecificOutput.additionalContext` when both phases pass. Silent-passes in every other case. Honors D-007 (never deny, never block), D-008 (compact reminder ~200 tokens), and D-012 (observability log contains zero user content).
- **`rag-plugin/scripts/analyze_hook_decisions.py`** — new maintainer tool, ~150 lines. Reads `~/.claude/rag-plugin/hook-decisions.log` and prints aggregate stats: decisions by action tag, probe-score histogram, shape-gate pass rate, reminder-injection rate, hook version distribution, tuning hints. Read-only, stdlib only, takes no arguments.
- **`/config hook-observability {status|on|off|analyze|clear}`** — new subcommand group. Controls the hook-decisions log. Default **enabled** (opt-out via `~/.claude/rag-plugin/.hook-observability-disabled` marker file). `analyze` invokes the analyzer script; `clear` deletes the log with typed `CLEAR` confirmation.
- **Observability log at `~/.claude/rag-plugin/hook-decisions.log`** — JSONL, append-only. Schema: `{ts, shape_match, probe_match, probe_top_score, action, prompt_length, hook_version}`. Zero user content. D-012 aligned.
- **D-017** in `docs/decisions.md` — the binding decision, terminology correction ("Tier 2 = guided, Tier 3 = strong"), observability-first escalation rationale, D-001/D-012 non-violation argument.

### Changed
- **`rag-plugin/hooks/hooks.json`** — now registers two hooks: the existing `PreToolUse` Bash lock-conflict guardrail AND the new `UserPromptSubmit` retrieval-reminder. Both use the plugin-level format with `matcher` field (`"Bash"` and `"*"` respectively).
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.2.0` → `0.3.0`.
- **`rag-plugin/commands/rag-config.md`** — four feature groups now (was three). New `hook-observability` subcommand group documented with per-subcommand steps. Unified `status` dashboard now reports four rows.
- **`rag-plugin/ARCHITECTURE.md`** — layer diagram updated with the new `UserPromptSubmit` hook, the new `scripts/` directory, and the plugin's right to inject `hookSpecificOutput.additionalContext`. Forbidden list unchanged (the hook never wraps or calls `search_knowledge_base` — the `/api/search` probe reads only `results[0].score`, never result content).
- **`rag-plugin/README.md`** — status badge `v0.2.0` → `v0.3.0`. Added "Tier-2 UserPromptSubmit retrieval-reminder hook" as a new capability bullet under "What this plugin IS". Updated "What we record" section to document the hook-decisions log schema alongside the existing telemetry description.
- **`~/.claude/CLAUDE.md`** (on the development machine) — canonical marker-wrapped upgrade applied via direct splice. Manually-written Section 0 (29 lines, no markers) replaced with the marker-wrapped v0.2.0 canonical block (33 lines). Backup at `~/.claude/CLAUDE.md.bak-pre-claude-md-install`. This is outside the plugin repo and does not ship with the release, but the operation is documented here for completeness.

### Rationale
The D-016 CLAUDE.md rule was correct as a first step but insufficient on its own. User incident: *"What is the process for emergency assistance requests?"* — rule loaded, still skipped. Two root causes:

1. **CLAUDE.md is advisory.** The harness doesn't enforce it; Claude reads it and chooses whether to follow it per-turn.
2. **Model judgment gap.** Even when the rule is read, classifying a question as "domain" vs "general" is fuzzy without explicit `my notes` signals.

Fix: add a **harness-enforced** layer via `UserPromptSubmit`. The hook always runs. When the shape heuristic + domain probe both pass, a reminder is injected into the model's context **at the moment of answering** (not at session start). Claude can still choose to ignore the reminder, but failure mode #1 (forgot the rule) is closed, and failure mode #2 (misjudged the domain) is sharply reduced by surfacing the reminder right when the decision is being made.

Observability is paired with the hook so the Tier-2-vs-Tier-3 decision can be data-driven. If the reminder alone is sufficient, we never ship Tier 3 (pre-fetch) and save the context cost. If not, we have the data to justify the escalation.

**Key safety properties preserved:**
- Hook never blocks, denies, or throws. Silent-pass on any error.
- Probe is a confidence check (`results[0].score` only), not a retrieval — never reads content.
- Observability log contains zero user content (metadata only).
- Default-enabled observability is consistent with diagnostic syslogs; opt-out is one command.
- `D-001` (ops-only, never search) non-violation: registering a reminder ≠ wrapping the MCP.

### Verification
- 9 unit tests via echo-pipe (current-context, trivia, low-probe, high-probe, service-down, malformed JSON, no user_prompt, possessive domain, question+current-context). All pass.
- Emergency-assistance regression test: probe returned score 0.813, reminder injected correctly.
- Analyzer script run against 9 real log entries: stats render correctly, tuning hints fire appropriately.
- Validator: 9 commands, 1 skill, 1 hooks file, 0 errors (same 2 documented stale-validator false positives on hooks.json from Phase 6).

## [0.2.0] — 2026-04-14

Post-roadmap amendment. Ships the CLAUDE.md retrieval rule as an auto-installed plugin asset, adds MCP-duplicate detection/cleanup, and wires both into `/setup`, `/doctor`, `/rag-repair`, and `/config`.

### Added
- **`rules/claude-md-retrieval-rule.md`** — new top-level `rules/` directory. Contains the single source of truth for the Section-0 retrieval rule block delimited by machine-readable `<!-- rag-plugin:retrieval-rule:begin v=0.2.0 -->` / `<!-- rag-plugin:retrieval-rule:end -->` markers. Commands splice this block into target CLAUDE.md files idempotently.
- **`/config claude-md status|install|remove [--yes] [--project]`** — new subcommand group. Installs, upgrades, removes, or reports on the retrieval rule in `~/.claude/CLAUDE.md` (or `<cwd>/CLAUDE.md` with `--project`). Idempotent. Backs up before writing. Atomic writes only.
- **`/config mcp-dedupe status|clean [--yes]`** — new subcommand group. Scans `~/.claude.json` (top-level and per-project `mcpServers`) and `~/.claude/.mcp.json` for duplicate `ragtools` MCP registrations that conflict with the plugin-level `.mcp.json`. Removes duplicates atomically, leaving the plugin-level one as canonical.
- **`/setup` Branch C Step C.2b** — detects and removes duplicate MCP registrations before wiring. Delegates to `/config mcp-dedupe clean --yes`.
- **`/setup` Branch C Step C.5** — installs the retrieval rule into `~/.claude/CLAUDE.md` as part of first-time setup. Delegates to `/config claude-md install --yes`. Reminds user the rule takes effect in the next session.
- **`/doctor` — two new rows** in the diagnostic summary table: `CLAUDE.md rule` (INSTALLED v<N> / MISSING / OUTDATED / TARGET MISSING) and `MCP registrations` (1 canonical / N duplicates found / plugin-level missing). Each maps to a remediation command.
- **`/rag-repair` — two new plugin-behavior classifier IDs**: **P-RULE** (retrieval rule missing → `/config claude-md install`) and **P-DEDUPE** (duplicate MCP registrations → `/config mcp-dedupe clean`). These are separate from the F-001..F-012 catalog, which is reserved for ragtools product failures.
- **D-016** in `docs/decisions.md` documenting the retrieval-rule decision with the incident context, safety rules for touching user CLAUDE.md files, and the non-violation of D-001 (installing a workflow instruction is not the same as wrapping a search tool).
- **Extended D-015** scope documentation — the D-015 entry now references `/config mcp-dedupe` as the dedupe mechanism.

### Changed
- **`plugin.json` version bumped** `0.1.0` → `0.2.0` (minor bump — new functionality, no breaking changes).
- **`ARCHITECTURE.md` layer diagram updated** with the new `RULES (1)` layer between references and product surfaces, and a new `USER CONFIG (external)` layer showing the four files the plugin writes to with care (`~/.claude/CLAUDE.md`, `~/.claude.json`, `~/.claude/.mcp.json`, and the plugin's own `.mcp.json`).
- **`README.md`** updated with the v0.2.0 auto-install behavior under "What this plugin IS".

### Rationale
User incident — asked *"What is the process for emergency assistance requests?"*. The ragtools MCP was loaded and the answer was in `tq-workspace/planing/Alaqraboon/_Emergency_Assistance_Procedure_en.md` at confidence 0.80. Claude never called `search_knowledge_base` and said *"I don't have information about an 'emergency assistance request' process."* This was a retrieval failure: the tool existed, but nothing instructed Claude *when* to use it.

Fix: ship a workflow instruction block (`rules/claude-md-retrieval-rule.md`) that the plugin's setup and repair commands inject into the user's `~/.claude/CLAUDE.md`. The rule loads at session start and applies globally across all projects — no per-project configuration needed. Versioned with begin/end markers for idempotent upgrade and clean removal. Safety-gated like every other write operation in the plugin: backup, atomic write, confirmation, splice by marker.

Paired with MCP-duplicate cleanup (`/config mcp-dedupe`) so users migrating from v0.1.0 (where they may have manually wired ragtools via `~/.claude.json`) get a clean single-registration state after upgrading.

## [0.1.0] — 2026-04-14

Initial release. All 10 phases (0–9) of the rag-plugin roadmap shipped.

### Phase 0 — Foundation, Boundaries, Scaffold

- Plugin manifest at `.claude-plugin/plugin.json`
- README, LICENSE (MIT), ARCHITECTURE.md (layer-ownership diagram + forbidden list + 5-question boundary self-test)
- `docs/decisions.md` with 13 binding decisions (D-001..D-013) covering scope, transport, references bundling, install discovery, service-down behavior, skill granularity, hook posture, output verbosity, macOS posture, plugin name, versioning, telemetry, helper genericity
- Marketplace registration as the 7th entry in `plugins/.claude-plugin/marketplace.json` under category `productivity`

### Phase 1 — Doc to References Library

- Split the 21-section `ragtools_doc.md` into 16 topic-focused reference files under `skills/ragtools-ops/references/` plus `INDEX.md` and `_meta.md`
- Stable failure IDs `F-001..F-012` defined in `known-failures.md`
- Stable gap IDs `G-001..G-010` defined in `gaps.md`
- Every file under the 400-line skill-loadable budget; full cross-link discipline

### Phase 2 — Core Skill and Status Surface

- `skills/ragtools-ops/SKILL.md` — keyword-rich router with 15+ trigger phrases including error-message substrings, 14-row routing table mirroring `INDEX.md`, 3-phase body (detect mode → route → answer/handoff)
- `commands/rag-status.md` — one-screen state probe (mode banner + state table + per-project table); HTTP API parallel fetch when service UP, CLI fallback when DOWN
- `commands/rag-doctor.md` — wraps `rag doctor`, classifies findings against F-001..F-012, special-cases F-010 (`Collection NOT FOUND` while service up = expected, NOT a bug), optional `--logs` mode
- Mode banner format established (6 lines, fixed) and reused across all later commands

### Phase 3 — Setup and Install Workflows

- `commands/rag-setup.md` — conversational 3-branch onboarding (Branch A install / Branch B start service / Branch C wire MCP + add project)
- Hard refusal for Intel macOS (G-004) and Linux packaged install (G-001)
- MCP wiring reads `/api/mcp-config` from the running service — never hand-constructed
- `references/setup-walkthrough.md` long-form companion with time budget table and per-platform install procedures

### Phase 4 — Diagnostics and Repair Playbooks

- `commands/rag-repair.md` — 3 input modes (free-text symptom / `--symptom F-NNN` / `--scan-logs`), 16-row classifier rubric with 4 disambiguation rules (most importantly, F-010 vs F-003 special case), all 8 walkable playbooks from `repair-playbooks.md`, typed-confirmation gates on every destructive step
- `agents/rag-log-scanner.md` — Haiku-tier scoped agent. 13 catalog patterns + 4 informational substrings. Returns single JSON object, never diagnoses, never invents F-IDs

### Phase 5 — Project Management Integration

- `commands/rag-projects.md` — single command with 6 subcommands (`list`, `add`, `remove`, `enable`, `disable`, `rebuild`)
- HTTP API only — never edits `config.toml` directly (D-002, F-001)
- Refuses write ops when service is down (D-005)
- 5-provider cloud-sync detection warning gate (Syncthing, iCloud, OneDrive, Dropbox, Google Drive)
- `remove` requires typing the project ID verbatim; all-projects `rebuild` requires typing `REBUILD`

### Phase 6 — Guardrail Hooks and Token-Efficient Outputs

- `hooks/hooks.json` — PreToolUse Bash guardrail in the official `security-guidance` plugin format
- `hooks/lock_conflict_check.py` — Python 3 stdlib-only script. 7-pattern matcher + 1-second urllib `/health` probe + two-condition gate (matcher AND service up). Returns `permissionDecision: ask` only when both hold; never `deny`. Live-tested with 8 echo-pipe payloads
- `references/output-conventions.md` — codifies D-008 as 8 binding rules with per-command line budgets

### Phase 7 — Upgrade and Recovery Tooling

- `commands/rag-upgrade.md` — version detection + GitHub releases lookup + 3 platform-specific upgrade walkthroughs (Windows installer / macOS tarball / dev source pull). Read-only — never auto-downloads
- `commands/rag-reset.md` — 3 escalation levels (`--soft` rebuild via HTTP API / `--data` delete data dir / `--nuclear` delete entire RAGTools dir) with 1×/2×/3× typed-`DELETE` gating
- Hard block on pre-v2.4.1 versions (F-001 is data-loss-tier)
- Service-state enforcement: `--soft` requires UP, `--data`/`--nuclear` require DOWN
- `references/upgrade-paths.md` — 4 upgrade modes with what-preserves and what-can-go-wrong tables

### Phase 8 — Cross-Platform Hardening

- `references/macos-specifics.md` — 8-aspect honest table, per-command behavior differences, MPS-must-stay-disabled rule, 6-row Windows-vs-macOS playbook variations table
- `references/linux-dev-mode.md` — dev-mode-only documentation with G-001 cited up front, CWD-relative path table, "wrong-CWD footgun" warning that ties to F-006 misclassification
- `references/INDEX.md` — added 3 new routing rows (macOS / Linux / upgrade-paths)
- Audit confirmed: existing commands already include macOS branches alongside Windows from Phases 4 and 7. No silent Windows-only assumptions

### Phase 9 — Polish, Distribution, Telemetry, Maintenance

- README finalized with full command catalog, troubleshooting table, limitations table (G-001..G-010), telemetry posture ("What we record"), architecture diagram
- This CHANGELOG file
- `commands/rag-sync-docs.md` — **maintainer-only** with `disable-model-invocation: true`. Reads upstream `ragtools_doc.md` and reports which references have drifted. Never auto-rewrites
- `commands/rag-config.md` — local-only opt-in usage-logging toggle. JSONL at `~/.claude/rag-plugin/usage.log`. Default off. No network egress, ever (D-012)
- `ARCHITECTURE.md` and `docs/decisions.md` finalized with Phase 9 closure note
- Final inventory documented in `<final_status>` of Phase 9 report

## Known issues

### Validator false positives (carried from Phase 6)

`validate_plugin_simple.py` (in `plugins/validate_plugin.py` sibling) line 267 has a stale `valid_events` list that predates the official Anthropic plugin hooks.json wrapper format. It treats the top-level `description` and `hooks` keys in `hooks/hooks.json` as unknown event names and emits 2 warnings. The same warnings would fire on the official `security-guidance` plugin run through this validator. The full `validate_plugin.py` validator has the correct event list. Fixing the simple validator is out of scope for this plugin.

These are **validator bugs**, not `rag-plugin` issues. Hook structure is verified to match the canonical Anthropic format byte-for-byte.

## Compatibility

- **ragtools versions:** 2.4.x (per D-011)
- **Claude Code:** any version that supports `.claude-plugin/plugin.json` manifest, slash commands, skills, agents, and PreToolUse hooks
- **Python:** the hook script uses Python 3 stdlib only (no third-party deps)
- **Operating systems:** Windows (primary), macOS arm64 (Phase 1), Linux dev mode only

## License

MIT — see `LICENSE`.
