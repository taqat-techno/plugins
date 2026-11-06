"""Fixture tests for the cleanup apply scripts.

apply_files.sh runs against a throwaway HOME under pytest's tmp dir (Git Bash on Windows,
bash elsewhere): dry mode changes nothing, run mode acts only on allowed lines, and every
guard refuses its line. Nothing outside tmp_path is ever named.

apply_dbs.sh needs a real Postgres: set ENVDOC_IT_WSL_DISTRO=<distro> (Windows, runs inside
WSL) or ENVDOC_IT_PG=1 (native) to run the integration test, which creates and drops only a
database named envdoc_test_<random>.
"""
import os
import pathlib
import secrets
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "dev-env-cleanup" / "scripts"


def _bash():
    if sys.platform != "win32":
        return shutil.which("bash")
    git = shutil.which("git")
    if git:  # <Git>\cmd\git.exe or <Git>\mingw64\bin\git.exe -> <Git>\bin\bash.exe (never WSL's bash.exe)
        for parent in pathlib.Path(git).parents:
            for cand in (parent / "bin" / "bash.exe", parent / "usr" / "bin" / "bash.exe"):
                if cand.is_file():
                    return str(cand)
    return None


BASH = _bash()
pytestmark = pytest.mark.skipif(not BASH, reason="needs bash (Git Bash on Windows)")


def posix(p) -> str:
    s = str(p).replace("\\", "/")
    if sys.platform == "win32" and len(s) > 1 and s[1] == ":":
        s = "/" + s[0].lower() + s[2:]
    return s


def run(script, *args, home):
    env = dict(os.environ, HOME=posix(home), LC_ALL="C", MSYS_NO_PATHCONV="1")
    return subprocess.run([BASH, posix(SCRIPTS / script), *args], env=env, capture_output=True, timeout=120)


@pytest.fixture
def tree(tmp_path):
    home = tmp_path / "home"
    h = posix(home)
    files = {
        ".local/share/odoo/proj/filestore/dead_db/aa/blob": "x" * 100,
        ".local/share/odoo/proj/filestore/live_db/aa/blob": "x",
        ".local/share/Odoo/addons/17.0/keep": "x",
        ".local/share/Odoo/oldcluster/filestore/gone/f": "x",
        "tmp/old_work/a.txt": "x",
        "tmp/keep_me/a.txt": "x",
        ".cache/pip/http/a": "x",
        ".config/proj/odoo.wsl.conf": f"[options]\ndata_dir = {h}/.local/share/odoo/proj\n",
        ".config/proj/lane-a.conf": "[options]\ndb_name = lane_a\n",
    }
    for rel, text in files.items():
        p = home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    outside = tmp_path / "outside" / "precious.txt"
    outside.parent.mkdir()
    outside.write_text("do not touch", encoding="utf-8")
    return home, h, outside


def write_list(tmp_path, lines):
    p = tmp_path / "list.tsv"
    p.write_text("".join(l + "\n" for l in lines), encoding="utf-8", newline="\n")
    return posix(p)


GOOD = ["delete\t{h}/.local/share/odoo/proj/filestore/dead_db",
        "delete\t{h}/tmp/old_work",
        "delete\t{h}/.local/share/Odoo/oldcluster",
        "delete\t{h}/.cache/pip",
        "archive\t{h}/.config/proj/lane-a.conf\t{h}/.config/proj/_archive_20261106"]
BAD = ["delete\t",                                              # empty
       "delete\trelative/path",                                 # not absolute
       "delete\t{h}/tmp/../.ssh",                               # .. segment
       "delete\t{h}/tmp/*",                                     # glob
       "delete\t{h}/tmp/",                                      # the prefix itself
       "delete\t{h}/.ssh",                                      # outside the allow-list
       "delete\t{outside}",                                     # outside HOME
       "delete\t{h}/.local/share/odoo/proj",                    # live conf data_dir
       "delete\t{h}/.local/share/Odoo/addons",                  # never root
       "archive\t{h}/tmp/keep_me/a.txt\t{h}/tmp/keep_me/_a",    # archive takes .conf only
       "archive\t{h}/.config/proj/odoo.wsl.conf\t{h}/elsewhere",  # destination not next to it
       "nuke\t{h}/tmp/keep_me"]                                 # unknown action


