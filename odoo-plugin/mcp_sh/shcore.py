"""Odoo.sh over SSH: build resolution, the ssh runner, the doctor, actions and redaction.

Odoo.sh has no API token for builds or logs. The only programmatic access is SSH to a
build, with a key the developer added to their Odoo.sh profile. A build's SSH user and
host carry its build id, which changes on every rebuild, so the build is resolved on
EVERY call and never cached:

    POST <url>/web/database/list            -> ["<project>-<branch>-<buildid>"]
    ssh <buildid>@<project>-<branch>-<buildid>.dev.odoo.com

Network seams (`http_post`, `resolve_host`, `tcp_probe`, `run_process`) are module-level
functions so the tests replace them; nothing here needs a network to be unit-tested.

Remote work is a fixed script built here from validated arguments and sent on stdin to
`bash -s` - no caller text is ever spliced into a shell command unquoted.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(HERE), "mcp"))

import shconfig as C  # noqa: E402
from guards import redact as _redact_values  # noqa: E402  (the data MCP's redaction helper)

CONNECT_TIMEOUT = 10
PROBE_TIMEOUT = 8
HTTP_TIMEOUT = 15
CMD_TIMEOUT_DEFAULT, CMD_TIMEOUT_MAX = 60, 300
OUTPUT_MAX = 200_000
LOGS_DIR = "~/logs"        # per-profile override: logs_dir
SRC_DIR = "~/src/user"     # per-profile override: src_dir
LOG_ALIASES = {"odoo": "odoo.log", "install": "install.log", "pip": "pip.log"}
LOG_FILES = LOG_ALIASES    # kept for callers that list the aliases
CONTROL_HOST = ("github.com", 22)
SECRET_MARK = "__ODOOSH_SECRET__ "
MODULE_RE = re.compile(r"^[a-z0-9_]{1,100}$")
SINCE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$")
JOB_RE = re.compile(r"^(update|restart)-\d{8}T\d{6}$")


class ShError(Exception):
    """A classified failure: `cls` is the doctor class, `fix` the actionable steps."""

    def __init__(self, cls, message, fix=None, **extra):
        super().__init__(message)
        self.cls, self.message, self.fix, self.extra = cls, message, list(fix or []), extra

    def as_dict(self):
        out = {"ok": False, "result": self.cls, "message": self.message, "fix": self.fix}
        out.update(self.extra)
        return out


# ------------------------------------------------------------------------------------
# Redaction - exact values (the shared guards.redact) plus patterns for log text
# ------------------------------------------------------------------------------------

MASK = "***REDACTED***"
_TEXT_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
     lambda m: "[REDACTED PRIVATE KEY]"),
    (re.compile(r"(?i)\b([\w.-]*(?:passw(?:or)?d|passwd|secret|token|api[_-]?key|apikey|access[_-]?key|"
                r"private[_-]?key|client[_-]?secret)[\w.-]*)(\"?\s*[=:]\s*\"?)([^\s,;&\"'<>]+)"),
     lambda m: m.group(1) + m.group(2) + MASK),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), lambda m: m.group(1) + " " + MASK),
    (re.compile(r"(\b[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(@)"),
     lambda m: m.group(1) + MASK + m.group(3)),
    (re.compile(r"(?i)([?&](?:access_token|token|api_key|apikey|key|password|secret|signature|sig)=)([^&\s#\"']+)"),
     lambda m: m.group(1) + MASK),
]


def redact_text(text: str, secrets=()) -> str:
    """Known secret values first (exact match, guards.redact), then patterns."""
    vals = [s for s in secrets if isinstance(s, str) and s.strip() and s.strip().lower() not in
            ("false", "none", "true", "null")]
    text = _redact_values(text, vals)
    for rx, repl in _TEXT_PATTERNS:
        text = rx.sub(repl, text)
    return text


def split_secrets(stdout: str):
    """Strip the SECRET_MARK lines a remote script printed; return (text, secrets)."""
    keep, secrets = [], []
    for line in stdout.splitlines(True):
        if line.startswith(SECRET_MARK):
            try:
                secrets.append(base64.b64decode(line[len(SECRET_MARK):].strip()).decode("utf-8", "replace"))
            except Exception:
                pass
        else:
            keep.append(line)
    return "".join(keep), secrets


# Remote prelude: values of secret-looking keys in odoo.conf files and the environment,
# base64-encoded on marked lines. They travel to this process only, are used to scrub the
# output, and are removed before anything is returned.
SECRETS_PRELUDE = r"""
__odoosh_secret() { while IFS= read -r v; do [ -n "$v" ] && printf '__ODOOSH_SECRET__ %s\n' "$(printf %s "$v" | base64 | tr -d '\n')"; done; }
for c in "${ODOO_RC:-}" "$HOME/.odoorc" "$HOME/.config/odoo/odoo.conf" /etc/odoo/odoo.conf "$HOME/src/odoo.conf"; do
  [ -n "$c" ] && [ -r "$c" ] && sed -n -E 's/^[[:space:]]*[A-Za-z_]*(pass|passwd|password|secret|token|key)[A-Za-z_]*[[:space:]]*=[[:space:]]*(.+)$/\2/p' "$c" | __odoosh_secret
done
env | sed -n -E 's/^[A-Za-z_]*(PASS|SECRET|TOKEN|KEY)[A-Za-z_]*=(.+)$/\2/p' | __odoosh_secret
"""


# ------------------------------------------------------------------------------------
# Network seams (replaced in tests)
# ------------------------------------------------------------------------------------

def http_post(url: str, body: dict, timeout: int = HTTP_TIMEOUT):
    """Return (status, parsed_json_or_None). Raises OSError/URLError on network failure."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "odoo-plugin-sh/1"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read(1_000_000)
            status = resp.status
    except urllib.error.HTTPError as e:
        return e.code, None
    try:
        return status, json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return status, None


def resolve_host(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None)
        return True
    except socket.gaierror:
        return False


