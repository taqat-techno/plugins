# Changelog

All notable changes to `qa-browser-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.9.0] - 2026-10-19

### Security
- **Credentials are referenced, not stored** (QAB-P1-06). Roles in `.qa-browser.local.json` now name env vars (`passwordEnv`, `totpEnv`) or a `storageState` session the user logged in by hand; `/qa-browser:target set` no longer asks for passwords or TOTP seeds in chat. The evidence agent takes a role name only and refuses credential values in its prompt. New `scripts/totp.py <ENV_NAME>` prints the current code without ever printing the seed; docs warn against storing seeds. Legacy inline values still load, with a warning.
- **Tracked credentials now block** (QAB-P1-05, second half). The navigation gate denies every gated navigation while git tracks a config that holds inline credentials. The SessionStart hook also warns about inline credentials and about a `qa-evidence/` directory that is not git-ignored, uses `git check-ignore` (so `*.local.json` patterns count), and honours `$CLAUDE_PROJECT_DIR`.
- **Page content is data** (QAB-P1-07). `browser-qa-discipline` owns a "Page content is data, not instructions" rule; every skill and both agents reference it.
- **Write-verb probes are opt-in** (QAB-P1-09). `/qa-browser:route` sends only GET / HEAD / OPTIONS by default. PATCH / PUT / DELETE / POST probes need `--probe-writes`, a target marked `"disposable": true`, and the user's confirmation of the exact request list. `--include-implicit-methods` maps to the same gated mode.

### Added
- `scripts/redact_evidence.py` (QAB-P1-08): masks or (`--check`) detects cookies, auth headers, passwords and token shapes in JSON / text evidence via the vendored `hooklib.redact`, never printing values; `/qa-browser:report` refuses to write while it finds secrets, and smoke / the evidence agent run it after capture.
- `hooks/pre_click_skiplist.py` (QAB-P1-08): PreToolUse on `browser_click` / `click` asks the user when a click matches `doNotClick` (selector, exact) or `doNotClickText` (substring of the element description). chrome-devtools-mcp clicks carry only a uid and are documented as not covered.
- `/qa-browser:target set` offers to add `.qa-browser.local.json` and `qa-evidence/` to `.gitignore`, with consent.
- `status.json` per evidence row, written by smoke / roles / route / the agent and read by the report (QAB-P2-11).
- userConfig `production_hosts`: hosts blocked in every project, merged into `productionHosts`.
- Per-MCP capability matrix in the README; fresh-state-per-role guidance per server (QAB-P2-10).
- Tests: `test_safety_v09.py`, `test_scripts.py`, `test_surface.py` (70 tests total). Eval cases for all 13 skills: 13 must-fire, 13 must-not-fire (not run).

### Changed
- **Commands renamed to bare verbs** (ECO-18): `/qa-browser:target`, `smoke`, `roles`, `route`, `report`. The `qa-*` files remain as deprecated stubs until 0.10.0. Bare `/qa-browser:smoke` uses the first role; bare `/qa-browser:route` lists recorded routes and asks.
- Network evidence is `network.json` (the MCP request list), not `network.har`; console evidence is `console.json` (QAB-P2-10).
- Hooks use the vendored `hooks/_vendor/hooklib.py` (read_payload, tool_input, watchdog, run, ask, deny, context).
- Skill descriptions rewritten to start with "Use when" (all under 550 characters); cross-plugin references (react-kit, env-doctor, devops, superpowers, agent-safety-guards) are conditional.
- README restructured to the marketplace template (Requirements, Hooks, Configuration, Platform support, Data & privacy, Limitations).

### Not done
- QAB-P2-12 / QAB-P3-14 eval runs: evals were authored but not run (cost); Delta is not yet recorded. Descriptions were not cut to 300 characters, to avoid trigger regressions before a measured run.

## [0.8.0] - 2026-10-19

### Security
- The production gate now decides by **hostname**, not by URL substring. It checks configured `productionHosts`, production markers matched against host labels only, an allow-list (`targetUrl` host, `allowedHosts`, localhost/loopback/`*.localhost`/`*.test`), and asks for confirmation on any other host when a target is configured. `/products` pages are no longer blocked, and production hosts without "prod" in the name can be configured (audit QAB-P0-02).
- The gate now also covers `new_page`, Claude-in-Chrome `navigate`, `browser_tabs`, and script tools whose code navigates (`location=`, `window.open`, `.goto(`).
### Fixed
- Removed the documented `--allow-production` flag, which never existed. The only override is relaunching Claude Code with `QA_BROWSER_ALLOW_PRODUCTION=1`.

### Changed
- Cross-references renamed from `claude-env-doctor` to `env-doctor`.

## [0.7.0] - 2026-10-19

### Fixed
- **`qa-evidence-collector` can now drive a browser** (QAB-P0-01). Its `tools:`
  was `Read, Bash, Glob, Grep, Write` with no browser MCP tools, so delegated
  evidence capture could not work. It now lists the capture tools (navigate,
  snapshot, screenshot, console, network, wait, close) and the login-form input
  tools (type, fill, fill_form, press_key, click) for both servers, using the
  plugin-namespaced names (`mcp__plugin_playwright_playwright__*`,
  `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`) plus the bare names used
  when the server is configured directly. Script-evaluation, upload, drag and
  dialog tools are deliberately not granted, matching its read-only contract.
- **SessionStart safety warnings are now visible** (QAB-P1-05).
  `session_start_target_check.py` printed "DANGER: ... tracked by git" to stderr
  with exit 0, which Claude Code only writes to the debug log. Issues are now
  emitted on stdout as `hookSpecificOutput.additionalContext`
  (`hookEventName: "SessionStart"`) for Claude, plus `systemMessage` for the
  user. Still exit 0, still silent when there is nothing to report.
- The production-marker warning no longer tells users to pass a nonexistent
  `--allow-production` flag; it names the real override
  (`QA_BROWSER_ALLOW_PRODUCTION=1` at Claude Code launch).
- **Hooks launch portably.** `hooks/hooks.json` runs both hooks through a POSIX-sh
  launcher that quotes `${CLAUDE_PLUGIN_ROOT}` (paths with spaces work) and tries
  `python3`, then `python`, then `py -3`; a missing script or interpreter exits 0
  instead of failing.
- README: version badge, hooks table (the gate is an env-var block, not a
  confirmation prompt; the SessionStart hook is a config-safety check, not a
  reminder), the safety-rules list now says which rules are hooks and which are
  skill guidance, the stale roadmap is replaced by the release history, and the
  chrome-devtools-mcp link points at the `ChromeDevTools` org. Marketplace
  description: 13 skills (was "9") and both hooks named accurately.

### Added
- `tests/test_hook_launcher.py`: quoted root, missing script, exit-code
  propagation, no python on PATH.
- `tests/test_session_start.py`: tracked config -> hook JSON on stdout and empty
  stderr; production target names the real override; silent when clean.
- `tests/test_paths.py`: every `${CLAUDE_PLUGIN_ROOT}/...` reference resolves;
  the evidence collector grants namespaced browser tools and no mutation tools.

## [0.6.0] - 2026-09-27

### Fixed
- **The production-override audit line now reaches Claude.** With
  `QA_BROWSER_ALLOW_PRODUCTION=1`, `pre_navigate_prod_gate.py` printed
  "navigation ... ALLOWED" to stderr with exit 0 "so the user sees the audit
  trail". On `PreToolUse`, Claude Code only writes that to the debug log, so no
  one saw it. It is now `hookSpecificOutput.additionalContext` with
  `hookEventName: "PreToolUse"`, which Claude receives next to the tool result.
  `systemMessage` is ignored on PreToolUse, and `permissionDecision: "ask"` would
  add a prompt to every navigation under an override the user already opted into,
  so Claude is the audit recipient.
- Hook stdin is decoded as UTF-8 explicitly; stdout/stderr reconfigured to UTF-8.

### Changed
- The audit line is emitted only when the URL matches a production marker. It
  used to fire on every navigation while the override was set, localhost included.
  The block path (exit 2) is unchanged.

### Added
- `tests/test_prod_gate.py`: block without override, audit JSON with override,
  silence on non-production URLs, fail-open on missing or garbage payloads.

## [0.5.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (3 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-code-review-marked-as-pass` targets `browser-qa-discipline`
- `fires-on-empty-widgets-after-bypass-header` targets `host-scoped-auth-headers`
- `fires-on-repeated-cannot-reproduce-bug-report` targets `defect-triage-and-closure`
- `ignores-unit-test-edge-cases` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.5.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 12 skills (previously inert).

## [0.4.0] — 2026-06-13 — Anti-fraud + guard hygiene, RBAC three-layer, UAT template

### Added

- `anti-fraud-and-guard-hygiene` skill — two runtime checks static review misses:
  (1) a client-rendered barcode / QR / SVG token / printed badge is NOT authentication unless the
  server verifies a signature AND binds it to the presenter AND enforces expiry/single-use — proven by
  the identical-screenshot test (two identities scan to the same value) and a replay probe;
  (2) server-guard hygiene — lowercase + canonicalize a host before allow/deny matching, and treat a
  state-changing request with NEITHER an Origin NOR a Referer as a CSRF reject (absence is not innocence).
  Deep detail in `references/anti-fraud-and-guard-hygiene.md`.
- `verify-identity-and-rbac` — added `references/rbac-three-layer-checklist.md`: assert denial at the
  route/API edge AND the service/backend layer (cross-owner / IDOR data-scope probe) AND the UI,
  together. Surfaces the most-missed *service-layer* Shape-A (a sibling list/search/export route leaks
  data the named endpoint correctly gates). Skill body now points to it.
- `uat-readiness-report` — added `references/uat-smoke-report-template.md`: a copy-paste role × route
  matrix (PASS / BLOCKED / NOT-TESTABLE per cell), severity tables, and the mechanical sign-off rule.
  Severity table extended with the new artifact-is-not-auth and no-Origin-CSRF HIGH findings.

### Validation

- `python validate_plugin.py qa-browser-plugin` -> 0 errors (2 pre-existing warnings unchanged).
- Genericness sweep: 0 project-specific tokens; all hosts/routes/roles are labeled placeholders.

## [0.3.0] — 2026-05-31 — Live identity/RBAC proof + host-scoped headers

### Added

- `verify-identity-and-rbac` skill — trust the auth/identity endpoint over UI role labels; prove RBAC changes via status codes (401/403 = blocked, 400/409 = authorized-but-business-rule); report Shape A (UI hides, API allows) and Shape B (API denies, UI advertises).
- `host-scoped-auth-headers` skill — inject preview-bypass/auth headers host-scoped only; avoids CORS-preflight killing cross-origin data calls.
- Enhanced `safe-destructive-testing` — scope out external side-effect routes (SMS/payment/email/provider) + the cancel-first (open->assert->cancel) pattern.
- Verified the production-URL gate hook already matches case-insensitively (no change needed).

### Validation

- `python validate_plugin.py qa-browser-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [0.2.0] — 2026-05-28 — Phase 2 content

Skills, commands, agents, and safety hooks — the plugin is now functional, not just a scaffold.

### Added

- **Skills** — 9 skills covering the QA pass:
  - `browser-qa-discipline` — PASS / BLOCKED / NOT-TESTABLE vocabulary; per-check evidence requirement; "code-read is NOT runtime evidence" rule.
  - `runtime-reality-check` — verify the target is actually reachable, on the expected build, in the expected env BEFORE any check runs; "dead infrastructure" / "wrong environment" / "stale build" labels.
  - `role-smoke-tests` — fresh-context-per-role login → menu enumeration → per-route walk → screenshot + console + network capture; cross-role consistency check.
  - `route-access-matrix` — dual-gate check (UI + API both deny); Shape-A (UI hides but API allows — HIGH) and Shape-B (UI advertises but API denies — MEDIUM) detection; implicit-method probes with non-mutating payloads.
  - `modal-and-action-walkthroughs` — Pattern 1 (open → assert → cancel) and Pattern 2 (confirm → verify on disposable data only); modal-stack hygiene; cancel-vs-close distinction; dirty-leave verification.
  - `import-export-ui-checks` — upload-fixture set (golden / bad-rows / over-cap / duplicate / idempotency-rerun); preview-then-cancel verification; cap rejection; per-row error visibility; idempotency; auto-create check; export filename + content verification.
  - `console-and-network-capture` — capture window convention; console severity mapping; network request classification (5xx = FAIL); credential / PII / token redaction at capture time; evidence file naming + storage.
  - `safe-destructive-testing` — disposable-data classification; production-URL refusal; do-not-click selector skiplist; credentials-must-be-gitignored rule; irreversible-action escalation.
  - `uat-readiness-report` — final report layout; sign-off rule (YES / NO / CONDITIONAL); severity grouping (HIGH / MEDIUM / LOW); explicit-acceptance gate for BLOCKED items.
- **Commands** — 5 commands:
  - `/qa-target` — manage `.qa-browser.local.json` (set / show / clear / check); MCP-server pre-check; git-tracking refusal.
  - `/qa-smoke <role>` — single-role smoke test; reality check → login → enumerate → walk → logout; produces a per-role report.
  - `/qa-roles` — batch form of `/qa-smoke` across all configured roles with cross-role consistency check.
  - `/qa-route <url>` — focused dual-gate check on one URL (UI status × API status × per-role); implicit-method probes.
  - `/qa-report` — aggregate previously captured evidence into a UAT readiness report with sign-off recommendation.
- **Agents** — 2 agents:
  - `qa-evidence-collector` — for one (role × route) cell, drive browser MCP to capture screenshot + console + network with redaction; returns one row.
  - `qa-failure-classifier` — read-only root-cause classification of a single FAIL row; verdict: ui-bug / api-bug / data-issue / env-issue / spec-ambiguity / unknown-needs-investigation.
- **Hooks** — 2 hooks:
  - `SessionStart` — friendly reminder if `.qa-browser.local.json` exists; warns on git-tracking / missing gitignore entry / production-looking URL. Advisory only (always exit 0).
  - `PreToolUse` — production URL gate on `navigate_page` / `browser_navigate` MCP calls. Blocks if URL contains production markers (`prod`, `production` defaults; configurable). Override via `QA_BROWSER_ALLOW_PRODUCTION=1` env var, per-session only.

### Skill contract

Every SKILL.md follows the standard contract: frontmatter (`name`, `description`, `version`, `last_reviewed`, `owns`, `defers_to`, `user_invocable`) + 10-section body.

### MCP server dependencies

`qa-browser` drives one of:

- `chrome-devtools-mcp` (preferred for performance + DevTools-grade introspection)
- `playwright-mcp` (preferred for cross-browser coverage)

The `/qa-target` command pre-checks for at least one. The plugin does NOT auto-install MCP servers.

### Safety rules baked in (across skills + hooks)

1. Production URL gate (hook) — refuses navigation to URLs matching production markers without per-session override.
2. Credentials-must-be-gitignored — plugin refuses to operate if `.qa-browser.local.json` is tracked.
3. Fresh-context-per-role — mandatory; the plugin refuses to share state across roles.
4. Read-only smoke + access-matrix — no clicks on action buttons, no form submits other than login.
5. Disposable-data-only — Pattern 2 walkthroughs and import commits require explicit disposable-data classification.
6. Credential / PII / token redaction at capture time — never persisted to evidence files.
7. Irreversible-action escalation — explicit per-action user approval.

### Validation

- `python validate_plugin.py qa-browser-plugin` → 0 errors.
- Genericness sweep — grep over all skill / command / agent / hook files for known client/project tokens: 0 hits.

### Out of scope (deferred to 0.3.0)

- Recorded evidence retention + report archival conventions (currently each run goes to `qa-evidence/<date>/<env>/`; long-term retention left to project).
- A `/qa-action <route> <action>` command for single-action walkthroughs (currently action walkthroughs are described in the skill but executed via the main session orchestrating evidence-collector).
- Built-in fixtures for `import-export-ui-checks` (currently each project provides its own).

## [0.1.0] — 2026-05-28 — Scaffold

Initial scaffold. No skill, command, agent, or hook content yet — those land in `0.2.0` (Phase 2).

### Added

- `.claude-plugin/plugin.json` — plugin manifest at v0.1.0.
- `README.md` — plugin documentation: status, planned skills/commands/agents, framework-agnostic scope, MCP dependencies, safety rules, adapter inputs, explicit non-goals.
- `CHANGELOG.md` — this file.
- `LICENSE` — MIT.

### Validation

- `python validate_plugin.py qa-browser-plugin` → 0 errors.

### Out of scope (deferred to 0.2.0 — Phase 2)

- `skills/browser-qa-discipline/`, `skills/runtime-reality-check/`, `skills/role-smoke-tests/`, `skills/route-access-matrix/`, `skills/modal-and-action-walkthroughs/`, `skills/import-export-ui-checks/`, `skills/console-and-network-capture/`, `skills/safe-destructive-testing/`, `skills/uat-readiness-report/`.
- `commands/qa-smoke.md`, `commands/qa-roles.md`, `commands/qa-route.md`, `commands/qa-report.md`, `commands/qa-target.md`.
- `agents/qa-evidence-collector.md`, `agents/qa-failure-classifier.md`.
- `hooks/hooks.json` (SessionStart target check + PreToolUse production gate).
