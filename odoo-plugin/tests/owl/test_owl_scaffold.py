"""Tests for scripts/owl/owl_scaffold.py.

The load-bearing test is `test_generated_module_lints_clean`: the scaffold and
the linter are two halves of the same opinion, so the generator's output must
satisfy the checker. If that ever fails, one of the two is wrong.

Run standalone:   python tests/owl/test_owl_scaffold.py
Run under pytest: pytest tests/owl/test_owl_scaffold.py
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = PLUGIN_ROOT / "scripts" / "owl" / "owl_scaffold.py"
LINT = PLUGIN_ROOT / "scripts" / "owl" / "owl_lint.py"

APP = "my_console"


def scaffold(dest: Path, *extra, name: str = APP) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), "--name", name, "--dest", str(dest), *extra],
        capture_output=True, text=True, encoding="utf-8",
    )


def make(dest: Path, name: str = APP) -> Path:
    proc = scaffold(dest, name=name)
    assert proc.returncode == 0, "scaffold failed: %s%s" % (proc.stdout, proc.stderr)
    return dest / name


def lint(path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(LINT), str(path), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(proc.stdout)


# --------------------------------------------------------------------------
# The dogfood
# --------------------------------------------------------------------------

def test_generated_module_lints_clean():
    """The generator and the checker must agree. No findings at any severity."""
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        result = lint(mod)
        assert result["findings"] == [], (
            "scaffold output does not satisfy owl_lint:\n%s"
            % json.dumps(result["findings"], indent=2)
        )


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------

def test_creates_the_expected_layout():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        for rel in (
            "__manifest__.py",
            "controllers/main.py",
            "models/%s_config.py" % APP,
            "models/%s_load_mixin.py" % APP,
            "security/ir.model.access.csv",
            "views/%s_assets_index.xml" % APP,
            "static/src/utils.js",
            "static/src/app/main.js",
            "static/src/app/%s_app.js" % APP,
            "static/src/app/%s_app.xml" % APP,
            "static/src/app/hooks/use_store.js",
            "static/src/app/services/%s_store.js" % APP,
            "static/src/app/services/data_service.js",
            "static/src/app/components/loader/loader.js",
            "static/src/app/screens/home_screen/home_screen.js",
            "static/tests/unit/utils.js",
        ):
            assert (mod / rel).is_file(), "missing %s" % rel


def test_manifest_parses_and_declares_the_bundle_triple():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        text = (mod / "__manifest__.py").read_text(encoding="utf-8")
        manifest = ast.literal_eval(text)
        assets = manifest["assets"]

        for bundle in ("%s.base_app" % APP, "%s._assets_app" % APP, "%s.assets_prod" % APP):
            assert bundle in assets, "missing bundle %s" % bundle

        private = assets["%s._assets_app" % APP]
        prod = assets["%s.assets_prod" % APP]

        # main.js is removed from the private bundle and appended last to prod.
        assert ("remove", "%s/static/src/app/main.js" % APP) in [
            tuple(e) for e in private if not isinstance(e, str)
        ], "private bundle must remove main.js"
        assert prod[-1] == "%s/static/src/app/main.js" % APP, \
            "main.js must be the LAST entry of assets_prod"
        assert ("include", "%s._assets_app" % APP) in [
            tuple(e) for e in prod if not isinstance(e, str)
        ], "assets_prod must include the private bundle"


def test_test_bundle_removes_the_boot_file_again():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        assets = ast.literal_eval((mod / "__manifest__.py").read_text(encoding="utf-8"))["assets"]
        setup = [tuple(e) if not isinstance(e, str) else e
                 for e in assets["web.assets_unit_tests_setup"]]
        assert ("remove", "%s/static/src/app/main.js" % APP) in setup, \
            "the unit-test bundle must remove main.js so tests mount the app themselves"


# --------------------------------------------------------------------------
# Bootstrap correctness
# --------------------------------------------------------------------------

def test_index_document_is_standalone_with_an_empty_body():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        xml = (mod / "views" / ("%s_assets_index.xml" % APP)).read_text(encoding="utf-8")
        assert "DOCTYPE html" in xml, "a full OWL app needs its own HTML document"
        assert "loadMenusPromise" in xml, "must short-circuit the webclient menu service"
        assert 't-call-assets="%s.assets_prod"' % APP in xml
        assert re.search(r"<body[^>]*/>", xml), "body must be EMPTY - the root owns the DOM"


def test_main_js_mounts_from_web_env_not_the_webclient():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        js = (mod / "static/src/app/main.js").read_text(encoding="utf-8")
        assert 'from "@web/env"' in js
        assert "@web/webclient/webclient" not in js
        assert "mountComponent" in js


def test_root_renders_main_components_container():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        xml = (mod / "static/src/app" / ("%s_app.xml" % APP)).read_text(encoding="utf-8")
        assert "<MainComponentsContainer/>" in xml, \
            "without it, dialog/notification/overlay services silently render nothing"


# --------------------------------------------------------------------------
# Layer rules the scaffold must itself obey
# --------------------------------------------------------------------------

def test_only_the_data_service_touches_orm():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        offenders = []
        for f in (mod / "static/src/app").rglob("*.js"):
            if f.name == "data_service.js":
                continue
            src = f.read_text(encoding="utf-8")
            if re.search(r'useService\(\s*["\']orm["\']|\bdeps\.orm\b|\bthis\.orm\b', src):
                offenders.append(f.name)
        assert not offenders, "orm reached outside the data service: %s" % offenders


def test_components_use_the_hook_not_env_services():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        for sub in ("components", "screens"):
            for f in (mod / "static/src/app" / sub).rglob("*.js"):
                src = f.read_text(encoding="utf-8")
                assert "env.services." not in src, "%s captures env.services" % f.name


def test_screen_self_registers_at_module_top_level():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        src = (mod / "static/src/app/screens/home_screen/home_screen.js").read_text(
            encoding="utf-8")
        assert re.search(r'^registry\.category\(', src, re.M), \
            "registration must be at column 0, not nested in a function"


def test_store_is_reactive_and_registered_as_a_service():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        src = (mod / "static/src/app/services" / ("%s_store.js" % APP)).read_text(encoding="utf-8")
        assert "extends Reactive" in src, "a non-reactive store never drives a render"
        assert 'category("services").add("%s"' % APP in src


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        proc = scaffold(Path(td), "--dry-run")
        assert proc.returncode == 0
        assert "Would create" in proc.stdout
        assert not (Path(td) / APP).exists()


def test_refuses_to_overwrite_without_force():
    with tempfile.TemporaryDirectory() as td:
        make(Path(td))
        again = scaffold(Path(td))
        assert again.returncode == 2
        assert "already exists" in again.stderr
        forced = scaffold(Path(td), "--force")
        assert forced.returncode == 0


def test_rejects_a_bad_module_name():
    with tempfile.TemporaryDirectory() as td:
        for bad in ("My-Console", "9lives", "has space"):
            proc = scaffold(Path(td), name=bad)
            assert proc.returncode == 2, "accepted invalid name %r" % bad


def test_route_default_and_override():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td))
        ctrl = (mod / "controllers/main.py").read_text(encoding="utf-8")
        assert "'/%s/ui'" % APP in ctrl, "default route should be /<name>/ui"
    with tempfile.TemporaryDirectory() as td:
        proc = scaffold(Path(td), "--route", "/kiosk")
        assert proc.returncode == 0
        ctrl = (Path(td) / APP / "controllers/main.py").read_text(encoding="utf-8")
        assert "'/kiosk'" in ctrl


def test_name_is_substituted_everywhere():
    with tempfile.TemporaryDirectory() as td:
        mod = make(Path(td), name="widget_hub")
        for f in mod.rglob("*"):
            if not f.is_file():
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            for token in ("__APP__", "__TITLE__", "__CLASS__", "__ROUTE__", "__PAGES__"):
                assert token not in src, "unsubstituted %s in %s" % (token, f.name)


# --------------------------------------------------------------------------

def _run_all():
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    passed, failed = 0, []
    for name, fn in fns:
        try:
            fn()
            passed += 1
            print("  PASS  %s" % name)
        except AssertionError as exc:
            failed.append(name)
            print("  FAIL  %s\n        %s" % (name, str(exc)[:500]))
        except Exception as exc:
            failed.append(name)
            print("  ERROR %s\n        %s: %s" % (name, type(exc).__name__, str(exc)[:500]))
    print("\n%d passed, %d failed, %d total" % (passed, len(failed), len(fns)))
    return 1 if failed else 0


if __name__ == "__main__":
    print("owl_scaffold test suite\n" + "-" * 60)
    raise SystemExit(_run_all())