def tcp_probe(host: str, port: int, timeout: float = PROBE_TIMEOUT) -> str:
    """'open' | 'refused' | 'timeout' | 'unreachable' | 'dns'."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "open"
    except ConnectionRefusedError:
        return "refused"
    except socket.timeout:
        return "timeout"
    except socket.gaierror:
        return "dns"
    except OSError:
        return "unreachable"


def run_process(argv, stdin_text: str, timeout: int):
    """Return (rc, stdout, stderr); rc None means timed out. Raises FileNotFoundError."""
    try:
        p = subprocess.run(argv, input=stdin_text.encode("utf-8"), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or b"").decode("utf-8", "replace"), (e.stderr or b"").decode("utf-8", "replace")
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


# ------------------------------------------------------------------------------------
# Keys (paths only; private key bytes never leave this module)
# ------------------------------------------------------------------------------------

def expand(p: str) -> str:
    return os.path.abspath(os.path.expandvars(os.path.expanduser(p)))


def key_info(key_path: str) -> dict:
    """{exists, private, encrypted, public_key, fingerprint, type, comment}. Never returns
    private key material; public_key is the .pub line meant to be pasted into Odoo.sh."""
    p = expand(key_path)
    info = {"path": p, "exists": os.path.isfile(p), "private": False, "encrypted": None,
            "public_key": None, "fingerprint": None, "fingerprint_md5": None, "type": None, "comment": None}
    if not info["exists"]:
        return info
    try:
        with open(p, "rb") as fh:
            head = fh.read(65536).decode("ascii", "replace")
    except OSError:
        return info
    if "PRIVATE KEY-----" in head:
        info["private"] = True
        if "BEGIN OPENSSH PRIVATE KEY" in head:
            body = "".join(l for l in head.splitlines() if l and not l.startswith("-----"))
            try:
                blob = base64.b64decode(body + "===")
                magic = b"openssh-key-v1\x00"
                if blob.startswith(magic):
                    (n,) = struct.unpack(">I", blob[len(magic):len(magic) + 4])
                    cipher = blob[len(magic) + 4:len(magic) + 4 + n].decode("ascii", "replace")
                    info["encrypted"] = cipher != "none"
            except Exception:
                info["encrypted"] = None
        else:
            info["encrypted"] = "ENCRYPTED" in head
    del head
    pub = p + ".pub"
    if os.path.isfile(pub):
        try:
            with open(pub, encoding="utf-8", errors="replace") as fh:
                line = fh.read().strip().splitlines()[0]
            info.update(parse_public(line))
        except (OSError, IndexError):
            pass
    return info


def parse_public(line: str) -> dict:
    parts = line.split()
    if len(parts) < 2 or not parts[0].startswith(("ssh-", "ecdsa-", "sk-")):
        return {}
    try:
        blob = base64.b64decode(parts[1])
    except Exception:
        return {}
    fp = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    digest = hashlib.md5(blob).hexdigest()   # a display fingerprint, not a security use
    md5 = ":".join(digest[i:i + 2] for i in range(0, 32, 2))
    return {"public_key": " ".join(parts[:3]) if len(parts) > 2 else " ".join(parts[:2]),
            "type": parts[0], "comment": " ".join(parts[2:]) or None, "fingerprint": fp,
            "fingerprint_md5": md5}


# Odoo.sh accepts only these two key types (its SSH keys page says so).
ODOO_SH_KEY_TYPES = ("ssh-ed25519", "ssh-rsa")


def norm_fingerprint(text) -> str:
    """A fingerprint as the user pasted it, reduced to a comparable form. Odoo.sh shows the
    MD5 form (0c:87:...); ssh-keygen and GitHub show SHA256:..."""
    t = str(text or "").strip()
    if t.upper().startswith("SHA256:"):
        return "SHA256:" + t[7:].rstrip("=")
    if t.upper().startswith("MD5:"):
        t = t[4:]
    return t.replace(":", "").replace(" ", "").lower()


def match_keys(fingerprint, keys) -> list:
    """The keys in `keys` (from list_keys) whose MD5 or SHA256 fingerprint is `fingerprint`."""
    want = norm_fingerprint(fingerprint)
    if not want:
        return []
    return [k for k in keys if want in (norm_fingerprint(k.get("fingerprint")),
                                        norm_fingerprint(k.get("fingerprint_md5")))]


_NOT_KEYS = ("known_hosts", "known_hosts.old", "config", "authorized_keys", "authorized_keys2", "environment")


def is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8", errors="replace") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return False


def key_dirs(extra=None) -> list:
    """Where to look for keys on this platform: ~/.ssh, and under WSL the Windows
    profiles' .ssh folders too (their files need copying to ~/.ssh with chmod 600 before
    ssh accepts them; the doctor says so)."""
    dirs = [expand(extra)] if extra else [expand("~/.ssh")]
    if not extra and is_wsl() and os.path.isdir("/mnt/c/Users"):
        for u in sorted(os.listdir("/mnt/c/Users")):
            cand = os.path.join("/mnt/c/Users", u, ".ssh")
            if os.path.isdir(cand) and os.access(cand, os.R_OK):
                dirs.append(cand)
    return dirs


def list_keys(ssh_dir=None) -> list:
    """Every key pair or lone private key in the key folders, any type and any file name."""
    out = []
    for d in key_dirs(ssh_dir):
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        seen = set()
        for name in names:
            full = os.path.join(d, name)
            if name in _NOT_KEYS or not os.path.isfile(full):
                continue
            if name.endswith(".pub"):
                priv = full[:-4]
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        pub = parse_public(fh.read().strip())
                except OSError:
                    continue
                if not pub:
                    continue
                info = key_info(priv) if os.path.isfile(priv) else {"exists": False, "encrypted": None}
                seen.add(priv)
                out.append({"private_key_path": priv, "has_private_key": info.get("exists", False),
                            "passphrase": info.get("encrypted"), "type": pub["type"], "comment": pub["comment"],
                            "fingerprint": pub["fingerprint"], "fingerprint_md5": pub["fingerprint_md5"],
                            "public_key": pub["public_key"]})
        for name in names:   # private keys without a .pub beside them
            full = os.path.join(d, name)
            if name.endswith(".pub") or name in _NOT_KEYS or full in seen or not os.path.isfile(full):
                continue
            try:
                if os.path.getsize(full) > 65536:
                    continue
            except OSError:
                continue
            info = key_info(full)
            if info["private"]:
                out.append({"private_key_path": full, "has_private_key": True, "passphrase": info["encrypted"],
                            "type": None, "comment": "no .pub beside it (ssh-keygen -y -f <key> > <key>.pub)",
                            "fingerprint": None, "fingerprint_md5": None, "public_key": None})
    return out


def find_ssh(prof=None) -> str:
    """The ssh client: the profile's ssh_binary, ODOO_SH_SSH, then per platform.
    Windows: Windows OpenSSH first (it uses the Windows ssh-agent service), then any ssh on
    PATH (Git Bash, MSYS2, Cygwin). macOS, Linux, WSL: ssh on PATH, then the usual folders."""
    explicit = (prof or {}).get("ssh_binary") or os.environ.get("ODOO_SH_SSH")
    if explicit:
        return expand(explicit) if os.path.sep in explicit or "/" in explicit else explicit
    if sys.platform == "win32":
        root = os.environ.get("SystemRoot", r"C:\Windows")
        for sub in ("System32", "Sysnative"):
            cand = os.path.join(root, sub, "OpenSSH", "ssh.exe")
            if os.path.isfile(cand):
                return cand
    found = shutil.which("ssh")
    if found:
        return found
    for cand in ("/usr/bin/ssh", "/usr/local/bin/ssh", "/opt/homebrew/bin/ssh",
                 r"C:\Program Files\Git\usr\bin\ssh.exe", r"C:\Program Files\OpenSSH\ssh.exe"):
        if os.path.isfile(cand):
            return cand
    raise ShError("ssh_missing", "no ssh client found",
                  ["Windows: Settings > System > Optional features > add 'OpenSSH Client' (or install Git for Windows)",
                   "macOS: ssh ships with the system; Linux/WSL: install openssh-client",
                   "or point the profile at one: odoo_sh.py add <profile> --ssh-binary <path>"])


def agent_has_keys(prof=None) -> bool:
    """True when the ssh-agent that the chosen ssh client uses holds at least one key."""
    try:
        try:
            ssh = find_ssh(prof)
            add = os.path.join(os.path.dirname(ssh), "ssh-add" + (".exe" if ssh.lower().endswith(".exe") else ""))
            if not os.path.isfile(add):
                add = shutil.which("ssh-add") or "ssh-add"
        except ShError:
            add = shutil.which("ssh-add") or "ssh-add"
        p = subprocess.run([add, "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# ------------------------------------------------------------------------------------
# Build resolution (every call, never cached)
# ------------------------------------------------------------------------------------

def _fmt(template: str, **kw) -> str:
    try:
        return template.format(**kw)
    except (KeyError, IndexError, ValueError):
        raise ShError("config_error", "template %r uses an unknown placeholder; allowed: "
                      "{project} {branch} {build} {db}" % template)


def pinned(prof: dict) -> bool:
    """host and ssh_user both fixed (no {placeholders}): no resolution possible or needed."""
    h, u = prof.get("host"), prof.get("ssh_user")
    return bool(h and u and "{" not in h and "{" not in u)


def list_databases(url: str) -> list:
    host = urlparse(url).hostname or ""
    try:
        status, doc = http_post(url.rstrip("/") + "/web/database/list",
                                {"jsonrpc": "2.0", "method": "call", "params": {}, "id": 1})
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.gaierror) or not resolve_host(host):
            raise ShError("url_dns_failure", "the build URL host %s does not resolve" % host,
                          ["check the url in the profile (copy it from the branch in Odoo.sh)",
                           "check this machine's DNS / VPN"])
        raise ShError("url_unreachable", "cannot reach %s over HTTPS: %s" % (url, reason),
                      ["open the url in a browser from this machine", "check proxy/VPN settings"])
    if status in (403, 404) or doc is None:
        raise ShError("db_list_unavailable",
                      "%s/web/database/list answered HTTP %s - this URL does not list databases "
                      "(list_db off or a non-Odoo front)" % (url, status),
                      ["use the branch's own Odoo.sh URL rather than a custom domain",
                       "or pin the build: set host and ssh_user from the branch's SSH tab in Odoo.sh "
                       "(odoo_sh.py add <name> --host ... --ssh-user ...); pins go stale on every rebuild"])
    if isinstance(doc, dict) and doc.get("error"):
        msg = json.dumps(doc["error"])[:300]
        raise ShError("db_list_unavailable", "database listing is disabled on %s: %s" % (url, msg),
                      ["pin host and ssh_user from the branch's SSH tab instead (they go stale on rebuild)"])
    result = doc.get("result") if isinstance(doc, dict) else None
    if not isinstance(result, list):
        raise ShError("db_list_unavailable", "unexpected /web/database/list answer from %s" % url)
    return [d for d in result if isinstance(d, str)]


def pick_build(dbs: list, project: str, branch=None) -> dict:
    """Choose `<project>-<branch>-<buildid>` from a database list (highest build id)."""
    if branch:
        rx = re.compile(r"^%s-(?P<branch>%s)-(?P<build>\d+)$" % (re.escape(project), re.escape(branch)))
    else:
        rx = re.compile(r"^%s-(?P<branch>.+)-(?P<build>\d+)$" % re.escape(project))
    hits = [(m.group("branch"), int(m.group("build")), d) for d in dbs for m in [rx.match(d)] if m]
    if not hits:
        raise ShError("build_not_found",
                      "no database named %s-%s-<buildid> on this URL (it lists: %s)"
                      % (project, branch or "<branch>", ", ".join(dbs[:10]) or "nothing"),
                      ["check the project slug and branch in the profile against Odoo.sh",
                       "a build that is still starting or was just dropped has no database yet - retry in a minute"])
    branches = sorted({h[0] for h in hits})
    if not branch and len(branches) > 1:
        raise ShError("config_error", "the URL serves several branches (%s); set branch in the profile"
                      % ", ".join(branches))
    br, build, db = max(hits, key=lambda h: h[1])
    return {"db": db, "branch": br, "build": str(build)}


def resolve(prof: dict) -> dict:
    """Target for this call: {db, branch, build, user, host, port, proxy_jump, pinned}."""
    if pinned(prof):
        return {"db": None, "branch": prof.get("branch"), "build": None, "user": prof["ssh_user"],
                "host": prof["host"], "port": prof.get("port"), "proxy_jump": prof.get("proxy_jump"),
                "pinned": True}
    b = pick_build(list_databases(prof["url"]), prof["project"], prof.get("branch"))
    kw = dict(project=prof["project"], branch=b["branch"], build=b["build"], db=b["db"])
    host = _fmt(prof.get("host") or "{db}.dev.odoo.com", **kw)
    user = _fmt(prof.get("ssh_user") or "{build}", **kw)
    return dict(b, user=user, host=host, port=prof.get("port"), proxy_jump=prof.get("proxy_jump"), pinned=False)


# ------------------------------------------------------------------------------------
# SSH
# ------------------------------------------------------------------------------------

def known_hosts_file(host: str) -> str:
    d = C.known_hosts_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, re.sub(r"[^A-Za-z0-9._-]", "_", host)).replace("\\", "/")


def ssh_argv(prof: dict, target: dict) -> list:
    """ssh options. With `key`, only that identity is offered (-i + IdentitiesOnly; a .pub
    path works when the agent holds the private half). Without `key`, ssh uses the agent and
    the user's default keys. Prompts are impossible either way (BatchMode)."""
    argv = [find_ssh(prof)]
    if prof.get("key"):
        argv += ["-i", expand(prof["key"]), "-o", "IdentitiesOnly=yes"]
    # The safety options go first: for each option ssh keeps the first value it sees, so a
    # profile's ssh_options can never weaken them.
    argv += ["-o", "BatchMode=yes",
             "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
             "-o", "StrictHostKeyChecking=accept-new",
             "-o", 'UserKnownHostsFile="%s"' % known_hosts_file(target["host"]),
             "-o", "ConnectTimeout=%d" % int(prof.get("connect_timeout") or CONNECT_TIMEOUT),
             "-o", "LogLevel=ERROR"]
    for opt in prof.get("ssh_options") or []:
        if C.SSH_OPTION_RE.match(opt):
            argv += ["-o", opt]
    argv += ["-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2"]
    if target.get("port"):
        argv += ["-p", str(int(target["port"]))]
    if target.get("proxy_jump"):
        argv += ["-J", target["proxy_jump"]]
    argv += ["-l", target["user"], target["host"], "bash", "-s"]
    return argv


