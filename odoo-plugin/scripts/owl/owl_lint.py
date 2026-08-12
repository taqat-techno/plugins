#!/usr/bin/env python3
"""owl_lint — static scanner for Odoo OWL front-end anti-patterns (Odoo 17-19).

Why this exists: almost every OWL failure mode is SILENT. A file outside every
asset glob produces no error. A mistyped registry category returns a fresh empty
registry. A patch on a renamed method installs as a brand-new property. There is
no compiler, and schema validation is debug-gated. Review is the only gate, so
this makes part of that review automatic.

Rule ids match the anti-pattern catalogue in
`reference/owl/anti-pattern-catalogue.md`.

Usage:
    python owl_lint.py <module-path> [more paths...]
      [--format text|json] [--severity error|warning|info]
      [--only A1,P5] [--skip X2] [--no-assets]

Exit codes: 0 clean (or warnings only), 1 at least one error, 2 bad invocation.

Standard library only.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ASSET_EXTS = {".js", ".xml", ".scss", ".css"}
JS_EXTS = {".js"}
COMPONENT_DIRS = ("components", "screens", "popups", "dialogs", "widgets")

# Categories whose consumer snapshots them ONCE at construction. Registering into
# one of these after boot is silently ignored. Live categories (services,
# main_components, systray, error_handlers, web_tour.tours) are deliberately absent.
ONE_SHOT_CATEGORIES = ("pos_pages", "pos_available_models")

# Extending a browser/language built-in is not the Odoo patch anti-pattern; test
# helpers legitimately stub XMLHttpRequest.prototype.send and similar.
JS_BUILTINS = frozenset({
    "String", "Number", "Boolean", "Array", "Object", "Function", "Date", "RegExp",
    "Map", "Set", "WeakMap", "WeakSet", "Promise", "Error", "Math", "JSON",
    "XMLHttpRequest", "Element", "HTMLElement", "Node", "Event", "EventTarget",
    "Window", "Document", "Image", "FormData", "Blob", "File", "Storage",
})

# Vendored third-party code. Never our anti-pattern to fix, and it drowns the report.
VENDOR_DIR_MARKERS = ("/static/lib/", "/static/src/lib/", "/node_modules/")

SEVERITIES = ("error", "warning", "info")


@dataclass
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    message: str
    fix: str = ""

    def as_dict(self) -> dict:
        return {
            "rule": self.rule, "severity": self.severity, "file": self.path,
            "line": self.line, "message": self.message, "fix": self.fix,
        }


@dataclass
class Module:
    root: Path
    name: str
    manifest: dict = field(default_factory=dict)
    manifest_path: Path | None = None


# --------------------------------------------------------------------------
# Glob handling (Odoo asset globs, not fnmatch semantics)
# --------------------------------------------------------------------------

def glob_to_regex(pattern: str) -> re.Pattern:
    """Translate an Odoo asset glob to a regex.

    `**` crosses directory separators, `*` and `?` do not.
    """
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def read_manifest(module_root: Path) -> tuple[dict, Path | None]:
    for name in ("__manifest__.py", "__openerp__.py"):
        p = module_root / name
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                node = ast.parse(text, mode="exec")
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Dict):
                        return ast.literal_eval(stmt.value), p
            except (SyntaxError, ValueError):
                return {}, p
            return {}, p
    return {}, None


def iter_files(root: Path, exts: set[str] | None = None) -> Iterable[Path]:
    skip = {".git", "node_modules", "__pycache__", ".idea", ".vscode"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            p = Path(dirpath) / fn
            if exts is None or p.suffix.lower() in exts:
                yield p


def rel_asset_path(mod: Module, f: Path) -> str:
    """Asset paths in a manifest are '<module>/static/...' from the addons root."""
    return (mod.name + "/" + f.relative_to(mod.root).as_posix()).replace("\\", "/")


# --------------------------------------------------------------------------
# Source scanning helpers
# --------------------------------------------------------------------------

def lines_of(p: Path) -> list[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def strip_js_comments(text: str) -> str:
    """Blank out // and /* */ comments and string literals, preserving offsets so
    line numbers stay correct. Prevents matching patterns inside comments."""
    out = list(text)
    i, n = 0, len(text)
    state = None  # None | 'line' | 'block' | 'sq' | 'dq' | 'tpl'
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"; out[i] = out[i + 1] = " "; i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; out[i] = out[i + 1] = " "; i += 2; continue
            if c == "'":
                state = "sq"; i += 1; continue
            if c == '"':
                state = "dq"; i += 1; continue
            if c == "`":
                state = "tpl"; i += 1; continue
            i += 1; continue
        if state == "line":
            if c == "\n":
                state = None
            else:
                out[i] = " "
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                out[i] = out[i + 1] = " "; state = None; i += 2; continue
            if c != "\n":
                out[i] = " "
            i += 1; continue
        # inside a string: keep it (we match on some string content), just track the end
        if state == "sq" and c == "'" and text[i - 1] != "\\":
            state = None
        elif state == "dq" and c == '"' and text[i - 1] != "\\":
            state = None
        elif state == "tpl" and c == "`" and text[i - 1] != "\\":
            state = None
        i += 1
    return "".join(out)


def line_of_offset(text: str, off: int) -> int:
    return text.count("\n", 0, off) + 1


# --------------------------------------------------------------------------
# Stale-pattern table (Odoo <=18 idioms that provably do not work in 19)
# --------------------------------------------------------------------------

STALE = [
    ("S-POSGLOBAL", r"\bPosGlobalState\b|\bmodels\.PosModel\b",
     "PosGlobalState / models.PosModel do not exist in Odoo 19.",
     "The store is PosStore. Use patch(PosStore.prototype, {...})."),
    ("S-POSSCREENS", r"""registry\.category\(\s*["']pos_screens["']""",
     "The 'pos_screens' registry category does not exist in Odoo 19.",
     "Use 'pos_pages' and navigate with pos.navigate(name, params)."),
    ("S-SHOWSCREEN", r"\.showScreen\(",
     "showScreen() was replaced in Odoo 19.",
     "Use pos.navigate(name, params)."),
    ("S-ADDCTRLBTN", r"\baddControlButton\b",
     "ProductScreen.addControlButton() does not exist in Odoo 19.",
     "patch(ControlButtons.prototype, {...}) plus a t-inherit xpath."),
    ("S-LOADERPARAMS", r"\bdef\s+_loader_params_\w+|\bsearch_params\b",
     "_loader_params_<model>() is dead in Odoo 19.",
     "Use _load_pos_data_models / _load_pos_data_domain / _load_pos_data_fields."),
    ("S-PATCHNAME", r"""patch\(\s*[^,()]+\s*,\s*["'][^"']+["']\s*,""",
     "The three-argument patch(obj, 'name', ext) form THROWS in Odoo 19.",
     "Use the two-argument patch(obj, ext); in tests use patchWithCleanup."),
    ("S-UNPATCH", r"\bimport\s+\{[^}]*\bunpatch\b[^}]*\}",
     "No unpatch export exists in Odoo 19.",
     "Use patchWithCleanup in tests, which registers its own cleanup."),
    ("S-DEVASSETS", r"--dev=assets",
     "--dev=assets is not accepted by Odoo 19 (only access, qweb, reload, xml).",
     "Use ?debug=assets in the URL."),
    ("S-ORMNAMEGET", r"\borm\.nameGet\(|\borm\.nameSearch\(|\borm\.readGroup\(",
     "orm.nameGet / nameSearch / readGroup are absent from orm_service.js in 19.",
     "Use orm.call(model, 'web_name_search', ...) or formattedReadGroup."),
    ("S-TYPEJSON", r"""type\s*=\s*["']json["']""",
     "route type='json' is deprecated in Odoo 19.",
     "Use type='jsonrpc'."),
    ("S-CHECKACCESS", r"\.check_access_rights\(|\.check_access_rule\(",
     "check_access_rights() / check_access_rule() are deprecated since 18.0.",
     "Use check_access / has_access / _filtered_access."),
    ("S-OWLATTR", r"""owl\s*=\s*["']1["']""",
     "owl=\"1\" on a template is read by nothing in Odoo 19.",
     "Remove the attribute."),
    ("S-QUNIT", r"\bQUnit\.(module|test)\b",
     "QUnit is not the Odoo 19 JS test runner.",
     "Use HOOT: <addon>/static/tests/**/*.test.js."),
    ("S-NAMEGET", r"\bdef\s+name_get\s*\(",
     "name_get() was REMOVED from BaseModel in 18.0 (not 17.0, as widely believed).",
     "Compute display_name instead."),
    ("S-FIELDSVIEWGET", r"\bfields_view_get\s*\(",
     "fields_view_get() was removed in 17.0.",
     "Use get_views / get_view."),
]


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

