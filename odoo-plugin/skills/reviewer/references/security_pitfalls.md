# Odoo 17 Security — review reference

Source: [Security in Odoo](https://www.odoo.com/documentation/17.0/developer/reference/backend/security.html)

## The three security layers

| Layer | Backed by | Granularity |
|---|---|---|
| Access rights | `ir.model.access` | Per model × group × CRUD flag |
| Record rules | `ir.rule` | Per record (domain) × group × CRUD flag |
| Field access | Field `groups=` attribute | Per field × group |

A user's accesses are the **union** of accesses granted by their groups.

## `ir.model.access` (access rights)

Every new model **must** have at least one row in `ir.model.access.csv`.
Without it the model is effectively invisible — including to `self.env.ref()`
in views that hide menu items.

Fields:

- `name` — describes the ACL (free text).
- `model_id:id` — the model XML id (e.g. `model_sale_order`).
- `group_id:id` — the group XML id. **Empty group_id** = every user
  (including portal / public). Be careful.
- `perm_read`, `perm_write`, `perm_create`, `perm_unlink` — 0 or 1. Unset
  by default. Access is *additive*: union of all matching ACLs.

## `ir.rule` (record rules)

Filters by domain. Two flavours:

- **Global rule** (no group). All global rules **intersect** — adding one
  always restricts further.
- **Group rule** (one or more groups). Group rules **unify** — adding one
  expands access (within the bounds set by global rules).

**Danger:** multiple non-overlapping global rules can lock everything out.
The global and group rulesets intersect, so the first group rule added under
a global ruleset will restrict access.

`perm_*` semantics on `ir.rule` differ from `ir.model.access`: they say "this
rule applies *for* these operations" — if unselected, the rule is not
evaluated for that op. All ops are selected by default.

Domain variables available:

- `user` — current user (singleton recordset)
- `time` — Python `time` module
- `company_id` — user's currently selected company **id**
- `company_ids` — list of all company ids the user has access to

## Field-level access

```python
salary = fields.Monetary(groups='hr.group_hr_user')
```

If the current user isn't in the listed group(s):

- The field is removed from views.
- It disappears from `fields_get()`.
- Explicit reads / writes raise `AccessError`.

### `groups=` is all-or-nothing — for "read-yes, write-no" use a `write()` whitelist

Field `groups=` is **all-or-nothing**: a non-member loses read *and* write
*and* visibility. It cannot express "everyone may read this field, only
group X may change it." There is **no declarative** way to do that — enforce
it in code:

- Give the editing group a normal model ACL row (e.g. `1,1,0,0` —
  read+write, no create/unlink) so it can write at all.
- Override `write()` (and `create()`, if the field is settable at create)
  on the **most-derived** model and **whitelist** who may set the protected
  field, raising `AccessError` otherwise:

```python
PROTECTED_FIELDS = {'credit_limit', 'internal_rating'}

def write(self, vals):
    if PROTECTED_FIELDS & vals.keys() and not self.env.user.has_group(
            'my_module.group_risk_manager'):
        raise AccessError(_("Only Risk Managers may change these fields."))
    return super().write(vals)
```

Put the guard on the most-derived class so a later `write()` in the MRO
can't shadow it; combine with a `create()` whitelist (see the mass-assignment
pattern in `odoo_vulnerabilities.md`) to cover the insert path.

#### Two escapes that survive the whitelist

A guard written as above inspects `vals.keys()` on the model being written.
Two paths never appear there:

- **x2many nested commands.** `(0, 0, {...})` / `(1, id, {...})` / `(2, id)`
  in a *whitelisted* x2many field carry writes to the **comodel**, which the
  top-level key check never sees. If the whitelisted relation reaches a shared
  catalogue, a "may only edit these fields" group can create, mutate, and
  delete records in it. For every whitelisted x2many, either validate the
  nested command payload explicitly or accept only `(4, id)` / `(6, 0, ids)`
  link forms, which cannot mutate the comodel.
- **A `sudo()`'d recompute or maintenance method.** Any public method that
  internally `sudo()`s is **RPC-callable in its own right** — the write guard
  is not on its path at all. A vendor's "recompute the schedule/board" action
  can therefore be invoked directly and wipe records the guarded group was
  never allowed to touch. Gate such methods with a one-shot context flag set
  only by the internal write path (and prefix-rename them to `_`-private if
  they are yours).

**UI `readonly` is not a security control.** A field marked `readonly` in a
view or via `attrs`/`invisible` is still writable by RPC, by data import, and
by any `write()` — it only affects the web form. Never rely on `readonly` (or
a hidden widget) to protect a field; the enforcement must be the ACL +
`write()` whitelist above (or a `groups=` restriction when full hiding is
acceptable).

**A stored compute with no inverse is not a security control either.** The
absence of an inverse method is necessary but not sufficient: a direct
`write({'my_computed_field': True})` is **accepted** and the value persists
until something retriggers the compute. So "the framework makes this
impossible" is not a guarantee for a field whose whole point is that an import
or an integration must not be able to assert it.

Enforce it the same way as any other protected field — **drop the key** in the
`create()` / `write()` overrides. That costs nothing legitimate, because the
ORM's own recomputation writes through `_write()` and never passes through
your override. Then test **both** halves: that the direct write is rejected,
and that the genuine computed value still persists *and remains searchable* —
a guard written slightly too wide silently breaks the field it was protecting.
General rule: when a security property is stated as "the framework makes this
impossible", write the test that tries it before believing it.

## Security pitfalls

