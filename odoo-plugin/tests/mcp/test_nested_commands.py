"""Hard-deny and the unlink gate must hold inside x2many command tuples.

RA-ODOO-01: before the fix, guards decided on (model, op) only, so in write mode
`odoo_write res.partner {"user_ids": [[1, uid, {"groups_id": [[4, gid]]}]]}`
updated res.users and `{"child_ids": [[2, id]]}` deleted records without
write+unlink. These tests drive the guard directly and through the tool
handlers with a fake client (no live Odoo).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parents[1] / "mcp"
sys.path.insert(0, str(MCP_DIR))

import guards  # noqa: E402
import tools  # noqa: E402
from guards import GuardError  # noqa: E402
from profiles import Profile  # noqa: E402

META = {
    "res.partner": {
        "name": {"type": "char"},
        "user_ids": {"type": "one2many", "relation": "res.users"},
        "child_ids": {"type": "one2many", "relation": "res.partner"},
        "category_id": {"type": "many2many", "relation": "res.partner.category"},
        "bank_ids": {"type": "one2many", "relation": "res.partner.bank"},
        "properties": {"type": "properties"},
    },
    "res.partner.bank": {
        "acc_number": {"type": "char"},
        "allowed_group_ids": {"type": "many2many", "relation": "res.groups"},
    },
    "res.partner.category": {"name": {"type": "char"}},
    "sale.order": {
        "order_line": {"type": "one2many", "relation": "sale.order.line"},
        "tag_ids": {"type": "many2many", "relation": "crm.tag"},
    },
    "sale.order.line": {"name": {"type": "char"}},
    "res.users": {"groups_id": {"type": "many2many", "relation": "res.groups"}},
}


def fields_of(model):
    if model not in META:
        raise RuntimeError("fields_get failed for %s" % model)
    return META[model]


def _prof(mode="write", **kw):
    return Profile(name="local", url="http://127.0.0.1:1", db="t",
                   ceiling="write+unlink", mode=mode, **kw)


def check(values, model="res.partner", op="write", mode="write", **kw):
    guards.check_nested_values(_prof(mode, **kw), model, values, op, fields_of)


# ------------------------------------------------------------ hard-deny

@pytest.mark.parametrize("mode", ["write", "write+unlink"])
def test_update_through_o2m_to_res_users_is_refused(mode):
    with pytest.raises(GuardError, match="res.users.*blocked"):
        check({"user_ids": [[1, 7, {"groups_id": [[4, 2]]}]]}, mode=mode)


@pytest.mark.parametrize("cmd", [
    [0, 0, {"login": "x"}], [1, 7, {"name": "x"}], [3, 7], [4, 7], [5, 0, 0], [6, 0, [7]],
])
def test_every_command_on_a_denied_comodel_is_refused(cmd):
    with pytest.raises(GuardError, match="blocked"):
        check({"user_ids": [cmd]})


def test_plain_id_list_is_set_and_refused_on_denied_comodel():
    with pytest.raises(GuardError, match="blocked"):
        check({"allowed_group_ids": [1, 2]}, model="res.partner.bank")


def test_deny_is_found_in_deeply_nested_values():
    vals = {"bank_ids": [[0, 0, {"acc_number": "1", "allowed_group_ids": [[4, 1]]}]]}
    with pytest.raises(GuardError, match="res.partner.bank.allowed_group_ids.*res.groups"):
        check(vals, op="create")


def test_allow_write_models_opt_in_covers_nested_too():
    check({"user_ids": [[1, 7, {"name": "x"}]]},
          allow_write_models=frozenset({"res.users"}))


def test_create_vals_list_is_walked():
    with pytest.raises(GuardError, match="blocked"):
        check([{"name": "ok"}, {"user_ids": [[0, 0, {"login": "x"}]]}], op="create")


# ------------------------------------------------------------ unlink gate

def test_delete_command_needs_write_plus_unlink():
    with pytest.raises(GuardError, match="write\\+unlink"):
        check({"child_ids": [[2, 5]]})
    check({"child_ids": [[2, 5]]}, mode="write+unlink")


def test_delete_command_on_m2m_needs_write_plus_unlink():
    with pytest.raises(GuardError, match="write\\+unlink"):
        check({"category_id": [[2, 5]]})


@pytest.mark.parametrize("cmd", [[3, 5], [5, 0, 0], [6, 0, [1]]])
def test_o2m_unlink_clear_set_on_existing_record_need_write_plus_unlink(cmd):
    with pytest.raises(GuardError, match="write\\+unlink"):
        check({"order_line": [cmd]}, model="sale.order")
    check({"order_line": [cmd]}, model="sale.order", mode="write+unlink")


def test_m2m_unlink_clear_set_are_ordinary_writes():
    for cmd in ([3, 5], [4, 5], [5, 0, 0], [6, 0, [1, 2]]):
        check({"tag_ids": [cmd]}, model="sale.order")
    check({"tag_ids": [1, 2]}, model="sale.order")


def test_delete_nested_inside_update_is_found():
    with pytest.raises(GuardError, match="write\\+unlink"):
        check({"child_ids": [[1, 3, {"child_ids": [[2, 9]]}]]})


# ------------------------------------------------------------ normal use / fail closed

def test_ordinary_nested_create_passes():
    check({"order_line": [[0, 0, {"name": "line"}], [0, 0, {"name": "line 2"}]]},
          model="sale.order", op="create")
    check({"name": "x", "properties": [{"name": "p", "value": 1}]})


def test_unresolvable_comodel_refuses_commands():
    with pytest.raises(GuardError, match="could not be resolved"):
        check({"mystery_ids": [[4, 1]]})
    with pytest.raises(GuardError, match="could not be resolved"):
        check({"order_line": [[0, 0, {"x": 1}]]}, model="unknown.model")


def test_failed_fields_get_refuses_plain_id_lists_too():
    with pytest.raises(GuardError, match="could not be resolved"):
        check({"group_ids": [1, 2]}, model="unknown.model")


def test_values_without_lists_never_call_fields_get():
    def boom(model):
        raise AssertionError("fields_get should not be needed")
    guards.check_nested_values(_prof(), "res.partner", {"name": "x", "active": True},
                               "write", boom)


# ------------------------------------------------------------ tool handlers (fake client)

class FakeClient:
    def __init__(self):
        self.sent = []
        self.fields_calls = []

    def fields_get(self, model, attributes=None, context=None):
        self.fields_calls.append(model)
        return fields_of(model)

    def create(self, model, values, context=None):
        self.sent.append(("create", model, values))
        return [1]

    def write(self, model, ids, values, context=None):
        self.sent.append(("write", model, values))
        return True

    def call(self, model, method, ids=None, kwargs=None, context=None):
        self.sent.append((method, model, kwargs))
        return True


class FakeSession:
    def __init__(self, mode="write"):
        self.prof = _prof(mode)
        self.c = FakeClient()

    def client(self):
        return self.c

    def load(self, force=False):
        return self.prof, None

    def secrets(self):
        return ()


def test_odoo_write_refuses_and_sends_nothing():
    sess = FakeSession()
    with pytest.raises(GuardError, match="blocked"):
        tools._write(sess, {"model": "res.partner", "ids": [1],
                            "values": {"user_ids": [[1, 7, {"groups_id": [[4, 2]]}]]}})
    with pytest.raises(GuardError, match="write\\+unlink"):
        tools._write(sess, {"model": "res.partner", "ids": [1],
                            "values": {"child_ids": [[2, 5]]}})
    assert sess.c.sent == []


def test_odoo_create_walks_values():
    sess = FakeSession()
    with pytest.raises(GuardError, match="blocked"):
        tools._create(sess, {"model": "res.partner",
                             "values": {"user_ids": [[0, 0, {"login": "x"}]]}})
    assert sess.c.sent == []
    tools._create(sess, {"model": "sale.order",
                         "values": {"order_line": [[0, 0, {"name": "l"}]]}})
    assert sess.c.sent and sess.c.fields_calls.count("sale.order") == 1


def test_odoo_call_walks_kwargs():
    sess = FakeSession()
    with pytest.raises(GuardError, match="blocked"):
        tools._call(sess, {"model": "res.partner", "method": "write", "ids": [1],
                           "kwargs": {"vals": {"user_ids": [[4, 7]]}}})
    with pytest.raises(GuardError, match="write\\+unlink"):
        tools._call(sess, {"model": "res.partner", "method": "create",
                           "kwargs": {"vals_list": [{"child_ids": [[2, 5]]}]}})
    assert sess.c.sent == []


def test_odoo_call_read_methods_are_not_walked():
    sess = FakeSession(mode="read")
    tools._call(sess, {"model": "res.partner", "method": "search_read",
                       "kwargs": {"domain": [["user_ids", "in", [1, 2]]]}})
    assert sess.c.fields_calls == []


@pytest.mark.parametrize("model", ["website.page", "base.module.upgrade",
                                   "res.config.settings", "change.password.wizard"])
def test_inherits_and_wizard_models_are_hard_denied(model):
    with pytest.raises(GuardError, match="blocked"):
        guards.check_write_allowed(_prof("write+unlink"), model, "create")
