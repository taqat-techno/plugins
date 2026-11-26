# List workbooks — lists, reporting views and a Calc sheet instead of pivots

Reference for `spreadsheet-dashboards` rule 15. A dashboard can read its numbers from **lists**
(`ODOO.LIST`) and compute every card with plain spreadsheet formulas, with no pivot at all. This
file is the layout, the reporting-view rules, the traps and the checks. It describes an option;
`SKILL.md` rule 15 says when to take it.

Evidence labels used below: **source** = read in the Odoo source for that version;
**field** = seen on a running Odoo 17 Enterprise database, not re-checked in source.

## 1. When lists, when pivots

| Situation | Take |
|---|---|
| The board is copied, frozen, exported or synchronised to a place where live pivots do not survive | lists: the data is in cells, so formulas and charts keep working |
| The numbers come from a reporting SQL view, already grouped | lists |
| A pivot over raw records makes the workbook large or slow (thousands of rows, megabytes of JSON) | lists over a grouped view |
| Cards need rules a pivot domain cannot express (several unrelated models, a `UNION`, a bucket computed in SQL) | lists over a view |
| Period-over-period deltas, relation filters, relative periods, click-through from a pivot cell to its records | pivots: all of these are native there |
| A small board on one model with standard measures | pivots: less to build and nothing to size |

What lists cost: you size the data sheet yourself (§3), drill-down links are written by hand
(`odoo://view/…`, `authoring-recipes.md` §5), category names typed into the Calc sheet are fixed at
build time (§6), and a comparison needs its own formulas (§5).

## 2. The three-sheet layout

Dashboard mode shows only the first sheet, so the other two are working space.

| Sheet | Holds |
|---|---|
| `Dashboard` (first) | figures and label cells only; every figure points at `Calc` |
| `Calc` | one labelled row per card (`SUMIFS` over the data columns), the small tables that feed the charts |
| `DATA_<name>` (one per list) | row 1: `=ODOO.LIST.HEADER(id,"field")`; rows 2…n+1: `=ODOO.LIST(id,n,"field")` |

```json
"lists": {
  "1": {"id": "1", "name": "DATA_SALES", "model": "x_report.sales_daily",
        "columns": ["x_date", "x_status", "x_count", "x_amount"],
        "domain": [], "context": {},
        "orderBy": [{"name": "x_date", "asc": true}, {"name": "id", "asc": true}],
        "fieldMatching": {}}
},
"listNextId": 2
```

Cards and tables on `Calc`:

```
=SUMIFS(DATA_SALES!D2:D, DATA_SALES!B2:B, "Confirmed")          one card
=IFERROR(SUM(DATA_SALES!D2:D)/SUM(DATA_SALES!C2:C), 0)          an average (see §4, zero)
=SUMIFS(DATA_SALES!C2:C, DATA_SALES!A2:A, ">="&DATE($B$1,3,1),
        DATA_SALES!A2:A, "<"&DATE($B$1,4,1))                    one month of a chart table
```

Charts are native `bar` / `line` / `pie` figures whose `dataSets` and `labelRange` point at a `Calc`
table. When converting a pivot dashboard, an `odoo_bar` / `odoo_line` figure becomes the native type
fed from such a table; keep the series in the original order, because on 17 colours follow series
order (rule 10).

Give the order a tie-breaker (`id` last). Without it two loads can return the rows in a different
order, and a stable row order is what makes a data sheet readable when someone has to debug it.

## 3. Sizing the data sheet

`ODOO.LIST(id, n, field)` reads row `n`. The list fetches as many records as the highest `n` written
in the workbook, and a row past the end of the data returns an empty string (**source**, 17:
`list_data_source.js` `getListCellValue`, `increaseMaxPosition`). Two consequences:

- **Rows you did not write are not loaded, and nothing warns you.** When the view grows from 3 rows to
  6 and the sheet holds 3, the cards read too low (**field**: a card showed 2 instead of 4).
- **Extra rows are free.** They return `""`, and `SUMIFS` ignores them.

So build with headroom, for example `max(rows * 2, rows + 500)`, and write at least one row even for
an empty view. `scripts/dashboard/list_sheets.py` builds the sheets and applies that rule. Re-size
when the view's grain changes (month to day multiplies the rows) and when the board is copied to a
database with more data (§8).

## 4. Traps

1. **A list with no `fieldMatching` inherits another list's filter mapping.** `_addList` copies the
   mapping already used for the same model when the list carries none (**source**, 17 and 18:
   `list_core_plugin.js`; the check is `if (!fieldMatching)`, so an empty object stops it). A list
   meant to be unfiltered ends up filtered. Write `"fieldMatching": {}` on every list.
