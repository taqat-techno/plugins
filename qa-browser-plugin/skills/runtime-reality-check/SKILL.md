---
name: runtime-reality-check
description: Verify the QA target is actually reachable, healthy, and on the expected build BEFORE running any checks. Owns the "is it actually running" gate, the build-identity check (commit / version / deploy timestamp), the env-claim-vs-actual check, the restart-stale-dev-server-before-QC step, the "dead infrastructure" labels, and the browser-side wait-strategy / client-cache traps — Playwright networkidle never settling on a Turbopack dev server with React-Query refetching, a forced-error / 500 state that needs a fresh context because a client query cache serves stale rows, a dirty beforeunload guard silently blocking browser_navigate, and a stale CSS/JS chunk surviving a dev-server restart in the tab. Activates at the start of any QA pass, before re-running a failed check, and whenever a run's evidence smells stale.
version: 0.4.0
last_reviewed: 2026-07-23
owns:
  - target-reachability gate (HEAD probe + landing render)
  - build identity check (commit / version / deploy timestamp)
  - dead-infrastructure / deferred-path / wrong-environment labels
  - env-claim-vs-actual comparison
  - restart-stale-dev-server-before-QC (next start chunk pin; runserver --noreload)
  - browser-side wait-strategy / client-cache traps (networkidle never settles; fresh context for forced-error states; beforeunload blocks navigate; stale chunk survives restart)
defers_to:
  - browser-qa-discipline (evidence vocabulary for the reality-check outputs)
  - safe-destructive-testing (any probe must not mutate data)
  - project SOPs / wiki (the canonical narrative about what runs where)
user_invocable: false
---

# runtime-reality-check

## Purpose

The most expensive QA pass is one that ran against the wrong environment, the wrong build, or a deployment that already died. This skill makes the verification step mandatory and read-only: confirm the URL responds, the build identity matches expectations, the environment label on the page matches the URL you typed.

If reality does not match the canonical narrative ("production is on host X with commit Y"), the QA pass MUST stop and surface the discrepancy before continuing.

## When to use

Activate at the start of any QA pass — before the first check.

Also re-run when:

- A check fails unexpectedly and you suspect environment drift.
- A check passes when you expected a fail (and vice versa).
- A test run is more than ~30 minutes old; redeploys may have happened.
- A trigger phrase appears: "is staging up?", "did the deploy go through?", "I'm on the right env, right?"

Skip when:

- Running offline against a local file fixture (no target to verify).

## Inputs

- The target base URL.
- The expected build identity — commit SHA, version string, deploy timestamp. Sourced from the project's release notes, CI artifact, or wiki.
- The expected environment label — e.g., staging, UAT, sandbox. The page itself should expose this somewhere (badge in header, footer text, `meta` tag).

## Read-only investigation steps

Before any other QA activity:

1. **Reachability** — HTTP GET against the base URL. Expect 200 (or the documented expected status for unauthenticated landing).
2. **Identity probe** — GET against a build-identity endpoint if the app exposes one:
   - `/api/health`, `/health`, `/_health`, `/__version__`, `/api/version` — common patterns.
   - Many apps expose commit / version in HTML `meta` tags or a footer badge.
3. **Environment-label probe** — render the landing page (with `browser_navigate` + `browser_take_screenshot`) and verify the env label matches the URL you typed:
   - `https://staging.example.com` → page shows "STAGING" badge.
   - `https://uat.example.com` → page shows "UAT" badge.
   - Mismatch → STOP; surface the discrepancy.
4. **Console + network on landing** — a clean landing should produce no 5xx network responses and no console errors. Capture a snapshot.
5. **Time skew** — confirm your wall-clock and the server's are close enough (within ~5 minutes). Some auth flows fail on clock skew.

## Decision framework

### Reality matches → proceed

The target is reachable, the build identity matches the canonical narrative, the env label matches the URL, the landing is clean. Proceed with the QA pass; cite this reality-check as the first PASS row.

### Reality contradicts → STOP

| Symptom | Likely cause | Action |
|---|---|---|
| URL returns 502 / 503 / 504 | Service down, deploy in flight, supervisor restart | Wait and re-probe; if persistent, BLOCKED with operator handoff |
| URL returns 200 but the page shows the wrong env label | DNS / reverse-proxy points to the wrong upstream | STOP; surface |
| Build identity differs from canonical narrative | Stale deploy / hotfix / out-of-band push / wrong branch | STOP; surface; do not test "production" against an old build silently |
| Landing has console errors that look like missing assets | CDN drift; build asset mismatch | STOP; surface — this often masks the rest of the run |
| Auth landing redirects to a different domain than expected | OAuth misconfig / wrong env | STOP; surface |

