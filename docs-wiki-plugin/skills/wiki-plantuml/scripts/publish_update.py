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
  - Renders locally by default (privacy-safe). --render kroki POSTs the source to a
    SELF-HOSTED Kroki endpoint, only with --approve (a preview makes no network call),
    and REFUSES a public endpoint.
  - The "_Source:" link in the page is the .puml path relative to the wiki root, never an
    absolute local path; a .puml outside the wiki gets no link (WIKI-P2-08).
  - Never echoes the PAT (delegated to upload_attachment.py, which reads AZDO_PAT from env).
  - No PowerShell dependency: the render + upload helpers are Python (stdlib only) and are
    run with sys.executable. Rendering needs Java 8+ and a PlantUML jar (--plantuml-jar /
    PLANTUML_JAR) or a `plantuml` executable on PATH - see render_puml.py.
  - Idempotent: a no-op .puml change produces no diff.
  - Never commits or pushes: after --approve the git commit/push (or live page publish)
    remains a deliberate step routed through wiki-safe-updates.

Pipelines by flavour (side effects happen only with --approve):
  github  -> render PNG, copy into the OWNER/REPO.wiki.git sibling clone /images, embed.
  azure   -> render PNG, upload_attachment.py (base64 + verify-on-500), embed root-relative.
  gitlab/mkdocs -> NO render/attach; embed the inline ```plantuml fence (native render).
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
PUBLIC_KROKI = ("kroki.io", "plantuml.com")  # each also covers its subdomains


def endpoint_host(endpoint: str) -> str | None:
    """Lower-cased hostname of an endpoint URL (scheme optional), without the port,
    userinfo or trailing dot; None when no host can be read."""
    ep = (endpoint or "").strip().replace("\\", "/")
    if "://" not in ep:
        ep = "http://" + ep.lstrip("/")
    try:
        host = urllib.parse.urlsplit(ep).hostname
    except ValueError:
        return None
    host = (host or "").rstrip(".").lower()
    return host or None


def is_public_kroki(endpoint: str) -> bool:
    """True for a public Kroki / PlantUML host (exact or subdomain, case-insensitive),
    and for an endpoint whose host cannot be read (fail closed)."""
    host = endpoint_host(endpoint)
    if host is None:
        return True
    return any(host == h or host.endswith("." + h) for h in PUBLIC_KROKI)


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
    ap.add_argument("--plantuml-jar", default=None,
                    help="plantuml.jar for the local render (else PLANTUML_JAR env, else "
                         "`plantuml` on PATH)")
    # GitHub
    ap.add_argument("--wiki-clone", help="path to the OWNER/REPO.wiki.git sibling clone (github)")
    ap.add_argument("--wiki-root", default=None,
                    help="wiki root used to make the .puml link relative (default: the "
                         "--wiki-clone for github, else the page's directory)")
    # Azure
    ap.add_argument("--org"); ap.add_argument("--project"); ap.add_argument("--wiki-id")
    ap.add_argument("--body-encoding", choices=["base64", "raw"], default="base64",
                    help="azure attachment body form, passed to upload_attachment.py")
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
        if is_public_kroki(ep):
            die("REFUSED: a PUBLIC Kroki/PlantUML endpoint (or one whose host cannot be "
                "read) receives the full diagram source (paste-leak). Use a self-hosted "
                "endpoint.")
    if args.flavour == "azure":
        for req in ("org", "project", "wiki_id"):
            if not getattr(args, req):
                die(f"azure flavour requires --{req.replace('_', '-')}")
        # The PAT is sent to this host: refuse plain http before any side effect and
        # warn on a host that is not Azure DevOps (WIKI-P3-21).
        sys.dont_write_bytecode = True  # no __pycache__ next to the shipped scripts
        sys.path.insert(0, str(HERE))
        try:
            from upload_attachment import check_org
        finally:
            sys.path.pop(0)
        try:
            _, warning = check_org(args.org)
        except ValueError as exc:
            die(str(exc))
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
    if args.flavour == "github" and not args.wiki_clone:
        die("github flavour requires --wiki-clone (the OWNER/REPO.wiki.git sibling path).")


def kroki_render(endpoint: str, puml: Path, fmt: str, out_dir: Path) -> Path:
    """POST the source to a self-hosted Kroki (`<endpoint>/plantuml/<fmt>`) and save the
    output. Called only after --approve."""
    url = endpoint.rstrip("/") + "/plantuml/" + urllib.parse.quote(fmt)
    req = urllib.request.Request(url, data=puml.read_bytes(), method="POST",
                                 headers={"Content-Type": "text/plain"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (self-hosted)
            body = resp.read()
    except Exception as exc:  # noqa: BLE001
        die(f"kroki render failed ({type(exc).__name__}): {exc}")
    out = out_dir / f"{puml.stem}.{fmt}"
    out.write_bytes(body)
    print(f"rendered via kroki -> {out}")
    return out


def render(args: argparse.Namespace, fmt: str, out_dir: Path | None) -> Path | None:
    """Render for github/azure (gitlab/mkdocs render natively). Local render: no network.
    Kroki: network, so it runs only on --approve (out_dir None means approved)."""
    if args.flavour not in ("github", "azure"):
        return None
    puml = Path(args.puml)
    if args.render == "kroki":
        if out_dir is not None:
            print("preview: the kroki render runs on --approve (no network call now).")
            return None
        return kroki_render(args.kroki_endpoint.strip(), puml, fmt, puml.parent)
    cmd = [sys.executable, str(HERE / "render_puml.py"), "--puml", str(puml), "--format", fmt]
    if out_dir is not None:
        cmd += ["--out", str(out_dir)]
    if args.plantuml_jar:
        cmd += ["--plantuml-jar", args.plantuml_jar]
    if run(cmd).returncode != 0:
        die("render_puml.py failed (see its error above).")
    rendered = (out_dir / f"{puml.stem}.{fmt}") if out_dir is not None \
        else puml.with_suffix(f".{fmt}")
    if not rendered.is_file():
        die(f"expected rendered artifact missing: {rendered}")
    return rendered


def puml_link(args: argparse.Namespace) -> str | None:
    """The .puml path relative to the wiki root, POSIX form, or None when the source sits
    outside the wiki (an absolute local path would leak into the published page)."""
    root = args.wiki_root or (args.wiki_clone if args.flavour == "github" else None) \
        or str(Path(args.page).resolve().parent)
    try:
        rel = os.path.relpath(Path(args.puml).resolve(), Path(root).resolve())
    except ValueError:  # different drive on Windows
        return None
    rel = Path(rel).as_posix()
    if rel.startswith("../") or rel == "..":
        return None
    return rel


def embed_command(args: argparse.Namespace, artifact_name: str, dry_run: bool) -> list[str]:
    cmd = [sys.executable, str(HERE / "embed_swimlane.py"),
           "--page", args.page, "--flavour", args.flavour,
           "--artifact", artifact_name, "--alt", args.alt]
    link = puml_link(args)
    if link:
        cmd += ["--puml-link", link]
    if args.flavour in ("gitlab", "mkdocs"):
        cmd += ["--puml-source", Path(args.puml).read_text(encoding="utf-8")]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def pending_actions(args: argparse.Namespace, artifact_name: str) -> list[str]:
    actions: list[str] = []
    if args.flavour == "azure":
        actions.append(f"render {args.puml} -> {artifact_name} ({args.render})")
        actions.append(f"UPLOAD {artifact_name} to Azure DevOps wiki attachments "
                       f"(org={args.org}, project={args.project}, wiki={args.wiki_id}) [network]")
    elif args.flavour == "github":
        actions.append(f"render {args.puml} -> {artifact_name} ({args.render})")
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
        cmd = [sys.executable, str(HERE / "upload_attachment.py"),
               "--org", args.org, "--project", args.project, "--wiki-id", args.wiki_id,
               "--file", str(rendered), "--name", artifact_name,
               "--body-encoding", args.body_encoding]
        if run(cmd).returncode != 0:
            die("upload_attachment.py failed (see verify-on-fail output above).")
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
