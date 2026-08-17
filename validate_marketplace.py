#!/usr/bin/env python3
"""validate_marketplace.py - marketplace-level architecture checks.

`validate_plugin.py` validates ONE plugin's internal shape. It passed 17/17 while
15 skills were silently undiscoverable at runtime, because a per-plugin structural
check cannot see:

  - a SKILL.md parked outside `<plugin>/skills/<name>/` (4 cases: devops, ntfy,
    pandoc, remotion had `<plugin>/<name>/SKILL.md`)
  - a SKILL.md nested one level too deep (11 cases: odoo had
    `skills/frontend/<sub>/SKILL.md` and `skills/owl/<sub>/SKILL.md`)
  - identity drift between plugin.json and the marketplace entry
  - a command and a skill claiming the same invocation name

This script closes that gap. It is dependency-free (stdlib only) and exits non-zero
on any ERROR so it can gate CI.

    python validate_marketplace.py            # all checks
    python validate_marketplace.py --json     # machine-readable
    python validate_marketplace.py --list     # show the check catalogue

DESIGN NOTE - folder name vs plugin identity:
    `odoo-plugin/` (filesystem) and `odoo` (plugin identity) intentionally differ.
    The folder name is repository architecture; the identity is the runtime
    namespace. This validator deliberately does NOT require them to match. It
    requires only that plugin.json and the marketplace entry agree with each other.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Frontmatter keys Claude Code accepts on a skill. Sourced from the harness
# allowlist; unknown keys are reported as WARN (forward-compatible, not fatal).
KNOWN_SKILL_KEYS = {
    "name", "description", "model", "allowed-tools", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "effort", "shell", "version",
    "when_to_use", "paths", "hooks", "context", "agent", "created_by",
    "improved_by", "license", "metadata", "allowed_tools",
}

errors: list[str] = []
warns: list[str] = []


def err(check: str, msg: str) -> None:
    errors.append(f"[{check}] {msg}")


def warn(check: str, msg: str) -> None:
    warns.append(f"[{check}] {msg}")


def plugin_dirs() -> list[Path]:
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir() and (p / ".claude-plugin" / "plugin.json").is_file()
    )


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err("json", f"{p.relative_to(ROOT)} is not valid JSON: {exc}")
        return None


def frontmatter(path: Path) -> dict | None:
    """Parse the leading YAML block without a yaml dependency.

    Handles `key: value`, block scalars (`|`, `>-`), and nested lines. Only
    top-level keys are returned; values are kept as raw text.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.match(r"(?s)\A---\s*\n(.*?)\n---\s*(\n|\Z)", text)
    if not m:
        return None
    out: dict[str, str] = {}
    key = None
    for line in m.group(1).split("\n"):
        km = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s?(.*)$", line)
        if km:
            key = km.group(1)
            out[key] = km.group(2)
        elif key is not None:
            out[key] = (out[key] + "\n" + line).strip()
    return out


# ---------------------------------------------------------------- checks

def check_identity(dirs: list[Path]) -> dict[Path, str]:
    """marketplace <-> plugin.json identity, duplicates, orphans."""
    mk = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    idents: dict[Path, str] = {}
    if not mk:
        return idents

    entries = mk.get("plugins", [])
    by_source = {}
    for e in entries:
        src = str(e.get("source", "")).lstrip("./").rstrip("/")
        by_source[src] = e.get("name")

    seen: dict[str, str] = {}
    for d in dirs:
        pj = load_json(d / ".claude-plugin" / "plugin.json")
        if not pj:
            continue
        ident = pj.get("name")
        idents[d] = ident
        if not ident:
            err("identity", f"{d.name}/plugin.json has no 'name'")
            continue

        mkname = by_source.get(d.name)
        if mkname is None:
            err("identity", f"{d.name}/ has plugin.json but NO marketplace entry "
                            f"(source: ./{d.name}) - it will not be installable")
        elif mkname != ident:
            err("identity",
                f"identity mismatch for {d.name}/: plugin.json name={ident!r} "
                f"but marketplace name={mkname!r}. These must agree "
                f"(the FOLDER name may differ from both - that is allowed).")

        if ident in seen:
            err("identity", f"duplicate plugin identity {ident!r} "
                            f"used by {seen[ident]} and {d.name}")
        seen[ident] = d.name

    known_sources = {d.name for d in dirs}
    for src, nm in by_source.items():
        if src not in known_sources:
            err("identity", f"marketplace entry {nm!r} points at ./{src} "
                            f"which has no plugin.json - orphan entry")
    return idents


