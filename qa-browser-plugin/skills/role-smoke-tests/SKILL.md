---
name: role-smoke-tests
description: Per-role smoke-test pattern. For each configured role, log in, visit every visible menu item, capture screenshot + console + network, and produce one PASS row per (role × route). Owns the per-role login flow, the menu-walk pattern, the per-step evidence capture, and the cross-role consistency check. Generic and framework-agnostic.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - per-role login flow pattern
  - menu-walk pattern (visit every item the role can see)
  - per-step evidence capture (screenshot + console + network)
  - cross-role consistency check (does role A see only what they should?)
  - role-rotation discipline (logout between roles, fresh storage state)
defers_to:
  - runtime-reality-check (must pass before smoke starts)
  - browser-qa-discipline (status vocabulary for every captured row)
  - route-access-matrix (negative checks — what the role CANNOT reach)
  - safe-destructive-testing (smoke must not mutate data)
  - console-and-network-capture (what to capture and how)
  - project credentials cache (`.qa-browser.local.json`)
user_invocable: false
---

# role-smoke-tests

## Purpose

A role smoke-test is the cheapest way to detect regression that affects access, navigation, or first-render. For each configured role, log in, walk the visible menu, and capture evidence for every page. If any page fails to load, throws a console error, or surfaces a UI that the role should not see, the smoke test catches it before users do.

This skill describes the **positive path** — what the role CAN do. The **negative path** — what the role CANNOT do — is owned by `route-access-matrix`.

## When to use

Activate when:

- A fresh build is ready for QA.
- A change touches auth, role gating, the admin shell, or the menu.
- A deploy promoted a feature from staging to UAT.
- A scheduled regression sweep is due.

Skip when:

- The change is scoped to a single non-routing concern (e.g., a backend index optimization with no UI surface).
- The change is to documentation only.

## Inputs

- **Reality check passed** for the target — `runtime-reality-check` is the gate.
- **Role list** — from the project's adapter cache.
- **Credential map** — from `.qa-browser.local.json` (gitignored). Each role has `{username, password, totp?}`.
- **Login flow** — the exact selector / URL / steps to log in. Differs per app — captured per project as a small `login(role)` recipe.
- **Menu enumeration strategy** — how to enumerate the visible menu items after login. Options:
  - **DOM scrape**: navigate to the app's landing; query the visible sidebar / navbar; collect anchor `href` attributes.
  - **Manifest read**: if the project exposes a menu manifest somewhere fetchable, read it.
  - **Static list**: the user supplies an explicit list per role.

## The smoke-test loop

For each role:

1. **Fresh state** — start a clean browser context (no leftover cookies / storage / cache from a prior role).
2. **Login** — execute the `login(role)` recipe. Capture: post-login URL, the landing page screenshot, any redirects, console + network during the login.
3. **Enumerate** — collect the visible menu items the role can see (DOM scrape or manifest read).
4. **Walk** — for each menu item:
   - Navigate to its URL.
   - Wait for load complete (configurable; default 5s after navigate).
   - Capture screenshot.
   - Capture console messages emitted during the navigation + 5s after.
   - Capture network requests + status codes.
   - Produce one row in the report with status (PASS / BLOCKED / FAIL).
5. **Logout** — execute the logout flow (or destroy the browser context).
6. **Cross-role consistency check** — after all roles are walked, compare the menu enumerations: each role's seen menu should match the project's permission matrix.

## Per-step evidence row

```
[<status>] role=<name> route=<href>
  Login: <PASS — landed on /home in 1.2s, 0 console errors>
  Navigation: <PASS — page loaded in 0.8s, 0 console errors, 0 5xx>
  Render: <screenshot path>
  Console: <0 errors, 2 warnings — listed below>
  Network: <12 requests, 0 5xx, 1 retry on /api/X>
  Run: <YYYY-MM-DD HH:MM tz>
```

A row is **PASS** when navigation completes, page renders the expected role-appropriate content, no console errors, no 5xx network responses.

A row is **FAIL** when any of: navigation does not complete, the page renders an error, console error appears, network 5xx occurs.

A row is **BLOCKED** when login itself failed (downstream checks for this role cannot proceed; mark them all NOT-TESTABLE).

## Cross-role consistency check

After all roles walked, compare:

```
COMPARE
  admin:    sees [users, products, orders, reports, settings, audit-log]
  manager:  sees [users, products, orders, reports]
  support:  sees [users, orders]
  viewer:   sees [orders]
```

Then verify against the project's permission matrix (if available — typically owned by `react-kit/admin-roles-and-permissions/_matrix.ts` or equivalent):

| Inconsistency | Severity | Example |
|---|---|---|
| Role sees a menu item not in their matrix row | HIGH | manager sees `audit-log` |
| Role does NOT see a menu item their matrix row allows | MEDIUM | support's matrix says `read:orders` but `orders` is missing from their menu |
| Role sees the same menu items as another role and that is unexpected | LOW | viewer's menu identical to support's |

