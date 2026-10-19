#!/usr/bin/env python3
"""Fail when tracked files contain personal data that should not be published.

Checks every git-tracked text file for:
  * e-mail addresses outside an allowlist of placeholder and public-contact addresses;
  * home-directory paths naming a real-looking user (C:\\Users\\<name>, /home/<name>,
    /Users/<name>) instead of a placeholder such as <user> or you;
  * any string listed, one per line, in an optional local file `.privacy-denylist` at the
    repository root. The file is git-ignored, so maintainers can add their own usernames,
    workspace paths or client names without publishing them.

    python tools/check_privacy.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "example.test", "test.com", "company.com",
    "customer.com", "acme.com", "ex.com", "email.com", "real.com", "li.org",
    "users.noreply.github.com", "github.com",  # git remotes such as user@github.com:org/repo
}
ALLOWED_EMAILS = {"info@taqatechno.com", "noreply@anthropic.com", "git@github.com"}
PLACEHOLDER_USERS = {
    "you", "<you>", "user", "<user>", "username", "<username>", "me", "x", "bob", "alice",
    "jane", "john", "jdoe", "name", "<name>", "runner", "runneradmin", "odoo", "delete",
    "public", "default", "shared", "...", "%username%", "$user", "${user}",
}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf",
                 ".zip", ".gz", ".mp3", ".mp4", ".webm", ".pyc"}

EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b")
# Drive-letter paths are case-insensitive on Windows; /Users (macOS) and /home (Linux) are not,
# which keeps web routes such as app/users/page.tsx out of the check.
HOME = re.compile(r"(?:(?i:[A-Z]:[\\/]{1,2}Users[\\/]{1,2})|/home/|/Users/)([A-Za-z0-9<>%${}._-]+)")
FILE_LIKE = re.compile(r"\.[A-Za-z0-9]{1,5}$")


def tracked_files() -> list[Path]:
    # Tracked plus new-but-not-ignored files, so a local run before `git add` sees what CI will see.
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


def denylist() -> list[str]:
    path = ROOT / ".privacy-denylist"
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def main() -> int:
    deny = [d.lower() for d in denylist()]
    problems = []
    for path in tracked_files():
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for n, line in enumerate(text.splitlines(), 1):
            for m in EMAIL.finditer(line):
                addr, domain = m.group(0).lower(), m.group(1).lower()
                token_start = max(line.rfind(c, 0, m.start()) for c in " \t\"'`(<[=") + 1
                if "://" in line[token_start:m.start() + 1] or addr.startswith("git@"):
                    continue  # URL userinfo (https://user@host) or an SSH git remote, not an address
                allowed_domain = domain in ALLOWED_EMAIL_DOMAINS or any(
                    domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)
                if addr not in ALLOWED_EMAILS and not allowed_domain \
                        and not domain.endswith((".example", ".test", ".invalid", ".localhost")):
                    problems.append(f"{rel}:{n}: e-mail address {m.group(0)[0]}***@{domain}")
            for m in HOME.finditer(line):
                user = m.group(1).rstrip(".").lower()
                if user and user not in PLACEHOLDER_USERS and not FILE_LIKE.search(user) \
                        and re.fullmatch(r"[a-z][a-z0-9._-]{2,}", user):
                    problems.append(f"{rel}:{n}: home path names user {m.group(1)!r}")
            low = line.lower()
            for item in deny:
                if item in low:
                    problems.append(f"{rel}:{n}: matches an entry in .privacy-denylist")
    if problems:
        print(f"privacy check: {len(problems)} finding(s)")
        for p in problems:
            print("  " + p)
        return 1
    print("privacy check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
