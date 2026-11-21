"""odoo-sh MCP server: build resolution, doctor classification, write gate, redaction.

Offline: http_post, resolve_host, tcp_probe and run_process are replaced, so no network,
no ssh and no Odoo.sh account is needed. A real blocked-port case (22 times out, 443
and github.com:22 open) was checked by hand; see CHANGELOG 4.6.0.
"""

from __future__ import annotations

import base64
import json
import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp_sh"))
sys.path.insert(0, str(ROOT / "scripts" / "mcp"))

import shconfig as C  # noqa: E402
import shcore as S  # noqa: E402
import sh_tools as T  # noqa: E402

PRIV = ("-----BEGIN OPENSSH PRIVATE KEY-----\n"
        + base64.b64encode(b"openssh-key-v1\x00" + b"\x00\x00\x00\x04none" + b"\x00" * 40).decode() + "\n"
        "-----END OPENSSH PRIVATE KEY-----\n")
PRIV_ENC = ("-----BEGIN OPENSSH PRIVATE KEY-----\n"
            + base64.b64encode(b"openssh-key-v1\x00" + b"\x00\x00\x00\x0aaes256-ctr" + b"\x00" * 40).decode() + "\n"
            "-----END OPENSSH PRIVATE KEY-----\n")
PUB = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519" + b"\x01" * 36).decode() + " dev@box"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home" / ".odoo-mcp"
    monkeypatch.setenv("ODOO_SH_HOME", str(h))
    monkeypatch.delenv("ODOO_SH_FILE", raising=False)
    monkeypatch.delenv("ODOO_SH_PROJECT_DIR", raising=False)
    monkeypatch.setenv("ODOO_SH_SSH", "ssh")
    return tmp_path


@pytest.fixture
def key(tmp_path):
    d = tmp_path / "ssh"
    d.mkdir()
    (d / "id_odoo").write_text(PRIV)
    (d / "id_odoo.pub").write_text(PUB + "\n")
    return str(d / "id_odoo")


def prof(key, **kw):
    base = {"project": "acme-erp", "branch": "stage", "role": "stage",
            "url": "https://acme-erp-stage.odoo.com", "key": key}
    base.update(kw)
    return base


class Net:
    """Scripted network: db list answer, DNS, TCP ports, ssh result."""

    def __init__(self, monkeypatch, dbs=("acme-erp-stage-41234567",), dns=None, tcp=None, ssh=None):
        self.dbs = list(dbs) if isinstance(dbs, (list, tuple)) else dbs
        self.calls = []
        self.dns = dns or {}
        self.tcp = tcp or {}
        self.ssh = ssh or (0, "__ODOOSH_OK__\nabc123 2026-11-20T10:00:00+00:00 fix\n", "")
        monkeypatch.setattr(S, "http_post", self.http_post)
        monkeypatch.setattr(S, "resolve_host", lambda h: self.dns.get(h, True))
        monkeypatch.setattr(S, "tcp_probe", lambda h, p, timeout=8: self.tcp.get((h, p), "open"))
        monkeypatch.setattr(S, "run_process", self.run)
        monkeypatch.setattr(S, "agent_has_keys", lambda prof=None: False)

    def http_post(self, url, body, timeout=15):
        self.calls.append(url)
        if isinstance(self.dbs, Exception):
            raise self.dbs
        if self.dbs is None:
            return 404, None
        return 200, {"jsonrpc": "2.0", "id": 1, "result": self.dbs}

    def run(self, argv, stdin_text, timeout):
        self.argv, self.script = argv, stdin_text
        return self.ssh


# --------------------------------------------------------------------- resolution

def test_pick_build_takes_highest_build_of_the_branch():
    dbs = ["acme-erp-stage-41234567", "acme-erp-stage-41300002", "acme-erp-main-1"]
    b = S.pick_build(dbs, "acme-erp", "stage")
    assert b == {"db": "acme-erp-stage-41300002", "branch": "stage", "build": "41300002"}


def test_pick_build_infers_branch_with_hyphens():
    b = S.pick_build(["acme-co-feature-x-12"], "acme-co")
    assert b["branch"] == "feature-x" and b["build"] == "12"


