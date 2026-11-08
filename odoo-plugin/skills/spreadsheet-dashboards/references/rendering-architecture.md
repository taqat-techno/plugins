# Rendering architecture — where every visible pixel comes from

Reference for `spreadsheet-dashboards`. Facts are tagged by where they were established:

- **[17 runtime]** — observed in a live Odoo 17 browser (o-spreadsheet 17.0.71, Chart.js 4.3.0).
- **[17 src]** — read from Odoo 17 source.
- **[19 src]** — read from Odoo 19.0 community source (o-spreadsheet 19.0.4). Not runtime-tested.
- No tag — confirmed in both 17 and 19 source.

Odoo 18 was not checked; treat it as "between" and verify. Line numbers are version-bound; the
*mechanisms* are what to rely on. `o_spreadsheet.js` / `o_spreadsheet.xml` mean
`spreadsheet/static/src/o_spreadsheet/o_spreadsheet.{js,xml}` — **generated build artifacts of the
separately versioned `odoo/o-spreadsheet` library. Never edit them**, and treat their internals as
version-bound. The full 17-vs-19 table is `version-differences.md`.

## 1. Architecture map

```
ir.ui.menu "Dashboards"
 └─ ir.actions.client  tag="action_spreadsheet_dashboard"
     └─ [EAGER, web.assets_backend] loader stub
         ├─ loads Chart.js (web.chartjs_lib)
         └─ loads spreadsheet.o_spreadsheet   [LAZY: all JS + OWL XML, never SCSS]
              └─ re-registers the real client action, stub re-dispatches the tag

DashboardAction (OWL, spreadsheet_dashboard)
 ├─ ControlPanel ── global filter values (.o_filter_value_container) + share button
 │                  19: also a dashboard search bar with facets and a favourite star
 ├─ desktop: .o_spreadsheet_dashboard_search_panel (dashboard picker sidebar)
 │           19: collapsible (Expanded / Collapsed templates + toggle button)
 │  mobile : DashboardMobileSearchPanel
 ├─ loader  17: dashboard_loader.js   19: dashboard_loader_service.js
 │    └─ ORM: spreadsheet.dashboard → readonly snapshot (+ user locale, company currency)
 │    └─ new Model(migrate(snapshot), {…, mode: "dashboard"})
 └─ 17 desktop: <Spreadsheet/> ; 17 mobile: <MobileFigureContainer/>  (figures only)
    19 both   : <SpreadsheetComponent/> inside div.o_renderer
        └─ env.isDashboard() ⇒ SpreadsheetDashboard
             ├─ ONE <canvas>  ← cells, text, fills, borders (raster)
             ├─ figures → charts / scorecards (DOM boxes, own canvases)
             ├─ .o-dashboard-clickable-cell overlays (drill-down hit areas)
             ├─ GridPopover, filter icons
             └─ .o-scrollbar vertical / horizontal / corner (DOM proxies)
```

**Two disjoint styling systems meet on this page.**

| System | Owns | Changed by |
|---|---|---|
| Odoo SCSS bundles (tokenised, dark-recompiled, RTL-flipped) | action root, sidebar, control panel, filter strip, share button, print | ordinary SCSS in `web.assets_backend` |
| Runtime-injected library CSS + canvas constants (raw hex, LTR-only, theme-blind) | everything inside `.o-spreadsheet` | out-specifying CSS (chrome only) or workbook JSON (content) |

The boundary selector core itself writes: `.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet`
(`dashboard_action.scss`, same in 17 and 19).

**The one-line rule:** content and its colours live in the workbook JSON; only the chrome around it
lives in CSS. Roughly 80% of a dashboard redesign is JSON authoring.

## 2. Asset bundles — which bundle holds what

