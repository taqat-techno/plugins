# Odoo 17 Performance — review reference

Source: [Performance](https://www.odoo.com/documentation/17.0/developer/reference/backend/performance.html)

## Profile *before* optimising

Odoo ships an integrated profiler at `odoo.tools.profiler.Profiler`. Enable
it from:

- the UI: dev-mode tools → toggle *Enable profiling*; results stored as
  `ir.profile` records;
- Python: `with Profiler(): do_stuff()`.

Results render in **speedscope** (open-source flamegraph viewer) with view
modes:

- **Combined** — SQL + traces merged.
- **Combined no context** — same, ignoring execution-context frames.
- **sql (no gap)** — only SQL queries, back-to-back; good for query
  optimisation.
- **sql (density)** — SQL with timing gaps; spots Python vs SQL bottlenecks.
- **frames** — just the periodic-collector traces.

Tip: wrap suspect blocks in `ExecutionContext(label=…)` to break a hot loop
into named slices in the flamegraph.

### Collectors

| Collector | Key | Class | Notes |
|---|---|---|---|
| SQL | `sql` | `SqlCollector` | Stack + query per execute |
| Periodic | `traces_async` | `PeriodicCollector` | Sample-based, lowest overhead |
| QWeb | `qweb` | `QwebCollector` | Tracks QWeb directives |
| Sync | `traces_sync` | `SyncCollector` | Per-call traces, **heavy** |

`with self.profile():` is a shortcut inside test cases; pair with
`self.assertQueryCount(N)`.

### Profiler caveats

- Randomness: garbage collection mid-run skews numbers.
- Blocking C calls don't release the GIL — show up as huge frames; the
  profiler emits a warning.
- Cache matters: first run pays for view/asset compile.
- Profiling itself has overhead (especially the SQL collector). Measure
  again with profiler off to confirm real wins.
- Speedscope rendering is memory-heavy; bump `--limit-memory-hard` if it
  500s.

## Common Odoo perf issues at review time

### 1. N+1 reads

```python
# bad — N queries
for partner in partners:
    print(partner.country_id.name)

# good — single prefetch
partners.mapped('country_id.name')
```

Mapping over a recordset triggers a single prefetch for the whole batch.

### 2. Loop writes

```python
# bad — N SQL UPDATEs
for r in recordset:
    r.write({'state': 'done'})

# good — 1 SQL UPDATE
recordset.write({'state': 'done'})
```

Same with `unlink()`. For `create()`, pass a list of dicts:

```python
self.env['account.move'].create([{'partner_id': p.id, ...} for p in partners])
```

### 3. `search()` instead of `search_count` / `read_group`

```python
# bad
count = len(self.env['x'].search(domain))

# good
count = self.env['x'].search_count(domain)
```

```python
# bad — Python sum after pulling everything
total = sum(self.env['account.move.line'].search(domain).mapped('balance'))

# good — single SQL with GROUP BY
data = self.env['account.move.line'].read_group(
    domain, fields=['balance:sum'], groupby=[]
)
total = data[0]['balance']
```

### 4. Compute that doesn't iterate `self`

```python
# bad — only the first record receives the value
@api.depends('value')
def _compute_total(self):
    self.total = self.value * 1.2

# good
@api.depends('value')
def _compute_total(self):
    for record in self:
        record.total = record.value * 1.2
```

### 5. Incomplete `@api.depends`

A `store=True` compute that doesn't list a field it actually reads will
silently go stale. Worst class of bug — no error, just bad data.

```python
# bad — reads partner.country but doesn't depend on it
@api.depends('partner_id')
def _compute_zone(self):
    for rec in self:
        rec.zone = rec.partner_id.country_id.region_id.code

# good
@api.depends('partner_id.country_id.region_id.code')
def _compute_zone(self):
    for rec in self:
        rec.zone = rec.partner_id.country_id.region_id.code
```

### 6. Missing index on a filtered column

If you filter on a field often (e.g. `state`, `partner_id`, `date`), set
`index=True` on the field declaration:

```python
state = fields.Selection(SELECTION, index=True)
```

Add explicit indexes via `_sql_constraints` or `_sql` for composite indexes.

### 7. Over-eager `store=True`

`store=True` is a win for searchable / report fields. It costs SQL on every
write that touches a dependency. Don't store fields that are only read on a
form (the compute is fast enough).

### 8. Big `related=` chains

Each `related` adds a compute. Long chains across many records cost more
than one carefully-written compute that does a `search_read` with a join.

### 9. QWeb-side performance

- Avoid `t-foreach` over thousands of records with per-row queries.
- Use `t-set` to cache values used multiple times inside a template.
- For report templates, precompute aggregates in the report Python class.

### 10. Asset bundle bloat

Every module's `assets` declaration accumulates into the page bundles. Big
dependency trees mean large JS/CSS bundles → slow first paint.

## Database population for perf testing

`odoo-bin populate` fills a database with synthetic data:

```python
class CustomModel(models.Model):
    _inherit = "custom.some_model"
    _populate_sizes = {"small": 100, "medium": 2000, "large": 10000}
    _populate_dependencies = ["custom.some_other_model"]

    def _populate_factories(self):
        ...
```

`_populate_sizes` defaults: small=10, medium=100, large=1000.
`_populate_dependencies` declares populate order across models. Define at
least `_populate()` or `_populate_factories()`.

Use it before declaring "this code is fast" — small dev datasets hide the
problems that matter.

## Review-time shortlist

When eyeballing a module without running it:

1. Grep for `for ` near `.search(` → N+1 candidates.
2. Grep for `len(self.env[` → likely `search_count` candidate.
3. Grep for `.write(` inside `for ` → loop write.
4. Diff `@api.depends(...)` against the field accesses in the compute
   body — they should match exactly.
5. Grep for `index=True` on `state`, `date`, `partner_id`, custom FK
   fields — flag fields that are filtered in views but lack the flag.
6. Look at the manifest's `data` list — large XML files loaded on every
   upgrade slow installs.
7. Look at the `static/src/js/` size — bundled minified JS in source is
   a smell; vendored libs belong in `static/lib/`.