def rule_assets(mod: Module) -> list[Finding]:
    """A1/A2/A3 — bundle membership and asset-directive ordering."""
    out: list[Finding] = []
    if not mod.manifest_path:
        return out
    assets = mod.manifest.get("assets")
    static = mod.root / "static"

    if not isinstance(assets, dict):
        if static.is_dir() and any(iter_files(static, ASSET_EXTS)):
            out.append(Finding(
                "A1", "error", str(mod.manifest_path), 1,
                "Module has static asset files but the manifest declares no 'assets' key. "
                "Files outside every bundle glob never execute and raise no error.",
                "Add an 'assets' entry, e.g. "
                "'web.assets_backend': ['%s/static/src/**/*']" % mod.name))
        return out

    patterns: list[tuple[str, re.Pattern]] = []
    manifest_lines = lines_of(mod.manifest_path)

    def manifest_line_of(needle: str) -> int:
        for i, ln in enumerate(manifest_lines, 1):
            if needle in ln:
                return i
        return 1

    for bundle, entries in assets.items():
        if not isinstance(entries, (list, tuple)):
            continue
        seen_globs: list[tuple[str, re.Pattern]] = []
        for entry in entries:
            if isinstance(entry, str):
                pat = entry
                rx = glob_to_regex(pat)
                patterns.append((pat, rx))
                seen_globs.append((pat, rx))
            elif isinstance(entry, (list, tuple)) and entry:
                op = str(entry[0])
                target = str(entry[-1]) if len(entry) > 1 else ""
                if op in ("after", "before", "replace"):
                    for gpat, grx in seen_globs:
                        if grx.match(target):
                            out.append(Finding(
                                "A2", "warning", str(mod.manifest_path),
                                manifest_line_of(target),
                                "Ordering directive ('%s', ..., '%s') appears AFTER glob '%s' "
                                "which already matches it. AssetPaths.insert skips paths "
                                "already in its memo, so this directive is a no-op."
                                % (op, target, gpat),
                                "Move ordering directives BEFORE the glob. Order only "
                                "matters for SCSS; JS order is decided by the module loader."))
                            break
                    rx = glob_to_regex(target)
                    patterns.append((target, rx))
                elif op == "remove":
                    first_seg = target.split("/", 1)[0]
                    if first_seg and first_seg != mod.name:
                        out.append(Finding(
                            "A3", "warning", str(mod.manifest_path),
                            manifest_line_of(target),
                            "('remove', '%s') strips a file owned by '%s' out of bundle '%s'. "
                            "Removal is GLOBAL for that bundle: every module importing that "
                            "export stops working, reported only as a loader 'not defined' line."
                            % (target, first_seg, bundle),
                            "patch() the exported object instead. If you must remove, re-add "
                            "what consumers still need."))
                elif op in ("append", "prepend", "include"):
                    if len(entry) > 1:
                        patterns.append((target, glob_to_regex(target)))

    # A1 — every asset-extension file under static/ should match some pattern
    if static.is_dir():
        for f in sorted(iter_files(static, ASSET_EXTS)):
            rp = rel_asset_path(mod, f)
            if any(marker in ("/" + rp) for marker in VENDOR_DIR_MARKERS):
                continue  # vendored third-party assets are cherry-picked, not globbed
            if any(rx.match(rp) for _, rx in patterns):
                continue
            # tests are frequently loaded by a separate test bundle
            sev = "info" if "/static/tests/" in rp else "error"
            out.append(Finding(
                "A1", sev, str(f), 1,
                "No manifest glob in this module matches '%s', so the file is in no bundle "
                "and never executes. This fails silently - no console error." % rp,
                "Add a glob covering it, or move the file under an existing glob. Verify at "
                "runtime with odoo.loader.factories.has(\"@%s/...\")." % mod.name))
    return out


