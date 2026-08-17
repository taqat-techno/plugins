---
name: spreadsheet-dashboards
description: Design, review and restyle Odoo `spreadsheet.dashboard` workbooks (o-spreadsheet; Odoo 16+, mechanisms verified on 17). Owns the two-rendering-systems model (the sheet body is one raster canvas that CSS cannot reach; only figures are DOM), the CSS specificity rule against the library's JS-injected stylesheets, the figure `data-id` scoping hook and the scope-isolation trap, the figures-or-invisible-on-mobile rule, geometry-is-data (colNumber sets the sheet width, not the last used column), the period-over-period delta recipe, and the correctness rules for pivot domains, literal constants and filter coverage. Activates when asked to build, redesign, restyle, audit or review an Odoo spreadsheet dashboard or a `spreadsheet.dashboard` record; when someone proposes CSS to change dashboard cell colours, card backgrounds or "the dashboard background"; when a dashboard renders blank on a phone, shows a permanent horizontal scrollbar, refuses to centre, or its section labels are off-screen; when authoring or editing a dashboard workbook JSON (figures, pivots, globalFilters, cols/rows, styles); when a KPI needs a delta, trend or comparison; and when auditing the numbers already on a dashboard against the pivots and models they claim to summarise. Anti-triggers — this skill writes and runs no tests, and it reviews the workbook artifact, never the state of your task or whether your work is finished.
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - the two-rendering-systems model (canvas cells vs DOM figures) and what each layer can change
  - the specificity rule for overriding library CSS injected from JS at import time
  - the figure `data-id` scoping hook and the shared-action scope-isolation trap
  - the figures-or-invisible-on-mobile rule (below 768px only figures render)
  - geometry-is-data (colNumber/rowNumber set the sheet box; spacing is empty gutter columns)
  - the period-over-period delta recipe (twin pivot + filter offset + scorecard baseline)
  - dashboard correctness rules (translatable-name domains, literal constants, unlabelled period exemptions)
  - the four-way A/B/C/D separation used to plan and review a dashboard redesign
defers_to:
  - theme-scss / theme-design for website-theme SCSS variables and palettes (this skill governs backend dashboard chrome only)
  - reviewer for general Odoo module review conventions and manifest/version hygiene
  - i18n / i18n-audit for `.pot` extraction, msgid discipline and the translation-file workflow once labels are wrapped in `=_t()`
  - stack-doctor for module-update and DB-lifecycle verification (reading the server log rather than the exit code, cloning a DB with its filestore) — this skill only says which checks a dashboard change needs
  - a general data-visualisation skill, where one is available, for chart-type choice and palette accessibility; this skill owns only the subset o-spreadsheet can actually express
  - the issue/decision owner for any defect that source control shows was a deliberate, documented choice
user-invocable: false
---

# spreadsheet-dashboards

## Purpose

An Odoo spreadsheet dashboard looks like a web page and is not one. The body is a raster canvas; only figures are DOM. Nearly every wasted hour on these dashboards comes from attacking the wrong layer — writing CSS for cells that CSS cannot reach, or "spacing out" cards that are absolute pixels stored in data. These reflexes route each change to the layer that actually owns it, and encode the design and correctness failures that survive a naive re-skin.

## When to use

Activate when:

- You are asked to build, redesign, restyle or audit a `spreadsheet.dashboard`.
- Someone proposes CSS to change cell colours, the "paper" background, or card padding.
- A dashboard is blank on mobile, scrolls horizontally forever, or never centres.
- You are editing a workbook JSON — `figures`, `pivots`, `globalFilters`, `cols`, `rows`, `styles`.
- A KPI needs a delta, a baseline, a trend, or any comparison.
- You are auditing the numbers already on a dashboard against the pivots and models behind them.

Do **not** activate this skill as a generic "is my work done" check, and do not let it stand in for
writing or running tests — it reasons about a workbook artifact, nothing else.

## The rules

### 1. Two rendering systems — identify which one you are touching, first

The sheet body is a **single `<canvas>`**. Cell text, fills, borders and gridlines are raster-painted by the renderer; **CSS reaches none of it**. `drawGlobalBackground` fills opaque white across the whole sheet area, so restyling "the dashboard background" in CSS is a **verified no-op** — forcing `.o-grid { background-color: … }` and pixel-probing the canvas returns `rgba(255,255,255,255)` at every sample. Background is a `fillColor` job in the workbook JSON.

