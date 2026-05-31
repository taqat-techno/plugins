# Changelog

All notable changes to `qa-browser-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

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
- Genericness sweep — grep over all skill / command / agent / hook files for `aqraboon|beneficiar|coupon|qid|qatar|taqatfortechnology|AdminUser|AppConfig|HELPDESK|SUPER_ADMIN|alaqraboon|indogate`: 0 hits.

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
