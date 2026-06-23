# Odoo Test Pattern Catalogue

Reusable, version-neutral test structures distilled from Odoo standard-addon tests (`base`, `account`, `stock`, `sale`, `mail`, `web`, `portal`, and the dedicated `test_*` modules). Adapt the model/field names to the target module. Keep snippets short and concrete. For class names that differ by version (`SavepointCase`, `Command`, `<list>`, `jsonrpc`) see `odoo-version-matrix.md`.

All examples assume a shared base:

```python
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import tagged
from odoo.fields import Command            # Odoo 13+; older: legacy tuples
from odoo.exceptions import AccessError, ValidationError, UserError

class ModuleCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.user_internal = new_test_user(cls.env, login='int_user', groups='base.group_user')
        cls.user_manager = new_test_user(cls.env, login='mgr_user',
                                         groups='base.group_user,<module_name>.group_manager')
        cls.record = cls.env['<model>'].create({'name': 'Fixture A'})
```

---

## 1. Model logic (create / values / generated records)

```python
class TestModel(ModuleCommon):
    def test_create_sets_defaults(self):
        rec = self.env['<model>'].create({'name': 'X'})
        self.assertRecordValues(rec, [{'name': 'X', 'state': 'draft', 'active': True}])

    def test_action_generates_child(self):
        self.record.action_do_thing()
        self.assertEqual(len(self.record.line_ids), 1)
        self.assertRecordValues(self.record.line_ids, [{'qty': 1.0}])
```

`assertRecordValues(records, [dict, ...])` compares index-by-index (m2o → id, x2many → sorted ids). Reusable structure: build → act → assert values + generated records.

## 2. Computed / related fields

```python
def test_amount_total_recomputes(self):
    self.record.line_ids = [Command.create({'qty': 2, 'price': 10})]
    self.assertEqual(self.record.amount_total, 20.0)
    self.record.line_ids.qty = 3
    self.assertEqual(self.record.amount_total, 30.0)   # recompute on @api.depends change
```

## 3. Constraints

```python
def test_python_constraint(self):                       # @api.constrains
    with self.assertRaises(ValidationError):
        self.record.write({'qty': -1})

def test_sql_constraint(self):                          # _sql_constraints
    from odoo.tools import mute_logger
    from psycopg2 import IntegrityError
    with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
        self.env['<model>'].create({'name': self.record.name})   # unique violation
```

Always wrap the expected-error block in `mute_logger(...)` so CI logs stay clean.

## 4. Onchange / view defaults (via Form)

```python
from odoo.tests import Form

def test_partner_onchange_fills_pricelist(self):
    form = Form(self.env['<model>'])
    form.partner_id = self.partner            # fires @api.onchange synchronously
    self.assertEqual(form.pricelist_id, self.partner.property_product_pricelist)
    rec = form.save()
    self.assertTrue(rec.id)
```

Use `Form` to exercise the *same* path as a user; raw `create()` skips onchange side-effects.

## 5. Workflow / state transitions

```python
@tagged('post_install', '-at_install')
class TestWorkflow(ModuleCommon):
    def test_full_cycle(self):
        self.assertEqual(self.record.state, 'draft')
        self.record.action_confirm()
        self.assertEqual(self.record.state, 'confirmed')
        self.record.action_done()
        self.assertEqual(self.record.state, 'done')

    def test_cannot_confirm_empty(self):
        empty = self.env['<model>'].create({'name': 'E'})
        with self.assertRaises(UserError):
            empty.action_confirm()
```

Assert `state` after **each** transition, plus the negative (illegal transition raises).

## 6. Access rights (ir.model.access)

```python
@tagged('post_install', '-at_install')
class TestAccess(ModuleCommon):
    def test_internal_user_cannot_write(self):
        from odoo.tools import mute_logger
        rec = self.record.with_user(self.user_internal)
        with mute_logger('odoo.models'), self.assertRaises(AccessError):
            rec.write({'name': 'nope'})

    def test_manager_can_write(self):
        self.record.with_user(self.user_manager).write({'name': 'ok'})
        self.assertEqual(self.record.name, 'ok')
```

Test the **forbidden** and the **allowed** path; run as a non-admin via `with_user`.

## 7. Record rules (ir.rule)

```python
@tagged('post_install', '-at_install')
class TestRecordRule(ModuleCommon):
    def test_user_sees_only_own(self):
        mine = self.env['<model>'].create({'name': 'mine', 'user_id': self.user_internal.id})
        other = self.env['<model>'].create({'name': 'other', 'user_id': self.user_manager.id})
        visible = self.env['<model>'].with_user(self.user_internal).search([])
        self.assertIn(mine, visible)
        self.assertNotIn(other, visible)
```

Invalidate cache between privilege levels if a record was first read as admin:
`self.env.invalidate_all()`.