def rule_js(mod: Module) -> list[Finding]:
    """R2/S1/S3/P2/P5/D2 plus the stale-pattern table, over JS sources."""
    out: list[Finding] = []
    for f in sorted(iter_files(mod.root, JS_EXTS)):
        raw = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""
        if not raw:
            continue
        code = strip_js_comments(raw)
        posix = f.as_posix()
        if any(marker in posix for marker in VENDOR_DIR_MARKERS):
            continue  # vendored third-party code
        is_test = "/static/tests/" in posix or f.name.endswith(".test.js")
        # Only true HOOT test bodies. Fixtures under tests/**/data/** and tour
        # definitions legitimately patch mock model classes at module scope.
        is_test_body = f.name.endswith(".test.js")
        in_component_dir = any(("/%s/" % d) in f.as_posix() for d in COMPONENT_DIRS)

        for rid, pat, msg, fix in STALE:
            for m in re.finditer(pat, code):
                out.append(Finding(rid, "error" if rid in
                                   ("S-PATCHNAME", "S-UNPATCH") else "warning",
                                   str(f), line_of_offset(code, m.start()), msg, fix))

        # R2 — a ONE-SHOT category must be written at module top level.
        # Live categories (services, main_components, systray, web_tour.tours,
        # error_handlers) re-read after boot, so late registration is fine there;
        # flagging them would be noise. Note [ \t] not \s: \s matches newlines and
        # would match column-0 code preceded by a blank line.
        if not is_test:
            for m in re.finditer(
                    r"""^[ \t]+registry\s*\.\s*category\(\s*["'](%s)["']\s*\)\s*\.\s*add\("""
                    % "|".join(ONE_SHOT_CATEGORIES), code, re.M):
                out.append(Finding(
                    "R2", "error", str(f), line_of_offset(code, m.start()),
                    "registry.category(\"%s\").add(...) is indented, so it is not at module "
                    "top level. That category is snapshotted once by its consumer at "
                    "construction; anything registered later is silently ignored."
                    % m.group(1),
                    "Move the registration to file scope."))

        # S1 — force-replacing a service
        for m in re.finditer(r"""category\(\s*["']services["']\s*\)\s*\.\s*add\(""", code):
            seg = code[m.start():m.start() + 400]
            if "force" in seg and "true" in seg.lower():
                out.append(Finding(
                    "S1", "error", str(f), line_of_offset(code, m.start()),
                    "Re-registering a service with {force: true} is last-writer-wins by "
                    "topological order. The next addon forcing the same key discards you "
                    "silently, and a force after boot does nothing at all.",
                    "patch() the service definition object instead."))

        # S3 — env.services inside a component (not in tests: a test legitimately
        # reaches into env.services of a mounted component to assert on it)
        if in_component_dir and not is_test:
            for m in re.finditer(r"\benv\s*\.\s*services\s*\.\s*(\w+)", code):
                out.append(Finding(
                    "S3", "error", str(f), line_of_offset(code, m.start()),
                    "env.services.%s inside a component skips the useState(service) branch, "
                    "so the component STOPS RE-RENDERING when that service changes. This is "
                    "the most common OWL bug in Odoo code." % m.group(1),
                    'Use useService("%s") in setup().' % m.group(1)))

        # P5 — raw prototype assignment. [ \t] not \s, or the match starts on the
        # previous newline and reports the wrong line. Built-in globals are excluded:
        # patching XMLHttpRequest or String in a test helper is not the Odoo anti-pattern.
        for m in re.finditer(
                r"^[ \t]*(\w[\w.]*)\.prototype\.(\w+)\s*=(?!=)\s*(.{0,12})", code, re.M):
            owner, member, tail = m.group(1), m.group(2), m.group(3)
            if owner.split(".")[0] in JS_BUILTINS:
                continue
            is_fn = bool(re.match(r"(async\b|function\b|\(|\w+\s*=>)", tail.strip()))
            out.append(Finding(
                "P5", "error" if is_fn else "warning", str(f),
                line_of_offset(code, m.start()),
                "Raw prototype assignment (%s.prototype.%s = ...) creates no patch skeleton: "
                "'super' is unavailable inside it, and a later patch() of the same key records "
                "YOUR value as the original, so unpatch restores the wrong thing. In HOOT it "
                "also leaks between tests." % (owner, member),
                "Use patch(%s.prototype, { ... }) with an inline object literal." % owner))

        # P5b — patch() whose 2nd argument is a shared variable, not a literal
        for m in re.finditer(r"patch\(\s*[^,()]+?\s*,\s*([A-Za-z_$][\w$]*)\s*\)", code):
            name = m.group(1)
            if name in ("true", "false", "null", "undefined"):
                continue
            out.append(Finding(
                "P5", "warning", str(f), line_of_offset(code, m.start()),
                "patch() called with a variable ('%s') as the extension. patch() MUTATES the "
                "extension object to build the super chain, so reusing one literal across two "
                "targets silently rewires the first target's chain." % name,
                "Write the extension object inline at each call site."))

        # P2 — patch(X, {...}) defining methods (statics vs prototype confusion)
        for m in re.finditer(r"patch\(\s*([A-Za-z_$][\w$.]*)\s*,\s*\{", code):
            target = m.group(1)
            if target.endswith(".prototype"):
                continue
            body = code[m.end(): m.end() + 500]
            if re.search(r"^\s*(async\s+)?\w+\s*\([^)]*\)\s*\{", body, re.M):
                out.append(Finding(
                    "P2", "warning", str(f), line_of_offset(code, m.start()),
                    "patch(%s, {...}) with a method body patches the CLASS, adding a static "
                    "that instances never call. Neither form throws." % target,
                    "Use %s.prototype for instance behaviour; keep the class form for "
                    "statics such as `components` or `extraFields`." % target))

        # P1 — patched method with no super call anywhere in the extension
        for m in re.finditer(r"patch\(\s*[A-Za-z_$][\w$.]*\s*,\s*\{", code):
            depth, i, n = 1, m.end(), len(code)
            while i < n and depth:
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                    depth -= 1
                i += 1
            body = code[m.end():i]
            if re.search(r"^\s*(async\s+)?\w+\s*\([^)]*\)\s*\{", body, re.M) \
                    and "super." not in body:
                out.append(Finding(
                    "P1", "warning", str(f), line_of_offset(code, m.start()),
                    "This patch defines a method but never calls super. Omitting super drops "
                    "the base implementation AND every earlier patch in the chain - the "
                    "symptom usually lands on a different addon.",
                    "Call super.method(...arguments). If replacing deliberately, say so in a "
                    "comment on the line above."))

        # Tests must use patchWithCleanup
        if is_test_body:
            for m in re.finditer(r"(?<![\w.])patch\(", code):
                seg = code[max(0, m.start() - 20):m.start()]
                if "patchWithCleanup" in seg or "WithCleanup" in seg:
                    continue
                out.append(Finding(
                    "P5", "error", str(f), line_of_offset(code, m.start()),
                    "Bare patch() in a test. Nothing unpatches between HOOT tests, so this "
                    "leaks into every later test in the run and passes in isolation.",
                    "Use patchWithCleanup(...) from web_test_helpers."))
            for m in re.finditer(r"\b(test|describe)\.only\(", code):
                out.append(Finding(
                    "Q1", "error", str(f), line_of_offset(code, m.start()),
                    "A stray .only() fails CI (web/tests/test_js.py asserts none exist).",
                    "Remove .only before committing."))

        # D2 — awaited RPC inside a loop
        for m in re.finditer(r"\bfor\s*\(([^)]*)\)\s*\{", code):
            depth, i, n = 1, m.end(), len(code)
            while i < n and depth:
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                    depth -= 1
                i += 1
            body = code[m.end():i]
            if re.search(r"await\s+[\w.$]*\b(orm|rpc)\b\s*\.", body):
                out.append(Finding(
                    "D2", "warning", str(f), line_of_offset(code, m.start()),
                    "Awaited RPC inside a loop: one network round trip per iteration.",
                    "Batch it - one call with a domain or a list of ids, or Promise.all."))
    return out


