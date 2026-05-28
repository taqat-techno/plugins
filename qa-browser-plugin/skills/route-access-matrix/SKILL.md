---
name: route-access-matrix
description: Negative-path access verification. For every (role × restricted route) pair, navigate directly to the route while authenticated as that role, verify the UI denies AND the API denies. Owns the dual-gate check (UI 403 page plus API 403 response), the "UI hides but API allows" detection pattern (the most common RBAC bug), and the "API denies but UI shows the link" detection pattern.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - dual-gate check (UI + API both deny for unauthorized role)
  - Shape-A detection — UI hides but API allows (the most common RBAC bug)
  - Shape-B detection — API denies but UI advertises (broken-link UX bug)
  - the implicit-method check (DELETE / PATCH endpoints often missing role check even when GET is gated)
  - direct-URL probe pattern (bypass menu; type URL)
defers_to:
  - runtime-reality-check (must pass first)
  - browser-qa-discipline (status vocabulary)
  - role-smoke-tests (positive path — what the role CAN reach)
  - safe-destructive-testing (probes must not mutate)
  - console-and-network-capture (capture the API response code)
user_invocable: false
---

# route-access-matrix

## Purpose

The most common RBAC bug is not "the user got an error page" — it is "the user clicked a hidden URL and the API returned 200 with someone else's data." This skill makes the negative path explicit: for each (role × restricted route), confirm both the UI denies AND the API denies. If only one denies, that is the bug.

## When to use

Activate when:

- After `role-smoke-tests` completes the positive walk.
- Before sign-off of any change that adds a route, a role, or a permission predicate.
- When auditing a recent RBAC-related bug to confirm fix and no regression.
- When promoting code from staging to UAT or UAT to production.

## Inputs

- **Reality check passed**.
- **Role list** + credentials (from adapter cache, gitignored).
- **Route × role denial expectation matrix** — for each restricted route, the list of roles that should be denied. Generated from the project's permission matrix (e.g., `react-admin-kit/_matrix.ts`) or supplied by the user.
- **API endpoint map** — for each restricted route, the corresponding API endpoint(s). Format: `{ uiRoute, apiEndpoint, method }`. Typically inferable from the route's network panel; can also be supplied.

## The matrix shape

```
ROUTE                          | METHOD | DENIED ROLES               | LOGGED-IN BEHAVIOR
/admin/users/delete            | DELETE | manager, support, viewer   | 403 from API; UI hidden in menu
/admin/audit-log               | GET    | support, viewer            | UI 403 page; API 403 response
/admin/settings                | GET    | manager, support, viewer   | UI redirect to /unauthorized; API 403
/admin/users/[id]/impersonate  | POST   | manager, support, viewer   | UI hidden; API 403
```

Each row is a check.

## The dual-gate test

For each (role, restricted route):

1. **Login as the role.**
2. **Bypass the menu** — type the URL directly (or use `browser_navigate` with the full path). This simulates a user who knows the URL (because they bookmarked it, or because they were promoted/demoted, or because they got a stale tab).
3. **Observe UI denial**:
   - The UI should either show a 403 page, redirect to a public page, or render an "Access denied" component.
   - "Render the actual content" → FAIL.
   - "Render an empty page with no error" → FAIL (silent failure).
4. **Observe API denial**:
   - During the navigation, the network panel will show the API call(s) that the page tries to make.
   - The API should return 403 (or 401 if the session is interpreted as logged-out; but in a logged-in role-denied scenario, expect 403).
   - "API returns 200 with data" → FAIL — this is the bug.
5. **Probe the implicit methods** — for the same route, probe `PATCH`, `PUT`, `DELETE`, `POST` against the corresponding API endpoint(s). UI gating often covers GET only; mutating verbs are forgotten:
   ```
   PASS — GET /api/users/123 returned 200 (UI render allowed)
   PASS — DELETE /api/users/123 returned 403 (UI gate matches API gate)
   FAIL — PATCH /api/users/123 returned 200 — UI hides edit form but API accepts the patch
   ```

## The two bug shapes

### Shape A — UI hides but API allows (HIGH severity, the classic bug)

```
Symptom:
  role=manager visits /admin/audit-log
  UI: shows 403 page
  API call to GET /api/audit-log: returns 200 with full data

Why this is a bug:
  The 403 page is decoration. Anyone with the API URL gets the data.
  The bypass is trivial (curl, fetch from devtools, any HTTP client).

Fix:
  Server-side authorization check in the API handler.
  The UI 403 is fine to keep as ergonomics; the bug is the missing server gate.
```

### Shape B — API denies but UI advertises (MEDIUM severity)

```
Symptom:
  role=manager logged in
  Sidebar menu shows "Audit Log" link
  Click → page loads, shows skeleton, then 403 error from API

Why this is a bug:
  The user sees the link, clicks it, and gets an error.
  Either the link should not show, or the access should be granted.

Fix:
  Update the menu's allowedRoles to match the actual API gate.
  Either way, the menu and the API must agree.
```

