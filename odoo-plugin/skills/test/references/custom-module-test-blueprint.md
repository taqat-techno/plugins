# Custom Module Test Suite Blueprint

The recommended `tests/` layout for a custom Odoo module, mirroring standard-addon structure. **Create only the files that are relevant to the module** — never scaffold empty files to look complete.

## Structure

```
<module_name>/
  tests/
    __init__.py          # trivial relative imports ONLY — one per test file
    common.py            # optional: <Module>Common(TransactionCase) shared fixtures
    test_models.py       # model logic, computed/related fields, constraints, onchange
    test_security.py     # ir.model.access + ir.rule, with_user, AccessError (if perms matter)
    test_wizards.py      # TransientModel launch + action + assertions (if wizards exist)
    test_workflows.py    # state machines / multi-step business flows (if stateful)
    test_controllers.py  # HttpCase routes (if controllers exist) — post_install
    test_reports.py      # QWeb/report rendering (if reports exist)
```

What belongs where:

| File | Put here |
|---|---|
| `common.py` | `<Module>Common(TransactionCase)` with `setUpClass` building shared users/companies/records + factory helpers. No `@tagged` (inherited). |
| `test_models.py` | `create`/`write` values, computed/related fields, `@api.depends` recompute, `@api.constrains`/`_sql_constraints`, `@api.onchange` via `Form`. Usually default `at_install`. |
| `test_security.py` | ACL + record-rule tests as a non-admin (`with_user`/`@users`); both allowed and forbidden paths. `@tagged('post_install','-at_install')`. |
| `test_wizards.py` | `TransientModel` launched via `with_context(active_ids=…)` or `Form`; action + side-effects + ACL + error path. |
| `test_workflows.py` | full state machine; assert `state` after each transition; multi-user approval via `with_user`. |
| `test_controllers.py` | `HttpCase` routes; status/headers/body; JSON error envelope. `@tagged('post_install','-at_install')`. |
| `test_reports.py` | `_render_qweb_html` content / `_get_report_values`. `@tagged('post_install','-at_install')`. |

## `tests/__init__.py`

Trivial relative imports only — a file not imported here **silently never runs**:

```python
from . import test_models
from . import test_security
from . import test_wizards
from . import test_workflows
from . import test_controllers
from . import test_reports
```

(Import only the files that exist.)

## `tests/common.py` skeleton

```python
from odoo.tests.common import TransactionCase, new_test_user
from odoo.fields import Command           # Odoo 13+

class ModuleCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.user_user = new_test_user(cls.env, login='tu_user',
                                      groups='base.group_user')
        cls.user_manager = new_test_user(cls.env, login='tu_manager',
                                         groups='base.group_user,<module_name>.group_manager')
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.record = cls.env['<model>'].create({
            'name': 'Fixture',
            'line_ids': [Command.create({'qty': 1.0})],
        })

    @classmethod
    def _make_record(cls, **vals):
        return cls.env['<model>'].create({'name': 'R', **vals})
```

## `test_models.py` skeleton

```python
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError
from .common import ModuleCommon

class TestModels(ModuleCommon):
    def test_default_state(self):
        self.assertEqual(self._make_record().state, 'draft')

    def test_amount_total_computed(self):
        self.assertEqual(self.record.amount_total, 1.0)

    def test_constraint_negative_qty(self):
        with self.assertRaises(ValidationError):
            self.record.line_ids.qty = -1

    @mute_logger('odoo.sql_db')
    def test_unique_name(self):
        with self.assertRaises(IntegrityError):
            self._make_record(name=self.record.name)
```

## `test_security.py` skeleton

```python
from odoo.tests import tagged
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from .common import ModuleCommon

@tagged('post_install', '-at_install')
class TestSecurity(ModuleCommon):
    @mute_logger('odoo.models')
    def test_user_cannot_write(self):
        with self.assertRaises(AccessError):
            self.record.with_user(self.user_user).write({'name': 'x'})

    def test_manager_can_write(self):
        self.record.with_user(self.user_manager).write({'name': 'ok'})
        self.assertEqual(self.record.name, 'ok')
```

## `test_wizards.py` skeleton

```python
from .common import ModuleCommon

class TestWizards(ModuleCommon):
    def test_wizard_apply(self):
        wiz = self.env['<wizard.model>'].with_context(
            active_model='<model>', active_ids=self.record.ids
        ).create({'mode': 'confirm'})
        wiz.action_apply()
        self.assertEqual(self.record.state, 'confirmed')
```

## `test_workflows.py` skeleton

```python
from odoo.tests import tagged
from odoo.exceptions import UserError
from .common import ModuleCommon

@tagged('post_install', '-at_install')
class TestWorkflows(ModuleCommon):
    def test_cycle(self):
        self.record.action_confirm()
        self.assertEqual(self.record.state, 'confirmed')
        self.record.action_done()
        self.assertEqual(self.record.state, 'done')

    def test_illegal_transition(self):
        self.record.action_done() if self.record.state == 'confirmed' else None
        with self.assertRaises(UserError):
            self.env['<model>'].create({'name': 'E'}).action_done()
```

## `test_controllers.py` skeleton

```python
from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user

@tagged('post_install', '-at_install')
class TestControllers(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='web_user', groups='base.group_user')

    def test_route_ok(self):
        self.authenticate('web_user', 'web_user')
        res = self.url_open('/<module_route>')
        self.assertEqual(res.status_code, 200)
```

## `test_reports.py` skeleton

```python
from odoo.tests import tagged
from .common import ModuleCommon

@tagged('post_install', '-at_install')
class TestReports(ModuleCommon):
    def test_render_html(self):
        html = self.env['ir.actions.report']._render_qweb_html(
            '<module_name>.<report_xmlid>', self.record.ids)[0]
        self.assertIn(b'Fixture', html)
```

## Manifest note

Tests are **not** declared in `__manifest__.py` — they are discovered by import from `tests/__init__.py`. Test-only data (a CSV/XML fixture used only by tests) can live under `tests/` and be loaded explicitly, or referenced from the module's regular `data` via `env.ref()`.