def rule_xml(mod: Module) -> list[Finding]:
    """X2/X3 — xpath fragility and template naming."""
    out: list[Finding] = []
    for f in sorted(iter_files(mod.root, {".xml"})):
        src = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""
        if not src:
            continue
        for m in re.finditer(r"""<xpath\b[^>]*\bexpr\s*=\s*["']([^"']+)["']""", src):
            expr = m.group(1)
            ln = line_of_offset(src, m.start())
            if re.search(r"\[\s*\d+\s*\]", expr):
                out.append(Finding(
                    "X2", "warning", str(f), ln,
                    "xpath '%s' uses a positional predicate. Template xpaths resolve "
                    "CLIENT-SIDE at first render, so this ships green and breaks in the "
                    "browser when any sibling element is added." % expr,
                    "Anchor on a semantic class, e.g. hasclass('o_my_marker')."))
            if re.search(r"(contains|text\(\))\s*\(?\s*['\"]", expr) and "hasclass" not in expr:
                out.append(Finding(
                    "X2", "warning", str(f), ln,
                    "xpath '%s' matches on element text or an expression string; rewording "
                    "the source breaks it with no build-time warning." % expr,
                    "Anchor on a semantic class instead."))
        for m in re.finditer(r"""<t\b[^>]*\bt-inherit\s*=\s*["']([^"']+)["'][^>]*>""", src):
            tag = m.group(0)
            if "t-inherit-mode" not in tag:
                out.append(Finding(
                    "X3", "warning", str(f), line_of_offset(src, m.start()),
                    "t-inherit without an explicit t-inherit-mode.",
                    'Add t-inherit-mode="extension" (change what everyone sees) or '
                    '"primary" (a coexisting variant, which freezes the parent).'))
    return out


