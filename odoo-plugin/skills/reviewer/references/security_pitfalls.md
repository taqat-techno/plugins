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
