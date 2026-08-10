# Rendering architecture — where every visible pixel comes from

Reference for `spreadsheet-dashboards`. Line citations are from Odoo 17 with o-spreadsheet
17.0.71; treat exact line numbers as version-bound and the *mechanisms* as durable. Paths are
relative to the Odoo addons root. `o_spreadsheet.js` / `o_spreadsheet.xml` mean
`spreadsheet/static/src/o_spreadsheet/o_spreadsheet.{js,xml}` — **generated build artifacts of a
separately versioned library. Never edit them.**

## 1. The two disjoint styling systems

| System | Owns | Changed by |
|---|---|---|
| Odoo SCSS bundles (tokenised, dark-recompiled, RTL-flipped) | action root, sidebar, control panel, filter strip, share button, print | ordinary SCSS in `web.assets_backend` |
| Runtime-injected library CSS + canvas constants (raw hex, LTR-only, theme-blind) | everything inside `.o-spreadsheet` | out-specifying CSS (chrome only) or workbook JSON (content) |

The boundary selector core itself writes:
`.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet` (`dashboard_action.scss`).

**The one-line rule:** content and its colours live in the workbook JSON; only the chrome around it
lives in CSS.

## 2. Style origins — identify one before trying to change anything

| Origin | Reaches | Changed by |
|---|---|---|
| Canvas renderer (JS constants + workbook data) | cell text, fills, borders, gridlines, headers, scorecard text | workbook JSON, or a JS patch of the renderer |
| Chart.js runtime config (mostly hardcoded) | chart titles, axes, legends, tooltips, series colours | chart definition (small subset), `Chart.defaults`, or a re-registered chart runtime |
| Library CSS-in-JS (`<style>` tags injected at import) | figure boxes, overlays, scrollbars, popovers | out-specifying CSS from your module |
| Odoo SCSS bundles | chrome | SCSS in `web.assets_backend` |

Specific facts worth keeping:

- **Page background behind the dashboard** is a hardcoded literal `white` on the action root — not a
  token, so it stays white in dark mode.
- **The "paper" you actually see** is the canvas: `drawGlobalBackground` fills `#ffffff` across the
  whole sheet view (`o_spreadsheet.js:46829-46835`). Runtime verified opaque at every sample point.
- **Figure background** is an inline style on the figure canvas from the chart definition's
  `background` (default `#FFFFFF`) — set it in the definition, not in CSS.
- **Figure border** is hardcoded to 0 in dashboard mode (`getBorderWidth()` returns 0).
- **Figure radius and shadow do not exist** in the library CSS. That gap is the highest-value CSS win.
- **Cell text** is `style.textColor || "#000"`, single font family `DEFAULT_FONT = "'Roboto', arial"`
  — there is no per-cell `fontFamily` key. Sizes are points, rendered as `round(pt * 96/72)`, so the
  10pt default is 13px.
- **Cell fill** is painted only when non-white.
- **Gridlines and row/column headers** are forced off in dashboard mode regardless of the JSON flags.
- **Scorecard typography** is auto-computed from the box (0.65 key / 0.35 baseline, 2% padding). You
  size the box; you do not size the text.

Dashboard mode itself is a model config, not a CSS class: `new Model(…, { mode: "dashboard" })`.
It strips the top bar, sheet tabs, headers, gridlines, selection and figure borders.

## 3. Specificity — why load order cannot save you

The library appends ~59 `css` tagged templates to `<head>` at import time. Runtime verified on a live
page: **one** `<link>` (`web.assets_web.min.css`) at DOM position 0, followed by **63**
`<style component="__sheet__N">` tags. Your module's SCSS is compiled *into that link*.

Consequence: a custom rule at equal specificity **loses**. Core beats the library's
`.o-grid { background-color:#f5f5f5 }` (0,1,0) with a four-class selector (0,4,0). Runtime verified:
injecting a rule with that same four-class selector overrode core without `!important`; a one-class
`.o-grid` rule would not have.

Do not spray `!important` — you are then fighting core's dark-mode `!important` rules as well.

## 4. Stable DOM tree (runtime verified)

```
div.o_action.o_spreadsheet_dashboard_action                      <- STABLE anchor
├── ControlPanel
│   ├── div.o_filter_value_container × N                         <- STABLE (module-authored)
│   └── button.btn.btn-light > i.fa.fa-share-alt
└── div.o_content.o_component_with_search_panel[.o_mobile_dashboard]
    ├── div.o_spreadsheet_dashboard_search_panel                 <- STABLE (module-authored)
    ├── h3.dashboard-loading-status[.error]                      <- STABLE (module-authored)
    └── div.o_renderer                                           <- STABLE (module-authored)
        └── div.o-spreadsheet
            └── div.o-grid
                ├── div.mx-auto  [inline max-width]
                │   ├── div.o-grid-overlay
                │   │   └── div.o-figure-wrapper  [inline left/top/width/height/z-index]
                │   │        ├── div.o-figure[data-id="<figure id>"]
                │   │        │   └── div.o-chart-container > canvas.o-figure-canvas
                │   │        └── div.o-figure-border  [inline border: 0px]
                │   ├── canvas                                   <- THE grid raster
                │   └── div.o-dashboard-clickable-cell × N
                └── div.o-scrollbar.vertical / .horizontal / .corner
```