def rule_python(mod: Module) -> list[Finding]:
    """SEC2/SEC3 — payload exposure and sudo on the load path."""
    out: list[Finding] = []
    for f in sorted(iter_files(mod.root, {".py"})):
        if "/static/" in f.as_posix():
            continue
        src = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""
        if not src:
            continue
        for rid, pat, msg, fix in STALE:
            if rid in ("S-LOADERPARAMS", "S-CHECKACCESS", "S-TYPEJSON", "S-NAMEGET",
                       "S-FIELDSVIEWGET"):
                for m in re.finditer(pat, src):
                    out.append(Finding(rid, "warning", str(f),
                                       line_of_offset(src, m.start()), msg, fix))
        for m in re.finditer(r"def\s+(_load_pos_data_fields|_load_pos_data_domain)\s*\(", src):
            depth_src = src[m.start():m.start() + 1200]
            if ".sudo()" in depth_src:
                out.append(Finding(
                    "SEC3", "warning", str(f), line_of_offset(src, m.start()),
                    "sudo() on the data-loading path. Every field in the payload reaches "
                    "every client with the app open, and anyone reading their IndexedDB.",
                    "Remove sudo and classify the exposure instead."))
        for m in re.finditer(r"def\s+(_load_pos_data_fields)\s*\(", src):
            out.append(Finding(
                "SEC2", "info", str(f), line_of_offset(src, m.start()),
                "This method widens the client payload. A field carrying groups= blanks the "
                "WHOLE model for users outside that group, because load_data catches "
                "AccessError per model and substitutes [] behind an INFO log line.",
                "Confirm no added field carries groups=, and that company containment is "
                "explicit."))
    return out


