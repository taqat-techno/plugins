# Odoo 17 ORM patterns — review reference

Source: [ORM API](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html)

## Model base classes

| Base class | Use when |
|---|---|
| `models.Model` | Regular database-persisted records. Default. |
| `models.TransientModel` | Wizards / temporary data. Stored but vacuumed periodically. |
| `models.AbstractModel` | Shared logic / mixins meant to be inherited without their own table. |

Set `_register = False` on a class that should not be instantiated.

## Three inheritance modes

### Classic — extend in place

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    note = fields.Char()
```

No `_name`. Adds fields/methods to the existing model. Most common.

### Prototypal — new model derived from another

```python
class CustomOrder(models.Model):
    _name = 'custom.order'
    _inherit = 'sale.order'   # copies fields/methods, but separate table
```

`_name` differs from `_inherit`. New model copies fields/methods from
`sale.order` at class build time. Use sparingly — it diverges quickly.

### Delegation (`_inherits`)

```python
class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherits = {'product.product': 'product_id'}
    product_id = fields.Many2one('product.product', required=True,
                                 ondelete='cascade')
```

Composition: the new model exposes all fields of the parent but stores none of
them. The parent record is reached via the declared Many2one. If multiple
`_inherits` entries declare the same field name, the last one in the dict wins.

### Order inside an `_inherit` list is C3 linearization

When `_inherit` is a **list**, the entries are bases in MRO order, so a wrong
order is a `TypeError: Cannot create a consistent method resolution order`
(or a mixin whose methods silently never run), not a style issue.

- **A mixin that itself subclasses something the base model already carries
  must come FIRST.** `rating.mixin` subclasses `mail.thread`; a model that
  already carries `mail.thread` early in its own bases can only linearize if
  `rating.mixin` precedes it. Same shape for any mixin layered on a mixin.
- **Website mixins go `seo` → `published` → `searchable`**, matching the order
  they build on each other.
- **Standalone mixins with no shared ancestry go last** — `image.mixin` is the
  usual one.

Review note: a change that only **reorders** an `_inherit` list is a pure
linearization fix. It adds no sink, no validator, no permission and no data
flow, so it does not need a security review — reorder it and move on.

## Key `_` class attributes

| Attr | Default | Purpose |
|---|---|---|
| `_name` | — | Required dot-name in module namespace |
| `_description` | None | Human-readable label (also for `ir.model`) |
| `_inherit` | () | str or list of parent models |
| `_inherits` | {} | Delegation map |
| `_auto` | True for Model | If False, no DB table is auto-created |
| `_log_access` | follows `_auto` | Adds `create_uid/write_uid/...` |
| `_table` | None | Override table name |
| `_sql_constraints` | [] | List of `(name, sql_def, message)` |
| `_rec_name` | `'name'` | Field used to render records as text |
| `_order` | `'id'` | Default ordering |
| `_check_company_auto` | False | Auto-validate `check_company=True` fields |
| `_parent_name` | `'parent_id'` | Hierarchy field |
| `_parent_store` | False | Maintain a `parent_path` for fast hierarchical queries |

## Fields — the rules that matter at review time

### Field declaration

```python
total = fields.Float(compute='_compute_total', store=True)

@api.depends('value', 'tax')
def _compute_total(self):
    for record in self:
        record.total = record.value + record.value * record.tax
