---
name: data-fetching-states
description: Data-layer contract that maps a fetch result to exactly one UI state, sitting beneath admin-states which owns display. Owns the rule that a data hook MUST surface the error and never swallow it into a nullish or empty value, the UI state enum (loading, empty, no-results, access-required, error, partial-error), and the HTTP-status-to-state mapping where 401 or 403 means access-required, 404 means not-found, 400 or 409 means business-rule-error, and 5xx or network means retryable error. Activates when writing or reviewing any data-fetching hook, query, or loader, and when debugging a blank screen or empty shell that appears for only some users. Generic and portable — the data-fetching library and the auth status convention are project-supplied adapter inputs.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - surface-the-error rule (a data hook never collapses an error into null/[]/{})
  - the UI state enum — loading | empty | no-results | access-required | error | partial-error
  - HTTP-status-to-state mapping (401/403, 404, 400/409, 5xx/network)
  - the empty-data vs inaccessible-data distinction
  - the "no 0/0 shell on a 403" rule
  - retry / stale policy per outcome class (retry 5xx/network, never retry 4xx)
  - the DATA STATE MAP emitted per resource
defers_to:
  - admin-states (renders each state; owns the visual/display contract)
  - admin-roles-and-permissions (UI hide is NOT authorization; gate at the API)
  - admin-crud (list-level wiring of the resolved state)
  - project data-fetching layer (which library; how a response/error is shaped)
  - project auth layer (how 401 vs 403 is signalled)
user_invocable: false
---

# data-fetching-states

## Purpose

A blank screen for "some users" is almost never an empty database — it is an access error (401/403) that a hook quietly turned into `[]` or `null`. The display layer then renders a correct-looking empty shell for a request that actually failed. This skill owns the layer underneath display: it forces every fetch outcome to resolve to exactly one named state, and it forbids the silent collapse of an error into a falsy value. Empty data and inaccessible data are different facts and must reach the UI as different states.

## When to use

Activate when:

- Writing or reviewing any data-fetching hook, query, or route loader.
- A consumer branches on the result of a fetch to pick what to render.
- Debugging a "blank screen / empty shell for some users" symptom.
- Deciding retry or stale behavior for a request.
- A list partially loads (some items resolved, some failed).
- Reviewing a `catch` that returns a default value instead of propagating.

## Inputs (adapter)

1. **Data-fetching library** — the project's query/fetch mechanism (any async data library, a router loader, or a hand-rolled fetch wrapper). The skill specifies WHAT the hook must surface (status + error + data), not which library produces it.
2. **Auth / permission status convention** — how the backend signals "not authenticated" vs "authenticated but not allowed" (e.g. 401 vs 403, or a typed error code). The skill maps these to `access-required`; the project supplies the actual shape.
3. **Status extractor** — how to read an HTTP status (or equivalent error category) off a failed request in this stack. Provided once, reused by the mapping.
4. **Retryable classifier (optional)** — project override for which statuses are retryable, if it differs from the default (5xx + network = retry; 4xx = never).

## Read-only investigation steps

1. **Does the hook return only `data`?** If the signature is `{ data }` and the error is not in the return shape, the error is being discarded — the root smell. Look for the matching `catch`.
2. **What does the `catch` (or `onError`) do?** If it `return []`, `return null`, or sets default state and stops, the error is swallowed. Trace where the original status went.
3. **Where does 401/403 land?** Follow an unauthorized response through the hook to the UI. If it arrives as empty data, that is the "empty shell for some users" bug.
4. **How does the consumer branch?** If it only checks `loading` and `data?.length`, it cannot distinguish empty from inaccessible from errored. It is missing states.
5. **What is the retry policy on 4xx?** If 401/403/404 are retried, you have a retry storm hidden behind a spinner.

## Decision framework

### The state enum (resolve to exactly one)

```
loading        request in flight, no usable prior data
empty          request OK, resource genuinely has zero rows (ever)
no-results     request OK, rows exist but the active filter/query returned zero
access-required request rejected for identity/permission reasons (401/403)
error          request failed (retryable: 5xx/network; or terminal: business rule)
partial-error  collection request where some items resolved and some failed
```

Every fetch outcome maps to one — and only one — of these. `empty` and `access-required` are never the same state.

### HTTP status -> state -> what the UI shows

