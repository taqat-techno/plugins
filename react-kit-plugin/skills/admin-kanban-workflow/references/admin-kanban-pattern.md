# Admin kanban / board pattern

A reusable reference for building an admin board (kanban-style) where Records move through an ordered set of project-supplied states. Domain-neutral: the same layout and behavior work for Orders, Tickets, Requests, Customers, Products, or any Records with a status field. Roles are referred to generically as admin / manager / operator / viewer.

## Core principles

These rules hold regardless of domain. Treat them as the contract the board implementation must satisfy.

- States are **project-supplied**, not hard-coded. The board renders whatever ordered state set the consuming project passes in.
- Column order is **fixed and frontend-owned**. The API may return states in any order or omit some; the board reorders to the configured sequence and synthesizes missing columns.
- Card movement is **action-based**, not drag-based. Transitions happen via buttons in a detail drawer.
- Role and state gating happens at the **render layer** (don't render an unavailable action), with the backend as the authoritative second check.
- Layout is **full-height and responsive** via flex, never fixed pixel heights on the container.

## State model (project-supplied)

The board is driven by an ordered list of state configs supplied by the consuming project. The plugin never assumes specific state names.

| Field | Purpose |
|-------|---------|
| `key` | Stable identifier for the state (matches the Record's status field). |
| `label` | Human-readable column title. |
| `order` | Position in the pipeline; defines left-to-right column sequence. |
| `color` (optional) | Accent for header/badge. |

Example (illustrative — not required): a three-state set `New / In progress / Done`. Any project may supply two states or twelve; the names carry no behavior. The plugin must work identically whether the states are `New / In progress / Done`, `Draft / Review / Published`, or anything else.

## Board layout

The board is a horizontal row of ordered columns, one per state, inside a scroll container.

- Container: full height of its parent, `flex flex-col`. A thin toolbar (refresh / hint) is `shrink-0`; the board row grows with `flex-1 min-h-0`.
- Board row: horizontal scroll for columns (do not hide overflow-x). Each column is `h-full` relative to the board container.
- Column: `flex flex-col` with a sticky header and a scrollable card area beneath it.
- Card area: `flex-1 overflow-y-auto` so each column scrolls vertically and independently.

Rule: every `flex-1` child that must shrink needs `min-h-0`, otherwise it will not shrink below its content height and breaks scrolling.

## Column anatomy

Each column has a sticky header and a body that is either a card list or an empty-state affordance.

| Part | Behavior |
|------|----------|
| Header | Sticky (`sticky top-0 z-10`) so it floats above scrolling cards; shows label, count badge, and a collapse toggle. |
| Count badge | Small rounded badge showing the number of cards in this state. |
| Card area | Scrollable flex column of cards; renders the empty state when there are no cards. |
| Width (expanded) | Roughly 240–280px (`min-w-[240px] max-w-[280px]`). |
| Width (collapsed) | Narrow (~56px / `w-14`). |

## Collapsible columns

Columns collapse independently to save horizontal space. Collapse state is tracked per state key (e.g. a `Record<stateKey, boolean>` with a `toggleCollapse(key)`).

- Expanded header: horizontal layout — label on the left, count badge + collapse button on the right.
- Collapsed header: vertical layout — collapse button on top, rotated vertical label in the middle (`[writing-mode:vertical-rl] rotate-180`), count badge at the bottom.
- When collapsed, the card scroll area is hidden (conditional render) and a thin `flex-1` filler keeps the column full height.
- Accessibility: set `aria-expanded` on the toggle and a descriptive `aria-label` (e.g. "Collapse In progress column").

Anti-patterns: do not fix the header height (let content size it); do not render both header layouts at once; do not forget `sticky` + `z-10`.

## Card anatomy

A card is a compact summary the operator can scan and click. Keep it neutral and minimal.

- Primary line: Record identifier or title.
- Secondary line(s): a few key fields relevant to triage (status-adjacent metadata, owner, timestamp).
- Whole card is clickable and opens the detail drawer.
- Visual: solid border to distinguish from the empty-state affordance (which uses a dashed border).

## Per-column count and pagination

Each column header shows a live count of the cards currently in that state.

- The count reflects the cards present in the column's data, updated on refetch.
- Pagination inside a column's scroll area is **deferred** until the data source supports paged results per state. Until then, render the available cards and rely on vertical scroll.
- When server-side paging is added, append a "load more" affordance at the bottom of the card area; never silently truncate.

Anti-pattern: do not invent client-only pagination that hides cards the count claims exist.

## Empty-column affordance

When a column has no cards, render a centered empty state instead of an empty list.

- Container fills available height: vertically centered (`items-center justify-center`) with a sensible minimum (`min-h-[120px]`) and extends through the `flex-1` space.
- Text is muted and centered; use a dashed border to differentiate from a card.
- Message is generic (e.g. "No items"), never domain-specific.

Rules: render the empty state only when the card count is zero; never render cards and the empty state simultaneously; do not use a tiny box that fails to fill the column height.

## Detail drawer (open from card)

Clicking a card opens a right-edge slide-out drawer. It is the single place where Record details and actions live.

- Structure: a fragment containing a backdrop plus the panel. Sticky header (Record id/title + close button) over a scrollable body. The body holds a Details section, an Actions section, and optional inline action panels.
- Non-modal: the user can still see and interact with the board; close via backdrop click or the X button.
- Drawer detail is **derived from the board query**, not a separate fetch. After a successful action the board refetches and the open drawer reflects the new state.
- Drawer state to track: `selectedCard` (null = closed) and `activePanel` (which inline panel, if any, is open).

Anti-patterns: do not make the drawer modal; do not move cards via drag from the drawer; do not reload the whole board manually after an action (rely on cache invalidation).

## Action-based movement vs drag

Movement between states is performed by action buttons in the drawer that call a set-state mutation — never by dragging cards.

- Each action button maps to a single logical transition and is pre-gated by current state + role + Record condition.
- The mutation is the authority on legality; the UI gating is a usability layer, not the security boundary.
- Do not update the card's state optimistically — wait for the mutation to succeed, then let invalidation refresh.
- Render exactly one button per logical transition; never show conflicting buttons for the same move.

Some transitions are system-driven (e.g. time-based) rather than operator-initiated; render those as disabled/info-only, not as clickable actions.

## Inline action panels

Some transitions need extra input first (assign an owner, attach a file, record a value). These use collapsible inline panels inside the drawer's Actions section.

- Clicking an action button toggles `activePanel`. When `activePanel === '<name>'`, a form slides in with inputs and a footer (Cancel + Submit).
- On submit: validate required fields, call the mutation; on success clear the panel (optionally auto-close the drawer).
- On cancel: clear the panel and any local error state.
- Track the active panel with a union/string state; render form inputs only inside the matching conditional.

Anti-patterns: do not render form inputs outside the `activePanel` conditional; do not disable the action button while its panel is open (re-clicking to toggle closed is clearer); do not persist `activePanel` across separate drawer opens.

## Role and state gating

Compute action visibility at render time from three inputs and conditionally render — do not render-then-disable.

| Input | Example check |
|-------|---------------|
| Role | `isManager` / `isAdmin` from a single role query, cached at the drawer level. |
| Current state | The action only applies to certain source states. |
| Record condition | A field on the Record gates the action (e.g. a required attachment is present). |

Rules: call the role check once per drawer, not once per button; if the role lacks access, omit the button entirely; never rely on mutation failure as the gating mechanism — the backend validates as defense in depth, but the UI must not surface unavailable actions.

## Data fetching, errors, and refresh

A board hook owns the query and exposes `{ data, isLoading, isError, refetch, isFetching }`. Mutation hooks expose `{ isPending, isSuccess, isError, mutate, mutateAsync }`.

- Loading: render a skeleton column per state.
- Error: centered message with a Retry button that calls `refetch()`; do not disable Retry while refetching; show only one error at a time.
- Mutation pending: the triggering button shows a spinner and all actions disable until it resolves.
- Mutation error: extract a message from the standardized error shape and show it in a dismissible alert inside the drawer; clear it when the user submits again or closes the panel.
- On mutation success: invalidate the board query key so it refetches. Prefer targeted invalidation over manual full reloads. Do not leave the drawer open with stale data — refetch or close.

Anti-pattern: do not use optimistic updates for state transitions; wait for confirmation.

## Stable column ordering (test contract)

The board must render columns in the configured order regardless of API ordering, and must not render removed states.

- Build a lookup from the API response keyed by state, then iterate the configured state list, hydrating each from the map or synthesizing an empty column when absent.
- Tests verify: columns appear in the exact configured order; a state removed from the config does not appear in the DOM; transitions are gated by role and Record condition; an action requiring side-data is unavailable until that data exists.

Anti-patterns: do not render columns in raw API order; do not skip a configured state because the API omitted it (synthesize an empty column); do not let users reorder states without persisting the preference.

## Mobile fallback

The horizontal multi-column layout does not fit narrow viewports. Below a breakpoint, fall back to a single-column view.

- Replace the side-by-side columns with a **stacked** layout: one state's cards visible at a time.
- Provide a **select-column** control (segmented control or dropdown listing the project-supplied state labels) to switch which state is shown.
- Show the selected state's count next to the selector.
- The detail drawer can expand to full-width (or full-screen) on small viewports; everything else (action gating, inline panels, invalidation) behaves identically.

Rule: the mobile fallback changes presentation only — the state model, gating, and movement rules are unchanged.