def fill(lines, h, outside):
    return [l.format(h=h, outside=posix(outside)) for l in lines]


def snapshot(root):
    return sorted(str(p.relative_to(root)) for p in pathlib.Path(root).rglob("*"))


def test_dry_run_changes_nothing(tree, tmp_path):
    home, h, outside = tree
    before = snapshot(tmp_path)
    lst = write_list(tmp_path, fill(GOOD + BAD, h, outside))
    after_list = snapshot(tmp_path)
    proc = run("apply_files.sh", "dry", lst, home=home)
    out = proc.stdout.decode()
    assert snapshot(tmp_path) == after_list and len(after_list) == len(before) + 1
    assert out.count("DRY ") == len(GOOD), out
    assert proc.returncode == 1  # refusals make the run fail loudly
    assert not (home / ".local" / "state" / "env-doctor").exists()  # dry run writes no log


def test_every_guard_refuses_its_line(tree, tmp_path):
    home, h, outside = tree
    for line in fill(BAD, h, outside):
        lst = write_list(tmp_path, [line])
        proc = run("apply_files.sh", "run", lst, home=home)
        out = proc.stdout.decode()
        assert "REFUSE" in out and proc.returncode == 1, (line, out, proc.stderr.decode())
    assert outside.read_text(encoding="utf-8") == "do not touch"
    assert (home / ".local/share/odoo/proj/filestore/live_db/aa/blob").exists()
    assert (home / ".local/share/Odoo/addons/17.0/keep").exists()
    assert (home / "tmp/keep_me/a.txt").exists()


def test_run_acts_on_allowed_lines_only_and_logs(tree, tmp_path):
    home, h, outside = tree
    lst = write_list(tmp_path, fill(GOOD, h, outside))
    proc = run("apply_files.sh", "run", lst, home=home)
    out = proc.stdout.decode()
    assert proc.returncode == 0, out + proc.stderr.decode()
    assert not (home / ".local/share/odoo/proj/filestore/dead_db").exists()
    assert not (home / "tmp/old_work").exists()
    assert not (home / ".local/share/Odoo/oldcluster").exists()
    assert not (home / ".cache/pip").exists()
    assert (home / ".config/proj/_archive_20261106/lane-a.conf").exists()
    assert not (home / ".config/proj/lane-a.conf").exists()
    # untouched neighbours
    assert (home / ".local/share/odoo/proj/filestore/live_db/aa/blob").exists()
    assert (home / "tmp/keep_me/a.txt").exists() and (home / ".config/proj/odoo.wsl.conf").exists()
    logs = list((home / ".local/state/env-doctor").glob("clean_*.log"))
    assert logs and "DELETED" in logs[0].read_text(encoding="utf-8")
    # a second run is a no-op, not an error
    again = run("apply_files.sh", "run", lst, home=home)
    assert again.returncode == 0 and "already gone" in again.stdout.decode()


