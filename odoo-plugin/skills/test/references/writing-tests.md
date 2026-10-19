# Writing Odoo tests: architecture, tags, CRUD/compute/constraint/wizard and controller patterns

Moved out of `SKILL.md` to keep the skill body small. Load this file when the task needs it.

## Testing Architecture

### Test Class Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ODOO TEST CLASS HIERARCHY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  unittest.TestCase (Python standard)                                          │
│  └── odoo.tests.common.BaseCase                                              │
│       ├── TransactionCase          ← MOST COMMON                             │
│       │   • Each test wrapped in transaction rolled back on completion        │
│       │   • Full ORM access via self.env                                      │
│       │   • Database state reset between tests                                │
│       │   • setUpClass() for shared expensive setup                           │
│       │                                                                       │
│       ├── SavepointCase (Odoo 14-15) / TransactionCase with savepoints        │
│       │   • Allows partial rollback within a test                             │
│       │   • Useful for testing exception handling                             │
│       │   • Use self.cr.savepoint() context manager                           │
│       │                                                                       │
│       └── HttpCase                 ← FOR WEBSITE/API                         │
│           • Starts real HTTP server on localhost                              │
│           • Supports phantom_js() / browser_js()                              │
│           • Supports jsonrpc() / url_open()                                   │
│           • Full route testing with authentication                            │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### TransactionCase vs HttpCase vs SavepointCase

| Feature | TransactionCase | SavepointCase | HttpCase |
|---------|----------------|---------------|----------|
| DB Isolation | Per test (rollback) | Per class (savepoints) | Per test (rollback) |
| HTTP server | No | No | Yes (localhost) |
| Speed | Fast | Medium | Slow |
| Best for | ORM/business logic | Exception testing | Routes, UI, JSON |
| Auth control | Direct `self.env` | Direct `self.env` | `self.authenticate()` |
| Access | `env.user` | `env.user` | Via HTTP session |

### When to Use Each

```python
# TransactionCase - Business logic, CRUD, compute, constraints, workflows
class TestSaleOrder(TransactionCase):
    def test_order_confirmation(self):
        order = self.env['sale.order'].create({...})
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

# HttpCase - Website routes, API endpoints, authenticated pages
class TestWebsiteController(HttpCase):
    def test_shop_page(self):
        self.authenticate('admin', 'admin')
        res = self.url_open('/shop')
        self.assertEqual(res.status_code, 200)

# SavepointCase - When you need to test that an exception rolls back properly
class TestConstraints(TransactionCase):
    def test_constraint_rollback(self):
        with self.assertRaises(ValidationError):
            self.env['my.model'].create({'required_field': False})
```

## Test Tagging System

### Tag Decorator Reference

```python
from odoo.tests import tagged

# Most common - runs after all modules installed (stable environment)
@tagged('post_install', '-at_install')
class TestMyModel(TransactionCase):
    pass

# Runs during module install (early execution, limited env)
@tagged('at_install', '-post_install')
class TestEarlyLogic(TransactionCase):
    pass

# Standard tests (default, equivalent to post_install)
@tagged('standard')
class TestStandard(TransactionCase):
    pass

# Explicitly exclude from automatic runs
@tagged('-standard', 'manual')
class TestManualOnly(TransactionCase):
    pass

# Multiple tags
@tagged('post_install', '-at_install', 'sale', 'critical')
class TestSaleIntegration(TransactionCase):
    pass
```

### Tag Precedence Rules

```
Tag with '-' prefix = EXCLUSION (remove from selection)
Tag without '-'    = INCLUSION (add to selection)

Default run: --test-tags=standard
Post-install: --test-tags=post_install (most common for production tests)

Examples:
  --test-tags=post_install           → all post_install tests of EVERY installed module
  --test-tags=/my_module             → all tests in module my_module (without the "/" it is a TAG)
  --test-tags=/my_module:MyClass     → specific class in module
  --test-tags=/my_module:MyClass.test_method  → specific method
```

### Built-in Odoo Tags

| Tag | When it runs | Use case |
|-----|-------------|----------|
| `standard` | Default CI runs | Unit tests, business logic |
| `at_install` | During install | Basic module integrity |
| `post_install` | After all installs | Integration, full env tests |
| `slow` | Skipped by default | Long-running tests |
| `external` | Skipped by default | External API tests |
| `multi_company` | Special flag | Multi-company scenarios |

## Writing Tests

### Complete CRUD Test Pattern

