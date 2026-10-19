#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit|MultiEdit): refuse inline JavaScript in an Odoo module's XML.

Odoo loads JavaScript through asset bundles (`static/src/js/` + the manifest
`assets`). An inline `<script>` with code in a QWeb/XML view bypasses the bundler,
breaks with CSP and is not translated or minified. This hook refuses that write and
says where the code belongs.

Scope and exceptions:
- Only XML files inside an Odoo module (a `__manifest__.py` / `__openerp__.py` in the
  file's directory or one of its ancestors). XML anywhere else passes.
- Non-executable script blocks pass: `type="application/ld+json"`, `application/json`,
  `text/template`, `text/x-template`, `text/html`, `text/plain`, and an empty
  `<script src="...">` tag.
- ODOO_INLINE_SCRIPT_CHECK=off (set before starting Claude Code) disables the check;
  ODOO_INLINE_SCRIPT_CHECK=warn turns the refusal into a note for Claude.

Fails open: bad input, an exception or the 3 s watchdog all end in exit 0.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_vendor"))

import hooklib  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)
_TYPE_RE = re.compile(r"""\btype\s*=\s*["']?\s*([^"'\s>]+)""", re.IGNORECASE)
_DATA_TYPES = {
    "application/ld+json", "application/json", "text/template", "text/x-template",
    "text/html", "text/plain", "text/x-handlebars-template", "importmap",
}
_MANIFESTS = ("__manifest__.py", "__openerp__.py")


def in_odoo_module(file_path: str, max_up: int = 8) -> bool:
    here = os.path.dirname(os.path.abspath(file_path))
    for _ in range(max_up):
        if any(os.path.isfile(os.path.join(here, m)) for m in _MANIFESTS):
            return True
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return False


def inline_scripts(content: str) -> list:
    """Executable inline <script> blocks with a non-empty body."""
    found = []
    for attrs, body in _SCRIPT_RE.findall(content):
        if not body.strip():
            continue
        m = _TYPE_RE.search(attrs)
        if m and m.group(1).lower() in _DATA_TYPES:
            continue
        found.append(body.strip()[:60])
    return found


def main() -> int:
    hooklib.watchdog(3.0)
    mode = os.environ.get("ODOO_INLINE_SCRIPT_CHECK", "").strip().lower()
    if mode in ("off", "0", "false"):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    ti = hooklib.tool_input(payload)
    file_path = ti.get("file_path", "")
    content = ti.get("content", "") or ti.get("new_string", "")
    edits = ti.get("edits")
    if not content and isinstance(edits, list):  # MultiEdit
        content = "\n".join(e.get("new_string", "") for e in edits
                            if isinstance(e, dict) and isinstance(e.get("new_string"), str))
    if not isinstance(file_path, str) or not isinstance(content, str):
        return 0
    if not file_path.lower().endswith(".xml") or "<script" not in content.lower():
        return 0
    if not inline_scripts(content) or not in_odoo_module(file_path):
        return 0
    reason = ("Inline JavaScript detected in an Odoo XML template (%s). Put the code in a "
              "separate .js file under static/src/js/ and load it through the manifest "
              "`assets`. JSON-LD and template blocks (type=\"application/ld+json\", "
              "\"text/template\") are allowed." % os.path.basename(file_path))
    if mode == "warn":
        hooklib.context("PreToolUse", "[odoo] " + reason)
    else:
        hooklib.deny(reason)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
