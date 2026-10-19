#!/usr/bin/env python3
"""SessionStart hook: one release-safety reminder, only where it is relevant.

Prints nothing unless the project shows a release signal: CI workflow files, a deploy
configuration, or a release-tooling config. Even then it speaks at most once per
project; a marker under ${CLAUDE_PLUGIN_DATA} remembers that it did. Output goes out
as SessionStart additionalContext JSON.

Silence it completely with the plugin option `session_hint` = false (reaches the hook
as CLAUDE_PLUGIN_OPTION_SESSION_HINT) or the environment variable
RELEASE_SAFETY_HINT=off. Never blocks; any error exits 0 with no output.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

# (relative path, label). A directory counts when it exists and is not empty.
SIGNALS = [
    (".github/workflows", "GitHub Actions"),
    (".gitlab-ci.yml", "GitLab CI"),
    ("azure-pipelines.yml", "Azure Pipelines"),
    (".azure-pipelines", "Azure Pipelines"),
    (".circleci/config.yml", "CircleCI"),
    ("Jenkinsfile", "Jenkins"),
    ("bitbucket-pipelines.yml", "Bitbucket Pipelines"),
    (".buildkite", "Buildkite"),
    ("railway.json", "Railway"),
    ("railway.toml", "Railway"),
    ("fly.toml", "Fly.io"),
    ("vercel.json", "Vercel"),
    ("netlify.toml", "Netlify"),
    ("render.yaml", "Render"),
    ("app.yaml", "App Engine"),
    ("Procfile", "Procfile"),
    ("serverless.yml", "Serverless"),
    (".goreleaser.yml", "GoReleaser"),
    (".goreleaser.yaml", "GoReleaser"),
    (".releaserc", "semantic-release"),
    (".releaserc.json", "semantic-release"),
    ("release-please-config.json", "release-please"),
]

OFF = ("0", "false", "off", "no")
CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts",
                            "check_release.py").replace(os.sep, "/")


def release_signals(root: str) -> list[str]:
    found = []
    for rel, label in SIGNALS:
        path = os.path.join(root, *rel.split("/"))
        try:
            present = (os.path.isdir(path) and any(os.scandir(path))) or os.path.isfile(path)
        except OSError:
            present = False
        if present and label not in found:
            found.append(label)
    return found


def silenced(env) -> bool:
    for key in ("RELEASE_SAFETY_HINT", "CLAUDE_PLUGIN_OPTION_SESSION_HINT"):
        if str(env.get(key, "")).strip().lower() in OFF:
            return True
    return False


def marker_path(data_dir: str, root: str) -> str:
    digest = hashlib.sha256(os.path.normcase(os.path.abspath(root)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(data_dir, "session-hint", digest)


def already_shown(data_dir: str | None, root: str) -> bool:
    if not data_dir:
        return False
    return os.path.exists(marker_path(data_dir, root))


def remember(data_dir: str | None, root: str) -> None:
    if not data_dir:
        return
    try:
        path = marker_path(data_dir, root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("shown\n")
    except OSError:
        pass


def message(signals: list[str]) -> str:
    return ("[release-safety] This project has release machinery (" + ", ".join(signals[:4]) + "). "
            "Before calling a fix done, prove it in the target environment: run "
            "/release-safety:release-verify. Push the branch and wait for green before tagging; "
            "check a tag against the manifest, changelog and earlier tags with: python \""
            + CHECK_SCRIPT + "\" --tag <tag>")


def main() -> int:
    hooklib.watchdog(4)
    if silenced(os.environ):
        return 0
    payload = hooklib.read_payload() or {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    signals = release_signals(root)
    if not signals:
        return 0
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    if already_shown(data_dir, root):
        return 0
    hooklib.context("SessionStart", message(signals))
    remember(data_dir, root)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