### Selector stability tiers

- **Tier 1 — safe.** Authored by the dashboard module, dashboard-only:
  `.o_spreadsheet_dashboard_action`, `.o_spreadsheet_dashboard_search_panel`, `.o_renderer`,
  `.o_filter_value_container`, `.dashboard-loading-status`, `.o_mobile_dashboard`.
- **Tier 2 — acceptable, always ancestor-scoped.** Load-bearing library classes:
  `.o-figure`, `.o-figure-wrapper`, `.o-figure-border`, `.o-chart-container`, `.o-figure-canvas`,
  `.o-grid`, `.o-spreadsheet`, `.o-scrollbar`.
- **Tier 3 — avoid.** Internal plumbing: `.o-figure-viewport-inverse`, `.o-figure-container`,
  `.o-grid-overlay`, `.o-two-columns`, anything matched by `[component^="__sheet__"]`, and the
  unclassed `div`s the mobile container emits.

**No `data-*` hooks exist on the chrome.** Figures carry `data-id="<figureId>"` on `.o-figure` — the
figure's `id` straight from your JSON. Runtime verified: figures authored with ids `kpi1`, `bar1`,
`gauge1` rendered as `div.o-figure[data-id="kpi1"|"bar1"|"gauge1"]`.

### Mobile DOM (runtime verified at ~420px)

```
div.o_content.o_component_with_search_panel.o_mobile_dashboard
├── div.o_search_panel.o_search_panel_summary.btn.w-100
└── div[style="min-height: 180px; direction: ltr;"]     <- UNCLASSED, one per figure
    └── div.o-chart-container.w-100.h-100 > canvas.o-figure-canvas
```

No `.o_renderer`, no grid canvas, **no cell content at all**. Figure order is by figure `y`; width is
`window.innerWidth`. The threshold is `env.isSmall` — viewport ≤ 767px. To style mobile cards, prefer
`.o_mobile_dashboard .o-chart-container` over selecting unclassed children.

## 5. Layout knobs and where they live

| Property | Lives in | Note |
|---|---|---|
| Figure `x`,`y`,`width`,`height` | stored JSON | absolute px from the A1 corner; **not cell-anchored** |
| Figure z-order | stored JSON order | insertion order preserved |
| Column widths | `cols["i"].size` | absent ⇒ 96px default |
| Row heights | `rows["i"].size`, else computed from the tallest cell, else 23px | **pin explicit sizes** or figure alignment drifts as content grows |
| Sheet width cap | computed = **sum of all column widths** → inline `max-width` | the last column, not the last used one |
| Horizontal centring | CSS `mx-auto` | engages only when the sheet is narrower than the viewport |
| Gridlines / headers / selection / figure border | hardcoded off in dashboard mode | JSON flags ignored |
| Scorecard font sizes | computed, auto-fit to the box | size the box, not the text |
| Scrollbar width | hardcoded 15px | |

**Scrolling.** The grid does not DOM-scroll. Scroll offset lives in the model, the canvas repaints,
and the `.o-scrollbar` divs are native-overflow proxies dispatching `SET_VIEWPORT_OFFSET`. Figures
track scroll by **counter-translation** inside clipped containers. Adding `overflow`, `transform` or
`position` to `.o-grid`, `.o-grid-overlay` or `.o-figure-container` desynchronises the DOM overlays
from the canvas — charts drift on scroll and drill-downs land on the wrong cell.

## 6. Component inventory and its ceilings

| Component | Rendered as | You control | You do not control |
|---|---|---|---|
| Scorecard (KPI) | own canvas, hand-drawn | `title`, `keyValue`, `baseline`, `baselineMode` (`percentage`/`difference`/`text`), `baselineDescr`, `baselineColorUp/Down`, `background` | fonts, sizes, padding, arrow shape; no icon, no sparkline, no unit suffix |
| Gauge | Chart.js custom controller | `dataRange`, `title`, `background`, `sectionRule` | half-circle geometry, needle, value pill |
| `odoo_bar` / `odoo_line` / `odoo_pie` | Chart.js on own canvas | `title`, `background`, `legendPosition`, `verticalAxisPosition`, `stacked`, `cumulative`, `metaData`, `searchParams.domain` | series colours, fonts, axis titles, gridlines; rasterised to PNG on share |
| Pivot / list table | **canvas cells** via `=ODOO.PIVOT(…)` / `=ODOO.LIST(…)` | full cell styling | not a widget: no sorting, no resizing, no sticky header; zebra striping is manual per-row styles |
| Text, titles, section labels | **canvas cells** | bold/italic/underline, `fontSize` (pt), `textColor`, `fillColor`, `align`, `verticalAlign`, `wrapping` | one font family; **invisible on mobile** |
| Separators | cell borders | `{style, color}` per side | shipped dashboards use only `thin #000` |
| Global filters | **DOM** in the control panel | container width/height via SCSS | control markup is web core; types are `text`, `date`, `relation` only |
| Drill-down link | canvas text + invisible `.o-dashboard-clickable-cell` | the `odoo://view/{…}` target | no hover highlight; the cursor change is the only affordance |
| Chart → menu navigation | whole figure clickable | `chartOdooMenusReferences` map | dashboard mode only |

