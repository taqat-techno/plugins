#!/usr/bin/env python3
"""
Orchestrate the swimlane publish: render -> (Azure attach | GitHub stage) -> embed ->
diff-preview -> approval (wiki-safe-updates) -> commit/push ONLY on explicit approval.

Owned by the docs-wiki `wiki-plantuml` skill. This is the single entry the /wiki-swimlane
command drives. It composes the sibling helper scripts and enforces the governance gate.

Governance / safety:
  - Renders locally by default (privacy-safe). renderMode=kroki REFUSES a public endpoint.
  - Never echoes the PAT (delegated to upload_attachment.ps1, which reads $env:AZDO_PAT).
  - Stops at the diff preview unless --approve is passed (mirrors wiki-safe-updates:
    nothing is committed/pushed without explicit approval).
  - Idempotent: a no-op .puml change produces no diff and no commit.

Pipelines by flavour:
  github  -> render PNG, copy into the OWNER/REPO.wiki.git sibling clone /images, embed,
             (on --approve) git add+commit+push from the .wiki clone.
  azure   -> render PNG, upload_attachment.ps1 (base64 + verify-on-500), embed root-relative,
             (on --approve) publish the page edit.
  gitlab/mkdocs -> NO render/attach; embed the inline ```plantuml fence (native render),
             (on --approve) commit the page.
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
PUBLIC_KROKI = ("kroki.io", "www.plantuml.com", "plantuml.com")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print("+ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=False, text=True)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish a swimlane through the governance gate.")
    ap.add_argument("--page", required=True, help="the wiki .md page to embed into")
    ap.add_argument("--flavour", required=True, choices=["github", "azure", "gitlab", "mkdocs"])
    ap.add_argument("--puml", required=True, help="the swimlane .puml source")
    ap.add_argument("--alt", required=True, help="alt text (accessibility)")
    ap.add_argument("--render", choices=["local", "kroki"], default="local")
    ap.add_argument("--kroki-endpoint", default=os.environ.get("DOCS_WIKI_KROKI_ENDPOINT"))
    ap.add_argument("--format", choices=["svg", "png"], default=None,
                    help="default PNG for github/azure, svg for gitlab/mkdocs")
    # GitHub
    ap.add_argument("--wiki-clone", help="path to the OWNER/REPO.wiki.git sibling clone (github)")
    # Azure
    ap.add_argument("--org"); ap.add_argument("--project"); ap.add_argument("--wiki-id")
    ap.add_argument("--approve", action="store_true",
                    help="actually commit/publish after the diff preview (otherwise stop at preview)")
    args = ap.parse_args()

    puml = Path(args.puml)
    if not puml.is_file():
        die(f"puml not found: {puml}")

    # --- governance: kroki endpoint ---
    if args.render == "kroki":
        ep = (args.kroki_endpoint or "").strip()
        if not ep:
            die("renderMode=kroki requires a self-hosted --kroki-endpoint (no default).")
        if any(h in ep for h in PUBLIC_KROKI):
            die("REFUSED: a PUBLIC Kroki/PlantUML endpoint receives the full diagram source "
                "(paste-leak). Use a self-hosted endpoint.")

    fmt = args.format or ("svg" if args.flavour in ("gitlab", "mkdocs") else "png")
    base = puml.stem  # swimlane-<epic>-<slug>
    artifact_name = f"{base}.{fmt}"

    # --- render (github/azure only; gitlab/mkdocs render natively) ---
    rendered: Path | None = None
    if args.flavour in ("github", "azure"):
        if args.render == "local":
            ps = ["pwsh", "-File", str(HERE / "render_puml.ps1"),
                  "-Puml", str(puml), "-Format", fmt]
            if run(ps).returncode != 0:
                die("render_puml.ps1 failed.")
            rendered = puml.with_suffix(f".{fmt}")
        else:
            die("kroki render path: POST the .puml to the self-hosted endpoint, save the "
                f"output as {artifact_name}, then re-run with --render local-style staging "
                "(kroki output still feeds commit/attach, never a live <img> src).")
        if rendered and not rendered.is_file():
            die(f"expected rendered artifact missing: {rendered}")

    # --- attach / stage ---
    embed_extra: list[str] = []
    if args.flavour == "azure":
        for req in ("org", "project", "wiki_id"):
            if not getattr(args, req):
                die(f"azure flavour requires --{req.replace('_','-')}")
        ps = ["pwsh", "-File", str(HERE / "upload_attachment.ps1"),
              "-Org", args.org, "-Project", args.project, "-WikiId", args.wiki_id,
              "-File", str(rendered), "-Name", artifact_name]
        if run(ps).returncode != 0:
            die("upload_attachment.ps1 failed (see verify-on-fail output above).")
    elif args.flavour == "github":
        if not args.wiki_clone:
            die("github flavour requires --wiki-clone (the OWNER/REPO.wiki.git sibling path).")
        if rendered is None:
            die("internal: github flavour produced no rendered artifact.")
        images = Path(args.wiki_clone) / "images"
        images.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(rendered), images / artifact_name)
        print(f"staged image into {images / artifact_name}")

    # --- embed (idempotent ### Swimlane block; prints the diff) ---
    embed = [sys.executable, str(HERE / "embed_swimlane.py"),
             "--page", args.page, "--flavour", args.flavour,
             "--artifact", artifact_name, "--alt", args.alt,
             "--puml-link", str(puml)]
    if args.flavour in ("gitlab", "mkdocs"):
        embed += ["--puml-source", puml.read_text(encoding="utf-8")]
    embed += embed_extra
    if run(embed).returncode != 0:
        die("embed_swimlane.py failed.")

    # --- approval gate ---
    if not args.approve:
        print("\n--- PREVIEW ONLY ---")
        print("Reviewed the diff above? Re-run with --approve to commit/publish through "
              "wiki-safe-updates. Nothing was pushed.")
        return 0

    print("\n--approve set: commit/publish step.")
    print("Route this through wiki-safe-updates (diff preview already shown). "
          "For github: commit+push from the .wiki clone. For azure/gitlab/mkdocs: commit the page edit.")
    # Intentionally does NOT auto-push: the actual git push remains a deliberate, gated action.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
