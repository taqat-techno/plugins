#!/usr/bin/env python3
"""release-safety PreToolUse hook for the Bash and PowerShell tools.

Watches for the release actions whose ORDER matters:

  remote-tag-delete  `git push --delete <remote> v1.2.0`, `git push <remote> :refs/tags/v1.2.0`,
                     `gh release delete`: withdraws a public ref other people may have pinned
  push-mirror        `git push --mirror`: publishes every local ref, tags included, and deletes
                     remote refs that do not exist locally
  tag-move           a tag pushed with `-f`/`--force`/`+ref` (`git push -f origin v1`,
                     `git push origin +latest`): repoints a published tag consumers pin
  tags-with-branch   a branch and a tag pushed in one command (`git push origin main --tags`,
                     `git push origin main v1.2.0`, `git push origin main && git push origin v1.2.0`):
                     the release workflow starts while the tests that should gate it are running
  release-create     `gh release create` (also `gh -R owner/repo release create`): publishes a release
  push-all-tags      `git push --tags` / `--follow-tags`: publishes every local tag, stray ones too
  tag-push           `git push <remote> v1.2.0` / `refs/tags/...` / `tag <name>` / `"$TAG"`: a tag is
                     a promise the release workflow acts on immediately

What counts as a tag ref (offline; the hook never runs git):
  * `refs/tags/<x>`, or `tag <x>` (git push's own shorthand for refs/tags/<x>);
  * a version-shaped name: `vN`, `vN.N[.N]`, `N.N.N` (pre-release / build suffix allowed),
    `<name>-vN.N[.N]`, `<name>@N.N[.N]`. A bare two-part number such as `17.0` and a
    branch-like `release-1.2` are NOT tags: maintenance branches are named that way;
  * `latest` / `stable`, but only when force-pushed (moving tags; as plain pushes they are
    usually branches);
  * a shell expansion (`$TAG`, `"${VERSION}"`, `"v$VERSION"`, `$(...)`) when its variable
    name says tag/version/release, or the same command creates or names a tag
    (`git tag ...`, `refs/tags/`, `gh release`). An expansion named like a branch
    (`$BRANCH`, `$HEAD`) is a branch.
  `refs/heads/<x>`, and a name equal to the checked-out branch (read from `.git/HEAD`
  under the hook's cwd), are always branches.

Modes (strictest of the user setting and nothing else; there is no project override):
  advise (default)  hand Claude a reminder as PreToolUse additionalContext. Claude Code
                    delivers it with the tool result, so the command has already run.
  ask               return permissionDecision "ask" so the user confirms before it runs.
  off               do nothing.
Set with the plugin option `guard_mode` (CLAUDE_PLUGIN_OPTION_GUARD_MODE) or the
environment variable RELEASE_SAFETY_MODE, which wins.

Only the command that will run is matched: segments are split on unquoted ; && || | &
and newlines, quotes are respected, `${...}` / `$(...)` are opaque words (their bodies are
analysed too), `sh -c` / `bash -c` / `pwsh -Command` bodies are analysed, and only `git` /
`gh` programs count. Stdlib only; fails open.

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
    "push-mirror": "`git push --mirror` publishes every local ref, all tags included, and deletes remote refs "
                   "that do not exist locally. Push the branch and the one release tag by name instead.",
    "tag-move": "Force-pushing a tag moves a published ref: everything pinned to it (for example "
                "`uses: owner/action@v1`) picks up the new commit at once. Confirm the new commit is the "
                "released, green one.",
    "tag-push": "Pushing a tag starts the release workflow immediately. Confirm the branch run is green, the tag "
                "is on that commit, and the tag matches the manifest version and a CHANGELOG entry.",
    "release-create": "`gh release create` publishes a release. Confirm the tag is on a green commit and matches "
                      "the manifest version and CHANGELOG first.",
    "remote-tag-delete": "This withdraws a published tag or release. Downstream users may have pinned it. Cancel "
                         "any in-flight release run first and confirm nothing was published; deleting a tag "
                         "does not stop a running publish.",
}
ORDER = ["remote-tag-delete", "push-mirror", "tag-move", "tags-with-branch", "release-create",
         "push-all-tags", "tag-push"]

# --------------------------------------------------------------------------- parsing

_SEPARATORS = ("&&", "||", ";", "|", "&", "\n", "(", ")", "{", "}")
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"command", "builtin", "exec", "sudo", "doas", "env", "time", "nohup", "nice", "xargs", "&", "."}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd"}
_GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                          "--config-env", "--super-prefix", "--attr-source"}
_GH_GLOBAL_WITH_VALUE = {"-R", "--repo", "--hostname"}
_EXPANSION_TOKEN = re.compile(r"^\$(?:[A-Za-z_][A-Za-z0-9_]*|[@*#?0-9]|\{.*\}|\(.*\))$", re.S)


def _expansion_end(s: str, i: int) -> int:
    """If s[i:] starts a `${...}` or `$(...)` expansion, return the index just past it
    (len(s) when unterminated); otherwise -1. Brackets inside it are not separators."""
    if s[i] != "$" or s[i + 1:i + 2] not in ("{", "("):
        return -1
    open_ch = s[i + 1]
    close_ch = "}" if open_ch == "{" else ")"
    depth, j, quote = 1, i + 2, None
    while j < len(s):
        ch = s[j]
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "$" and s[j + 1:j + 2] in ("{", "("):
            j = _expansion_end(s, j)
            continue
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return len(s)


def _substitutions(segment: str) -> list[str]:
    """Bodies of `$(...)` command substitutions outside single quotes; they run too."""
    bodies, quote, i = [], None, 0
    while i < len(segment):
        ch = segment[i]
        if quote == "'":
            if ch == "'":
                quote = None
        elif ch == "$" and segment[i + 1:i + 2] == "(":
            end = _expansion_end(segment, i)
            bodies.append(segment[i + 2:end - 1] if segment[end - 1] == ")" else segment[i + 2:end])
            i = end
            continue
        elif ch == '"':
            quote = None if quote == '"' else '"'
        elif ch == "'" and quote is None:
            quote = "'"
        i += 1
    return bodies


def split_segments(command: str) -> list[str]:
    command = command.replace("\\\r\n", " ").replace("\\\n", " ")
    segments, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote != "'":
            end = _expansion_end(command, i)
            if end > 0:
                buf.append(command[i:end])
                i = end
                continue
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
    i = 0
    while i < len(segment):
        ch = segment[i]
        if quote != "'":
            end = _expansion_end(segment, i)
            if end > 0:
                buf.append(segment[i:end])
                i = end
                continue
        i += 1
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


def _is_expansion(token: str) -> bool:
    return bool(_EXPANSION_TOKEN.match(token))


def _prog(token: str) -> str:
    base = re.split(r"[\\/]", token)[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def invocations(command: str, depth: int = 0) -> list[tuple[str, list[str]]]:
    """(program, args after the program and its global options) for git and gh."""
    found: list[tuple[str, list[str]]] = []
    if depth > 3:
        return found
    for segment in split_segments(command):
        for body in _substitutions(segment):
            found.extend(invocations(body, depth + 1))
        tokens = tokenize(segment)
        i = 0
        while i < len(tokens) and (_ASSIGN.match(tokens[i]) or _prog(tokens[i]) in _WRAPPERS
                                   or tokens[i].startswith("$env:") or _is_expansion(tokens[i])):
            i += 1
            while i < len(tokens) and tokens[i].startswith("-") and _prog(tokens[i - 1]) in _WRAPPERS:
                i += 1
        if i >= len(tokens):
            continue
        prog = _prog(tokens[i])
        i += 1
        if prog in _SHELLS:
            rest = tokens[i:]
            for k, tok in enumerate(rest):
                if tok.lower() in ("-c", "-command", "/c", "-lc", "-ic") and k + 1 < len(rest):
                    body = " ".join(rest[k + 1:]) if prog in ("cmd", "pwsh", "powershell") else rest[k + 1]
                    found.extend(invocations(body, depth + 1))
                    break
        elif prog == "git":
            while i < len(tokens) and (tokens[i].startswith("-") or _is_expansion(tokens[i])):
                opt = tokens[i]
                i += 1
                if opt in _GIT_GLOBAL_WITH_VALUE:
                    i += 1
            found.append(("git", tokens[i:]))
        elif prog == "gh":
            while i < len(tokens) and tokens[i].startswith("-"):
                opt = tokens[i]
                i += 1
                if opt in _GH_GLOBAL_WITH_VALUE:
                    i += 1
            found.append(("gh", tokens[i:]))
    return found


# --------------------------------------------------------------------------- tag shape

_VERSION_TAG = re.compile(
    r"^(?:"
    r"v\d+(?:\.\d+){0,2}"                    # v1, v1.2, v1.2.3
    r"|\d+\.\d+\.\d+"                         # 1.2.3 (a bare 17.0 is a maintenance branch)
    r"|[\w.-]+-v\d+(?:\.\d+){1,2}"            # mypkg-v0.3.0
    r"|[\w.@/-]+@v?\d+(?:\.\d+){1,2}"         # mypkg@1.2.3, @scope/pkg@1.2.3
    r")(?:[-+][\w.-]+)?$")
_MOVING_TAGS = {"latest", "stable"}
# hints read from variable names, and from the body of a `$(...)` ref
_TAGGY_HINT = re.compile(r"TAG|VERSION|(?<![A-Za-z])VER(?![A-Za-z])|RELEASE|DESCRIBE", re.I)
_BRANCHY_HINT = re.compile(r"BRANCH|(?<![A-Za-z])HEAD(?![A-Za-z])", re.I)
_VAR_NAME = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")


def _split_refspec(ref: str) -> tuple[str, str]:
    """(src, dst) of a refspec; a ':' inside `${X:-y}` does not split it."""
    i = 0
    while i < len(ref):
        end = _expansion_end(ref, i)
        if end > 0:
            i = end
            continue
        if ref[i] == ":":
            return ref[:i], ref[i + 1:]
        i += 1
    return ref, ref


def _ref_kind(ref: str, ctx: dict, forced: bool) -> str:
    """'tag' or 'branch' for one push destination (or source)."""
    if ref.startswith("refs/tags/"):
        return "tag"
    if ref.startswith("refs/heads/"):
        return "branch"
    if ctx.get("current_branch") and ref == ctx["current_branch"]:
        return "branch"
    if "$" in ref:
        hint = " ".join(_VAR_NAME.findall(ref))
        if "$(" in ref:
            hint += " " + ref
        taggy, branchy = bool(_TAGGY_HINT.search(hint)), bool(_BRANCHY_HINT.search(hint))
        if branchy and not taggy:
            return "branch"
        if taggy or ctx.get("mentions_tag") or re.match(r"^v\$", ref):   # "v$VERSION"
            return "tag"
        return "branch"
    if _VERSION_TAG.match(ref):
        return "tag"
    if forced and ref.lower() in _MOVING_TAGS:
        return "tag"
    return "branch"


def _mentions_tag(invs: list[tuple[str, list[str]]], command: str) -> bool:
    """The command creates or names a tag, so an unresolved `$X` ref is probably a tag."""
    if "refs/tags/" in command:
        return True
    for prog, args in invs:
        if prog == "gh" and args[:1] == ["release"]:
            return True
        if prog == "git" and args[:1] == ["tag"]:
            rest = args[1:]
            if not any(a in ("-l", "--list", "-d", "--delete", "-v", "--verify") or a.startswith("--contains")
                       for a in rest) and any(not a.startswith("-") for a in rest):
                return True
    return False


def classify(prog: str, args: list[str], ctx: dict | None = None) -> tuple[set[str], bool, bool]:
    """Return (rules, pushed_branch, pushed_tag) for one invocation."""
    ctx = ctx or {}
    rules: set[str] = set()
    if prog == "gh":
        pos = [a for a in args if not a.startswith("-")]
        if pos[:2] == ["release", "create"]:
            rules.add("release-create")
        elif pos[:2] == ["release", "delete"]:
            rules.add("remote-tag-delete")
        return rules, False, False
    if not args or args[0].lower() != "push":
        return rules, False, False
    rest = args[1:]
    flags = {a.split("=", 1)[0] for a in rest if a.startswith("--")}
    short = "".join(a[1:] for a in rest if a.startswith("-") and not a.startswith("--"))
    pos = [a for a in rest if not a.startswith("-")]
    refspecs = pos[1:]
    # `git push origin tag v1.2.0` is git's shorthand for refs/tags/v1.2.0
    expanded: list[str] = []
    k = 0
    while k < len(refspecs):
        if refspecs[k] == "tag" and k + 1 < len(refspecs):
            expanded.append("refs/tags/" + refspecs[k + 1])
            k += 2
            continue
        expanded.append(refspecs[k])
        k += 1
    deleting = "--delete" in flags or "d" in short
    forced_all = "--force" in flags or "f" in short
    branch = tag = False
    if "--mirror" in flags:
        rules.add("push-mirror")
        tag = True
    for ref in expanded:
        forced = forced_all or ref.startswith("+")
        ref = ref.lstrip("+")
        src, dst = _split_refspec(ref)
        dst_kind = _ref_kind(dst, ctx, forced) if dst else "branch"
        src_kind = _ref_kind(src, ctx, forced) if src else "branch"
        if ref.startswith(":") or deleting:
            if dst_kind == "tag":
                rules.add("remote-tag-delete")
        elif dst_kind == "tag" or src_kind == "tag":
            tag = True
            if forced:
                rules.add("tag-move")
        else:
            branch = True
    if not deleting and ("--tags" in flags or "--follow-tags" in flags):
        rules.add("push-all-tags")
        tag = True
    if tag and not rules & {"push-all-tags", "push-mirror", "tag-move"}:
        rules.add("tag-push")
    return rules, branch, tag


def detect(command: str, current_branch: str | None = None) -> list[str]:
    if not command or not re.search(r"\b(git|gh)(\.exe)?\b", command, re.I):
        return []
    invs = invocations(command)
    ctx = {"current_branch": current_branch, "mentions_tag": _mentions_tag(invs, command)}
    rules: set[str] = set()
    any_branch = any_tag = False
    for prog, args in invs:
        r, b, t = classify(prog, args, ctx)
        rules |= r
        any_branch |= b
        any_tag |= t
    if any_branch and any_tag:
        rules.add("tags-with-branch")
    return [r for r in ORDER if r in rules]


# --------------------------------------------------------------------------- hook


def current_branch(cwd: str | None) -> str | None:
    """Checked-out branch from .git/HEAD above cwd (no git process); None when unknown."""
    path = os.path.abspath(cwd or os.getcwd())
    for _ in range(40):
        head = os.path.join(path, ".git", "HEAD")
        if os.path.isfile(head):
            try:
                with open(head, encoding="utf-8") as fh:
                    text = fh.read().strip()
            except Exception:
                return None
            return text[len("ref: refs/heads/"):] if text.startswith("ref: refs/heads/") else None
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent
    return None


def _mode(env) -> str:
    for key in ("RELEASE_SAFETY_MODE", "CLAUDE_PLUGIN_OPTION_GUARD_MODE"):
        value = str(env.get(key, "")).strip().lower()
        if value in MODES:
            return value
    return "advise"


def decide(command: str, mode: str, branch: str | None = None) -> tuple[str, str] | None:
    if mode == "off":
        return None
    rules = detect(command, branch)
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
    mode = _mode(os.environ)
    if mode == "off":
        return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    result = decide(command, mode, current_branch(cwd))
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
    # RA-REL-01: variable tags, major/moving tags, wrappers, gh global flags, --mirror
    ("git tag v1.2.0 && git push origin \"$TAG\"", ["tag-push"]),
    ("git tag \"$NEXT\" && git push origin \"$NEXT\"", ["tag-push"]),
    ("git push origin $TAG", ["tag-push"]),
    ("git push origin \"${RELEASE_VERSION}\"", ["tag-push"]),
    ("git push origin \"v$VERSION\"", ["tag-push"]),
    ("git push origin main \"$TAG\"", ["tags-with-branch", "tag-push"]),
    ("git push --delete origin \"$TAG\"", ["remote-tag-delete"]),
    ("git push origin v1", ["tag-push"]),
    ("git push origin v1 --force", ["tag-move"]),
    ("git push -f origin v1", ["tag-move"]),
    ("git push origin +v1", ["tag-move"]),
    ("git push origin latest --force", ["tag-move"]),
    ("git push origin +latest", ["tag-move"]),
    ("git push --mirror origin", ["push-mirror"]),
    ("bash -c \"git push --tags\"", ["push-all-tags"]),
    ("sh -c 'git push origin v1.2.0'", ["tag-push"]),
    ("gh -R owner/repo release create v1.0.0", ["release-create"]),
    ("gh --repo owner/repo release create v1.0.0", ["release-create"]),
    ("gh --repo=owner/repo release delete v1.0.0", ["remote-tag-delete"]),
    ("gh release create v1.0.0 -R owner/repo", ["release-create"]),
    ("git push origin tag v1.2.0", ["tag-push"]),
    ("git push origin \"$(git describe --tags --abbrev=0)\"", ["tag-push"]),
    ("git push origin mypkg@1.2.3", ["tag-push"]),
    # RA-REL-02: branch-shaped refs are not tags
    ("git push origin release-1.2", []),
    ("git push origin release/1.2", []),
    ("git push origin 17.0", []),
    ("git push origin latest", []),
    ("git push origin refs/heads/v1.2.0", []),
    ("git push origin \"$BRANCH\"", []),
    ("git push origin $(git branch --show-current)", []),
    ("git push origin ${BRANCH} --force", []),
    ("git tag -l && git push origin \"$X\"", []),
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
