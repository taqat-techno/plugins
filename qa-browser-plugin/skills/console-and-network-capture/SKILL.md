---
name: console-and-network-capture
description: What to capture from the browser console and network panel during QA, when each signal counts as a failure, and how to redact credentials / PII before evidence lands in a shared report. Owns the capture window convention, the severity mapping (error / warning / info), the request-classification table, and the redaction rules.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - capture window convention (when to start, when to stop)
  - console severity mapping (error / warning / info → status impact)
  - network request classification (success / client-error / server-error / retry / cancelled)
  - redaction rules (passwords / OTPs / JWTs / session cookies / sensitive headers)
  - evidence file naming + storage convention
defers_to:
  - browser-qa-discipline (status vocabulary)
  - safe-destructive-testing (do not capture more than needed; never persist raw secrets)
  - project secret / PII catalogue (which fields are sensitive)
user_invocable: false
---

# console-and-network-capture

## Purpose

The console and network panels expose what the UI cannot — silent JavaScript errors, fire-and-forget API failures, cache-control mistakes, missing assets. Capturing them is cheap; failing to capture them lets bugs ship. This skill names exactly what to capture, when, and how to scrub before evidence lands in a report.

## When to use

Activate during every smoke / walkthrough / action / import-export check. The other skills produce evidence rows; this skill is the spec for what those rows include.

Skip when running offline against a fixture (nothing to capture).

## Inputs

- Browser MCP capabilities (`list_console_messages`, `list_network_requests`, `take_screenshot`).
- A capture-window convention (when to start, when to stop).
- The project's PII / secret catalogue, if available, to drive redaction.

## The capture window

Default convention:

- **Start**: 100ms before the action (clicking a button, navigating).
- **Stop**: 5 seconds after the action's expected completion (page load, modal close, API response).

For SPAs with heavy hydration, raise the stop window to 8–10 seconds. For first-paint-only smoke, drop to 2 seconds — but cite the window in the evidence so the reader can reproduce.

## Console severity mapping

| Console level | Default impact on the row |
|---|---|
| `error` | FAIL the row (any error during the window = failure) |
| `warning` | Note in the row; do not auto-fail; aggregate by message for the report |
| `info` / `log` / `debug` | Capture for context; never fail on them |
| `trace` | Capture only if specifically requested |

Exceptions to "any error = fail":

- **Known-allowed errors**: list per project in the adapter cache (e.g., a third-party analytics SDK throws a benign error on init). Match by message prefix or stable identifier; redact before storing.
- **Resource 404 on optional assets**: e.g., a missing favicon. Capture as a LOW finding, not a FAIL.

The plugin does NOT bake in any allowlist. Allowlists are project-specific and live in `.qa-browser.local.json` under `consoleAllowlist`.

## Console capture row

```
console
  errors: <n>
    [<line N>] <ISO timestamp> <message excerpt — first 200 chars; redacted>
  warnings: <n>
    [<message hash>] <first occurrence; total count in window>
  info: <suppressed — N messages>
  total messages in window: <n>
```

## Network request classification

| Status range | Classification | Default impact |
|---|---|---|
| 2xx | success | Note count; no impact |
| 3xx | redirect | Note count; follow chain; no impact |
| 4xx (except 401, 403, 404) | client error | Capture; investigate (likely a request bug) |
| 401 | unauthorized | Expected on logged-out probes; investigate when logged in |
| 403 | forbidden | Expected on negative-path checks; investigate elsewhere |
| 404 | not found | Resource missing — investigate (asset? endpoint?) |
| 5xx | server error | FAIL the row (always) |
| `(cancelled)` | request cancelled | Capture; investigate cause (often legitimate — navigation away) |
| `(failed)` | network error | FAIL the row |
| Retried | request was retried by the client | Note count; investigate if frequent |

The 5xx rule is strict: any 5xx during the capture window FAILs the row, even if the UI rendered correctly. The 5xx is real; the UI just did not surface it.

## Network capture row

```
network
  total requests: <n>
  by status:
    2xx: <n>
    3xx: <n>
    4xx (excl 401/403/404): <n>
    401: <n>
    403: <n>
    404: <n>
    5xx: <n>          ← any non-zero here is a row failure
    cancelled: <n>
    failed: <n>
  slowest: <method> <url> — <duration>ms
  retries: <n>
  failed requests:
    [<url>] <status> <duration>ms <response excerpt — redacted>
```

## Redaction rules

NEVER include in captured evidence:

| Class | Examples | Redaction |
|---|---|---|
| Credentials | passwords, OTP codes | Replace entire value with `***REDACTED***` |
| Auth tokens | JWT, session cookies, API keys | Replace entire value with `***REDACTED-TOKEN***` |
| Sensitive request headers | `Authorization`, `Cookie`, `X-API-Key`, `X-Auth-Token` | Replace value with `***REDACTED***` |
| Sensitive response headers | `Set-Cookie` | Replace value with `***REDACTED***` |
| Sensitive form payloads | request body containing password / OTP / TOTP | Replace each sensitive field's value with `***REDACTED***` |
| Project-specific PII | as listed in the project's PII catalogue | Replace value with `***PII***` (preserve the field key) |