## Probe technique

Direct URL probe via the browser MCP:

```
1. browser_navigate to <full-restricted-route-url>
2. Wait for load complete + 2s
3. browser_take_screenshot for evidence
4. browser_list_network_requests, filter to API endpoints during the navigation window
5. For each API request, record: method, URL, status code, response body excerpt (redacted)
6. Categorize: dual-deny PASS / dual-allow FAIL / split-shape-A FAIL / split-shape-B FAIL
```

Implicit-method probe — once the API endpoint is known, use `browser_evaluate` or a network-aware probe to send a non-mutating OPTIONS request (and recorded GET if not yet recorded) to detect what verbs the server even accepts. Then probe the dangerous verbs with intentionally invalid payloads (so even if the gate is missing, no real mutation happens):

```
fetch('/api/users/999999999', {
  method: 'DELETE',
  headers: { 'X-QA-Probe': 'route-access-matrix' },
})
  → status 403?  → PASS (gate works)
  → status 404?  → AMBIGUOUS (record may not exist; try a known id but observe-only)
  → status 200?  → FAIL — gate missing
```

NOTE: probing DELETE with a non-existent id avoids data loss but can produce ambiguous results (404 ≠ 403). Where possible, use a deliberately invalid payload that fails earlier in the request lifecycle (e.g., malformed body) so the gate, not the data layer, decides.

## Safety gates

- **Never** mutate data during a route-access probe. Use non-existent ids, malformed payloads, or a custom header the server treats as no-op.
- **Never** probe production by default — staging / UAT only. If production is required, the production-URL gate (a `qa-browser` hook) requires explicit per-session approval.
- **Never** rely on UI-only evidence for the dual-gate test — always capture the API response code.
- **Never** mark a (role × route) as PASS without checking the implicit methods.
- **Never** include the role's auth token in a captured network request that lands in a shared report.

## Validation checklist

Before sending a route-access-matrix report:

- [ ] Reality-check PASS row.
- [ ] Every (role × restricted route) check has UI status + API status.
- [ ] Implicit methods probed for every API endpoint.
- [ ] Shape-A failures listed at top (HIGH severity).
- [ ] Shape-B failures listed second (MEDIUM severity).
- [ ] No mutation occurred during probes.
- [ ] Auth tokens / cookies redacted in captured network excerpts.

## Output format

```
ROUTE ACCESS MATRIX — <env-name> — <date>

[PASS] reality-check

DENIAL CHECKS

Role: manager
  [<status>] /admin/audit-log (GET)
    UI: <403 page rendered>
    API: GET /api/audit-log → <403 / 200> (<reason>)
    Implicit methods probed: PATCH /api/audit-log → <status>; DELETE /api/audit-log → <status>
    Verdict: <dual-deny PASS | shape-A FAIL | shape-B FAIL>

  [<status>] /admin/settings (GET)
    ...

Role: support
  ...

SHAPE-A FAILURES (HIGH — UI hides but API allows)
  | Route | Method | API status | Fix |
  |-------|--------|-----------|-----|
  | /api/audit-log | GET | 200 | Add `requireRole('admin')` in handler |

SHAPE-B FAILURES (MEDIUM — UI advertises but API denies)
  | Route | API status | Fix |
  |-------|------------|-----|
  | /admin/reports | 403 | Remove from manager's menu OR grant API access |

SUMMARY
  Checks: <N>
  Shape-A failures: <n>     HIGH
  Shape-B failures: <n>     MEDIUM
  Dual-deny PASS: <n>
  Recommended action: <top fix>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Trust the UI 403 page as evidence of API denial | The API may be wide open behind the UI shield | Always check the API response |
| Probe only GET endpoints | DELETE / PATCH / POST often missing role checks | Probe implicit methods too |
| Probe destructive endpoints with real ids | Real data destroyed | Use non-existent ids or malformed payloads |
| Probe via the menu (clicking the link) | Hidden links don't get clicked; bug not surfaced | Direct URL navigation |
| Skip the negative path because "the positive path passed" | Positive ≠ negative; both can be wrong | Run both |
| Run on production to "make sure it really works" | Live data, live users, live observability noise | Staging by default |
| Report only failures (no PASS rows) | Cannot tell what was checked | Per-check status |

## Portability rationale

The dual-gate check applies to any web app with role-based access control. The skill does not depend on:

- A specific framework
- A specific auth library
- A specific HTTP client

It only requires the MCP browser to navigate and inspect network responses.

## Cross-references

- `runtime-reality-check` — required first row.
- `browser-qa-discipline` — status vocabulary.
- `role-smoke-tests` — positive path complement.
- `safe-destructive-testing` — probes must not mutate.
- `console-and-network-capture` — capture rules for the API responses.
- `uat-readiness-report` — failure rows feed the final report at HIGH severity.