2. **Old and new filter format.** A file with a low `odooVersion` keeps mappings in
   `globalFilters[].listFields`; `migrate4to5` moves them into `lists[*].fieldMatching` on load
   (**source**, 17, 18, 19: `o_spreadsheet/migration.js`). Use one form per file: `listFields` in an
   old-format file, `fieldMatching` in a new one. Constructing `new Model(data)` by hand in the
   browser console does not run Odoo's migration, so test by saving the record and opening it.
3. **Booleans are text on 17.** A boolean column returns the strings `"TRUE"` / `"FALSE"` on 17 and
   real booleans on 18 and 19 (**source**). A criterion written for one fails on the other, and a
   frozen or exported copy may store the other type again. Keep yes/no tests out of the sheet: put
   them in the list domain, or return text such as `'Yes'` / `'No'` from the view.
4. **Zero comes back empty.** On 17 and 18 a numeric `0` returns `""` (**source**: the default branch
   is `record[fieldName] || ""`); 19 keeps the zero. `AVERAGE` then skips those rows and reads too
   high. Compute averages as `SUM(values) / SUM(counts)` or `SUM / COUNT` of an id column.
5. **The list cache is shared.** A second model built in the page with the same list ids reads the
   cache of the open dashboard and shows wrong numbers (**field**). Test by saving and reloading.
6. **Big workbooks.** A workbook of raw records (several megabytes, a dozen lists) can crash the tab
   (**field**). Group in the view first (§5), and do not export a very large model in the page.
7. **Creating the record with its data.** On 17 Enterprise `create()` runs
   `_copy_spreadsheet_image_attachments`, which parses the stored workbook (**source**); creating with
   `spreadsheet_binary_data` in the values failed there, and creating with `spreadsheet_data` stored
   an empty sheet (**field**). Create the record bare, then write the binary once. On a record users
   have never opened this wipes nothing; on any other record see §7.
8. **Date grain.** A date filter mapped to a month column filters whole months: "10 to 20 November"
   counts all of November. If people filter by day, group the view by day. Charts by month keep
   working, because their formulas use `">="&DATE(y,m,1)` bounds, not the column's grain. Convert
   timestamps to the business timezone before casting to a date
   (`(create_date AT TIME ZONE 'UTC' AT TIME ZONE '<zone>')::date`), or records made late in the
   evening land on the next UTC day.
9. **Style and format ids are not stable.** An export keeps only the styles and formats in use and
   renumbers them, so `format: 3` in one export can be another format, or none, in the next
   (**field**). Find the id by its value (`"0.0%"`) in the current export, or add it there, each time.
10. **Scorecard number colour.** The number takes the static `textColor` of its key cell
    (**source**, 17: `keyValueStyle?.textColor`); conditional formats do not reach it. A number
    coloured by sign has no clean route on 17. Workaround (**field**): three copies of the card at
    the same position, pointing at `=IF(v=0,v,"")`, `=IF(v>0,v,"")` with a green cell, and
    `=IF(v<0,v,"")` with a red cell, the upper two with a transparent background. Only one shows a
    number. The title is drawn three times and looks slightly bold; say so in the hand-over, or use
    the baseline arrow instead (rule 6), which colours by sign natively.

## 5. Reporting views as the data source

Group in SQL so the list holds hundreds of rows, not the raw records.

- **One view per grain.** An entity view (one row per combination of the dimensions the cards cut by,
  plus a count) and a transaction view (date, buckets, count, amount) stay separate. Mixing grains in
  one view double-counts.
- **Joins are 1:1 to the grain.** A join that fans out multiplies the amounts. Put the business
  exclusions (cancelled, archived, deposits) in the `JOIN` / `WHERE` exactly as the rule is stated.
- **A count column on every view**, so cards are `SUMIFS(count, …)` and the checks below are possible.
- **Flags as text**, never booleans (§4.3).
- **No database ids in the SQL.** A stage id, an analytic account id or a company matched by its name
  is different on the next database, and the view returns wrong numbers with no error. Join on an
  XML id (`ir_model_data`), a code, or a field that carries the meaning (`is_closed`, a selection key).
- **Buckets must partition.** Every `CASE` ends in an explicit "other" bucket, and a bucket derived
  from a name (`ILIKE '%done%'`) is the fragile kind rule 7 warns about: a renamed stage moves
  silently. Prefer a stored flag or selection.

Two ways to publish a view:

| Route | How | Trade-off |
|---|---|---|
| Module model | `_auto = False` model with `init()` creating the view, fields declared, access rules in `ir.model.access.csv` | goes through review, tests and the release like any code; a change needs a deploy |
| OCA `bi_sql_editor` | a `bi.sql.view` record: validate the SQL, set field types, create the model and menu; the model is `x_bi_sql_view.<name>` and columns must start with `x_` | no deploy, changed in minutes; lives only in that database, so every environment needs the same record, and it is outside code review. The editor scans the raw text, comments included, for DDL and DML words. Do not alter a view another board reads: add a new one |

