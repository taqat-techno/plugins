"""odoo_call must not be a way around the dedicated write tools' gates.

Before the fix, check_call_allowed only checked "is the session in write mode",
so in write mode `odoo_call res.users write` (privilege escalation),
`odoo_call ir.config_parameter set_param` (secrets) and
`odoo_call res.partner unlink` (delete without write+unlink) all went through,
although odoo_write / odoo_unlink refuse exactly those.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parents[1] / "mcp"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(HERE))

import guards  # noqa: E402
from guards import GuardError  # noqa: E402
from config import Instance  # noqa: E402
from test_mcp_server import Client, _profile_dir  # noqa: E402


def _prof(mode="write", tier="local", access="full", **kw):
    return Instance(project="t", name="local", url="http://127.0.0.1:1", db="t", db_auto=False,
                    username="u", api_key="k", tier=tier, access=access, mode=mode, **kw)


# ---------------------------------------------------------------- unit level

@pytest.mark.parametrize("model,method", [
    ("res.users", "write"),
    ("res.users", "create"),
    ("res.groups", "write"),
    ("ir.config_parameter", "set_param"),
    ("ir.actions.server", "copy"),
    ("ir.ui.view", "write"),
])
def test_hard_deny_models_refused_through_call(model, method):
    for mode in ("write", "write+unlink"):
        with pytest.raises(GuardError, match="blocked"):
            guards.check_call_allowed(_prof(mode), model, method)


def test_unlink_through_call_needs_write_plus_unlink():
    with pytest.raises(GuardError, match="write\\+unlink"):
        guards.check_call_allowed(_prof("write"), "res.partner", "unlink")
    guards.check_call_allowed(_prof("write+unlink"), "res.partner", "unlink")


def test_call_matches_the_dedicated_tools_decision():
    """Same profile, same model: odoo_call and odoo_write/unlink agree."""
    for mode in ("write", "write+unlink"):
        prof = _prof(mode)
        for model in ("res.partner", "res.users", "ir.config_parameter"):
            for method, op in (("write", "write"), ("create", "create"),
                               ("unlink", "unlink")):
                def outcome(fn, *a):
                    try:
                        fn(*a)
                        return "ok"
                    except GuardError:
                        return "refused"
                assert outcome(guards.check_call_allowed, prof, model, method) == \
                    outcome(guards.check_write_allowed, prof, model, op), (mode, model, method)


def test_allow_write_models_opt_in_still_works():
    prof = _prof("write", allow_write_models=frozenset({"ir.config_parameter"}))
    guards.check_call_allowed(prof, "ir.config_parameter", "set_param")


def test_ordinary_business_methods_still_pass_in_write_mode():
    guards.check_call_allowed(_prof("write"), "sale.order", "action_confirm")
    guards.check_call_allowed(_prof("write"), "res.partner", "action_archive")


def test_stage_read_access_hint_names_the_cli_and_approval():
    with pytest.raises(GuardError, match=r"access 'read'.*--approved-by"):
        guards.check_write_allowed(_prof("read", tier="stage", access="read"), "res.partner", "write")


def test_locked_prod_hint_names_the_unlock():
    with pytest.raises(GuardError, match="odoo_session action=unlock instance=t/local"):
        guards.check_write_allowed(_prof("read", tier="prod", access="write"), "res.partner", "write")


def test_read_methods_on_hard_deny_models_still_pass_in_read_mode():
    guards.check_call_allowed(_prof("read"), "res.users", "search_read")
    with pytest.raises(GuardError, match="read-only"):
        guards.check_call_allowed(_prof("read"), "res.partner", "action_archive")


def test_invalid_model_name_is_refused_by_the_call_gate():
    with pytest.raises(GuardError, match="invalid model name"):
        guards.check_call_allowed(_prof("write"), "Res.Users", "write")


# ------------------------------------------- end to end through the MCP server

def _call(c, model, method, **extra):
    args = {"model": model, "method": method, "ids": [1]}
    args.update(extra)
    return c.text("odoo_call", args)


def test_acceptance_odoo_call_refusals_in_write_mode():
    with tempfile.TemporaryDirectory() as td:
        env = _profile_dir(Path(td), access="write")
        with Client(env_extra=env) as c:
            c.handshake()
            text, is_error = _call(c, "res.users", "write", kwargs={"vals": {"groups_id": [4]}})
            assert is_error is True and "blocked" in text.lower(), text

            text, is_error = _call(c, "ir.config_parameter", "set_param",
                                   kwargs={"key": "x", "value": "y"})
            assert is_error is True and "blocked" in text.lower(), text

            text, is_error = _call(c, "res.partner", "unlink")
            assert is_error is True and "write+unlink" in text, text


def test_hard_deny_holds_through_call_even_with_unlink_allowed():
    with tempfile.TemporaryDirectory() as td:
        env = _profile_dir(Path(td), access="full")
        with Client(env_extra=env) as c:
            c.handshake()
            text, is_error = _call(c, "res.users", "unlink")
            assert is_error is True and "blocked" in text.lower(), text


# ------------------------------------------------ kwargs.context (ODOO-P1-02)

def test_kwargs_context_denied_key_is_refused_end_to_end():
    with tempfile.TemporaryDirectory() as td:
        env = _profile_dir(Path(td), access="write")
        with Client(env_extra=env) as c:
            c.handshake()
            text, is_error = _call(c, "sale.order", "action_confirm",
                                   kwargs={"context": {"tracking_disable": True}})
            assert is_error is True and "tracking_disable" in text, text


def test_kwargs_context_must_be_an_object():
    with tempfile.TemporaryDirectory() as td:
        env = _profile_dir(Path(td), access="write")
        with Client(env_extra=env) as c:
            c.handshake()
            text, is_error = _call(c, "sale.order", "action_confirm",
                                   kwargs={"context": "tracking_disable"})
            assert is_error is True and "kwargs.context" in text, text


def test_client_folds_kwargs_context_into_the_merged_context():
    import odoo_client

    prof = _prof(lang="ar_001")
    client = odoo_client.OdooClient(prof)
    client._flavor = "json2"
    seen = {}

    def fake(model, method, ids, args, kwargs):
        seen.update(kwargs)
        return True

    client._call_json2 = fake
    client.call("res.partner", "read", ids=[1],
                kwargs={"context": {"active_test": False}}, context={"tz": "UTC"})
    assert seen["context"] == {"lang": "ar_001", "active_test": False, "tz": "UTC"}