## 8. The `@users` decorator (run a body per login)

```python
from odoo.tests.common import users

@tagged('post_install', '-at_install')
class TestPerUser(ModuleCommon):
    @users('int_user', 'mgr_user')
    def test_read_scope(self):
        # self.env.user is the decorated login; body runs once per login
        recs = self.env['<model>'].search([])
        self.assertTrue(all(r.user_id == self.env.user or self.env.user.has_group(
            '<module_name>.group_manager') for r in recs))
```

## 9. Wizard (TransientModel)

```python
class TestWizard(ModuleCommon):
    def test_wizard_via_context(self):
        wiz = self.env['<wizard.model>'].with_context(
            active_model='<model>', active_ids=self.record.ids
        ).create({'mode': 'confirm'})
        res = wiz.action_apply()
        self.assertEqual(self.record.state, 'confirmed')
        self.assertEqual(res.get('type'), 'ir.actions.act_window')   # if it returns an action

    def test_wizard_via_form(self):                                  # when the wizard has onchanges
        from odoo.tests import Form
        wiz_form = Form(self.env['<wizard.model>'].with_context(active_ids=self.record.ids))
        wiz_form.qty = 5
        wiz = wiz_form.save()
        wiz.action_apply()
```

For a wizard launched by a button that returns an action dict, use `Form.from_action(self.env, action_dict)`.

## 10. Controller / HTTP route

```python
from odoo.tests.common import HttpCase

@tagged('post_install', '-at_install')
class TestController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='web_user', groups='base.group_user')

    def test_public_route(self):
        res = self.url_open('/<module_route>')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Expected', res.text)

    def test_authenticated_route(self):
        self.authenticate('web_user', 'web_user')
        res = self.url_open('/<module_route>/secure')
        self.assertEqual(res.status_code, 200)
```

For JSON routes, the HTTP status is 200 even on app errors — inspect the JSON `error` envelope (use `make_jsonrpc_request(route, params)` where the version provides it). Wrap deliberate-error tests in `mute_logger('odoo.http')`.

## 11. Report / QWeb

```python
@tagged('post_install', '-at_install')
class TestReport(ModuleCommon):
    def test_report_renders_content(self):
        html = self.env['ir.actions.report']._render_qweb_html(
            '<module_name>.<report_xmlid>', self.record.ids)[0]
        self.assertIn(b'Expected label', html)

    def test_report_values(self):
        report = self.env.ref('<module_name>.<report_action_xmlid>')
        values = report._get_report_values(self.record.ids)
        self.assertIn(self.record, values['docs'])
```

Prefer HTML content / report-values assertions over brittle full-PDF byte comparisons.

## 12. Mail / activity

```python
def test_post_message_and_activity(self):
    # If the module uses mail.thread, prefer the module's MailCommon mock base.
    self.record.message_post(body='Hello')
    self.assertIn('Hello', self.record.message_ids[0].body)

def test_activity_scheduled(self):
    act = self.record.activity_schedule('<module_name>.mail_activity_type_x',
                                        user_id=self.user_manager.id)
    self.assertEqual(act.user_id, self.user_manager)
```

When the addon sends email, mock the gateway (e.g. inherit the standard `MailCommon` / `mock_mail_gateway`) so no SMTP is hit; flush tracking before asserting tracking values; read tracking via `sudo()`.

## 13. Multi-company / multi-currency

```python
@tagged('post_install', '-at_install')
class TestMultiCompany(ModuleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})

    def test_company_isolation(self):
        rec_b = self.env['<model>'].with_company(self.company_b).create({'name': 'B'})
        self.assertEqual(rec_b.company_id, self.company_b)

    def test_check_company_consistency(self):
        with self.assertRaises(UserError):
            self.env['<model>'].create({
                'company_id': self.company_b.id,
                'parent_id': self.record.id,        # belongs to another company
            })
```

Drive company scope with `with_company` / `with_context(allowed_company_ids=ids)` — never poke `env.context` by hand.

## 14. JS / browser tour

Python launcher (`HttpCase`):
```python
@tagged('post_install', '-at_install')
class TestTour(HttpCase):
    def test_my_tour(self):
        self.start_tour('/odoo', 'my_module_tour', login='admin')
```
JS definition (in `static/tests/tours/` or `static/src/...`), registered under the tour registry with the **same id** (`my_module_tour`). The test passes only when the tour completes; a failing step fails the test.

## 15. Regression test for a bugfix

```python
def test_regression_issue_NNN_zero_qty_no_crash(self):
    """Proves the fix for <short description>; fails on the pre-fix code."""
    rec = self.env['<model>'].create({'name': 'Z', 'qty': 0})
    rec.action_compute()                 # used to raise ZeroDivisionError
    self.assertEqual(rec.unit_price, 0.0)
```

A regression test must assert the exact previously-broken behavior and would fail on the old code.