**Not available at all:** combo charts, waterfall, radar, horizontal bar, secondary axis, trend lines,
per-dataset colours, sparklines in cells, icons, gradients, rounded canvas corners, a hero band,
responsive column reflow, dark theme inside the sheet.

## 7. Chart styling — the hardcoded list

Configurable from data: `title`, `background`, `legendPosition`, `verticalAxisPosition`, `stacked`,
`aggregated`, `cumulative`, `labelsAsText`, plus data bindings. Tick and tooltip number formats are
inherited from the **cell formats of the source ranges**.

Hardcoded, in decreasing order of how often it will bother you:

1. **Font family** never set — Chart.js default (`'Helvetica Neue', 'Helvetica', 'Arial', sans-serif`),
   so a stock dashboard mixes Roboto (cells, scorecards) with Helvetica (charts).
2. **Series colours** — fixed 20-colour palette cycled by dataset index.
3. **Title 22px, weight normal.**
4. Layout padding `{left:20, right:20, top: title?10:25, bottom:10}`.
5. Gridlines — no config anywhere; pure Chart.js defaults.
6. Tooltip visual style — only the label callback is overridden.
7. Number humanisation — hard threshold `abs(v) >= 1000`.
8. `beginAtZero: true` on the y axis.
9. Animation disabled; legend toggle disabled; line tension 0.
10. Label truncation at 20 characters.
11. Odoo-chart x-tick rotation locked to 15-60°.
12. Text colour auto-flips white/black at background luminance 0.3 — a mid-tone card background
    leaves you no control over text contrast.

Three override surfaces: `Chart.defaults` (global, one line), a `chartRegistry` re-registration
wrapping `getChartRuntime` (per chart type, still global to every spreadsheet), and CSS (figure
**box** only).

## 8. Extension ladder

| | Technique | Reaches | Risk | Use when |
|---|---|---|---|---|
| **A** | Native data/config — workbook JSON + `spreadsheet.dashboard(.group)` records | all cell styling, layout, figures, chart definitions, filters, links | none; migrations are built in | **Default. Exhaust first.** |
| **B** | SCSS in `web.assets_backend`, scoped `.o_spreadsheet_dashboard_action` | page background, sidebar, control panel, filters, figure card chrome, loading states, print | low | the primary tool for chrome |
| **C** | OWL `t-inherit` in `spreadsheet.o_spreadsheet` | restructure chrome DOM, add a CSS hook | moderate | when B needs a hook that does not exist |
| **D** | Public registries via `@odoo/o-spreadsheet` | chart palettes and runtimes, new chart/figure types, clickable-cell behaviour, formulas, plugins | moderate | new visual capability |
| **E** | `patch()` prototypes | anything | high | last resort; patch only exported components, keep it tiny, pin with a test |

Mechanics that are easy to get wrong:

- **Custom JS goes in `spreadsheet.o_spreadsheet`; custom SCSS goes in `web.assets_backend`.**
  `@odoo/o-spreadsheet` does not exist until the lazy bundle runs, so importing it from
  `web.assets_backend` fails. SCSS is eager, JS is lazy — that split also avoids a flash of unstyled
  dashboard.
- **Registrations must run before any `Model` is constructed** — the constructor snapshots the plugin
  registries.
- **`Registry.add` silently overwrites** (unlike `@web/core/registry`, no `{force:true}` needed).
- **Registrations are global.** A plugin or formula registered for one dashboard is constructed when
  *any* dashboard opens, on the shared library singleton. Guard with `getters.isDashboard()` or a
  dashboard check if that matters.
- **CSS does not reach the shared/public dashboard** — `/dashboard/share/<id>/<token>` renders in a
  different DOM tree (`.o-public-spreadsheet`) from a different bundle, with live formulas frozen to
  literals and `odoo_*` charts rasterised to PNG.
- **There is no sheet switcher in dashboard mode.** Only the first sheet is ever displayed; the
  convention is a `Dashboard` sheet for presentation and a `Data` sheet for staging formulas.
- **Filters work in readonly mode** only because `SET_GLOBAL_FILTER_VALUE` and friends are explicitly
  whitelisted. A `fieldMatching` entry that does not match **silently unfilters** the object.
- **The user's locale and company currency are injected server-side** by `get_readonly_dashboard()`.
  Your authored `settings.locale` block is a placeholder, not a contract.
