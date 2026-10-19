# qa-browser

![Version](https://img.shields.io/badge/version-0.7.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Framework-agnostic browser QA and role-based smoke testing.

This plugin drives the [`chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp) or [`playwright-mcp`](https://github.com/microsoft/playwright-mcp) servers to log in as each role, walk through the UI, capture evidence (screenshot + console + network), and produce a PASS / BLOCKED / NOT-TESTABLE table for UAT signoff. It enforces evidence discipline — no silent "looks good" passes — and refuses destructive operations on non-disposable data.

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
| `verify-identity-and-rbac` | Live identity + RBAC proof via status codes; three-layer denial checklist (route/API + service/backend + UI) |
| `host-scoped-auth-headers` | Host-scope preview-bypass/auth headers so cross-origin data calls survive CORS preflight |
| `anti-fraud-and-guard-hygiene` | A client-rendered barcode/QR/SVG/badge is NOT authentication (no signature/binding/expiry); host canonicalization + no-Origin-and-no-Referer CSRF reject |
| `uat-readiness-report` | Composing the final PASS / BLOCKED report; includes a copy-paste role × route smoke-report template |
| `defect-triage-and-closure` | The gate before "working as designed" / "cannot reproduce" / "external blocker" / "won't do" is written; spec granularity, exact-gesture repro, the reporter's workaround as diagnostic, file-before-fix ordering, re-probing a stale blocker |

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
| `SessionStart` | startup | If `.qa-browser.local.json` exists in the working directory: warns (as hook context Claude sees, plus a user-visible message) when it is tracked by git, missing from `.gitignore`, unparseable, or its `targetUrl` matches a production marker. Silent when no config exists. Advisory only — never blocks |
| `PreToolUse` | `navigate_page` / `browser_navigate` tool calls | Blocks (exit 2) navigation to a URL containing a production marker substring (`prod`, `production`, or `productionMarkers` from the config). There is no in-session approval: the only override is launching Claude Code with `QA_BROWSER_ALLOW_PRODUCTION=1`. Other navigation paths (new pages, link clicks, other browser MCPs) are not gated |

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

**Credential storage:** written to `.qa-browser.local.json` in the project root. This file MUST be gitignored. If it is tracked by git, the SessionStart hook surfaces a DANGER warning and the commands instruct Claude to stop; this is not enforced by code.

## MCP server dependencies

This plugin drives one of:

- [`chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp) — preferred for performance + DevTools-grade introspection.
- [`playwright-mcp`](https://github.com/microsoft/playwright-mcp) — preferred for cross-browser coverage.

`/qa-target` checks for at least one of them and surfaces a clear "please install one" message if neither is loaded. It does **not** auto-install MCP servers.

## What this plugin deliberately does NOT do

- Replace a unit / integration test suite. This is acceptance-level UI QA, not the test pyramid base.
- Drive headless API testing without a browser. Use a dedicated API testing tool for that.
- Author the admin panel itself. See [`react-kit`](../react-kit-plugin/README.md) for that.
- Document QA SOPs / runbooks. See [`docs-wiki`](../docs-wiki-plugin/README.md) for that.
- Manage credentials in any way other than the local gitignored file. No vault, no secrets manager.

## Safety rules baked in

1. Production URL gate (hook) — a navigate call to any URL containing `prod` or `production` (configurable substrings) is blocked unless Claude Code was launched with `QA_BROWSER_ALLOW_PRODUCTION=1`. Substring match only: a production host without a marker in its URL is not caught unless you add it to `productionMarkers`.
2. Destructive-action discipline (skill guidance, not a hook) — `delete`, `purge`, `truncate`, `drop` actions require explicit per-action approval AND a disposable-data signal.
3. Credential redaction (skill/agent guidance, not a script) — Claude is instructed to redact passwords, JWTs and OTP codes from console / network captures before writing them.
4. Tracked-credentials warning (hook) — the SessionStart hook warns when `.qa-browser.local.json` is tracked by git; the refusal to continue is an instruction to Claude, not a code-level block.

## Installation

This plugin is published as part of the `taqat-techno-plugins` marketplace. To install:

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace** and enter `https://github.com/taqat-techno/plugins.git` (skip if already installed).
4. Find **qa-browser** and click **Install**.
5. (Recommended) install `chrome-devtools-mcp` or `playwright-mcp` from their respective marketplaces.

## Release history

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold |
| `0.2.0` | Initial skills, 5 commands, 2 agents, 2 hooks (target check + production gate) |
| `0.3.0` | Live identity/RBAC proof skill + host-scoped auth-header skill |
| `0.4.0` | Anti-fraud + guard-hygiene skill; RBAC three-layer checklist; UAT smoke-report template |
| `0.5.x` | Marketplace-wide frontmatter fixes; behavioural eval suite |
| `0.6.0` | Production-override audit line reaches Claude; UTF-8 hook I/O |
| `0.7.0` (current) | Evidence agent can drive the browser; SessionStart warnings become visible; portable hook launcher; README matches shipped behaviour |

See [`CHANGELOG.md`](./CHANGELOG.md) for details.

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
