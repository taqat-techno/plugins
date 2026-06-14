# Odoo 17 Testing — review reference

Source: [Testing Odoo](https://www.odoo.com/documentation/17.0/developer/reference/backend/testing.html)

Three kinds of tests in Odoo:

| Kind | What it covers | Base class |
|---|---|---|
| Python unit tests | Model / business logic | `TransactionCase`, `SingleTransactionCase` |
| JS unit tests | Frontend code in isolation | (web framework testing harness) |
| Tours | End-to-end, browser-driven | `HttpCase` + tour script |

## Test layout

```
your_module/
├── ...
└── tests/
    ├── __init__.py        # MUST import every test_*.py module to run
    ├── test_foo.py
    └── test_bar.py
```

`tests/__init__.py`:

```python
from . import test_foo, test_bar
```

> **Tests not imported from `tests/__init__.py` will not be run.** This is
> the #1 silent-failure cause in Odoo test reviews.

File / class / method conventions:

- Test files: `test_<topic>.py`.
- Test classes: `class TestFoo(TransactionCase): ...`.
- Test methods: `def test_<name>(self):`.

Run a specific test:

```bash
odoo-bin -d my_db -i my_module --test-tags /my_module:TestFoo.test_bar
```

## Base classes

### `TransactionCase`

- All tests share a single transaction; each test method runs inside its
  own savepoint and is rolled back at the end.
- The transaction's cursor is closed without committing.
- Common setup in `setUpClass()` (runs once for the class).
- After each test, record and registry caches are reset.
- If the test modifies the registry (custom models/fields), call
  `self.registry.reset_changes()` in `tearDown()`.

This is the default. Use it unless you have a specific reason not to.

### `SingleTransactionCase`

- All test methods share **one** transaction, started at the first test
  and rolled back after the last.
- Useful when methods are inherently ordered and share setup that is
  expensive even once per class.
- Test isolation is weaker — a bug in one test pollutes the next.

### `HttpCase`

- Full transactional test with `url_open()` and Chrome headless helpers.
- Used for routes, controllers, and **tours** (browser-driven UI tests).
- Heavier; reserve for tests that genuinely need HTTP / a browser.

Tour test pattern:

```python
class TestCheckoutTour(HttpCase):
    def test_checkout_tour(self):
        self.start_tour('/shop', 'checkout_tour', login='demo')
```

The tour itself is registered in JS under
`static/tests/tours/checkout_tour.js`.

## Useful helpers (available on all base classes)

| Helper | Purpose |
|---|---|
| `self.env` | The test environment (`Environment` instance) |
| `self.env.user` | Current test user |
| `self.ref('module.xmlid')` | Returns the **id** for an external identifier |
| `self.browse_ref('module.xmlid')` | Returns the **recordset** for an external identifier |
| `self.assertQueryCount(N)` | Asserts the wrapped block fires exactly N SQL queries |
| `self.profile()` | Context manager that profiles a block (stores `ir.profile` record) |
| `self.cr` | The test cursor (use sparingly) |

## Patterns to follow

### Build data in `setUpClass`

```python
class TestSaleFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'ACME'})
        cls.product = cls.env['product.product'].create({
            'name': 'Widget', 'list_price': 10.0,
        })
```

Per-method setup duplicates work — slow.

### Assert behaviour, not implementation

```python
# good
order.action_confirm()
self.assertEqual(order.state, 'sale')

# bad — couples test to private method names
order._set_state('sale')
self.assertTrue(order._is_confirmed())
```

### Watch SQL query counts

```python
with self.assertQueryCount(__system__=12):
    order.action_confirm()
```

A test that locks down a query count is fragile but invaluable when
hunting N+1 regressions.

### Mocking the database is a smell

Odoo tests run in a sub-transaction that's rolled back at the end — the
database is essentially free to use. Mocking it usually means the test is
testing the wrong layer.

## Test groups & tags

```python
from odoo.tests import tagged, TransactionCase

@tagged('post_install', '-at_install')
class TestPostInstall(TransactionCase):
    ...
```

Tags:

- `at_install` (default) — run during module install.
- `post_install` — run after all modules of the test run are installed.
- `standard` (default) — included in `--test-tags ''` runs.
- `nightly`, `slow`, custom tags — exclude from CI fast lane.

Negate a tag with a leading `-`: `@tagged('post_install', '-at_install')`.

## Reviewing tests at PR time

- [ ] `tests/__init__.py` imports every `test_*.py` in the dir.
- [ ] Base class fits the test (mostly `TransactionCase`).
- [ ] No `cr.commit()` anywhere.
- [ ] Heavy setup in `setUpClass`, not `setUp`.
- [ ] Asserts on observable behaviour, not private methods.
- [ ] `assertQueryCount` used on flows known to be N+1-prone.
- [ ] Tours have a corresponding `HttpCase` Python test that triggers them.
- [ ] No "skipped" test left in place without an issue link in the comment.
- [ ] User-as identity is set explicitly when ACLs matter
  (`with_user(self.env.ref('base.user_demo'))`).