def classify_ssh(rc, stderr: str):
    """Map an ssh failure to (class, message). rc None = command timed out."""
    s = stderr or ""
    low = s.lower()
    if rc is None:
        return "ssh_timeout", "the remote command did not finish in time"
    if "could not resolve hostname" in low or "name or service not known" in low:
        return "dns_failure", "the SSH host does not resolve"
    if "connection timed out" in low or "operation timed out" in low:
        return "tcp_timeout", "the TCP connection to the SSH port timed out"
    if "connection refused" in low:
        return "tcp_refused", "the SSH port refused the connection"
    if "unprotected private key" in low or "bad permissions" in low:
        return "key_permissions", "ssh refuses the key file because other accounts can read it"
    if "host identification has changed" in low or "host key verification failed" in low:
        return "host_key_changed", "the host key differs from the one recorded for this host"
    if "no matching host key type" in low or "no matching key exchange" in low or "no mutual signature" in low \
            or "no matching cipher" in low:
        return "algorithm_mismatch", "the client and the server share no host-key, key-exchange or signature algorithm"
    if "incorrect passphrase" in low or "invalid format" in low or "load key" in low:
        return "key_unusable", "ssh could not load the private key (passphrase-protected without an agent, or not a key)"
    if "permission denied" in low:
        return "auth_refused", "the server refused the key"
    if rc == 255:
        return "ssh_error", (s.strip().splitlines() or ["ssh failed"])[-1][:300]
    return None, None


