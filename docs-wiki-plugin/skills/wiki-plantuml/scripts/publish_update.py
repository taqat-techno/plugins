#!/usr/bin/env python3
"""
Orchestrate the swimlane publish: validate -> preview (diff + pending actions) ->
on --approve ONLY: render -> (Azure attach | GitHub stage) -> embed (page write).

Owned by the docs-wiki `wiki-plantuml` skill. This is the single entry the /wiki-swimlane
command drives. It composes the sibling helper scripts and enforces the governance gate.

Governance / safety:
  - The --approve check comes BEFORE every side effect. A run without --approve (the
    default) is a pure preview: it makes NO network call (no Azure attachment upload),
    stages NO image into the wiki clone, and does NOT write the page. The only write is
    a local render into a temporary directory (deleted on exit) to prove the .puml
    renders; the page diff is computed by embed_swimlane.py --dry-run.
  - Renders locally by default (privacy-safe). renderMode=kroki REFUSES a public endpoint.
  - Never echoes the PAT (delegated to upload_attachment.ps1, which reads $env:AZDO_PAT).
  - Idempotent: a no-op .puml change produces no diff.
  - Never commits or pushes: after --approve the git commit/push (or live page publish)
    remains a deliberate step routed through wiki-safe-updates.

Pipelines by flavour (side effects happen only with --approve):
  github  -> render PNG, copy into the OWNER/REPO.wiki.git sibling clone /images, embed.
  azure   -> render PNG, upload_attachment.ps1 (base64 + verify-on-500), embed root-relative.
  gitlab/mkdocs -> NO render/attach; embed the inline ```plantuml fence (native render).
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
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


def build_parser() -> argparse.ArgumentParser:
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
                    help="perform the upload / image staging / page write. Without it the run "
                         "is a preview: diff + pending actions, no network, no writes.")
    return ap


def validate(args: argparse.Namespace) -> None:
    """Every precondition, checked before ANY side effect."""
    if not Path(args.puml).is_file():
        die(f"puml not found: {args.puml}")
    if args.render == "kroki":
        ep = (args.kroki_endpoint or "").strip()
        if not ep:
            die("renderMode=kroki requires a self-hosted --kroki-endpoint (no default).")
        if any(h in ep for h in PUBLIC_KROKI):
            die("REFUSED: a PUBLIC Kroki/PlantUML endpoint receives the full diagram source "
                "(paste-leak). Use a self-hosted endpoint.")
    if args.flavour == "azure":
        for req in ("org", "project", "wiki_id"):
            if not getattr(args, req):
                die(f"azure flavour requires --{req.replace('_', '-')}")
    if args.flavour == "github" and not args.wiki_clone:
        die("github flavour requires --wiki-clone (the OWNER/REPO.wiki.git sibling path).")


def render(args: argparse.Namespace, fmt: str, out_dir: Path | None) -> Path | None:
    """Local render for github/azure (gitlab/mkdocs render natively). No network."""
    if args.flavour not in ("github", "azure"):
        return None
    puml = Path(args.puml)
    if args.render != "local":
        die("kroki render path: POST the .puml to the self-hosted endpoint, save the "
            f"output as {puml.stem}.{fmt}, then re-run with --render local-style staging "
            "(kroki output still feeds commit/attach, never a live <img> src).")
    ps = ["pwsh", "-File", str(HERE / "render_puml.ps1"), "-Puml", str(puml), "-Format", fmt]
    if out_dir is not None:
        ps += ["-Out", str(out_dir)]
    if run(ps).returncode != 0:
        die("render_puml.ps1 failed.")
    rendered = (out_dir / f"{puml.stem}.{fmt}") if out_dir is not None \
        else puml.with_suffix(f".{fmt}")
    if not rendered.is_file():
        die(f"expected rendered artifact missing: {rendered}")
    return rendered


def embed_command(args: argparse.Namespace, artifact_name: str, dry_run: bool) -> list[str]:
    cmd = [sys.executable, str(HERE / "embed_swimlane.py"),
           "--page", args.page, "--flavour", args.flavour,
           "--artifact", artifact_name, "--alt", args.alt,
           "--puml-link", str(args.puml)]
    if args.flavour in ("gitlab", "mkdocs"):
        cmd += ["--puml-source", Path(args.puml).read_text(encoding="utf-8")]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def pending_actions(args: argparse.Namespace, artifact_name: str) -> list[str]:
    actions: list[str] = []
    if args.flavour == "azure":
        actions.append(f"render {args.puml} -> {artifact_name} (local)")
        actions.append(f"UPLOAD {artifact_name} to Azure DevOps wiki attachments "
                       f"(org={args.org}, project={args.project}, wiki={args.wiki_id}) [network]")
    elif args.flavour == "github":
        actions.append(f"render {args.puml} -> {artifact_name} (local)")
        actions.append(f"copy {artifact_name} into {Path(args.wiki_clone) / 'images'}")
    actions.append(f"write the ### Swimlane block into {args.page}")
    return actions


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate(args)

    fmt = args.format or ("svg" if args.flavour in ("gitlab", "mkdocs") else "png")
    artifact_name = f"{Path(args.puml).stem}.{fmt}"  # swimlane-<epic>-<slug>.<fmt>

    # --- approval gate: FIRST, before any upload / staging / page write ---
    if not args.approve:
        with tempfile.TemporaryDirectory(prefix="docs-wiki-swimlane-") as tmp:
            render(args, fmt, Path(tmp))  # proves the source renders; output discarded
        if run(embed_command(args, artifact_name, dry_run=True)).returncode != 0:
            die("embed_swimlane.py --dry-run failed.")
        print("\n--- PREVIEW ONLY --- nothing was uploaded, staged, or written.")
        print("Pending actions on --approve:")
        for action in pending_actions(args, artifact_name):
            print("  - " + action)
        print("Reviewed the diff above? Re-run with --approve to perform them "
              "(routed through wiki-safe-updates).")
        return 0

    print("--approve set: render -> attach/stage -> embed.")
    rendered = render(args, fmt, None)

    # --- attach / stage ---
    if args.flavour == "azure":
        ps = ["pwsh", "-File", str(HERE / "upload_attachment.ps1"),
              "-Org", args.org, "-Project", args.project, "-WikiId", args.wiki_id,
              "-File", str(rendered), "-Name", artifact_name]
        if run(ps).returncode != 0:
            die("upload_attachment.ps1 failed (see verify-on-fail output above).")
    elif args.flavour == "github":
        if rendered is None:
            die("internal: github flavour produced no rendered artifact.")
        images = Path(args.wiki_clone) / "images"
        images.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(rendered), images / artifact_name)
        print(f"staged image into {images / artifact_name}")

    # --- embed (idempotent ### Swimlane block; prints the diff, writes the page) ---
    if run(embed_command(args, artifact_name, dry_run=False)).returncode != 0:
        die("embed_swimlane.py failed.")

    print("\nRoute the commit through wiki-safe-updates. For github: commit+push from the "
          ".wiki clone. For azure/gitlab/mkdocs: commit/publish the page edit.")
    # Intentionally does NOT auto-push: the actual git push remains a deliberate, gated action.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
