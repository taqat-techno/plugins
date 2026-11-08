# Authoring recipes — workbook JSON, geometry, deltas, scoped chrome

Reference for `spreadsheet-dashboards`. Sections 1-6 are workbook JSON (ladder rung A); 7 is SCSS
(B); 8 is JS (D); 9 applies a brand palette across all three; 10 is the module architecture. Schema
shown is the shipped Odoo 17 dashboard idiom (`version: 12`, `odooVersion: 4`); the library's own
`CURRENT_VERSION` runs ahead (14.5 in 17) and migrations run client-side on load, so authoring at the
shipped version is safe — and a 17-shaped workbook also loads on 19 (`version-differences.md`).

**Authoring route that actually works:** build the dashboard in the editor UI (Enterprise
`spreadsheet_dashboard_edition` adds the **Spreadsheets** tab with *Add a spreadsheet* and a per-row
**Edit** button to the dashboard group form), then in the editor, in debug mode, use **File › Download
as JSON** and commit that file as the module's workbook. Do **not** export the record's
`spreadsheet_data`: once anyone has edited the dashboard, that field still holds the original file —
the edits live in revisions and a snapshot (§11). Hand-writing this JSON is error-prone, and the
failure mode is silent — a malformed pivot yields `0`, not an error. Keeping the shipped dashboard
editable from the UI afterwards is §11.

## 1. Workbook skeleton

```json
{
  "version": 12,
  "sheets": [{
    "id": "sheet1", "name": "Dashboard",
    "colNumber": 7, "rowNumber": 57,
    "rows": {"6": {"size": 40}, "18": {"size": 40}},
    "cols": {"0": {"size": 225}, "1": {"size": 150}, "2": {"size": 100},
             "3": {"size": 50},
             "4": {"size": 225}, "5": {"size": 150}, "6": {"size": 100}},
    "merges": [],
    "cells": {
      "A7":  {"style": 1, "border": 1, "content": "[Section Title](odoo://view/{...})"},
      "B7":  {"border": 1}, "C7": {"border": 1},
      "A20": {"style": 2, "border": 2, "content": "=_t(\"Name\")"},
      "A21": {"style": 3, "content": "=ODOO.LIST(1,1,\"name\")"},
      "C21": {"style": 3, "format": 2, "content": "=ODOO.LIST(1,1,\"amount_untaxed\")"}
    },
    "conditionalFormats": [],
    "figures": [
      {"id": "kpi-demand", "x": 0, "y": 0, "width": 200, "height": 120, "tag": "chart",
       "data": {"type": "scorecard", "title": "Requests", "background": "",
                "keyValue": "Data!D2", "baseline": "Data!E2",
                "baselineMode": "percentage", "baselineDescr": "vs last period",
                "baselineColorUp": "#00A04A", "baselineColorDown": "#DC6965"}},
      {"id": "chart-trend", "x": 0, "y": 178, "width": 1000, "height": 230, "tag": "chart",
       "data": {"type": "odoo_line", "title": "", "background": "#FFFFFF",
                "legendPosition": "none", "verticalAxisPosition": "left",
                "metaData": {"groupBy": ["date:day"], "measure": "__count",
                             "order": null, "resModel": "your.model"},
                "searchParams": {"comparison": null, "context": {}, "domain": [],
                                 "groupBy": ["date:day"], "orderBy": []}}}
    ],
    "areGridLinesVisible": true, "isVisible": true
  }, {
    "id": "sheet2", "name": "Data", "colNumber": 26, "rowNumber": 100,
    "rows": {}, "cols": {}, "merges": [],
    "cells": {"D2": {"content": "=ODOO.PIVOT(1,\"__count\")"},
              "E2": {"content": "=ODOO.PIVOT(2,\"__count\")"}},
    "conditionalFormats": [], "figures": [],
    "areGridLinesVisible": true, "isVisible": true
  }],
  "entities": {},
  "styles": {
    "1": {"textColor": "#01666b", "bold": true, "fontSize": 16},
    "2": {"bold": true, "fillColor": ""},
    "3": {"fillColor": "#f2f2f2", "textColor": "#01666b"}
  },
  "formats": {"1": "#,##0", "2": "[$$]#,##0", "3": "0.0%"},
  "borders": {"1": {"bottom": ["thin", "#000"]}, "2": {"top": ["thin", "#000"]}},
  "revisionId": "START_REVISION",
  "settings": {"locale": {"name": "English (US)", "code": "en_US",
     "thousandsSeparator": ",", "decimalSeparator": ".", "dateFormat": "mm/dd/yyyy",
     "timeFormat": "hh:mm:ss", "formulaArgSeparator": ","}},
  "chartOdooMenusReferences": {"chart-trend": "your_module.your_menu_xmlid"},
  "odooVersion": 4,
  "lists": {"1": {"id": "1", "model": "your.model", "columns": ["name", "amount_untaxed"],
                  "domain": [], "context": {},
                  "orderBy": [{"name": "amount_untaxed", "asc": false}], "name": "Top Records"}},
  "listNextId": 2,
  "pivots": {
    "1": {"id": "1", "model": "your.model", "colGroupBys": [], "rowGroupBys": [],
          "context": {}, "domain": [], "measures": [{"field": "__count"}],
          "name": "kpi - current", "sortedColumn": null},
    "2": {"id": "2", "model": "your.model", "colGroupBys": [], "rowGroupBys": [],
          "context": {}, "domain": [], "measures": [{"field": "__count"}],
          "name": "kpi - previous", "sortedColumn": null}
  },
  "pivotNextId": 3,
  "globalFilters": [
    {"id": "<uuid-f1>", "type": "date", "label": "Period",
     "defaultValue": "last_three_months", "rangeType": "relative",
     "defaultsToCurrentPeriod": false,
     "pivotFields": {"1": {"field": "date", "type": "datetime", "offset": 0},
                     "2": {"field": "date", "type": "datetime", "offset": -1}},
     "listFields":  {"1": {"field": "date_order", "type": "datetime", "offset": 0}},
     "graphFields": {"chart-trend": {"field": "date", "type": "datetime", "offset": 0}}}
  ]
}
```