def ssh_run(prof: dict, target: dict, script: str, timeout=None) -> dict:
    """Run `script` on the build. Raises ShError for connection/auth failures.
    Timeout: the call's, else the profile's command_timeout, else the default."""
    argv = ssh_argv(prof, target)
    timeout = timeout or prof.get("command_timeout") or CMD_TIMEOUT_DEFAULT
    timeout = max(5, min(int(timeout), CMD_TIMEOUT_MAX))
    try:
        rc, out, err = run_process(argv, script, timeout)
    except FileNotFoundError:
        raise ShError("ssh_missing", "cannot run %s" % argv[0])
    cls, msg = classify_ssh(rc, err)
    if cls:
        raise ShError(cls, "%s (%s@%s)" % (msg, target["user"], target["host"]), fix_for(cls, prof, target))
    text, secrets = split_secrets(out)
    if len(text) > OUTPUT_MAX:
        text = "[... output cut to the last %d characters ...]\n" % OUTPUT_MAX + text[-OUTPUT_MAX:]
    return {"rc": rc, "stdout": redact_text(text, secrets), "stderr": redact_text(err[-4000:], secrets)}


def fix_for(cls: str, prof: dict, target: dict) -> list:
    name_hint = prof.get("_name") or "<profile>"
    if cls == "auth_refused":
        fx = ["check that the profile uses the key Odoo.sh lists: copy the fingerprint from Odoo.sh "
              "(avatar > Profile > SSH keys > Active keys) and run odoo_sh.py keys --match <fingerprint>; "
              "if it names another key: odoo_sh.py edit %s --key <that key>" % name_hint,
              "or add this key's PUBLIC half in Odoo.sh: avatar > Profile > SSH keys "
              "(odoo_sh.py keys --print <key> shows it), then retry - no rebuild needed",
              "your Odoo.sh user also needs access to the project (a collaborator on it)",
              "if the key has a passphrase, load it into ssh-agent first (ssh-add <key>): BatchMode never prompts",
              "compare user@host with the SSH command the branch shows in Odoo.sh; if they differ, paste it: "
              "odoo_sh.py add %s --ssh \"<the ssh command Odoo.sh shows>\"" % name_hint]
        ki = key_info(prof["key"]) if prof.get("key") else {}
        if (ki.get("type") or "").endswith("ed25519"):
            fx.append("some Odoo.sh users report Ed25519 keys refused while RSA works: try an RSA key "
                      "(odoo_sh.py keys --generate <name> --type rsa)")
        return fx
    return {
        "dns_failure": ["check the host override in the profile (odoo_sh.py add %s --clear host)" % name_hint],
        "tcp_timeout": ["run the doctor: it tells a blocked network apart from a dead host"],
        "tcp_refused": ["run the doctor; check a port override in the profile"],
        "key_permissions": ["Windows: icacls <key> /inheritance:r /grant:r \"%USERNAME%:R\"",
                            "macOS/Linux: chmod 600 <key>",
                            "WSL with a key under /mnt/c: copy it to ~/.ssh, chmod 600 it, and point the profile there"],
        "algorithm_mismatch": ["for a server that offers only ssh-rsa: odoo_sh.py add %s --ssh-option "
                               "HostKeyAlgorithms=+ssh-rsa --ssh-option PubkeyAcceptedAlgorithms=+ssh-rsa" % name_hint,
                               "or update the ssh client"],
        "host_key_changed": ["delete the recorded host key: %s (builds are recreated, so a changed key on a "
                             "reused hostname can be legitimate; check the build in Odoo.sh first)"
                             % known_hosts_file(target.get("host") or "host")],
        "key_unusable": ["ssh-add <key> to load a passphrase-protected key into the agent",
                         "or point the profile at another key: odoo_sh.py add %s --key <path>" % name_hint],
        "ssh_timeout": ["raise timeout_s, narrow the request (fewer lines, a since filter)"],
    }.get(cls, [])