def check_skill_discovery(dirs: list[Path]) -> None:
    """THE regression this file exists for: SKILL.md must be at
    <plugin>/skills/<name>/SKILL.md - no shallower, no deeper."""
    for d in dirs:
        for sk in d.rglob("SKILL.md"):
            rel = sk.relative_to(d)
            parts = rel.parts
            ok = len(parts) == 3 and parts[0] == "skills" and parts[2] == "SKILL.md"
            if ok:
                continue
            if parts[0] != "skills":
                err("discovery",
                    f"{d.name}/{rel.as_posix()} is OUTSIDE skills/ - Claude Code will "
                    f"NOT discover it. Move to {d.name}/skills/{parts[0]}/SKILL.md")
            else:
                err("discovery",
                    f"{d.name}/{rel.as_posix()} is nested too deep - Claude Code only "
                    f"discovers skills/<name>/SKILL.md. Flatten to "
                    f"{d.name}/skills/{parts[-2]}/SKILL.md")

        # A directory under skills/ with no SKILL.md is a dead container.
        sd = d / "skills"
        if sd.is_dir():
            for child in sorted(sd.iterdir()):
                if child.is_dir() and not (child / "SKILL.md").is_file():
                    nested = list(child.rglob("SKILL.md"))
                    if nested:
                        err("discovery",
                            f"{d.name}/skills/{child.name}/ has no SKILL.md but contains "
                            f"{len(nested)} nested one(s) - those are invisible at runtime")
                    else:
                        warn("discovery",
                             f"{d.name}/skills/{child.name}/ contains no SKILL.md")


def check_name_collisions(dirs: list[Path], idents: dict[Path, str]) -> None:
    """A command and a skill resolving to the same /<plugin>:<name> shadow each other."""
    for d in dirs:
        cmds = {}
        cdir = d / "commands"
        if cdir.is_dir():
            for f in sorted(cdir.glob("*.md")):
                fm = frontmatter(f) or {}
                cmds[(fm.get("name") or f.stem).strip()] = f.name

        skills = {}
        sdir = d / "skills"
        if sdir.is_dir():
            for f in sorted(sdir.glob("*/SKILL.md")):
                fm = frontmatter(f) or {}
                skills[(fm.get("name") or f.parent.name).strip()] = f.parent.name

        for nm in sorted(set(cmds) & set(skills)):
            err("collision",
                f"{idents.get(d, d.name)}: name {nm!r} is claimed by BOTH "
                f"commands/{cmds[nm]} and skills/{skills[nm]}/SKILL.md - "
                f"one will shadow the other at /{idents.get(d, d.name)}:{nm}")


def check_skill_frontmatter(dirs: list[Path]) -> None:
    for d in dirs:
        for f in sorted((d / "skills").glob("*/SKILL.md")) if (d / "skills").is_dir() else []:
            rel = f.relative_to(ROOT).as_posix()
            fm = frontmatter(f)
            if fm is None:
                err("frontmatter", f"{rel} has no YAML frontmatter block")
                continue
            if not fm.get("name"):
                err("frontmatter", f"{rel} has no 'name'")
            if not fm.get("description"):
                err("frontmatter", f"{rel} has no 'description'")
            for k in fm:
                if k not in KNOWN_SKILL_KEYS:
                    warn("frontmatter", f"{rel} has unrecognized key {k!r}")
            for boolkey in ("user-invocable", "disable-model-invocation"):
                v = (fm.get(boolkey) or "").strip().lower()
                if v and v not in ("true", "false"):
                    err("frontmatter", f"{rel}: {boolkey} must be true/false, got {v!r}")


def check_broken_refs(dirs: list[Path]) -> None:
    """Relative file references inside a SKILL.md that no longer resolve."""
    pat = re.compile(r"`((?:references|scripts|refs|examples|docs|assets)/[A-Za-z0-9_./-]+)`")
    for d in dirs:
        if not (d / "skills").is_dir():
            continue
        for f in sorted((d / "skills").glob("*/SKILL.md")):
            body = f.read_text(encoding="utf-8", errors="replace")
            for ref in set(pat.findall(body)):
                if not (f.parent / ref).exists():
                    warn("refs", f"{f.relative_to(ROOT).as_posix()} references "
                                 f"'{ref}' which does not exist")


def check_line_endings(dirs: list[Path]) -> None:
    for d in dirs:
        for f in d.rglob("*.sh"):
            try:
                if b"\r\n" in f.read_bytes():
                    err("eol", f"{f.relative_to(ROOT).as_posix()} has CRLF - "
                               f"bash fails with $'\\r': command not found")
            except Exception:
                pass