## Fresh state per role

NEVER reuse a browser context across roles:

- Cookies from role A leak the session.
- LocalStorage / sessionStorage carries over (admin's recent-searches into viewer's view).
- Service-worker cache may serve cached responses keyed to the wrong role.
- IndexedDB state from a privileged role can pollute a less-privileged one.

The cleanest pattern: one browser context per role; destroy after the role's walk.

If the MCP server does not support context isolation cleanly, an alternative: full storage clear + hard reload between roles. Less clean; document.

## Wait strategy after navigate

- Default: wait 5 seconds after the navigate completes, then capture.
- For SPAs with heavy client-side hydration, raise to 8–10 seconds.
- For first-paint-only smoke, drop to 2 seconds — but be honest in the report about what the wait captures.
- Adaptive wait (wait until network idle, then +2s) is preferred when the MCP server supports it.

## Performance signal as a side benefit

Capture timing during navigation:

```
PASS — page loaded in 1240ms (TTFB 220ms, DOMContentLoaded 980ms, last paint 1240ms)
```

This is not a perf test, but a smoke can surface "this page now takes 8 seconds to load" regressions cheaply.

## Safety gates

- **Never** run the smoke against production by default. Smoke runs against staging / UAT / sandbox.
- **Never** click destructive buttons during smoke. Smoke is a navigation pass; per-action evidence is owned by `modal-and-action-walkthroughs` and lives behind safety gates in `safe-destructive-testing`.
- **Never** persist credentials anywhere except `.qa-browser.local.json` (gitignored). The plugin refuses to run if the credential file is tracked by git.
- **Never** include passwords / OTPs in screenshots — the login flow must dismiss any visible credential field before capture.
- **Never** continue smoke when reality-check is BLOCKED.

## Validation checklist

Before sending a smoke report:

- [ ] Reality-check PASS row is the first row.
- [ ] Every configured role had a fresh browser context.
- [ ] Every role's login succeeded OR is marked BLOCKED with the failure.
- [ ] Every visible menu item per role has its own row.
- [ ] Cross-role consistency check appears at the end.
- [ ] No credentials visible in any screenshot.
- [ ] No PASS row without evidence.

## Output format

```
SMOKE — <env-name> — <date>

[<status>] reality-check                  (must be first)

ROLE: admin
  [<status>] login                         <evidence>
  [<status>] /admin/users                  <evidence>
  [<status>] /admin/products               <evidence>
  ...

ROLE: manager
  [<status>] login                         <evidence>
  ...

CONSISTENCY CHECK
  admin menu:    [users, products, orders, reports, settings, audit-log]
  manager menu:  [users, products, orders, reports]
  ...
  Matrix mismatches: <count> — <listed by severity>

SUMMARY
  Roles tested: <count>
  Routes per role: <average>
  PASS: <n>   BLOCKED: <n>   FAIL: <n>
  Failures by category: <auth | render | console | network>
  Recommended action: <list of top-3 issues>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Reuse browser context across roles | Session leakage; admin's data visible as viewer; false PASS | Fresh context per role |
| Skip the reality check | Whole smoke could be against the wrong env | Reality check first |
| Wait 0ms after navigate | SPA hydration not complete; missing console errors | Configurable wait (default 5s) |
| Mark login PASS because the page navigated to `/login?error=...` | Login actually failed; URL navigated to error page | Verify post-login URL is the expected landing |
| Take a screenshot of the login form (with password visible) | Credential leak in evidence | Dismiss password field before screenshot OR redact post-capture |
| Smoke clicks "Delete" buttons | Destroys test data; not a smoke | Smoke is navigation-only; actions are a different skill |
| Smoke runs against production | Real user traffic affected; mutations leak | Staging / UAT only by default; production needs explicit override |
| Skip the cross-role consistency check | Most-common admin bug class not detected | Always run after the walk |

## Portability rationale

The smoke loop (fresh state → login → enumerate → walk → logout) is framework-agnostic. It depends on:

- A browser MCP (chrome-devtools-mcp or playwright-mcp) for navigation + capture.
- A login recipe per project.
- A menu enumeration strategy per project.

It does NOT depend on:

- A specific UI framework, router, or auth library.
- A specific server framework.
- A specific test runner.

## Cross-references

- `runtime-reality-check` — required first row.
- `browser-qa-discipline` — status vocabulary.
- `route-access-matrix` — negative checks (what role CANNOT reach).
- `modal-and-action-walkthroughs` — per-action evidence (smoke does navigation only).
- `console-and-network-capture` — what to capture; redaction rules.
- `safe-destructive-testing` — no smoke action mutates data.
- `uat-readiness-report` — smoke rows feed the final report.
