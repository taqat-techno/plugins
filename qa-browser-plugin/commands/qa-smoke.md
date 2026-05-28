---
description: Run a role smoke test — login as one role, walk every visible menu item, capture screenshot + console + network per page, produce a PASS / BLOCKED / FAIL report. Read-only; no mutations. Requires /qa-target to be configured.
argument-hint: "<role-name> [--wait-seconds N] [--include-perf]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /qa-smoke

You are running a role smoke test for one role. Apply the patterns from the `qa-browser` skill set:

- `runtime-reality-check` — must pass before the first navigation.
- `role-smoke-tests` — the loop (fresh context → login → enumerate menu → walk → logout).
- `console-and-network-capture` — what to capture, redaction rules.
- `safe-destructive-testing` — no clicks on destructive selectors; no mutations.
- `browser-qa-discipline` — PASS / BLOCKED / FAIL vocabulary.

## Step 0 — Gate

1. Verify `/qa-target check` passes (file exists, gitignored, not tracked, target URL set).
2. Verify the requested role is configured. If not, fail with: "Role `<name>` not in credentials. Configure via /qa-target set."
3. Verify the target URL does NOT match a production marker (unless `--allow-production` AND explicit override).
4. Verify at least one browser MCP is loaded.

If any gate fails, surface clearly and stop.

## Step 1 — Reality check

Per the `runtime-reality-check` skill:

1. HTTP GET the target URL. Expect 2xx (or documented status).
2. Probe `/health`, `/api/health`, `/__version__` — capture build identity if available.
3. Navigate to the landing page; screenshot; capture env label visible on the page.
4. Verify env label matches the URL (e.g., URL contains `staging`, page shows STAGING badge).

If mismatch: STOP. Surface labels (DEAD INFRASTRUCTURE / WRONG ENVIRONMENT / STALE BUILD / DEFERRED PATH / PENDING DECISION). Report row reality-check status BLOCKED and abort.

Write the reality-check row to the report:

```
[PASS] reality-check
  Target: <url>
  Build: <commit/version>
  Env label: <name> matches URL
  Landing: 0 console errors, 0 5xx
  Probed at: <ISO timestamp>
```

## Step 2 — Fresh browser context + login

1. Open a fresh browser context (no leftover cookies / storage from prior runs).
2. Navigate to the login URL.
3. Apply the project's login recipe for this role:
   - Fill username from credentials.
   - Fill password from credentials.
   - Submit.
   - If TOTP is configured, wait for the prompt and enter the current code.
4. Wait for post-login landing (default 5s).
5. Verify post-login URL is the expected landing (NOT the login URL with `?error=`).

Login row:

```
[<status>] role=<name> login
  Landed: <url>
  Duration: <ms>
  Console: <0 errors, X warnings>
  Network: <count requests, 0 5xx>
  Run: <ISO timestamp>
```

If login BLOCKED: every subsequent row for this role is NOT-TESTABLE. Skip to Step 5 (report).

## Step 3 — Enumerate visible menu

After login:

1. Capture the rendered sidebar / top-nav / menu DOM.
2. Extract `href` values from visible menu items.
3. Filter to in-scope routes (admin tree; project-defined).

If the project's menu definition is reachable (e.g., a config file), prefer reading it over DOM scrape — cross-check both.

Record the enumeration:

```
ROLE: <name>
  Visible menu items: <count>
  Routes: [<href>, <href>, ...]
```

## Step 4 — Walk

For each route:

1. Navigate. Wait the configured window (default 5s; configurable via `--wait-seconds`).
2. Capture screenshot.
3. Capture console messages during navigate + window. Apply allowlist; classify errors / warnings.
4. Capture network requests during navigate + window. Classify by status.
5. If `--include-perf`: capture TTFB, DOMContentLoaded, last paint.
6. Apply the do-not-click skiplist as a defensive check — no actions to click, but verify no auto-click occurred during navigation.
7. Save evidence to `qa-evidence/<YYYY-MM-DD>/<env>/<role>/<route-slug>/`:
   - `screenshot.png`
   - `console.log.json` (redacted)
   - `network.har` (redacted)
   - `notes.md` (optional)
8. Write the row to the report.

Row per route:

```
[<status>] role=<name> route=<href>
  Navigation: <PASS — loaded in Xms>
  Render: qa-evidence/.../screenshot.png
  Console: <0 errors, X warnings>
  Network: <Y requests, 0 5xx, Z retries>
  Performance: TTFB Xms, DCL Yms, last paint Zms     ← only with --include-perf
  Run: <ISO timestamp>
```

## Step 5 — Logout + cleanup

1. Execute logout (or destroy the browser context).
2. Verify post-logout state (e.g., redirect to login).

## Step 6 — Report

Produce the smoke report for this role:

```
SMOKE — role=<name> — <env> — <date>

[PASS] reality-check
[<status>] login
[<status>] route 1
[<status>] route 2
...

SUMMARY
  Routes walked: <N>
  PASS: <n>   BLOCKED: <n>   FAIL: <n>
  Failures by category:
    auth: <n>
    render: <n>
    console errors: <n>
    network 5xx: <n>
  Top-3 failing routes: <list>
  Evidence: qa-evidence/<date>/<env>/<role>/
```

If the user has run smokes for multiple roles, suggest `/qa-roles` next to consolidate (or `/qa-report` to compile the final UAT report).

## Flags

- `--wait-seconds N` — override the post-navigate wait window. Default 5.
- `--include-perf` — capture TTFB / DCL / last-paint timing per route.
- `--allow-production` — explicit opt-in to run against a production URL. Requires user confirmation phrase: "yes, run qa-smoke against production".

## Safety

- Read-only. No clicks on action buttons. No form submits.
- Refuses production URLs without `--allow-production` + confirmation.
- Refuses to operate if `.qa-browser.local.json` is tracked by git.
- Credentials never appear in output / evidence / report.
