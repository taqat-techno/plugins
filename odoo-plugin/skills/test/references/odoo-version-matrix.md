# Odoo Version Matrix for Tests

The skill is version-generic. Detect the Odoo series from the module's `__manifest__.py` (`version`) and the running source, then apply the right form. When unsure, inspect the actual `odoo/tests/common.py` and `odoo/fields.py` of the target tree rather than assuming.

## Base test classes

| Concern | Odoo ≤ 12 | Odoo 13 – 15 | Odoo 16+ |
|---|---|---|---|
| Isolated unit test, class-level setup + per-test rollback | `TransactionCase` (per-test setup) / `SavepointCase` (13+ pattern emerging) | **`SavepointCase`** = class `setUpClass` + per-test savepoint; `TransactionCase` = per-test setup | **`TransactionCase`** *is* the class-level + savepoint variant; `SavepointCase` was **merged in** and may be a deprecated alias or absent |
| HTTP / controllers / tours | `HttpCase` | `HttpCase` | `HttpCase` |
| Single growing transaction (ordered) | `SingleTransactionCase` | `SingleTransactionCase` | `SingleTransactionCase` |

**Rule of thumb:**
- On **16+**, use `TransactionCase` and put fixtures in `setUpClass` — you already get per-test rollback. Don't import `SavepointCase`.
- On **13–15**, if you want class-level fixtures, use `SavepointCase`; `TransactionCase` there rebuilds per test.
- Always confirm by checking what `odoo.tests.common` actually exports in the target tree.

## Relational write API

| Form | Odoo ≤ 12 | Odoo 13+ |
|---|---|---|
| Create line | `(0, 0, {...})` | `Command.create({...})` (alias of `(0,0,{...})`) |
| Update line | `(1, id, {...})` | `Command.update(id, {...})` |
| Delete line | `(2, id)` | `Command.delete(id)` |
| Unlink (keep record) | `(3, id)` | `Command.unlink(id)` |
| Link | `(4, id)` | `Command.link(id)` |
| Clear | `(5, 0, 0)` | `Command.clear()` |
| Replace set | `(6, 0, [ids])` | `Command.set([ids])` |

`from odoo.fields import Command` is available from Odoo 13. Legacy tuples still work in all versions; prefer `Command` where available for readability.

## Views (affects Form/view tests)

| Concern | Older | Newer (Odoo 17+/19) |
|---|---|---|
| List view tag | `<tree>` | `<list>` (in 17+ `<tree>` may still parse; 19 standardizes `<list>`) |
| Conditional visibility | `attrs="{'invisible': [...]}"` | inline `invisible="<python expr>"` |
| Field modifiers | `attrs`/`states` dicts | inline expressions |

When a test passes a view xmlid to `Form(model, view=...)`, the view must use the version-correct syntax.

## Controllers / routes

| Concern | Older | Newer |
|---|---|---|
| JSON route type | `type='json'` | `type='jsonrpc'` (Odoo 17+/19) — older `type='json'` may be deprecated/aliased |
| Test helper for JSON | manual JSON-RPC envelope via `url_open` | `make_jsonrpc_request(route, params)` where provided |

For any JSON route, the HTTP status is 200 even on app errors — assert the JSON `error` envelope, not just the status.

## Helpers that are broadly available

- `new_test_user(env, login=..., groups='a,b')` — create a user with groups (comma-separated xmlids).
- `tagged(*tags)` — `@tagged('post_install', '-at_install')`; classes default to `{'standard','at_install'}`.
- `Form` (and its x2many proxies) — the in-test web-form simulator.
- `users('login', ...)` decorator — run a test body once per login.
- `mute_logger('logger.name')` — silence expected error logs around `assertRaises`.
- `freeze_time(...)` — deterministic date/time (wraps freezegun in recent versions).

Names and exact import paths can shift between versions — verify against the target tree's `odoo/tests/common.py` before relying on a less-common helper.
