# Authoring recipes — workbook JSON, geometry, deltas, scoped chrome

Reference for `spreadsheet-dashboards`. Everything here is category A/B (workbook JSON) except the
last two sections. Schema shown is the shipped dashboard idiom (`version: 12`, `odooVersion: 4`);
the library's own `CURRENT_VERSION` runs ahead and migrations are applied client-side on load, so
authoring at the shipped version is safe.

**Authoring route that actually works:** build the dashboard in the editor UI (a dashboard-edition
module adds an "Add a spreadsheet" button to the group form), then export the record's
`spreadsheet_data` and commit it as the module's JSON file. Hand-writing this JSON is error-prone,
and the failure mode is silent — a malformed pivot yields `0`, not an error.

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
  "lists": {}, "listNextId": 1,
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
     "listFields":  {},
     "graphFields": {"chart-trend": {"field": "date", "type": "datetime", "offset": 0}}}
  ]
}
```

Binding record:

```xml
<record id="my_dashboard" model="spreadsheet.dashboard">
    <field name="name">My Dashboard</field>
    <field name="spreadsheet_binary_data" type="base64" file="my_module/data/files/my_dashboard.json"/>
    <field name="dashboard_group_id" ref="spreadsheet_dashboard.spreadsheet_dashboard_group_sales"/>
    <field name="group_ids" eval="[Command.link(ref('base.group_user'))]"/>
    <field name="sequence">100</field>
</record>
```

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
- **Palette:** one accent hue carrying both section titles and the primary text column (the sample
  workbooks use a teal, `#01666b`); a near-white zebra fill (`#f2f2f2` / `#f8f9fa`); thin `#000`
  rules. `#00A04A` / `#DC6965` for KPI up/down are the library's own scorecard defaults — leave those
  alone unless the whole design has a reason to diverge, since users read them as a fixed convention.
- **Typography:** two steps only — 10pt body and 16pt bold titles. Scorecard titles render at an
  engine-fixed size regardless of what you author, so a third step would only ever apply to cells and
  would not survive next to a scorecard.
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
- **Compact big numbers:** `=FORMAT.LARGE.NUMBER(B2)` on the `Data` sheet, with `keyValue` pointing at
  that cell. There is no `humanize` flag.
- **Always wrap literals for translation:** `=_t("Customer")`. Hardcoded bilingual strings
  (`"ملغي — Cancelled"`) show both languages to every user regardless of their own.
- Chart `title: ""` on the figure; render the title as a styled cell above it. The canvas title is
  locked at 22px in the Chart.js font family, which does not match the cell font.

## 7. Scoped card chrome (category C — one SCSS file)

Register in `web.assets_backend` (SCSS is eager; the JS bundle is lazy and never carries SCSS).
Separate file — never inline styles.

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

// Print: drop the elevation.
@media print {
    .o_spreadsheet_dashboard_action .o-figure { box-shadow: none; }
}
```

Runtime verified: radius, shadow and background apply to `.o-figure` with **no `!important`**, and
`.o-figure` computes to `border-box`. **Never** add padding to `.o-figure-wrapper` (content-box +
inline sizing → 300x180 becomes 312x192 and falls out of grid alignment).

Page background, if you want it, needs the four-class depth and only tints the margins around the
sheet — the canvas covers the sheet itself:

```scss
.o_spreadsheet_dashboard_action { background-color: #f7f8fa; }
.o_spreadsheet_dashboard_action .o_renderer .o-spreadsheet .o-grid { background-color: #f7f8fa; }
```

Other useful chrome targets: `.o_spreadsheet_dashboard_search_panel` (core caps it at 200px),
`.o_filter_value_container` (core: 235px), `.dashboard-loading-status`.

## 8. Chart theme (category D — optional, and global)

Separate JS file registered in `spreadsheet.o_spreadsheet`. Wrap the existing runtime rather than
reimplementing it; `Registry.add` silently overwrites.

```js
/** @odoo-module **/
import * as spreadsheet from "@odoo/o-spreadsheet";
const { chartRegistry } = spreadsheet.registries;
// Replace with the module's own palette. Order matters: series are assigned by dataset index.
const PALETTE = ["#01666b", "#741b47", "#f1c232", "#3266ca", "#6aa84f"];

for (const type of ["odoo_bar", "odoo_line", "odoo_pie"]) {
    const base = chartRegistry.get(type);
    chartRegistry.add(type, {
        ...base,
        getChartRuntime(chart, getters) {
            const runtime = base.getChartRuntime(chart, getters);
            if (getters.isDashboard()) {
                runtime.chartJsConfig.data.datasets.forEach((ds, i) => {
                    ds.backgroundColor = ds.borderColor = PALETTE[i % PALETTE.length];
                });
            }
            return runtime;
        },
    });
}
```

Font unification is one line (`window.Chart.defaults.font.family = …`) but is **session-global** — it
also restyles graph views. Both of these change charts in *every* spreadsheet, not just yours; the
`isDashboard()` guard above is the minimum containment. State the global effect in the module
description, and skip the whole layer if the design does not require it.