def test_crlf_list_and_symlink_escape(tree, tmp_path):
    home, h, outside = tree
    p = tmp_path / "crlf.tsv"
    p.write_bytes(f"delete\t{h}/tmp/old_work\r\n".encode())
    proc = run("apply_files.sh", "dry", posix(p), home=home)
    assert proc.returncode == 0 and "DRY delete" in proc.stdout.decode()
    link = home / "tmp" / "sneaky"
    try:
        os.symlink(outside.parent, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks here")
    lst = write_list(tmp_path, [f"delete\t{h}/tmp/sneaky/precious.txt"])
    proc = run("apply_files.sh", "run", lst, home=home)
    assert "REFUSE" in proc.stdout.decode() and outside.exists()


def test_missing_mode_defaults_to_dry(tree, tmp_path):
    home, h, outside = tree
    lst = write_list(tmp_path, fill(GOOD[:1], h, outside))
    proc = run("apply_files.sh", "whatever", lst, home=home)
    assert "DRY delete" in proc.stdout.decode()
    assert (home / ".local/share/odoo/proj/filestore/dead_db").exists()


def test_scripts_are_lf_and_bash_parses_them():
    for script in SCRIPTS.glob("*.sh"):
        assert b"\r\n" not in script.read_bytes(), f"{script.name} has CRLF line endings"
        proc = subprocess.run([BASH, "-n", posix(script)], capture_output=True, timeout=30)
        assert proc.returncode == 0, (script.name, proc.stderr.decode())


# --------------------------------------------------------------------------- integration (opt-in)

def _it_enabled():
    return bool(os.environ.get("ENVDOC_IT_WSL_DISTRO") and sys.platform == "win32") or os.environ.get("ENVDOC_IT_PG") == "1"


@pytest.mark.skipif(not _it_enabled(), reason="set ENVDOC_IT_WSL_DISTRO or ENVDOC_IT_PG=1 to run")
def test_apply_dbs_backup_verify_and_drop_disposable_db():
    """Creates envdoc_test_<rand> on the port given by ENVDOC_IT_PORT (default 5432), with a
    table and a row, then runs apply_dbs.sh dry and run on it. Never touches another database."""
    port = os.environ.get("ENVDOC_IT_PORT", "5432")
    login = os.environ.get("ENVDOC_IT_LOGIN", "")  # e.g. "-h 127.0.0.1 -U odoo"
    db = "envdoc_test_" + secrets.token_hex(4)
    host, user = "-", "-"
    if login:
        parts = login.split()
        host, user = parts[parts.index("-h") + 1], parts[parts.index("-U") + 1]
    body = f"""set -eu
P="psql -X -w -At {login} -p {port}"
$P -d postgres -c 'CREATE DATABASE {db}'
$P -d {db} -c 'create table t (id int); insert into t values (1); create table u (x text)'
L=$(mktemp); B=$(mktemp -d)
printf '%s\\t%s\\t1\\t%s\\t%s\\t-\\n' {port} {db} {host} {user} > "$L"
S=$(mktemp); cat > "$S"
echo "== dry"; bash "$S" dry "$L" "$B"
test "$($P -d postgres -c "select count(*) from pg_database where datname='{db}'")" = 1
echo "== run"; bash "$S" run "$L" "$B"
echo "== after"; $P -d postgres -c "select count(*) from pg_database where datname='{db}'"
ls "$B"; pg_restore -l "$B/{db}.dump" | grep -c 'TABLE DATA'
rm -rf -- "${{B:?}}" "${{L:?}}" "${{S:?}}"
"""
    # stdin = <driver body><apply_dbs.sh>: head takes the driver, whose `cat` takes the script.
    inner = "D=$(mktemp); head -c " + str(len(body.encode())) + " > $D; bash $D"
    distro = os.environ.get("ENVDOC_IT_WSL_DISTRO")
    cmd = ["wsl.exe", "-d", distro, "-e", "bash", "-c", inner] if distro and sys.platform == "win32" else ["bash", "-c", inner]
    proc = subprocess.run(cmd, input=body.encode() + (SCRIPTS / "apply_dbs.sh").read_bytes(), capture_output=True,
                          timeout=600, env=dict(os.environ, MSYS_NO_PATHCONV="1"))
    out = proc.stdout.decode()
    assert proc.returncode == 0, out + proc.stderr.decode()
    assert f"DRY drop {db}@{port}" in out
    assert f"BACKUP {db}@{port}" in out and f"DROPPED {db}@{port}" in out
    after = out.split("== after", 1)[1].split()
    assert after[0] == "0" and f"{db}.dump" in out and after[-1] == "2"
