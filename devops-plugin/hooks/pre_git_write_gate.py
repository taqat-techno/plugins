#!/usr/bin/env python3
"""
devops-plugin PreToolUse/Bash hook — conservative remote git-write gate.

Enforces the deterministic, false-positive-averse subset of
rules/git-remote-write-gate.md (permission-first + identity-correctness).
It does NOT re-implement the full rule; it only catches the two signals that
can be detected reliably from a shell command, and otherwise stays out of the
way. The LLM + the rule own everything nuanced.

Behavior on the Bash tool's `command`:

  HARD-BLOCK  (exit 2, one-line reason on stderr) — only on a deterministic danger:
    1. A FORCE push (--force / -f / --force-with-lease) targeting a protected
       branch (main, master, production, prod, staging, release).
    2. A clear IDENTITY/OWNER mismatch on a remote WRITE op: the target remote
       owner (parsed from the command's remote URL, or from `git remote get-url`)
       does not match the active `gh` account (from `gh auth status`).

  ADVISORY-WARN (exit 0, one short line on stderr) — never blocks:
    - A plain (non-force) push to a protected branch.
    - A `gh pr create` / `gh api`-style write.
    Reminds to confirm permission + identity per rules/git-remote-write-gate.md.

  IGNORE (exit 0, silent) — everything else: reads, non-protected branches,
    non-git commands, anything ambiguous. When uncertain, ALLOW.

Self-contained, stdlib-only, fast (gh/git probes only run when a write is seen,
each capped by a short timeout), and never prints secrets/tokens.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master", "production", "prod", "staging", "release"}
FORCE_FLAGS = ("--force", "--force-with-lease", "-f")
PROBE_TIMEOUT = 4  # seconds — cap each external probe so the hook stays fast


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # unparseable payload -> allow (best-effort hook)

    # Only the Bash tool carries a shell command.
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    if tool_name and tool_name != "Bash":
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    # Cheap pre-filter: if it touches neither git nor gh, there is nothing to gate.
    lowered = command.lower()
    if "git " not in lowered and "git\t" not in lowered and "gh " not in lowered:
        return 0

    # ---- gh pr create / gh api write -> advisory only -------------------------
    if _is_gh_write(command):
        _warn(
            "[devops] gh write (pr/api) detected. Per rules/git-remote-write-gate.md: "
            "confirm explicit permission and that the active identity may write to the "
            "target repo before proceeding."
        )
        return 0

    # ---- git push handling ----------------------------------------------------
    if not _is_git_push(command):
        return 0  # not a push and not a gh write -> nothing deterministic to gate

    is_force = _is_force_push(command)
    protected = _push_targets_protected_branch(command)

    # HARD-BLOCK 1: force push to a protected branch.
    if is_force and protected:
        _deny(
            f"[devops] BLOCKED: force push to protected branch '{protected}'. "
            "Force-pushing a protected branch can destroy shared history. "
            "Push without --force, or target a feature branch. "
            "See rules/git-remote-write-gate.md."
        )
        return 2

    # HARD-BLOCK 2: clear owner/identity mismatch on this write op.
    #
    # A name difference alone is NOT a clear mismatch: a gh login is a personal
    # account, while a repo owner is frequently an ORG the user belongs to
    # (login 'alice' pushing to 'acme/app' is normal and authorized). Blocking
    # on names alone would fire on every org push -> unacceptable false positive.
    #
    # So we only treat it as a CLEAR mismatch when BOTH:
    #   (a) names differ, AND
    #   (b) an access probe proves the active account CANNOT see the target repo.
    # If access is confirmed, or the probe is inconclusive (offline, no repo,
    # gh missing, timeout), we do NOT block — when uncertain, allow.
    owner, repo = _target_owner_repo(command)
    repo = _base_repo(repo)  # wiki pushes authorize against the base repo (issue #16)
    active_identity = _active_gh_account()
    if (
        owner
        and repo
        and active_identity
        and owner.lower() != active_identity.lower()
        and _active_account_lacks_access(owner, repo) is True
    ):
        _deny(
            f"[devops] BLOCKED: the active gh account '{active_identity}' has no "
            f"access to the write target '{owner}/{repo}'. Switch to an authorized "
            "identity (do not auto-switch without an explicit owner->identity "
            "mapping). See rules/git-remote-write-gate.md Gate 2."
        )
        return 2

    # ADVISORY: plain push to a protected branch (no force, identity not clearly wrong).
    if protected:
        _warn(
            f"[devops] push to protected branch '{protected}'. Per "
            "rules/git-remote-write-gate.md: confirm explicit permission and that the "
            "active identity may write to the target before proceeding."
        )
        return 0

    return 0  # ordinary push to a non-protected branch -> allow silently


# --------------------------------------------------------------------------- #
# Detection helpers
# --------------------------------------------------------------------------- #

def _is_git_push(command: str) -> bool:
    return re.search(r"\bgit\b[^\n|&;]*?\bpush\b", command) is not None


def _is_force_push(command: str) -> bool:
    # Token-aware so "--force" inside a quoted message etc. is less likely to misfire,
    # but conservative: only matters in combination with a protected branch below.
    tokens = command.split()
    for tok in tokens:
        if tok in FORCE_FLAGS or tok.startswith("--force-with-lease="):
            return True
    return False


def _push_targets_protected_branch(command: str) -> str | None:
    """
    Return the protected branch name if the push clearly targets one, else None.

    Detects:
      - an explicit branch arg / refspec naming a protected branch
        (e.g. `git push origin main`, `git push origin HEAD:release`,
         `git push origin feature:main`)
      - `git push origin :main`  (delete) -> still protected target
    Stays conservative: only flags when a protected name appears as a ref token.
    """
    # Grab the segment from `push` onward (first push occurrence).
    m = re.search(r"\bpush\b(.*)$", command, re.DOTALL)
    if not m:
        return None
    tail = m.group(1)
    # Stop at a shell separator so we don't read into a chained command.
    tail = re.split(r"[\n|;&]", tail, maxsplit=1)[0]

    tokens = [t for t in tail.split() if t and not t.startswith("-")]
    # tokens may be: [remote, refspec...]. Inspect every non-flag token for a
    # protected ref. For a refspec "src:dst", the destination (dst) is what lands
    # on the remote, so prefer it; also check a bare branch token.
    for tok in tokens:
        candidates = []
        if ":" in tok:
            # src:dst -> the destination ref is what matters on the remote.
            dst = tok.split(":", 1)[1]
            candidates.append(dst)
        else:
            candidates.append(tok)
        for cand in candidates:
            ref = _normalize_ref(cand)
            if ref in PROTECTED_BRANCHES:
                return ref
    return None


def _normalize_ref(ref: str) -> str:
    # refs/heads/main -> main ; HEAD stays HEAD ; strip a leading colon (delete form)
    ref = ref.strip().lstrip(":")
    ref = re.sub(r"^refs/heads/", "", ref)
    return ref


def _is_gh_write(command: str) -> bool:
    if not re.search(r"\bgh\b", command):
        return False
    # gh pr create / gh pr merge ; gh release create ; gh api with a write method.
    if re.search(r"\bgh\s+pr\s+(create|merge)\b", command):
        return True
    if re.search(r"\bgh\s+release\s+(create|edit|delete)\b", command):
        return True
    if re.search(r"\bgh\s+api\b", command) and re.search(
        r"(?:-X|--method)\s+(POST|PUT|PATCH|DELETE)", command, re.IGNORECASE
    ):
        return True
    return False


def _target_owner_repo(command: str) -> tuple[str | None, str | None]:
    """
    Best-effort: parse (owner, repo) of the remote the push targets.

    1. If the command contains an explicit remote URL, parse from it.
    2. Else resolve the named remote (default 'origin') via `git remote get-url`.
    Returns (None, None) when it can't be determined confidently (-> no block).
    """
    # 1. explicit URL in the command itself.
    url = _find_remote_url(command)
    if url:
        owner, repo = _owner_repo_from_url(url)
        if owner and repo:
            return owner, repo

    # 2. resolve the named remote from the push command.
    remote = _push_remote_name(command)
    url = _git_remote_url(remote)
    if url:
        return _owner_repo_from_url(url)
    return None, None


def _find_remote_url(command: str) -> str | None:
    m = re.search(r"(https?://[^\s'\"]+|git@[^\s'\"]+|ssh://[^\s'\"]+)", command)
    return m.group(1) if m else None


def _owner_repo_from_url(url: str) -> tuple[str | None, str | None]:
    """
    Extract (owner, repo) from a git remote URL. Returns (None, None) on no match.

    Handles:
      https://host/owner/repo(.git)
      git@host:owner/repo(.git)
      ssh://host/owner/repo(.git)
    """
    u = url.strip()
    # scp-like: git@host:owner/repo(.git)
    m = re.match(r"^[^@]+@[^:]+:([^/]+)/([^/\s]+?)(?:\.git)?/?$", u)
    if m:
        return _clean(m.group(1)), _clean(m.group(2))
    # https:// or ssh:// -> take owner/repo after the host.
    m = re.match(
        r"^(?:https?|ssh)://(?:[^@/]+@)?[^/]+/([^/]+)/([^/\s]+?)(?:\.git)?/?$", u
    )
    if m:
        return _clean(m.group(1)), _clean(m.group(2))
    return None, None


def _clean(seg: str | None) -> str | None:
    if not seg:
        return None
    seg = seg.strip().strip("/")
    seg = re.sub(r"\.git$", "", seg)
    return seg or None


def _base_repo(repo: str | None) -> str | None:
    """
    Map a GitHub Wiki repo name to its base repo.

    A wiki's git remote is `<owner>/<repo>.wiki.git`, but the wiki is NOT a separate
    API repository — `gh repo view <owner>/<repo>.wiki` (and GET /repos/.../<repo>.wiki)
    returns 404. A wiki push is authorized by the BASE repo's permissions, so the access
    probe and the user-facing message must use the base repo, not the `.wiki` pseudo-repo.
    Without this, an admin/collaborator pushing a wiki update gets a false BLOCK (issue #16).
    """
    if not repo:
        return repo
    return re.sub(r"\.wiki$", "", repo)


def _active_account_lacks_access(owner: str, repo: str) -> bool | None:
    """
    Probe whether the ACTIVE gh account can see owner/repo.

    Returns:
      True  -> probe ran and reported NO access (a clear, blockable mismatch)
      False -> access confirmed (authorized org/collab push -> do NOT block)
      None  -> inconclusive (gh missing, offline, timeout, unexpected output)
               -> caller must NOT block on None (when uncertain, allow).
    """
    if not shutil.which("gh"):
        return None
    try:
        out = subprocess.run(
            ["gh", "repo", "view", f"{owner}/{repo}", "--json", "name"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
        )
    except Exception:
        return None  # timeout / spawn failure -> inconclusive -> allow

    if out.returncode == 0 and '"name"' in (out.stdout or ""):
        return False  # repo is visible to the active account -> authorized

    blob = ((out.stderr or "") + (out.stdout or "")).lower()
    # Only treat clearly-negative signals as a confirmed lack of access.
    if any(s in blob for s in ("could not resolve", "not found", "http 404", "404")):
        return True
    if "http 403" in blob or "permission" in blob or "denied" in blob:
        return True
    return None  # anything else (auth prompt, network error, etc.) -> inconclusive


def _push_remote_name(command: str) -> str:
    m = re.search(r"\bpush\b(.*)$", command, re.DOTALL)
    if not m:
        return "origin"
    tail = re.split(r"[\n|;&]", m.group(1), maxsplit=1)[0]
    for tok in tail.split():
        if tok.startswith("-"):
            continue
        # First non-flag, non-URL token after push is the remote name.
        if "://" in tok or "@" in tok or ":" in tok and "/" in tok:
            continue
        return tok
    return "origin"


def _git_remote_url(remote: str) -> str | None:
    if not shutil.which("git"):
        return None
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", remote],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    url = (out.stdout or "").strip()
    return url or None


def _active_gh_account() -> str | None:
    """
    Parse the active GitHub account from `gh auth status`.

    The output lists each account on a 'Logged in to github.com account NAME'
    line, followed by an 'Active account: true|false' line. We return the NAME
    whose block is marked active. Never reads or echoes the token.
    """
    if not shutil.which("gh"):
        return None
    try:
        out = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
        )
    except Exception:
        return None
    text = (out.stdout or "") + "\n" + (out.stderr or "")
    if not text.strip():
        return None

    last_account = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.search(r"account\s+([A-Za-z0-9][A-Za-z0-9-]*)", line)
        if m and "Logged in" in line:
            last_account = m.group(1)
            continue
        if "Active account: true" in line and last_account:
            return last_account
    return None


# --------------------------------------------------------------------------- #
# Output helpers (stderr only; never prints secrets)
# --------------------------------------------------------------------------- #

def _warn(msg: str) -> None:
    print(msg, file=sys.stderr)


def _deny(msg: str) -> None:
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
