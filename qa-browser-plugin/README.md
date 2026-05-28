# qa-browser

![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Framework-agnostic browser QA and role-based smoke testing.

This plugin drives the [`chrome-devtools-mcp`](https://github.com/anthropics/chrome-devtools-mcp) or [`playwright-mcp`](https://github.com/microsoft/playwright-mcp) servers to log in as each role, walk through the UI, capture evidence (screenshot + console + network), and produce a PASS / BLOCKED / NOT-TESTABLE table for UAT signoff. It enforces evidence discipline — no silent "looks good" passes — and refuses destructive operations on non-disposable data.

## What this plugin owns

### Skills (under `skills/`)

| Skill | Owns |
|---|---|
| `browser-qa-discipline` | PASS / BLOCKED / NOT-TESTABLE vocabulary, per-check evidence requirement, "code-read is not runtime evidence" rule |
| `runtime-reality-check` | Verify the target is actually reachable, the build is the one you think it is, before testing |
| `role-smoke-tests` | Login as each role, visit each menu item, capture screenshot + console + network |
| `route-access-matrix` | Verify each role's allowed/blocked routes at UI AND at API |
| `modal-and-action-walkthroughs` | Row actions, bulk actions, modal open/close, confirmation dialog handling |
| `import-export-ui-checks` | Upload → preview → commit → verify result |
| `console-and-network-capture` | What to capture, when to fail, redaction rules for credentials in logs |
| `safe-destructive-testing` | Disposable-data-only rule, never run delete on production data |
| `uat-readiness-report` | Composing the final PASS / BLOCKED report |

### Commands

| Command | Purpose |
|---|---|
| `/qa-smoke <role>` | Run smoke tests for one role |
| `/qa-roles` | Run smoke tests across all configured roles |
| `/qa-route <url>` | Focused check of one route across roles |
| `/qa-report` | Compile the final UAT report from captured evidence |
| `/qa-target` | Set or inspect target URL + credentials |

### Agents

| Agent | Purpose |
|---|---|
| `qa-evidence-collector` | For one role + one route, capture screenshot + console + network and produce one row of the PASS table |
| `qa-failure-classifier` | Take a failure description and classify as ui-bug / api-bug / data-issue / env-issue / spec-ambiguity / unknown |

### Hooks

| Hook | Trigger | Purpose |
|---|---|---|
| `SessionStart` | startup | Reminder to run `/qa-target` if no target configured |
| `PreToolUse` | `browser_navigate` to a URL containing `prod` or `production` | Confirmation gate — refuse without explicit user approval |

## Framework scope

**Framework-agnostic.** Requires a reachable URL + at least one role credential. Tested mental-model against:

- Next.js apps
- React SPAs (Vite / CRA / Remix)
- Django admin
- Laravel Nova / Filament
- Odoo backend
- WordPress wp-admin
- Any browser-accessible web app

The plugin **never assumes** a framework. It detects what it sees and adapts.

## Adapter inputs (asked once via `/qa-target`)

| Input | Notes |
|---|---|
| Target base URL | Staging / UAT — never production by default |
| Credential map | `{role-name: {username, password, totp?}}` |
| Optional route map | `{role-name: [allowed-routes]}` for stricter access checks |
| Optional "do not click" selectors | E.g. delete buttons on non-disposable data |

**Credential storage:** written to `.qa-browser.local.json` in the project root. This file MUST be gitignored — the plugin refuses to operate if it is tracked by git.

## MCP server dependencies

This plugin drives one of:

- [`chrome-devtools-mcp`](https://github.com/anthropics/chrome-devtools-mcp) — preferred for performance + DevTools-grade introspection.
- [`playwright-mcp`](https://github.com/microsoft/playwright-mcp) — preferred for cross-browser coverage.

`/qa-target` checks for at least one of them and surfaces a clear "please install one" message if neither is loaded. It does **not** auto-install MCP servers.

## What this plugin deliberately does NOT do

- Replace a unit / integration test suite. This is acceptance-level UI QA, not the test pyramid base.
- Drive headless API testing without a browser. Use a dedicated API testing tool for that.
- Author the admin panel itself. See [`react-admin-kit`](../react-admin-kit-plugin/README.md) for that.
- Document QA SOPs / runbooks. See [`docs-wiki`](../docs-wiki-plugin/README.md) for that.
- Manage credentials in any way other than the local gitignored file. No vault, no secrets manager.

## Safety rules baked in

1. Production URL gate — any URL containing `prod` or `production` (configurable substring) requires explicit per-session approval.
2. Destructive-action gate — `delete`, `purge`, `truncate`, `drop` selectors require explicit per-action approval AND a disposable-data signal.
3. Credential redaction — passwords, JWTs, OTP codes are redacted from console / network captures.
4. Refusal-on-tracked-credentials — plugin refuses to operate if `.qa-browser.local.json` is tracked by git.

## Installation

This plugin is published as part of the `taqat-techno-plugins` marketplace. To install:

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace** and enter `https://github.com/taqat-techno/plugins.git` (skip if already installed).
4. Find **qa-browser** and click **Install**.
5. (Recommended) install `chrome-devtools-mcp` or `playwright-mcp` from their respective marketplaces.

## Roadmap

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold |
| `0.2.0` (this release) | 9 skills + 5 commands + 2 agents + 2 hooks (target check + production gate) |
| `0.3.0` | Recorded evidence retention + report archival conventions; built-in fixtures; `/qa-action` command |
| `1.0.0` | First stable release after real-project shakedown |

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
