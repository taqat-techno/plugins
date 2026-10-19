#!/usr/bin/env python3
"""
Render a PlantUML activity-beta swimlane (.puml) to SVG (default) or PNG locally -
the privacy-safe default render path (no network, the source never egresses).

Owned by the docs-wiki `wiki-plantuml` skill. Standard library only; runs on
Windows, macOS and Linux (no PowerShell needed).

Renderer discovery (first match wins):
  1. --plantuml-jar <path>          -> java -jar <path>
  2. PLANTUML_JAR env var           -> java -jar <path>
     (DOCS_WIKI_PLANTUML_JAR is accepted as a legacy alias)
  3. a `plantuml` executable on PATH (Homebrew / apt / choco / scoop wrapper)
A jar needs Java 8+: --java <exe>, else DOCS_WIKI_JAVA, else $JAVA_HOME/bin/java,
else `java` on PATH. If nothing is found the script exits 2 with install steps.

Guarantees:
  - Refuses the 2012 Maven-"latest" build 8059 trap (pin a 1.2026.x jar).
  - Sets PLANTUML_LIMIT_SIZE (default 8192) to clear the silent 4096px-per-axis clip.
  - Lints before rendering: rejects the DEPRECATED prefix colour form (#color:text;)
    and unbalanced if/endif gateways - both mis-render silently in activity-beta.

    python render_puml.py --puml swimlane-orders-fulfilment.puml --format png
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Optional

INSTALL_HELP = """\
PlantUML renderer not found. Install ONE of:
  * Java 8+ plus a pinned PlantUML jar (1.2026.x from
    https://github.com/plantuml/plantuml/releases), then pass --plantuml-jar <path>
    or set PLANTUML_JAR=<path>.
      Windows: winget install EclipseAdoptium.Temurin.21.JRE   (or: choco install temurin)
      macOS:   brew install openjdk
      Linux:   sudo apt install default-jre   (or: dnf install java-21-openjdk)
  * the `plantuml` CLI on PATH (bundles/uses Java):
      Windows: choco install plantuml   (or: scoop install plantuml)
      macOS:   brew install plantuml
      Linux:   sudo apt install plantuml   (distro builds can be old - prefer the jar)
  * or render through a SELF-HOSTED Kroki endpoint (publish_update.py --render kroki).
    Public kroki.io / plantuml.com are refused (paste-leak)."""

Which = Callable[[str], Optional[str]]


class RendererNotFound(Exception):
    """No usable PlantUML renderer (jar + Java, or `plantuml` on PATH)."""


def find_java(java_flag: str | None, environ: Mapping[str, str], which: Which) -> str | None:
    for cand in (java_flag, environ.get("DOCS_WIKI_JAVA")):
        if cand:
            return which(cand) or (cand if Path(cand).is_file() else None)
    home = environ.get("JAVA_HOME")
    if home:
        for name in ("java.exe", "java"):
            exe = Path(home) / "bin" / name
            if exe.is_file():
                return str(exe)
    return which("java")


def resolve_renderer(jar_flag: str | None = None, java_flag: str | None = None,
                     environ: Mapping[str, str] | None = None,
                     which: Which | None = None) -> list[str]:
    """Return the command prefix to invoke PlantUML. Raises RendererNotFound."""
    env = os.environ if environ is None else environ
    which = which or shutil.which
    jar = jar_flag or env.get("PLANTUML_JAR") or env.get("DOCS_WIKI_PLANTUML_JAR")
    if jar:
        if not Path(jar).is_file():
            raise RendererNotFound(f"plantuml.jar not found: {jar}\n\n{INSTALL_HELP}")
        if "8059" in Path(jar).name:
            raise RendererNotFound(
                f"Refusing plantuml jar '{jar}' - build 8059 is the 2012 Maven-'latest' "
                "trap. Pin a 1.2026.x jar.")
        java = find_java(java_flag, env, which)
        if not java:
            raise RendererNotFound(
                f"Java not found (needed to run {Path(jar).name}; Java 8+). Pass --java, "
                f"set DOCS_WIKI_JAVA or JAVA_HOME, or put java on PATH.\n\n{INSTALL_HELP}")
        return [java, "-jar", jar]
    cli = which("plantuml")
    if cli:
        return [cli]
    raise RendererNotFound(INSTALL_HELP)


def lint(src: str) -> list[str]:
    """Authoring faults that mis-render silently in activity-beta."""
    problems: list[str] = []
    prefix = [i + 1 for i, line in enumerate(src.splitlines())
              if re.match(r"^\s*#[0-9A-Za-z]+\s*:.+;\s*$", line)]
    if prefix:
        problems.append(
            f"Deprecated PREFIX colour form on line(s) {', '.join(map(str, prefix))}. "
            "activity-beta requires the END-OF-LINE suffix stereotype ':text; <<#RRGGBB>>'.")
    ifs = len(re.findall(r"(?m)^\s*if\s*\(", src))
    endifs = len(re.findall(r"(?m)^\s*endif\b", src))
    if ifs != endifs:
        problems.append(f"Unbalanced gateways: {ifs} 'if(' vs {endifs} 'endif'. "
                        "Balance them before rendering.")
    return problems


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Render a .puml swimlane locally (no network).")
    ap.add_argument("--puml", required=True)
    ap.add_argument("--format", choices=["svg", "png"], default="svg")
    ap.add_argument("--out", help="output directory (default: the .puml's directory)")
    ap.add_argument("--plantuml-jar", help="plantuml.jar path (else PLANTUML_JAR, else "
                                           "`plantuml` on PATH)")
    ap.add_argument("--java", help="java executable for the jar (else DOCS_WIKI_JAVA, "
                                   "JAVA_HOME, PATH)")
    ap.add_argument("--limit-size", type=int, default=8192, help="PLANTUML_LIMIT_SIZE")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    puml = Path(args.puml).resolve()
    if not puml.is_file():
        print(f"error: puml not found: {args.puml}", file=sys.stderr)
        return 1
    problems = lint(puml.read_text(encoding="utf-8"))
    if problems:
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        return 1
    try:
        prefix = resolve_renderer(args.plantuml_jar, args.java)
    except RendererNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out).resolve() if args.out else puml.parent
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PLANTUML_LIMIT_SIZE=str(args.limit_size))
    cmd = prefix + [f"-t{args.format}", "-o", str(out), str(puml)]
    print(f"Rendering {puml.name} -> {args.format} (limit={args.limit_size}) with "
          f"{Path(prefix[-1]).name}")
    proc = subprocess.run(cmd, env=env, check=False)
    if proc.returncode != 0:
        print(f"error: PlantUML render failed (exit {proc.returncode}).", file=sys.stderr)
        return 1
    artifact = out / f"{puml.stem}.{args.format}"
    if not artifact.is_file():
        print(f"error: render reported success but {artifact} is missing.", file=sys.stderr)
        return 1
    print(f"OK: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