Charts and scorecards are real DOM: `div.o-figure-wrapper > div.o-figure > div.o-chart-container > canvas.o-figure-canvas`. The card **box** is stylable; the card **content** is canvas. That boundary is the whole styling model.

### 2. Out-specify, never out-order

The library injects its CSS from JavaScript at import time: the live page carries exactly **one stylesheet `<link>` at DOM position 0**, followed by ~63 `<style component="__sheet__N">` tags. Your module's compiled SCSS is inside that one link — it lands *before* every library rule. **At equal specificity the library always wins.** Core itself solves this with four-class selectors (`.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet .o-grid`). Match that depth; do not reach for `!important`, which only starts a fight with core's dark-mode `!important` rules.

### 3. `data-id` is the only per-card hook — and `.o_spreadsheet_dashboard_action` alone is a trap

A figure `id` authored in the workbook JSON surfaces as `data-id` on `.o-figure` (runtime verified). So the scoping mechanism is:

```scss
.o_spreadsheet_dashboard_action .o-figure[data-id^="<prefix>-"] { /* only our cards */ }
```

`.o_spreadsheet_dashboard_action` **alone matches every spreadsheet dashboard in the database** — yours, the other team's, and all the core ones. That is the scope-isolation trap: a "harmless" card style silently restyles a dozen dashboards you never opened. Give every figure a readable, stable slug id (`kpi-demand`, `chart-stage`); UUIDs are core's habit, not a requirement.

Never put `padding` or `margin` on `.o-figure-wrapper`. The library forces `content-box` on every `.o-spreadsheet` descendant and the wrapper carries inline width/height, so padding **inflates the box out of grid alignment** — verified: `padding: 6px` grew a 300x180 figure to 312x192. `.o-figure` itself computes to `border-box`; put breathing room there, or better, in the figure's stored `x`/`y`.

### 4. Zero figures means blank on mobile

Below 768px the mobile container renders **figures only** — no grid canvas, no cell content at all. A dashboard built entirely from styled cells shows one sentence: *"Only chart figures are displayed in small screens but this dashboard doesn't contain any."* Cells-imitating-cards is therefore an **invisible-on-mobile architecture**, not a cosmetic choice. Anything that must survive on a phone has to be a figure. Detail tables may stay as cells if you accept, in writing, that they vanish.

### 5. Geometry is data, and the sheet is as wide as its LAST column

The sheet's inline `max-width` is the sum of **all** column widths, not the last *used* one. Leaving `colNumber` at the 26-column default with 14 unused 96px columns produces a ~2884px sheet: a permanent horizontal scrollbar (`scrollWidth 2980` vs `clientWidth 1225` at 1440px) and `mx-auto` centring that **never engages**, because centring only applies when the sheet is narrower than the viewport. Fix: set `colNumber`/`rowNumber` to the content. Figures are absolute pixels from the A1 corner and are not cell-anchored; "spacing" exists only as empty gutter columns and figure coordinates.

### 6. Deltas are free — and are the highest value-per-effort change on any dashboard

Clone the pivot, register the clone in `globalFilters[].pivotFields` with `offset: -1`, point the scorecard at current as `keyValue` and prior as `baseline` with `baselineMode: "percentage"`. Cost: one duplicated pivot definition per KPI. Payoff: every headline number gains the context that separates a dashboard from a report. An absolute integer with no baseline cannot be judged — a manager cannot tell whether 312 is good.

### 7. A domain keyed on a translatable stage *name* is a correctness bug, not a style issue

Matching `stage_id.name ilike '…'` is fragile in three compounding ways: stage names are `translate=True`, so **one translation silently zeroes every card**; renaming a stage does the same; and keyword buckets do not partition their total, so stages matching no bucket become invisible and the parts never sum to the whole. **Group by the stage relation instead** (`groupBy: ["stage_id"]`, or a stored `state` field where one exists). One bar chart grouped on the relation replaces five keyword cards and fixes both defects at once — every stage appears, including the ones currently matching nothing.

### 8. Never ship a literal constant styled as a measurement

A hardcoded `"0"` carrying a number format renders `0.00%` — **indistinguishable from a real measurement**, and it invites a manager to believe the figure. If no source exists, remove the card or label it explicitly as a placeholder; do not render a placeholder in the same visual language as a measured KPI. The same rule covers a card whose formula silently ignores the period filter while sitting beside period-filtered siblings: either wire the filter or state the exemption in the label ("all time").

