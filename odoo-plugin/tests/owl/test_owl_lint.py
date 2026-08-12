"""Tests for scripts/owl/owl_lint.py.

Two halves, both of which matter:

  * TRUE POSITIVES - a synthetic module containing each anti-pattern verbatim
    must produce the matching rule id.
  * FALSE POSITIVES - correct code written the way Odoo core writes it must
    produce nothing. A linter that cries wolf on the reference implementation
    gets switched off, which is worse than having no linter.

Run standalone:   python tests/owl/test_owl_lint.py
Run under pytest: pytest tests/owl/test_owl_lint.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
LINT = PLUGIN_ROOT / "scripts" / "owl" / "owl_lint.py"


def run(path: Path, *extra) -> dict:
    proc = subprocess.run(
        [sys.executable, str(LINT), str(path), "--format", "json", *extra],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.stdout.strip(), "linter produced no output\nstderr: %s" % proc.stderr
    return json.loads(proc.stdout)


def rules(result: dict, severity: str | None = None) -> set:
    return {f["rule"] for f in result["findings"]
            if severity is None or f["severity"] == severity}


def write_module(root: Path, name: str, manifest: str, files: dict) -> Path:
    mod = root / name
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "__manifest__.py").write_text(manifest, encoding="utf-8")
    for rel, content in files.items():
        p = mod / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return mod


GOOD_MANIFEST = """{
    'name': 'Good Module',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'good_mod/static/src/**/*',
        ],
    },
}
"""


# --------------------------------------------------------------------------
# True positives
# --------------------------------------------------------------------------

def test_a1_file_outside_every_glob():
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "bad_mod", """{
    'name': 'Bad', 'assets': {'web.assets_backend': ['bad_mod/static/src/**/*']},
}""", {"static/js/orphan.js": "export const x = 1;\n"})
        assert "A1" in rules(run(mod), "error")


def test_a1_clean_when_glob_covers_everything():
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/thing.js": "export const x = 1;\n"})
        assert "A1" not in rules(run(mod))


def test_a3_removing_another_modules_file():
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "rm_mod", """{
    'name': 'Rm',
    'assets': {'point_of_sale._assets_pos': [
        ('remove', 'web/static/src/core/errors/error_handlers.js'),
    ]},
}""", {})
        assert "A3" in rules(run(mod))


def test_stale_patterns_detected():
    stale_js = """
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
registry.category("pos_screens").add("X", {});
export function f(pos) {
    pos.showScreen("ProductScreen");
    return PosGlobalState;
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/stale.js": stale_js})
        found = rules(run(mod))
        for rid in ("S-POSSCREENS", "S-SHOWSCREEN", "S-POSGLOBAL"):
            assert rid in found, "missing %s (got %s)" % (rid, sorted(found))


def test_three_argument_patch_is_an_error():
    js = """
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
patch(PosOrder.prototype, "my_module.PosOrder", { setup() {} });
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/p.js": js})
        assert "S-PATCHNAME" in rules(run(mod), "error")


def test_raw_prototype_assignment():
    js = """
import { PosOrder } from "@point_of_sale/app/models/pos_order";
PosOrder.prototype.myMethod = function () { return 1; };
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/p.js": js})
        assert "P5" in rules(run(mod), "error")


def test_env_services_in_a_component():
    js = """
import { Component } from "@odoo/owl";
export class MyScreen extends Component {
    setup() {
        this.pos = this.env.services.pos;
    }
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/screens/my_screen.js": js})
        assert "S3" in rules(run(mod), "error")


def test_use_service_in_a_component_is_clean():
    js = """
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class MyScreen extends Component {
    setup() {
        this.pos = useService("pos");
    }
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/screens/my_screen.js": js})
        assert "S3" not in rules(run(mod))


def test_one_shot_registry_not_at_top_level():
    js = """
import { registry } from "@web/core/registry";
export function setupLater() {
    registry.category("pos_pages").add("MyPage", { component: null });
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/r.js": js})
        assert "R2" in rules(run(mod), "error")


def test_top_level_registration_is_clean():
    js = """
import { registry } from "@web/core/registry";
registry.category("pos_pages").add("MyPage", { component: null });
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/r.js": js})
        assert "R2" not in rules(run(mod))


def test_live_category_late_registration_is_not_flagged():
    """services / web_tour.tours re-read after boot; flagging them is noise."""
    js = """
import { registry } from "@web/core/registry";
export function later() {
    registry.category("services").add("thing", { start() {} });
    registry.category("web_tour.tours").add("t", { steps: () => [] });
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/r.js": js})
        assert "R2" not in rules(run(mod))


def test_force_replacing_a_service():
    js = """
import { registry } from "@web/core/registry";
registry.category("services").add("pos", myPosService, { force: true });
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/s.js": js})
        assert "S1" in rules(run(mod), "error")


def test_patch_without_super():
    js = """
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
patch(PosStore.prototype, {
    async setup(...args) {
        this.thing = 1;
    },
});
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/p.js": js})
        assert "P1" in rules(run(mod))


def test_patch_with_super_is_clean():
    js = """
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
patch(PosStore.prototype, {
    async setup(...args) {
        await super.setup(...arguments);
        this.thing = 1;
    },
});
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/p.js": js})
        assert "P1" not in rules(run(mod))


def test_xpath_positional_predicate():
    xml = """<?xml version="1.0"?>
<templates>
    <t t-inherit="point_of_sale.Orderline" t-inherit-mode="extension">
        <xpath expr="//div[3]/button[2]" position="after"><span/></xpath>
    </t>
</templates>
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/t.xml": xml})
        assert "X2" in rules(run(mod))


def test_semantic_xpath_is_clean():
    xml = """<?xml version="1.0"?>
<templates>
    <t t-inherit="point_of_sale.Orderline" t-inherit-mode="extension">
        <xpath expr="//div[hasclass('info-list')]" position="inside"><span/></xpath>
    </t>
</templates>
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/t.xml": xml})
        assert "X2" not in rules(run(mod))


def test_bare_patch_in_a_test_body():
    js = """
import { patch } from "@web/core/utils/patch";
test("thing", () => {
    patch(Cls.prototype, { foo() { return super.foo(...arguments); } });
});
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/tests/unit/thing.test.js": js})
        assert "P5" in rules(run(mod), "error")


def test_mock_data_fixtures_may_patch_at_module_scope():
    """tests/**/data/*.data.js define HOOT mock models; module-scope patch is correct."""
    js = """
import { patch } from "@web/core/utils/patch";
import { PosOrderLine } from "@point_of_sale/../tests/unit/data/pos_order_line.data";
patch(PosOrderLine.prototype, { _records: [] });
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/tests/unit/data/thing.data.js": js})
        assert "P5" not in rules(run(mod), "error")


def test_n_plus_one_rpc_in_a_loop():
    js = """
export async function load(orm, ids) {
    for (const id of ids) {
        await orm.read("res.partner", [id], ["name"]);
    }
}
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/d.js": js})
        assert "D2" in rules(run(mod))


def test_vendored_lib_is_ignored():
    js = "String.prototype.trimAll = function () { return this; };\n"
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/lib/vendor/thing.js": js})
        assert rules(run(mod)) == set() or "P5" not in rules(run(mod))


def test_comments_do_not_trigger_rules():
    js = """
// PosGlobalState was the Odoo 16 name; do not use it.
/* registry.category("pos_screens").add("X", {}); */
export const ok = 1;
"""
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/c.js": js})
        found = rules(run(mod))
        assert "S-POSGLOBAL" not in found
        assert "S-POSSCREENS" not in found


# --------------------------------------------------------------------------
# CLI behaviour
# --------------------------------------------------------------------------

def test_exit_codes_and_filters():
    js = 'PosOrder.prototype.x = function () {};\n'
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST,
                           {"static/src/app/p.js": js})
        err = subprocess.run([sys.executable, str(LINT), str(mod)],
                             capture_output=True, text=True)
        assert err.returncode == 1, "an error-level finding must exit 1"

        skipped = subprocess.run([sys.executable, str(LINT), str(mod), "--skip", "P5"],
                                 capture_output=True, text=True)
        assert skipped.returncode == 0, "--skip must suppress the finding"

        only = run(mod, "--only", "P5")
        assert rules(only) == {"P5"}

        bad = subprocess.run([sys.executable, str(LINT), str(mod / "nope")],
                             capture_output=True, text=True)
        assert bad.returncode == 2, "a missing path must exit 2"


def test_clean_module_is_silent():
    with tempfile.TemporaryDirectory() as td:
        mod = write_module(Path(td), "good_mod", GOOD_MANIFEST, {
            "static/src/app/screens/ok.js": """
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

export class Ok extends Component {
    setup() {
        this.pos = useService("pos");
    }
}
registry.category("pos_pages").add("Ok", { component: Ok });
patch(Ok.prototype, {
    setup() {
        super.setup(...arguments);
    },
});
""",
        })
        res = run(mod)
        assert res["counts"]["error"] == 0, "clean module reported: %s" % res["findings"]


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
            print("  FAIL  %s\n        %s" % (name, str(exc)[:400]))
        except Exception as exc:
            failed.append(name)
            print("  ERROR %s\n        %s: %s" % (name, type(exc).__name__, str(exc)[:400]))
    print("\n%d passed, %d failed, %d total" % (passed, len(failed), len(fns)))
    return 1 if failed else 0


if __name__ == "__main__":
    print("owl_lint test suite\n" + "-" * 60)
    raise SystemExit(_run_all())
