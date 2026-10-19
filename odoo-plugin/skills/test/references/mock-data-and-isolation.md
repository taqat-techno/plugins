# Mock data and test isolation

Moved out of `SKILL.md` to keep the skill body small. Load this file when the task needs it.

## Mock Data Creation

### Pattern Overview

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()
    # Using env.ref() for existing XML ID records
    cls.partner_azure = cls.env.ref('base.res_partner_1')
    cls.product_service = cls.env.ref('product.product_product_1')
    cls.currency_usd = cls.env.ref('base.USD')
    cls.company_main = cls.env.ref('base.main_company')
    cls.user_admin = cls.env.ref('base.user_admin')

    # Create fresh test records
    cls.partner_test = cls.env['res.partner'].create({
        'name': 'Automated Test Partner',
        'email': 'autotest@example.com',
        'phone': '+1-555-0100',
        'street': '123 Test Street',
        'city': 'Test City',
        'country_id': cls.env.ref('base.us').id,
        'customer_rank': 1,
    })

    cls.product_test = cls.env['product.product'].create({
        'name': 'Test Product',
        'type': 'service',
        'list_price': 100.0,
        'standard_price': 60.0,
        'uom_id': cls.env.ref('uom.product_uom_unit').id,
    })
```

### Creating Realistic Batch Records

```python
def _create_batch_orders(self, count=5):
    """Helper to create multiple test sale orders."""
    partners = self.env['res.partner'].create([
        {
            'name': f'Test Partner {i}',
            'email': f'partner{i}@test.com',
        }
        for i in range(count)
    ])
    orders = self.env['sale.order'].create([
        {
            'partner_id': partner.id,
            'date_order': fields.Datetime.now(),
        }
        for partner in partners
    ])
    return orders
```

### Model-Specific Mock Data

```python
# res.partner - Customer
partner = env['res.partner'].create({
    'name': 'Acme Corporation',
    'is_company': True,
    'email': 'contact@acme.com',
    'phone': '+1-800-ACME',
    'street': '100 Main St',
    'city': 'Springfield',
    'state_id': env.ref('base.state_us_53').id,
    'country_id': env.ref('base.us').id,
    'zip': '12345',
    'vat': 'US123456789',
    'customer_rank': 5,
    'supplier_rank': 1,
})

# res.users - Internal User
user = env['res.users'].create({
    'name': 'Test Salesperson',
    'login': 'test_salesperson@company.com',
    'email': 'test_salesperson@company.com',
    'groups_id': [(4, env.ref('sales_team.group_sale_salesman').id)],
    'company_id': env.company.id,
    'company_ids': [(4, env.company.id)],
})

# product.product - Storable Product
product = env['product.product'].create({
    'name': 'Office Chair',
    'type': 'product',  # storable
    'list_price': 299.99,
    'standard_price': 150.00,
    'categ_id': env.ref('product.product_category_all').id,
    'uom_id': env.ref('uom.product_uom_unit').id,
    'uom_po_id': env.ref('uom.product_uom_unit').id,
})

# sale.order - Sales Order with Lines
sale_order = env['sale.order'].create({
    'partner_id': partner.id,
    'partner_invoice_id': partner.id,
    'partner_shipping_id': partner.id,
    'date_order': fields.Datetime.now(),
    'validity_date': fields.Date.add(fields.Date.today(), days=30),
    'order_line': [(0, 0, {
        'product_id': product.id,
        'product_uom_qty': 3,
        'price_unit': 299.99,
    })],
})

# account.move - Vendor Bill
bill = env['account.move'].create({
    'move_type': 'in_invoice',
    'partner_id': partner.id,
    'invoice_date': fields.Date.today(),
    'invoice_date_due': fields.Date.add(fields.Date.today(), days=30),
    'currency_id': env.ref('base.USD').id,
    'invoice_line_ids': [(0, 0, {
        'name': 'Services rendered',
        'quantity': 10,
        'price_unit': 200.0,
        'account_id': env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1).id,
    })],
})