### Unsafe public methods

Anything not prefixed with `_` is callable via XML-RPC / JSON-RPC with any
arguments. ACLs are only enforced on **CRUD** operations, not on method
invocation.

```python
# public — anyone with RPC access can call this with arbitrary kwargs
def action_done(self):
    if self.state == "draft" and self.user_has_groups('base.manager'):
        self._set_state("done")

# private — only callable from Python
def _set_state(self, new_state):
    self.sudo().write({'state': new_state})
```

Rules:

- Public method names must be safe to invoke with attacker-chosen args /
  records. Always re-check preconditions inside the method.
- Move sensitive mutations into a `_private_method` and expose a public
  wrapper that validates state, identity, and inputs.
- Making a method private is *necessary* but not sufficient — care still
  needed.

### Bypassing the ORM

Direct `cr.execute()` skips ACL, record rules, cache invalidation, computed
recomputation, `active` filtering, and translation. Replace with `search` /
`read` whenever possible. See `orm_patterns.md`.

### SQL injection

```python
# very bad — string concatenation
self.env.cr.execute(
    "SELECT distinct child_id FROM account_account_consol_rel "
    "WHERE parent_id IN (" + ",".join(map(str, ids)) + ")")

# good — psycopg2 parameterises
self.env.cr.execute(
    "SELECT DISTINCT child_id FROM account_account_consol_rel "
    "WHERE parent_id IN %s", (tuple(ids),))
```

Never `+`-concatenate or `%`-format query strings. Let psycopg2 format
parameters — it knows that a tuple becomes `(…)` for `IN %s`, that a list
becomes an array, etc.

### Unescaped QWeb content (`t-raw`)

`t-raw` injects HTML verbatim. It's an XSS vector. The "current input is
safe" argument fails after the next refactor.

```xml
<!-- vulnerable -->
<div id="information-bar"><t t-raw="info_message"/></div>
```

```xml
<!-- safe -->
<div id="information-bar">
    <div class="info"><t t-esc="message"/></div>
    <div class="subject"><t t-esc="subject"/></div>
</div>
```

Default to `t-esc`. When you genuinely need HTML, use `Markup` (see below)
or structured templates.

### `Markup` — safe HTML formatting

`Markup` is a string subclass from `markupsafe` that auto-escapes any
non-Markup operand inserted into it.

```python
from markupsafe import Markup, escape

Markup('<em>Hello</em> ') + '<foo>'
# Markup('<em>Hello</em> &lt;foo&gt;')

Markup('<em>Hello</em> %s') % '<foo>'
# Markup('<em>Hello</em> &lt;foo&gt;')
```

Patterns:

```python
def get_name(self, to_html=False):
    if to_html:
        return Markup('<strong>%s</strong>') % self.name  # escapes name
    return self.name

# Translation + Markup composition
_(
    "List of tasks on project %s: %s",
    project.name,
    Markup("<ul>%s</ul>") % Markup().join(
        Markup("<li>%s</li>") % t.name for t in project.task_ids
    ),
)
```

Pitfalls when using `Markup`:

```python
Markup("<p>Foo %s</p>" % bar)         # BAD: bar inserted before escaping
Markup("<p>Foo %s</p>") % bar         # OK: bar is escaped if text, kept if Markup

link = Markup("<a>%s</a>") % self.name
message = "Click %s" % link           # BAD: 'message' is a str, Markup info lost
message = escape("Click %s") % link   # OK: format two Markup objects together

Markup(f"<p>Foo {self.bar}</p>")      # BAD: bar inserted before escaping
Markup("<p>Foo {bar}</p>").format(bar=self.bar)  # OK
```

`escape()` (alias `html_escape`) turns a `str` into a `Markup` after
escaping; it leaves an existing `Markup` untouched.

## Trusting context keys

`self.env.context` is user-controlled. A user can pass any key on any RPC
call. Don't use a context key as the *only* authority for a security
decision:

```python
# wrong — user can pass `bypass_check=True` themselves
if self.env.context.get('bypass_check'):
    return self._do_dangerous_thing()
```

Use ACL groups, record rules, or `with_user(internal_admin)` for real
elevation.

## `sudo()` — when is it justified?

Reach for `sudo()` only when:

- The operation must succeed regardless of the caller's groups, AND
- The data being touched is **independent** of the caller's identity (e.g.
  writing to a configuration record that the user shouldn't directly own).

`sudo()` is **not** the right answer for:

- "I'm getting an AccessError." → fix the ACL/rule instead.
- "I want to read a referenced field across a Many2one." → that already
  works under normal rules unless rules explicitly forbid it.
- "It's the easy fix." → audit later finds these and they are blockers.

## Multi-company sanity

> "No sanity checks applied in sudo mode! When in sudo mode, a user can
> access any company, even if not in his allowed companies."

When you sudo in a multi-company environment, also be explicit about the
target company:

```python
record.sudo().with_company(target_company).do_stuff()
```

Otherwise you can silently leak data across companies.

## Self-audit checklist (drop into PR description)

- [ ] Every new model has an `ir.model.access.csv` row.
- [ ] No public method mutates state without re-validating preconditions.
- [ ] No `cr.execute` with string concatenation / `%`-formatting.
- [ ] No `t-raw` introduced; existing `t-raw` is justified in a comment.
- [ ] Every `sudo()` has a one-line `# justification` comment.
- [ ] No security decision relies on a context key alone.
- [ ] Cross-company writes use `with_company`.
- [ ] Field-level `groups=` reviewed against the data classification policy.