def test_pick_build_no_match_is_build_not_found():
    with pytest.raises(S.ShError) as e:
        S.pick_build(["other-stage-1"], "acme-erp", "stage")
    assert e.value.cls == "build_not_found"


def test_pick_build_ambiguous_branches_needs_branch():
    with pytest.raises(S.ShError) as e:
        S.pick_build(["p-a-1", "p-b-2"], "p")
    assert e.value.cls == "config_error"


def test_resolve_derives_user_and_host_and_is_never_cached(monkeypatch, key):
    net = Net(monkeypatch)
    p = prof(key)
    t = S.resolve(p)
    assert (t["user"], t["host"]) == ("41234567", "acme-erp-stage-41234567.dev.odoo.com")
    net.dbs = ["acme-erp-stage-41300002"]
    t2 = S.resolve(p)
    assert t2["user"] == "41300002" and len(net.calls) == 2
    assert net.calls[0] == "https://acme-erp-stage.odoo.com/web/database/list"


def test_resolve_host_template_and_pinned(monkeypatch, key):
    Net(monkeypatch)
    t = S.resolve(prof(key, host="{project}.odoo.com", ssh_user="{build}"))
    assert t["host"] == "acme-erp.odoo.com" and t["user"] == "41234567"
    pinned = S.resolve(prof(key, host="x.dev.odoo.com", ssh_user="123"))
    assert pinned["pinned"] and pinned["host"] == "x.dev.odoo.com"


def test_db_list_disabled_is_classified(monkeypatch, key):
    Net(monkeypatch, dbs=None)
    with pytest.raises(S.ShError) as e:
        S.resolve(prof(key))
    assert e.value.cls == "db_list_unavailable"


# --------------------------------------------------------------------- ssh argv

def test_ssh_argv_safety_options(monkeypatch, key):
    Net(monkeypatch)
    p = prof(key, port=2222, proxy_jump="me@jump.example.com")
    argv = S.ssh_argv(p, S.resolve(p))
    joined = " ".join(argv)
    for opt in ("BatchMode=yes", "StrictHostKeyChecking=accept-new", "ConnectTimeout=", "IdentitiesOnly=yes",
                "PasswordAuthentication=no"):
        assert opt in joined
    kh = [a for a in argv if a.startswith("UserKnownHostsFile=")][0]
    assert kh.endswith('acme-erp-stage-41234567.dev.odoo.com"')    # one file per host
    assert argv[argv.index("-p") + 1] == "2222" and argv[argv.index("-J") + 1] == "me@jump.example.com"
    assert argv[-4:] == ["41234567", "acme-erp-stage-41234567.dev.odoo.com", "bash", "-s"]
    assert PRIV not in joined


# --------------------------------------------------------------------- doctor

def _doctor(monkeypatch, key, **net):
    Net(monkeypatch, **net)
    return S.doctor("st", prof(key))


def test_doctor_ok_reports_deployed_commit(monkeypatch, key):
    out = _doctor(monkeypatch, key)
    assert out["ok"] and out["result"] == "ok" and "abc123" in out["message"]


def test_doctor_tcp22_blocked_but_443_and_github_open(monkeypatch, key):
    host = "acme-erp-stage-41234567.dev.odoo.com"
    out = _doctor(monkeypatch, key, tcp={(host, 22): "timeout", (host, 443): "open", ("github.com", 22): "open"})
    assert out["result"] == "tcp_timeout"
    assert "443 on the same host connects" in out["message"] and "github.com:22 works" in out["message"]
    assert any("proxy-jump" in f for f in out["fix"]) and any("--port" in f for f in out["fix"])


def test_doctor_host_unreachable_everywhere(monkeypatch, key):
    host = "acme-erp-stage-41234567.dev.odoo.com"
    out = _doctor(monkeypatch, key, tcp={(host, 22): "timeout", (host, 443): "timeout"})
    assert out["result"] == "tcp_timeout" and "unreachable" in out["message"]


def test_doctor_tcp_refused(monkeypatch, key):
    out = _doctor(monkeypatch, key, tcp={("acme-erp-stage-41234567.dev.odoo.com", 22): "refused"})
    assert out["result"] == "tcp_refused"


