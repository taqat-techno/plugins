"""Advice for a write to an Odoo migration script (used by guard_core_odoo.py).

Odoo runs a script under `<module>/migrations/<version>/` (or `upgrades/`) only when

    installed version  <  <version>  <=  version in __manifest__.py

and only when the file name starts with `pre-`, `post-` or `end-`
(odoo/modules/migration.py, the same in 17.0, 18.0 and 19.0). A script outside that
window, or with another name, is skipped without an error. `advise(path, tool)` returns
the notes that apply to this write, or an empty list.

Never blocks. Silent outside an Odoo module. ODOO_MIGRATION_GUARD=off disables it.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess

_MIG_RE = re.compile(r"^(?P<module>.+)/(?P<kind>migrations|upgrades)/(?P<version>[^/]+)/(?P<file>[^/]+\.py)$")
_STAGES = ("pre-", "post-", "end-")


def _ints(version: str):
    parts = version.split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def _manifest_version(module_dir: str):
    for name in ("__manifest__.py", "__openerp__.py"):
        path = os.path.join(module_dir, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    data = ast.literal_eval(fh.read())
                version = data.get("version") if isinstance(data, dict) else None
                return str(version) if version else ""
            except Exception:
                return ""
    return None


def _committed(path: str) -> bool:
    """True when the file is tracked by git, so it may already have shipped."""
    try:
        res = subprocess.run(["git", "-C", os.path.dirname(path), "ls-files", "--error-unmatch",
                              os.path.basename(path)], capture_output=True, timeout=2)
        return res.returncode == 0
    except Exception:
        return False


def advise(file_path: str, tool_name: str = "", env=os.environ) -> list:
    if (env.get("ODOO_MIGRATION_GUARD") or "").strip().lower() in ("off", "0", "false", "no"):
        return []
    m = _MIG_RE.match(file_path.replace("\\", "/"))
    if not m or m.group("file") == "__init__.py":
        return []
    module_dir = m.group("module")
    manifest = _manifest_version(module_dir)
    if manifest is None:
        return []   # not an Odoo module
    notes = []
    fname, version = m.group("file"), m.group("version")

    if not fname.startswith(_STAGES):
        notes.append("%s will never run: Odoo loads only files named pre-*.py, post-*.py or end-*.py "
                     "from a migration folder, and skips any other name without an error." % fname)

    folder, declared = _ints(version), _ints(manifest)
    if folder and declared and len(folder) == len(declared) and folder > declared:
        notes.append("Folder %s is above the manifest version %s, so this script will not run until the "
                     "manifest reaches %s. Bump the manifest in the same change." % (version, manifest, version))

    if os.path.isfile(file_path) and _committed(file_path):
        notes.append("%s/%s is already committed. A migration runs once, on databases whose installed "
                     "version is below %s. Any database already at or above %s will never run this edit. "
                     "Check the installed version on every environment (SELECT latest_version FROM "
                     "ir_module_module WHERE name = '%s'); if any has passed %s, put the fix in a new "
                     "folder above the highest installed version instead of editing this one."
                     % (version, fname, version, version, os.path.basename(module_dir), version))
    elif not os.path.isfile(file_path) and folder and declared and len(folder) == len(declared):
        notes.append("New migration in folder %s (manifest %s). It runs only on databases whose installed "
                     "version is below %s; a fresh install runs no migration at all. Confirm the installed "
                     "version on each environment before relying on this folder." % (version, manifest, version))
    if notes:
        notes.insert(0, "[odoo migration]")
    return notes
