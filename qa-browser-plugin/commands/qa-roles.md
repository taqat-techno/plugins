---
description: Run /qa-smoke across every configured role; produce one consolidated smoke report including the cross-role consistency check. Use after /qa-target is set with multiple roles.
argument-hint: "[--wait-seconds N] [--include-perf] [--only role1,role2]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /qa-roles

You are running role smoke tests for every configured role and producing one consolidated report. This is the batch form of `/qa-smoke`.

## Step 0 — Gate

1. Run `/qa-target check`. Abort on any failure.
2. Verify at least one browser MCP is loaded.
3. Verify the role set:
   - Default: every role in the credentials map.
   - With `--only`: comma-separated subset. Reject roles not in the credentials map.
4. Verify the target URL does not match a production marker (unless explicit override).

## Step 1 — Reality check (once)

Run the reality check from `runtime-reality-check` once at the top — same as `/qa-smoke`. If it BLOCKS, the whole pass aborts; mark every role's smoke as NOT-TESTABLE.

Write the row to the consolidated report.

## Step 2 — Per-role smoke

For each role in scope:

1. Open a **fresh** browser context (mandatory between roles — see `role-smoke-tests`).
2. Run the smoke loop:
   - Login.
   - Enumerate visible menu.
   - Walk every visible route, capturing screenshot + console + network.
   - Logout.
3. Append the rows to the consolidated report.

The per-role flow is identical to `/qa-smoke`. The only differences are:
- One consolidated report file.
- Fresh-context discipline enforced across roles.
- Cross-role consistency check (Step 3) runs at the end.

## Step 3 — Cross-role consistency check

After all roles walked, compare:

```
admin    sees [<routes>]
manager  sees [<routes>]
support  sees [<routes>]
viewer   sees [<routes>]
```

If the project provides a permission matrix (e.g., from `react-kit/admin-roles-and-permissions/_matrix.ts`), verify each role's seen menu against their matrix-allowed routes:

| Inconsistency | Severity |
|---|---|
| Role sees a menu item not in their matrix row | HIGH |
| Role does NOT see a menu item their matrix allows | MEDIUM |
| Two roles see identical menus unexpectedly | LOW |

If no matrix is available, perform structural checks only:

- Higher-privilege roles should see a superset of lower-privilege roles' menus.
- Every role should see something (an empty menu is a finding).

Write the consistency rows:

```
CROSS-ROLE CONSISTENCY

  Matrix source: <path or "not provided">
  admin    sees [users, products, orders, reports, settings, audit-log]   ← matrix: same
  manager  sees [users, products, orders, reports]                        ← matrix: same
  support  sees [users, orders, audit-log]                                ← matrix says no audit-log → HIGH
  viewer   sees [orders]                                                  ← matrix: same

  Mismatches: 1 HIGH
```

## Step 4 — Consolidated report

Layout:

```
SMOKE — ALL ROLES — <env> — <date>

[PASS] reality-check

ROLE: admin
  [<status>] login
  [<status>] /admin/users
  ...

ROLE: manager
  ...

CROSS-ROLE CONSISTENCY
  ...

SUMMARY
  Roles tested: <count>     Skipped: <count> — <list>
  Total routes walked: <N>
  PASS: <n>   BLOCKED: <n>   FAIL: <n>
  Top issues across roles:
    1. <issue> (affects <roles>)
    2. ...
  Evidence: qa-evidence/<date>/<env>/

NEXT
  /qa-report → compile UAT report
  /qa-route <url> → focused dual-gate check on a specific URL
```

## Flags

- `--only role1,role2` — only run smoke for these roles. Useful when iterating on one role's issue.
- `--wait-seconds N` — override post-navigate wait window. Default 5.
- `--include-perf` — capture TTFB / DCL / last paint per route.
- `--allow-production` — explicit opt-in for production URL.

## Safety

- Same safety gates as `/qa-smoke`.
- Fresh browser context per role is mandatory. The command refuses to share state across roles even if asked.
- Refuses production URL without explicit opt-in.
