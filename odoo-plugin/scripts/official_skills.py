#!/usr/bin/env python3
"""Install Odoo's official agent skills into a project - fetched, never vendored.

Odoo S.A. publishes skills for agentic development in the Odoo repository itself
(`skills/` on 20.0 and master): odoo-guidelines, odoo-web-guidelines, odoo-security,
odoo-review. They are written for that branch's framework. This script puts the set
that matches the PROJECT'S Odoo version into <project>/.claude/skills/, straight from
upstream, so the rules stay authoritative, current and version-exact, and this plugin
redistributes nothing (they are LGPL-3, part of Odoo Community).

  (no command)  status, then install or update when the project's version has them
  install       fetch the set for the detected (or --branch) version
  update        re-fetch when upstream has a newer commit
  status        installed set, its commit, whether upstream moved
  remove        delete the directories this script installed (marker-verified)

Projects on Odoo 14-19 get an explanation and nothing is installed: those branches
ship no official skills, and the 20.0 rules are wrong for them (ir.access, removed
t-esc/t-raw, models.Constraint-only constraints). This plugin's own skills cover them.

Standard library only. `--self-test` checks version detection.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = "odoo/odoo"
API = "https://api.github.com/repos/%s" % REPO
RAW = "https://raw.githubusercontent.com/%s" % REPO
MARKER = ".odoo-official.json"
FIRST_MAJOR = 20          # first stable branch that ships skills/
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".claude", "static"}


# --------------------------------------------------------------------------
# Version detection
# --------------------------------------------------------------------------


def _manifest_majors(root: Path, limit: int = 400) -> Counter:
    votes: Counter = Counter()
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if Path(dirpath).relative_to(root).parts.__len__() > 5:
            dirnames[:] = []
        if "__manifest__.py" in filenames:
            seen += 1
            try:
                data = ast.literal_eval(Path(dirpath, "__manifest__.py").read_text(encoding="utf-8"))
                ver = str(data.get("version", ""))
            except Exception:
                continue
            m = re.match(r"^(saas~)?(\d+)\.(\d+)\.\d+", ver)
            if m and int(m.group(2)) >= 8:
                votes[int(m.group(2))] += 1
            if seen >= limit:
                break
    return votes


def _release_major(root: Path):
    for cand in (root / "odoo" / "release.py", root.parent / "odoo" / "release.py"):
        if cand.is_file():
            m = re.search(r"version_info\s*=\s*\(\s*(?:'saas~)?(\d+)", cand.read_text(encoding="utf-8"))
            if m:
                return int(m.group(1))
    return None


def detect(root: Path) -> dict:
    votes = _manifest_majors(root)
    if votes:
        major, count = votes.most_common(1)[0]
        return {"major": major, "how": "module manifests (%d of %d agree)" % (count, sum(votes.values())),
                "votes": dict(votes)}
    rel = _release_major(root)
    if rel:
        return {"major": rel, "how": "odoo/release.py"}
    return {"major": None, "how": "no __manifest__.py or odoo/release.py found"}


def branch_for(major) -> "str | None":
    if major is None:
        return None
    return "%d.0" % major if major >= FIRST_MAJOR else None


# --------------------------------------------------------------------------
# Upstream
# --------------------------------------------------------------------------


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "odoo-plugin-official-skills",
                                               "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com"):
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def upstream(branch: str) -> dict:
    """Latest commit touching skills/ and the file list, or raise with a clear reason."""
    try:
        commits = json.loads(_get("%s/commits?sha=%s&path=skills&per_page=1" % (API, branch)))
        tree = json.loads(_get("%s/git/trees/%s:skills?recursive=1" % (API, branch)))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit("odoo/odoo branch %r has no skills/ directory." % branch)
        if exc.code == 403:
            raise SystemExit("GitHub API rate limit reached. Set GITHUB_TOKEN (read-only) and retry.")
        raise SystemExit("GitHub API error %s for branch %r." % (exc.code, branch))
    except urllib.error.URLError as exc:
        raise SystemExit("cannot reach GitHub: %s" % exc.reason)
    if not commits:
        raise SystemExit("odoo/odoo branch %r has no skills/ history." % branch)
    files = [e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"]
    skills = sorted({p.split("/", 1)[0] for p in files if "/" in p and p.endswith("SKILL.md")})
    return {"commit": commits[0]["sha"], "date": commits[0]["commit"]["committer"]["date"],
            "files": files, "skills": skills}


# --------------------------------------------------------------------------
# Local
# --------------------------------------------------------------------------


def installed(dest: Path) -> dict:
    out = {}
    if dest.is_dir():
        for d in sorted(dest.iterdir()):
            m = d / MARKER
            if m.is_file():
                try:
                    out[d.name] = json.loads(m.read_text(encoding="utf-8"))
                except ValueError:
                    out[d.name] = {"broken_marker": True}
    return out


def do_install(dest: Path, branch: str, force: bool) -> dict:
    up = upstream(branch)
    blocked = [s for s in up["skills"]
               if (dest / s).exists() and not (dest / s / MARKER).is_file()]
    if blocked and not force:
        raise SystemExit(
            "refusing to overwrite %s in %s: those directories were not installed by this "
            "command (no %s). Rename them, or pass --force to replace them."
            % (", ".join(blocked), dest, MARKER))
    staging = dest / ".odoo-official.staging"
    if staging.exists():
        shutil.rmtree(staging)
    for path in up["files"]:
        top = path.split("/", 1)[0]
        if top not in up["skills"]:
            continue  # README.md and anything that is not a skill
        target = staging / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_get("%s/%s/skills/%s" % (RAW, up["commit"], path)))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for skill in up["skills"]:
        marker = {
            "source": "https://github.com/%s/tree/%s/skills/%s" % (REPO, branch, skill),
            "branch": branch,
            "commit": up["commit"],
            "upstream_date": up["date"],
            "fetched_at": now,
            "license": "LGPL-3.0, Odoo S.A. Fetched unmodified from upstream; not part of odoo-plugin.",
            "installed_by": "odoo-plugin /official-skills",
        }
        (staging / skill / MARKER).write_text(json.dumps(marker, indent=2), encoding="utf-8")
    dest.mkdir(parents=True, exist_ok=True)
    for skill in up["skills"]:
        final = dest / skill
        if final.exists():
            shutil.rmtree(final)
        (staging / skill).rename(final)
    shutil.rmtree(staging, ignore_errors=True)
    return {"installed": up["skills"], "branch": branch, "commit": up["commit"][:10],
            "upstream_date": up["date"], "dest": str(dest)}


def do_remove(dest: Path) -> dict:
    gone = []
    for name in installed(dest):
        shutil.rmtree(dest / name)
        gone.append(name)
    return {"removed": gone, "dest": str(dest)}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _explain_not_applicable(det: dict) -> dict:
    major = det.get("major")
    return {
        "applicable": False,
        "detected_version": major,
        "detected_by": det.get("how"),
        "why": ("Odoo's official skills exist only on 20.0 and master. This project is on %s, "
                "where several of their rules are wrong (ir.access replaces ir.model.access + "
                "ir.rule on 20; t-esc/t-raw removed; models.Constraint-only constraints). "
                "Nothing was installed - odoo-plugin's own reviewer and security skills cover "
                "Odoo 14-19." % ("Odoo %s" % major if major else "an undetected version")),
        "override": "pass --branch 20.0 (or master) only if this project really targets it",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Install Odoo's official agent skills (20.0+) into a project.")
    ap.add_argument("command", nargs="?", default="auto",
                    choices=["auto", "install", "update", "status", "remove"])
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--branch", help="odoo/odoo branch to fetch from (default: detected)")
    ap.add_argument("--dest", help="skills directory (default: <project>/.claude/skills)")
    ap.add_argument("--force", action="store_true", help="replace same-named skills this command did not install")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    project = Path(args.project).resolve()
    dest = Path(args.dest).resolve() if args.dest else project / ".claude" / "skills"
    have = installed(dest)

    if args.command == "remove":
        print(json.dumps(do_remove(dest), indent=2))
        return 0

    det = detect(project)
    branch = args.branch or branch_for(det["major"])
    report = {"project": str(project), "detected_version": det["major"], "detected_by": det["how"],
              "branch": branch, "installed": {k: {"commit": v.get("commit", "")[:10],
                                                  "branch": v.get("branch")} for k, v in have.items()}}

    if args.command == "status":
        if branch:
            try:
                up = upstream(branch)
                report["upstream_commit"] = up["commit"][:10]
                report["up_to_date"] = bool(have) and all(
                    v.get("commit") == up["commit"] for v in have.values())
            except SystemExit as exc:
                report["upstream_error"] = str(exc)
        else:
            report.update(_explain_not_applicable(det))
        print(json.dumps(report, indent=2))
        return 0

    if not branch:
        out = _explain_not_applicable(det)
        if have:
            out["warning"] = ("official skills are installed here (%s) but the project is not on "
                              "20.0+; run `remove` so their rules stop applying."
                              % ", ".join(sorted(have)))
        print(json.dumps(out, indent=2))
        return 0

    if args.command in ("auto", "update") and have:
        up = upstream(branch)
        if all(v.get("commit") == up["commit"] and v.get("branch") == branch for v in have.values()):
            report["result"] = "already up to date"
            print(json.dumps(report, indent=2))
            return 0
    if args.command == "update" and not have:
        report["result"] = "nothing installed; run install"
        print(json.dumps(report, indent=2))
        return 0

    result = do_install(dest, branch, args.force)
    result["note"] = ("Restart the Claude Code session so the new skills are discovered. "
                      "odoo-plugin's reviewer and security skills treat these as the rule floor "
                      "on 20.0+. Decide whether .claude/skills/ belongs in version control.")
    print(json.dumps(result, indent=2))
    return 0


def self_test() -> int:
    import tempfile

    fails = 0

    def check(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for i, ver in enumerate(("17.0.1.0.0", "17.0.2.1.0", "16.0.1.0.0")):
            mod = root / ("m%d" % i)
            mod.mkdir()
            (mod / "__manifest__.py").write_text("{'name': 'x', 'version': '%s'}" % ver, encoding="utf-8")
        det = detect(root)
        check("majority manifest version wins", det["major"] == 17)
        check("17 is not applicable", branch_for(17) is None)
    check("20 maps to 20.0", branch_for(20) == "20.0")
    check("21 maps to 21.0", branch_for(21) == "21.0")
    check("undetected is not applicable", branch_for(None) is None)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "odoo").mkdir()
        (root / "odoo" / "release.py").write_text("version_info = (20, 0, 0, FINAL, 0, '')\n", encoding="utf-8")
        check("release.py fallback", detect(root)["major"] == 20)
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        (dest / "odoo-review").mkdir()
        check("unmarked dir is not treated as installed", installed(dest) == {})
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
