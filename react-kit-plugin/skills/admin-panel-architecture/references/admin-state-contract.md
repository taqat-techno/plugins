# Admin data-state contract

Every admin view in this kit honors a single, canonical set of data states. This page is the quick-reference card for the `data-fetching-states` skill: it defines the state enum, the HTTP-status to state mapping, and the rules each list, detail, drawer, dialog, and table must satisfy before it is considered done. The `data-fetching-states` skill is the long-form companion; this contract is the checklist.

This document is domain-agnostic. Replace the neutral placeholders (Orders, Tickets, Requests, Customers, Products, Records) and the generic roles (admin, manager, operator, viewer) with your own. Plugin behavior never depends on any example below.

## The canonical state enum

Every view resolves to exactly one of these states at any moment. No view may render a blank surface that maps to none of them.

| State | Meaning | What the view shows |
|---|---|---|
| `loading` | First fetch in flight, no data yet | Skeleton or spinner sized to the eventual content |
| `empty` | Fetch succeeded, zero records exist | Explicit empty-state message and (if applicable) a create affordance |
| `no-results` | Fetch succeeded, records exist but the active filter/search excludes all of them | "No matches for the current filter" plus a clear-filters affordance |
| `access-required` | Caller is unauthenticated (401) | "Sign-in required" prompt or redirect to the sign-in flow |
| `forbidden` | Caller is authenticated but lacks permission (403) | "You do not have permission to view this." No retry button |
| `not-found` | Target record does not exist (404) | "This record no longer exists." Offer navigation back to the list |
| `business-rule-error` | Action rejected by a domain rule (409, sometimes 422) | Inline alert with the server's message; recoverable after the user changes something |
| `server-error` | Backend fault or network failure (5xx, network) | "Something went wrong." plus an explicit Retry control |
| `partial-failure` | Composite view where some panels loaded and others failed | Render what loaded; show a scoped error + retry only on the failed panel |
| `stale` | Cached data is shown while a background refetch runs | Show existing data; add a subtle refreshing indicator. Never blank the surface |

Distinguish `empty` (the dataset is genuinely empty) from `no-results` (a filter is hiding everything). They lead to different user actions: create-a-record versus clear-the-filter.

Distinguish `loading` (no data yet, first load) from `stale` (data already on screen, refetch in background). Gate the skeleton on the first-load flag, not on the background-fetch flag.

## Status to state mapping

The data layer maps transport signals to the enum. Views read the resolved state, not raw status codes.

| Signal from data layer | Resolved state |
|---|---|
| First fetch pending, no cached data | `loading` |
| Background refetch pending, cached data present | `stale` |
| Success, total count is 0 and no filter active | `empty` |
| Success, total count is 0 but a filter/search is active | `no-results` |
| Success, records present | (render data) |
| HTTP 401 | `access-required` |
| HTTP 403 | `forbidden` |
| HTTP 404 | `not-found` |
| HTTP 409 (and 400/422 violating a domain rule) | `business-rule-error` |
| HTTP 400/422 with field-level details | `business-rule-error` (render field errors inline) |
| HTTP 5xx | `server-error` |
| Network/timeout (no response received) | `server-error` |
| Composite view, mixed success and failure across panels | `partial-failure` |

Map by category, not by exact code where a category covers several codes. Treat any 5xx the same; treat any unhandled 4xx as `business-rule-error` with a generic message rather than falling through to `server-error`.

## The "no silent empty shell" rule

This is the load-bearing rule of the contract.

> A view must never render a chrome-only shell (header, padding, borders) with no content and no state indicator. If a view has no data to show, it MUST resolve to one of `empty`, `no-results`, `forbidden`, `not-found`, or `server-error` and render that state's message. A blank interior reads as "the page broke" to the user.

Concrete obligations:

- Handle `empty` and `no-results` as deliberately as you handle `loading` and `server-error`. A zero-length result set is a designed state, not an afterthought.
- Never show a stale "Loading..." after data has arrived. Gate the loading UI on first-load-pending, not on any-fetch-pending.
- For composite views, scope failure to the panel that failed (`partial-failure`); do not blank the whole page because one sub-query errored.
- `forbidden` is terminal for the current session/role: do not offer a Retry control, since retrying without a permission change cannot succeed. `server-error` is transient: always offer Retry.

## Authorization is UX gating only

Hiding or disabling an action for a role is a usability optimization. The backend authorizes every action independently. A caller who bypasses a disabled control still receives `forbidden` (403) or `business-rule-error` (409), and the view must render that state gracefully rather than assuming the action could not have been attempted.

## Recoverability by state

| State | Recoverable in place? | Affordance to offer |
|---|---|---|
| `loading` | n/a | none (transient) |
| `stale` | n/a | none (transient indicator only) |
| `empty` | yes | create-a-record (if permitted) |
| `no-results` | yes | clear filters / adjust search |
| `access-required` | yes | sign-in |
| `forbidden` | no | none (requires a role change off-screen) |
| `not-found` | no | navigate back to the list |
| `business-rule-error` | yes | show server message; user fixes input, then re-submits |
| `server-error` | yes | Retry |
| `partial-failure` | partly | Retry on the failed panel only |

## Example (illustrative — not required)

A reviewer opens a detail drawer for a single Order. The data layer reports first-load-pending, so the drawer shows a skeleton (`loading`). The fetch returns 404 because the Order was deleted by another operator; the drawer resolves to `not-found` and offers a link back to the Orders list. Had the reviewer instead lacked the Orders permission, the same fetch would have returned 403, resolving to `forbidden` with no Retry button. None of this behavior is wired to the word "Order" — swap in Tickets, Requests, Customers, Products, or Records and the contract is identical.

## Checklist before a view is done

- Resolves to exactly one enum state at all times; no unhandled branch.
- `empty` and `no-results` are distinct and both rendered.
- `loading` keys off first-load, not background refetch; `stale` keeps data on screen.
- 401, 403, 404, 409, 5xx, and network each map to their state and render the right message.
- `forbidden` and `not-found` omit Retry; `server-error` and `partial-failure` include scoped Retry.
- No chrome-only shell is reachable for any state.
- See the `data-fetching-states` skill for the hook-level implementation patterns this card summarizes.