| Outcome | State | What the UI shows (delegated to admin-states) |
|---|---|---|
| in flight | `loading` | Skeleton matching final layout |
| 200 + non-empty | (data) | The data |
| 200 + zero rows, no active filter | `empty` | "Nothing here yet" + primary create CTA |
| 200 + zero rows, active filter | `no-results` | "No matches" + clear-filters CTA |
| 401 / 403 | `access-required` | Access-required state — sign in, or "subscription/permission required" — NOT an empty list |
| 404 | `error` (not-found) | Not-found state for that resource |
| 400 / 409 | `error` (business-rule) | Authorized-but-rejected message (validation/conflict); the user did reach the resource |
| 5xx / network / timeout | `error` (retryable) | Retryable error block with Retry |
| collection, mixed item outcomes | `partial-error` | Resolved items + per-item failure indicator |

### The "no 0/0 shell on a 403" rule

```
            request --> fetch
                          |
              +-----------+-----------+
              |                       |
           rejected                 resolved
              |                       |
        read status               data.length?
              |                  +----+----+
   401/403 -> access-required    0         >0
   404     -> error(not-found)   |          |
   400/409 -> error(business)  filter?     data
   5xx/net -> error(retryable)  /    \
                              yes     no
                               |       |
                          no-results  empty
```

Rule: the consumer reaches the `data.length === 0` branch ONLY after the request resolved successfully. A rejected request must short-circuit to `access-required` / `error` BEFORE any length check. Rendering a `0/0` count shell on a 403 is the canonical bug this skill exists to prevent.

### Retry / stale policy per class

| Outcome class | Retry? | Stale data |
|---|---|---|
| 5xx / network / timeout | Yes — bounded, backoff | Keep showing last-good data dimmed if present |
| 401 / 403 | No — re-auth or escalate; retrying cannot fix permission | Clear stale; do not show another user's cached rows |
| 404 | No — resource will not appear by retrying | n/a |
| 400 / 409 | No — auto-retry repeats the same rejected request | Keep the form/context so the user can correct |

- Auto-retry is for transient classes only. A 4xx is a decision by the server, not a transient failure.
- Bound retries (finite count + backoff); an unbounded retry on a flapping 5xx is a self-inflicted load spike.

### Admin-panel examples

Concrete admin situations mapped to the one correct state. These reinforce the status->state contract above; the plugin never depends on the specific surface (board / dashboard / list / detail) — it depends on the resolved state.

| Admin situation | Correct state | Why — and the bug to avoid |
|---|---|---|
| Board with zero cards in one column (request 200, column genuinely has no items) | `empty` (per-column) | Legitimately empty. Show the column with an empty affordance, not an error. |
| Board fails to load because the viewer cannot access it (401/403) | `access-required` | Never render an empty board that looks like "no work exists" — that is the 0/0 shell bug for a denied request. |
| Dashboard where a metric genuinely has zero records (200 + 0) | `empty` / `no-data` | A real zero is data. Render `0` as a value only when the request resolved successfully. |
| Dashboard KPI whose API errored (5xx/network) | `error` (retryable) | NEVER render `0` for a failed KPI request — a fabricated zero misleads. Show a retryable error tile, not the number 0. |
| List that is truly empty (200 + 0 rows, no active filter) | `empty` | Show "Nothing here yet" + primary create CTA. |
| List that returns zero rows because a filter/search is active (200 + 0 rows, filter on) | `no-results` | Show "No matches" + clear-filters CTA — never the create-first CTA. |
| Detail / form where the record does not exist (404) | `error` (not-found) | The record is gone or never existed; retrying will not conjure it. |
| Detail / form the viewer is not allowed to open (401/403) | `access-required` (forbidden) | Distinct from not-found: the record may exist; the viewer lacks permission. Do not leak existence by showing not-found, and do not show an empty form. |
| Action returns 409 (e.g. transition not allowed in current status, or duplicate) | `error` (business-rule) | Surface the rule the server stated ("already processed", "cannot transition from X"), NOT a generic "something went wrong". The viewer reached the resource and was authorized — only the operation was rejected. |
| Composite view where some widgets/rows loaded and one failed | `partial-error` | Keep the resolved widgets/rows; flag only the failed one with a per-item retry. One failed widget must not blank the whole page. |

- `empty` vs `access-required`: a zero count is only honest after a 2xx. A 401/403 that renders as zero is the canonical bug this skill prevents.
- `no-data` vs `error` on a KPI: do not let a failed metric request silently render `0`. Resolve the request first; `0` is a value, an error is a state.
- `empty` vs `no-results`: the difference is the active-filter signal, not the row count.
- `not-found` (404) vs `forbidden` (401/403): both block the detail view, but they are different facts and produce different states and different copy.

## Safety gates

