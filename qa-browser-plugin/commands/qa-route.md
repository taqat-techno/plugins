---
description: Focused dual-gate check on one URL — for each configured role, navigate to the URL, observe UI denial / allow, observe API status, classify as PASS / Shape-A FAIL (UI hides but API allows) / Shape-B FAIL (UI advertises but API denies). Read-only.
argument-hint: "<url-path> [--include-implicit-methods] [--only role1,role2]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /qa-route

You are running a route-access-matrix check on a single URL. Apply the patterns from `route-access-matrix` and `console-and-network-capture`.

This command is most useful when:

- A bug report mentions one URL behaving wrong for one role.
- A change adds or modifies the role gating on one route.
- You want to verify a fix for a known Shape-A or Shape-B bug.

For full-tree access matrix, run after `/qa-roles` and the access checks each role's menu enumeration discovered.

## Step 0 — Gate

1. `/qa-target check` passes.
2. URL path is provided (e.g., `/admin/audit-log`).
3. Target URL + path does not match a production marker (unless explicit override).
4. At least one browser MCP loaded.

## Step 1 — Reality check (once)

Run `runtime-reality-check`. Abort the whole flow if BLOCKED.

## Step 2 — Identify the API endpoint(s)

Approach (pick the first that works):

1. **Project provides**: a manifest mapping URL paths to API endpoints. Read from `.qa-browser.local.json` under `routeApiMap` if present.
2. **Probe + observe**: navigate to the URL as a privileged role; inspect the network panel for the API calls made; record them.
3. **Convention-based**: derive likely API paths from the URL (`/admin/users` → `/api/users` / `/api/admin/users`). Confirm with the user before using.

Record the API endpoint(s) + their HTTP verbs:

```
ROUTE: /admin/audit-log
  API endpoints observed:
    GET /api/audit-log         (used to populate the list)
    GET /api/audit-log/:id     (used on row click)
```

## Step 3 — Per-role dual-gate check

For each role in scope:

1. Open a fresh browser context.
2. Login as the role.
3. **Direct URL probe** — type the URL (do NOT click a link in the menu; this simulates a user who knows the URL).
4. Wait for load complete.
5. **UI observation**:
   - Did the page render the expected content?
   - Did it render a 403 page?
   - Did it redirect (to login, to unauthorized, to home)?
   - Did it render silently (no content, no error)?
6. **API observation**: capture every API call made during the navigation. For each:
   - HTTP method.
   - Status code (200 / 403 / 401 / 404 / 5xx).
   - Was the response body returned with actual data, or empty?
7. **Classify**:
   - Both UI and API deny → PASS (dual-deny).
   - Both UI and API allow → PASS (if role should have access) / FAIL (if role should NOT — this is a leak).
   - UI denies, API allows → **Shape-A FAIL — HIGH**. The 403 is decoration; data leaks.
   - UI shows, API denies → **Shape-B FAIL — MEDIUM**. User clicks a broken link.

8. (If `--include-implicit-methods`) Probe the API endpoint with implicit verbs (PATCH, PUT, DELETE, POST) using non-mutating payloads:
   - Send malformed body OR target a non-existent id OR use a header marker the server treats as no-op.
   - Record status codes.
   - Classify each.

## Step 4 — Report

```
ROUTE CHECK — <url> — <env> — <date>

[PASS] reality-check

API endpoints under check:
  GET /api/audit-log
  GET /api/audit-log/:id

ROLE: admin
  UI: <rendered the list>
  API: GET /api/audit-log → 200 (data returned)
  Verdict: PASS (admin should have access; got access)

ROLE: manager
  UI: <403 page rendered>
  API: GET /api/audit-log → 200 (data returned)        ← Shape-A FAIL
  Verdict: SHAPE-A FAIL — HIGH — UI denies but API returns data
  Fix: server-side requireRole('admin') on GET /api/audit-log

ROLE: support
  UI: <link visible in menu; clicking navigates>
  API: GET /api/audit-log → 403                         ← Shape-B FAIL
  Verdict: SHAPE-B FAIL — MEDIUM — UI advertises but API denies
  Fix: remove support from /admin/audit-log menu allowedRoles OR grant API access

ROLE: viewer
  UI: <redirected to /unauthorized>
  API: GET /api/audit-log → 403
  Verdict: PASS (dual-deny)

IMPLICIT METHODS (with --include-implicit-methods)

ROLE: manager
  PATCH /api/audit-log → 405 (Method Not Allowed)        ← PASS (verb not exposed)
  DELETE /api/audit-log → 403                            ← PASS

SUMMARY
  Verdicts: PASS 2 / Shape-A FAIL 1 / Shape-B FAIL 1
  Highest severity: HIGH (RAM-1)
  Recommended action: add server-side role gate on GET /api/audit-log
```

## Flags

- `--include-implicit-methods` — probe PATCH / PUT / DELETE / POST in addition to GET. Probes use non-mutating payloads.
- `--only role1,role2` — limit to a subset of roles.
- `--allow-production` — explicit opt-in for production URL.

## Safety

- Read-only navigation only.
- Implicit-method probes use non-mutating payloads (malformed body / non-existent id / no-op header).
- Refuses production URL without explicit opt-in.
- Never propagates session cookies between role contexts.
- Auth tokens redacted in captured network excerpts.
