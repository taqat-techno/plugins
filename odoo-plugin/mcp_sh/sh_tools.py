"""odoo-sh MCP tools: Odoo.sh builds over SSH, read-only by default.

Why MCP tools and not a script run through Bash: the remote commands are fixed scripts
built from validated arguments (no shell text from the model outside the opt-in `shell`
action), every byte of output passes redaction here before it reaches the model, and the
gate (per-profile opt-in for each non-read action, plus a fresh yes per production call)
is enforced in code instead of in a prompt. The CLI scripts/mcp/odoo_sh.py shares this core
for setup, the doctor and a read-only fallback.
"""

from __future__ import annotations

import json

import shconfig as C
import shcore as S

_prof = {"type": "string", "description": "Profile name in ~/.odoo-mcp/odoo-sh.json (default: the profile bound "
                                          "to this folder, the file's default, or the only one)"}
_timeout = {"type": "integer", "minimum": 5, "maximum": S.CMD_TIMEOUT_MAX,
            "description": "Remote command timeout in seconds (default: the profile's command_timeout, else %d)"
                           % S.CMD_TIMEOUT_DEFAULT}
_approved = {"type": "string", "description": "Production-role profiles only: the developer's verbatim yes "
                                              "for THIS call. Never reuse an earlier answer."}
_GATE = ("Refused unless the profile allows '%s' (the developer opts in with odoo_sh.py allow <profile> %s "
         "--approved-by); on a prod-role profile also needs approved_by_user on every call.")

TOOLS = [
    {"name": "sh_status",
     "description": "Odoo.sh SSH profiles on this machine (project, branch, role, url, key path and fingerprint, "
                    "overrides, allowed actions) and, unless resolve=false, the build each one points at right now "
                    "(from <url>/web/database/list; no SSH). Start here.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "resolve": {"type": "boolean", "description": "Resolve the current build (default true)"}}}},
    {"name": "sh_doctor",
     "description": "Test the SSH path to the profile's current build step by step and return ONE classified "
                    "result with fixes: key_missing, key_not_private, key_encrypted_no_agent, no_key, ssh_missing, "
                    "url_dns_failure, url_unreachable, db_list_unavailable, build_not_found, stale_build, dns_failure, "
                    "tcp_timeout (with whether 443 on the same host and github.com:22 connect), tcp_refused, "
                    "auth_refused, key_permissions, host_key_changed, algorithm_mismatch, ok.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"profile": _prof}}},
    {"name": "sh_commit",
     "description": "The code the build actually runs: in the source folder (default ~/src/user), the branch, "
                    "git log -1, uncommitted changes on the build, and submodule state. The proof of a deploy - "
                    "not the green build or an HTTP 200.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "timeout_s": _timeout}}},
    {"name": "sh_logs",
     "description": "Tail a build log. file: odoo (odoo.log), install (install.log: the build's module install/"
                    "upgrade log), pip (pip.log), or any file name in the logs folder (default ~/logs; "
                    "list_files=true lists them). Filters run on the build: grep (extended regex), since "
                    "'YYYY-MM-DD HH:MM:SS' (log time, UTC), errors_only (ERROR/CRITICAL entries with their traceback "
                    "lines), pid. Secrets (odoo.conf values, tokens, passwords) are redacted.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "file": {"type": "string"}, "list_files": {"type": "boolean"},
         "lines": {"type": "integer", "minimum": 1, "maximum": 3000},
         "grep": {"type": "string"}, "ignore_case": {"type": "boolean"},
         "since": {"type": "string"}, "errors_only": {"type": "boolean"}, "pid": {"type": "integer"},
         "timeout_s": _timeout}}},
    {"name": "sh_modules",
     "description": "Module versions in the build's database (ir_module_module via psql): name, latest_version, "
                    "state, write_date. Default: installed modules; pass names to check specific ones.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "names": {"type": "array", "items": {"type": "string"}},
         "state": {"type": "string", "enum": ["installed", "all", "to upgrade", "to install", "uninstalled"]},
         "timeout_s": _timeout}}},
    {"name": "sh_health",
     "description": "Build health: disk (home, /tmp, filestore, odoosh-storage), load, memory, Odoo worker "
                    "processes, worker and limit settings.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "timeout_s": _timeout}}},
    {"name": "sh_update",
     "description": "OPT-IN: upgrade modules on the build (odoo-bin -u <modules> --stop-after-init --no-http) as "
                    "a background job; returns a job id for sh_job. " + _GATE % ("update", "update"),
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["modules"], "properties": {
         "profile": _prof, "modules": {"type": "array", "items": {"type": "string"}, "minItems": 1},
         "approved_by_user": _approved}}},
    {"name": "sh_restart",
     "description": "OPT-IN: restart the build's Odoo server (odoosh-restart http) as a background job. "
                    + _GATE % ("restart", "restart"),
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "profile": _prof, "approved_by_user": _approved}}},
    {"name": "sh_shell",
     "description": "OPT-IN: run one non-interactive shell command on the build (stdin closed) and return its "
                    "redacted output and exit code. For inspection the other tools do not cover (ls, cat a "
                    "config, pip list, git diff). " + _GATE % ("shell", "shell"),
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["command"], "properties": {
         "profile": _prof, "command": {"type": "string"}, "approved_by_user": _approved, "timeout_s": _timeout}}},
    {"name": "sh_odoo_shell",
     "description": "OPT-IN: run a Python snippet in odoo-bin shell on the build's database (env is available), "
                    "always followed by env.cr.rollback(); a snippet that calls commit() is refused. Database "
                    "changes are discarded, but side effects outside the transaction (mail, HTTP calls, files) "
                    "still happen. " + _GATE % ("odoo_shell", "odoo_shell"),
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["snippet"], "properties": {
         "profile": _prof, "snippet": {"type": "string"}, "approved_by_user": _approved, "timeout_s": _timeout}}},
    {"name": "sh_job",
     "description": "Result of an sh_update / sh_restart job: exit code once finished, ERROR count, log tail. "
                    "Call it when you need the result; do not poll in a loop.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["job_id"], "properties": {
         "profile": _prof, "job_id": {"type": "string"}, "tail": {"type": "integer", "minimum": 0, "maximum": 500}}}},
]