**The same figures in the Odoo 19 shape** — what a 19 export looks like, and what you author only if
the module ships on 19 alone (a 19-shaped file does not load correctly on 17):

```json
{"id": "kpi-demand", "col": 0, "row": 0, "offset": {"x": 0, "y": 0},
 "width": 200, "height": 120, "tag": "chart",
 "data": {"type": "scorecard", "chartId": "kpi-demand",
          "title": {"text": "Requests", "fontSize": 14},
          "keyValue": "Data!D2", "baseline": "Data!E2", "humanize": true,
          "baselineMode": "percentage", "baselineDescr": {"text": "vs last period"},
          "baselineColorUp": "#43C5B1", "baselineColorDown": "#EA6175", "background": ""}},
{"id": "chart-stage", "col": 0, "row": 0, "offset": {"x": 0, "y": 178},
 "width": 1000, "height": 230, "tag": "chart",
 "data": {"type": "odoo_bar", "chartId": "chart-stage",
          "title": {"text": "", "bold": true, "fontSize": 14, "color": "#10233A", "align": "left"},
          "background": "#FFFFFF", "legendPosition": "top", "showValues": false, "humanize": true,
          "dataSets": [{"backgroundColor": "#0F3D5E"}, {"backgroundColor": "#1BA39C"}],
          "metaData": {"groupBy": ["stage_id"], "measure": "__count", "order": null,
                       "resModel": "your.model"},
          "searchParams": {"comparison": null, "context": {}, "domain": [],
                           "groupBy": ["stage_id"], "orderBy": []}}}
```

Export a real 19 dashboard and diff against it before shipping: keys above were read from the 19
source, not from a 19 export.

Binding record:

```xml
<!-- noupdate="1": the module installs the dashboard once; after that the UI owns it (§11). -->
<odoo noupdate="1">
    <record id="my_dashboard" model="spreadsheet.dashboard">
        <field name="name">My Dashboard</field>
        <field name="spreadsheet_binary_data" type="base64" file="my_module/data/files/my_dashboard.json"/>
        <field name="dashboard_group_id" ref="spreadsheet_dashboard.spreadsheet_dashboard_group_sales"/>
        <field name="group_ids" eval="[Command.link(ref('base.group_user'))]"/>
        <field name="sequence">100</field>
    </record>
</odoo>
```

Record fields by version (`spreadsheet_dashboard` model):

