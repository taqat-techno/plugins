#!/usr/bin/env python3
"""Read-only tag / version correctness check for a release.

Answers three questions before (or after) a tag is pushed:

  1. tag-matches-manifest  the tag's version equals the version in the manifest
                           (package.json, pyproject.toml, Cargo.toml,
                           .claude-plugin/plugin.json, VERSION, or --manifest PATH)
  2. changelog-entry       CHANGELOG.md has a heading for that version
                           ("## [1.2.3]", "## 1.2.3", "## v1.2.3 - date", ...)
  3. semver-monotonic      the version is greater than every existing tag with the
                           same prefix (a re-tag or a downgrade fails)

It never writes, never fetches and never pushes. The only external command is a
read-only `git tag --list` (and `git describe --tags --exact-match` when no tag is
given). Stdlib only.

    python check_release.py                       # tag on HEAD, files in the cwd
    python check_release.py --tag v1.4.0          # a tag you are about to create
    python check_release.py --tag mypkg-v0.3.0 --root packages/mypkg
    python check_release.py --version 1.4.0       # no tag yet; check manifest + changelog
    python check_release.py --json                # machine-readable result

Exit codes: 0 all checks pass, 1 a check failed, 2 the inputs could not be determined.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

SEMVER = re.compile(r"(?P<ver>(?P<maj>0|[1-9]\d*)\.(?P<min>0|[1-9]\d*)\.(?P<pat>0|[1-9]\d*)"
                    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?)$")


# --------------------------------------------------------------------------- versions


def split_tag(tag: str) -> tuple[str, str] | None:
    """'mypkg-v1.2.3' -> ('mypkg-v', '1.2.3'); 'v1.2.3' -> ('v', '1.2.3')."""
    m = re.search(r"v?" + SEMVER.pattern, tag)
    if not m:
        return None
    start = m.start("ver")
    return tag[:start], m.group("ver")


def _series(prefix: str) -> str:
    """'mypkg-v' and 'mypkg-' are one tag series; so are 'v' and ''."""
    return prefix[:-1] if prefix.endswith("v") else prefix


def version_key(version: str):
    m = SEMVER.match(version)
    if not m:
        return None
    pre = m.group("pre")
    pre_key = () if pre is None else tuple((0, int(p)) if p.isdigit() else (1, p) for p in pre.split("."))
    # a release sorts after all of its pre-releases
    return (int(m.group("maj")), int(m.group("min")), int(m.group("pat")), pre is None, pre_key)


# --------------------------------------------------------------------------- manifests


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _toml_version(text: str, tables: tuple[str, ...]) -> str | None:
    table = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            table = s.strip("[] ")
            continue
        if table in tables:
            m = re.match(r'version\s*=\s*["\']([^"\']+)["\']', s)
            if m:
                return m.group(1)
    return None


def manifest_version(root: str, manifest: str | None = None) -> tuple[str | None, str | None]:
    """Return (version, manifest path) from the first manifest that declares a version."""
    candidates = [manifest] if manifest else [
        "package.json", "pyproject.toml", "Cargo.toml", os.path.join(".claude-plugin", "plugin.json"),
        "VERSION",
    ]
    for rel in candidates:
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        text = _read(path)
        if text is None:
            continue
        name = os.path.basename(path)
        version = None
        if name.endswith(".json"):
            try:
                data = json.loads(text)
                version = data.get("version") if isinstance(data, dict) else None
            except ValueError:
                version = None
        elif name == "pyproject.toml":
            version = _toml_version(text, ("project", "tool.poetry"))
        elif name == "Cargo.toml":
            version = _toml_version(text, ("package", "workspace.package"))
        else:
            version = text.strip().splitlines()[0].strip() if text.strip() else None
        if isinstance(version, str) and version.strip():
            return version.strip().lstrip("v"), os.path.relpath(path, root)
    return None, None


def changelog_has(root: str, version: str, changelog: str | None = None) -> tuple[bool | None, str | None]:
    names = [changelog] if changelog else ["CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"]
    for rel in names:
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        text = _read(path)
        if text is None:
            continue
        pattern = re.compile(r"^#{1,4}\s*\[?v?" + re.escape(version) + r"\]?(?:\s|$|\(|-)", re.M)
        return bool(pattern.search(text)), os.path.relpath(path, root)
    return None, None


# --------------------------------------------------------------------------- git (read-only)


def _git(args: list[str], cwd: str) -> str | None:
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def head_tag(root: str) -> str | None:
    out = _git(["describe", "--tags", "--exact-match", "HEAD"], root)
    return out.strip() if out and out.strip() else None


def existing_tags(root: str) -> list[str]:
    out = _git(["tag", "--list"], root)
    return [t.strip() for t in out.splitlines() if t.strip()] if out else []


# --------------------------------------------------------------------------- checks


def check(root: str, tag: str | None, version: str | None, manifest: str | None,
          changelog: str | None, tags: list[str] | None) -> dict:
    result: dict = {"tag": tag, "version": None, "checks": [], "ok": False}
    prefix = ""
    if tag:
        parts = split_tag(tag)
        if not parts:
            result["error"] = f"tag {tag!r} does not contain a semantic version (X.Y.Z)"
            return result
        prefix, version_from_tag = parts
        if version and version != version_from_tag:
            result["error"] = f"--version {version} disagrees with tag {tag}"
            return result
        version = version_from_tag
    mver, mpath = manifest_version(root, manifest)
    if not version:
        version = mver
    if not version:
        result["error"] = "no tag on HEAD, no --tag/--version given and no manifest version found"
        return result
    if not SEMVER.match(version):
        result["error"] = f"version {version!r} is not a semantic version"
        return result
    result["version"] = version

    def add(name, status, detail):
        result["checks"].append({"name": name, "status": status, "detail": detail})

    if mver is None:
        add("tag-matches-manifest", "skip", "no manifest with a version field found")
    elif mver == version:
        add("tag-matches-manifest", "pass", f"{mpath} declares {mver}")
    else:
        add("tag-matches-manifest", "fail", f"{mpath} declares {mver}, release is {version}")

    has, cpath = changelog_has(root, version, changelog)
    if has is None:
        add("changelog-entry", "skip", "no CHANGELOG file found")
    elif has:
        add("changelog-entry", "pass", f"{cpath} has a heading for {version}")
    else:
        add("changelog-entry", "fail", f"{cpath} has no heading for {version}")

    all_tags = existing_tags(root) if tags is None else tags
    same = []
    for t in all_tags:
        if t == tag:
            continue
        parts = split_tag(t)
        if parts and _series(parts[0]) == _series(prefix) and version_key(parts[1]) is not None:
            same.append(parts[1])
    if not same:
        add("semver-monotonic", "pass", f"no earlier tags with prefix {prefix!r}")
    else:
        latest = max(same, key=version_key)
        if version_key(version) > version_key(latest):
            add("semver-monotonic", "pass", f"{version} > latest {prefix}{latest}")
        elif version == latest:
            add("semver-monotonic", "fail", f"{prefix}{version} already exists; a re-tag is a different build")
        else:
            add("semver-monotonic", "fail", f"{version} is not greater than latest {prefix}{latest}")

    result["ok"] = all(c["status"] != "fail" for c in result["checks"])
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only tag/version correctness check.")
    ap.add_argument("--root", default=".", help="directory holding the manifest and changelog")
    ap.add_argument("--tag", help="tag to check (default: the tag on HEAD)")
    ap.add_argument("--version", help="version to check when there is no tag yet")
    ap.add_argument("--manifest", help="manifest file to read the version from")
    ap.add_argument("--changelog", help="changelog file to look in")
    ap.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    tag = args.tag or (None if args.version else head_tag(root))
    result = check(root, tag, args.version, args.manifest, args.changelog, None)
    if args.json:
        print(json.dumps(result, indent=2))
    elif "error" in result:
        print(f"release check: cannot run: {result['error']}")
    else:
        label = result["tag"] or result["version"]
        print(f"release check for {label}:")
        for c in result["checks"]:
            print(f"  {c['status'].upper():4}  {c['name']}: {c['detail']}")
        print("  result: " + ("PASS" if result["ok"] else "FAIL"))
    if "error" in result:
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
