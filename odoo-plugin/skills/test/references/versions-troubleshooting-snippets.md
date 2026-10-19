# Version compatibility, troubleshooting, and quick snippets

Moved out of `SKILL.md` to keep the skill body small. Load this file when the task needs it.

## Version Compatibility

### Test Framework Differences Odoo 14-19

| Feature | Odoo 14 | Odoo 15 | Odoo 16 | Odoo 17 | Odoo 18 | Odoo 19 |
|---------|---------|---------|---------|---------|---------|---------|
| `SavepointCase` | Yes | Yes | Deprecated | Removed | Removed | Removed |
| `TransactionCase` | Yes | Yes | Yes | Yes | Yes | Yes |
| `HttpCase` | Yes | Yes | Yes | Yes | Yes | Yes |
| `--test-tags` format | Basic | Basic | Enhanced | Enhanced | Enhanced | Enhanced |
| `setUpClass` | Yes | Yes | Yes | Yes | Yes | Yes |
| `assertRaises` context | Yes | Yes | Yes | Yes | Yes | Yes |
| `browser_js` | Yes | Yes | Yes | Deprecated | Removed | Removed |
| `phantom_js` | Yes | Yes | Yes | Yes | Yes | Yes |
| Mock `patch` in base | Manual | Manual | Built-in | Built-in | Built-in | Built-in |

### Version-Specific Import Changes

```python
# Odoo 14 - SavepointCase still valid
from odoo.tests.common import SavepointCase, TransactionCase, HttpCase

# Odoo 15 - SavepointCase deprecated
from odoo.tests.common import TransactionCase, HttpCase
from odoo.tests import tagged

# Odoo 16-19 - Use TransactionCase with savepoints for rollback control
from odoo.tests import TransactionCase, HttpCase, tagged
# SavepointCase was removed; use TransactionCase with self.cr.savepoint()
```

### Version-Safe Test Template

```python
# Works across Odoo 14-19
try:
    from odoo.tests.common import SavepointCase as TestBase
except ImportError:
    from odoo.tests.common import TransactionCase as TestBase

from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestCompatible(TestBase):
    """Version-compatible test class."""
    pass
```

### Field API Changes

```python
# Odoo 14-15: fields.Date.from_string('2024-01-01')
# Odoo 16+:   fields.Date.to_date('2024-01-01')  (also works in 14-15)

# Odoo 14-16: self.env['ir.sequence'].next_by_code('my.sequence')
# Odoo 17+:   Same API - no change

# Odoo 14-17: order.write({'state': 'cancel'})
# Odoo 18+:   May require specific action methods depending on model
```

## Troubleshooting

### Common Test Failures and Fixes

#### 1. Module Not Found in Test Discovery

```
ERROR: no test found in my_module
```

**Fix**: Ensure `tests/` directory has `__init__.py` and imports test files:

```python
# my_module/tests/__init__.py
from . import test_my_model
from . import test_other
```

Also ensure `__manifest__.py` has:
```python
'installable': True,
# No 'tests' key needed - discovered automatically
```

#### 2. ImportError in Test File

```
ImportError: cannot import name 'SavepointCase' from 'odoo.tests.common'
```

**Fix**: Replace `SavepointCase` with `TransactionCase` (removed in Odoo 16).

#### 3. Access Rights Error

```
AccessError: my_module.my_model: Permission denied
```

**Fix**: Use `.sudo()` for admin-level test setup, or add user to proper group:

```python
def setUp(self):
    super().setUp()
    # Use admin env for setup
    self.record = self.env['my.model'].sudo().create({...})

    # Or add current user to required group
    self.env.user.write({
        'groups_id': [(4, self.env.ref('my_module.group_manager').id)]
    })
```

#### 4. Database Not Reset Between Tests

```
# If setUpClass data is being modified by tests unintentionally:
```

**Fix**: Never mutate `cls.*` attributes in test methods. Use `setUp` for mutable records.

#### 5. Compute Field Not Triggering

```
AssertionError: 0 != 100.0 (computed field returned default)
```

**Fix**: Invalidate cache after dependency changes:

```python
record.write({'base_amount': 200.0})
record.invalidate_recordset(['total_amount'])  # Odoo 16+
# Or
record._compute_total_amount()  # Direct call for stored fields
```

#### 6. Email Sent During Tests (Slows Execution)

