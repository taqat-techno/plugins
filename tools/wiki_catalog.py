#!/usr/bin/env python3
"""Regenerate the plugin table and totals in wiki/Plugin-Catalog.md from the plugin files.

    python tools/wiki_catalog.py           # rewrite the table
    python tools/wiki_catalog.py --check   # exit 1 if the table is stale
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "wiki" / "Plugin-Catalog.md"
WIKI_PAGES = {p.stem for p in (ROOT / "wiki").glob("*-Plugin.md")}


def is_deprecated(cmd: Path) -> bool:
    head = "\n".join(cmd.read_text(encoding="utf-8", errors="replace").splitlines()[:8]).lower()
    return "deprecated" in head


def hook_handlers(plugin: Path) -> int:
    path = plugin / "hooks" / "hooks.json"
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    # Count distinct scripts, so notification's three-interpreter fallback counts once per event.
    seen = set()
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                args = [a for a in (hook.get("args") or []) if a != "-3"]
                target = " ".join(args) or hook.get("command", "")
                seen.add((event, group.get("matcher", ""), re.sub(r"\b(python3?|py -3|py)\b", "", target)))
    return len(seen)


def row(i: int, entry: dict) -> tuple[str, dict]:
    plugin = ROOT / entry["source"]
    pj = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    cmds = [c for c in (plugin / "commands").glob("*.md")] if (plugin / "commands").is_dir() else []
    counts = {
        "commands": sum(not is_deprecated(c) for c in cmds),
        "agents": len(list((plugin / "agents").glob("*.md"))) if (plugin / "agents").is_dir() else 0,
        "skills": len(list((plugin / "skills").glob("*/SKILL.md"))) if (plugin / "skills").is_dir() else 0,
        "hooks": hook_handlers(plugin),
        "mcp": (plugin / ".mcp.json").is_file(),
        "fire": len(list((plugin / "evals").glob("fires-*"))) if (plugin / "evals").is_dir() else 0,
        "ignore": len(list((plugin / "evals").glob("ignores-*"))) if (plugin / "evals").is_dir() else 0,
    }
    page = "-".join(w.capitalize() if w != "devops" else "DevOps" for w in entry["name"].split("-")) + "-Plugin"
    page = page.replace("Ui-Ux", "Ui-Ux")
    docs = (f"[[{page.replace('-', ' ')}\\|{page}]] · " if page in WIKI_PAGES else "") + \
           f"[README](../../{plugin.name}/README.md)"
    evals = f"{counts['fire']} + {counts['ignore']}" if counts["fire"] or counts["ignore"] else "n/a"
    line = (f"| {i} | **{entry['name']}** | `{pj['version']}` | {entry.get('category', '')} | "
            f"{counts['commands']} | {counts['agents']} | {counts['skills']} | {counts['hooks']} | "
            f"{'yes' if counts['mcp'] else '—'} | {evals} | {docs} |")
    return line, counts


def render() -> tuple[str, str]:
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    rows, tot = [], {"commands": 0, "agents": 0, "skills": 0, "hooks": 0, "mcp": 0, "fire": 0, "ignore": 0}
    for i, entry in enumerate(market["plugins"], 1):
        line, c = row(i, entry)
        rows.append(line)
        for k in tot:
            tot[k] += int(c[k])
    table = "\n".join(rows)
    totals = (f"**Totals:** {tot['commands']} commands · {tot['agents']} agents · {tot['skills']} skills · "
              f"{tot['hooks']} hook handlers · {tot['mcp']} bundled MCP servers · "
              f"{tot['fire'] + tot['ignore']} eval cases ({tot['fire']} must-fire + {tot['ignore']} must-not-fire).")
    return table, totals


def main(argv: list[str]) -> int:
    raw = PAGE.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    table, totals = render()
    new = re.sub(r"(?m)^(\|---(?:\|---)+\|\n)(?:\| \d+ \|.*\n)+", lambda m: m.group(1) + table + "\n", text, count=1)
    new = re.sub(r"(?m)^\*\*Totals:\*\*.*$", lambda m: totals, new, count=1)
    count = len(json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["plugins"])
    new = re.sub(r"All \d+ plugins", f"All {count} plugins", new, count=1)
    if "--check" in argv:
        stale = new != text
        print("wiki catalog: " + ("stale" if stale else "ok"))
        return 1 if stale else 0
    PAGE.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
    print("wiki catalog: written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
