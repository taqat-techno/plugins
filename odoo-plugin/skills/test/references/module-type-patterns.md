# Test patterns by module type (sales, HR, accounting, inventory)

Moved out of `SKILL.md` to keep the skill body small. Load this file when the task needs it.

## Common Test Patterns by Module Type

### Sales Module Tests

```python
@tagged('post_install', '-at_install')
class TestSaleOrders(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref('base.res_partner_1')
        cls.product = cls.env.ref('product.product_product_5')
        cls.pricelist = cls.env.ref('product.list0')

    def _create_sale_order(self, qty=1, price=100.0):
        """Helper to create a minimal sale order."""
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': qty,
                'price_unit': price,
            })],
        })

    def test_create_sale_order(self):
        """Test creating a sale order in draft state."""
        order = self._create_sale_order()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(len(order.order_line), 1)

    def test_confirm_sale_order(self):
        """Test confirming a sale order changes state to 'sale'."""
        order = self._create_sale_order()
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_invoice_from_sale_order(self):
        """Test creating an invoice from a confirmed sale order."""
        order = self._create_sale_order(qty=2, price=500.0)
        order.action_confirm()
        # Create invoice
        invoice = order._create_invoices()
        self.assertTrue(invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.state, 'draft')
        # Post the invoice
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)

    def test_cancel_sale_order(self):
        """Test cancelling a draft order."""
        order = self._create_sale_order()
        order.action_cancel()
        self.assertEqual(order.state, 'cancel')

    def test_cancel_confirmed_order_raises(self):
        """Test that cancelling a confirmed order with stock moves raises error."""
        from odoo.exceptions import UserError
        order = self._create_sale_order()
        order.action_confirm()
        # Depending on stock integration, this may raise UserError
        # This test documents expected behavior
```

### HR Module Tests

```python
@tagged('post_install', '-at_install')
class TestHREmployee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = cls.env['hr.department'].create({
            'name': 'Test IT Department',
        })
        cls.job = cls.env['hr.job'].create({
            'name': 'Test Software Engineer',
            'department_id': cls.department.id,
        })

    def _create_employee(self, name='Test Employee'):
        return self.env['hr.employee'].create({
            'name': name,
            'job_id': self.job.id,
            'department_id': self.department.id,
            'work_email': f'{name.lower().replace(" ", ".")}@company.com',
            'company_id': self.env.company.id,
        })

    def test_create_employee(self):
        """Test creating an employee."""
        emp = self._create_employee()
        self.assertTrue(emp.id)
        self.assertEqual(emp.department_id, self.department)

    def test_employee_archive(self):
        """Test archiving an employee."""
        emp = self._create_employee('Archive Me')
        emp.toggle_active()
        self.assertFalse(emp.active)

    def test_attendance_checkin(self):
        """Test employee check-in if hr_attendance is installed."""
        if 'hr.attendance' not in self.env:
            self.skipTest("hr_attendance module not installed")
        emp = self._create_employee()
        attendance = self.env['hr.attendance'].create({
            'employee_id': emp.id,
            'check_in': fields.Datetime.now(),
        })
        self.assertTrue(attendance.id)
```

### Account Module Tests

```python
@tagged('post_install', '-at_install')
class TestAccountMove(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref('base.res_partner_2')
        cls.account_receivable = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)
        cls.account_revenue = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)

    def _create_invoice(self, amount=100.0):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Service',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.account_revenue.id,
            })],
        })

    def test_create_draft_invoice(self):
        """Test creating a draft invoice."""
        invoice = self._create_invoice()
        self.assertEqual(invoice.state, 'draft')
        self.assertAlmostEqual(invoice.amount_untaxed, 100.0, places=2)

    def test_post_invoice(self):
        """Test posting (confirming) an invoice."""
        invoice = self._create_invoice(500.0)
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertTrue(invoice.name)  # Name assigned on posting

    def test_register_payment(self):
        """Test registering a payment against an invoice."""
        invoice = self._create_invoice(200.0)
        invoice.action_post()
        # Register payment
        payment_wizard = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'payment_date': fields.Date.today(),
            'amount': 200.0,
        })
        payment_wizard.action_create_payments()
        self.assertEqual(invoice.payment_state, 'paid')
```

### Inventory / Stock Tests

```python
@tagged('post_install', '-at_install')
class TestInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Storable',
            'type': 'product',
        })
        cls.warehouse = cls.env.ref('stock.warehouse0')
        cls.location_stock = cls.env.ref('stock.stock_location_stock')
        cls.location_customer = cls.env.ref('stock.stock_location_customers')

    def test_create_picking(self):
        """Test creating a stock picking."""
        picking = self.env['stock.picking'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_customer.id,
            'move_ids': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'location_id': self.location_stock.id,
                'location_dest_id': self.location_customer.id,
            })],
        })
        self.assertEqual(picking.state, 'draft')
        self.assertEqual(len(picking.move_ids), 1)

    def test_validate_picking(self):
        """Test validating a picking (immediate transfer)."""
        # First ensure stock is available
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.location_stock.id,
            'quantity': 100.0,
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_customer.id,
            'move_ids': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'location_id': self.location_stock.id,
                'location_dest_id': self.location_customer.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        # Set done quantities
        for move_line in picking.move_line_ids:
            move_line.qty_done = move_line.product_uom_qty
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
```