| Bundle | Loading | Contents |
|---|---|---|
| `web.assets_backend` | eager | loader stubs + **all SCSS** of `spreadsheet` and `spreadsheet_dashboard` |
| `spreadsheet.o_spreadsheet` | lazy, first dashboard open | the library + **all module JS and OWL XML** — never SCSS |
| `web.chartjs_lib` (`spreadsheet.dependencies`) | lazy | Chart.js + luxon adapter |
| `spreadsheet.assets_print` | lazy, on print | print-only SCSS (`spreadsheet_dashboard/static/src/print_assets/**`) |
| `web.assets_web_dark` | eager when the `color_scheme` cookie is `dark` | `**/*.dark.scss` |
| `spreadsheet.public_spreadsheet` | separate page | standalone bundle for the shared `/dashboard/share/<id>/<token>` page |

**SCSS is eager, JS is lazy.** Custom SCSS belongs in `web.assets_backend` (no flash of unstyled
dashboard); custom JS belongs in `spreadsheet.o_spreadsheet`, because `@odoo/o-spreadsheet` does
not exist until that bundle runs. Print-only SCSS goes in `spreadsheet.assets_print`.

## 3. Rendering lifecycle

1. The menu dispatches `action_spreadsheet_dashboard`; the eager registry entry is only a stub.
2. The stub loads Chart.js, then the lazy `spreadsheet.o_spreadsheet` bundle. If the bundle crashes, a
   poison action replaces it so the client cannot loop.
3. Bundle evaluation force-replaces the stub with the real action; the stub re-dispatches the tag.
4. **Library CSS lands now** — the library's `css` tagged templates execute at import and append
   `<style>` tags to `<head>`. [17 runtime]: one `<link>` at DOM position 0, then 63
   `<style component="__sheet__N">` tags.
5. One `webSearchRead` on `spreadsheet.dashboard.group` builds the whole sidebar. A record rule on
   `group_ids` filters dashboards by the user's groups server-side.
6. Active dashboard: restored breadcrumb state → `action.params.dashboard_id` → first dashboard of
   the first non-empty group.
7. The fetch is lazy: the template paints `Loading...` first (`h3.dashboard-loading-status`), or
   `An error occured while loading the dashboard` (`.dashboard-loading-status.error`).
8. The server returns the snapshot with **the user's locale injected** and the company currency
   (19 also returns a `translation_namespace`). Your authored `settings.locale` is a placeholder.
9. The client migrates the snapshot (built-in migrations, so older workbook JSON still loads) and
   builds `new Model(…, {mode: "dashboard"})`, activating the **first sheet**.
10. The grid canvas is drawn by the layered renderer.
11. Odoo data sources (`ODOO.PIVOT`, `ODOO.LIST`, `odoo_*` charts) resolve asynchronously. Until then
    cells hold a **silent** loading error displayed as `Loading...`; each arrival re-evaluates.
12. A global filter change dispatches `SET_GLOBAL_FILTER_VALUE` → per-object domain → reload. This
    works in readonly mode only because those commands are explicitly whitelisted.

**Dashboard mode is a model config, not a CSS class.** It strips the top bar, sheet tabs, row and
column headers, gridlines, selection and figure borders. There is **no sheet switcher**: only the
first sheet is ever displayed. Convention: a `Dashboard` sheet for presentation, a `Data` sheet for
staging formulas.

**Sharing.** The Share button freezes live formulas to literals, rasterises `odoo_*` charts to PNG,
stores a frozen `spreadsheet.dashboard.share` copy and serves it at `/dashboard/share/<id>/<token>`
through a **different bundle and DOM tree** (`.o-public-spreadsheet`). Backend-scoped CSS and JS
chart themes do not reach the shared page.

**Print.** Print hides the sidebar and control panel, sets `height: auto`, temporarily forces the
model to dashboard mode and resizes it to the full sheet. Print SCSS ships in
`spreadsheet.assets_print`.

## 4. Key files