def test_doctor_url_dns_failure(monkeypatch, key):
    import socket
    import urllib.error
    out = _doctor(monkeypatch, key, dbs=urllib.error.URLError(socket.gaierror("nx")),
                  dns={"acme-erp-stage.odoo.com": False})
    assert out["result"] == "url_dns_failure"


def test_doctor_ssh_host_dns_failure_is_stale_build(monkeypatch, key):
    out = _doctor(monkeypatch, key, dns={"acme-erp-stage-41234567.dev.odoo.com": False})
    assert out["result"] == "stale_build"


def test_doctor_custom_host_dns_failure(monkeypatch, key):
    Net(monkeypatch, dns={"bad.example.com": False})
    out = S.doctor("st", prof(key, host="bad.example.com"))
    assert out["result"] == "dns_failure"


def test_doctor_auth_refused(monkeypatch, key):
    out = _doctor(monkeypatch, key, ssh=(255, "", "41234567@host: Permission denied (publickey).\r\n"))
    assert out["result"] == "auth_refused"
    assert any("Profile > SSH keys" in f for f in out["fix"])


def test_doctor_auth_refused_after_rebuild_is_stale_build(monkeypatch, key):
    net = Net(monkeypatch, ssh=(255, "", "Permission denied (publickey)."))
    orig = net.run

    def run(argv, stdin_text, timeout):
        net.dbs = ["acme-erp-stage-41300002"]   # rebuilt while we connected
        return orig(argv, stdin_text, timeout)
    monkeypatch.setattr(S, "run_process", run)
    out = S.doctor("st", prof(key))
    assert out["result"] == "stale_build"


def test_doctor_build_not_found(monkeypatch, key):
    out = _doctor(monkeypatch, key, dbs=["acme-erp-main-1"])
    assert out["result"] == "build_not_found"


@pytest.mark.parametrize("stderr,cls", [
    ("Permissions for 'k' are too open.\nWARNING: UNPROTECTED PRIVATE KEY FILE!", "key_permissions"),
    ("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!", "host_key_changed"),
    ("ssh: connect to host h port 22: Connection timed out", "tcp_timeout"),
    ("ssh: Could not resolve hostname h: Name or service not known", "dns_failure"),
])
def test_classify_ssh_stderr(stderr, cls):
    assert S.classify_ssh(255, stderr)[0] == cls


def test_classify_ssh_timeout():
    assert S.classify_ssh(None, "")[0] == "ssh_timeout"


def test_doctor_missing_and_wrong_key(monkeypatch, key, tmp_path):
    Net(monkeypatch)
    assert S.doctor("st", prof(str(tmp_path / "nope")))["result"] == "key_missing"
    assert S.doctor("st", prof(key + ".pub"))["result"] == "key_not_private"


def test_doctor_encrypted_key_without_agent(monkeypatch, key):
    Path(key).write_text(PRIV_ENC)
    out = _doctor(monkeypatch, key)
    assert out["result"] == "key_encrypted_no_agent"


def test_key_info_never_returns_private_material(key):
    info = S.key_info(key)
    assert info["private"] and info["encrypted"] is False and info["fingerprint"].startswith("SHA256:")
    assert "PRIVATE" not in json.dumps(info)


# --------------------------------------------------------------------- redaction

def test_redact_text_patterns_and_conf_values():
    text = ("2026-11-21 10:00:00,1 42 INFO db x: admin_passwd = s3cretAdmin\n"
            "connecting with db_password=hunter22 and Authorization: Bearer abcdefghijklmnop\n"
            "url https://user:pa55word@api.example.com/x?access_token=tok123456&y=1\n"
            '{"api_key": "ak_live_123456"}\n'
            "value only: myConfValue99\n")
    out = S.redact_text(text, ["myConfValue99", "False"])
    for secret in ("s3cretAdmin", "hunter22", "abcdefghijklmnop", "pa55word", "tok123456", "ak_live_123456",
                   "myConfValue99"):
        assert secret not in out
    assert "INFO db x" in out and "y=1" in out


def test_ssh_run_strips_secret_lines_and_redacts(monkeypatch, key):
    secret = base64.b64encode(b"conf-only-secret-value").decode()
    Net(monkeypatch, ssh=(0, "__ODOOSH_SECRET__ %s\nlog line with conf-only-secret-value\n" % secret, ""))
    p = prof(key)
    res = S.ssh_run(p, S.resolve(p), "true")
    assert "__ODOOSH_SECRET__" not in res["stdout"] and "conf-only-secret-value" not in res["stdout"]
    assert "***REDACTED***" in res["stdout"]