### Reality is unclear → probe more

If neither match nor mismatch is conclusive (e.g., no health endpoint exists, no env label visible):

- Capture the screenshot, the URL, the timestamp.
- Mark the reality-check as BLOCKED with a named precondition: "no build identity surface — need /health or visible env label."
- Do NOT continue the QA pass as if reality is confirmed.

## Stale local server — restart before QC

When the target is a dev server you started yourself and you just changed the code under test, the running process is the stale build — restart it **before** the QA pass, then re-probe build identity. A "looks like a code bug" or "looks like an access bug" is often just a process that never picked up the new code. Two concrete signatures:

| Signature | What you see | Why | Fix |
|---|---|---|---|
| `next start` serving a prebuilt `.next/`, then rebuilt underneath it | Every route 500s with `ChunkLoadError` (the served HTML references chunk hashes that no longer exist on disk) | `next start` pins the build at boot; a rebuild swaps the chunks but not the running process | Stop, rebuild, restart `next start` (or use `next dev` which recompiles per request) |
| Django `runserver --noreload` | A **new** route 404s while **old** routes still 200 — partial, not total, failure | `--noreload` disables the autoreloader, so the URLconf / new view is never re-imported | Restart `runserver` (drop `--noreload` for QC so it picks up edits) |

The tell is the split: old paths work, new paths don't (Django), or *everything* breaks with a chunk/asset error after a rebuild (Next). Restart first, then decide whether it's a real bug.

### The restart is only half the fix — the browser tab caches too

Restarting the dev server clears the *server's* stale build; it does not clear the *tab's*. A CSS or JS chunk the browser already fetched can survive the restart in memory / disk cache, so the tab keeps rendering the old asset while the server serves the new one — a QC-side false "still broken." When a fix is confirmed on the server (new build identity, correct file on disk) but the tab still shows the old behavior, escalate the reload:

- **Hard-reload** the tab (bypass cache) — the cheapest fix.
- **Fresh browser context** — no carried-over cache / storage / service-worker.
- **Different port** — the surest defeat of a stale cache keyed to `host:port`; a restart on the *same* port can still be served from cache, a new port cannot.

Confirm the served chunk actually changed (hash in the network panel, or the new marker in the asset) before calling either a pass or a fail.

## Wait-strategy and client-cache traps (browser-side)

A page can be fully rendered and correct while the QC tooling reports failure — or stale while it reports success. Three traps produce evidence that lies about the runtime; each has a deterministic fix.

| Trap | What you see | Why | Fix |
|---|---|---|---|
| `networkidle` never settles | `browser_navigate` / wait-for-load times out (~30s) even though the content is present on screen | A dev server that recompiles per request (e.g. Turbopack) plus a client that refetches on an interval (e.g. React-Query) means the network is *never* idle — there is always an in-flight request, so `networkidle` can never fire | Wait on `domcontentloaded` or an **explicit element** (`wait_for` the exact selector / text you are asserting), not on network-idle; or QC a **production build**, where the recompile / refetch churn is gone |
| Forced-error / 500 state shows stale rows | You force a backend error (stop the API, inject a 500) but the UI keeps showing the previous good data, so the error state "won't reproduce" | A client query cache (e.g. React-Query, SWR — often a ~30s stale window) serves the last successful response from memory; the current tab never refetches inside the window | Assert the error state from a **fresh browser context** (cold cache), or hard-invalidate the cache — do not trust the warm tab |
| Dirty `beforeunload` blocks navigation | `browser_navigate` hangs and the goto times out with no new page | The current page has a dirty-state `beforeunload` guard (unsaved-changes prompt); the browser raises a native confirm dialog that silently blocks the programmatic navigation | Clear the dirty state (or pre-register a dialog handler / accept-the-dialog step) **before** navigating away; `browser_navigate` alone will not leave a dirty page |

The through-line: on a dev server the "quiet network / warm cache / clean navigation" assumptions the tooling defaults to are all violable. When a wait times out, an error state won't reproduce, or a navigate hangs, suspect the wait strategy / cache / unload guard *before* concluding "bug."

The `networkidle` caveat also qualifies the wait strategy in `role-smoke-tests` — prefer an explicit element wait over network-idle on a recompile-per-request dev server.

## Labels for the report

When reality-check produces a finding, use one of:

| Label | Meaning |
|---|---|
| **DEAD INFRASTRUCTURE** | The supervisor / process / container is down or missing; whatever is responding is not the expected service. |
| **WRONG ENVIRONMENT** | The URL maps to a different env than the page label or the operator expects. |
| **STALE BUILD** | The build identity does not match the canonical narrative; an older or newer build is live. |
| **DEFERRED PATH** | The intended deploy path (CI workflow, script) is parked / disabled / never ran; the live build came from a different path. |
| **PENDING DECISION** | The discrepancy is real but a decision is in flight (e.g., "we will hotfix later today"); QA pauses until the decision lands. |

Each label needs evidence: the expected vs actual, with file:line citations to the canonical narrative if applicable.

## Safety gates

- **Never** mutate data during a reality check. Only GET / navigate / screenshot.
- **Never** log in with destructive-action credentials during a reality check.
- **Never** assume "it must be up because it was up yesterday."
- **Never** ignore an env-label mismatch; it is the most common cause of wrong-env test runs.
- **Never** continue QA when DEAD INFRASTRUCTURE is found — escalate first.
- **Never** "fix" the discrepancy from within QA (e.g., trigger a deploy). Hand off to the operator.

## Validation checklist

Before the first real check:

- [ ] Target URL responds with the expected status.
- [ ] Build identity probed and recorded (commit / version / deploy timestamp).
- [ ] Env label on the page matches the URL.
- [ ] Landing page has no 5xx network responses; console clean.
- [ ] Reality-check row written to the report as the first entry with status PASS or BLOCKED.

## Output format

The reality-check produces one row in the report:

```
[<status>] runtime-reality-check
  Target: <URL>
  Expected env: <name>          Actual env on page: <name>     → match | MISMATCH
  Expected build: <commit/version>   Actual build: <commit/version>   → match | STALE | UNKNOWN
  Landing: <0 console errors, 0 5xx, screenshot attached>
  Probed at: <YYYY-MM-DD HH:MM tz>
  Labels (if any): <DEAD INFRASTRUCTURE / WRONG ENV / STALE BUILD / DEFERRED PATH / PENDING DECISION>
  Evidence: <screenshot path; /health response body; commit comparison>
```

If status is BLOCKED, the rest of the QA pass writes itself as NOT-TESTABLE pending resolution.

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Skip the reality check — "it's always up" | The day it is not, the whole report is invalid | Always probe |
| Trust the URL alone — page env label not checked | DNS / proxy misconfigs route silently | Verify env label on the page |
| Continue QA on a STALE BUILD because "the changes are probably there" | Bugs may be fixed in source but not in the running build | STOP; redeploy or test the actual build |
| Mark reality-check PASS without recording build identity | Cannot reproduce later | Capture build identity |
| Treat 200 OK as healthy — the page may be a maintenance / "service unavailable" 200 | False positive | Render the page; check content |
| Test "production" by typing `staging.example.com` because "they share a build" | They do not always; one fix lands in staging only | Test the actual URL of the env claimed |
| QC code you just changed against the dev server that was already running | The process holds the old build (`next start` pins chunks; `runserver --noreload` skips re-import) — you debug a phantom bug | Restart the server first, then re-probe build identity |
| Wait on `networkidle` against a recompile-per-request dev server | It never goes idle (per-request compile + interval refetch) → a ~30s timeout on a page that actually rendered | Wait on `domcontentloaded` or an explicit element; or QC a prod build |
| Assert a forced-error / 500 state in the same warm tab | A client query cache serves stale good rows; the error "won't reproduce" | Assert from a fresh browser context (cold cache) |
| `browser_navigate` away from a page with unsaved changes and assume it left | A dirty `beforeunload` guard fires a native dialog that silently blocks the goto (timeout) | Clear dirty / pre-handle the dialog before navigating |
| Assume a dev-server restart cleared the browser too | A stale CSS / JS chunk can survive in the tab cache → a QC-side false "still broken" | Hard-reload / fresh context / different port; confirm the chunk hash changed |

## Portability rationale

The reality-check applies to any deployed web app:

- Hosted on any cloud (AWS, Azure, GCP, on-prem)
- Behind any reverse proxy (nginx, Caddy, ALB, CloudFront)
- Supervised by any runner (systemd, PM2, docker, k8s)

The skill does not depend on:

- A specific health endpoint shape
- A specific build identity convention
- A specific environment naming

## Cross-references

- `browser-qa-discipline` — the reality-check row uses PASS / BLOCKED vocabulary.
- `safe-destructive-testing` — the reality-check is itself a read-only probe.
- `role-smoke-tests`, `route-access-matrix`, `modal-and-action-walkthroughs`, `import-export-ui-checks` — all gated by reality-check.
- `uat-readiness-report` — surface reality-check labels in the final report.