# hr.employee - Employee
employee = env['hr.employee'].create({
    'name': 'John Doe',
    'job_id': env.ref('hr.job_consultant').id,
    'department_id': env.ref('hr.dep_it').id,
    'work_email': 'john.doe@company.com',
    'work_phone': '+1-555-0101',
    'company_id': env.company.id,
    'resource_calendar_id': env.ref('resource.resource_calendar_std').id,
})

# stock.picking - Delivery Order
picking = env['stock.picking'].create({
    'partner_id': partner.id,
    'picking_type_id': env.ref('stock.picking_type_out').id,
    'location_id': env.ref('stock.stock_location_stock').id,
    'location_dest_id': env.ref('stock.stock_location_customers').id,
    'move_ids': [(0, 0, {
        'name': product.name,
        'product_id': product.id,
        'product_uom_qty': 5,
        'product_uom': product.uom_id.id,
        'location_id': env.ref('stock.stock_location_stock').id,
        'location_dest_id': env.ref('stock.stock_location_customers').id,
    })],
})
```

## Test Isolation

### Transaction Rollback Mechanism

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TRANSACTION ISOLATION IN TESTS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Database State:  [module data] [demo data] [setUpClass data]                │
│                                                                               │
│  SAVEPOINT ──────────────────────────────────────────────────────────────── │
│  │  test_one()  → create records → assert → ROLLBACK to savepoint           │
│  │                                                                           │
│  SAVEPOINT ──────────────────────────────────────────────────────────────── │
│  │  test_two()  → create records → assert → ROLLBACK to savepoint           │
│  │                                                                           │
│  SAVEPOINT ──────────────────────────────────────────────────────────────── │
│  │  test_three() → create records → assert → ROLLBACK to savepoint          │
│                                                                               │
│  After ALL tests: ROLLBACK entire setUpClass data                            │
│  Database returns to exactly pre-test state                                  │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### SetUp and TearDown Patterns

```python
@tagged('post_install', '-at_install')
class TestWithSetup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Runs ONCE before all tests. Use for expensive operations."""
        super().setUpClass()
        # These records persist across all test methods in this class
        cls.company = cls.env.ref('base.main_company')
        cls.currency = cls.env.ref('base.USD')
        cls.partner = cls.env['res.partner'].create({
            'name': 'Shared Test Partner',
            'email': 'shared@test.com',
        })
        # Disable mail sending during tests
        cls.env = cls.env(context=dict(cls.env.context, no_mail_send=True))

    def setUp(self):
        """Runs BEFORE each test method. Use for per-test state."""
        super().setUp()
        # Fresh record per test, automatically rolled back
        self.record = self.env['my.model'].create({
            'name': 'Per-Test Record',
            'partner_id': self.partner.id,
        })

    @classmethod
    def tearDownClass(cls):
        """Runs ONCE after all tests in class. Clean up class-level resources."""
        # Usually not needed - transaction rollback handles cleanup
        super().tearDownClass()

    def tearDown(self):
        """Runs AFTER each test method."""
        # Usually not needed - savepoint rollback handles cleanup
        super().tearDown()

    def test_example(self):
        # self.partner is available (from setUpClass)
        # self.record is fresh (from setUp)
        self.assertTrue(self.record.id)
```

### Disabling Side Effects in Tests

```python
# Prevent emails from being sent
def setUp(self):
    super().setUp()
    # Method 1: Context flag
    self.env = self.env(context={**self.env.context, 'mail_notrack': True})

    # Method 2: Mock the send method
    def _mock_send(self, *args, **kwargs):
        return True
    self.patch(type(self.env['mail.mail']), '_send', _mock_send)

# Prevent scheduled actions
# NOTE: set_param mutates state the whole instance shares. It is acceptable inside a
# TransactionCase (rolled back) for a test-only key like this one; never do it for a key
# that drives an integration — patch the consuming method instead. See "Fixtures on an
# inherited database".
def setUp(self):
    super().setUp()
    self.env['ir.config_parameter'].sudo().set_param(
        'mail.catchall.domain', 'test.example.com'
    )

# Bypass security for testing business logic only
def test_without_security(self):
    record = self.env['my.model'].sudo().create({'name': 'Test'})
    # Uses sudo() to bypass access rights - focus on business logic
```
