# Odoo 17 → 19 deltas (review reference)

When clusters in a fleet run on different Odoo versions (some on 17, some
moving to 19), the **same rule does not always apply across both
versions**. This file lists the changes that matter at review time and the
cross-version implications.

Sources:

- v19: https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html
- v19: https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html

The corresponding v17 URLs are the ones cited in `SKILL.md`.

## TL;DR — what changes between 17 and 19

| Area | v17 | v19 |
|---|---|---|
| List view XML tag | `<tree>` | `<list>` |
| View type enum | `tree` | `list` |
| Translation primary API | `from odoo import _` then `_(...)` | `self.env._(...)` (the import is now a *local alias*) |
| Domain composition | Python lists `[('a','=',1), …]` | `Domain` class: `Domain('a','=',1) & Domain('b','=',2)` |
| `cr.commit/rollback` outside framework | Forbidden (`cr.commit`) | Forbidden (`cr.commit` AND `cr.rollback`) |
| Catching exceptions | Implicit best practice | New explicit section: "Avoid catching exceptions" |
| Savepoint cap | Not documented | 64 savepoints / transaction warning |
| `read_group()` | Public | Renamed `_read_group()` (now private; public still works but private is canonical) |
| Field aggregate attr | `group_operator='sum'` | `aggregator='sum'` |
| Selection `group_expand` | manual method | `group_expand=True` auto-expands all keys |
| `company_dependent` storage | `ir.property` | jsonb dict on the model table, `ir.default` for fallbacks |
| `_search_<field>` method | Must implement | May `return NotImplemented` to let ORM retry |
| `Char.trim` | Web client only | Web client + server-side import |
| Raw SQL helper | `self.env.cr.execute(query, params)` | Same + new `SQL(...)` wrapper and `self.env.execute_query(SQL(...))` |
| `user_has_groups(...)` | Available | Replaced in docs examples by `env.user.has_group(...)` |
| `BaseModel` module path | `odoo.models.BaseModel` | `odoo.orm.models.BaseModel` |
| Class attr order | `_sql_constraints` in "private attrs" bucket | New bucket "SQL constraints and indexes" between fields and computes |
| Example `create()` signature | `def create(self, values):` | `@api.model_create_multi` + `def create(self, vals_list):` |
| New field attrs (Html / Float) | — | `sanitize_conditional_comments`, `sanitize_output_method`, `min_display_digits` |
| Database population (`_populate*`) | Documented on perf page | Removed from the perf page (likely relocated; verify before relying on it) |
| QUnit JS unit-test section | On the testing page | Removed (web framework moved to a different test harness) |
| Module manifest (`__manifest__.py`) | Same | Same (identical doc page) |

Same-day check: the `__manifest__.py` reference page is **bit-identical**
between 17 and 19. Every rule in `references/module_manifest.md` carries
over unchanged.

---

## The substantive changes, grouped by review checklist section

### §1 Manifest hygiene — no change

`__manifest__.py` keys, license list, `auto_install` semantics,
`external_dependencies`, hooks — all identical. Apply
`references/module_manifest.md` as-is on both versions.

### §2 Module layout & file naming — no change

Canonical tree, file-naming rules, `[a-z0-9_]` filename constraint,
deprecation of `main.py` — all identical.

### §3 XML conventions — **breaking rename**

- `<tree>` → `<list>` everywhere a list view is declared.
- View type enum in XML IDs: `<model>_view_<list|tree|kanban|form|search|...>`.
  In v19 use `list`; in v17 use `tree`.
- Inheriting-view rules are unchanged (same XML id, `.inherit.<details>` in
  `name`, `primary` for new layouts).

**Mixed-cluster implication**: an XML file shared between a v17 and a v19
cluster needs preprocessing (or two copies). A `<tree>` tag in a v19 view
will silently render nothing useful. Conversely, `<list>` in a v17 view is
an unknown element.

Practically: every cluster on v17 keeps `<tree>`. When a cluster migrates
to v19, every `<tree>` in its custom modules must be renamed to `<list>`.
Add this to the migration checklist; flag any cross-version shared view
file as BLOCKER until split.

### §4 Python style & idioms — three real changes

1. **`cr.rollback()` joins `cr.commit()`** in the forbidden list outside
   framework code. v17 only forbade `cr.commit()` explicitly.
2. **New section: "Avoid catching exceptions"**. Be specific about which
   exception you catch. Narrow the `try:` scope. If you must handle
   framework exceptions, use a savepoint:

   ```python
   try:
       with self.env.cr.savepoint():
           do_stuff()
   except SpecificError:
       ...
   ```

   Postgres slows down beyond 64 savepoints in one transaction; if you
   loop with a savepoint, cap the batch or move the work into a
   scheduled action.