# ------------------------------------------------------------------------------------
# Doctor
# ------------------------------------------------------------------------------------

IP_LOOKUP_URLS = ("https://api.ipify.org", "https://checkip.amazonaws.com")
_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def public_ip(timeout: float = 4):
    """This machine's public IPv4 as an IP-echo service sees it, or None. Only used to tell the
    developer which address to put on the Odoo.sh SSH allow-list. The request carries no data.
    ODOO_SH_NO_IP_LOOKUP=1 switches it off."""
    if (os.environ.get("ODOO_SH_NO_IP_LOOKUP") or "").strip().lower() in ("1", "true", "yes", "on"):
        return None
    for url in IP_LOOKUP_URLS:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read(64).decode("ascii", "replace").strip()
            if _IPV4_RE.match(text):
                return text
        except Exception:
            continue
    return None


def local_key_lines(keys=None) -> list:
    """One line per local key in the form Odoo.sh displays, for matching against its list."""
    out = []
    for k in (list_keys() if keys is None else keys):
        if k.get("fingerprint_md5"):
            out.append("%s  %s  %s%s" % (k["fingerprint_md5"], k["private_key_path"], k.get("type") or "?",
                                         "" if k.get("has_private_key") else "  (private half missing)"))
    return out


def doctor(name: str, prof: dict) -> dict:
    """Walk config > key > ssh client > URL/build > DNS > TCP > SSH auth and stop at the
    first failure with one distinct, actionable class."""
    steps = []

    def step(label, ok, detail=""):
        steps.append({"step": label, "ok": ok, "detail": detail})

    def fail(err: ShError):
        out = err.as_dict()
        out.update({"profile": name, "steps": steps})
        return out

    agent_fix = ["Windows (OpenSSH): Get-Service ssh-agent | Set-Service -StartupType Automatic; "
                 "Start-Service ssh-agent; ssh-add <key>",
                 "macOS: ssh-add --apple-use-keychain <key>",
                 "Linux, WSL, Git Bash: eval \"$(ssh-agent -s)\" && ssh-add <key>",
                 "the passphrase is typed into ssh-add in your own terminal, never into this chat"]
    if not prof.get("key"):
        if not agent_has_keys(prof):
            step("key", False, "agent mode, agent empty")
            return fail(ShError("no_key", "the profile names no key and no ssh-agent holds one", agent_fix + [
                "or name a key file: odoo_sh.py add %s --key <path>" % name]))
        step("key", True, "keys offered by ssh-agent")
    else:
        ki = key_info(prof["key"])
        if not ki["exists"]:
            step("key", False, ki["path"])
            return fail(ShError("key_missing", "the key file %s does not exist" % ki["path"],
                                ["odoo_sh.py keys lists the keys on this machine",
                                 "odoo_sh.py add %s --key <path to the private key>" % name]))
        if not ki["private"]:
            if not ki["path"].endswith(".pub") or not agent_has_keys(prof):
                step("key", False, "not a private key")
                return fail(ShError("key_not_private",
                                    "%s is not a private key; a .pub path only works while ssh-agent holds the "
                                    "private half" % prof["key"],
                                    ["odoo_sh.py add %s --key <private key path>" % name] + agent_fix))
            step("key", True, "public key, private half in ssh-agent")
        elif ki["encrypted"] and not agent_has_keys(prof):
            step("key", False, "passphrase-protected, no agent")
            return fail(ShError("key_encrypted_no_agent",
                                "the key has a passphrase and no ssh-agent holds it; BatchMode never prompts",
                                [f.replace("<key>", ki["path"]) for f in agent_fix]))
        else:
            step("key", True, "%s %s%s" % (
                ki.get("type") or "key", ki.get("fingerprint") or "(no .pub beside it)",
                "  (Odoo.sh shows it as %s)" % ki["fingerprint_md5"] if ki.get("fingerprint_md5") else ""))
            if ki.get("type") and ki["type"] not in ODOO_SH_KEY_TYPES:
                step("key type", False, "%s - Odoo.sh accepts only ssh-ed25519 and ssh-rsa" % ki["type"])
    try:
        step("ssh client", True, find_ssh(prof))
    except ShError as e:
        step("ssh client", False)
        return fail(e)
    try:
        target = resolve(prof)
    except ShError as e:
        step("build", False, e.message)
        return fail(e)
    step("build", True, "pinned %s@%s" % (target["user"], target["host"]) if target["pinned"]
         else "%s -> %s@%s" % (target["db"], target["user"], target["host"]))

    host, port = target["host"], int(target.get("port") or 22)
    if not resolve_host(host):
        step("dns", False, host)
        url_ok = resolve_host(urlparse(prof["url"]).hostname or "")
        if url_ok and not target["pinned"] and not prof.get("host"):
            return fail(ShError("stale_build",
                                "%s does not resolve although %s does: build %s is gone or not yet "
                                "published (rebuilt, dropped, or still starting)" % (host, prof["url"], target["build"]),
                                ["retry in a minute; check the branch's current build in Odoo.sh",
                                 "if the branch's SSH tab shows a different host pattern, set it: "
                                 "odoo_sh.py add %s --host '<pattern with {build}>'" % name]))
        return fail(ShError("dns_failure", "the SSH host %s does not resolve" % host,
                            ["check the host override in the profile (or remove it)", "check DNS / VPN"]))
    step("dns", True, host)

    if target.get("proxy_jump"):
        jump = target["proxy_jump"].split(",")[0]
        jhost = jump.split("@")[-1]
        jport = 22
        if re.match(r"^[^:\[\]]+:\d+$", jhost):
            jhost, jport = jhost.rsplit(":", 1)[0], int(jhost.rsplit(":", 1)[1])
        r = tcp_probe(jhost, jport)
        step("tcp (jump host %s:%s)" % (jhost, jport), r == "open", r)
        if r != "open":
            return fail(ShError("tcp_timeout" if r in ("timeout", "unreachable") else "tcp_refused",
                                "the ProxyJump host %s:%s is %s from this machine" % (jhost, jport, r),
                                ["check proxy_jump in the profile", "ssh to the jump host by hand once"]))
    else:
        r = tcp_probe(host, port)
        step("tcp %s:%s" % (host, port), r == "open", r)
        if r != "open":
            https = tcp_probe(host, 443)
            ctl = tcp_probe(*CONTROL_HOST)
            ctx = "443 on the same host is %s; %s:%s is %s" % (https, CONTROL_HOST[0], CONTROL_HOST[1], ctl)
            fixes = ["route SSH through a host that can reach Odoo.sh on port %s: "
                     "odoo_sh.py add %s --proxy-jump user@jumphost" % (port, name),
                     "or, if your network forwards another port to it, odoo_sh.py add %s --port <n>" % name,
                     "or retry from another network (VPN on/off, a phone hotspot) to confirm"]
            if r == "refused":
                return fail(ShError("tcp_refused", "TCP %s on %s was refused (%s)" % (port, host, ctx), fixes,
                                    https=https, control=ctl))
            if https == "open":
                seen = "TCP %s to %s timed out while 443 on the same host connects%s" % (
                    port, host, " and %s:%s works" % CONTROL_HOST if ctl == "open" else "")
                role = prof.get("role") or "prod"
                ip = public_ip()
                shown = ip or "this machine's public IP (look it up, for example at https://api.ipify.org)"
                allow_fix = ("in Odoo.sh open the project > Settings > Firewall > \"Allow SSH to production and "
                             "staging builds from specific IP addresses\" and add %s (IPv4, up to 10 addresses; "
                             "it takes effect within about 5 minutes), then run the doctor again. A project "
                             "admin has to do it" % shown)
                if role in ("stage", "prod"):
                    msg = ("%s: most likely the project's Odoo.sh SSH allow-list does not include %s. Odoo.sh "
                           "silently drops SSH to production and staging builds from addresses that are not on "
                           "that list, while HTTPS keeps working. If the address is already listed, the network "
                           "between this machine and Odoo.sh drops SSH (firewall, ISP or corporate rule for that "
                           "destination). Either way your key and the build are not the problem"
                           % (seen, shown))
                    fixes = [allow_fix] + fixes
                else:
                    msg = ("%s: the network between this machine and Odoo.sh drops SSH (firewall, ISP or "
                           "corporate rule for that destination) - your key and the build are not the problem. "
                           "The Odoo.sh SSH allow-list (project Settings > Firewall) covers production and "
                           "staging builds; development builds are normally not behind it"
                           % seen)
                    fixes = fixes + ["if this build is really a staging or production build, set the role "
                                     "(odoo_sh.py edit %s --role stage) and check the allow-list: %s"
                                     % (name, allow_fix)]
                return fail(ShError("tcp_timeout", msg, fixes, https=https, control=ctl, public_ip=ip))
            else:
                msg = "TCP %s to %s timed out and 443 is %s too: the host is unreachable from here" % (port, host, https)
            return fail(ShError("tcp_timeout", msg, fixes, https=https, control=ctl))

    probe = SECRETS_PRELUDE + "echo __ODOOSH_OK__\ngit -C %s log -1 --format='%%H %%cI %%s' 2>/dev/null || true\n" % (
        rdir(prof.get("src_dir") or SRC_DIR))
    try:
        res = ssh_run(prof, target, probe, timeout=30)
    except ShError as e:
        step("ssh auth", False, e.cls)
        if e.cls == "auth_refused" and not target["pinned"]:
            try:   # the build may have been replaced between resolution and connect
                again = resolve(prof)
                if again.get("build") != target.get("build"):
                    return fail(ShError("stale_build", "build %s was replaced by %s during the check"
                                        % (target["build"], again["build"]), ["run the doctor again"]))
            except ShError:
                pass
        if e.cls == "auth_refused":
            lines = local_key_lines()
            if lines:
                e.extra["local_keys"] = lines
                e.fix.insert(0, "keys on this machine, with the fingerprint Odoo.sh shows under avatar > Profile > "
                                "SSH keys > Active keys (a key \"Imported from GitHub\" is your GitHub key) - the "
                                "profile must use the one listed there:\n      " + "\n      ".join(lines))
        return fail(e)
    if "__ODOOSH_OK__" not in res["stdout"]:
        step("ssh auth", False, "no shell")
        return fail(ShError("ssh_error", "connected but the remote shell did not run the probe: %s"
                            % (res["stderr"].strip()[:300] or "no output")))
    commit = res["stdout"].split("__ODOOSH_OK__", 1)[1].strip()
    step("ssh auth", True, "%s@%s" % (target["user"], target["host"]))
    return {"ok": True, "result": "ok", "profile": name, "message": "connected; deployed commit: %s"
            % (commit or "unknown (no git checkout at %s)" % (prof.get("src_dir") or SRC_DIR)),
            "target": target, "steps": steps,
            "fix": []}


