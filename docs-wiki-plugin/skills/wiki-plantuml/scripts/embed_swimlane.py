#!/usr/bin/env python3
"""
Idempotently insert or replace the swimlane embed inside a wiki .md page, under a
stable "### Swimlane" marker, with the FLAVOUR-CORRECT embed snippet.

Owned by the docs-wiki `wiki-plantuml` skill.

Embed tracks (one source .puml, four wrappers):
  github  -> leading-slash wiki-link to a committed image: [[/images/<name>.png|alt]]
  azure   -> root-relative attachment image:               ![alt](/.attachments/<name>.png)
  gitlab  -> inline ```plantuml fence (no image)
  mkdocs  -> inline ```plantuml fence (no image)

Idempotent: re-running with the same inputs yields a byte-identical file (no diff).
Does NOT push or render — it only rewrites the "### Swimlane" region and prints the
unified diff for wiki-safe-updates to preview.
"""
from __future__ import annotations
import argparse
import difflib
import io
import re
import sys

MARKER = "### Swimlane"
# Match the "### Swimlane" heading and everything until the next heading (## or ###) or EOF.
BLOCK_RE = re.compile(r"(?ms)^### Swimlane\b.*?(?=^\#\#|\Z)")


def build_block(flavour: str, artifact: str, alt: str, puml_link: str | None,
                puml_source: str | None) -> str:
    flavour = flavour.lower()
    lines = [MARKER, ""]
    if flavour == "github":
        # Committed image in the OWNER/REPO.wiki.git repo; leading-slash wiki-link.
        lines.append(f"[[/images/{artifact}|{alt}]]")
    elif flavour == "azure":
        # Root-relative attachment (NOT relative to the .md).
        lines.append(f"![{alt}](/.attachments/{artifact})")
    elif flavour in ("gitlab", "mkdocs"):
        # Native render — inline the .puml source as a plantuml fence.
        if not puml_source:
            print("error: --puml-source is required for gitlab/mkdocs (native render).",
                  file=sys.stderr)
            sys.exit(2)
        lines.append("```plantuml")
        lines.append(puml_source.rstrip("\n"))
        lines.append("```")
    else:
        print(f"error: unknown flavour '{flavour}'.", file=sys.stderr)
        sys.exit(2)

    if puml_link:
        lines.append("")
        lines.append(f"_Source: [{puml_link}]({puml_link}) — edit the `.puml`, re-render; "
                     f"never hand-edit the image._")
    lines.append("")  # trailing blank before the next section
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Idempotently embed a swimlane into a wiki page.")
    ap.add_argument("--page", required=True, help="path to the wiki .md page")
    ap.add_argument("--flavour", required=True, choices=["github", "azure", "gitlab", "mkdocs"])
    ap.add_argument("--artifact", required=True,
                    help="image filename for github/azure, e.g. swimlane-orders-fulfilment.png")
    ap.add_argument("--alt", required=True, help="alt text (required — accessibility)")
    ap.add_argument("--puml-link", default=None, help="relative path/URL to the .puml source")
    ap.add_argument("--puml-source", default=None,
                    help="the .puml text (required for gitlab/mkdocs native fences)")
    args = ap.parse_args()

    if not args.alt.strip():
        print("error: --alt must be meaningful (accessibility).", file=sys.stderr)
        return 2

    with io.open(args.page, "r", encoding="utf-8") as f:
        original = f.read()

    block = build_block(args.flavour, args.artifact, args.alt, args.puml_link, args.puml_source)

    match = BLOCK_RE.search(original)
    if match:
        # Splice by span (avoids re.sub backslash processing on the .puml source).
        updated = original[:match.start()] + block + original[match.end():]
    else:
        # Append a new Swimlane section at the end, separated by a blank line.
        sep = "" if original.endswith("\n\n") else ("\n" if original.endswith("\n") else "\n\n")
        updated = original + sep + block

    if updated == original:
        print("no change (idempotent): the page already has this exact Swimlane block.")
        return 0

    diff = difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile=args.page + " (current)", tofile=args.page + " (proposed)",
    )
    sys.stdout.writelines(diff)

    with io.open(args.page, "w", encoding="utf-8", newline="") as f:
        f.write(updated)
    print(f"\nwrote {args.page} — preview the diff via wiki-safe-updates before pushing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