| File (addons-relative) | Responsibility |
|---|---|
| `spreadsheet_dashboard/models/spreadsheet_dashboard.py` | the model: `name`, `dashboard_group_id`, `sequence`, `group_ids`; the readonly-snapshot entry point |
| `spreadsheet/models/spreadsheet_mixin.py` | storage: `spreadsheet_binary_data` (attachment) + computed `spreadsheet_data` text |
| `spreadsheet_dashboard/models/spreadsheet_dashboard_group.py` | sidebar sections; module-data groups are delete-protected |
| `spreadsheet_dashboard/models/spreadsheet_dashboard_share.py` | frozen public copy + access token |
| `spreadsheet_dashboard/static/src/bundle/dashboard_action/dashboard_action.{js,xml}` | the client action and **the only DOM this module authors** — every stable dashboard-only class comes from here |
| `spreadsheet_dashboard/static/src/bundle/dashboard_action/dashboard_action.scss` | the entire dashboard skin (~100 lines in 17, ~150 in 19) — read it in full before overriding anything |
| 17: `…/dashboard_loader.js`; 19: `…/dashboard_loader_service.js` | fetch, cache, build the model in dashboard mode |
| 17 only: `…/mobile_figure_container/*` | the figures-only mobile reflow |
| `spreadsheet/static/src/o_spreadsheet/odoo_module.js` | republishes `window.o_spreadsheet` as `@odoo/o-spreadsheet` — **the single shared library instance, i.e. the whole extension mechanism** |
| `spreadsheet/static/src/chart/odoo_chart/*.js` | the Odoo chart types (3 in 17, 13 in 19) |
| `spreadsheet/static/src/chart/odoo_menu/figure_component.{js,xml}` | `t-inherit` precedent against a library template |

## 5. Style origins — identify one before trying to change anything

| Origin | Reaches | Changed by |
|---|---|---|
| Canvas renderer (JS constants + workbook data) | cell text, fills, borders, gridlines, headers, scorecard text | workbook JSON, or a JS patch of the renderer |
| Chart.js runtime config (mostly hardcoded) | chart titles, axes, legends, tooltips, series colours | chart definition (17: small subset; 19: much larger), `Chart.defaults`, or a re-registered runtime |
| Library CSS-in-JS (`<style>` tags injected at import) | figure boxes, overlays, scrollbars, popovers | out-specifying CSS from your module |
| Odoo SCSS bundles | chrome | SCSS in `web.assets_backend` |

### Where each visible element's style comes from

| Element | Final source |
|---|---|
| Page background behind the dashboard | hardcoded `background-color: white` on `.o_spreadsheet_dashboard_action` — **a literal, not a token**, so it stays white in dark mode |
| Empty space around the centred sheet | `.o-grid { background-color: white }` (four-class selector) overriding the library's `#f5f5f5` — visible only **outside** the canvas |
| The dashboard "paper" | **canvas**: `drawGlobalBackground` fills `#ffffff` over the whole sheet view. [17 runtime] forcing `.o-grid` to another colour and pixel-probing the canvas returned `rgba(255,255,255,255)` everywhere |
| Sheet width and centring | **data**: inline `max-width` = sum of column widths, plus `mx-auto` |
| Sidebar container | `width: fit-content; max-width: 200px`, `bg-view`, `border-end`. [17 runtime] 200px, `padding-left: 30px` |
| Sidebar item / hover / active | padding `4px 8px 4px 12px`; hover `$o-gray-100`; active = Bootstrap `list-group-item.active`. 19 adds an `.o_edit_dashboard` button revealed on hover and `.o_dashboard_star` favourites |
| Chart / KPI card background | **canvas**: inline `background-color` on the figure canvas from the chart definition's `background` (default `#FFFFFF`). Overriding it in CSS needs `!important` and Chart.js still paints over it — set `background` in the definition |
| Chart / KPI card border | none in dashboard mode (`getBorderWidth()` returns 0). [17 runtime] inline `border: 0px solid #c9ccd2` |
| Chart / KPI card radius and shadow | **do not exist** in the library CSS — the highest-value CSS win |
| Chart title | **canvas**. 17: 22px, weight normal, colour auto-flipped by background luminance. 19: `title` object `{text, color, fontSize, bold, italic, align}`, default 16px |
| Chart series colours | **canvas**. 17: fixed palette by dataset index, not storable. 19: bar/line/combo store `dataSets[i].backgroundColor`; pie still not storable |
| Scorecard number | **canvas**, auto-scaled on `'Roboto', arial`; colour = key cell's `textColor`, else derived |
| Cell text | **canvas**: `style.textColor || "#000"`, default 10pt |
| Cell fill | **canvas**: `style.fillColor`, painted only when non-white |
| Gridlines, row/column headers | **forced off** in dashboard mode regardless of JSON flags |
| Global filter controls | `.o_filter_value_container` 235px wide, `max-height: 150px`; `.o-filter-value` min-height 25px (19 adds `min-width: 100px`, `.o-filter-value-double-size` 200px basis) |
| Control-panel filter strip | 19: `.o_control_panel_actions` `max-height: 200px`, wraps, `gap` spacer 2 |
| Share button | Bootstrap `btn btn-light`; pane 320×100 |
| Loading / error state | `h3.dashboard-loading-status` centred by `margin: auto`; `.error` variant |
| Sample dashboard (19) | `div.o_renderer.o-sample-dashboard` when the dashboard is a sample |