```

- A field and a method **cannot share a name** — the second silently
  overwrites the first.
- `string="..."` overrides the auto-capitalized label.
- `default=` accepts a value or a callable.

### Computed fields

- `@api.depends(...)` must list **every** field the compute reads. Dotted
  paths are allowed: `@api.depends('line_ids.value')`.
- A compute method **must iterate `self`**: `for record in self:`. If it
  assigns `self.field = …` directly, it only works on a singleton; on a
  longer recordset, only one record gets the value (silent bug).
- Without `store=True` the field is computed on every access — fine for
  display, problematic for domains, exports, reports, downstream stored
  computes. Add `store=True` when needed.
- `store=True` + `@api.depends` enables searching automatically; with
  `store=False`, add `search='_search_<field>'` to make it searchable.
- `compute_sudo`: default is `True` if stored, `False` if non-stored. Flip
  only with a written justification — flipping to `True` on a non-stored
  field is a common ACL-bypass hole.
- Recursive computes (depends on `parent_id.X`) **must** set
  `recursive=True`, otherwise recomputation order is undefined.

### Related fields

`related='a.b.c'` is sugar for a compute. Defaults: not stored, not copied,
readonly, computed in superuser mode.

- Add `store=True` to persist.
- Add `depends=[...]` to narrow what triggers recomputation.
- You **cannot chain** `One2many` / `Many2many` in a `related`. Going through
  a Many2one is fine. The doc spells out which combinations are legal.

### Field suffix conventions

- `Many2one` → suffix `_id` (e.g. `partner_id`).
- `One2many`, `Many2many` → suffix `_ids` (e.g. `sale_order_line_ids`).

Mixing these up is a real review trigger because Odoo and many third-party
modules grep on them.

## API decorators

| Decorator | Purpose |
|---|---|
| `@api.depends('a', 'b.c')` | Declare dependencies of a compute method |
| `@api.depends_context('uid')` | Declare *context* deps for a compute |
| `@api.constrains('a', 'b')` | Python constraint, runs on create/write |
| `@api.onchange('a')` | Form-view side effect — does NOT run on save |
| `@api.model` | Class-level method (no records bound to `self`) |
| `@api.model_create_multi` | `create()` receives a list of dicts |
| `@api.returns('model')` | Return wrapped recordset of `model` |

`@api.onchange` is a UX helper only; never put validation logic there alone —
mirror it in `@api.constrains`.

## Context, sudo, with_user, with_company

```python
records.with_context(new_dict)            # replace context entirely
records.with_context(**extra)             # merge / override keys
records.sudo()                            # run as superuser
records.sudo(self.env.ref('base.user_demo'))   # as a specific user (deprecated form)
records.with_user(other_user)             # preferred way to change user
records.with_company(company)             # change current company
```

Rules:

- The context is a `frozendict`; mutating it is impossible. Always use the
  helpers above.
- `sudo()` bypasses **ACL and record rules**. Don't reach for it to silence
  an `AccessError`. Use it only when the operation legitimately needs
  superuser rights and the access is independent of the caller's identity.
- `with_user()` is the safe way to "act as another user" while keeping
  proper ACL checks.
- `with_company()` is required when writing fields with `check_company=True`
  in a multi-company context.

## CRUD batching

The recordset is the unit of work. Patterns:

```python
# good — single SQL UPDATE
recordset.write({'state': 'done'})

# bad — N updates
for r in recordset:
    r.write({'state': 'done'})

# good — single SQL INSERT (batch create)
self.env['account.move'].create([
    {'partner_id': p.id, ...} for p in partners
])

# bad — N inserts
for p in partners:
    self.env['account.move'].create({'partner_id': p.id, ...})
```

Same pattern for `unlink`: pass the whole recordset to a single `unlink()`
call.

## ORM bypass — when NOT to use `cr.execute()`

> "You should never use the database cursor directly when the ORM can do the
> same thing!"

Bypassing the ORM skips:
- ACL and record rules
- field cache invalidation
- computed-field recomputation
- `active` filtering
- translations

Replace patterns like:

```python
# very wrong (SQL injection + unreadable + ORM bypass)
self.env.cr.execute(
    'SELECT id FROM auction_lots WHERE auction_id IN ('
    + ','.join(map(str, ids))
    + ') AND state=%s AND obj_price > 0', ('draft',))
ids = [x[0] for x in self.env.cr.fetchall()]

# still wrong (ORM bypass, even with parameterised query)
self.env.cr.execute(
    'SELECT id FROM auction_lots WHERE auction_id IN %s '
    'AND state=%s AND obj_price > 0', (tuple(ids), 'draft'))
ids = [x[0] for x in self.env.cr.fetchall()]