# --------------------------------------------------------------------- scripts

def test_script_logs_quotes_user_input():
    s = S.script_logs("install", lines=50, grep="x'; rm -rf ~; '", since="2026-11-21 10:00:00", errors_only=True)
    assert "-e %s " % shlex.quote("x'; rm -rf ~; '") in s     # one quoted argument, not spliced
    assert '"$HOME/logs"/install.log' in s and "tail -n 50" in s


@pytest.mark.parametrize("kw", [{"file": "../etc/passwd"}, {"since": "yesterday"}, {"grep": "("},
                                {"pid": "1; ls"}])
def test_script_logs_rejects_bad_args(kw):
    with pytest.raises(S.ShError):
        S.script_logs(**kw)


def test_script_modules_validates_names():
    with pytest.raises(S.ShError):
        S.script_modules(names=["sale'; drop table x; --"])
    s = S.script_modules(db="acme-erp-stage-1", names=["sale", "stock"])
    sql = shlex.split(s.splitlines()[-1])[-1]
    assert "name in ('sale', 'stock')" in sql and "-d acme-erp-stage-1" in s


# --------------------------------------------------------------------- config + gate

def test_config_refuses_other_files_and_git_trees(monkeypatch, tmp_path):
    monkeypatch.setenv("ODOO_SH_FILE", str(tmp_path / "profiles.json"))
    with pytest.raises(C.ConfigError):
        C.path()
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("ODOO_SH_FILE", str(repo / "odoo-sh.json"))
    with pytest.raises(C.ConfigError):
        C.path()


def test_new_profile_is_read_only_and_key_material_refused(key):
    p = C.upsert("st", prof(key))
    assert p["allow"] == ["read"]
    with pytest.raises(C.ConfigError):
        C.upsert("bad", prof(PRIV))


def test_unknown_role_is_treated_as_prod(key):
    p = C.upsert("x", {k: v for k, v in prof(key).items() if k != "role"})
    assert p["role"] == "prod"


def test_allow_needs_approval_and_deny_does_not(key):
    C.upsert("st", prof(key))
    with pytest.raises(C.ConfigError):
        C.set_allow("st", ["read", "update"])
    assert C.set_allow("st", ["read", "update"], "yes, allow update on stage")["allow"] == ["read", "update"]
    assert C.set_allow("st", ["read"])["allow"] == ["read"]
    log = Path(C.audit_path()).read_text(encoding="utf-8")
    assert "yes, allow update on stage" in log


def test_write_tools_gate(monkeypatch, key):
    net = Net(monkeypatch, ssh=(0, "__JOB__ update-x pid 9\n", ""))
    C.upsert("st", prof(key))
    text, err = T.dispatch("sh_update", {"modules": ["sale"]})
    assert err and "not_allowed" in text and not hasattr(net, "script")
    C.set_allow("st", ["update"], "ok")
    text, err = T.dispatch("sh_update", {"modules": ["sale"]})
    assert not err and "started update job" in text and "odoo-bin -u sale" in net.script


def test_prod_write_needs_fresh_yes_each_call(monkeypatch, key):
    Net(monkeypatch, dbs=["acme-erp-main-1"], ssh=(0, "__JOB__\n", ""))
    C.upsert("pr", prof(key, branch="main", role="prod", url="https://acme-erp.odoo.com"))
    C.set_allow("pr", ["restart"], "yes")
    text, err = T.dispatch("sh_restart", {})
    assert err and "confirmation_needed" in text
    text, err = T.dispatch("sh_restart", {"approved_by_user": "yes restart prod now"})
    assert not err and "started restart job" in text


def test_pick_by_folder_then_default(key, tmp_path, monkeypatch):
    C.upsert("a", prof(key))
    C.upsert("b", prof(key, paths=[str(tmp_path / "proj")]))
    assert C.pick()[0] == "a"            # first profile became the default
    monkeypatch.setenv("ODOO_SH_PROJECT_DIR", str(tmp_path / "proj" / "sub"))
    assert C.pick()[0] == "b"