3. **Scheduled actions run in their own transactions.** You can commit /
   rollback directly inside a `ir.cron` job to report progress — the
   global "never commit" rule still holds for normal RPC paths.

Apply all three to v17 review too — they were good practice already, the
v19 docs just made them explicit.

### §5 Symbols, conventions, model attribute order — one structural change

v19 reshuffles the class attribute order:

1. Private attrs (`_name`, `_description`, `_inherit`, `_order`, …)
   — **without** `_sql_constraints`
2. Default methods + `default_get`
3. Field declarations
4. **SQL constraints and indexes** (new bucket — was in #1)
5. Compute / inverse / search methods (in field-declaration order)
6. Selection methods
7. `@api.constrains` + `@api.onchange`
8. CRUD overrides
9. `action_*` methods
10. Other business methods

When reviewing a model that targets v19, expect `_sql_constraints` to sit
*between* fields and computes, not at the top with the other underscores.
On v17 keep it in the original "private attrs" group. Don't grade either
choice as a violation against the other version's convention.

### §6 ORM patterns — several renames and one storage change

#### `read_group()` → `_read_group()`

v17 documents `read_group()` as a public method. v19 documents
`_read_group()` (private, leading underscore). Both still work, but if
you're writing v19-native code, call the private form. Don't rewrite v17
code just to match.

#### `group_operator` → `aggregator`

The `Float` / `Integer` / `Monetary` field attribute that controlled
group aggregation is renamed:

```python
# v17
amount = fields.Monetary(group_operator='sum')

# v19
amount = fields.Monetary(aggregator='sum')
```

If you support both versions, you cannot share the field definition
unless you wrap it. Practical advice: keep separate field declarations
in version-specific modules.

#### `_search_<field>` may return `NotImplemented`

In v19, a search method can `return NotImplemented` to tell the ORM to
try a semantically equivalent operator instead. Useful for "I only handle
`in`/`like`; let the ORM rewrite `=` to `in` and call me again":

```python
def _search_partner_ref(self, operator, value):
    if operator not in ('in', 'like'):
        return NotImplemented
    return Domain('partner_id.ref', operator, value)
```

v17 search methods must implement every operator they want to support;
returning `NotImplemented` does nothing.

#### `Domain` class (`from odoo.fields import Domain`)

v19 introduces a `Domain` object that wraps the list domain and supports
safe boolean composition. This is the recommended way to build domains
that combine user input with security-sensitive filters:

```python
# v19 good
domain = Domain(user_supplied_domain) & Domain('user_id', '=', self.env.uid)
self.search(domain)

# v17 (no Domain class) — still safe IF you control list construction
domain = user_supplied_domain + [('user_id', '=', self.env.uid)]
self.search(domain)
```

The v19 docs flag the list-concatenation pattern as a security risk
(domain injection via `|` operator), so on v19, missing-`Domain` usage in
security-sensitive code is MAJOR. On v17, use AND-via-concatenation but
**always** add the security predicate at the end (where it can't be
overridden by a user-supplied `|`).

#### `company_dependent` field storage

v17: values stored as `ir.property` records, looked up by company.
v19: values stored as a `jsonb` column on the model table, keyed by
company id; fallbacks come from `ir.default`.

**Migration implication**: upgrading a model with `company_dependent`
fields from v17 → v19 requires a data migration step. Don't assume the
existing `ir.property` rows survive automatically. Add a verification
step to any 17→19 upgrade plan.

### §7 Security — `user_has_groups()` deprecation in examples

The security page in v17 uses `self.user_has_groups('base.manager')` in
its "unsafe public methods" example. v19 uses
`self.env.user.has_group('base.manager')`. The substance of the rule is
identical; only the API surface changed.

Both forms still work at runtime in v19, but new code should use
`env.user.has_group(...)`. Flag the older form as MINOR drift in v19
code, no finding in v17 code.

### §7 Security — `SQL` wrapper for raw queries (new in v19)

v19 ships an `SQL` query template wrapper:

```python
from odoo.tools.sql import SQL

# v19
self.env.cr.execute(SQL(
    "SELECT DISTINCT child_id FROM account_account_consol_rel "
    "WHERE parent_id IN %s",
    tuple(ids),
))

# also v19 (preferred for SELECT-and-fetch):
rows = self.env.execute_query(SQL(
    "SELECT id FROM auction_lots WHERE auction_id IN %s "
    "AND state = %s AND obj_price > 0",
    tuple(ids), 'draft',
))
```

It's still parameterised (psycopg2 does the quoting), but `SQL` composes
multiple fragments safely and is what the docs recommend for any
ORM-bypass case. On v17, stick with `cr.execute(sql, params)`.

### §7 Security — Domain injection

(Already covered under §6: `Domain` class.)

### §8 Performance — `_populate*` API gone from the page

The v17 perf page has a full "Database population" section documenting
`_populate_sizes`, `_populate_dependencies`, `_populate()`,
`_populate_factories()` and `odoo-bin populate`. **The v19 perf page does
not.**

The CLI command and the underlying mechanism are likely still present
(this is the docs page being trimmed, not the feature being removed) —
but rely on it only after confirming via the v19 source tree. Until then,
don't *recommend* `_populate*` in a v19-targeted review.

The v19 profiler section is otherwise the same: `Profiler`,
`SqlCollector`, `PeriodicCollector`, `QwebCollector`, `SyncCollector` are
all still documented.

### §9 Views — list/tree (covered under §3)

The only review-level view change is the tag rename. Inherited-view rules
and primary-view rules are unchanged.

### §10 JS / Owl / assets — QUnit replaced

v17 documents the QUnit-based JS test harness on the testing page. v19
removes that section. Modern Odoo's frontend test harness has moved (the
v19 web framework reference is the place to look for the current
harness — verify against the source tree before recommending a specific
test pattern).

