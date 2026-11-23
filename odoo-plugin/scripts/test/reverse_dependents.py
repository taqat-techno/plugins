#!/usr/bin/env python3
"""List the modules a change to MODULE can break: its reverse dependents.

A change to security, a core hook, a constraint or a shared model is proven by the test
suites of the modules that reach it, not only by its own. This script names them.

    reverse_dependents.py MODULE --addons PATH [--addons PATH ...] [--model res.partner]
                          [--direct] [--json]

It reads manifests only (no database, no Odoo import):
  * every module whose `depends` reaches MODULE, directly or through other modules;
  * with --model, also every module in the given paths whose Python files declare
    `_inherit` on that model, whatever it depends on;
  * for each one, whether it has a tests/ folder.

The last line is a --test-tags selector for the modules that have tests. Modules outside
the given addons paths (Enterprise, another repository) are not seen: pass their paths too.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

MANIFESTS = ("__manifest__.py", "__openerp__.py")


def find_modules(paths):
    """{name: {"path", "depends", "has_tests", "auto_install"}} for every module under `paths`."""
    found = {}
    for root in paths:
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            continue
        candidates = [root] + [os.path.join(root, d) for d in sorted(os.listdir(root))]
        for d in candidates:
            if not os.path.isdir(d):
                continue
            for mf in MANIFESTS:
                path = os.path.join(d, mf)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        data = ast.literal_eval(fh.read())
                except Exception:
                    data = None
                if not isinstance(data, dict):
                    break
                name = os.path.basename(d)
                found.setdefault(name, {
                    "path": d,
                    "depends": [str(x) for x in (data.get("depends") or [])],
                    "has_tests": os.path.isdir(os.path.join(d, "tests")),
                    "auto_install": bool(data.get("auto_install")),
                    "installable": data.get("installable", True) is not False,
                })
                break
    return found


def reverse_dependents(module, modules, direct=False):
    """Names of the modules that depend on `module`, nearest first."""
    children = {}
    for name, info in modules.items():
        for dep in info["depends"]:
            children.setdefault(dep, set()).add(name)
    order, seen, frontier = [], {module}, [module]
    while frontier:
        nxt = []
        for cur in frontier:
            for child in sorted(children.get(cur, ())):
                if child not in seen:
                    seen.add(child)
                    order.append(child)
                    nxt.append(child)
        if direct:
            break
        frontier = nxt
    return order


def inheritors(model, modules):
    """Names of the modules with a Python file that sets _inherit to `model`."""
    pat = re.compile(r"_inherit\s*=\s*(?:\[[^\]]*)?['\"]%s['\"]" % re.escape(model))
    hits = []
    for name, info in sorted(modules.items()):
        for base, dirs, files in os.walk(info["path"]):
            dirs[:] = [d for d in dirs if d not in ("static", "node_modules", ".git", "i18n", "tests")]
            if any(f.endswith(".py") and _matches(os.path.join(base, f), pat) for f in files):
                hits.append(name)
                break
    return hits


def _matches(path, pat):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return bool(pat.search(fh.read()))
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("module")
    ap.add_argument("--addons", action="append", required=True, help="an addons path; repeat for each one")
    ap.add_argument("--model", help="also list modules that _inherit this model")
    ap.add_argument("--direct", action="store_true", help="direct dependents only")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    modules = find_modules(a.addons)
    if a.module not in modules:
        print("module %r not found under: %s" % (a.module, ", ".join(a.addons)), file=sys.stderr)
        return 2
    names = reverse_dependents(a.module, modules, a.direct)
    by_model = [n for n in (inheritors(a.model, modules) if a.model else []) if n != a.module]
    rows = []
    for n in names + [m for m in by_model if m not in names]:
        info = modules[n]
        rows.append({"module": n, "via": "depends" if n in names else "inherits %s" % a.model,
                     "has_tests": info["has_tests"], "auto_install": info["auto_install"],
                     "installable": info["installable"], "path": info["path"]})
    with_tests = [r["module"] for r in rows if r["has_tests"] and r["installable"]]
    selector = ",".join("/%s" % m for m in [a.module] + with_tests)
    if a.json:
        print(json.dumps({"module": a.module, "dependents": rows, "test_tags": selector}, indent=1))
        return 0
    if not rows:
        print("No module under the given paths depends on %s." % a.module)
    for r in rows:
        print("%-40s %-28s tests=%s%s%s" % (r["module"], r["via"], "yes" if r["has_tests"] else "NO",
                                           " auto_install" if r["auto_install"] else "",
                                           "" if r["installable"] else " (not installable)"))
    print("\n%d dependent module(s), %d with tests." % (len(rows), len(with_tests)))
    print("--test-tags %s" % selector)
    print("Modules outside these addons paths are not listed; add their paths to see them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