def check_state_in_plugin_root(dirs: list[Path]) -> None:
    """Persistent state must never be written into the version-pinned install dir."""
    write = re.compile(
        r"(open\s*\(\s*[^)]*|>>?\s*|mkdir\s+-p\s+|write_text|touch\s+)"
        r"[\"']?\$?\{?(CLAUDE_PLUGIN_ROOT|SCRIPT_DIR|PLUGIN_ROOT)\}?/"
        r"(logs|state|cache|data|refs|var|tmp)\b")
    for d in dirs:
        for f in list(d.rglob("*.py")) + list(d.rglob("*.sh")):
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(txt.split("\n"), 1):
                if write.search(line) and not line.lstrip().startswith(("#", "//")):
                    err("persistence",
                        f"{f.relative_to(ROOT).as_posix()}:{i} appears to write persistent "
                        f"state into the plugin install root (wiped on every upgrade). "
                        f"Use ${{CLAUDE_PLUGIN_DATA}} or ~/.claude/<plugin>/ instead")


def check_mcp(dirs: list[Path], idents: dict[Path, str]) -> None:
    """Legacy namespace refs + undefaulted ${VAR} in MCP configs."""
    harness = {"CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_DATA"}
    for d in dirs:
        mcp = d / ".mcp.json"
        if not mcp.is_file():
            continue
        cfg = load_json(mcp)
        if not cfg:
            continue
        servers = cfg.get("mcpServers", cfg)
        if not isinstance(servers, dict):
            err("mcp", f"{d.name}/.mcp.json has no server map")
            continue
        for sname, scfg in servers.items():
            blob = json.dumps(scfg)
            bare = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", blob))
            defaulted = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-", blob))
            risky = sorted(v for v in bare - defaulted if v not in harness)
            if risky:
                warn("mcp",
                     f"{d.name}/.mcp.json server {sname!r}: {risky} use bare ${{VAR}}. "
                     f"An unset variable is forwarded LITERALLY. Either give it a "
                     f"${{VAR:-}} default (if optional) or add a preflight check that "
                     f"explains the missing configuration (if required).")

    ident_set = set(idents.values())
    legacy = re.compile(r"mcp__(?!plugin_)([a-z0-9-]+)__")
    for d in dirs:
        for f in list(d.rglob("*.json")) + list(d.rglob("*.md")):
            if f.name in ("CHANGELOG.md",) or "/tests/" in f.as_posix():
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for srv in set(legacy.findall(txt)):
                if srv in ("ide",) or srv in ident_set:
                    continue
                warn("mcp-ns",
                     f"{f.relative_to(ROOT).as_posix()} references legacy "
                     f"'mcp__{srv}__' - plugin MCP tools are namespaced "
                     f"mcp__plugin_<plugin>_<server>__")


CHECKS = [
    ("identity",    "marketplace <-> plugin.json identity, duplicates, orphans"),
    ("discovery",   "SKILL.md is at the discoverable path skills/<name>/SKILL.md"),
    ("collision",   "no command and skill share an invocation name"),
    ("frontmatter", "skill frontmatter is present and valid"),
    ("refs",        "relative references inside SKILL.md resolve"),
    ("eol",         "shell scripts are LF"),
    ("persistence", "no plugin writes state into its own install root"),
    ("mcp",         "MCP env-var config and tool namespacing"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Marketplace architecture validator")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--list", action="store_true", help="list the check catalogue")
    args = ap.parse_args()

    if args.list:
        for n, desc in CHECKS:
            print(f"  {n:<12} {desc}")
        return 0

    dirs = plugin_dirs()
    idents = check_identity(dirs)
    check_skill_discovery(dirs)
    check_name_collisions(dirs, idents)
    check_skill_frontmatter(dirs)
    check_broken_refs(dirs)
    check_line_endings(dirs)
    check_state_in_plugin_root(dirs)
    check_mcp(dirs, idents)

    skills = sum(len(list((d / "skills").glob("*/SKILL.md"))) for d in dirs if (d / "skills").is_dir())

    if args.json:
        print(json.dumps({"plugins": len(dirs), "discoverable_skills": skills,
                          "errors": errors, "warnings": warns}, indent=2))
        return 1 if errors else 0

    print(f"Marketplace architecture check - {len(dirs)} plugins, "
          f"{skills} discoverable skills\n")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  x {e}")
        print()
    if warns:
        print(f"WARNINGS ({len(warns)}):")
        for w in warns[:40]:
            print(f"  ! {w}")
        if len(warns) > 40:
            print(f"  ... and {len(warns) - 40} more")
        print()
    if not errors:
        print(f"OK - no architecture errors ({len(warns)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
