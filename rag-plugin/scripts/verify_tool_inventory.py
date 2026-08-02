#!/usr/bin/env python3
"""Drift gate for the MCP tool inventory in ``rules/mcp-envelope.md`` (WP-5, D-035).

Why this exists
---------------
Every consumer of the ragtools MCP surface has re-derived the tool list by hand,
and each drifted differently. At the 2026-08-01 audit:

  * ``rules/mcp-envelope.md`` documented **21** of **30** live tools, put three
    unconditional core tools in an "optional" tier, omitted the four
    shared-dependency tools entirely, and described ``add_project`` as an
    "unresolved contradiction" two releases after it was deliberately added;
  * ragtools' own ``integration/mcp_server.py`` module docstring said "3 core"
    when six tools carry the decorator.

A hand-maintained list nobody can check is a list that drifts. This turns drift
into a build failure instead of a discovery.

What it can and cannot check
----------------------------
A Claude Code plugin is **not** an MCP client — it is markdown, JSON and
scripts. It cannot open a stdio session and call ``tools/list`` without spawning
a second MCP server, which would contend with the running one. So there are
three sources, in descending order of authority:

  1. ``--source-tree <path>``  parse ragtools' ``integration/mcp_server.py``
     directly (decorators + the ``_register_ops_tools`` table). Authoritative.
  2. ``--registry-file <path>`` a newline- or JSON-list of tool names captured
     from a live session (``ToolSearch``, or the admin panel's MCP Tool Access
     card). Authoritative for *that* install's grants.
  3. no source                 self-check only: the table parses, tiers are
     well-formed, counts are internally consistent.

Exit codes: ``0`` no drift · ``1`` drift found · ``2`` usage/parse error.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Optional

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ENVELOPE = PLUGIN_ROOT / "rules" / "mcp-envelope.md"

#: Tier headings in the envelope, mapped to the tier label used in output.
_TIER_HEADINGS = [
    (re.compile(r"^### Tier 1 — Core", re.M), "core"),
    (re.compile(r"^### Tier 2 — Project inspection", re.M), "inspection"),
    (re.compile(r"^### Tier 3 — Project writes", re.M), "writes"),
    (re.compile(r"^### Tier 4 — Shared dependencies", re.M), "dependencies"),
    (re.compile(r"^### Tier 5 — Diagnostics", re.M), "diagnostics"),
]

_BACKTICKED = re.compile(r"`([a-z_][a-z0-9_]*)`")

# Words that appear in backticks inside the tier sections but are not tools.
_NOT_A_TOOL = {
    "mcp_app", "tool", "integration", "mcp_server", "py", "structured",
    "file_path", "mode", "access", "get", "name", "true", "settings",
    "mcp_tools", "config", "project", "projects", "rag", "odoo", "docs",
    "code", "general", "path", "query", "top_k", "confirm_token",
    "dependency_id", "project_id", "error_code", "error", "ok", "as_of",
    "data", "hint", "retry_after_seconds", "check", "none", "null",
    "x_mcp_session", "source", "state", "bound_port", "points", "reachable",
}


class InventoryFormatError(Exception):
    """The envelope is not in the tier format this gate contracts against.

    Reported as DRIFT (exit 1), not as a usage error (exit 2). A document that
    has lost its tier structure has a documentation defect — the gate ran fine.
    Exiting 2 there would read as "the tool is broken" and get ignored, which is
    how the v0.17.0 inventory survived three ragtools releases.
    """


def documented_tools(text: str) -> dict[str, str]:
    """Tool name -> tier label, parsed from the envelope's Tier sections."""
    positions = []
    for pattern, label in _TIER_HEADINGS:
        m = pattern.search(text)
        if m:
            positions.append((m.start(), label))
    if not positions:
        loose = {n for n in _BACKTICKED.findall(text)
                 if n not in _NOT_A_TOOL and "_" in n}
        raise InventoryFormatError(
            "no '### Tier N — ...' headings found. This envelope predates the "
            "tiered inventory contract (D-035); it names roughly "
            f"{len(loose)} tool-shaped identifiers with no tier structure, so "
            "core-vs-optional and default-on-vs-off cannot be checked at all."
        )
    positions.sort()

    # A tier section runs to the next '### '/'---' after its heading.
    out: dict[str, str] = {}
    for idx, (start, label) in enumerate(positions):
        end = len(text)
        nxt = re.compile(r"^(### |---$)", re.M).search(text, start + 5)
        if nxt:
            end = nxt.start()
        if idx + 1 < len(positions):
            end = min(end, positions[idx + 1][0])
        for name in _BACKTICKED.findall(text[start:end]):
            if name in _NOT_A_TOOL or "_" not in name:
                continue
            out.setdefault(name, label)
    return out