- **Never** return only `data` and discard the error — the hook's return shape MUST carry status + error alongside data.
- **Never** collapse an error into a nullish or empty value (`return []`, `return null`, `return {}`) inside a `catch`/`onError`.
- **Never** render an empty or zero-count shell when the real cause is 401, 403, or 404.
- **Never** treat 401/403 as `empty` or `no-results` — it is `access-required`.
- **Never** auto-retry a 4xx (401/403/404/400/409).
- **Never** reach the `data.length === 0` branch before confirming the request resolved successfully.
- **Never** show one user's stale cached rows after an `access-required` outcome.
- **Never** let one failed item in a collection drop the whole collection to `error` — that is `partial-error`.

## Validation checklist

Before committing a data-fetching change:

- [ ] The hook surfaces status + error + data; the error is never swallowed.
- [ ] No `catch`/`onError` returns `[]`, `null`, or `{}` in place of the real failure.
- [ ] 401/403 resolves to `access-required`, not `empty`.
- [ ] 404 resolves to not-found; 400/409 to business-rule; 5xx/network to retryable.
- [ ] The `data.length === 0` branch is reachable only after a successful resolve.
- [ ] `empty` and `no-results` are distinguished using an active-filter signal.
- [ ] Retryable classes retry with bounds + backoff; 4xx never auto-retries.
- [ ] Stale data is cleared on `access-required` (no cross-user leakage).
- [ ] Collection endpoints can express `partial-error` without dropping resolved items.
- [ ] The consumer branches on STATE, not just on `loading` + `data?.length`.

## Output format

When wiring a resource, emit a DATA STATE MAP:

```
DATA STATE MAP — <resource-name>
  Source: <adapter: data-fetching library / loader>
  Auth signal: <adapter: 401 vs 403 convention>

  in flight                  -> loading
  200 + rows                 -> (render data)
  200 + 0 rows, no filter    -> empty          (CTA: create first <entity>)
  200 + 0 rows, with filter  -> no-results     (CTA: clear filters)
  401 / 403                  -> access-required (sign-in / permission required)
  404                        -> error:not-found
  400 / 409                  -> error:business-rule (authorized, rejected)
  5xx / network / timeout    -> error:retryable (Retry; backoff; keep last-good dimmed)
  collection: mixed outcomes -> partial-error  (per-item retry)

  Retry: 5xx/network = yes (bounded); 4xx = never
  Stale on access-required: cleared
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `catch (e) { return [] }` in a data hook | The error vanishes; the UI shows a correct-looking empty state for a failed request | Surface status + error; map to `error` / `access-required` |
| Hook returns only `{ data }` | Consumer cannot tell empty from inaccessible from errored | Return `{ data, error, status }` (or library equivalent) |
| Treating 403 as `empty` | Renders a 0/0 shell; the user thinks there is nothing, not that they lack access | Map 401/403 to `access-required` |
| `data.length === 0` checked before the request resolved | An access error is read as "no rows" | Short-circuit rejected requests before any length check |
| Auto-retry on 401/403/404 | Retrying cannot grant permission or conjure a missing resource; just a storm | Retry 5xx/network only; re-auth or escalate on 4xx |
| Unbounded retry on 5xx | Self-inflicted load spike during an outage | Bounded retries + backoff |
| `empty` and `no-results` share one branch | Either a stale "add first" CTA on a filtered view, or no clear-filters path | Distinguish via active-filter signal |
| One failed list item drops the whole list to `error` | Lose N resolved records because 1 failed | Resolve to `partial-error`; keep resolved items |
| Showing cached rows after a 401 | Cross-user data leakage; a logged-out/forbidden view shows prior data | Clear stale on `access-required` |

## Portability rationale

The contract is data-layer logic, not framework UI. It does not depend on:

- A specific data-fetching library (the return-shape rule applies to any async fetch).
- A specific transport (HTTP status is the common case; any error-category signal maps the same way).
- A specific auth implementation (the 401-vs-403 distinction is supplied as an adapter input).

Only the status extractor and the auth-status convention are project-specific, and both are named adapter inputs.

## Cross-references

- `admin-states` — renders each resolved state (loading / empty / no-results / error / partial-error); owns the visual contract. This skill decides WHICH state; that skill decides how it LOOKS.
- `admin-roles-and-permissions` — UI hide is NOT authorization; the `access-required` state pairs with an API-side gate, never a UI-only hide.
- `admin-crud` — consumes the resolved state for list/detail wiring; the list/detail examples above feed it.
- `admin-dashboard-overview` — KPI/metric tiles must apply the `no-data` (200 + 0) vs `error` (request failed) split; never render `0` for an errored KPI.
- `admin-kanban-workflow` — per-column `empty` vs board-level `access-required`; a denied board is never an empty board.
- `qa-browser` (agent) verify-identity-and-rbac — live proof that 401/403/404 produce `access-required`/not-found and never a silent empty shell.
