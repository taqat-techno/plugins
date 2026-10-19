# qa-browser

![Version](https://img.shields.io/badge/version-0.9.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What it does

qa-browser drives a browser MCP server ([chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) or [playwright-mcp](https://github.com/microsoft/playwright-mcp)) to log in as each role of a web app, walk its menus, modals and table actions, compare what the UI shows with what the API allows, and capture screenshot, console and network evidence. It reports every check as PASS / BLOCKED / NOT-TESTABLE / FAIL and compiles a UAT readiness report. Hooks block production hosts and ask before clicks on a do-not-click list.

It is for QA engineers and developers running acceptance-level checks against a staging, UAT or local deployment of any browser-accessible app (Next.js, React SPAs, Django admin, Laravel, Odoo, WordPress, ...). It does not assume a framework.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install qa-browser@taqat-techno-plugins
```

Then install one browser MCP server and restart Claude Code. Quick start:

```
/qa-browser:target set      # target URL, roles, hosts, skiplist
/qa-browser:smoke admin     # one role
/qa-browser:roles           # every role + cross-role consistency
/qa-browser:report          # UAT report from qa-evidence/
```

## Requirements

| Requirement | Why | How to check |
|---|---|---|
| A browser MCP server: chrome-devtools-mcp or playwright-mcp | All browser work goes through it | `/mcp` lists it; `/qa-browser:target` checks for its tools |
| Python 3.8+ as `python3`, `python` or `py -3` | Hooks and `scripts/` | `python3 --version` |
| `sh` (Git Bash on Windows) | The hook launcher | `sh -c 'echo ok'` |
| git (optional) | Tracked / ignored checks on the config and `qa-evidence/` | `git --version` |
| A reachable non-production target and test accounts | What is tested | `/qa-browser:target check` sends one HEAD request |

### What each MCP server can do

| Need | playwright-mcp | chrome-devtools-mcp | Claude in Chrome / other |
|---|---|---|---|
| Navigate, snapshot, screenshot | yes | yes | yes |
| Console messages | yes | yes | yes (`read_console_messages`) |
| Network request list | yes, as a list (not HAR) | yes, as a list (not HAR) | yes, as a list |
| Fresh state per role | `--isolated` or one `--storage-state` per role | `new_page` shares the profile; use `--isolated` and restart between roles | your own profile: log out and clear site data |
| Do-not-click hook can see the target | yes (`element` description, `target`) | no (only an element `uid`) | no |
| Mask secrets in tool responses | `--secrets <dotenv>` | no | no |

## Commands

| Command | What it does | Bare invocation |
|---|---|---|
| `/qa-browser:target` | Set, show, check or clear `.qa-browser.local.json` | `check` (read-only) |
| `/qa-browser:smoke [role]` | Smoke test one role: log in, walk the visible menu, capture evidence | first configured role |
| `/qa-browser:roles` | Smoke every configured role plus the cross-role consistency check | all roles |
| `/qa-browser:route [path]` | Dual-gate (UI + API) access check of one route across roles; GET / HEAD / OPTIONS only unless `--probe-writes` on a disposable target | lists recorded routes and asks |
| `/qa-browser:report` | Compile the UAT readiness report from `qa-evidence/`; refuses while the redaction scan finds secrets | latest date and env |

`/qa-browser:qa-target`, `qa-smoke`, `qa-roles`, `qa-route` and `qa-report` still work as deprecated aliases and are removed in 0.10.0.

## Skills

All skills are model-invoked (`user-invocable: false`).

| Skill | Use when |
|---|---|
| `anti-fraud-and-guard-hygiene` | A QR / barcode / badge is used as identity, or a host allow/deny or CSRF guard is under test |
| `browser-qa-discipline` | Starting a QA pass or about to call a check PASS; owns the status words and the page-content-is-data rule |
| `console-and-network-capture` | Capturing console / network evidence and redacting it |
| `defect-triage-and-closure` | About to close a defect as WAD, cannot-reproduce, external or won't-do |
| `host-scoped-auth-headers` | Adding a bypass or auth header to reach a protected preview / staging host |
| `import-export-ui-checks` | Testing an import (upload, preview, commit) or export flow |
| `modal-and-action-walkthroughs` | Walking row / bulk actions, modals, confirmations, dirty-leave |
| `role-smoke-tests` | Smoke-testing per role |
| `route-access-matrix` | Checking that roles are denied restricted routes at UI and API |
| `runtime-reality-check` | Confirming the target is up and on the expected build before testing |
| `safe-destructive-testing` | Before any action that could change data |
| `uat-readiness-report` | Composing the final report and sign-off recommendation |
| `verify-identity-and-rbac` | Proving who is logged in and whether a permission change took effect |

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `qa-evidence-collector` | Read, Bash, Glob, Grep, Write + browser capture and login-input tools (no script evaluation, upload, drag or dialog tools) | Capture one role x route cell and return one evidence row |
| `qa-failure-classifier` | Read, Glob, Grep | Classify one FAIL row as ui-bug / api-bug / data-issue / env-issue / spec-ambiguity / unknown |

## Hooks

| Script | Event / matcher | What it does | Can block |
|---|---|---|---|
| `hooks/session_start_target_check.py` | SessionStart `startup` | When `.qa-browser.local.json` exists: warns if it is tracked by git, not git-ignored, unparseable, holds inline credential values, or targets a production host; warns if `qa-evidence/` exists and is not git-ignored. Silent otherwise. | No (advisory) |
| `hooks/pre_navigate_prod_gate.py` | PreToolUse: `navigate`, `navigate_page`, `new_page`, `browser_navigate`, `browser_tabs`, `preview_start`, `browser_batch` (each nested action), and script tools (`browser_evaluate`, `browser_run_code(_unsafe)`, `evaluate_script`, `javascript_tool`) when the script navigates or sends a request (`fetch`, `XMLHttpRequest.open`, `navigator.sendBeacon`, `WebSocket`/`EventSource`/`Request`, Playwright `request.*`) | Host-based production gate, table below. Also denies all gated navigation while a git-tracked config holds inline credentials. | Yes |
| `hooks/pre_navigate_prod_gate.py` (shell) | PreToolUse `Bash` / `PowerShell`, only when a `.qa-browser.local.json` exists | Blocks `curl` / `wget` / httpie (`http`, `https`) / `xh` / `aria2c` / `Invoke-WebRequest` / `Invoke-RestMethod` aimed at a production host (other hosts pass silently). Denies a command that names a role credential variable outside the allow-list. | Yes |
| `hooks/pre_click_skiplist.py` | PreToolUse: `browser_click`, `click` | Asks the user when a click's `target` equals a `doNotClick` selector or its element description contains a `doNotClickText` entry | Asks |

All hooks use the portable launcher (`python3`, `python`, `py -3`), share `hooks/_vendor/hooklib.py`, and fail open on bad input.

**Production host gate.** Decided on the URL's hostname only, never the path (`/products` is not "prod"):

| Host | Result |
|---|---|
| In `productionHosts` or the `production_hosts` plugin option (exact or subdomain), or a hostname label / `-`-part equals a `productionMarkers` entry (default `prod`, `production`) | Blocked (exit 2) |
| localhost, 127.0.0.1, ::1, `*.localhost`, `*.test`, the `targetUrl` host, `allowedHosts` | Allowed |
| Any other host while `targetUrl` or `allowedHosts` is set | You are asked |
| Any other host, no target configured | Allowed |
| A URL whose host cannot be determined (`https://`, `http://[bad`) | You are asked (fails closed) |
| A page script whose request or navigation URL is built at run time (a variable, `${host}`) | You are asked when production hosts are configured; allowed otherwise |

URLs are normalised the way browsers do before the host is read: whitespace trimmed, backslashes treated as `/`, `https:/host`, `https:\host` and `https:host` read as `https://host`, `//host` scheme-relative, `user@` and the port dropped, the host percent-decoded, lower-cased, IDN-encoded to punycode and stripped of trailing dots, and numeric IPv4 forms canonicalised. `view-source:` and `blob:` are unwrapped; a `javascript:` URL is decided by the URLs inside it.

Link clicks and form submits that navigate are not gated; the `safe-destructive-testing` skill covers them. **Override:** none in-session. To test production on purpose, quit and relaunch Claude Code with `QA_BROWSER_ALLOW_PRODUCTION=1`; blocks become allows with an audit note to Claude.

## Configuration

**Plugin option** (`/plugin` -> qa-browser -> configure):

| Key | Type | Default | Meaning |
|---|---|---|---|
| `production_hosts` | string | empty | Comma-separated hosts blocked in every project |
| `credential_env_allowlist` | string | empty | Comma-separated env var names roles may use as `passwordEnv` / `totpEnv` besides `QA_*` names |

**Environment variables:**

| Variable | Meaning |
|---|---|
| `QA_BROWSER_ALLOW_PRODUCTION=1` | Set before launching Claude Code to lift the production block |
| `QA_<ROLE>_PASSWORD`, `QA_<ROLE>_TOTP` (names are yours) | Role passwords and TOTP seeds, referenced from the config by name |

**Per-project file** `.qa-browser.local.json` (git-ignored; found in `$CLAUDE_PROJECT_DIR` or the cwd and its parents):

```json
{
  "targetUrl": "https://staging.example.com",
  "disposable": false,
  "roles": {
    "admin":   { "username": "qa-admin@example.com", "passwordEnv": "QA_ADMIN_PASSWORD", "totpEnv": null },
    "manager": { "username": "qa-manager@example.com", "storageState": ".auth/manager.json" }
  },
  "allowedHosts": ["auth.staging.example.com"],
  "productionHosts": ["www.example.com"],
  "productionMarkers": ["prod", "production"],
  "doNotClick": ["button:has-text('Refund')"],
  "doNotClickText": ["Delete account", "Refund"],
  "consoleAllowlist": []
}
```

**Credential variables are allow-listed.** `passwordEnv` / `totpEnv` must start with `QA_` or be listed in `credential_env_allowlist`. A shared or cloned config that names `GITHUB_TOKEN` (or any other secret) is refused: the Bash gate denies reading it, `totp.py` exits 2, and the SessionStart hook warns. Credentials are typed only into a page on the exact `targetUrl` host, never into an `allowedHosts` host or a redirect target.

The file holds no credential values. Each role either reuses a session the user logged in by hand (`storageState`, preferred) or names env vars set before launch. `"disposable": true` is required for write-verb probes and confirm-and-commit walkthroughs. Files from 0.8 and earlier with inline `password` / `totp` values still load, with a warning.

## Scripts

| Script | Use |
|---|---|
| `scripts/redact_evidence.py [--check] <path>...` | Mask (or, with `--check`, detect and exit 1 on) cookies, auth headers, passwords and token shapes in JSON / text evidence. Never prints the values. Cannot scan screenshots. |
| `scripts/totp.py <ENV_NAME>` | Print the current RFC 6238 code from a base32 seed held in that env var; the seed is never printed |

## Platform support

| Platform | Status |
|---|---|
| Windows | Supported. Hooks need `sh` (Git Bash, installed with Git for Windows) and Python as `python3`, `python` or `py`. |
| macOS | Supported (`python3`). |
| Linux | Supported (`python3`). |
| WSL | Supported when Claude Code and the browser MCP run on the same side. |

## Data & privacy

- **Stored locally:** `.qa-browser.local.json` (target, usernames, env-var names, host lists) and `qa-evidence/<date>/<env>/...` (screenshots, `console.json`, `network.json`, `status.json`, notes, `REPORT.md`) in your project. Both must be git-ignored; the SessionStart hook warns when they are not. The plugin stores nothing elsewhere.
- **Leaves the machine:** only the browser traffic to your QA target that you ask for, and one HEAD request from `/qa-browser:target`. Nothing is sent to TAQAT Techno or any other third party by this plugin.
- **On screen / in the model's context:** page snapshots, console and network output, and screenshots of the target. With env-var login, the password value appears in the one tool call that types it; use dedicated test accounts, or storage-state login so no credential passes through the model. Redact evidence (`redact_evidence.py`) before sharing it; review screenshots by eye.

## Limitations

- The production gate sees navigation, batch, preview and script tools plus shell HTTP clients; a link click or form submit that leaves the target host is guarded by skill guidance, not code.
- Script and shell inspection is pattern-based: heavily obfuscated JavaScript, or HTTP sent from another language (`python -c`, `node -e`), is not resolved. Unresolvable script URLs prompt only when production hosts are configured.
- The click skiplist hook cannot see chrome-devtools-mcp or Claude in Chrome clicks.
- Redaction is shape-based: a secret with no recognisable key or form is not caught, and images are not scanned.
- Write-verb route probes can still change data on a misconfigured server; they run only on targets you mark disposable, after you confirm the request list.
- Acceptance-level UI QA only: not a replacement for unit or API test suites. For building admin panels see the optional `react-kit` plugin; for QA runbooks, `docs-wiki`.

## License

MIT (see `LICENSE`). The browser MCP servers are separate projects with their own licences.