**Fix**: Disable mail tracking in context:

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()
    cls.env = cls.env(context={
        **cls.env.context,
        'mail_notrack': True,
        'no_reset_password': True,
        'tracking_disable': True,
    })
```

#### 7. Test Timing Out

```
Test exceeded maximum time limit (300s)
```

**Fix**: Split slow tests, use `@tagged('slow')` to exclude from regular CI:

```python
@tagged('slow', 'post_install', '-at_install', '-standard')
class TestSlowIntegration(TransactionCase):
    pass
```

#### 8. PostgreSQL Integrity Error in Test

```
psycopg2.errors.UniqueViolation: duplicate key value
```

**Fix**: Use savepoints to catch expected DB errors:

```python
def test_unique_constraint(self):
    self.env['my.model'].create({'code': 'UNIQUE'})
    with self.assertRaises(Exception):
        with self.env.cr.savepoint():
            self.env['my.model'].create({'code': 'UNIQUE'})
```

#### 9. HttpCase Authentication Fails

```
AssertionError: Expected 200, got 403
```

**Fix**: Ensure user exists and password is correct:

```python
def test_requires_admin(self):
    # Use built-in admin (always available in tests)
    self.authenticate('admin', 'admin')
    res = self.url_open('/admin-only-route')
    self.assertEqual(res.status_code, 200)
```

**Caveat — `HttpCase` is unreliable for `Binary(attachment=True)` routes and
host-gated auth.** Two failure modes make an `HttpCase` status assertion a
false signal:

- **Binary / image routes answer 200 on deny.** `/web/image` and
  `/web/content` return **HTTP 200 + a placeholder** when access is denied,
  not 403 — so `assertEqual(status_code, 200)` passes for *both* an
  authorized and a denied caller. Assert on the **body** (placeholder vs
  real bytes / content-length), or better, don't test binary access over
  HTTP at all.
- **Host-gated auth doesn't reproduce.** Routes whose auth depends on the
  request Host / website / a cookie session may resolve differently under
  the test HTTP client than in production, giving false passes/failures.

For access-control assertions, **test at the controller / ACL layer**
instead: call the model with `with_user(some_user)` and assert `AccessError`
(allowed vs denied) at the record level, or invoke the controller method
directly. Reserve `HttpCase` for happy-path routing/tours, not for proving a
binary route's authorization.

#### 10. Field Not Found on Model

```
AttributeError: 'my.model' model has no field 'my_field'
```

**Fix**: Ensure module with the field is in `depends` in `__manifest__.py` and installed in test DB.

## Quick Snippets

### Assert Methods Reference

```python
# Equality
self.assertEqual(a, b)          # a == b
self.assertNotEqual(a, b)       # a != b
self.assertAlmostEqual(a, b, places=2)  # float comparison
self.assertIs(a, b)             # a is b (identity)
self.assertIsNone(a)            # a is None
self.assertIsNotNone(a)         # a is not None

# Boolean
self.assertTrue(x)              # bool(x) is True
self.assertFalse(x)             # bool(x) is False

# Membership
self.assertIn(a, b)             # a in b
self.assertNotIn(a, b)          # a not in b
self.assertIn(record, recordset)  # Odoo recordset check

# Collections
self.assertEqual(len(records), 3)  # Count check
self.assertGreater(len(records), 0)

# Exceptions
self.assertRaises(ValidationError, lambda: record.write({...}))
with self.assertRaises(UserError) as ctx:
    record.action_confirm()
self.assertIn('specific message', str(ctx.exception))

# Recordsets (Odoo-specific patterns)
self.assertFalse(empty_recordset)
self.assertTrue(non_empty_recordset)
self.assertEqual(record, expected_record)  # Recordset equality
```

### Useful Test Utilities

```python
# Skip test conditionally
def test_feature(self):
    if not self.env['account.move']._module_installed('account_lock'):
        self.skipTest('account_lock module not installed')
    # ...

# Generate unique names to avoid conflicts
import uuid
unique_name = f'Test_{uuid.uuid4().hex[:8]}'

# Freeze time (Odoo 16+)
from unittest.mock import patch
from datetime import date
with patch('odoo.fields.Date.today', return_value=date(2024, 6, 15)):
    record = self.env['my.model'].create({'date': fields.Date.today()})
    self.assertEqual(record.date, date(2024, 6, 15))

# Access Odoo configuration
param_value = self.env['ir.config_parameter'].sudo().get_param('my.param')

# Run as different user
record_as_user = record.with_user(self.env.ref('base.user_demo'))
```