def _pick(args):
    name, prof = C.pick(args.get("profile"))
    return name, dict(prof, _name=name)


def _header(name, prof, target):
    where = target.get("db") or ("%s@%s" % (target.get("user"), target.get("host")))
    return "[odoo.sh %s · %s · role %s · allow %s]" % (name, where, prof.get("role"), ",".join(prof.get("allow", [])))


def _ssh(args, prof, target, script):
    return S.ssh_run(prof, target, script, timeout=args.get("timeout_s"))


def _text(name, prof, target, res):
    return "%s\n%s%s" % (_header(name, prof, target), res["stdout"].rstrip(),
                         ("\n[stderr] " + res["stderr"].strip()) if res["stderr"].strip() else "")


def _profile_view(name, prof, resolve=True):
    view = {k: v for k, v in prof.items() if k not in ("created_at", "_name")}
    if prof.get("key"):
        ki = S.key_info(prof["key"])
        view["key_found"] = ki["exists"]
        view["key_fingerprint"], view["key_passphrase"] = ki.get("fingerprint"), ki.get("encrypted")
    else:
        view["key"] = "(none: keys offered by ssh-agent)"
    if resolve:
        try:
            t = S.resolve(prof)
            view["current_build"] = {k: t.get(k) for k in ("db", "build", "branch", "user", "host", "pinned")}
        except S.ShError as e:
            view["current_build"] = e.as_dict()
    return view


def t_status(args):
    doc = C.load()
    profs = doc["profiles"]
    if not profs:
        return {"profiles": {}, "file": C.path(),
                "next": "run /odoo:sh-setup - it lists your SSH keys, writes a profile and tests the connection"}
    names = [args["profile"]] if args.get("profile") else sorted(profs)
    out = {"file": C.path(), "default": doc.get("default"), "profiles": {}}
    for n in names:
        if n not in profs:
            raise C.ConfigError("unknown profile %r (known: %s)" % (n, ", ".join(sorted(profs))))
        out["profiles"][n] = _profile_view(n, dict(profs[n], _name=n), args.get("resolve", True))
    return out