In most codebases the practical impact is small: most custom tests are
Python-side. Any JS tests in a cluster need their harness check during the
v17→v19 migration.

### §11 Testing — minor doc additions

- Tour helpers gained a `step_delay` argument and a `debug=assets` query
  param for stop-on-exception. Useful but doesn't change review criteria.
- Test base classes (`TransactionCase`, `SingleTransactionCase`,
  `HttpCase`) are documented the same way.
- `ref()` / `browse_ref()` / `assertQueryCount()` / `self.profile()` are
  unchanged.

### §12 Translation — primary API change

```python
# v17 (primary form)
from odoo import _
raise UserError(_('Record %s cannot be modified', record))

# v19 (primary form per the docs)
raise UserError(self.env._('Record %s cannot be modified', record))

# v19 (still works, kept as a local alias)
_ = self.env._
raise UserError(_('Record %s cannot be modified', record))
```

The `from odoo import _` form is still available in v19 for
backward compatibility; the docs now showcase `self.env._` as the
canonical entry point.

**Mixed-cluster implication**: in shared modules that target both v17
and v19, keep `from odoo import _` — it's the lowest common denominator.
A v19-only module should prefer `self.env._`.

Rules from §12 of `SKILL.md` (only literal strings, named placeholders,
no concatenation, no f-strings, no `_(...)` around field values) hold on
both versions unchanged.

---

## How to use this file during a review

1. Identify the **target Odoo version** of the module under review.
2. Walk the 12-section checklist in `SKILL.md` as the *base*.
3. For each section, glance at the matching subsection here:
   - If the rule is unchanged, no action.
   - If the rule is v19-only or v17-only, apply only on that version.
   - If the rule renames an API, flag the wrong-version name as MINOR
     unless it's user-visible.
   - For breaking renames (`<tree>` / `<list>`, `Domain` injection
     pattern), grade as MAJOR / BLOCKER per the severity model.
4. When a module is **shared across versions**, the lowest-common-
   denominator wins:
   - `<tree>` is invalid on v19 → split the file.
   - `group_operator=` is invalid on v19 → wrap the field declaration.
   - `from odoo import _` is fine on both → use it.
   - List-domain composition with a security predicate is fine on both
     **only** if the predicate is appended last and the input list is
     trusted/normalised.

## Mixed-cluster checklist

For a fleet where one cluster may move to v19 while others stay on v17:

- [ ] Every shared module declares which version(s) it targets in the
      manifest's `description` or a `README.md`.
- [ ] CI runs the test suite on **both** versions.
- [ ] All `<tree>` tags are flagged before a cluster is moved to v19.
- [ ] `group_operator=` is grep'd before a cluster is moved to v19.
- [ ] `company_dependent` fields are reviewed for migration impact
      before the v17→v19 cutover.
- [ ] No code uses `self.env._` in a v17-target module.
- [ ] No code uses `from odoo.fields import Domain` in a v17-target
      module (it doesn't exist there).
- [ ] Tour tests are revalidated against the v19 web framework harness.

## Source-of-truth fallback

Where a rule conflicts between this file and the live docs, the live
docs win. When in doubt, open the v17 page and the v19 page side-by-side
and diff the relevant section. The reviewer's job is to apply rules
correctly, not to memorise them.