# ------------------------------------------------------------------------------------
# Actions (fixed remote scripts from validated arguments)
# ------------------------------------------------------------------------------------

def rdir(d: str) -> str:
    """A validated build-side folder as a double-quoted shell word ('~' -> $HOME)."""
    if not C.DIR_RE.match(d or "") or ".." in d:
        raise ShError("bad_request", "folder %r must be absolute or start with ~/" % d)
    return '"%s"' % (("$HOME" + d[1:]) if d.startswith("~") else d)


def script_commit(src_dir=SRC_DIR) -> str:
    return SECRETS_PRELUDE + (
        "cd %s 2>/dev/null || { echo 'no git checkout at %s'; exit 0; }\n"
        "echo \"branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)\"\n"
        "git log -1 --format='commit: %%H%%nauthor: %%an%%ndate: %%cI%%nsubject: %%s'\n"
        "echo '== working tree (changes on the build itself)'; git status --porcelain 2>/dev/null | head -20\n"
        "echo '== submodules'; git submodule status --recursive 2>/dev/null | head -40\n"
        % (rdir(src_dir), src_dir))


LOG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def script_log_list(logs_dir=LOGS_DIR) -> str:
    return "ls -la --time-style=+'%%F %%T' %s 2>/dev/null || echo 'no folder %s'\n" % (rdir(logs_dir), logs_dir)


