#!/usr/bin/env python3
"""release-safety PreToolUse hook for the Bash and PowerShell tools.

Watches for the release actions whose ORDER matters:

  tags-with-branch   a branch and a tag pushed in one command (`git push origin main --tags`,
                     `git push origin main v1.2.0`, `git push origin main && git push origin v1.2.0`):
                     the release workflow starts while the tests that should gate it are running
  push-all-tags      `git push --tags` / `--follow-tags`: publishes every local tag, stray ones too
  tag-push           `git push <remote> v1.2.0` / `refs/tags/...`: a tag is a promise the release
                     workflow acts on immediately
  release-create     `gh release create`: publishes a release
  remote-tag-delete  `git push --delete <remote> v1.2.0`, `git push <remote> :refs/tags/v1.2.0`,
                     `gh release delete`: withdraws a public ref other people may have pinned

Modes (strictest of the user setting and nothing else; there is no project override):
  advise (default)  hand Claude a reminder as PreToolUse additionalContext. Claude Code
                    delivers it with the tool result, so the command has already run.
  ask               return permissionDecision "ask" so the user confirms before it runs.
  off               do nothing.
Set with the plugin option `guard_mode` (CLAUDE_PLUGIN_OPTION_GUARD_MODE) or the
environment variable RELEASE_SAFETY_MODE, which wins.

Only the command that will run is matched: segments are split on unquoted ; && || | &,
quotes are respected, and only `git` / `gh` programs count. Stdlib only; fails open.

    python release_push_guard.py --self-test
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

MODES = ("off", "advise", "ask")

MSG = {
    "tags-with-branch": "Branch and tag are pushed together, so the release workflow starts before the tests "
                        "that should gate it finish. Push the branch, wait for green, then push the tag.",
    "push-all-tags": "`--tags`/`--follow-tags` publishes every local tag, including stray or stale ones. Push "
                     "the one release tag by name, after the branch is green.",
    "tag-push": "Pushing a tag starts the release workflow immediately. Confirm the branch run is green, the tag "
                "is on that commit, and the tag matches the manifest version and a CHANGELOG entry.",
    "release-create": "`gh release create` publishes a release. Confirm the tag is on a green commit and matches "
                      "the manifest version and CHANGELOG first.",
    "remote-tag-delete": "This withdraws a published tag or release. Downstream users may have pinned it. Cancel "
                         "any in-flight release run first and confirm nothing was published; deleting a tag "
                         "does not stop a running publish.",
}
ORDER = ["remote-tag-delete", "tags-with-branch", "release-create", "push-all-tags", "tag-push"]

_SEPARATORS = ("&&", "||", ";", "|", "&", "\n", "(", ")")
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"command", "builtin", "exec", "sudo", "env", "time", "nohup", "&"}
_GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_TAGLIKE = re.compile(r"^(?:refs/tags/.+|(?:[\w.-]+-)?v?\d+\.\d+(?:\.\d+)?(?:[-+][\w.-]+)?)$")


def split_segments(command: str) -> list[str]:
    segments, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            quote = None if ch == quote else quote
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "#" and (not buf or buf[-1].isspace()):
            j = command.find("\n", i)
            i = len(command) if j < 0 else j
            continue
        if ch == "&" and ((buf and buf[-1] in "<>") or command[i + 1:i + 2] == ">"):
            buf.append(ch)
            i += 1
            continue
        sep = next((s for s in _SEPARATORS if command.startswith(s, i)), None)
        if sep:
            segments.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def tokenize(segment: str) -> list[str]:
    tokens, buf, quote, has = [], [], None, False
    for ch in segment:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote, has = ch, True
        elif ch.isspace():
            if buf or has:
                tokens.append("".join(buf))
            buf, has = [], False
        else:
            buf.append(ch)
    if buf or has:
        tokens.append("".join(buf))
    return tokens


def _prog(token: str) -> str:
    base = re.split(r"[\\/]", token)[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def invocations(command: str) -> list[tuple[str, list[str]]]:
    """(program, args after the program and its global options) for git and gh."""
    found = []
    for segment in split_segments(command):
        tokens = tokenize(segment)
        i = 0
        while i < len(tokens) and (_ASSIGN.match(tokens[i]) or _prog(tokens[i]) in _WRAPPERS):
            i += 1
        if i >= len(tokens):
            continue
        prog = _prog(tokens[i])
        i += 1
        if prog == "git":
            while i < len(tokens) and tokens[i].startswith("-"):
                opt = tokens[i]
                i += 1
                if opt in _GIT_GLOBAL_WITH_VALUE:
                    i += 1
            found.append(("git", tokens[i:]))
        elif prog == "gh":
            found.append(("gh", tokens[i:]))
    return found


def _taglike(ref: str) -> bool:
    return bool(_TAGLIKE.match(ref.lstrip("+")))


def classify(prog: str, args: list[str]) -> tuple[set[str], bool, bool]:
    """Return (rules, pushed_branch, pushed_tag) for one invocation."""
    rules: set[str] = set()
    if prog == "gh":
        if args[:2] == ["release", "create"]:
            rules.add("release-create")
        elif args[:2] == ["release", "delete"]:
            rules.add("remote-tag-delete")
        return rules, False, False
    if not args or args[0].lower() != "push":
        return rules, False, False
    rest = args[1:]
    flags = {a.split("=", 1)[0] for a in rest if a.startswith("-")}
    short = "".join(a[1:] for a in rest if a.startswith("-") and not a.startswith("--"))
    pos = [a for a in rest if not a.startswith("-")]
    refspecs = pos[1:]
    deleting = "--delete" in flags or "d" in short
    branch = tag = False
    for ref in refspecs:
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        src = ref.split(":", 1)[0] if ":" in ref else ref
        if ref.startswith(":") and _taglike(dst):
            rules.add("remote-tag-delete")
        elif deleting and _taglike(dst):
            rules.add("remote-tag-delete")
        elif _taglike(dst) or _taglike(src):
            tag = True
        elif not deleting:
            branch = True
    if not deleting and ("--tags" in flags or "--follow-tags" in flags):
        rules.add("push-all-tags")
        tag = True
    if tag and not rules & {"push-all-tags"}:
        rules.add("tag-push")
    return rules, branch, tag


def detect(command: str) -> list[str]:
    if not command or not re.search(r"\b(git|gh)(\.exe)?\b", command, re.I):
        return []
    rules: set[str] = set()
    any_branch = any_tag = False
    for prog, args in invocations(command):
        r, b, t = classify(prog, args)
        rules |= r
        any_branch |= b
        any_tag |= t
    if any_branch and any_tag:
        rules.add("tags-with-branch")
    return [r for r in ORDER if r in rules]


def _mode(env) -> str:
    for key in ("RELEASE_SAFETY_MODE", "CLAUDE_PLUGIN_OPTION_GUARD_MODE"):
        value = str(env.get(key, "")).strip().lower()
        if value in MODES:
            return value
    return "advise"


def decide(command: str, mode: str) -> tuple[str, str] | None:
    if mode == "off":
        return None
    rules = detect(command)
    if not rules:
        return None
    text = "[release-safety] " + " ".join(MSG[r] for r in rules[:2])
    return ("ask" if mode == "ask" else "context"), text


def main() -> int:
    hooklib.watchdog(5)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    ti = hooklib.tool_input(payload)
    command = ti.get("command") if isinstance(ti.get("command"), str) else ""
    if not command:
        return 0
    result = decide(command, _mode(os.environ))
    if result is None:
        return 0
    kind, text = result
    if kind == "ask":
        hooklib.ask(text + " Approve only if this is intended.")
    else:
        hooklib.context("PreToolUse", text)
    return 0


SELF_TEST = [
    ("git push origin main --tags", ["tags-with-branch", "push-all-tags"]),
    ("git push --tags", ["push-all-tags"]),
    ("git push --follow-tags origin main", ["tags-with-branch", "push-all-tags"]),
    ("git push origin main v1.2.0", ["tags-with-branch", "tag-push"]),
    ("git push origin main && git push origin v1.2.0", ["tags-with-branch", "tag-push"]),
    ("git push origin v1.2.0", ["tag-push"]),
    ("git push origin refs/tags/mypkg-v0.3.0", ["tag-push"]),
    ("git push origin mypkg-v0.3.0", ["tag-push"]),
    ("git -C repo push origin v2.0.0", ["tag-push"]),
    ("gh release create v1.2.0 --notes x", ["release-create"]),
    ("gh release delete v1.2.0", ["remote-tag-delete"]),
    ("git push --delete origin v1.2.0", ["remote-tag-delete"]),
    ("git push origin :refs/tags/v1.2.0", ["remote-tag-delete"]),
    ("git push origin main", []),
    ("git push origin feature/x", []),
    ("git push origin --delete feature/x", []),
    ("git tag v1.2.0", []),
    ("echo 'git push --tags'", []),
    ("git commit -m 'git push origin main --tags'", []),
    ("gh release list", []),
    ("gh pr create --title x", []),
    ("ls", []),
]


def self_test() -> int:
    failed = 0
    for command, expected in SELF_TEST:
        got = detect(command)
        if got != expected:
            failed += 1
            print(f"FAIL {command!r}: expected {expected}, got {got}")
    print(f"{len(SELF_TEST) - failed}/{len(SELF_TEST)} detection cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    hooklib.run(main)