```python
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError

@tagged('post_install', '-at_install')
class TestMyModel(TransactionCase):
    """Test suite for my.model CRUD operations and business logic."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures shared across all tests in this class.
        Called once before any test method in the class.
        """
        super().setUpClass()
        # Create shared records (not rolled back between tests)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })
        cls.currency = cls.env.ref('base.USD')
        cls.company = cls.env.company

    def setUp(self):
        """Set up per-test fixtures. Called before EACH test method."""
        super().setUp()
        # Create fresh records for each test (rolled back after each test)
        self.record = self.env['my.model'].create({
            'name': 'Test Record',
            'partner_id': self.partner.id,
            'amount': 100.0,
        })

    # ─── CREATE TESTS ────────────────────────────────────────────────────────

    def test_create_minimal(self):
        """Test creating a record with only required fields."""
        record = self.env['my.model'].create({'name': 'Minimal'})
        self.assertTrue(record.id, "Record should have been created with an ID")
        self.assertEqual(record.name, 'Minimal')
        self.assertEqual(record.state, 'draft')  # Default state

    def test_create_full(self):
        """Test creating a record with all fields populated."""
        vals = {
            'name': 'Full Record',
            'partner_id': self.partner.id,
            'amount': 1500.50,
            'date': '2024-01-15',
            'notes': 'Test notes',
            'active': True,
        }
        record = self.env['my.model'].create(vals)
        self.assertEqual(record.name, vals['name'])
        self.assertEqual(record.partner_id, self.partner)
        self.assertAlmostEqual(record.amount, 1500.50, places=2)

    def test_create_required_field_missing(self):
        """Test that creating without required fields raises an error."""
        with self.assertRaises(Exception):
            self.env['my.model'].create({})  # Missing 'name' (required)

    # ─── READ/SEARCH TESTS ──────────────────────────────────────────────────

    def test_search_by_name(self):
        """Test searching records by name."""
        results = self.env['my.model'].search([('name', '=', 'Test Record')])
        self.assertIn(self.record, results)

    def test_search_domain(self):
        """Test complex domain search."""
        results = self.env['my.model'].search([
            ('amount', '>=', 50.0),
            ('partner_id', '=', self.partner.id),
        ])
        self.assertGreater(len(results), 0)

    def test_name_get(self):
        """Test the display name of the record."""
        name = self.record.display_name
        self.assertIn('Test Record', name)

    # ─── WRITE TESTS ─────────────────────────────────────────────────────────

    def test_write_name(self):
        """Test updating the record name."""
        self.record.write({'name': 'Updated Name'})
        self.assertEqual(self.record.name, 'Updated Name')

    def test_write_amount(self):
        """Test updating a numeric field."""
        self.record.write({'amount': 999.99})
        self.assertAlmostEqual(self.record.amount, 999.99, places=2)

    def test_write_state_transition(self):
        """Test valid state transition."""
        self.record.action_confirm()
        self.assertEqual(self.record.state, 'confirmed')

    # ─── DELETE TESTS ────────────────────────────────────────────────────────

    def test_unlink(self):
        """Test deleting a record."""
        record_id = self.record.id
        self.record.unlink()
        result = self.env['my.model'].search([('id', '=', record_id)])
        self.assertFalse(result, "Record should have been deleted")

    def test_unlink_confirmed_raises(self):
        """Test that confirmed records cannot be deleted."""
        self.record.action_confirm()
        with self.assertRaises(UserError):
            self.record.unlink()
```

### Compute Field Tests

```python
@tagged('post_install', '-at_install')
class TestComputedFields(TransactionCase):

    def test_amount_total_compute(self):
        """Test that amount_total correctly sums line amounts."""
        order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
        })
        self.env['sale.order.line'].create([
            {
                'order_id': order.id,
                'product_id': self.env.ref('product.product_product_1').id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            },
            {
                'order_id': order.id,
                'product_id': self.env.ref('product.product_product_2').id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            },
        ])
        # Force recompute in case it's not stored
        order.invalidate_recordset()
        self.assertAlmostEqual(order.amount_untaxed, 250.0, places=2)

    def test_compute_depends_triggers(self):
        """Test that modifying a dependency triggers recompute."""
        record = self.env['my.model'].create({'base_amount': 100.0, 'tax_rate': 0.15})
        # Verify initial computed value
        self.assertAlmostEqual(record.total_with_tax, 115.0, places=2)
        # Change a dependency and verify recompute
        record.write({'base_amount': 200.0})
        self.assertAlmostEqual(record.total_with_tax, 230.0, places=2)

    def test_stored_compute_persists(self):
        """Test that stored computed fields are saved to the database."""
        record = self.env['my.model'].create({'name': 'Compute Test', 'value': 42})
        record_id = record.id
        # Clear cache and reload from DB
        self.env.cr.execute("SELECT computed_field FROM my_model WHERE id = %s", [record_id])
        row = self.env.cr.fetchone()
        self.assertIsNotNone(row[0], "Stored computed field should be in DB")

    def test_onchange_simulation(self):
        """Test onchange logic by calling the method directly."""
        record = self.env['my.model'].new({'partner_id': self.env.ref('base.res_partner_1').id})
        record._onchange_partner_id()
        # Verify that onchange populated expected fields
        self.assertTrue(record.currency_id, "Currency should be set from partner country")
```

### Constraint Tests