**Access.** A SQL view model has no record rules unless you write them, and no company filter. Its
only guard is the access list (or the `bi.sql.view` groups). A view that sums across companies shows
every company's figures to everyone who can read it. Decide who may read each view before publishing
it, and add a company column plus a rule where that matters (`security` owns the rule syntax).

**Patterns.**

- *Metric view.* When the cards are unrelated counts, `UNION ALL` each card's rule into
  `x_date, x_metric, x_value` and group by date and metric. One list feeds every card:
  `=SUMIFS(value, metric, "<key>")`.
- *Translating an Odoo domain into SQL.* `not in` in a domain also matches empty values, `= False`
  on a path follows the relation, and `active` rows are excluded by default. Compare each metric
  with `search_count` of the same domain.
- *Analytic revenue.* `analytic_distribution` is JSON keyed by account id, and a key can hold several
  ids (`"8,15"`): `CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution)`, split the key on
  `,`, amount `= -balance * pct / 100` for income accounts.

**Verify the view before building anything on it** (with `read_group` / `search_count` on the source
model):

- every card value for the default period, and for one other period;
- `distinct groups == rows` (no duplicate group);
- `sum(count) == number of source records` in scope.

## 6. Filters and labels

- Map date filters only to the lists that have a date column; lists without one keep
  `"fieldMatching": {}` and their cards are labelled as not filtered (rule 8).
- A selected-period cell lets chart tables follow the filter:
  `=IFERROR(VALUE(ODOO.FILTER.VALUE("Year")), YEAR(TODAY()))`. The formula looks the filter up by its
  label, so renaming the filter breaks it (`authoring-recipes.md` §4).
- Category names typed into `Calc` (buildings, teams, statuses) are fixed when the board is built. A
  new category does not appear until the table is rebuilt. Say so in the hand-over, or read the names
  from a second list.
- Never change text that a formula matches on (a `SUMIFS` criterion, a bucket key) when translating
  labels. Keep keys in one language and translate only what is displayed.
- A comparison without a pivot: a second `SUMIFS` on the previous period's bounds, used as the
  scorecard `baseline` (rule 6 still applies; only the mechanism changes).
- Card details: `"baselineDescr": " "` leaves an empty second line and makes the number smaller; a
  percent card with the count underneath uses `baseline` on a text cell with `baselineMode: "text"`;
  shares that must add up to 100% are divided by the sum of the shown parts and formatted `0.0%`,
  because whole percents round to 99.

## 7. Saving a workbook built outside the editor

This is the route for boards that live as database records. For boards shipped in a module, rule 13
and `authoring-recipes.md` §11 apply unchanged.

1. Read the `spreadsheet.revision` count for the record. Zero means nobody edited it in the editor.
2. Build the workbook.
3. **Read the count again immediately before the write.** If it changed, someone is editing: stop and
   start from their version.
4. Write `spreadsheet_binary_data` (a new board: create bare first, §4.7).

When the count is not zero, do not rebuild from a script: the write deletes every revision. Open the
board in the editor, export the live model (revisions applied), change only what was asked in that
export, and write it back, with the owner's agreement and their editor tab closed.

Open the board from the dashboard sidebar to check it. On 17 the dashboard action opened the first
board whatever id was passed (**field**).

## 8. Copying a board to another database

- Publish the same views there first, under the same technical names.
- Re-size every `DATA_*` sheet to the target's row count plus headroom (§3). `list_sheets.py
  --resize` does this for an exported workbook.
- Rebuild the name lists typed into `Calc` from the target's data (§6).
- Check group ids, menu ids and any id in a drill-down link: they belong to the source database.
- Compare every card with the target's views. A copy that opens without `#ERROR` is not a check.
- A write to a production database follows the project's approval rule like any other write.

## 9. Checks

- [ ] Every list has `"fieldMatching"` (an empty object when unfiltered) and an order with a tie-breaker.
- [ ] Every `DATA_*` sheet has headroom, and the hand-over says how many rows and when to re-size.
- [ ] No boolean criterion and no `AVERAGE` over list cells.
- [ ] Each view was compared with its source model: card values, no duplicate groups, total count.
- [ ] No database id and no name match in the SQL; every bucket has an "other".
- [ ] Who can read each view is stated; cross-company views are deliberate.
- [ ] Revision count read before the build and again before the write.
- [ ] Each date filter moved once and every card either responds or says it does not.
- [ ] The report lists rows before and after, every number compared, and the known limits (static
      name lists, date grain, headroom).