def script_logs(file="odoo", lines=200, grep=None, since=None, errors_only=False, pid=None,
                ignore_case=False, logs_dir=LOGS_DIR) -> str:
    """`file`: odoo, install, pip (-> <name>.log) or any file name inside the logs folder."""
    name = LOG_ALIASES.get(file or "odoo", file)
    if not isinstance(name, str) or not LOG_NAME_RE.match(name):
        raise ShError("bad_request", "file must be odoo, install, pip or a file name inside the build's logs "
                                     "folder (list them with list_files=true)")
    lines = max(1, min(int(lines or 200), 3000))
    if since and not SINCE_RE.match(since):
        raise ShError("bad_request", "since must be 'YYYY-MM-DD[ HH:MM[:SS]]' (the build's log time, UTC)")
    if grep is not None:
        if not isinstance(grep, str) or len(grep) > 200:
            raise ShError("bad_request", "grep must be a regex of at most 200 characters")
        try:
            re.compile(grep)
        except re.error as e:
            raise ShError("bad_request", "grep is not a valid regex: %s" % e)
    if pid is not None and not isinstance(pid, int):
        raise ShError("bad_request", "pid must be an integer")
    scan = 400000 if (since or grep or errors_only or pid) else lines
    awk = ("awk -v since=%s -v errs=%s -v pid=%s '"
           "/^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:/ {"
           " keep=1; ts=substr($0,1,19);"
           " if (since!=\"\" && ts<since) keep=0;"
           " if (errs==\"1\" && $4!=\"ERROR\" && $4!=\"CRITICAL\") keep=0;"
           " if (pid!=\"\" && $3!=pid) keep=0 }"
           " keep'" % (shlex.quote(since or ""), "1" if errors_only else "0", shlex.quote(str(pid or ""))))
    pipe = "tail -n %d \"$f\" | %s" % (scan, awk)
    if grep:
        pipe += " | { grep -E %s-e %s || true; }" % ("-i " if ignore_case else "", shlex.quote(grep))
    pipe += " | tail -n %d" % lines
    folder = rdir(logs_dir)
    return SECRETS_PRELUDE + (
        "f=%s/%s\n[ -f \"$f\" ] || { echo \"__NOFILE__ $f\"; ls -1 %s 2>/dev/null; exit 0; }\n"
        "echo \"__SIZE__ $(wc -c < \"$f\") bytes, modified $(date -u -r \"$f\" '+%%F %%T' 2>/dev/null) UTC\"\n"
        "%s\n" % (folder, name, folder, pipe))


def script_modules(db=None, names=None, state=None) -> str:
    names = names or []
    if not isinstance(names, list) or not all(isinstance(n, str) and MODULE_RE.match(n) for n in names):
        raise ShError("bad_request", "modules must be technical names (a-z, 0-9, _)")
    if state not in (None, "", "installed", "all", "to upgrade", "to install", "uninstalled"):
        raise ShError("bad_request", "state must be installed, all, to upgrade, to install or uninstalled")
    where = []
    if names:
        where.append("name in (%s)" % ", ".join("'%s'" % n for n in names))
    if state in (None, "", "installed"):
        where.append("state in ('installed', 'to upgrade', 'to install', 'to remove')")
    elif state != "all":
        where.append("state = '%s'" % state)
    sql = ("select name, coalesce(latest_version, ''), state, to_char(write_date, 'YYYY-MM-DD HH24:MI:SS') "
           "from ir_module_module%s order by name" % (" where " + " and ".join(where) if where else ""))
    dbarg = "-d %s " % shlex.quote(db) if db else ""
    return SECRETS_PRELUDE + "echo 'name|latest_version|state|write_date'\npsql -X -A -t -F '|' %s-c %s\n" % (
        dbarg, shlex.quote(sql))


def script_health() -> str:
    return SECRETS_PRELUDE + (
        "echo '== disk'; df -h \"$HOME\" /tmp 2>/dev/null; du -sh \"$HOME/data/filestore\" 2>/dev/null\n"
        "command -v odoosh-storage >/dev/null 2>&1 && odoosh-storage 2>/dev/null | head -20\n"
        "echo '== load'; uptime; nproc 2>/dev/null\n"
        "echo '== memory'; free -m 2>/dev/null\n"
        "echo '== odoo processes'; ps -eo pid,etimes,rss,pcpu,args --sort=-rss 2>/dev/null"
        " | grep -E '[o]doo|[g]event|[w]orker' | cut -c1-200 | head -30\n"
        "echo '== limits'; grep -hE '^[[:space:]]*(workers|max_cron_threads|limit_time_real|limit_time_cpu|"
        "limit_memory_soft|limit_memory_hard)[[:space:]]*=' \"${ODOO_RC:-/dev/null}\" "
        "\"$HOME/.config/odoo/odoo.conf\" /etc/odoo/odoo.conf 2>/dev/null | head -12\n")