### 9. RTL is hard-disabled inside the sheet — do not fake it with alignment

The library forces `direction: ltr` on itself and every descendant, commented *"rtl not supported ATM"*. An Arabic session therefore gets **mirrored chrome around an LTR sheet**. Arabic strings shape correctly on canvas; column order, default alignment and figure coordinates stay LTR. Do **not** set `align: "right"` inside a full-width merge to fake RTL order: the text then renders at the far right of the merged range (x≈1540px on a 1540px content span) and section labels become **blank coloured strips at normal widths**, appearing only on very wide screens. Left-align section labels and merge only across the used span.

### 10. Dark mode is forced light, and chart series colours are not yours

Core deliberately forces the spreadsheet back to light with `!important` ("until we have the proper scss toolchain"); treat dark dashboards as unsupported. Chart series colours come from a **hardcoded 20-colour runtime palette cycled by dataset order** and are not storable in the chart definition — CSS cannot recolour them. Only a `chartRegistry` wrapper around `getChartRuntime` can, and **that is global**: it repaints every spreadsheet chart in the session, not just your dashboard. Same for `Chart.defaults.font.family`. Take the global cost deliberately or branch on `getters.isDashboard()` inside the wrapper.

### 11. The design method

Figures for KPIs, charts for distribution and trend, **cells only for tables and labels** — because a cell is canvas (rule 4: it disappears entirely below 768px, and it can never carry card chrome since no `.o-figure` exists for CSS to reach). A fixed design width (~1000-1200px), because the sheet's `max-width` is the sum of its columns and `mx-auto` engages only when that sum is under the viewport (rule 5). Colour spent **semantically** — exception amber, breach red, improvement green, everything else neutral ink on white: one hue per status label spends the whole palette on identity, after which a colour change carries no information and the reader has nothing left to scan for. Every headline KPI carries a comparison, for the reason in rule 6 — an absolute integer is unjudgeable. Chart titles authored as `""` on the figure and rendered as a styled cell above it, because the canvas title is locked at 22px in a different font family than the cells, so an authored title guarantees two type systems in one card.

### 12. Plan and review in four separations

Any dashboard redesign splits cleanly, and stating the split up front is what makes the plan reviewable:

- **A — business logic unchanged.** Pivot semantics, model methods, domains that survive. Name them explicitly as untouched.
- **B — workbook JSON configuration.** Geometry, styles, figures, pivots, filters, formats, `=_t()` labels, drill-down links. This is the bulk (typically ~85%).
- **C — small scoped SCSS.** Figure card chrome, sidebar, filter strip, print. One file, ancestor-scoped.
- **D — optional work needing new data or code.** New stored fields, custom chart runtimes, formula signature changes.

And the governance rule that goes with it: **a defect that source control shows was a deliberate, documented decision is a decision to re-open with its owner, not a bug to silently fix.** List those separately as gated, with the evidence that they were deliberate.

## Decision framework

Route the change to its owning layer before writing anything:

| You want to change | Owner | Mechanism |
|---|---|---|
| Cell text, fill, border, align, number format | **JSON (A/B)** | `cells`, `styles`, `formats`, `borders` |
| Sheet width, centring, dead scroll | **JSON (B)** | `colNumber`/`rowNumber` + `cols`/`rows` sizes |
| Spacing between cards | **JSON (B)** | empty gutter columns + figure `x`/`y` |
| KPI delta / baseline | **JSON (B)** | twin pivot + filter `offset: -1` + scorecard `baseline` |
| Chart type, data, background, legend | **JSON (B)** | figure `data` + `metaData`/`searchParams` |
| Card radius, shadow, outer background | **SCSS (C)** | `.o_spreadsheet_dashboard_action .o-figure[data-id^="…"]` |
| Page background *outside* the canvas | **SCSS (C)** | four-class selector; canvas still covers the sheet |
| Sidebar, filter strip, loading state, print | **SCSS (C)** | Tier-1 `o_*` classes, ancestor-scoped |
| Chart fonts, series palette, gridlines | **JS (D)** | `chartRegistry` wrapper — global, declare it |
| New figure type, sparkline, icon card | **JS (D)** | custom figure type; real cost, needs a named requirement |
| Cell font family, canvas theme, RTL sheet, dark sheet, responsive reflow | **nothing** | not achievable at reasonable cost — re-scope the design |

