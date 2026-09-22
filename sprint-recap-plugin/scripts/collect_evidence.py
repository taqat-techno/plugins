#!/usr/bin/env python3
"""Stage 01 - collect: gather sprint evidence from three sources and correlate.

Sources, in decreasing formality:
  * Azure DevOps  - the iteration's work items (what the board says shipped)
  * git           - commits in the sprint window (what actually shipped)
  * transcripts   - Claude sessions in the window (how it was built)

Correlated on work-item ID, scraped from branch names and commit subjects.
Every source degrades independently: a missing `az` CLI or an unreadable repo
downgrades that source and is reported in `sources`, it never aborts the run.

Read-only. Writes one artifact: 01-collect/evidence.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from _common import git, info, run_dir, which, write_json

# Explicit reference: "#23923", "AB#23923". Always trusted.
EXPLICIT_ID_RE = re.compile(r"(?:AB#|#)(\d{3,7})(?!\d)")
# Branch-style reference: "feature/23923-donor-export", "bugfix_23923".
BRANCH_ID_RE = re.compile(r"(?:^|[/_-])(\d{3,7})(?=[-_/]|$)")
# A bare 4-digit number that looks like a year is almost never a work item.
YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
SYSTEM_NOISE = ("<system-reminder>", "<command-name>", "[Artifact comment sent")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect sprint evidence.")
    p.add_argument("--sprint", required=True, help="Sprint name, e.g. 'Sprint 24'")
    p.add_argument("--iteration-path", help="Azure DevOps iteration path")
    p.add_argument("--since", required=True, help="ISO date, sprint start")
    p.add_argument("--until", required=True, help="ISO date, sprint end")
    p.add_argument("--repos", default="", help="Comma-separated repo paths")
    p.add_argument("--organization", help="Azure DevOps organization URL")
    p.add_argument("--project", help="Azure DevOps project")
    p.add_argument("--author", help="Filter git commits to this author substring")
    p.add_argument("--no-sessions", action="store_true")
    p.add_argument("--no-azure", action="store_true")
    p.add_argument("--out", help="Override output path")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Azure DevOps
# --------------------------------------------------------------------------- #
def collect_azure(args):
    if args.no_azure:
        return {}, "skipped (--no-azure)"
    if not which("az"):
        return {}, "unavailable (az CLI not on PATH)"
    if not args.iteration_path:
        return {}, "skipped (no --iteration-path given)"

    path = args.iteration_path.replace("'", "''")
    wiql = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType], "
        "[System.State], [System.AssignedTo] FROM WorkItems "
        "WHERE [System.IterationPath] UNDER '" + path + "'"
    )
    cmd = ["az", "boards", "query", "--wiql", wiql, "-o", "json"]
    if args.organization:
        cmd += ["--org", args.organization]
    if args.project:
        cmd += ["--project", args.project]

    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace", shell=(os.name == "nt"),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {}, "unavailable (" + str(exc) + ")"
    if out.returncode != 0:
        detail = (out.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "az returned non-zero"
        return {}, "failed (" + reason + ")"

    try:
        rows = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return {}, "failed (az returned non-JSON)"

    items = {}
    for row in rows:
        fields = row.get("fields", {}) or {}
        wid = str(row.get("id") or fields.get("System.Id") or "").strip()
        if not wid:
            continue
        assigned = fields.get("System.AssignedTo") or {}
        items[wid] = {
            "work_item": int(wid),
            "title": fields.get("System.Title", ""),
            "type": fields.get("System.WorkItemType", ""),
            "state": fields.get("System.State", ""),
            "assigned_to": (
                assigned.get("displayName") if isinstance(assigned, dict) else assigned
            ),
            "parent_pbi": None,
            "commits": [],
            "sessions": [],
        }
    return items, "ok (" + str(len(items)) + " work items)"


def attach_parents(items, args) -> None:
    """Fill parent_pbi. Best-effort: a failure degrades one item, not the run."""
    for wid, item in items.items():
        cmd = ["az", "boards", "work-item", "show", "--id", wid,
               "--expand", "relations", "-o", "json"]
        if args.organization:
            cmd += ["--org", args.organization]
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace", shell=(os.name == "nt"),
            )
            if out.returncode != 0:
                continue
            data = json.loads(out.stdout or "{}")
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            continue
        for rel in data.get("relations") or []:
            if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
                tail = (rel.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
                if tail.isdigit():
                    item["parent_pbi"] = int(tail)
                break


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #
def commit_bodies(repo, args) -> dict:
    """SHA -> commit body, fetched in its own pass.

    The body cannot ride along in the main `--name-only` call: it is
    multi-line, and git appends the file list straight after the formatted
    output, so there is no way to tell where a body ends and the paths begin.
    A second log is cheap next to the Azure DevOps round trips and keeps the
    header parsing unchanged.
    """
    log_args = [
        "log", "--all", "--no-merges",
        "--since=" + args.since, "--until=" + args.until,
        "--pretty=format:%x1d%H\x1e%b",
    ]
    if args.author:
        log_args.append("--author=" + args.author)
    bodies = {}
    for block in git(log_args, repo, timeout=120).split("\x1d"):
        if not block.strip():
            continue
        sha, _, body = block.partition("\x1e")
        bodies[sha.strip()] = body
    return bodies


def collect_git(repos, args):
    commits, notes = [], []
    sep = "\x1e"
    # The record separator leads the header. With --name-only git appends the
    # file list AFTER the formatted line, so a trailing separator would leave
    # every block but the first starting with filenames instead of a header.
    fmt = "%x1d" + sep.join(["%H", "%h", "%an", "%aI", "%s", "%D"])
    for repo in repos:
        if not (repo / ".git").exists():
            notes.append(str(repo) + ": not a git repo, skipped")
            continue
        log_args = [
            "log", "--all", "--no-merges",
            "--since=" + args.since, "--until=" + args.until,
            "--pretty=format:" + fmt, "--name-only",
        ]
        if args.author:
            log_args.append("--author=" + args.author)
        raw = git(log_args, repo, timeout=120)
        if not raw.strip():
            notes.append(repo.name + ": 0 commits in window")
            continue
        bodies = commit_bodies(repo, args)
        count = body_only = 0
        for block in raw.split("\x1d"):
            block = block.strip("\n")
            if not block.strip():
                continue
            head, _, files_blob = block.partition("\n")
            parts = head.split(sep)
            if len(parts) < 5:
                continue
            sha, short, author, date, subject = parts[:5]
            refs = parts[5] if len(parts) > 5 else ""
            files = [f for f in files_blob.splitlines() if f.strip()]
            # A team that writes "Closes #33724 #33727" in the BODY and keeps
            # the subject prose-only is invisible to subject-plus-refs
            # matching. Only EXPLICIT references count here: a bare number in
            # free prose is a version, a count or an HTTP status far more
            # often than it is a work item.
            head_ids = extract_ids(subject + " " + refs)
            body_ids = sorted(set(EXPLICIT_ID_RE.findall(bodies.get(sha, ""))))
            work_items = sorted(set(head_ids) | set(body_ids))
            if body_ids and not head_ids:
                body_only += 1
            commits.append({
                "repo": repo.name,
                "repo_path": str(repo),
                "sha": sha,
                "short_sha": short,
                "author": author,
                "date": date,
                "subject": subject,
                "refs": refs,
                "files": files[:50],
                "file_count": len(files),
                "work_items": work_items,
            })
            count += 1
        note = repo.name + ": " + str(count) + " commits"
        if body_only:
            note += " (" + str(body_only) + " matched on a body reference only)"
        notes.append(note)
    return commits, notes


# --------------------------------------------------------------------------- #
# Claude session transcripts
# --------------------------------------------------------------------------- #
def collect_sessions(repos, args):
    if args.no_sessions:
        return [], "skipped (--no-sessions)"
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return [], "unavailable (no " + str(base) + ")"

    since, until = args.since, args.until
    repo_names = {r.resolve().as_posix().lower() for r in repos}
    sessions = {}

    for transcript in base.glob("*/*.jsonl"):
        try:
            handle = transcript.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "user":
                    continue
                stamp = (rec.get("timestamp") or "")[:10]
                if not stamp or stamp < since or stamp > until:
                    continue
                cwd = (rec.get("cwd") or "").replace("\\", "/").lower()
                if repo_names and not any(cwd.startswith(n) for n in repo_names):
                    continue
                text = message_text(rec.get("message"))
                if not text or any(n in text for n in SYSTEM_NOISE):
                    continue
                sid = rec.get("sessionId") or transcript.stem
                entry = sessions.setdefault(sid, {
                    "session_id": sid,
                    "transcript": str(transcript),
                    "cwd": rec.get("cwd"),
                    "git_branch": rec.get("gitBranch"),
                    "date": rec.get("timestamp"),
                    "prompts": [],
                    "work_items": [],
                })
                if len(entry["prompts"]) < 12:
                    entry["prompts"].append(text[:400])
                entry["work_items"] = sorted(set(
                    entry["work_items"]
                    + extract_ids(text)
                    + extract_ids(rec.get("gitBranch") or "")
                ))
    return list(sessions.values()), "ok (" + str(len(sessions)) + " sessions)"


def message_text(message) -> str:
    if isinstance(message, str):
        return message.strip()
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p).strip()
    return ""


# --------------------------------------------------------------------------- #
# correlation
# --------------------------------------------------------------------------- #
def extract_ids(text: str):
    """Pull work-item IDs out of a commit subject, branch ref or prompt.

    An explicit "#23923" is always taken. A bare branch-style number is taken
    too, except when it looks like a year -- "release/2026-planning" should not
    invent work item 2026 and silently attach half the sprint's commits to it.
    """
    if not text:
        return []
    found = set(EXPLICIT_ID_RE.findall(text))
    for token in re.split(r"[\s,;()\[\]]+", text):
        # A token that is nothing BUT digits is not a branch-style reference.
        # In prose it is a status code, a port, a count or a version:
        # "serve a favicon instead of a 404 on every page" must not file that
        # commit under work item 404. A real branch-style reference always
        # carries its delimiter -- feature/23923-donor-export, bugfix_23923.
        if token.isdigit():
            continue
        for candidate in BRANCH_ID_RE.findall(token):
            if not YEAR_RE.match(candidate):
                found.add(candidate)
    return sorted(found)


def correlate(items, commits, sessions):
    unattributed = {"commits": [], "sessions": []}
    board_driven = bool(items)

    for commit in commits:
        matched = [w for w in commit["work_items"] if w in items]
        if matched:
            for wid in matched:
                items[wid]["commits"].append(commit)
        elif commit["work_items"] and not board_driven:
            # No board data at all: synthesise items from the IDs we found.
            for wid in commit["work_items"]:
                items.setdefault(wid, blank_item(wid))["commits"].append(commit)
        else:
            unattributed["commits"].append(commit)

    for session in sessions:
        matched = [w for w in session["work_items"] if w in items]
        if matched:
            for wid in matched:
                items[wid]["sessions"].append(session)
        else:
            unattributed["sessions"].append(session)

    return unattributed


def blank_item(wid: str) -> dict:
    return {
        "work_item": int(wid), "title": "", "type": "", "state": "",
        "assigned_to": None, "parent_pbi": None, "commits": [], "sessions": [],
    }


def main() -> int:
    args = parse_args()
    repos = [Path(p.strip()).resolve() for p in args.repos.split(",") if p.strip()]
    if not repos:
        repos = [Path.cwd().resolve()]

    items, azure_status = collect_azure(args)
    if items and which("az"):
        attach_parents(items, args)
    commits, git_notes = collect_git(repos, args)
    sessions, session_status = collect_sessions(repos, args)
    unattributed = correlate(items, commits, sessions)

    ordered = sorted(items.values(), key=lambda i: i["work_item"])
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sprint": args.sprint,
        "iteration_path": args.iteration_path,
        "window": {"since": args.since, "until": args.until},
        "repos": [str(r) for r in repos],
        "sources": {
            "azure_devops": azure_status,
            "git": git_notes,
            "sessions": session_status,
        },
        "items": ordered,
        "unattributed": unattributed,
        "summary": {
            "work_items": len(ordered),
            "commits": len(commits),
            "sessions": len(sessions),
            "items_with_commits": sum(1 for i in ordered if i["commits"]),
            "unattributed_commits": len(unattributed["commits"]),
        },
    }

    out = (Path(args.out) if args.out
           else run_dir(args.sprint) / "01-collect" / "evidence.json")
    write_json(out, evidence)

    info("Azure DevOps : " + azure_status)
    for note in git_notes:
        info("git          : " + note)
    info("sessions     : " + session_status)
    info(
        "correlated   : " + str(evidence["summary"]["items_with_commits"])
        + "/" + str(len(ordered)) + " work items have commits, "
        + str(len(unattributed["commits"])) + " commits unattributed"
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