def script_update(job: str, modules: list, db=None) -> str:
    if not modules or not all(isinstance(m, str) and MODULE_RE.match(m) for m in modules):
        raise ShError("bad_request", "modules must be one or more technical names")
    mods = ",".join(modules)
    dbarg = " -d %s" % shlex.quote(db) if db else ""
    # odoo-bin -u ... --stop-after-init is the documented Odoo.sh shell form; odoo-update's
    # argument syntax is not documented, so it is not guessed at here.
    inner = "odoo-bin -u %s%s --stop-after-init --no-http" % (mods, dbarg)
    return _background(job, inner)


def script_restart(job: str) -> str:
    inner = ("if command -v odoosh-restart >/dev/null 2>&1; then odoosh-restart http; "
             "else echo 'no odoosh-restart on this build: restart it from the Odoo.sh branch menu'; exit 3; fi")
    return _background(job, inner)


def _background(job: str, inner: str) -> str:
    log = "$HOME/logs/odoo-sh-mcp-%s.log" % job
    return ("mkdir -p \"$HOME/logs\"\n"
            "nohup sh -c %s > \"%s\" 2>&1 < /dev/null &\n"
            "echo \"__JOB__ %s pid $!\"\n" % (shlex.quote(inner + "; echo \"__EXIT__=$?\""), log, job))


def script_job(job: str, tail: int = 80) -> str:
    if not JOB_RE.match(job or ""):
        raise ShError("bad_request", "job_id looks like update-20261121T101500")
    tail = max(0, min(int(tail or 80), 500))
    return SECRETS_PRELUDE + (
        "f=\"$HOME/logs/odoo-sh-mcp-%s.log\"\n"
        "[ -f \"$f\" ] || { echo '__NOJOB__'; exit 0; }\n"
        "grep -h '^__EXIT__=' \"$f\" | tail -1 || true\n"
        "echo \"__ERRORS__ $(grep -cE ' (ERROR|CRITICAL) ' \"$f\")\"\n"
        "tail -n %d \"$f\"\n" % (job, tail))


SHELL_MAX = 4000


def script_shell(command: str) -> str:
    """A one-off, non-interactive shell command (opt-in action `shell`). It runs as given -
    the gate is the profile opt-in plus, on production, the developer's yes per call - with
    stdin closed so nothing can wait for input. Output is redacted like every other action."""
    if not isinstance(command, str) or not command.strip() or len(command) > SHELL_MAX:
        raise ShError("bad_request", "command must be 1-%d characters" % SHELL_MAX)
    if "\x00" in command:
        raise ShError("bad_request", "command contains a NUL byte")
    b64 = base64.b64encode(command.encode("utf-8")).decode("ascii")
    return SECRETS_PRELUDE + "printf %%s %s | base64 -d > \"$HOME/.odoo-sh-mcp-cmd.sh\"\n" \
        "bash \"$HOME/.odoo-sh-mcp-cmd.sh\" < /dev/null 2>&1; rc=$?\nrm -f \"$HOME/.odoo-sh-mcp-cmd.sh\"\n" \
        "echo \"__EXIT__=$rc\"\n" % b64


_COMMIT_RE = re.compile(r"\.\s*commit\s*\(|\bcommit\s*\(\s*\)")


def script_odoo_shell(snippet: str, db=None) -> str:
    """An `odoo-bin shell` snippet (opt-in action `odoo_shell`), ended by env.cr.rollback().
    commit() in the snippet is refused, so database changes are discarded. It is not a
    sandbox: side effects outside the transaction (mail sent, HTTP calls, files) still happen."""
    if not isinstance(snippet, str) or not snippet.strip() or len(snippet) > SHELL_MAX:
        raise ShError("bad_request", "snippet must be 1-%d characters of Python" % SHELL_MAX)
    if _COMMIT_RE.search(snippet):
        raise ShError("bad_request", "the snippet calls commit(); odoo_shell always rolls back. Database writes "
                                     "belong in a module/upgrade script or the 'odoo' data MCP")
    body = snippet.rstrip() + "\n\nenv.cr.rollback()\n"
    b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
    dbarg = " -d %s" % shlex.quote(db) if db else ""
    return SECRETS_PRELUDE + ("printf %%s %s | base64 -d | odoo-bin shell%s --no-http "
                              "--log-level=warn 2>&1; echo \"__EXIT__=$?\"\n" % (b64, dbarg))


def new_job_id(action: str) -> str:
    return "%s-%s" % (action, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))


def check_write(name: str, prof: dict, action: str, approved_by_user) -> str:
    """Gate update/restart: per-profile opt-in, plus a fresh yes on every prod-role call."""
    allow = prof.get("allow") or ["read"]
    if action not in allow:
        raise ShError("not_allowed",
                      "profile %s (role %s) does not allow %s - it is read-only for that action. "
                      "Enabling it needs the developer's explicit yes: ask them, then run "
                      "odoo_sh.py allow %s %s --approved-by \"<their answer>\""
                      % (name, prof.get("role"), action, name,
                         " ".join(sorted(set([a for a in allow if a != "read"] + [action])))))
    if prof.get("role", "prod") == "prod":
        answer = approved_by_user.strip() if isinstance(approved_by_user, str) else ""
        if len(answer) < 2:
            raise ShError("confirmation_needed",
                          "%s on production profile %s (%s) needs the developer's yes for THIS call. Ask them - "
                          "name the profile, the url and what will run - and pass their answer verbatim as "
                          "approved_by_user. Never reuse an earlier yes." % (action, name, prof.get("url")))
        return answer
    return ""