### Typography

- **Canvas text has exactly one font family:** `DEFAULT_FONT = "'Roboto', arial"` (17 and 19). There
  is no per-cell `fontFamily`. Cell sizes are **points**, rendered `round(pt × 96/72)` — 10pt = 13px.
- **Chart.js text uses the Chart.js default family** — no Odoo code sets `Chart.defaults.font`.
  [17 runtime] `'Helvetica Neue', 'Helvetica', 'Arial', sans-serif`, size 12, colour `#666`. A stock
  dashboard therefore mixes Roboto (cells, scorecards) with Helvetica (charts).
- **Chrome text is normal Odoo typography** ([17 runtime] sidebar 14px, system font stack).

### Dark mode

`*.dark.scss` files are collected into `web.assets_web_dark`, selected by the `color_scheme` cookie.
The chrome re-themes because it uses tokens. The body does not, for three independent reasons: the
action background is a literal `white`; the library's injected CSS is raw hex the SCSS pipeline never
sees; the canvas paints its own `#ffffff`. Odoo then *deliberately* forces the rest back to light
with `!important` in `o_spreadsheet_extended.dark.scss` ("until we have the proper scss tool
chain"). **Treat dark dashboards as unsupported** in 17 and 19.

### RTL

- Odoo compiles a separate RTL bundle through `rtlcss`; **all chrome SCSS flips correctly** (logical
  properties like `padding-inline-start` are already used).
- **The sheet never flips.** The library forces `direction: ltr` on itself and every descendant
  ("rtl not supported ATM" — still present in 19). The 17 mobile figure list repeats it inline.
- Net effect in an Arabic session: mirrored chrome around an LTR sheet. Arabic strings shape
  correctly on canvas; column order, default alignment and figure coordinates stay LTR.
- What you *can* do in the data: mirror the column order in the JSON and right-align text **within
  individual cells or within merges that span only the used columns**. What you must not do:
  right-align inside a **full-width** merge — the text renders at the far edge of the merge and falls
  off-screen at normal widths (verified on a shipped dashboard: blank coloured strips below ~1920px).

## 6. Specificity — why load order cannot save you

The library appends its CSS to `<head>` at import time, **after** the single stylesheet `<link>` that
holds your module's compiled SCSS. Consequence: a custom rule at equal specificity **loses**. Core
beats the library's `.o-grid { background-color:#f5f5f5 }` (0,1,0) with a four-class selector
(0,4,0):

```scss
.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet .o-grid { background-color: white; }
```

[17 runtime] injecting a rule with that same selector overrode core without `!important`; a
one-class `.o-grid` rule would not have. Do not spray `!important` — you then fight core's dark-mode
`!important` rules as well.

## 7. Stable DOM tree

```
div.o_action.o_spreadsheet_dashboard_action.o_field_highlight       <- STABLE anchor
├── ControlPanel
│   ├── div.o_filter_value_container × N                            <- STABLE (module-authored)
│   │   └── div.o-filter-value.d-flex.align-items-start.w-100
│   └── button.btn.btn-light > i.fa.fa-share-alt                    (share)
└── div.o_content.o_component_with_search_panel[.o_mobile_dashboard]
    ├── div.o_spreadsheet_dashboard_search_panel                    <- STABLE (module-authored)
    │   └── section.o_search_panel_section > ul > li.o_search_panel_category_value[.active]
    ├── h3.dashboard-loading-status[.error]                         <- STABLE (module-authored)
    └── div.o_renderer[.o-sample-dashboard]                         <- STABLE (module-authored)
        └── div.o-spreadsheet
            └── div.o-grid.o-two-columns
                ├── div.mx-auto.h-100.position-relative  [inline max-width]
                │   ├── div.o-grid-overlay
                │   │   └── div.o-figure-wrapper  [inline left/top/width/height/z-index]
                │   │        ├── div.o-figure.w-100.h-100[data-id="<figure id>"]
                │   │        │   └── div.o-chart-container > canvas.o-figure-canvas
                │   │        └── div.o-figure-border  [inline border: 0px]
                │   ├── canvas                                      <- THE grid raster
                │   ├── div.o-dashboard-clickable-cell × N
                │   └── (filter icons overlay, GridPopover)
                └── div.o-scrollbar.vertical / .horizontal / .corner
```

`data-id` on `.o-figure` is the figure's `id` from the JSON: [17 runtime] ids `kpi1`, `bar1`, `gauge1`
rendered as `div.o-figure[data-id="kpi1"|…]`; [19 src] `t-att-data-id="props.figureUI.id"`.

### Selector stability tiers

- **Tier 1 — safe.** Authored by the dashboard module, dashboard-only:
  `.o_spreadsheet_dashboard_action`, `.o_spreadsheet_dashboard_search_panel`, `.o_renderer`,
  `.o_filter_value_container`, `.dashboard-loading-status`, `.o_mobile_dashboard`.
- **Tier 2 — acceptable, always ancestor-scoped.** Load-bearing library classes:
  `.o-figure`, `.o-figure-wrapper`, `.o-figure-border`, `.o-chart-container`, `.o-figure-canvas`,
  `.o-grid`, `.o-spreadsheet`, `.o-scrollbar`.
- **Tier 3 — avoid.** Internal plumbing: `.o-figure-viewport-inverse`, `.o-figure-container`,
  `.o-grid-overlay`, `.o-grid-cell-icon`, `.o-two-columns`, anything matched by
  `[component^="__sheet__"]`, and unclassed `div`s.

**No `data-*` hooks exist on the chrome**; the figure `data-id` is the only per-element handle.

### Mobile — the version split that changes the architecture

**17 [17 runtime at ~420px]:** below 768px (`env.isSmall`, viewport ≤ 767px) the action renders
`MobileFigureContainer` instead of the grid:

```
div.o_content.o_component_with_search_panel.o_mobile_dashboard
├── div.o_search_panel.o_search_panel_summary.btn.w-100
└── div[style="min-height: 180px; direction: ltr;"]     <- UNCLASSED, one per figure
    └── div.o-chart-container.w-100.h-100 > canvas.o-figure-canvas
```

No grid canvas, **no cell content at all**; figures stack full-width ordered by `y`. A dashboard with
no figures shows only *"Only chart figures are displayed in small screens but this dashboard doesn't
contain any."* Style mobile cards through `.o_mobile_dashboard .o-chart-container`, not the
unclassed parents.

**19 [19 src]:** there is no `MobileFigureContainer`. The action always renders
`SpreadsheetComponent` inside `.o_renderer`, adding `.o_mobile_dashboard` on small screens and
swapping the sidebar for `DashboardMobileSearchPanel`. **Cells are drawn on mobile**, but the sheet
does not reflow or zoom: a 1000px design is a horizontally scrolled 1000px canvas on a phone. Verify
the real result on a device before relying on either outcome.

Design consequence, both versions: put every metric a phone user needs in a **figure near the left
edge, ordered top-down** — on 17 it is the only thing shown, on 19 it is what is visible without
sideways scrolling.

## 8. Layout knobs and where they live

| Property | Lives in | Note |
|---|---|---|
| Figure position | stored JSON. 17: `x`,`y`. 19: `{col, row, offset: {x, y}}` (migration `18.3.1` writes `col: 0, row: 0`) | absolute px from the A1 corner; not cell-anchored in practice |
| Figure size | stored JSON `width`, `height` | |
| Figure z-order | stored JSON order | insertion order preserved |
| Figure DOM position | computed → inline `left/top/width/height` | [17 runtime] `left:24px; top:260px; width:300px; height:180px; z-index:10` |
| Column widths | `cols["i"].size` | absent ⇒ 96px |
| Row heights | `rows["i"].size`, else computed from the tallest cell, else 23px | **pin explicit sizes** or figure alignment drifts as content grows |
| Sheet width cap | computed = **sum of all column widths** → inline `max-width` | [17 runtime] `max-width: 2424px` on a default 26-column sheet |
| Horizontal centring | CSS `mx-auto` | engages only when the sheet is narrower than the viewport ([17 runtime] 2424px sheet in an 836px area ⇒ scrollbar, no centring) |
| Gridlines / headers / selection / figure border | hardcoded off in dashboard mode | JSON flags ignored |
| Zoom | none on desktop: 1 CSS px per grid px | |
| Scorecard font sizes | computed, auto-fit to the box | size the box, not the text (19 lets you set title font size) |
| Scrollbar width | hardcoded 15px | |

**Scrolling.** The grid does not DOM-scroll. Scroll offset lives in the model, the canvas repaints,
and the `.o-scrollbar` divs are native-overflow proxies dispatching `SET_VIEWPORT_OFFSET`. Figures
track scroll by **counter-translation** inside clipped containers. Adding `overflow`, `transform` or
`position` to `.o-grid`, `.o-grid-overlay` or `.o-figure-container` desynchronises the DOM overlays
from the canvas — charts drift on scroll and drill-downs land on the wrong cell.

## 9. Component inventory and its ceilings

| Component | Rendered as | You control | You do not control |
|---|---|---|---|
| Scorecard (KPI) | own canvas, hand-drawn | `title`, `keyValue`, `baseline`, `baselineMode` (17: `percentage`/`difference`/`text`; 19 adds `progress`), `baselineDescr`, `baselineColorUp/Down`, `background`; key/baseline inherit the source cell's `textColor`/bold/italic. 19 adds `keyDescr`, `humanize`, title object | fonts, box ratios (0.65 key / 0.35 baseline), 2% padding, `#525252` secondary grey, arrow shape; no icon, no sparkline, no unit suffix; no colour in `text`/`progress` mode |
| Gauge | Chart.js custom controller | `dataRange`, `title`, `background`, `sectionRule` (3 colours, min/max, 2 inflection points as number or %) | half-circle geometry, needle, 30px white-on-black value pill |
| Odoo charts (`odoo_bar`/`odoo_line`/`odoo_pie`; 19 adds combo, waterfall, funnel, pyramid, radar, scatter, geo, sunburst, treemap) | Chart.js on own canvas | `title`, `background`, `legendPosition`, `verticalAxisPosition`, `stacked`, `cumulative`, `metaData` (model/measure/groupBy), `searchParams.domain`. 19 adds `dataSets[i].{backgroundColor,label,trend,yAxisId}`, `showValues`, `humanize`, `axesDesign`, `horizontal`, `isDoughnut`, `pieHolePercentage` | 17: series colours, fonts, axis titles, gridlines. 19: pie slice colours, fonts, gridlines. Not XLSX-exportable; rasterised on share |
| Plain charts (cell ranges) | Chart.js | as above plus `dataSets`, `labelRange`, `dataSetsHaveTitle`, `aggregated`, `labelsAsText` | same limits |
| Pivot table | **canvas cells** via `=ODOO.PIVOT(…)` / `=ODOO.PIVOT.HEADER(…)` | full cell styling: fill, text colour, bold, size, align, borders, format | not a widget: no sorting, resizing or sticky header; zebra striping is manual per-row styles |
| List table | **canvas cells** via `=ODOO.LIST(id, row, "field")` | same as pivot | row count fixed at authoring time |
| Text, titles, section labels | **canvas cells** | `bold`, `italic`, `underline`, `strikethrough`, `fontSize` (pt), `textColor`, `fillColor`, `align`, `verticalAlign`, `wrapping` | one font family; invisible on 17 mobile |
| Separators | cell borders | per side `{style: thin\|medium\|thick\|dashed\|dotted, color}` | shipped dashboards use only `thin #000` |
| Global filters | **DOM** in the control panel | container width/height via SCSS | control markup is web core; types `text`, `date`, `relation` (census across shipped 17 dashboards: relation ×102, date ×25, text ×1) |
| Drill-down link | canvas text + invisible `.o-dashboard-clickable-cell` | the `odoo://view/{…}` target | no hover highlight; the cursor change is the only affordance |
| Chart → menu navigation | whole figure clickable, `role="button"` | `chartOdooMenusReferences` map | dashboard mode only |
| Conditional formatting | canvas | colour scales, cell-is rules, icon sets, data bars (19 adds `customFormula` operator) | used by **zero** shipped 17 dashboards; verify rendering in dashboard mode on your version |
| Images | DOM `<img>` figure (`tag: "image"`) | — | no shipped dashboard uses one; only the share-freeze path creates them |

**Not available in 17:** combo, waterfall, radar, horizontal bar, secondary axis, trend lines,
per-dataset colours, sparklines in cells. **19 adds** combo, waterfall, funnel, pyramid, radar,
scatter, geo, sunburst, treemap, horizontal bars, trend lines, per-series colours (not pie).
**Neither** has: icons in cells or scorecards, gradients, rounded canvas corners, a hero band,
responsive column reflow, or a dark theme inside the sheet.

### Executive-pattern capability

| Pattern | Native? | How |
|---|---|---|
| Big-number KPI | yes | scorecard; value auto-scales to the box |
| Label under the number | yes | `baselineDescr` (19 also `keyDescr`) |
| Delta vs prior period | yes | twin pivots + date filter `offset: -1` + `baselineMode: "percentage"` |
| Up / down state | yes | automatic arrow + `baselineColorUp/Down` |
| Compact numbers (1.2M) | yes | 17: `=FORMAT.LARGE.NUMBER()` on the Data sheet; 19: scorecard `humanize` (default on) |
| Currency / percent | yes | `formats`, e.g. `[$$]#,##0`, `0.0%` |
| Section headings | yes | 40px row + 16pt bold cell, usually a drill-down link |
| Visually separated areas | partly | gutter columns and cell fills; **no card container exists in the data model** |
| Coloured status cells | yes | `fillColor` per cell, or conditional formats |
| Grouped metric tables | yes | pivot / list formulas + manual zebra striping |
| Gauge / progress | yes | gauge figure; 19 also scorecard `progress` mode |
| Icons | no | |
| Rounded cards with shadow | CSS only | `authoring-recipes.md` §7 |
| Sparkline in a KPI | no | custom figure type (ladder rung D) |
| Hero band | partly | tall row + merged/filled cells; no gradient, no image |

## 10. Chart styling — the hardcoded list (17)

Configurable from data in 17: `title`, `background`, `legendPosition`, `verticalAxisPosition`,
`stacked`, `aggregated`, `cumulative`, `labelsAsText`, plus data bindings. Tick and tooltip number
formats are inherited from the **cell formats of the source ranges**.

Hardcoded in 17, in decreasing order of how often it will bother you (19 status in brackets):

1. **Font family** never set — Chart.js default. [19: unchanged]
2. **Series colours** — fixed palette cycled by dataset index. [19: storable for bar/line/combo, not pie]
3. **Title 22px, weight normal.** [19: title object, default 16px, colour/bold/align settable]
4. Layout padding `{left:20, right:20, top: title?10:25, bottom:10}`.
5. Gridlines — no config anywhere; pure Chart.js defaults.
6. Tooltip visual style — only the label callback is overridden.
7. Number humanisation — hard threshold `abs(v) >= 1000`. [19: `humanize` flag]
8. `beginAtZero: true` on the y axis.
9. Animation disabled; legend toggle disabled; line tension 0.
10. Label truncation at 20 characters.
11. Odoo-chart x-tick rotation locked to 15-60°.
12. Stacked-area fill alpha 0.4.
13. Text colour auto-flips white/black at background luminance 0.3 — a mid-tone card background
    leaves you no control over text contrast. [19: same rule, muted `#666666` / `#C8C8C8`]
14. Scorecard typography, box ratios and `#525252` secondary grey.
15. Gauge geometry, needle and value pill.

Three override surfaces:

- **Global, one line:** `window.Chart.defaults.font.family` (and `.size`, `.color`) after Chart.js
  loads. Affects every Chart.js chart in the session, including graph views.
- **Per chart type:** re-register a type in `chartRegistry`, wrapping `getChartRuntime` and mutating
  the returned `chartJsConfig`. Still global to every spreadsheet.
- **CSS:** the figure **box** only (radius, shadow, outer background).

## 11. Extension ladder

| | Technique | Reaches | Risk | Upgrade impact | Use when |
|---|---|---|---|---|---|
| **A** | Native data/config — workbook JSON + `spreadsheet.dashboard(.group)` records | all cell styling, layout, figures, chart definitions, filters, links | none | lowest — migrations are built in | **Default. Exhaust first.** |
| **B** | SCSS in `web.assets_backend`, scoped `.o_spreadsheet_dashboard_action` | page background, sidebar, control panel, filters, figure card chrome, overlays, loading states; print via `spreadsheet.assets_print` | low | low–moderate (`o_*` classes stable, `o-*` are build artifacts) | the primary tool for chrome |
| **C** | OWL `t-inherit` in `spreadsheet.o_spreadsheet` | restructure chrome DOM, add a CSS hook | moderate | moderate (Odoo templates) / higher (library templates) | when B needs a hook that does not exist; precedent: `spreadsheet/static/src/chart/odoo_menu/figure_component.xml` |
| **D** | Public registries via `@odoo/o-spreadsheet` | chart palettes and runtimes, new chart/figure types, clickable-cell behaviour, formulas, plugins | moderate | moderate — the export list is the de-facto API, re-bundled each Odoo version with no semver promise | new visual capability |
| **E** | `patch()` prototypes | anything | high | highest | last resort; patch only **exported** components, keep it tiny, pin with a test |

Mechanics that are easy to get wrong:

- **Custom JS goes in `spreadsheet.o_spreadsheet`; custom SCSS goes in `web.assets_backend`**
  (print SCSS in `spreadsheet.assets_print`).
- **Ordered insertion** when your JS must run right after the library:
  `("after", "spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js", "your_module/static/src/**/*.js")`
  in the manifest's `spreadsheet.o_spreadsheet` list.
- **Registrations must run before any `Model` is constructed** — the constructor snapshots the plugin
  registries.
- **`Registry.add` silently overwrites** (unlike `@web/core/registry`, no `{force:true}` needed).
- **Registrations are global.** A plugin, formula or chart runtime registered for one dashboard is
  constructed when *any* spreadsheet opens, on the shared library singleton. Guard with
  `getters.isDashboard()` where that matters.
- **Filters work in readonly mode** only because their commands are whitelisted. A `fieldMatching`
  entry that does not match **silently unfilters** the object.
- **The user's locale and company currency are injected server-side.**
