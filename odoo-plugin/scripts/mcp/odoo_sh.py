#!/usr/bin/env python3
"""Odoo.sh SSH setup, doctor and read-only fallback for the odoo plugin.

Owns ~/.odoo-mcp/odoo-sh.json (a hook blocks direct edits). Shares its core with the
odoo-sh MCP server (mcp_sh/), so a profile written here is used by the next tool call.
Any number of profiles: several projects, several branches each.

    odoo_sh.py                         status: every profile and the build it resolves to
    odoo_sh.py list | show NAME        profiles without contacting builds / one profile in full
    odoo_sh.py keys [--dir D]          keys on this machine (any type, any file name)
    odoo_sh.py keys --print PATH       the public line to paste into Odoo.sh > Profile > SSH keys
    odoo_sh.py keys --generate NAME [--type ed25519|rsa] [--passphrase-prompt]
    odoo_sh.py keys --match FINGERPRINT   which local key is the one Odoo.sh lists (MD5 or SHA256)
    odoo_sh.py add NAME --project P --url URL [--branch B] [--role dev|stage|prod]
                       [--key PATH | --agent] [--ssh "<ssh command Odoo.sh shows>"]
                       [--ssh-user U] [--host H] [--port N] [--proxy-jump J]
                       [--ssh-binary PATH] [--ssh-option Key=Value ...]
                       [--connect-timeout S] [--command-timeout S] [--src-dir D] [--logs-dir D]
                       [--path DIR ...] [--clear FIELD ...]
    odoo_sh.py edit NAME [same options]   change an existing profile (refuses unknown names)
    odoo_sh.py allow NAME [update] [restart] [shell] [odoo_shell] --approved-by "<developer's answer>"
    odoo_sh.py deny NAME               back to read-only (no approval needed)
    odoo_sh.py default NAME | remove NAME
    odoo_sh.py doctor [NAME]           classified connection test
    odoo_sh.py run commit|logs|modules|health [--profile NAME] [filters]   read-only

Never prints a private key or passphrase, and never asks for one: a passphrase is typed
into ssh-add in the developer's own terminal. Exit codes: 0 ok, 1 failure, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "mcp_sh"))

import shconfig as C  # noqa: E402
import shcore as S  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, TypeError):
        pass

CLEARABLE = ("branch", "key", "ssh_user", "host", "port", "proxy_jump", "ssh_binary", "ssh_options",
             "connect_timeout", "command_timeout", "src_dir", "logs_dir", "paths")


def _print(obj, as_json):
    if as_json or not isinstance(obj, dict):
        print(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False, default=str))
        return
    if "result" in obj and "steps" in obj:   # doctor
        mark = "OK" if obj.get("ok") else "FAIL"
        print("%s  [%s]  %s" % (mark, obj["result"], obj.get("message", "")))
        for st in obj.get("steps", []):
            print("  %s %-24s %s" % ("+" if st["ok"] else "x", st["step"], st.get("detail", "")))
        for f in obj.get("fix", []):
            print("  fix: %s" % f)
        return
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def cmd_status(a, resolve=True, only=None):
    doc = C.load()
    if not doc["profiles"]:
        print("No Odoo.sh profiles yet (%s).\n"
              "Next: odoo_sh.py keys    - pick a key, then paste its public line into Odoo.sh > Profile > SSH keys\n"
              "      odoo_sh.py add <name> --project <project> --branch <branch> --role stage "
              "--url https://<project>-<branch>.odoo.com --key <private key path>\n"
              "      odoo_sh.py doctor <name>" % C.path())
        return 0
    import sh_tools as T
    out = T.t_status({"resolve": resolve, "profile": only})
    _print(out, a.json)
    return 0


def cmd_keys(a):
    if a.generate:
        if not C.NAME_RE.match(a.generate):
            print("key name must be lowercase letters, digits, - or _", file=sys.stderr)
            return 2
        target = S.expand(os.path.join(a.dir or "~/.ssh", a.generate))
        if os.path.exists(target):
            print("%s already exists; pick another name" % target, file=sys.stderr)
            return 1
        os.makedirs(os.path.dirname(target), exist_ok=True)
        argv = ["ssh-keygen", "-t", a.type, "-f", target, "-C", "odoo.sh %s" % a.generate]
        if a.type == "rsa":
            argv[3:3] = ["-b", "4096"]
        if not a.passphrase_prompt:
            argv += ["-N", ""]   # with --passphrase-prompt, ssh-keygen asks in this terminal itself
        try:
            rc = subprocess.call(argv)
        except FileNotFoundError:
            print("ssh-keygen not found; install the OpenSSH client", file=sys.stderr)
            return 1
        if rc != 0:
            return rc
        a.print = target
    if a.print:
        p = a.print[:-4] if a.print.endswith(".pub") else a.print
        ki = S.key_info(p)
        if not ki.get("public_key"):
            print("no readable .pub beside %s; create it with: ssh-keygen -y -f \"%s\" > \"%s.pub\""
                  % (ki["path"], ki["path"], ki["path"]), file=sys.stderr)
            return 1
        print("Paste this line into Odoo.sh > your avatar > Profile > SSH keys:\n")
        print(ki["public_key"])
        if ki.get("type") and ki["type"] not in S.ODOO_SH_KEY_TYPES:
            print("\nWARNING: this is a %s key; Odoo.sh accepts only ssh-ed25519 and ssh-rsa." % ki["type"])
        print("\nAfter adding it, Odoo.sh lists it under Active keys as: %s" % ki.get("fingerprint_md5"))
        print("\nprivate key path for the profile: %s (%s, passphrase: %s)"
              % (ki["path"], ki["fingerprint"], {True: "yes - load it with ssh-add before use", False: "no",
                                                 None: "unknown"}[ki["encrypted"]]))
        return 0
    keys = S.list_keys(a.dir)
    if a.match:
        hits = S.match_keys(a.match, keys)
        if a.json:
            _print(hits, True)
            return 0 if hits else 1
        if not hits:
            print("No key in %s has the fingerprint %s.\nThe key Odoo.sh lists is not on this machine "
                  "(or its .pub file is missing). Either add one of the keys below in Odoo.sh "
                  "(odoo_sh.py keys --print <path>), or copy that key pair here.\n"
                  % (", ".join(S.key_dirs(a.dir)), a.match))
        for k in hits:
            usable = k["has_private_key"] and (k["type"] in S.ODOO_SH_KEY_TYPES)
            print("MATCH  %s  %s  private=%s passphrase=%s  %s" % (
                k["private_key_path"], k["type"], "yes" if k["has_private_key"] else "MISSING",
                {True: "yes", False: "no", None: "?"}[k["passphrase"]], k["comment"] or ""))
            if usable:
                print("Use it: odoo_sh.py edit <profile> --key \"%s\"   (or add ... --key for a new profile)"
                      % k["private_key_path"])
        if hits:
            return 0
    if a.json:
        _print(keys, True)
        return 0
    if not keys:
        print("No keys in %s. Create one: odoo_sh.py keys --generate odoo_sh" % ", ".join(S.key_dirs(a.dir)))
        return 0
    for k in keys:
        print("%s  %-20s %s  private=%s passphrase=%s  %s" % (
            k["fingerprint"] or "(no .pub)", k["type"] or "?", k["private_key_path"],
            "yes" if k["has_private_key"] else "MISSING",
            {True: "yes", False: "no", None: "?"}[k["passphrase"]], k["comment"] or ""))
        if k.get("fingerprint_md5"):
            print("    Odoo.sh shows it as: %s%s" % (
                k["fingerprint_md5"],
                "" if k["type"] in S.ODOO_SH_KEY_TYPES else "   (type not accepted by Odoo.sh: use ed25519 or rsa)"))
    print("\nShow the line to paste: odoo_sh.py keys --print <private key path>")
    print("Find the key Odoo.sh already lists: odoo_sh.py keys --match <fingerprint from Odoo.sh>")
    if S.is_wsl():
        print("WSL: a key under /mnt/c must be copied to ~/.ssh and chmod 600 before ssh accepts it.")
    return 0


def _fields(a):
    f = {"project": a.project, "branch": a.branch, "role": a.role, "url": a.url,
         "ssh_user": a.ssh_user, "host": a.host, "port": a.port, "proxy_jump": a.proxy_jump,
         "ssh_binary": a.ssh_binary, "connect_timeout": a.connect_timeout,
         "command_timeout": a.command_timeout, "src_dir": a.src_dir, "logs_dir": a.logs_dir}
    if a.ssh:
        f.update(C.parse_ssh_address(a.ssh))
    if a.ssh_option:
        f["ssh_options"] = a.ssh_option
    if a.agent:
        f["key"] = ""
    elif a.key:
        ki = S.key_info(a.key)
        if not ki["exists"]:
            raise C.ConfigError("%s does not exist" % ki["path"])
        if not ki["private"] and not ki["path"].endswith(".pub"):
            raise C.ConfigError("%s is neither a private key nor a .pub file" % ki["path"])
        f["key"] = ki["path"].replace("\\", "/")
    for field in a.clear or []:
        if field not in CLEARABLE:
            raise C.ConfigError("--clear accepts: %s" % ", ".join(CLEARABLE))
        f[field] = ""
    return f


def cmd_add(a, must_exist=False):
    doc = C.load()
    if must_exist and a.name not in doc["profiles"]:
        raise C.ConfigError("unknown profile %r (known: %s); use add to create it"
                            % (a.name, ", ".join(sorted(doc["profiles"])) or "none"))
    fields = _fields(a)
    if a.path:
        cur = (doc["profiles"].get(a.name) or {}).get("paths") or []
        fields["paths"] = sorted(set(cur + [os.path.abspath(p) for p in a.path]))
    prof = C.upsert(a.name, fields)
    print("saved profile %s in %s (role %s, allow: %s)" % (a.name, C.path(), prof["role"], ", ".join(prof["allow"])))
    print("next: odoo_sh.py doctor %s" % a.name)
    return 0


def cmd_allow(a):
    prof = C.set_allow(a.name, ["read"] + a.actions, a.approved_by)
    print("%s now allows: %s" % (a.name, ", ".join(prof["allow"])))
    if prof.get("role") == "prod" and len(prof["allow"]) > 1:
        print("role prod: each of those actions still needs the developer's yes on that call")
    return 0


def cmd_doctor(a):
    name, prof = C.pick(a.name)
    out = S.doctor(name, dict(prof, _name=name))
    _print(out, a.json)
    return 0 if out.get("ok") else 1


def cmd_run(a):
    import sh_tools as T
    args = {"profile": a.profile, "timeout_s": a.timeout}
    fn = {"commit": T.t_commit, "health": T.t_health, "logs": T.t_logs, "modules": T.t_modules}[a.action]
    if a.action == "logs":
        args.update(file=a.file, lines=a.lines, grep=a.grep, since=a.since, errors_only=a.errors_only,
                    ignore_case=a.ignore_case, list_files=a.list)
    if a.action == "modules":
        args.update(names=a.names or None, state=a.state)
    print(fn({k: v for k, v in args.items() if v not in (None, False)}))
    return 0


def _profile_options(sp):
    for f in ("project", "branch", "url", "key", "ssh-user", "host", "proxy-jump", "ssh-binary",
              "src-dir", "logs-dir"):
        sp.add_argument("--" + f)
    sp.add_argument("--ssh", metavar="ADDRESS", help="paste the ssh command or user@host Odoo.sh shows for the build")
    sp.add_argument("--agent", action="store_true", help="no key file: use the keys ssh-agent offers")
    sp.add_argument("--role", choices=C.ROLES)
    sp.add_argument("--port", type=int)
    sp.add_argument("--connect-timeout", type=int)
    sp.add_argument("--command-timeout", type=int)
    sp.add_argument("--ssh-option", action="append", metavar="Key=Value")
    sp.add_argument("--path", action="append", help="bind the profile to a project folder")
    sp.add_argument("--clear", action="append", metavar="FIELD", help="remove an override")


def main(argv=None):
    p = argparse.ArgumentParser(prog="odoo_sh.py", description="Odoo.sh SSH profiles, doctor and reads")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-resolve", action="store_true", help="status without contacting the builds")
    sub = p.add_subparsers(dest="cmd")
    k = sub.add_parser("keys")
    k.add_argument("--print", metavar="PATH")
    k.add_argument("--generate", metavar="NAME")
    k.add_argument("--type", choices=["ed25519", "rsa"], default="ed25519",
                   help="Odoo.sh accepts only ssh-ed25519 and ssh-rsa keys")
    k.add_argument("--match", metavar="FINGERPRINT",
                   help="the fingerprint Odoo.sh shows under Profile > SSH keys > Active keys")
    k.add_argument("--passphrase-prompt", action="store_true")
    k.add_argument("--dir")
    for n in ("add", "edit"):
        sp = sub.add_parser(n)
        sp.add_argument("name")
        _profile_options(sp)
    al = sub.add_parser("allow")
    al.add_argument("name")
    al.add_argument("actions", nargs="*", choices=list(C.WRITE_ACTIONS))
    al.add_argument("--approved-by")
    for n in ("deny", "default", "remove", "show"):
        sub.add_parser(n).add_argument("name")
    sub.add_parser("list")
    d = sub.add_parser("doctor")
    d.add_argument("name", nargs="?")
    r = sub.add_parser("run")
    r.add_argument("action", choices=["commit", "logs", "modules", "health"])
    r.add_argument("--profile")
    r.add_argument("--timeout", type=int)
    r.add_argument("--file", default="odoo", help="odoo, install, pip or a file name in the logs folder")
    r.add_argument("--list", action="store_true", help="list the files in the logs folder")
    r.add_argument("--lines", type=int)
    r.add_argument("--grep")
    r.add_argument("--since")
    r.add_argument("--errors-only", action="store_true")
    r.add_argument("--ignore-case", action="store_true")
    r.add_argument("--names", nargs="*")
    r.add_argument("--state")
    a = p.parse_args(argv)
    try:
        if a.cmd is None:
            return cmd_status(a, resolve=not a.no_resolve)
        if a.cmd == "list":
            return cmd_status(a, resolve=False)
        if a.cmd == "show":
            return cmd_status(a, resolve=not a.no_resolve, only=a.name)
        if a.cmd == "keys":
            return cmd_keys(a)
        if a.cmd in ("add", "edit"):
            return cmd_add(a, must_exist=a.cmd == "edit")
        if a.cmd == "allow":
            return cmd_allow(a)
        if a.cmd == "deny":
            prof = C.set_allow(a.name, ["read"])
            print("%s is read-only: %s" % (a.name, ", ".join(prof["allow"])))
            return 0
        if a.cmd == "default":
            C.set_default(a.name)
            print("default profile: %s" % a.name)
            return 0
        if a.cmd == "remove":
            C.remove(a.name)
            print("removed %s" % a.name)
            return 0
        if a.cmd == "doctor":
            return cmd_doctor(a)
        if a.cmd == "run":
            return cmd_run(a)
    except C.ConfigError as e:
        print("refused: %s" % e, file=sys.stderr)
        return 1
    except S.ShError as e:
        _print(e.as_dict(), a.json)
        return 1
    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