Ladder: exhaust JSON, then scoped SCSS, then a DOM hook via template inheritance, then a registry wrapper, and only then a prototype patch. The order is not taste — **each rung widens the blast radius and the upgrade exposure at the same time.** JSON changes one record and is migrated forward by the library itself; SCSS is contained by its ancestor selector; a registry wrapper is constructed for *every* spreadsheet opened in the session; and a prototype patch binds you to the internals of a generated build artifact that is versioned separately from Odoo and rewritten wholesale on upgrade.

## Design review checklist

Run this against any dashboard before calling it designed. Each line has caught a real shipped defect.

- [ ] **Figure count > 0**, and every metric that matters on a phone is a figure. Open it at 414px and confirm you do not get the empty-state sentence.
- [ ] **Section labels visible at 1280px and 1440px**, not only at 1920px. No `align: "right"` inside a full-width merge.
- [ ] **`colNumber`/`rowNumber` match the content.** Inline `max-width` equals the intended design width; no horizontal scrollbar at 1440px; `mx-auto` actually centres.
- [ ] **No literal constants dressed as measurements.** Every number traces to a pivot, list, or model method.
- [ ] **No two cards silently sharing one source** unless that duplication is intentional and labelled.
- [ ] **No domain keyed on a translatable name.** Status breakdowns group on a relation or a stored selection.
- [ ] **Every card is either period-filtered or says it is not.** Mixed period semantics in one grid without disclosure is a correctness bug.
- [ ] Buckets **partition** their total — no uncovered state, or an explicit "Other".
- [ ] Every headline KPI has a **baseline, delta, target or trend**.
- [ ] Colour is **semantic** (exception / breach / improvement), not one hue per status label.
- [ ] One reading order, one left edge — per-section centring gives every block a different start position, so the eye has to re-acquire the margin at each section instead of scanning down one edge.
- [ ] Counts formatted `#,##0`, never `#,##0.00` — two decimals on a count assert a precision the measure does not have and read as a currency. Rates `0.0%`; large numbers via `=FORMAT.LARGE.NUMBER()` on the Data sheet, since there is no humanise flag on the figure.
- [ ] Labels wrapped in `=_t("…")`. A hardcoded bilingual literal shows *both* languages to *every* user, and it is invisible to the `.pot` export, so no translator can ever fix it (`i18n-audit` owns the export and msgid workflow from that point on).
- [ ] A header caption states the reading rule ("records created in the selected period, in their current status") — without it two readers apply different denominators to the same grid and both believe they read it correctly.
- [ ] Drill-down present where it is free: `odoo://view/{…}` on titles, `chartOdooMenusReferences` on charts. The cell is already a click target; omitting the link leaves re-deriving the filter by hand as the only route from a number to its records.

## Validation checklist

- [ ] The module update that loads the workbook is verified **from the server log, not the exit code** — `stack-doctor` owns that check and why the exit code lies. A workbook JSON is loaded as a data record, so a malformed one fails at load time and nowhere else.
- [ ] Dashboard opens with **zero browser console errors**; no cell shows `#ERROR`, `#NAME?`, or a stuck `Loading...`.
- [ ] Visual pass at **1280px, 1440px, 1920px and 414px**. Mobile shows KPIs, not the empty-state sentence.
- [ ] Inline `max-width` on the centred grid element equals the design width.
- [ ] Move every global filter and confirm each card responds — or is labelled as exempt. A `fieldMatching` mismatch **silently unfilters** a pivot rather than erroring.
- [ ] Arabic session: labels resolve to one language; layout does not regress.
- [ ] **Scope-isolation regression check** — open at least one other spreadsheet dashboard and confirm it is visually unchanged.
- [ ] Test on a **clone**, never a reference database — iterating on a dashboard means repeated module updates, and each one rewrites the `spreadsheet.dashboard` record, discarding any revisions users made through the UI in the meantime. `stack-doctor` owns how to clone safely (with the filestore, on its own config).
- [ ] A malformed pivot yields `0`, not an error — spot-check every number against the underlying model before sign-off.

## Anti-patterns