def t_doctor(args):
    name, prof = _pick(args)
    return S.doctor(name, prof)


def t_commit(args):
    name, prof = _pick(args)
    target = S.resolve(prof)
    return _text(name, prof, target, _ssh(args, prof, target, S.script_commit(prof.get("src_dir") or S.SRC_DIR)))


def t_logs(args):
    name, prof = _pick(args)
    logs_dir = prof.get("logs_dir") or S.LOGS_DIR
    if args.get("list_files"):
        script = S.script_log_list(logs_dir)
    else:
        kw = {k: args.get(k) for k in ("lines", "grep", "since", "errors_only", "pid", "ignore_case")}
        script = S.script_logs(file=args.get("file") or "odoo", logs_dir=logs_dir, **kw)
    target = S.resolve(prof)
    return _text(name, prof, target, _ssh(args, prof, target, script))


def t_modules(args):
    name, prof = _pick(args)
    target = S.resolve(prof)
    script = S.script_modules(db=target.get("db"), names=args.get("names"), state=args.get("state"))
    return _text(name, prof, target, _ssh(args, prof, target, script))


def t_health(args):
    name, prof = _pick(args)
    target = S.resolve(prof)
    return _text(name, prof, target, _ssh(args, prof, target, S.script_health()))


def _gated(args, action, build_script, background):
    name, prof = _pick(args)
    approved = S.check_write(name, prof, action, args.get("approved_by_user"))
    target = S.resolve(prof)
    job = S.new_job_id(action) if background else None
    script = build_script(target, job)    # validates arguments before anything is logged or sent
    C.audit({"action": action, "profile": name, "role": prof.get("role"), "db": target.get("db"),
             "host": target.get("host"), "modules": args.get("modules"), "job": job,
             "command_chars": len(args.get("command") or args.get("snippet") or "") or None,
             "approved_by": approved or None})
    if background:
        res = S.ssh_run(prof, target, script, timeout=30)
        return "%s\nstarted %s job %s on %s - read it with sh_job job_id=%s\n%s" % (
            _header(name, prof, target), action, job, target.get("db") or target.get("host"), job,
            res["stdout"].strip())
    return _text(name, prof, target, _ssh(args, prof, target, script))


def t_update(args):
    return _gated(args, "update", lambda t, job: S.script_update(job, args.get("modules") or [], db=t.get("db")), True)


def t_restart(args):
    return _gated(args, "restart", lambda t, job: S.script_restart(job), True)


def t_shell(args):
    return _gated(args, "shell", lambda t, job: S.script_shell(args.get("command")), False)


def t_odoo_shell(args):
    return _gated(args, "odoo_shell", lambda t, job: S.script_odoo_shell(args.get("snippet"), db=t.get("db")), False)


def t_job(args):
    name, prof = _pick(args)
    target = S.resolve(prof)
    res = _ssh(args, prof, target, S.script_job(args.get("job_id"), args.get("tail", 80)))
    if "__NOJOB__" in res["stdout"]:
        return ("%s\nno log for job %s on this build - the build was probably replaced since the job started "
                "(a rebuild drops ~/logs); check the branch history in Odoo.sh" % (_header(name, prof, target),
                                                                                  args.get("job_id")))
    return _text(name, prof, target, res)


HANDLERS = {"sh_status": t_status, "sh_doctor": t_doctor, "sh_commit": t_commit, "sh_logs": t_logs,
            "sh_modules": t_modules, "sh_health": t_health, "sh_update": t_update, "sh_restart": t_restart,
            "sh_shell": t_shell, "sh_odoo_shell": t_odoo_shell, "sh_job": t_job}


def dispatch(name: str, args: dict):
    fn = HANDLERS.get(name)
    if fn is None:
        return "unknown tool %s" % name, True
    try:
        out = fn(args or {})
    except S.ShError as e:
        return json.dumps(e.as_dict(), indent=1, ensure_ascii=False), True
    except C.ConfigError as e:
        return str(e), True
    if isinstance(out, str):
        return out, False
    return json.dumps(out, indent=1, default=str, ensure_ascii=False), not out.get("ok", True)
