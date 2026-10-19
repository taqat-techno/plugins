#!/usr/bin/env python3
"""git-safety PreToolUse hook for the Bash and PowerShell tools.

Looks at the shell command Claude is about to run and, when it contains a risky git
operation, does one of two things depending on the mode:

  advise (default)  hand Claude a short reminder as PreToolUse additionalContext.
                    Claude Code delivers that context together with the tool result,
                    so the command has ALREADY RUN when Claude reads it. Advise mode
                    shapes the next step; it cannot prevent anything.
  ask               for irreversible operations (reset --hard, clean -f, force push,
                    remote branch/tag delete, branch -D, checkout -f, history rewrites,
                    reflog/gc pruning ...) return permissionDecision "ask", so the user
                    confirms before the command runs. Other risky shapes still get the
                    advise-mode reminder. This is the only mode that prevents.
  off               do nothing.

Mode, strictest wins:
  * user setting:   env GIT_SAFETY_MODE, else the plugin option `guard_mode`
                    (exported by Claude Code as CLAUDE_PLUGIN_OPTION_GUARD_MODE),
                    else "advise";
  * project file:   .claude/git-safety.local.json in the repository, keys
                    {"mode": "ask", "protected_branches": ["main", "release/*"]}.
                    A project file can only RAISE strictness (advise -> ask), never
                    lower it, because the model can write files in the repository.

Detection works on the command that will run, not on text inside it: the command is
split into segments on unquoted ; && || | & and newlines, each segment is tokenised
with quotes respected, and only a segment whose program is `git` (or git.exe, or a
path ending in one) is analysed. Leading VAR=value assignments and wrappers such as
`command`, `sudo`, `env`, `exec`, `time`, `nohup` are skipped, `sh -c "..."` /
`bash -c` / `pwsh -Command` bodies are analysed recursively, and git's global options
(-C <path>, -c k=v, --git-dir, --work-tree, --namespace, --no-pager, ...) are skipped
before the subcommand. Flags are matched anywhere after the subcommand.

Cannot see: git aliases, scripts that call git, IDE or MCP git tools, commands built at
runtime (eval, $(...) strings). Stdlib only, fails open on any error.

    python risky_git_advisory.py              # hook mode (reads the payload on stdin)
    python risky_git_advisory.py --self-test  # run the built-in detection table
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

MODES = ("off", "advise", "ask")
PROJECT_FILE = os.path.join(".claude", "git-safety.local.json")

HIGH, MEDIUM, LOW = 3, 2, 1

# --------------------------------------------------------------------------- messages

MSG = {
    "reset-hard": (HIGH, True,
                   "`git reset --hard` discards uncommitted work and it is not in the reflog. On a tree "
                   "a second session or syncer shares, it wipes the peer's work too (skill: shared-checkout-safety)."),
    "clean-force": (HIGH, True,
                    "`git clean -f` deletes untracked files permanently (no reflog). Run `git clean -n` first "
                    "and never run it on a shared checkout (skill: shared-checkout-safety)."),
    "discard-checkout": (HIGH, True,
                         "This checkout/restore/switch discards uncommitted changes. Preserve first (commit, "
                         "`git stash push -m`, or a dated backup outside the repo) (skill: git-safety)."),
    "force-push": (HIGH, True,
                   "A force push (`--force`, `-f`, `+refspec`, `--mirror`) rewrites remote history. Confirm "
                   "nobody else builds on the branch and prefer `--force-with-lease` (skill: git-safety)."),
    "force-with-lease": (MEDIUM, False,
                         "`--force-with-lease` still rewrites remote history; it only refuses when the remote "
                         "moved since your last fetch. Fetch first and confirm the branch is yours (skill: git-safety)."),
    "push-delete": (HIGH, True,
                    "This push deletes a remote branch or tag (`--delete`, `-d`, `:ref`). Anyone who builds on it "
                    "loses it; confirm with the owner first (skill: git-safety)."),
    "branch-force-delete": (HIGH, True,
                            "`git branch -D` deletes a branch even if it is not merged. Its commits survive only "
                            "in the reflog. Check `git log <branch> --not --remotes` first (skill: git-safety)."),
    "tag-delete": (MEDIUM, True,
                   "`git tag -d` deletes a tag. If it was pushed or a release points at it, re-creating it "
                   "elsewhere is a different release (skill: git-safety)."),
    "history-rewrite": (HIGH, True,
                        "This rewrites repository history (filter-branch / filter-repo). Every clone must re-sync; "
                        "take a mirror backup first (skill: git-safety)."),
    "recovery-prune": (HIGH, True,
                       "Expiring the reflog or pruning unreachable objects now removes the only way to recover "
                       "reset, rebased or dropped work (skill: shared-checkout-safety)."),
    "ref-delete": (HIGH, True,
                   "`git update-ref -d` deletes a ref directly, bypassing the safety checks of branch/tag "
                   "deletion (skill: git-safety)."),
    "stash-drop": (MEDIUM, False,
                   "Dropping or clearing a stash discards it; recovering it later needs `git fsck`. Check "
                   "`git stash list` first (skill: shared-checkout-safety)."),
    "stash": (LOW, False,
              "On a shared working tree `stash@{0}` shifts the instant a peer pops, and a stash removes the "
              "change from the tree. Prefer a `git worktree` (skill: shared-checkout-safety)."),
    "add-all": (LOW, False,
                "`git add -A`/`.`/`-u` co-stages files you may not own. Stage explicit paths and verify with "
                "`git diff --cached --name-only` (skill: git-safety)."),
    "rm-cached": (MEDIUM, False,
                  "`git rm --cached` on a TRACKED file deletes it for the whole team when this merges. Flag it "
                  "and document the restore path (skill: git-safety)."),
    "protected-push": (MEDIUM, False,
                       "This pushes directly to a branch the project lists as protected in "
                       ".claude/git-safety.local.json. Confirm a direct push is intended (skill: git-safety)."),
}

# --------------------------------------------------------------------------- parsing

_SEPARATORS = ("&&", "||", ";", "|", "&", "\n", "(", ")", "{", "}")


def split_segments(command: str) -> list[str]:
    """Split on unquoted shell separators. Quotes are kept so the tokenizer sees them.
    `&` that is part of a redirection (2>&1, &>file) is not a separator."""
    command = command.replace("\\\r\n", " ").replace("\\\n", " ")
    segments, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "#" and (not buf or buf[-1].isspace()):
            # shell comment: skip to end of line
            j = command.find("\n", i)
            i = len(command) if j < 0 else j
            continue
        if ch == "&" and ((buf and buf[-1] in "<>") or command[i + 1:i + 2] == ">"):
            buf.append(ch)
            i += 1
            continue
        matched = next((s for s in _SEPARATORS if command.startswith(s, i)), None)
        if matched:
            segments.append("".join(buf))
            buf = []
            i += len(matched)
            continue
        buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def tokenize(segment: str) -> list[str]:
    """Whitespace split with single/double quotes removed. Backslashes are kept literally
    so Windows paths such as C:\\Git\\bin\\git.exe survive."""
    tokens, buf, quote, has = [], [], None, False
    for ch in segment:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
            continue
        if ch in ("'", '"'):
            quote, has = ch, True
            continue
        if ch.isspace():
            if buf or has:
                tokens.append("".join(buf))
            buf, has = [], False
            continue
        buf.append(ch)
    if buf or has:
        tokens.append("".join(buf))
    return tokens


_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"command", "builtin", "exec", "sudo", "doas", "env", "time", "nohup", "nice", "xargs", "&", "."}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd"}
# git global options that take a separate value argument
_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
                      "--super-prefix", "--list-cmds", "--attr-source"}


def _prog(token: str) -> str:
    base = re.split(r"[\\/]", token)[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def git_invocations(command: str, depth: int = 0) -> list[tuple[str, list[str]]]:
    """Return (subcommand, args) for every git invocation that will run."""
    found: list[tuple[str, list[str]]] = []
    if depth > 3:
        return found
    for segment in split_segments(command):
        tokens = tokenize(segment)
        i = 0
        while i < len(tokens) and (_ASSIGN.match(tokens[i]) or _prog(tokens[i]) in _WRAPPERS
                                   or tokens[i].startswith("$env:")):
            i += 1
            # `env -i`, `nice -n 5`, `sudo -u x`: skip their flags too
            while i < len(tokens) and tokens[i].startswith("-") and _prog(tokens[i - 1]) in _WRAPPERS:
                i += 1
        if i >= len(tokens):
            continue
        prog = _prog(tokens[i])
        if prog in _SHELLS:
            rest = tokens[i + 1:]
            for k, tok in enumerate(rest):
                if tok.lower() in ("-c", "-command", "/c", "-lc", "-ic") and k + 1 < len(rest):
                    found.extend(git_invocations(" ".join(rest[k + 1:]) if prog in ("cmd", "pwsh", "powershell")
                                                 else rest[k + 1], depth + 1))
                    break
            continue
        if prog != "git":
            continue
        i += 1
        while i < len(tokens) and tokens[i].startswith("-"):
            opt = tokens[i]
            i += 1
            if opt in _GLOBAL_WITH_VALUE and "=" not in opt:
                i += 1
        if i < len(tokens):
            found.append((tokens[i].lower(), tokens[i + 1:]))
    return found


# --------------------------------------------------------------------------- rules


def _has_short(args: list[str], letter: str) -> bool:
    """True when a short-option cluster such as -fdx contains `letter`."""
    return any(a.startswith("-") and not a.startswith("--") and letter in a[1:] for a in args)


def _positionals(args: list[str]) -> list[str]:
    return [a for a in args if not a.startswith("-")]


def _push_targets(args: list[str], current_branch: str | None) -> list[str]:
    pos = _positionals(args)
    refspecs = pos[1:] if pos else []
    targets = []
    for ref in refspecs:
        ref = ref.lstrip("+")
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        dst = re.sub(r"^refs/(heads|tags)/", "", dst)
        if dst and dst.upper() != "HEAD":
            targets.append(dst)
        elif dst.upper() == "HEAD" and current_branch:
            targets.append(current_branch)
    if not refspecs and current_branch:
        targets.append(current_branch)
    return targets


def classify(sub: str, args: list[str], protected: list[str] | None = None,
             current_branch: str | None = None) -> list[str]:
    """Return the rule ids one git invocation matches."""
    hits: list[str] = []
    long = {a.split("=", 1)[0] for a in args if a.startswith("--")}
    if sub == "reset" and "--hard" in long:
        hits.append("reset-hard")
    elif sub == "clean":
        dry = "--dry-run" in long or _has_short(args, "n")
        if not dry and ("--force" in long or _has_short(args, "f")):
            hits.append("clean-force")
    elif sub == "checkout":
        if "--force" in long or _has_short(args, "f") or "--" in args or "." in args:
            hits.append("discard-checkout")
    elif sub == "switch":
        if "--discard-changes" in long or "--force" in long or _has_short(args, "f"):
            hits.append("discard-checkout")
    elif sub == "restore":
        staged_only = ("--staged" in long or _has_short(args, "S")) and not (
            "--worktree" in long or _has_short(args, "W"))
        if not staged_only and _positionals(args):
            hits.append("discard-checkout")
    elif sub == "push":
        pos = _positionals(args)
        plus = any(p.startswith("+") for p in pos[1:])
        colon_delete = any(p.startswith(":") and len(p) > 1 for p in pos[1:])
        if "--force" in long or _has_short(args, "f") or plus or "--mirror" in long:
            hits.append("force-push")
        elif "--force-with-lease" in long or "--force-if-includes" in long:
            hits.append("force-with-lease")
        if "--delete" in long or _has_short(args, "d") or colon_delete or "--prune" in long:
            hits.append("push-delete")
        if protected:
            targets = _push_targets(args, current_branch)
            if any(fnmatch.fnmatchcase(t, pat) for t in targets for pat in protected):
                hits.append("protected-push")
    elif sub == "branch":
        if _has_short(args, "D") or (("--delete" in long or _has_short(args, "d"))
                                     and ("--force" in long or _has_short(args, "f"))):
            hits.append("branch-force-delete")
    elif sub == "tag":
        if "--delete" in long or _has_short(args, "d"):
            hits.append("tag-delete")
    elif sub in ("filter-branch", "filter-repo"):
        hits.append("history-rewrite")
    elif sub == "reflog":
        if args and args[0] in ("expire", "delete"):
            hits.append("recovery-prune")
    elif sub == "gc":
        if any(a in ("--prune=now", "--prune=all") or a.startswith("--prune=now") for a in args):
            hits.append("recovery-prune")
    elif sub == "prune":
        hits.append("recovery-prune")
    elif sub == "update-ref":
        if "-d" in args or "--delete" in long:
            hits.append("ref-delete")
    elif sub == "stash":
        action = args[0] if args and not args[0].startswith("-") else "push"
        if action in ("drop", "clear"):
            hits.append("stash-drop")
        elif action not in ("list", "show", "branch", "create", "store"):
            hits.append("stash")
    elif sub == "add":
        if ("--all" in long or "--update" in long or _has_short(args, "A") or _has_short(args, "u")
                or any(p in (".", ":/", "*", ":/.") for p in _positionals(args))):
            hits.append("add-all")
    elif sub == "rm":
        if "--cached" in long:
            hits.append("rm-cached")
    return hits


def detect(command: str, protected: list[str] | None = None, current_branch: str | None = None) -> list[str]:
    """All distinct rule ids for a full command line, most severe first."""
    if not command or "git" not in command.lower():
        return []
    seen: list[str] = []
    for sub, args in git_invocations(command):
        for rule in classify(sub, args, protected, current_branch):
            if rule not in seen:
                seen.append(rule)
    return sorted(seen, key=lambda r: -MSG[r][0])


# --------------------------------------------------------------------------- config


def _norm_mode(value) -> str | None:
    value = str(value or "").strip().lower()
    if value in ("advisory", "advice", "warn"):
        value = "advise"
    return value if value in MODES else None


def find_repo_root(cwd: str | None) -> str | None:
    path = os.path.abspath(cwd or os.getcwd())
    for _ in range(40):
        if os.path.exists(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, PROJECT_FILE)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent
    return None


def load_project_config(root: str | None) -> dict:
    if not root:
        return {}
    try:
        with open(os.path.join(root, PROJECT_FILE), encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def current_branch(root: str | None) -> str | None:
    if not root:
        return None
    try:
        with open(os.path.join(root, ".git", "HEAD"), encoding="utf-8") as fh:
            head = fh.read().strip()
    except Exception:
        return None
    return head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else None


def effective_mode(env: dict, project: dict) -> str:
    user = _norm_mode(env.get("GIT_SAFETY_MODE")) or _norm_mode(env.get("CLAUDE_PLUGIN_OPTION_GUARD_MODE")) \
        or "advise"
    proj = _norm_mode(project.get("mode"))
    if proj and MODES.index(proj) > MODES.index(user):
        return proj
    return user


def protected_branches(project: dict) -> list[str]:
    value = project.get("protected_branches")
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v.strip()]


# --------------------------------------------------------------------------- hook


def decide(command: str, mode: str, protected: list[str] | None = None,
           branch: str | None = None) -> tuple[str, str] | None:
    """Return ("ask"|"context", text) or None."""
    if mode == "off":
        return None
    rules = detect(command, protected, branch)
    if not rules:
        return None
    lines = [MSG[r][2] for r in rules[:3]]
    text = "[git-safety] " + " ".join(lines)
    irreversible = [r for r in rules if MSG[r][1]]
    if mode == "ask" and irreversible:
        return "ask", text
    return "context", text


def main() -> int:
    hooklib.watchdog(5)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    ti = hooklib.tool_input(payload)
    command = next((ti[k] for k in ("command", "script", "cmd") if isinstance(ti.get(k), str)), "")
    if not command or "git" not in command.lower():
        return 0
    root = find_repo_root(payload.get("cwd") if isinstance(payload.get("cwd"), str) else None)
    project = load_project_config(root)
    mode = effective_mode(os.environ, project)
    result = decide(command, mode, protected_branches(project), current_branch(root))
    if result is None:
        return 0
    kind, text = result
    if kind == "ask":
        hooklib.ask(text + " Approve only if this is intended.")
    else:
        hooklib.context("PreToolUse", text)
    return 0


# --------------------------------------------------------------------------- self-test

SELF_TEST = [
    # (command, exact rule ids most severe first; [] means no match)
    ("git reset --hard", ["reset-hard"]),
    ("git -C repo reset --hard", ["reset-hard"]),
    ("git -c core.pager=cat reset --hard HEAD~1", ["reset-hard"]),
    ("git --git-dir=.git --work-tree=. clean -fdx", ["clean-force"]),
    ("git --no-pager clean -xdf", ["clean-force"]),
    ("git clean -nd", []),
    ("git clean --dry-run -fd", []),
    ("git push origin main --force", ["force-push"]),
    ("git push -u origin main -f", ["force-push"]),
    ("git push origin +main", ["force-push"]),
    ("git push --force-with-lease origin feat", ["force-with-lease"]),
    ("git push origin --delete main", ["push-delete"]),
    ("git push origin :release", ["push-delete"]),
    ("git push origin main", []),
    ("git rm -r --cached .", ["rm-cached"]),
    ("git add src/ .", ["add-all"]),
    ("git add -A", ["add-all"]),
    ("git add src/app.py", []),
    ("git.exe reset --hard", ["reset-hard"]),
    ("& 'C:\\Program Files\\Git\\bin\\git.exe' reset --hard", ["reset-hard"]),
    ("git branch -D feature", ["branch-force-delete"]),
    ("git branch -d feature", []),
    ("git branch --delete --force feature", ["branch-force-delete"]),
    ("git checkout -f main", ["discard-checkout"]),
    ("git checkout -- .", ["discard-checkout"]),
    ("git checkout main", []),
    ("git switch --discard-changes main", ["discard-checkout"]),
    ("git restore --staged file.py", []),
    ("git restore file.py", ["discard-checkout"]),
    ("git tag -d v1.0.0", ["tag-delete"]),
    ("git reflog expire --expire=now --all", ["recovery-prune"]),
    ("git gc --prune=now", ["recovery-prune"]),
    ("git gc", []),
    ("git filter-branch --tree-filter 'rm x' HEAD", ["history-rewrite"]),
    ("git update-ref -d refs/heads/x", ["ref-delete"]),
    ("git stash list", []),
    ("git stash show -p", []),
    ("git stash", ["stash"]),
    ("git stash pop", ["stash"]),
    ("git stash drop", ["stash-drop"]),
    ("GIT_DIR=x git reset --hard", ["reset-hard"]),
    ("command git reset --hard", ["reset-hard"]),
    ("git  reset  --hard; echo ok", ["reset-hard"]),
    ("cd repo && git reset --hard", ["reset-hard"]),
    ("git add -A && git push --force", ["force-push", "add-all"]),
    ("git status 2>&1 | grep reset", []),
    ("echo 'git reset --hard'", []),
    ("git commit -m \"git reset --hard was wrong\"", []),
    ("grep -n 'push --force' notes.md", []),
    ("git log --oneline # git reset --hard", []),
    ("bash -c \"git reset --hard\"", ["reset-hard"]),
    ("(cd sub && git clean -fd)", ["clean-force"]),
    ("git status", []),
    ("git diff --cached --name-only", []),
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