```python
@tagged('post_install', '-at_install')
class TestConstraints(TransactionCase):

    def test_sql_constraint_unique_name(self):
        """Test SQL unique constraint prevents duplicate names."""
        self.env['my.model'].create({'name': 'Unique Name', 'code': 'UNAME'})
        from psycopg2 import IntegrityError
        with self.assertRaises(IntegrityError):
            # Must be in a separate transaction savepoint
            with self.env.cr.savepoint():
                self.env['my.model'].create({'name': 'Different', 'code': 'UNAME'})

    def test_python_constraint_amount_positive(self):
        """Test Python @constrains decorator validation."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['my.model'].create({'name': 'Negative', 'amount': -100.0})

    def test_python_constraint_date_range(self):
        """Test date range constraint."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['my.model'].create({
                'name': 'Bad Dates',
                'date_start': '2024-12-31',
                'date_end': '2024-01-01',  # End before start
            })

    def test_constraint_on_write(self):
        """Test that constraints fire on write, not just create."""
        from odoo.exceptions import ValidationError
        record = self.env['my.model'].create({'name': 'Valid', 'amount': 100.0})
        with self.assertRaises(ValidationError):
            record.write({'amount': -50.0})
```

### Wizard Tests

```python
@tagged('post_install', '-at_install')
class TestWizard(TransactionCase):

    def test_wizard_create_and_confirm(self):
        """Test wizard creation and confirmation."""
        record = self.env['my.model'].create({'name': 'Parent', 'amount': 500.0})
        wizard = self.env['my.wizard'].with_context(
            active_model='my.model',
            active_id=record.id,
            active_ids=[record.id],
        ).create({
            'reason': 'Testing cancellation',
        })
        result = wizard.action_confirm()
        # Verify state changed
        self.assertEqual(record.state, 'cancelled')
        # If wizard returns an action, verify structure
        if result:
            self.assertIn('type', result)

    def test_wizard_onchange(self):
        """Test wizard field dependencies."""
        wizard = self.env['my.wizard'].new({
            'partner_id': self.env.ref('base.res_partner_1').id,
        })
        wizard._onchange_partner_id()
        self.assertTrue(wizard.currency_id)

    def test_wizard_required_fields(self):
        """Test wizard raises UserError when required action fields missing."""
        from odoo.exceptions import UserError
        record = self.env['my.model'].create({'name': 'Test'})
        wizard = self.env['my.wizard'].with_context(
            active_ids=[record.id],
        ).create({})
        with self.assertRaises(UserError):
            wizard.action_confirm()
```

## HTTP Controller Tests

### Basic Route Testing

```python
from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestWebsiteRoutes(HttpCase):
    """Test HTTP routes and website controllers."""

    def test_public_page_accessible(self):
        """Test that a public page returns 200 without authentication."""
        res = self.url_open('/my-page')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Expected Content', res.text)

    def test_authenticated_page_redirects_unauthenticated(self):
        """Test that protected pages redirect to login."""
        res = self.url_open('/my-account')
        # Should redirect to login (302) or show login (200 with login form)
        self.assertIn(res.status_code, [200, 301, 302])

    def test_authenticated_route(self):
        """Test route that requires authentication."""
        self.authenticate('admin', 'admin')
        res = self.url_open('/my-account')
        self.assertEqual(res.status_code, 200)

    def test_portal_user_access(self):
        """Test portal user can access their own records."""
        portal_user = self.env['res.users'].create({
            'name': 'Portal Test User',
            'login': 'portal_test@example.com',
            'groups_id': [(4, self.env.ref('base.group_portal').id)],
        })
        self.authenticate(portal_user.login, 'portal_test@example.com')
        res = self.url_open('/my/orders')
        self.assertEqual(res.status_code, 200)
```

### JSON RPC Controller Testing

```python
@tagged('post_install', '-at_install')
class TestJsonController(HttpCase):
    """Test JSON-RPC API endpoints."""

    def test_json_endpoint_success(self):
        """Test a JSON endpoint returns correct data."""
        self.authenticate('admin', 'admin')
        result = self.jsonrpc(
            url='/web/dataset/call_kw',
            method='execute_kw',
            params={
                'model': 'res.partner',
                'method': 'search_read',
                'args': [[['name', 'ilike', 'Azure']]],
                'kwargs': {'fields': ['name', 'email'], 'limit': 5},
            }
        )
        self.assertIsInstance(result, list)

    def test_custom_json_route(self):
        """Test a custom JSON controller endpoint."""
        self.authenticate('admin', 'admin')
        result = self.jsonrpc(
            url='/api/my-endpoint',
            method='call',
            params={'record_id': 1, 'action': 'validate'},
        )
        self.assertEqual(result.get('status'), 'ok')

    def test_json_route_validation_error(self):
        """Test JSON endpoint returns error structure on invalid input."""
        self.authenticate('admin', 'admin')
        res = self.url_open(
            '/api/my-endpoint',
            data='{"jsonrpc": "2.0", "method": "call", "params": {"record_id": -999}}',
            headers={'Content-Type': 'application/json'},
        )
        data = res.json()
        self.assertIn('error', data)

    def test_post_form_submission(self):
        """Test a POST form submission via website."""
        res = self.url_open(
            '/contact',
            data={
                'name': 'Test Contact',
                'email': 'test@test.com',
                'message': 'Test message from automated test',
            },
        )
        self.assertIn(res.status_code, [200, 302])
```