def test_status_without_profiles_points_at_setup():
    text, err = T.dispatch("sh_status", {})
    assert not err and "sh-setup" in text


def test_logs_tool_end_to_end(monkeypatch, key):
    net = Net(monkeypatch, ssh=(0, "__SIZE__ 10 bytes\n2026-11-21 10:00:00,1 7 ERROR db odoo: boom password=xyz12345\n", ""))
    C.upsert("st", prof(key))
    text, err = T.dispatch("sh_logs", {"file": "install", "errors_only": True})
    assert not err and text.startswith("[odoo.sh st · acme-erp-stage-41234567 · role stage")
    assert "xyz12345" not in text and "boom" in text and "install.log" in net.script


def test_cli_keys_and_add(key, capsys, tmp_path):
    import odoo_sh
    assert odoo_sh.main(["keys", "--dir", str(Path(key).parent)]) == 0
    out = capsys.readouterr().out
    assert "SHA256:" in out and "PRIVATE" not in out
    assert odoo_sh.main(["keys", "--print", key]) == 0
    assert PUB in capsys.readouterr().out
    assert odoo_sh.main(["add", "st", "--project", "acme-erp", "--url", "https://acme-erp-stage.odoo.com",
                         "--key", key, "--role", "stage"]) == 0
    assert odoo_sh.main(["allow", "st", "update"]) == 1     # no --approved-by
    assert C.load()["profiles"]["st"]["allow"] == ["read"]


# --------------------------------------------------------------------- generic setups

@pytest.mark.parametrize("text,user,host,port", [
    ("ssh 1234567@acme-erp-stage-1234567.dev.odoo.com", "1234567", "acme-erp-stage-1234567.dev.odoo.com", None),
    ("1234567@acme-erp-main-1234567.dev.odoo.com", "1234567", "acme-erp-main-1234567.dev.odoo.com", None),
    ("ssh -p 2222 99@build.example.com", "99", "build.example.com", 2222),
    ("ssh://99@build.example.com:2200", "99", "build.example.com", 2200),
])
def test_parse_pasted_ssh_address(text, user, host, port):
    assert C.parse_ssh_address(text) == {"ssh_user": user, "host": host, "port": port}


def test_parse_ssh_address_rejects_garbage():
    with pytest.raises(C.ConfigError):
        C.parse_ssh_address("rm -rf /")


def test_many_projects_and_branches_pick_by_name(key):
    for name, project, branch in (("acme-stage", "acme-erp", "stage"), ("acme-dev", "acme-erp", "feature-x"),
                                  ("globex-prod", "globex", "main")):
        C.upsert(name, prof(key, project=project, branch=branch, url="https://%s-%s.odoo.com" % (project, branch)))
    assert sorted(C.load()["profiles"]) == ["acme-dev", "acme-stage", "globex-prod"]
    assert C.pick("globex-prod")[1]["project"] == "globex"
    C.remove("acme-stage")
    assert C.load().get("default") is None
    with pytest.raises(C.ConfigError):     # two left, no default, no folder binding
        C.pick()


def test_agent_mode_profile_has_no_key_and_no_identities_only(monkeypatch, key):
    Net(monkeypatch)
    p = C.upsert("ag", {k: v for k, v in prof(key).items() if k != "key"})
    argv = S.ssh_argv(p, S.resolve(p))
    assert "-i" not in argv and "IdentitiesOnly=yes" not in argv and "BatchMode=yes" in argv
    monkeypatch.setattr(S, "agent_has_keys", lambda prof=None: False)
    assert S.doctor("ag", p)["result"] == "no_key"
    monkeypatch.setattr(S, "agent_has_keys", lambda prof=None: True)
    assert S.doctor("ag", p)["result"] == "ok"


def test_pub_key_path_works_when_agent_holds_private_half(monkeypatch, key):
    Net(monkeypatch)
    monkeypatch.setattr(S, "agent_has_keys", lambda prof=None: True)
    assert S.doctor("st", prof(key + ".pub"))["result"] == "ok"