NEVER include in screenshots:

- Password input contents (capture should be done after the password field is empty or replaced with `***`).
- OTP code entry mid-flow (capture after dismissal).
- Audit-log queries that reveal raw PII (use the masked view).

Implementation rule: redact at capture time, NOT at report time. A redacted value should never be written to disk.

## Evidence file naming + storage

Convention:

```
qa-evidence/<YYYY-MM-DD>/<env-name>/<role>/<route-slug>/<action-slug>/
    screenshot.png
    console.log.json
    network.har
    notes.md
```

- The `qa-evidence/` directory is gitignored by default.
- Screenshots: PNG. JPEG only if size matters.
- Console: JSON array of `{level, timestamp, message-redacted}`.
- Network: HAR file (industry-standard), with all sensitive headers redacted.
- Notes: optional human-readable summary.

The plugin reads back from this directory to build the UAT report (per `uat-readiness-report`).

## Linking evidence into the report

Every row in any QA report references its evidence by relative path:

```
[PASS] role=admin route=/admin/users
  Evidence: qa-evidence/2026-05-28/staging/admin/admin-users/screenshot.png
  Console: 0 errors
  Network: 12 requests, 0 5xx
```

A row without an evidence path is unfinished (per `browser-qa-discipline`).

## What to capture, what to skip

| Always capture | Skip |
|---|---|
| Screenshot on navigation | Repeated screenshots for trivial state |
| Console errors / warnings | Console `debug` / `trace` unless asked |
| API response codes for every network request | Static asset 200s (note total count only) |
| Auth response (login / refresh) | Auth response body (token leak risk) |
| First and last network request timestamps | Sub-millisecond timing on every request |
| Any cross-origin failure | Resource policy headers on every request |

## Safety gates

- **Never** capture an unredacted token / password / OTP — redact at capture time.
- **Never** store a HAR file with `Set-Cookie` headers intact.
- **Never** screenshot during the moment a password field is filled.
- **Never** commit `qa-evidence/` to git — it must be gitignored.
- **Never** ship a report that links to evidence on a developer's local machine without copying the artifacts in.
- **Never** truncate a console message to less than its full first line — context for debugging is lost.

## Validation checklist

Before sending evidence:

- [ ] All captured tokens redacted.
- [ ] All sensitive headers redacted.
- [ ] All sensitive form fields redacted in HAR.
- [ ] No screenshot contains a visible password / OTP.
- [ ] `qa-evidence/` is gitignored.
- [ ] Every evidence file has a path that matches the convention.
- [ ] Window cited in each row (default 5s after action).
- [ ] Allowlist (if applied) cited in the row, with the matched messages.

## Output format

The skill's output is the **shape** of capture rows that other skills include:

```
EVIDENCE
  Screenshot: <path>
  Console:
    errors: <n>           [<excerpt>, ...]
    warnings: <n>         [<excerpt>, ...]
    suppressed (allowlist): <n>
  Network:
    total: <n>
    by status: 2xx=<n> 3xx=<n> 4xx=<n> 5xx=<n>
    failed: [<url>: <status>, ...]
    retries: <n>
    slowest: <method> <url> <duration>ms
  Window: -100ms before to +5s after action
  Run: <YYYY-MM-DD HH:MM tz>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Capture passwords in a HAR file "for debugging" | Credential leak in evidence; ends up in shared reports | Redact at capture |
| Skip console capture because "the page looks fine" | Silent JS errors invisible; bugs ship | Always capture during the window |
| Mark PASS when 5xx happened during the window | UI rendered but server failed; the API call may have succeeded only on retry | 5xx = FAIL |
| Use 0ms capture window | Async errors after the action are missed | Default 5s, project-tuned |
| Filter out 404s as noise | A 404 on `/api/X` is a missing endpoint; on `/favicon.ico` is benign | Classify per request type |
| Ignore retries | Hides flakiness signal | Count retries; investigate if frequent |
| Capture every network request body | HAR files explode; PII risk | Capture body only for failed requests + the action's primary call |
| Allowlist a console error by message regex without escaping | A real bug matching the pattern gets suppressed | Match by full prefix + ID; document each allowlist entry |

## Portability rationale

Console and network capture is a browser MCP capability — works against any web app. The skill does not depend on:

- A specific framework
- A specific observability tool
- A specific test report format

Adapter notes (per MCP server):

- `chrome-devtools-mcp` exposes `list_console_messages`, `list_network_requests`, `take_screenshot`.
- `playwright-mcp` exposes `browser_console_messages`, `browser_network_requests`, `browser_take_screenshot`.

Both produce equivalent evidence in this skill's format.

## Cross-references

- `browser-qa-discipline` — status vocabulary.
- `safe-destructive-testing` — no capture-driven write actions.
- `role-smoke-tests` — uses this skill's row shape.
- `route-access-matrix` — uses this skill's row shape; 4xx / 5xx classification critical for negative-path verdicts.
- `modal-and-action-walkthroughs` — uses this shape per action.
- `import-export-ui-checks` — uses this shape for upload + commit.
- `uat-readiness-report` — aggregates evidence paths into the final report.