| Field | 17 | 18 | 19 |
|---|---|---|---|
| `name` (translatable), `dashboard_group_id`, `sequence`, `group_ids` | yes | yes | yes |
| `is_published` (default `True`), `main_data_model_ids`, `sample_dashboard_file_path` | — | yes | yes |
| company scope | — | `company_id` (Many2one) | `company_ids` (Many2many) |
| favourites (`favorite_user_ids`, `is_favorite`) | — | — | yes |

Odoo's own shipped dashboard records are **not** `noupdate` — every update of the module that ships
them resets them to the file. That is right for core templates and wrong for a client dashboard
people are expected to edit.

Check `group_ids` deliberately. Widening a dashboard to all internal users is a governance decision,
not a default — if the surface it replaces was gated to a manager group, say so and get it confirmed.

## 2. The observed design grid — imitate it

The numbers below were measured across a set of existing dashboard workbooks; the *intent* behind
them is inferred, so treat them as a well-tested starting grid rather than a specification. Any
specific hex here is an example — substitute the palette the module actually uses.

- **Design width exactly 1000px** across every shipped dashboard, split as e.g.
  `100,175,100,100,50,100,175,100,100` or `225,150,100,50,225,150,100`. Widen to ~1200px only if you
  accept that laptops below ~1250px will scroll.
- **A 50px empty column is the gutter** between two half-width panels. That is the only "gap"
  mechanism that exists.
- **Rows:** 23px default; section-title rows resized to **40px**.
- **Vertical bands:** KPI scorecards float at `y=0, height=120` over six empty 23px rows; the first
  chart sits at **`y=178`** = `6×23 + 40`, exactly flush under the first title row. That same `y=178`
  recurs across modules.
- **KPI pitch:** 4 cards of 200px at `x = 0, 210, 420, 630` — a 10px gap. Also seen: 5×192 at 202
  pitch, 3×200, 2×450 at 500 pitch.
- **Charts per row:** one at 1000px, or two at 475px with the 50px gutter. Three does not work at this
  width — ~300px per chart puts the x axis under Chart.js's label truncation (20 characters) and
  forces the 15-60° tick rotation, so the category labels stop being readable before the chart does.
