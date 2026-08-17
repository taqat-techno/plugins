---
name: runtime-reality-check
description: Verify the QA target is actually reachable, healthy, and on the expected build BEFORE running any checks. Owns the "is it actually running" gate, the build-identity check (commit / version / deploy timestamp), the env-claim-vs-actual check, the restart-stale-dev-server-before-QC step, the "dead infrastructure" labels, and the browser-side wait-strategy / client-cache traps — Playwright networkidle never settling on a recompile-per-request dev server or on any page holding an SSE / WebSocket stream open, a forced-error / 500 state that needs a fresh context because a client query cache serves stale rows, a dirty beforeunload guard silently blocking browser_navigate, and a stale CSS/JS chunk surviving a dev-server restart in the tab. Activates at the start of any QA pass, before re-running a failed check, and whenever a run's evidence smells stale.
version: 0.4.0
last_reviewed: 2026-07-23
owns:
  - target-reachability gate (HEAD probe + landing render)
  - build identity check (commit / version / deploy timestamp)
  - dead-infrastructure / deferred-path / wrong-environment labels
  - env-claim-vs-actual comparison
  - QA-host renderer capability (headless font coverage for non-Latin / RTL screenshots)
  - local-schema-drift gate (unapplied migrations 500 a page nobody touched)
  - restart-stale-dev-server-before-QC (next start chunk pin; runserver --noreload; read the process's real start args)
  - browser-side wait-strategy / client-cache traps (networkidle never settles; fresh context for forced-error states; beforeunload blocks navigate; stale chunk survives restart)
defers_to:
  - browser-qa-discipline (evidence vocabulary for the reality-check outputs)
  - safe-destructive-testing (any probe must not mutate data)
  - project SOPs / wiki (the canonical narrative about what runs where)
user-invocable: false
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
6. **Renderer capability** — only when the run will judge *rendering*. The screenshot is produced by the browser host, not by the target: a headless browser can only draw glyphs from the fonts installed on the machine it runs on, and a minimal Linux image or a stock WSL distro usually ships Latin coverage only. Arabic, Hebrew, CJK and every other non-Latin script then render as tofu (missing-glyph boxes) no matter how correct the page is, and the RTL layout underneath them is unreadable. Before calling a non-Latin or RTL rendering defect from such a screenshot, confirm the script's font families are present in the directory the *browser* scans — a remote-dev IDE or a launcher wrapper can point `FONTCONFIG_PATH` somewhere other than your shell's, so `fc-list` in the terminal is not proof of what the browser sees. Installing the missing families into the per-user font directory needs no root. A missing font is an environment fix, not a code defect, and must never be filed as one.

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
| A page you did not touch 500s with a missing-column / undefined-table error | Local DB schema lags the code — a migration already applied on the env you are emulating was never applied here | Apply the project's migrations against the local DB, then re-probe; do not triage the 500 as the defect under investigation |

Schema drift deserves its own line because the build-identity probe cannot see it: the code is current, only the database is behind. It also disguises itself, because any endpoint that touches many models at once — an archive or admin index, a search-across-everything, a health page that counts every table — fails *entirely* on one missing column. So the symptom surfaces on a page unrelated to your change and reads as the bug you came to investigate. When the target is a local server, migrate before the first check.

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

### Read the start args off the process — do not trust your memory of them

"I started it with X" is an assumption, not an observation. A long-running server may predate the change under test, may have been launched by an earlier session, and may carry flags nobody would choose today — `--noreload` added weeks ago to work around something else, or a production server where you assume a dev one. None of that is visible from the outside: the port answers, the pages render, and the process quietly serves code it imported before your edit existed.

Identify the port owner, then dump its actual command line — `Get-CimInstance Win32_Process -Filter "ProcessId=<pid>"` on Windows, `ps -o args= -p <pid>` elsewhere — and read the flags before believing anything about the build it holds.

When the browser says a backend feature is broken while its unit tests pass, one probe separates "code bug" from "stale process" before any debugging. From the page's own authenticated session, hit the endpoint three ways and compare the result counts:

1. with no filter at all (the baseline set),
2. with a filter parameter that is known to work already,
3. with the new parameter under test.

If the known-good filter narrows the set and the new one returns the full baseline, the running process does not have the new code — restart and re-run. If the known-good filter does not narrow it either, the request is not reaching the code you think it is (wrong host, wrong route, proxy). If both narrow correctly, the defect is genuinely in the feature and debugging can start.

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
| `networkidle` never settles | The goto times out (~30s) but the page clearly rendered — the content is on screen while `browser_navigate` / wait-for-load reports failure | `networkidle` waits for "no in-flight requests for ~500ms", and two independent things make that condition unreachable. (a) A dev server that recompiles per request (e.g. Turbopack) plus a client that refetches on an interval (e.g. React-Query) — there is always something in flight. (b) A page holding a **persistent connection** open by design — SSE / `EventSource`, a WebSocket, long-polling, or an analytics beacon — which never closes, so the count never reaches zero, in a production build exactly as much as in dev | Wait on `domcontentloaded` or an **explicit element** (`wait_for` the exact selector / text you are asserting), never on network-idle. A production build removes cause (a) only; nothing removes (b) — if the page streams, `networkidle` is simply unusable |
| Forced-error / 500 state shows stale rows | You force a backend error (stop the API, inject a 500) but the UI keeps showing the previous good data, so the error state "won't reproduce" | A client query cache (e.g. React-Query, SWR — often a ~30s stale window) serves the last successful response from memory; the current tab never refetches inside the window | Assert the error state from a **fresh browser context** (cold cache), or hard-invalidate the cache — do not trust the warm tab |
| Dirty `beforeunload` blocks navigation | `browser_navigate` hangs and the goto times out with no new page | The current page has a dirty-state `beforeunload` guard (unsaved-changes prompt); the browser raises a native confirm dialog that silently blocks the programmatic navigation | Clear the dirty state (or pre-register a dialog handler / accept-the-dialog step) **before** navigating away; `browser_navigate` alone will not leave a dirty page |

The through-line: on a dev server the "quiet network / warm cache / clean navigation" assumptions the tooling defaults to are all violable — and the quiet-network one is violable on *any* build, dev or production, whenever the page holds a stream open. When a wait times out, an error state won't reproduce, or a navigate hangs, suspect the wait strategy / cache / unload guard *before* concluding "bug."

The `networkidle` caveat also qualifies the wait strategy in `role-smoke-tests` — prefer an explicit element wait over network-idle on a recompile-per-request dev server, and on any page carrying an SSE / WebSocket / long-poll connection regardless of environment.

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
- [ ] Local target: migrations applied against the local DB, so the schema matches the code under test.
- [ ] Rendering-sensitive run: the browser host has the font families for every script the run will judge.
- [ ] Self-started server: its real start args read off the process, not recalled.
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
| Reason about a running server from how you remember starting it | The process may predate the change, or belong to another session; `next start` vs `next dev` and `--noreload` are invisible from outside | Dump the port owner's real command line and read the flags |
| Debug a "broken" backend feature whose unit tests pass, without probing the endpoint | Cannot tell a code bug from a process serving pre-edit code | Probe three ways (no filter / known-good param / new param) and compare counts first |
| QC a local target without applying migrations | A schema behind the code 500s any endpoint that touches the missing column — usually a page you never changed | Migrate the local DB before the first check |
| File an RTL / non-Latin rendering defect from a headless screenshot without checking the host's fonts | The browser can only draw glyphs the host has; a Latin-only image renders every other script as tofu whatever the page does | Confirm the families exist in the dir the browser scans (`FONTCONFIG_PATH` may differ from your shell's), then re-shoot |
| Wait on `networkidle` at all on a live app | It never goes idle when the server recompiles per request, and never when the page holds an SSE / WebSocket / long-poll / beacon open → a ~30s timeout on a page that actually rendered | Wait on `domcontentloaded` or an explicit element; a prod build fixes only the recompile half |
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