def live_tools_from_source(source_tree: Path) -> set[str]:
    """Parse ragtools' mcp_server.py: @mcp_app.tool() + the registration table."""
    candidates = [
        source_tree / "src" / "ragtools" / "integration" / "mcp_server.py",
        source_tree / "integration" / "mcp_server.py",
        source_tree,
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise FileNotFoundError(
            f"could not find integration/mcp_server.py under {source_tree}"
        )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()

    # Core: functions decorated with @mcp_app.tool()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                found.add(node.name)

    # Optional: the ("name", fn) tuples inside _register_ops_tools.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_register_ops_tools":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Tuple) and sub.elts:
                    first = sub.elts[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        found.add(first.value)
    return found


def live_tools_from_registry(path: Path) -> set[str]:
    """Tool names captured from a live session (JSON list or one per line)."""
    raw = path.read_text(encoding="utf-8").strip()
    names: list[str] = []
    if raw.startswith("["):
        names = [str(x) for x in json.loads(raw)]
    else:
        names = [line.strip() for line in raw.splitlines() if line.strip()]
    # Accept fully-qualified MCP names.
    return {n.rsplit("__", 1)[-1] for n in names if not n.startswith("#")}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=(__doc__ or "verify the MCP tool inventory").split("\n")[0]
    )
    ap.add_argument("--source-tree", type=Path,
                    help="ragtools checkout (authoritative)")
    ap.add_argument("--registry-file", type=Path,
                    help="file of tool names captured from a live session")
    ap.add_argument("--envelope", type=Path, default=ENVELOPE)
    args = ap.parse_args(argv)

    if not args.envelope.is_file():
        print(f"ERROR: {args.envelope} not found", file=sys.stderr)
        return 2
    try:
        documented = documented_tools(args.envelope.read_text(encoding="utf-8"))
    except InventoryFormatError as exc:
        print(f"INVENTORY FORMAT DRIFT: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    by_tier: dict[str, list[str]] = {}
    for name, tier in sorted(documented.items()):
        by_tier.setdefault(tier, []).append(name)
    print(f"documented: {len(documented)} tools")
    for tier in ("core", "inspection", "writes", "dependencies", "diagnostics"):
        names = by_tier.get(tier, [])
        print(f"  {tier:13s} {len(names):2d}  {', '.join(names)}")

    # Self-check: the tier shape the plugin claims.
    expected_counts = {"core": 6, "inspection": 5, "writes": 6,
                       "dependencies": 4, "diagnostics": 9}
    shape_drift = [
        f"{tier}: documented {len(by_tier.get(tier, []))}, expected {n}"
        for tier, n in expected_counts.items()
        if len(by_tier.get(tier, [])) != n
    ]
    if shape_drift:
        print("\nTIER SHAPE DRIFT:", file=sys.stderr)
        for line in shape_drift:
            print(f"  {line}", file=sys.stderr)
        return 1

    live: Optional[set[str]] = None
    origin = ""
    try:
        if args.source_tree:
            live, origin = live_tools_from_source(args.source_tree), "source tree"
        elif args.registry_file:
            live, origin = live_tools_from_registry(args.registry_file), "session registry"
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"ERROR reading live tools: {exc}", file=sys.stderr)
        return 2

    if live is None:
        print("\nno live source given — self-check only "
              "(pass --source-tree or --registry-file to gate on real drift)")
        return 0

    missing = sorted(live - set(documented))
    extra = sorted(set(documented) - live)
    print(f"\nlive ({origin}): {len(live)} tools")
    if not missing and not extra:
        print("no drift.")
        return 0
    if missing:
        print("\nUNDOCUMENTED (live but not in the envelope):", file=sys.stderr)
        for n in missing:
            print(f"  + {n}", file=sys.stderr)
    if extra:
        print("\nSTALE (documented but not live — removed, renamed, or "
              "disabled by grant):", file=sys.stderr)
        for n in extra:
            print(f"  - {n}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