- **Then a repeating 13-row stanza:** 40px title row + column-header row + 10 data rows + 1 spacer.
- **Palette (Odoo's shipped design language):** one accent hue carrying both section titles and the
  primary text column (teal `#01666b`), magenta `#741b47` as a secondary accent, a near-white zebra
  fill (`#f2f2f2` / `#f8f9fa`), thin `#000` rules. KPI up/down use the library's scorecard defaults —
  `#00A04A` / `#DC6965` in 17, `#43C5B1` / `#EA6175` in 19. Keep the defaults unless the design has
  a reason to diverge, because users read them as a fixed convention. A deliberate house palette is
  that reason (§9).
- **Typography:** two steps only — 10pt body and 16pt bold titles. In 17 scorecard titles render at
  an engine-fixed ~18px grey regardless of what you author, so a third step would only ever apply to
  cells and would not survive next to a scorecard. In 19 the scorecard title is settable (default
  14px) — match it to the cell title step.
- **Every title is a drill-down** (`odoo://view/…`), and charts link to menus via
  `chartOdooMenusReferences`.
- **Restraint across the whole sampled suite:** no conditional formatting, no icons, no data bars, no
  images, essentially no merges, no hidden sheets.

Two sheets: `Dashboard` for presentation, `Data` for staging formulas. Only the first is displayed.

## 3. Period-over-period KPI (the delta recipe)

1. Define **two identical pivots** — `"kpi - current"` and `"kpi - previous"`.
2. In the date global filter, give the first `offset: 0` and the second `offset: -1` under
   `pivotFields`. The offset is applied as a `plusParam` on the date domain, so `-1` means one period
   back at the filter's own `rangeType` granularity.
3. Stage both on the `Data` sheet (`=ODOO.PIVOT(1,"…")`, `=ODOO.PIVOT(2,"…")`).
4. Point the scorecard at `keyValue: "Data!D2"`, `baseline: "Data!E2"`,
   `baselineMode: "percentage"`, `baselineDescr: "vs last period"`.

The up/down arrow and the `#00A04A` / `#DC6965` colouring are automatic.

**Limitation to plan around:** a KPI backed by a custom formula rather than a pivot usually cannot be
cloned this way — a custom function that takes a filter *label* has no offset parameter. Adding one
is an additive optional argument (category D), not a business-logic change, but it is code.

## 4. Filters

- `type` is `text`, `date` or `relation` only. Across shipped dashboards the census is roughly
  relation ×102, date ×25, text ×1 — relation filters are the workhorse.
- Prefer `rangeType: "relative"` with a `defaultValue` over `rangeType: "month"`: the month form
  renders as a month+year dropdown pair, and with the period pinned to a single month a `:month`
  grouping collapses every trend chart to one point. Intra-period granularity (`:day` / `:week`) is
  required for a trend.
- **Every pivot, list and chart needs its own entry** in `pivotFields` / `listFields` / `graphFields`.
  A missing or mismatched entry does not error — the object is simply **unfiltered**, which is how a
  card ends up silently all-time while its neighbours are monthly.
- A relation filter on the dimension users actually scope by (site, property, team, region) is
  usually the highest-value filter you can add, and costs one filter definition plus field matching.
- **A custom formula that resolves a filter by its `label` string breaks silently on rename.** If a
  module function takes `"Period"` and looks the filter up by label, renaming the filter in the
  workbook degrades that card to an unfiltered all-time count with no error. Rename the two together,
  or match on the filter `id`.

## 5. Section header that is also a drill-down and a full-width rule

```json
"A7": {"style": 1, "border": 1,
       "content": "[Monthly Sales](odoo://view/{\"viewType\":\"graph\",\"action\":{\"domain\":[],\"context\":{},\"modelName\":\"sale.report\",\"views\":[[false,\"graph\"]]},\"threshold\":0,\"name\":\"Analysis\"})"},
"B7": {"border": 1}, "C7": {"border": 1}
```

with `styles["1"] = {"textColor": "#01666b", "bold": true, "fontSize": 16}` and
`borders["1"] = {"bottom": ["thin", "#000"]}`. **The sibling `border: 1` cells are what extend the
rule across the row** — a border on one cell stops at that cell.

Keep section labels **left-aligned** and merge only across the used span. `align: "right"` inside a
full-width merge pushes the text to the far edge of the merge, where it falls outside the viewport at
normal widths.

## 6. Formatting idioms

- Counts `#,##0` — never `#,##0.00`, which claims a precision a count does not have and reads as
  money.
- Rates `0.0%`. Currency `[$$]#,##0` or `#,##0` with the company currency (injected server-side).
- **Compact big numbers:** 17 — `=FORMAT.LARGE.NUMBER(B2)` on the `Data` sheet, with `keyValue`
  pointing at that cell; there is no `humanize` flag. 19 — scorecards and charts carry `humanize`
  (scorecard default `true`), so `42.8M` is automatic; set `humanize: false` to show the full value.
- **Always wrap literals for translation:** `=_t("Customer")`. Hardcoded bilingual strings
  (`"ملغي — Cancelled"`) show both languages to every user regardless of their own.
- Chart titles: in 17, author `title: ""` on the figure and render the title as a styled cell above
  it — the canvas title is locked at 22px in the Chart.js font family, which does not match the cell
  font. In 19, set `title: {text, bold, fontSize, color, align: "left"}` on the figure instead: the
  title then lives inside the card, survives mobile, and the cell row above it is free.
- **Status fills on table cells** (over / near / under budget): a conditional format on the value
  column. In 19, `operator: "customFormula"` can compare neighbours (`=C2>B2`). In 17, stage a status
  value or ratio on the `Data` sheet and use a plain value rule on it. Fills are rectangles — there
  are no rounded "pills" on canvas.
- **Table header band:** one style with `fillColor` (dark brand colour), `textColor` `#FFFFFF`,
  `bold`, applied to every header cell in the used span; right-align numeric column headers to sit
  over their figures.

## 7. Scoped chrome (ladder rung B — one SCSS file)

Register in `web.assets_backend` (SCSS is eager; the JS bundle is lazy and never carries SCSS).
Separate file — never inline styles. Print rules go in a second file registered in
`spreadsheet.assets_print`, next to core's own print file. These selectors are the same in 17 and 19.

### 7.1 Cards for charts and KPIs — the highest-value change

```scss
// your_module/static/src/scss/dashboard.scss
// Scope: our dashboard's figures only. `data-id` values are authored in the workbook JSON.
.o_spreadsheet_dashboard_action .o-figure[data-id^="kpi-"],
.o_spreadsheet_dashboard_action .o-figure[data-id^="chart-"] {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 1px 3px rgba(16, 24, 40, .10);
    overflow: hidden;   // clips the chart canvas to the radius
}
```

[17 runtime] radius, shadow and background apply to `.o-figure` with **no `!important`**, and
`.o-figure` computes to `border-box`. A rule under `.o_spreadsheet_dashboard_action .o-figure` with
no `data-id` filter works too, but restyles **every** dashboard in the database — use it only when
that is the intent (a company-wide house style), and say so. Note the trade-off with UI editing: a
`data-id` prefix rule never reaches a figure a user adds through the editor (it gets a UUID id), so a
dashboard meant to be edited in the UI should take the unfiltered rule (§11). **Never** add padding to
`.o-figure-wrapper` (content-box + inline sizing → 300x180 becomes 312x192 and falls out of grid
alignment); put breathing room on `.o-figure` or in the stored position.

### 7.2 Page background

Needs the four-class depth, and only tints the margins around the sheet — the canvas covers the sheet:

```scss
.o_spreadsheet_dashboard_action { background-color: #f7f8fa; }
.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet .o-grid { background-color: #f7f8fa; }
```

To tint the sheet body itself, set `fillColor` on the cells in the JSON. A page background that
differs from the sheet fill makes the sheet read as a white slab: either fill the used cells with
the same colour, or accept the slab as the "paper".

### 7.3 Sidebar

```scss
.o_spreadsheet_dashboard_action .o_spreadsheet_dashboard_search_panel {
    max-width: 240px;                       // core caps at 200px
    li { border-radius: 6px; margin-inline: 4px; }
    li.active { /* accent here — use logical properties so RTL flips */ }
}
```

In 19 the sidebar also collapses (a toggle button) and carries `.o_edit_dashboard` and
`.o_dashboard_star` controls; do not hide them.

### 7.4 Filter strip

```scss
.o_spreadsheet_dashboard_action .o_control_panel_actions {
    .o_filter_value_container { width: 260px; }   // core: 235px
}
```

### 7.5 Loading state and mobile

`.o_spreadsheet_dashboard_action .dashboard-loading-status` for the `Loading...` / error text.
Mobile cards: `.o_mobile_dashboard .o-chart-container` (17 — never the unclassed parents).

### 7.6 Print (`spreadsheet.assets_print`)

```scss
@media print {
    .o_spreadsheet_dashboard_action .o-figure { box-shadow: none; }
}
```

## 8. Chart theme (ladder rung D — optional, and global)

Separate JS file registered in `spreadsheet.o_spreadsheet`.

### 8.1 Fonts

```js
/** @odoo-module **/
// Chart.js is loaded before the spreadsheet bundle by the action loader.
if (window.Chart) {
    window.Chart.defaults.font.family =
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    window.Chart.defaults.font.size = 12;
}
```

Session-global: it also restyles graph views. Not runtime-verified — check one dashboard chart and
one graph view after adding it. State the global effect in the module description.

### 8.2 Series palette

**On 19, set bar / line / combo colours in the definition** (`dataSets[i].backgroundColor`, §1) and
use this wrapper **only for pie and doughnut**, whose slice colours are not storable. **On 17 the
wrapper is the only way** to colour any series. Wrap the existing runtime rather than reimplementing
it; `Registry.add` silently overwrites.

```js
/** @odoo-module **/
import * as spreadsheet from "@odoo/o-spreadsheet";
const { chartRegistry } = spreadsheet.registries;
// Replace with the module's palette. Order matters: series / slices are assigned by index.
const PALETTE = ["#01666b", "#741b47", "#f1c232", "#3266ca", "#6aa84f"];

for (const type of ["odoo_bar", "odoo_line", "odoo_pie"]) {
    const base = chartRegistry.get(type);
    if (!base) continue;
    chartRegistry.add(type, {
        ...base,
        getChartRuntime(chart, getters) {
            const runtime = base.getChartRuntime(chart, getters);
            if (!getters.isDashboard()) {
                return runtime;
            }
            const datasets = runtime.chartJsConfig.data.datasets;
            if (type === "odoo_pie") {
                // One colour per slice, shared by every ring.
                for (const ds of datasets) {
                    ds.backgroundColor = ds.data.map((_, i) => PALETTE[i % PALETTE.length]);
                }
            } else {
                datasets.forEach((ds, i) => {
                    // 19: keep a colour the definition stored for this series.
                    if (chart.getDefinition?.().dataSets?.[i]?.backgroundColor) return;
                    ds.backgroundColor = ds.borderColor = PALETTE[i % PALETTE.length];
                });
            }
            return runtime;
        },
    });
}
```

The guide this was derived from marks the wrapper **not runtime-exercised**. Verify on the target
version: one bar, one line and one pie on a dashboard, plus one spreadsheet *outside* dashboard mode
to confirm the `isDashboard()` guard holds. The guard scopes the palette to dashboard mode, not to
*your* dashboards: every dashboard in the database gets it. Registrations must run before any
`Model` is constructed; use the `("after", "spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js", …)`
manifest form if load order bites.

## 9. Applying a brand palette — one token set, six carriers

A house palette cannot live in one place: o-spreadsheet has no theme object. Write the tokens down
once (in the module README or a design doc), then carry each token into exactly these places:

| Carrier | What it holds | Mechanism | Versions |
|---|---|---|---|
| Workbook `styles` | section titles, table header band, zebra rows, body text, page-coloured fills | `textColor`, `fillColor`, `bold`, `fontSize` | 17, 19 |
| Scorecard definitions | up / down colours per KPI, card background | `baselineColorUp`, `baselineColorDown`, `background` | 17, 19 |
| Chart definitions | series colours, title colour | `dataSets[i].backgroundColor`, `title.color` | **19 only** (bar/line/combo) |
| Conditional formats | status fills (good / watch / bad) | rule `style.fillColor` / `textColor` | 17, 19 (operator names differ — `version-differences.md`) |
| SCSS (rung B) | page background, card radius / border / shadow, sidebar accent, filter strip | §7 | 17, 19 |
| JS wrapper (rung D) | series colours on 17; pie / doughnut slices on 17 and 19; chart font | §8 | 17, 19 |

Rules that keep a palette honest:

- **Semantic colours are reserved.** Good / watch / bad hues appear only where they encode status —
  never as a series colour, a section accent or decoration. Otherwise a reader cannot tell "this is
  red because it is bad" from "this is red because it is series 5".
- **Swap up/down colours on KPIs where up is bad** (cost, overdue, churn): `baselineColorUp` = bad,
  `baselineColorDown` = good. The scorecard colours by sign only.
- **Series order is colour order.** The first series gets the primary colour; keep the dataset order
  stable across charts so "Q1" is the same colour everywhere.
- **Check contrast against the card.** Chart text auto-flips at luminance 0.3; a mid-tone card
  background takes text-colour control away from you. Keep cards white or near-white.
- `text` and `progress` scorecard modes render no colour — a coloured status caption ("7 at risk"
  in amber) is not reproducible on a scorecard; use a coloured cell next to it, or drop the colour.

## 10. Module architecture for dashboard work

Four layers keep upgrade risk where it belongs:

1. **Content and layout — JSON, per dashboard.** KPI values, tables, charts, section titles, colours,
   formats, geometry. One JSON file per dashboard under `<module>/data/files/`, bound by a
   `spreadsheet.dashboard` record. Standardise on one design grid (§2).
2. **One shared design-token module — SCSS, once for all dashboards.** All
   `.o_spreadsheet_dashboard_action`-scoped SCSS: cards, page background, sidebar, filter strip,
   print. One file, one place to review at upgrade time.
3. **One shared chart-theme module — JS, optional.** Only if the design needs brand chart colours on
   17, pie colours on 19, or a unified font. A single file in `spreadsheet.o_spreadsheet`; the piece
   most likely to need attention on an Odoo upgrade.
4. **Custom figure types — JS, only with a named requirement.** Sparkline KPIs, icon cards. Real cost.

A pure-data dashboard module (layer 1 only) and a data-plus-plugin module (layers 1 + 3/4, JS in
`spreadsheet.o_spreadsheet`) are both legitimate shapes — copy whichever an existing module in the
project already uses.

**Sequencing a redesign:** author in the editor UI → **File › Download as JSON** (debug mode) → commit
it as module data in a `noupdate="1"` record (§11) → add the layer-2 SCSS → update the module on a **cloned** database and read the server log
(`stack-doctor`) → verify at 1440px, 768px, 414px and in print → check an Arabic session if the
dashboard is user-facing → open one unrelated dashboard and confirm it is unchanged.

## 11. Organic dashboards — editable from the Edit button

An *organic* dashboard is one a functional user can open from the dashboard group form
(**Spreadsheets** tab › **Edit**), change in the spreadsheet editor, and keep — without a developer,
and without the next module update undoing it. Everything here was read from Enterprise
`spreadsheet_edition` / `spreadsheet_dashboard_edition` source for 17, 18 and 19 (identical on the
points below). On Community there is no Edit button, so there are no UI edits to lose.

### How UI edits are stored

- The Edit button opens the collaborative spreadsheet editor (`action_edit_dashboard`).
- Each change is saved as a `spreadsheet.revision` record; periodically the revisions are folded into
  `spreadsheet_snapshot`. `spreadsheet_binary_data` / `spreadsheet_data` keep the **original** file.
- The dashboard view loads snapshot + revisions (`join_spreadsheet_session` on 17;
  `_get_serialized_readonly_dashboard` on 18/19), so viewers see the edited version.
- **Any write to `spreadsheet_binary_data` deletes every revision and the snapshot**
  (`spreadsheet.mixin.write` → `_delete_collaborative_data`), unless the context carries
  `preserve_spreadsheet_revisions`. A module update that reloads a non-`noupdate` dashboard record is
  such a write: all UI edits vanish silently.

### The rules

1. **Ship custom dashboard records with `noupdate="1"`.** The module installs the dashboard once; the
   UI owns it afterwards. Without it, every `-u` resets the dashboard to the file.
2. **Round-trip through the editor, not the database field.** UI → **File › Download as JSON** (debug
   mode) → commit. `spreadsheet_data` is stale as soon as someone has edited.
3. **Never write `spreadsheet_binary_data` from code on a live dashboard** — a migration, a sync job, a
   server action — unless wiping the users' edits is the intent and has been agreed. To ship a new
   layout to a `noupdate` dashboard, either (a) write it only where the record has no revisions
   (`not dashboard.spreadsheet_revision_ids`) and report the others, or (b) ship it as a **new**
   dashboard record next to the edited one and let the owner retire the old one. Never force it.
4. **Only use what the editor can show and save.** Everything in the workbook JSON is editable in the
   UI. These are not, so keep them few and say where they live in the module README:
   - **SCSS chrome** (rung B): edited in code only. Scope it so figures a user *adds* in the UI get it
     too — a `data-id` prefix rule never matches a UI-created figure (the editor gives new figures
     UUID ids). For a company-wide house style, style every figure under
     `.o_spreadsheet_dashboard_action .o-figure`; reserve `data-id` rules for one-off cards.
   - **JS chart palettes** (rung D): the editor is not in dashboard mode, so an `isDashboard()`-guarded
     palette shows **default** colours while editing and the house colours when viewing. Tell editors.
     On 19, prefer series colours stored in the chart (`dataSets[i].backgroundColor`) — they are set
     and changed in the editor's chart panel, so they are organic; the wrapper must leave stored
     colours alone.
   - **Custom formulas / data sources** registered in `spreadsheet.o_spreadsheet`: the editor loads
     the same bundle, so they work while editing — but a dashboard that uses them breaks if the module
     providing them is uninstalled.
5. **Design for the editor's hands.** Readable figure titles, a `Data` sheet with labelled staging
   cells, `=_t()` labels, and pivots named for what they compute (`"revenue - current"`), so the next
   person can change the dashboard without reverse-engineering it.
6. **Access.** Editing needs write access on the dashboard (the collaborative access check runs on
   every save). `group_ids` controls who *sees* it; it does not grant editing.

### Checks

- [ ] Every custom `spreadsheet.dashboard` record is inside a `noupdate="1"` block.
- [ ] After install: open the dashboard via **Edit**, change one cell, close, reload the dashboard —
      the change shows. Then update the module (`-u`) on the clone and reload — the change is still
      there.
- [ ] Add a chart in the editor; on viewing, it gets the same card chrome as the shipped ones.
- [ ] No code path in the module (or any sync job) writes `spreadsheet_binary_data` on existing
      dashboards.
