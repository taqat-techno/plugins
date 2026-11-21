#!/usr/bin/env python3
"""PreToolUse hook: put Odoo.sh write and shell actions in front of the user.

The odoo-sh server and odoo_sh.py record an `approved_by` answer, but that text is
supplied by the model. This hook is the part the model cannot supply: it returns
`permissionDecision: "ask"`, so the user sees the action and answers it themselves.

It asks for:

  1. `sh_update`, `sh_restart`, `sh_shell`, `sh_odoo_shell` on a profile whose role is
     prod, on every call. Dev and stage profiles are not prompted per call: the user
     already opted in to the action through prompt 2.
  2. `odoo_sh.py allow NAME <actions>` when it adds update, restart, shell or
     odoo_shell to a profile. Narrowing the list never prompts.
  3. `odoo_sh.py add|edit NAME --role dev|stage` on a profile that is prod today
     (it would switch prompt 1 off for that build).
  4. A shell command that writes to ~/.odoo-mcp/odoo-sh.json or its backups directly
     instead of going through odoo_sh.py. Reading the file never prompts.

It stays silent when the server would refuse the call anyway (unknown profile, action
not allowed), so the user is never asked about something that cannot run.

There is no token the model could add to skip the prompt. To switch it off, the user
sets ODOO_SH_APPROVAL_PROMPT=off in the environment before starting Claude Code.

Fails open: bad input, an exception or the 3 s watchdog all end in exit 0. The
server-side gates in mcp_sh/shcore.py (allow list, approved_by_user) still apply.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_vendor"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mcp_sh"))

import hooklib  # noqa: E402
import _odoo_shell as sh  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WRITE_ACTIONS = ("update", "restart", "shell", "odoo_shell")
_TOOL_RE = re.compile(r"^mcp__(?:plugin_[A-Za-z0-9_-]+?_)?odoo-sh__sh_(update|restart|shell|odoo_shell)$")
_CLI_RE = re.compile(r"odoo_sh\.py[\"']?\s+(allow|add|edit)\b(.*)", re.I | re.S)
_FILE_RE = re.compile(r"\.odoo-mcp[\\/]+(?:sh-backups[\\/]+)?odoo-sh[^\s\"'\\/]*\.json", re.I)
_READERS = {"cat", "type", "head", "tail", "less", "more", "ls", "dir", "grep", "rg", "findstr", "stat",
            "wc", "file", "jq", "get-content", "gc", "select-string", "get-item", "get-childitem",
            "test-path", "echo"}
_WHAT = {
    "update": "upgrade modules on",
    "restart": "restart the Odoo service of",
    "shell": "run a shell command on",
    "odoo_shell": "run Python in the Odoo shell (direct database access) of",
}


def _profiles():
    """(profiles, default) from odoo-sh.json, or ({}, None) when it cannot be read."""
    try:
        import shconfig
        doc = shconfig.load()
        return doc.get("profiles") or {}, doc.get("default")
    except Exception:
        return {}, None


def _pick(name, project_dir):
    try:
        import shconfig
        return shconfig.pick(name or None, project_dir or None)
    except Exception:
        return None, None


def _short(text, limit=300):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + " ... (%d characters)" % len(text)


def _where(name, prof):
    return "%s (role %s, %s)" % (name, prof.get("role") or "prod", prof.get("url") or "no url")


def tool_reason(payload):
    m = _TOOL_RE.match(str(payload.get("tool_name") or ""))
    if not m:
        return None
    action = m.group(1)
    args = hooklib.tool_input(payload)
    explicit = args.get("profile")
    if explicit:
        candidates = [_pick(explicit, None)]
    else:
        # No profile named: the server resolves it from its own environment, which this
        # hook cannot see for certain. Consider every profile the call could land on and
        # prompt if any of them is a production profile that allows the action.
        dirs = [os.environ.get("ODOO_SH_PROJECT_DIR"), os.environ.get("CLAUDE_PROJECT_DIR"),
                payload.get("cwd"), None]
        candidates = [_pick(None, d) for d in dict.fromkeys(d or None for d in dirs)]
        os.environ.pop("ODOO_SH_PROJECT_DIR", None)
        candidates.append(_pick(None, None))
    hit = [(n, p) for n, p in candidates
           if p and action in (p.get("allow") or ["read"]) and (p.get("role") or "prod") == "prod"]
    if not hit:
        return None  # the server refuses this call itself, or it is not production
    name, prof = hit[0]
    detail = ""
    if action == "update":
        detail = " Modules: %s." % _short(args.get("modules") or "(none given)")
    elif action == "shell":
        detail = " Command: %s" % _short(args.get("command"))
    elif action == "odoo_shell":
        detail = " Snippet: %s" % _short(args.get("snippet"))
    return ("Odoo.sh PRODUCTION: this will %s %s.%s Approve only if you want this to run on the "
            "production build now." % (_WHAT[action], _where(name, prof), detail))


def _cli_calls(command):
    """(subcommand, args) for every odoo_sh.py allow/add/edit the command runs."""
    calls = []
    for argv in sh.commands(command):
        script = sh.python_script(argv)
        if script and script[0] == "odoo_sh.py" and script[1]:
            calls.append((script[1][0].lower(), list(script[1][1:])))
    if not calls:  # PowerShell quoting or a wrapper the parser does not unwrap
        first = (command.strip().split() or [""])[0].lower()
        m = _CLI_RE.search(command)
        if m and first not in _READERS and first != "git":
            calls.append((m.group(1).lower(), re.findall(r"[^\s\"';|&]+", m.group(2).split("\n")[0])))
    return [c for c in calls if c[0] in ("allow", "add", "edit")]


def _option(args, flag):
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def cli_reason(command):
    profiles, _default = _profiles()
    for sub, args in _cli_calls(command):
        positional = [a for a in args if not a.startswith("-")]
        name = positional[0] if positional else ""
        prof = profiles.get(name)
        if sub == "allow":
            wanted = [a for a in positional[1:] if a in WRITE_ACTIONS]
            current = (prof or {}).get("allow") or ["read"]
            added = [a for a in wanted if a not in current]
            if not added:
                continue
            target = _where(name, prof) if prof else "%s (profile not readable from here)" % (name or "?")
            extra = ""
            if "shell" in added or "odoo_shell" in added:
                extra = " shell and odoo_shell let the agent run any command or database change on that build."
            return ("Odoo.sh: this lets the agent %s on profile %s without being limited to read-only "
                    "tools.%s Approve only if you want to switch this on."
                    % (", ".join(added), target, extra))
        role = _option(args, "--role")
        if role and prof and (prof.get("role") or "prod") == "prod" and role.lower() != "prod":
            return ("Odoo.sh: this changes profile %s from role prod to role %s, which removes the "
                    "per-call approval prompt for its write and shell actions. Approve only if this "
                    "build is really not production." % (_where(name, prof), role))
    return None


def file_reason(command):
    if not _FILE_RE.search(command):
        return None
    progs = [sh.prog(argv) for argv in sh.commands(command)]
    if progs and all(p in _READERS for p in progs) and ">" not in command:
        return None
    if any(sh.python_script(argv) and sh.python_script(argv)[0] == "odoo_sh.py" for argv in sh.commands(command)):
        return None
    return ("Odoo.sh: this command touches ~/.odoo-mcp/odoo-sh.json directly. That file decides which "
            "builds the agent may change; it is normally edited only through odoo_sh.py. Approve only "
            "if you asked for this.")


def main() -> int:
    if (os.environ.get("ODOO_SH_APPROVAL_PROMPT") or "").strip().lower() in ("off", "0", "false", "no"):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool = str(payload.get("tool_name") or "")
    if tool.startswith("mcp__"):
        reason = tool_reason(payload)
    else:
        command = str(hooklib.tool_input(payload).get("command") or "")
        low = command.lower()
        if "odoo_sh" not in low and "odoo-sh" not in low:
            return 0
        reason = cli_reason(command) or file_reason(command)
    if reason:
        hooklib.ask(reason)
    return 0


if __name__ == "__main__":
    hooklib.watchdog(3)
    hooklib.run(main)