# right
lots = self.env['auction.lots'].search([
    ('auction_id', 'in', ids),
    ('state', '=', 'draft'),
    ('obj_price', '>', 0),
])
```

Direct SQL is acceptable for:
- Performance-critical aggregations (`read_group` first; SQL last resort).
- Reading from columns the ORM doesn't model (e.g. raw DB views).
- Schema introspection / migration scripts.

In every direct-SQL case, **parameterise** (`%s` placeholders) and wrap in
`self.env.cr.execute(query, params)`.

## Useful recordset helpers

| Method | When |
|---|---|
| `mapped('field')` | Get a list/recordset of a sub-field across records |
| `filtered(lambda r: …)` | Filter in memory, no SQL |
| `filtered_domain([...])` | Filter using domain syntax |
| `sorted(key=…)` | Order in memory |
| `ensure_one()` | Assert singleton before `self.x = …` |
| `exists()` | Drop deleted ids from a recordset |
| `browse([ids])` | Cheap, no SQL — just builds the recordset |
| `read_group([...], …)` | Group + aggregate, single SQL |
| `name_search(name, …)` | Used by Many2one widgets |
| `search_count([...])` | Use instead of `len(search(...))` |
| `search_read([...])` | One round-trip vs `search()` + `read()` |

## Search domains

Domain operators include `in`, `not in`, `=`, `!=`, `like`, `ilike`,
`=like`, `=ilike`, `child_of`, `parent_of`. Logical connectives `&`, `|`,
`!` are prefix.

```python
domain = ['|', ('a', '=', 1), '&', ('b', '=', 2), ('c', '=', 3)]
```

Prefer Python-list domains over string domains.

## ondelete

For `Many2one` fields:

| ondelete | Behaviour on parent delete |
|---|---|
| `'set null'` (default) | NULL the FK |
| `'restrict'` | Block delete if any child references it |
| `'cascade'` | Delete the child too |

For `One2many` deletes on the comodel via Command tuples, the inverse field's
`ondelete='cascade'` triggers child removal.

### A stored related `Many2one` carries its own `ondelete`

`store=True` on a `related=` `Many2one` materializes a **real FK column**
with a real `ondelete`. If that `ondelete` is `'restrict'` (or otherwise
conflicts with the source relation's intent), the referenced record becomes
**undeletable** through this mirror column — Postgres blocks the delete on
the stored FK even though the field is "only a copy." Symptoms: a user
can't delete an apparently unrelated master record; the error names a table
that merely mirrors the relation. Set the stored related M2o's `ondelete`
to match the semantics you actually want (usually `'set null'` or
`'cascade'`), or don't store it.

**The default `'set null'` is the trap when the mirror points *up the same
ownership chain* as a cascading FK.** Take a child row carrying both
`version_id` → parent-history with `ondelete='cascade'` and a stored
`related='version_id.owner_id'` M2o with no explicit `ondelete` (so: SET
NULL). Deleting the owner fires **both rules in one statement**: the SET NULL
issues `UPDATE … SET owner_id = NULL`, and that update re-validates **every**
FK on the row — including `version_id`, whose target is being cascade-deleted
in the same statement. Postgres reports
`insert or update on … violates foreign key constraint …_version_id_fkey`,
i.e. an INSERT/UPDATE error *during a DELETE*, which is baffling until you see
the two conflicting delete rules. Any owner with history becomes undeletable.

Rule: a stored related M2o that points "up" the same ownership chain as a
cascading FK must **also** be `ondelete='cascade'`.

Diagnose from the **database**, not from Python — the field definition tells
you what was intended, `pg_constraint` tells you what exists:

```sql
SELECT conname, confdeltype       -- 'a' no action, 'r' restrict, 'c' cascade, 'n' set null
FROM pg_constraint
WHERE conrelid = '<child_table>'::regclass AND contype = 'f';
```

Odoo recreates the FK with the new delete rule on `-u` (`confdeltype` flips to
`c`), so the fix is a declaration change plus an upgrade, not a manual DDL.

## `_sql_constraints`

```python
_sql_constraints = [
    ('email_uniq', 'unique(email)', 'Email already used!'),
]
```

DB-level constraints are stricter than Python `@api.constrains` and survive
RPC bypass. Prefer SQL constraints for uniqueness and simple invariants.

> **Odoo 19**: `_sql_constraints` is replaced by `models.Constraint(...)` /
> `models.UniqueIndex(...)` objects declared as class attributes (the tuple
> list still loads). See `references/v19_deltas.md`.

A `UNIQUE` whose column list includes a **nullable** column stops
deduplicating for exactly the rows where that column is NULL (Postgres treats
NULLs as distinct) — the constraint does not error, it just stops being a
constraint. The decision to replace it with a partial unique index belongs to
the **multi-tenancy-isolation** skill; the declaration syntax is here and in
`references/v19_deltas.md`.

### `@api.constrains` is not concurrency-safe for uniqueness

A Python `@api.constrains` that enforces uniqueness by `search()`-ing for a
duplicate has a **race window**: two concurrent transactions each run the
search, each sees no duplicate, and **both commit** — the constraint passes
in both and you end up with two rows that violate it. `@api.constrains`
runs inside the transaction *before* commit with no cross-transaction lock,
so it cannot see an uncommitted peer.

Enforce uniqueness at the **database** level instead — a `unique(...)`
`_sql_constraints` entry (v17) or a `models.UniqueIndex` (v19). Postgres
takes the lock and rejects the second committer with an `IntegrityError`,
which Odoo surfaces as the constraint's message. Keep an `@api.constrains`
only for the friendly early message or for rules a single `UNIQUE` index
can't express — never as the sole guarantee.

### Cross-table (cross-model) uniqueness

A `UNIQUE` index only spans **one table**. When a value must be unique
across several models/tables (e.g. a reference code shared by two unrelated
models, or a normalized email across partners *and* leads), no single-table
constraint can express it. Options, in order of robustness:

- A dedicated **registry model** with the normalized key as its own
  `UNIQUE` column; every writer `create()`s/`unlink()`s its registry row in
  the same transaction, so the DB enforces global uniqueness.
- A Postgres **trigger** / `EXCLUDE` constraint on a shared table.

A Python-only cross-model `@api.constrains` has the same race as above and
additionally can't see rows it doesn't `search()` — it is not a guarantee.

## Integrity semantics the ORM does not enforce

### A relational field's `domain=` is not a write constraint

The `domain=` on a `Many2one` / `Many2many` is a **UI / search descriptor**:
it filters what the dropdown offers and what the search widget proposes. It
is **not** validated on write. A value set by RPC, by data import, by a
compute, or by any `write()`/`create()` that supplies an id outside the
domain is stored **without error**. If the domain expresses a real
invariant (e.g. "the partner must be a company"), you must **also** enforce
it in `@api.constrains` (or a DB constraint) — the `domain=` alone protects
nothing at the data layer.

The mechanism is that nothing ever reads it on the write path: `create()`,
`write()` and `_validate_fields()` never consult a field's `domain=`, so
there is no check to bypass and no flag that turns one on. A `domain=`
supplied as a **string** is weaker still — the server discards it, so it
does not even filter for a caller that isn't a UI widget.

Integrity that actually holds is DDL: `models.Constraint` /
`models.UniqueIndex` (v19) or a `_sql_constraints` entry (v17) for
invariants and uniqueness, `required=True` for the NOT NULL, and the
`Many2one`'s `ondelete` for referential behaviour. Everything above that
layer — `domain=`, `@api.onchange`, `@api.constrains` — is a message, not a
guarantee.

### Import binds relationals by identity, and bypasses rules

When importing (CSV / `load()`), a relational column can be given three ways,
and the identity semantics differ:

- `field/id` — match by **external ID** (`ir.model.data` xmlid).
- `field/.id` — match by **database id**.
- bare `field` — match by **display name** via `name_search`.

`field/id` and `field/.id` resolve the record **directly by identity**,
which **bypasses `ir.rule` and `active_test`** — the import can link to
archived (`active=False`) records and to records outside the importing
user's record-rule domain. A bare display-name column instead goes through
`name_search` (which *does* apply rules + `active_test`), but on a
**duplicate name it logs a warning and silently binds the first match** —
a quiet data-corruption path. Prefer `/id` for deterministic imports, and
never rely on display-name matching where names aren't unique.

## Concurrency — a lost write race the framework's retry does not catch

Odoo runs each request transaction at **REPEATABLE READ** (`odoo/sql_db.py`).
When two requests write the same row, the loser's `UPDATE` raises a Postgres
`SerializationFailure`. On its own that is harmless: `service/model.py` wraps
the request in `retrying()`, whose
`except (IntegrityError, OperationalError, ConcurrencyError)` clause replays
the whole request.

What breaks is *where* the exception fires. Raised **deep inside a `write()`
override that has already flushed other statements**, it aborts the
transaction while further statements are still queued behind it. Those
statements do not raise `SerializationFailure` — they raise
`InFailedSqlTransaction`, which is a **`psycopg2.InternalError`, not an
`OperationalError`**. It therefore matches nothing in the retry clause, is
never retried, and arrives in the browser as a raw Odoo traceback. Two users
approving the same record at the same moment get a 500, not "someone else
decided first".

The fix is to move the collision **ahead of every write**:

1. Take a `SELECT … FOR UPDATE` on the contended rows as the **first**
   statement of the operation. Nothing has flushed yet, so the loser fails
   cleanly as a `SerializationFailure` that `retrying()` already handles.
2. **Re-check decidability after acquiring the lock**, not before. The
   replayed request must observe the winner's outcome and refuse — otherwise
   the retry cheerfully produces a second decision on an already-decided
   record.
3. Return a **business error** from that refusal path: a stable error code
   and an HTTP 409, not an exception.

**Do not catch DB exceptions in the controller.** By the time one reaches
that layer the transaction is already aborted, so building and returning a
payload fails again at the dispatcher's own flush — recreating the very 500
the handler was added to prevent. The race belongs to the model layer,
before the first write.

### A second cursor that commits mid-request collides with the request itself

The same REPEATABLE READ semantics turn a *single* request into a concurrency
bug the moment it opens its own cursor. Writing a diagnostic / audit row on
`self.env.registry.cursor()` and committing it inline, while the request
transaction is still open, makes the request's **next flush to that row** fail
with
`psycopg2.errors.SerializationFailure: could not serialize access due to
concurrent update`. Nothing in the code looks concurrent — both writers are
the same request.

The retry loop then converts a transient into a permanent failure.
`service/model.py` retries `SerializationFailure` up to five times, but each
retry re-runs the handler, which re-opens the separate cursor, re-commits, and
re-collides. All five attempts burn and the operator gets a raw psycopg2
traceback. A "self-healing" retry can be the thing that guarantees the failure.

`cr.postrollback` is the right hook but is **not sufficient on its own**:

- `commit()` **clears** the postrollback queue; `rollback()` runs it *after*
  `_cnx.rollback()`.
- So any caller that **swallows** the exception (`except: return notification`
  — a connection-test button is the classic one) commits, and the queued
  callback is silently discarded.
- Durability across both exits therefore needs an ordinary **in-transaction
  write** *plus* a postrollback callback. The two paths are mutually exclusive
  by construction, so the row is never written twice.

Two follow-on rules:

- **Bind nothing from `self` into a postrollback closure.** Its cursor is dead
  by the time the callback runs. Capture `registry`, `_name` and `id` as plain
  values and rebuild the Environment inside the callback.
- **Drain the queue in test teardown.** `TestCursor.rollback()` also runs
  postrollback, and `TransactionCase` tears down by rolling back — so a test
  that leaves a callback queued fires it at teardown, opens a real cursor and
  **commits residue into the test database**. Clear it explicitly:

```python
def tearDown(self):
    self.env.cr.postrollback.clear()
    super().tearDown()
