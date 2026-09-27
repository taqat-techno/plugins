#!/usr/bin/env python3
"""Developer-side control for the Odoo MCP server: human approvals and the audit log.

  approve <profile> <mode> [--ttl MIN]   grant this machine's Claude sessions <mode> on
                                         <profile> for MIN minutes (profiles whose
                                         approval is "human" - production by default)
  revoke <profile>                       remove that grant now
  grants                                 list live grants
  audit [--tail N]                       show the last N audit entries

`approve` is for the DEVELOPER. It refuses to run without an interactive terminal
and asks you to type the profile name back, so a grant cannot come from Claude's
non-interactive shell. (In Git Bash on Windows, run it via `winpty python ...` or
from PowerShell / Windows Terminal, where the terminal is detected.)

A grant never exceeds the profile's ceiling: the ceiling is what the developer wrote
in the profile, and only an edit there can raise it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# The server package lives in <plugin>/mcp. These CLIs sit outside it so the server
# itself contains no process-execution path (tests/mcp enforce that).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp"))

import profiles as P  # noqa: E402
import session_state as S  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _find_profile(name: str):
    """Look the profile up from this checkout, then from the servers file alone."""
    for proj in (Path.cwd(), P.home()):
        try:
            cat = P.load_catalog(None, proj)
        except P.ProfileError as exc:
            print("configuration problem: %s" % exc, file=sys.stderr)
            raise SystemExit(2)
        if name in cat.profiles:
            return cat.profiles[name]
    return None


def cmd_approve(args) -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("odoo_mcp_ctl approve must be run by the developer in an interactive terminal.\n"
              "It will not run from a non-interactive shell - that is what keeps an approval "
              "the developer's decision.", file=sys.stderr)
        return 3
    prof = _find_profile(args.profile)
    if prof is None:
        print("unknown profile %r" % args.profile, file=sys.stderr)
        return 2
    if args.mode not in P.MODES:
        print("mode must be one of %s" % ", ".join(P.MODES), file=sys.stderr)
        return 2
    if P.RANK[args.mode] > P.RANK[prof.ceiling]:
        print("profile %r has ceiling %r - a grant cannot exceed it. Edit the profile in %s if "
              "that is really intended." % (prof.name, prof.ceiling, prof.source), file=sys.stderr)
        return 2
    cap = S.MAX_TTL.get(prof.tier) or 480
    ttl = max(1, min(int(args.ttl), cap))
    print("Grant Claude sessions on this machine:")
    print("  profile : %s (%s)" % (prof.name, prof.tier))
    print("  target  : %s  database %s" % (prof.url, prof.db or "(host-selected)"))
    print("  mode    : %s for %d minutes" % (args.mode, ttl))
    typed = input("Type the profile name to approve: ").strip()
    if typed != prof.name:
        print("Not approved.")
        return 1
    now = time.time()
    grant = {"profile": prof.name, "mode": args.mode, "created_at": now,
             "expires_at": now + ttl * 60, "by": "odoo_mcp_ctl (interactive)"}
    path = S.grant_path(prof.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(grant, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    S.audit({"action": "grant", "profile": prof.name, "tier": prof.tier, "mode": args.mode,
             "ttl_minutes": ttl})
    print("Approved until %s UTC. Tell Claude to retry." % time.strftime("%H:%M", time.gmtime(now + ttl * 60)))
    return 0


def cmd_revoke(args) -> int:
    path = S.grant_path(args.profile)
    existed = path.exists()
    path.unlink(missing_ok=True)
    S.audit({"action": "revoke", "profile": args.profile})
    print("revoked" if existed else "no grant for %r" % args.profile)
    return 0


def cmd_grants(_args) -> int:
    rows = []
    folder = P.grants_dir()
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            try:
                g = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            left = int((float(g.get("expires_at", 0)) - time.time()) / 60)
            if left <= 0:
                path.unlink(missing_ok=True)
                continue
            rows.append({"profile": g.get("profile"), "mode": g.get("mode"), "minutes_left": left})
    print(json.dumps({"grants": rows}, indent=2))
    return 0


def cmd_audit(args) -> int:
    path = P.audit_file()
    if not path.is_file():
        print("(no audit entries yet)")
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[-args.tail:]:
        print(line)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Odoo MCP approvals and audit log")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("approve")
    a.add_argument("profile")
    a.add_argument("mode", choices=P.MODES)
    a.add_argument("--ttl", type=int, default=30, help="minutes (capped per tier)")
    r = sub.add_parser("revoke")
    r.add_argument("profile")
    sub.add_parser("grants")
    au = sub.add_parser("audit")
    au.add_argument("--tail", type=int, default=20)
    args = ap.parse_args(argv)
    handler = {"approve": cmd_approve, "revoke": cmd_revoke, "grants": cmd_grants,
               "audit": cmd_audit}.get(args.cmd)
    if handler is None:
        ap.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
