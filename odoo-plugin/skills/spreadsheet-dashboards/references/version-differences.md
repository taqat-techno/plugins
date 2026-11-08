# Version differences — Odoo 17 vs Odoo 19

Reference for `spreadsheet-dashboards`. The rest of this skill was verified on **Odoo 17
(o-spreadsheet 17.0.71)**. This file records what changed by **Odoo 19 (o-spreadsheet 19.0.4)**,
read from `spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js` and
`spreadsheet/static/src/chart/odoo_chart/*.js` in a 19.0 community tree. Odoo 18 was **not
checked**: on 18, verify each row below against its own source before relying on it.

**First step on any dashboard task:** read the target database's Odoo version (the
`spreadsheet` module's manifest, or `server_version` from the instance). Every row below is a
place where the right answer depends on it.

## Chart styling

| Capability | Odoo 17 | Odoo 19 | Where (19) |
|---|---|---|---|
| Per-series colour, bar / line / combo | not storable — fixed runtime palette by dataset index | **stored**: `definition.dataSets[i].backgroundColor` | `getChartColorsGenerator` → `ColorGenerator(size, dataSets.map(ds => ds.backgroundColor))` |
| Per-slice colour, pie / doughnut | not storable | **still not storable** — `getPieChartDatasets` builds a fresh `ColorGenerator` and ignores `dataSets` | `getPieChartDatasets` |
| Chart title | string; rendered 22px, normal weight | object `{text, color, fontSize, bold, italic, align}`; default 16px | `getChartTitle`, `CHART_TITLE_FONT_SIZE = 16` |
| Series label override | — | `dataSets[i].label` | `getBarChartDatasets` |
| Trend line per series | — | `dataSets[i].trend = {display, type, …}` (not on horizontal bars) | `getTrendDatasetForBarChart` |
| Value labels on bars / slices | — | `showValues: true` | `chartShowValuesPlugin` |
| Compact axis / value numbers | hard threshold `abs(v) >= 1000` | `humanize` flag on the chart | `formatTickValue(…, humanize)` |
| Odoo chart types | `odoo_bar`, `odoo_line`, `odoo_pie` | adds `odoo_combo`, `odoo_waterfall`, `odoo_funnel`, `odoo_pyramid`, `odoo_radar`, `odoo_scatter`, `odoo_geo`, `odoo_sunburst`, `odoo_treemap`; bars gain `horizontal`, `zoomable`, `axesDesign`; pie gains `isDoughnut` + `pieHolePercentage` | `chart/odoo_chart/` |
| Muted text colour on a chart | auto white/black at luminance 0.3 | unchanged: `#666666` on light, `#C8C8C8` on dark backgrounds, unless `title.color` is set | `chartMutedFontColor` |

## Scorecards

| Capability | Odoo 17 | Odoo 19 |
|---|---|---|
| Default up / down colours | `#00A04A` / `#DC6965` | `#43C5B1` / `#EA6175` (`DEFAULT_SCORECARD_BASELINE_COLOR_UP/DOWN`) |
| `baselineMode` | `percentage`, `difference`, `text` | adds `progress` (key ÷ baseline, rendered `0.0%`) |
| Colour in `text` / `progress` mode | none | **none** — `getBaselineColor` returns `undefined`; the baseline renders in the muted colour |
| Compact key value (`42.8M`) | `=FORMAT.LARGE.NUMBER()` on the Data sheet | `humanize` defaults to **true**; set `humanize: false` to show the full number |
| `keyDescr` (caption under the key) | — | stored |
| `baselineDescr` | string | object `{text}` (migration `18.4.2` converts strings) |
| Title | string | object, default 14px (`SCORECARD_CHART_TITLE_FONT_SIZE`) |

`getBaselineColor` colours by **sign of the difference only**: up gets `baselineColorUp`, down
gets `baselineColorDown`. For a KPI where *up is bad* (cost, churn, overdue), swap the two colours
on that card. There is no per-card threshold colouring.

## Workbook format

Odoo 19 migrates older workbooks on load, so a 17-shaped JSON still opens. The migrations that
matter when you read or diff a 19 export:

| Step | Change |
|---|---|
| `18.3.1` | figure `x`/`y` → `{col: 0, row: 0, offset: {x, y}}` (still pixel offsets from A1) |
| `18.4.1` | conditional-format operators renamed: `GreaterThan` → `isGreaterThan`, `Between` → `isBetween`, `Equal` → `isEqual`, `ContainsText` → `containsText`, etc. |
| `18.4.2` | scorecard `baselineDescr` string → `{text}` |
| `18.4.3` | pivot `sortedColumn.measure` → the measure's `id` |
| `18.5.1` | every chart figure gets `data.chartId = figure.id` |

Author for the **oldest version the module ships on**. A 17-shaped workbook works on both; a
19-shaped one (title objects, `dataSets` colours, `offset` positions) will not load correctly on 17.
If the module ships on both, keep one workbook per version, or author at 17 and accept 17's
limits.

Conditional formatting on 19 supports `operator: "customFormula"`, which can compare a cell with
its neighbours (for example `=C2>B2` to flag over-budget). On 17, verify before using it; the safe
17 route is a status value staged on the `Data` sheet, then a plain value rule on that.

## Unchanged in 19 (verified)

- The sheet body is still one canvas: `drawGlobalBackground` paints it before any cell.
- `.o-figure` still carries `data-id` = the figure id (`t-att-data-id="props.figureUI.id"`).
- The library still forces `direction: ltr` on itself ("rtl not supported ATM").
- `DEFAULT_FONT` is still `'Roboto', arial`; there is no per-cell font family.
- Dashboard mode still hides gridlines and headers regardless of the JSON flags.