RULES = (rule_assets, rule_js, rule_xml, rule_python)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def scan(module_root: Path, skip_assets: bool = False) -> list[Finding]:
    manifest, mpath = read_manifest(module_root)
    mod = Module(root=module_root, name=module_root.name, manifest=manifest,
                 manifest_path=mpath)
    findings: list[Finding] = []
    for fn in RULES:
        if skip_assets and fn is rule_assets:
            continue
        try:
            findings.extend(fn(mod))
        except Exception as exc:  # a bad file must never abort the whole scan
            findings.append(Finding("LINT", "info", str(module_root), 1,
                                    "rule %s failed: %s: %s"
                                    % (fn.__name__, type(exc).__name__, exc)))
    return findings


def render_text(findings: list[Finding], root: Path) -> str:
    if not findings:
        return "OWL lint: no findings.\n"
    order = {"error": 0, "warning": 1, "info": 2}
    findings = sorted(findings, key=lambda f: (order.get(f.severity, 3), f.rule, f.path, f.line))
    lines, counts = [], {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        try:
            shown = Path(f.path).relative_to(root).as_posix()
        except ValueError:
            shown = f.path
        lines.append("[%s] %s  %s:%d" % (f.severity.upper(), f.rule, shown, f.line))
        lines.append("    %s" % f.message)
        if f.fix:
            lines.append("    fix: %s" % f.fix)
        lines.append("")
    lines.append("%d error(s), %d warning(s), %d info"
                 % (counts.get("error", 0), counts.get("warning", 0), counts.get("info", 0)))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="owl_lint",
        description="Static scanner for Odoo OWL front-end anti-patterns (Odoo 17-19).")
    ap.add_argument("paths", nargs="+", help="module director(ies) to scan")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--severity", choices=SEVERITIES, default="info",
                    help="minimum severity to report (default: info)")
    ap.add_argument("--only", default="", help="comma-separated rule ids to keep")
    ap.add_argument("--skip", default="", help="comma-separated rule ids to drop")
    ap.add_argument("--no-assets", action="store_true",
                    help="skip bundle-membership analysis (A1/A2/A3)")
    args = ap.parse_args(argv)

    only = {r.strip().upper() for r in args.only.split(",") if r.strip()}
    skip = {r.strip().upper() for r in args.skip.split(",") if r.strip()}
    threshold = SEVERITIES.index(args.severity)

    all_findings: list[Finding] = []
    roots: list[Path] = []
    for raw in args.paths:
        root = Path(raw).expanduser()
        if not root.is_dir():
            print("error: not a directory: %s" % root, file=sys.stderr)
            return 2
        roots.append(root)
        all_findings.extend(scan(root, skip_assets=args.no_assets))

    kept = []
    for f in all_findings:
        if only and f.rule.upper() not in only:
            continue
        if f.rule.upper() in skip:
            continue
        if SEVERITIES.index(f.severity) > threshold:
            continue
        kept.append(f)

    if args.format == "json":
        print(json.dumps({"findings": [f.as_dict() for f in kept],
                          "counts": {s: sum(1 for f in kept if f.severity == s)
                                     for s in SEVERITIES}}, indent=2))
    else:
        sys.stdout.write(render_text(kept, roots[0]))

    return 1 if any(f.severity == "error" for f in kept) else 0


if __name__ == "__main__":
    raise SystemExit(main())