def test_per_profile_overrides_reach_ssh_and_scripts(monkeypatch, key, tmp_path):
    net = Net(monkeypatch, ssh=(0, "ok\n", ""))
    exe = tmp_path / "my-ssh"
    p = C.upsert("ov", prof(key, ssh_binary=str(exe), connect_timeout=25, command_timeout=200,
                            ssh_options=["HostKeyAlgorithms=+ssh-rsa"], src_dir="~/src/custom", logs_dir="/var/log/odoo"))
    argv = S.ssh_argv(p, S.resolve(p))
    assert argv[0] == str(exe) and "ConnectTimeout=25" in argv and "HostKeyAlgorithms=+ssh-rsa" in argv
    assert argv.index("BatchMode=yes") < argv.index("HostKeyAlgorithms=+ssh-rsa")   # safety options win
    T.dispatch("sh_logs", {"profile": "ov", "file": "custom-worker.log"})
    assert '"/var/log/odoo"/custom-worker.log' in net.script
    T.dispatch("sh_commit", {"profile": "ov"})
    assert '"$HOME/src/custom"' in net.script


@pytest.mark.parametrize("opt", ["ProxyCommand=sh -c x", "StrictHostKeyChecking=no", "LocalCommand=x",
                                 "BatchMode=no", "PermitLocalCommand=yes"])
def test_unsafe_ssh_options_refused(key, opt):
    with pytest.raises(C.ConfigError):
        C.upsert("bad", prof(key, ssh_options=[opt]))


def test_bad_dirs_and_timeouts_refused(key):
    for kw in ({"src_dir": "src/user"}, {"logs_dir": "~/../etc"}, {"connect_timeout": 1}, {"command_timeout": 9999}):
        with pytest.raises(C.ConfigError):
            C.upsert("bad", prof(key, **kw))


def test_log_names_and_listing():
    with pytest.raises(S.ShError):
        S.script_logs(file="../../etc/shadow")
    assert 'ls -la' in S.script_log_list("~/logs")


def test_classify_algorithm_mismatch_and_ed25519_hint(monkeypatch, key):
    assert S.classify_ssh(255, "Unable to negotiate: no matching host key type found. Their offer: ssh-rsa")[0] \
        == "algorithm_mismatch"
    Path(key + ".pub").write_text(PUB)   # an ed25519 public key
    fx = S.fix_for("auth_refused", prof(key), {"host": "h"})
    assert any("RSA" in f for f in fx) and any("--ssh" in f for f in fx)


def test_shell_and_odoo_shell_are_opt_in_and_rolled_back(monkeypatch, key):
    net = Net(monkeypatch, ssh=(0, "out\n__EXIT__=0\n", ""))
    C.upsert("st", prof(key))
    for tool, args in (("sh_shell", {"command": "ls ~"}), ("sh_odoo_shell", {"snippet": "print(env.uid)"})):
        text, err = T.dispatch(tool, args)
        assert err and "not_allowed" in text
    C.set_allow("st", ["shell", "odoo_shell"], "yes for shell and odoo shell on stage")
    text, err = T.dispatch("sh_shell", {"command": "ls ~"})
    assert not err and "| base64 -d >" in net.script and "< /dev/null" in net.script
    text, err = T.dispatch("sh_odoo_shell", {"snippet": "print(env['res.partner'].search_count([]))"})
    assert not err and "odoo-bin shell -d acme-erp-stage-41234567" in net.script
    body = base64.b64decode(net.script.split("printf %s ")[-1].split(" |")[0]).decode()
    assert body.rstrip().endswith("env.cr.rollback()")
    text, err = T.dispatch("sh_odoo_shell", {"snippet": "env['res.partner'].create({}); env.cr.commit()"})
    assert err and "commit" in text


def test_no_client_or_machine_names_in_shipped_sources():
    roots = [ROOT / "mcp_sh", ROOT / "scripts" / "mcp" / "odoo_sh.py", ROOT / "commands" / "sh-setup.md",
             ROOT / "skills" / "odoo-sh", Path(__file__)]
    banned = ("med" + "line", "ah" + "med", "C:" + "/Users/", "C:" + "\\" + "Users")
    for r in roots:
        for f in ([r] if r.is_file() else r.rglob("*")):
            if f.is_file() and f.suffix in (".py", ".md"):
                text = f.read_text(encoding="utf-8", errors="replace")
                assert not any(b.lower() in text.lower() for b in banned), f