```

One testing trap sits on top of this: `assertRaises` **discards writes made
before the raise**. `BaseCase._assertRaises` opens `self.env.cr.savepoint()`
and rolls it back when the expected exception fires, so a test asserting "the
failure state was staged in the caller's transaction, then it raised" reads
back the pre-write value and fails in a way that looks exactly like a broken
fix. Whenever the assertion is about state written *before* the raise, use a
bare `try` / `except` / `else: self.fail(...)` instead.

Pin such a fix by asserting the checkable property directly — *no independent
cursor is opened while the caller is live* (spy on `Registry.cursor`) — rather
than the symptom, which only appears under a race.

## Framework defaults that look like bugs

Each of these produces a symptom indistinguishable from a defect, and each is
the framework behaving as documented. Recognise them before opening an
investigation.

### A stored compute does not go through `write()`

Recomputation writes through the ORM's internal `_write()`, so a hook layered
on `write()` **never fires** for it. A derivation keyed on `SomeModel.write()`
therefore stays stale forever while the stored compute it depends on updates
correctly on every change — the counters are right, the thing derived from
them is frozen. A write hook cannot observe a stored compute; hook the compute
(or add the derived value to its `@api.depends` chain) instead.

The same asymmetry cuts the other way for security: because recompute goes
through `_write()`, dropping a key in `create()`/`write()` overrides blocks
direct writes without blocking legitimate recomputation.

### Work enqueued to a queue nothing drains looks like success

A button that enqueues a job returns cleanly and the UI reports success even
when the job's only executor is a cron shipping `active=False`. Jobs sit
`queued` for days with no error anywhere. Prefer synchronous recomputation in
the same transaction unless there is a proven reason not to — and if a queue
stays, prove something drains it **in that environment**, not in principle.

### `search()` hides inactive records, so an empty result IS the answer

`active_test` is on by default. Searching for a cron, a rule, or a record that
returns nothing is frequently the **confirmation that it is archived**, not
evidence that it is missing — and "missing" leads to recreating something that
already exists. Read with `.with_context(active_test=False)` before reporting
anything absent.

### `noupdate="1"` freezes shipped data across a rename

A record loaded from a `noupdate="1"` block is never re-imported on upgrade.
Rename the model behind an `ir.sequence` and the shipped sequence row keeps its
**pre-rename `code`**, so every reference rendering through it comes out as the
fallback (`/`) on any database created before the rename — while a fresh
database is fine, which makes it look environment-specific. Renaming a model
means fixing the sequence row and backfilling existing references in a
migration. The same flag that protects your data from being overwritten is what
strands it here; `noupdate="0"` has the opposite failure (seeds re-imported and
user edits wiped on every upgrade).

### Under `env.su`, mixin stamping neither happens nor is refused

A tenancy/ownership mixin that stamps its anchor from the acting user's
membership in `create()` has nothing to read in superuser mode. Seeding through
`odoo-bin shell` therefore **stamps nothing and refuses nothing** — the records
are created successfully and silently orphaned. Pass the anchor explicitly on
every owned model when seeding as superuser.

## Modeling traps

### Fixed shallow taxonomy ≠ a `_parent_store` tree

For a **fixed, shallow** classification (a known 2–3 level scheme like
Category → Subcategory), do **not** model it as one self-referential
`_parent_store` tree "capped" at N levels. `_parent_store` is for
arbitrary-depth hierarchies: it carries `parent_path` maintenance cost and
nothing stops data (or a future writer) from nesting deeper or creating a
cycle. Model each level as its **own model** with a `Many2one` to the level
above, and enforce **parent-scoped uniqueness** (`unique(name, parent_id)`).
When callers just want a flat "parent" label, expose it as a **computed
non-stored** field rather than a stored tree. This gives real per-level
constraints and makes an illegal depth unrepresentable.

### A stored computed `Selection` must declare every value it writes

A `fields.Selection` with a static `selection=[...]` list that is also
`compute=`d (`store=True`): if the compute assigns a key **not present** in
`selection`, Odoo raises `ValueError` at **runtime** (on write) — it is not
a silent no-op. Every value the compute can produce must appear in the
`selection` list. If the valid set is dynamic, use a `selection='_method'`
callable instead of a static list.

## Common ORM anti-patterns (flag during review)

1. **`self.env['x'].search(...)` inside a loop** → pull outside, build a dict
   keyed by id.
2. **Reading a field in a loop on a recordset** → use `.mapped('field')` to
   prefetch.
3. **Writing inside a loop** → batch via single `write` on the whole
   recordset.
4. **`compute=` without `@api.depends`** → silent staleness.
5. **`compute=` writing `self.field = …` without `for record in self:`** →
   only the first record gets the value.
6. **`store=True` compute without `@api.depends` listing every read** →
   silent staleness; very hard to debug.
7. **`related=` chaining through `One2many`/`Many2many`** → unsupported; values
   will be wrong.
8. **`sudo()` to silence an ACL error** → security hole.
9. **Direct SQL where the ORM works** → see ORM bypass above.
10. **`@api.onchange` carrying validation without `@api.constrains` mirror**
    → constraint is bypassed on import / RPC.
11. **Mutating `self.env.context`** → context is frozen, the mutation is
    silently lost.
12. **`@api.depends` listing fields the method doesn't read** → wasted
    recomputation.
13. **`@api.constrains` as the only uniqueness guard** → racy; two txns
    both pass and commit. Use a DB `UNIQUE` (see `_sql_constraints`).
14. **Relying on a relational `domain=` to enforce a value** → not checked
    on write; mirror it in `@api.constrains`.
15. **A stored computed `Selection` writing an undeclared key** → runtime
    `ValueError`, not a no-op.
16. **A "capped" `_parent_store` tree for a fixed shallow taxonomy** →
    model separate levels + parent-scoped uniqueness instead.
17. **Deciding a contended record without a `SELECT … FOR UPDATE` taken
    before the first write** → the loser's `SerializationFailure` fires
    mid-`write()` and degrades into an unretried `InFailedSqlTransaction`,
    i.e. a 500 instead of a retry.
18. **Catching DB exceptions in a controller** → the transaction is already
    aborted there, so returning a payload fails again at the dispatcher's
    flush and reproduces the 500.
19. **Opening `registry.cursor()` and committing it while the request
    transaction is still live** → under REPEATABLE READ the request's own next
    flush to that row raises `SerializationFailure`, and every retry re-commits
    and re-collides. Write in-transaction **plus** a `postrollback` callback.
20. **A `postrollback` closure capturing `self` (or any recordset/env)** → its
    cursor is dead when the callback runs; capture `registry`, `_name`, `id`
    and rebuild the Environment. Clear the queue in `tearDown`, or the
    callback commits residue into the test database.