| Pattern | Why it fails | Do instead |
|---|---|---|
| CSS to restyle cells or "the dashboard background" | The body is one canvas painting opaque white over everything; verified no-op | Set `fillColor`/`textColor` in the workbook JSON |
| A one-class `.o-figure` rule | Loses to the library's JS-injected sheets at equal specificity — they always land last | Out-specify with an ancestor chain; core uses four classes |
| `!important` inside `.o-spreadsheet` | Fights core's dark-mode `!important` and the injected sheets; unstable | Out-specify |
| Styling under `.o_spreadsheet_dashboard_action` alone | Matches every dashboard in the database — silent cross-dashboard restyle | Scope to `.o-figure[data-id^="<prefix>-"]` from your own authored ids |
| `padding` on `.o-figure-wrapper` | Content-box + inline sizing inflates the box (300x180 → 312x192) and breaks grid alignment | Use `.o-figure` (border-box), or the figure's stored `x`/`y` |
| `transform` / `overflow` / `position` on grid containers | Figures and clickable-cell overlays are counter-translated against the model's scroll offset; they desynchronise and drill-downs land on the wrong cell | Leave grid containers alone |
| A dashboard of styled cells imitating cards | Zero figures = one sentence on mobile; and card chrome is unstylable because `.o-figure` never exists | Scorecard figures for KPIs |
| Leaving `colNumber` at the default | Sheet width is the last column, not the last used one — permanent horizontal scroll, centring never engages | Set `colNumber`/`rowNumber` to the content |
| Relying on `mx-auto` to centre a wide sheet | Centring applies only when the sheet is narrower than the viewport | Design to a fixed width |
| `align: "right"` in a full-width merge to fake RTL | The library hard-forces `direction: ltr`; text renders off-screen at normal widths | Left-align; merge only across the used span |
| Absolute integers with no baseline | Unjudgeable; that is a report, not a dashboard | Twin pivot + `offset: -1` + `baselineMode: "percentage"` |
| `stage_id.name ilike '…'` buckets | One translation or rename zeroes the card; buckets never partition the total | Group by the relation or a stored selection field |
| A hardcoded `"0"` with a number format | Renders `0.00%`, indistinguishable from a measurement; invites a false decision | Remove it, or source it |
| Overriding chart colours in CSS | Series colours are painted into the figure's own canvas from a fixed runtime palette | `chartRegistry` wrapper — and declare that it is global |
| Silently fixing a documented deliberate decision | Reverts an accepted trade-off whose owner is elsewhere | List it as gated; re-open with the owner |
| Hand-writing the workbook JSON from scratch | Error-prone; a malformed pivot yields `0` rather than an error | Author in the editor UI, export `spreadsheet_data`, commit it as module data |

## Cross-references

Reference material owned by this skill:

- `skills/spreadsheet-dashboards/references/rendering-architecture.md` — the two systems in
  detail: what produces each visible pixel, the stable DOM tree and selector tiers, mobile and print
  DOM, the chart-styling hardcoded list, and the A-E extension ladder.
- `skills/spreadsheet-dashboards/references/authoring-recipes.md` — the workbook JSON
  skeleton, the observed design grid, the delta recipe, the section-header/drill-down idiom, the
  scoped SCSS card, and the chart-theme wrapper.

Owned elsewhere — reference, do not restate:

- `theme-scss` / `theme-design` — website theme SCSS variables and palettes. This skill governs backend dashboard chrome only; the two share no variable system.
- `frontend-js` — general Odoo asset-bundle and OWL conventions. Note the split this skill depends on: custom **JS** belongs in the lazy `spreadsheet.o_spreadsheet` bundle, custom **SCSS** in the eager `web.assets_backend`.
- `reviewer` — module-level review conventions, manifest hygiene, version bumps.
- `i18n` / `i18n-audit` — `.pot` extraction, msgid discipline and the translation workflow once labels are wrapped in `=_t()`. This skill only requires the wrapping; everything downstream of it is theirs.
- `stack-doctor` — module-update verification from the log, and cloning a database with its filestore onto its own config. The two validation-checklist lines above are pointers into that skill, not a second copy of it.
- A general data-visualisation skill, where one is available — chart-type selection, categorical palette construction and contrast/accessibility. This skill constrains those choices to what o-spreadsheet can express (rule 10: series colours come from a fixed runtime palette) but does not own them.
- The decision/issue owner — owns every gated item in the four-way separation. This skill flags them; it never resolves them.
