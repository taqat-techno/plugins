"""The migration advice in the write guard and scripts/test/reverse_dependents.py.

Offline: every module lives in a temp directory. The migration rule itself
(installed < folder <= manifest, pre-/post-/end- file names) is Odoo's
odoo/modules/migration.py, the same in 17.0, 18.0 and 19.0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "upgrade" / "guard_core_odoo.py"
SCRIPT = PLUGIN_ROOT / "scripts" / "test" / "reverse_dependents.py"
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "upgrade"))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts" / "test"))

import migration_advice  # noqa: E402
import reverse_dependents  # noqa: E402


def _module(tmp_path, name="mod", version="17.0.1.1.0", depends=(), tests=False, extra=""):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "__manifest__.py").write_text(
        "{'name': %r, 'version': %r, 'depends': %r%s}" % (name, version, list(depends), extra), encoding="utf-8")
    if tests:
        (d / "tests").mkdir(exist_ok=True)
    return d


def _hook(path, tool="Write", **env):
    e = {k: v for k, v in os.environ.items() if k not in ("ODOO_MIGRATION_GUARD", "CLAUDE_PROJECT_DIR")}
    e.update(env)
    payload = {"tool_name": tool, "tool_input": {"file_path": str(path), "content": "x"}}
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=e, timeout=30)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.decode("utf-8", "replace").strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


# --------------------------------------------------------------------- migration advice

def test_a_file_name_odoo_never_loads_is_called_out(tmp_path):
    mod = _module(tmp_path)
    out = _hook(mod / "migrations" / "17.0.1.1.0" / "post_migrate.py")
    assert out["hookEventName"] == "PreToolUse" and "permissionDecision" not in out
    assert "will never run" in out["additionalContext"] and "post-*.py" in out["additionalContext"]


def test_a_folder_above_the_manifest_version_is_called_out(tmp_path):
    mod = _module(tmp_path, version="17.0.1.1.0")
    out = _hook(mod / "migrations" / "17.0.1.2.0" / "post-migrate.py")
    assert "above the manifest version" in out["additionalContext"]


def test_a_new_script_inside_the_window_gets_the_version_reminder_only(tmp_path):
    mod = _module(tmp_path, version="17.0.1.2.0")
    text = _hook(mod / "migrations" / "17.0.1.2.0" / "pre-migrate.py")["additionalContext"]
    assert "installed version" in text and "will never run" not in text and "above the manifest" not in text


def test_editing_a_committed_migration_is_called_out(tmp_path, monkeypatch):
    mod = _module(tmp_path, version="17.0.1.2.0")
    f = mod / "migrations" / "17.0.1.2.0" / "post-migrate.py"
    f.parent.mkdir(parents=True)
    f.write_text("def migrate(cr, version):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(migration_advice, "_committed", lambda p: True)
    notes = "\n".join(migration_advice.advise(str(f), "Edit"))
    assert "already committed" in notes and "new" in notes and "latest_version" in notes
    monkeypatch.setattr(migration_advice, "_committed", lambda p: False)
    assert migration_advice.advise(str(f), "Edit") == []      # an uncommitted draft is yours to edit


def test_silent_outside_a_module_for_init_files_and_when_switched_off(tmp_path):
    assert _hook(tmp_path / "notamodule" / "migrations" / "1.0" / "post_x.py") is None
    mod = _module(tmp_path)
    assert _hook(mod / "migrations" / "17.0.1.1.0" / "__init__.py") is None
    assert _hook(mod / "models" / "post_migrate.py") is None
    assert _hook(mod / "migrations" / "17.0.1.1.0" / "post_migrate.py", ODOO_MIGRATION_GUARD="off") is None


def test_upgrades_folder_is_covered_too(tmp_path):
    mod = _module(tmp_path)
    assert "will never run" in _hook(mod / "upgrades" / "17.0.1.1.0" / "migrate.py")["additionalContext"]


# --------------------------------------------------------------------- reverse dependents

def _tree(tmp_path):
    _module(tmp_path, "base_x", tests=True)
    _module(tmp_path, "sale_x", depends=["base_x"], tests=True)
    _module(tmp_path, "report_x", depends=["sale_x"])
    _module(tmp_path, "bridge_x", depends=["sale_x", "other"], tests=True, extra=", 'auto_install': True")
    _module(tmp_path, "lonely", tests=True)
    (tmp_path / "lonely" / "models.py").write_text("class P:\n    _inherit = 'res.partner'\n", encoding="utf-8")
    (tmp_path / "sale_x" / "models.py").write_text("class P:\n    _inherit = ['mail.thread', 'res.partner']\n",
                                                  encoding="utf-8")
    return tmp_path


def test_reverse_dependents_are_transitive_and_nearest_first(tmp_path):
    mods = reverse_dependents.find_modules([str(_tree(tmp_path))])
    assert reverse_dependents.reverse_dependents("base_x", mods) == ["sale_x", "bridge_x", "report_x"]
    assert reverse_dependents.reverse_dependents("base_x", mods, direct=True) == ["sale_x"]
    assert reverse_dependents.reverse_dependents("lonely", mods) == []


def test_model_inheritors_are_found_without_a_dependency(tmp_path):
    mods = reverse_dependents.find_modules([str(_tree(tmp_path))])
    assert reverse_dependents.inheritors("res.partner", mods) == ["lonely", "sale_x"]


def test_cli_prints_a_test_tags_selector_for_modules_with_tests(tmp_path, capsys):
    root = str(_tree(tmp_path))
    assert reverse_dependents.main(["base_x", "--addons", root, "--model", "res.partner", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [d["module"] for d in doc["dependents"]] == ["sale_x", "bridge_x", "report_x", "lonely"]
    assert doc["test_tags"] == "/base_x,/sale_x,/bridge_x,/lonely"       # report_x has no tests
    assert doc["dependents"][-1]["via"] == "inherits res.partner"
    assert reverse_dependents.main(["missing", "--addons", root]) == 2


def test_script_runs_as_a_program(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPT), "base_x", "--addons", str(_tree(tmp_path))],
                          capture_output=True, timeout=30)
    assert proc.returncode == 0 and b"--test-tags /base_x,/sale_x,/bridge_x" in proc.stdout
