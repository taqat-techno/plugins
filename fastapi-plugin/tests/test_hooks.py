"""
Behavioral tests for the FastAPI plugin hooks.

Each hook is invoked as a subprocess with a PreToolUse/SessionStart JSON payload on
stdin (exactly as Claude Code calls it). We assert on the exit code and the JSON on
stdout: `permissionDecision: "ask"` for destructive commands, `additionalContext`
for advisories, and nothing at all when the hook has nothing to say.

Environment variables that change the guard's mode are pinned in every run.

Run:  python -m pytest -q -p no:cacheprovider
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
_MODE_VARS = ("CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_OPTION_DESTRUCTIVE_GUARD",
              "ALLOW_FASTAPI_DESTRUCTIVE", "HOOKLIB_DEBUG")
# Built from parts so that this file's own text never trips a live guard.
DOWN_BASE = "downgrade " + "base"
DROP_DB = "DROP " + "DATABASE"


def run_hook(script, payload, cwd=None, env_extra=None, raw=None):
    env = {k: v for k, v in os.environ.items() if k not in _MODE_VARS}
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=raw if raw is not None else json.dumps(payload),
        capture_output=True, text=True, timeout=30, cwd=cwd, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def hso(out):
    return json.loads(out)["hookSpecificOutput"] if out.strip() else {}


def advice(out):
    """additionalContext of an advisory; enforces that advisories never decide."""
    h = hso(out)
    if not h:
        return ""
    assert h["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in h
    return h["additionalContext"]


@pytest.fixture
def fastapi_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "acme-api"\ndependencies = ["fastapi>=0.115", "sqlalchemy>=2"]\n',
        encoding="utf-8")
    return tmp_path


@pytest.fixture
def plain_dir(tmp_path):
    d = tmp_path / "not-fastapi"
    d.mkdir()
    (d / "requirements.txt").write_text("fastapi-users-helper==1.0\nrequests\n", encoding="utf-8")
    return d


def bash(command, cwd):
    return {"cwd": str(cwd), "tool_input": {"command": command}}


def write_payload(file_path, content):
    return {"tool_input": {"file_path": file_path, "content": content}}


# ─── session_start.py ─────────────────────────────────────────────

class TestSessionStart:
    def test_silent_outside_a_fastapi_project(self, plain_dir):
        code, out, err = run_hook("session_start.py", {"cwd": str(plain_dir)}, cwd=plain_dir)
        assert code == 0
        assert out.strip() == "" and err.strip() == ""

    def test_context_json_in_a_fastapi_project(self, fastapi_project):
        code, out, _ = run_hook("session_start.py", {"cwd": str(fastapi_project)}, cwd=fastapi_project)
        assert code == 0
        h = hso(out)
        assert h["hookEventName"] == "SessionStart"
        assert "FastAPI ~0.115" in h["additionalContext"]
        assert "SQLAlchemy" in h["additionalContext"]
        assert "/fastapi:migrate" in h["additionalContext"]

    def test_detects_src_package_entrypoint(self, tmp_path):
        pkg = tmp_path / "src" / "acme"
        pkg.mkdir(parents=True)
        (pkg / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        _, out, _ = run_hook("session_start.py", {"cwd": str(tmp_path)}, cwd=tmp_path)
        assert "src/acme/main.py" in hso(out)["additionalContext"]

    def test_detects_monorepo_service(self, tmp_path):
        svc = tmp_path / "services" / "api"
        svc.mkdir(parents=True)
        (svc / "requirements.txt").write_text("fastapi==0.110.0\n")
        _, out, _ = run_hook("session_start.py", {"cwd": str(tmp_path)}, cwd=tmp_path)
        assert "services/api" in hso(out)["additionalContext"]

    def test_databases_must_be_the_package(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n# talks to two databases\n")
        _, out, _ = run_hook("session_start.py", {"cwd": str(tmp_path)}, cwd=tmp_path)
        assert "Async DB driver" not in hso(out)["additionalContext"]
        (tmp_path / "requirements.txt").write_text("fastapi\ndatabases[postgresql]\n")
        _, out, _ = run_hook("session_start.py", {"cwd": str(tmp_path)}, cwd=tmp_path)
        assert "Async DB driver" in hso(out)["additionalContext"]

    def test_handles_garbage_stdin(self, plain_dir):
        code, out, _ = run_hook("session_start.py", None, cwd=plain_dir, raw="not json at all")
        assert code == 0 and out.strip() == ""


# ─── pre_bash_guard.py ────────────────────────────────────────────

ASKED = [
    f"alembic {DOWN_BASE}",
    f"python -m alembic {DOWN_BASE}",
    f"poetry run alembic {DOWN_BASE}",
    f"uv run alembic -c alembic.ini {DOWN_BASE}",
    f"alembic -x tenant=acme {DOWN_BASE}",
    "alembic downgrade heads:base",
    "dropdb mydb",
    "sudo -u postgres dropdb mydb",
    f'psql -h db.example.com -c "{DROP_DB} mydb"',
    f'echo "{DROP_DB} mydb;" | psql',
    f"psql <<'SQL'\n{DROP_DB} mydb;\nSQL",
    f"bash -c 'alembic {DOWN_BASE}'",
    f"docker compose exec api alembic {DOWN_BASE}",
    f"cd services/api && alembic {DOWN_BASE}",
]
SILENT = [
    "alembic upgrade head",
    "alembic revision --autogenerate -m 'add item'",
    "alembic downgrade -1",
    f"alembic {DOWN_BASE} --sql",
    "alembic downgrade --help",
    "uvicorn app.main:app --reload",
    "pytest tests/",
    "grep -rn dropdb scripts/",
    "git log --grep dropdb",
    f'git commit -m "docs: never {DROP_DB} or alembic {DOWN_BASE} in prod"',
    f'echo "alembic {DOWN_BASE} is dangerous"',
    "dropdb --help",
]

# Wrappers, quote removal and extra SQL forms (re-audit RA-FAPI-01/02).
ALEMBIC = f"alembic {DOWN_BASE}"
ASKED_WRAPPED = [
    f"docker compose run --rm api {ALEMBIC}",
    f"docker compose -f compose.prod.yml run --rm -e ENV=prod api {ALEMBIC}",
    f"docker-compose run api {ALEMBIC}",
    f"docker compose exec -T api {ALEMBIC}",
    f"docker run --rm --env-file .env img {ALEMBIC}",
    f"docker exec -it -w /app api {ALEMBIC}",
    f"bash -lc '{ALEMBIC}'",
    f"sh -ec '{ALEMBIC}'",
    f"zsh -xc '{ALEMBIC}'",
    f"docker compose exec api bash -lc 'cd /app && {ALEMBIC}'",
    f"uv run --env-file .env {ALEMBIC}",
    f"uv run --with psycopg {ALEMBIC}",
    f"poetry run -C api {ALEMBIC}",
    f"timeout 60 {ALEMBIC}",
    f"nice -n 10 {ALEMBIC}",
    f"nohup {ALEMBIC} &",
    f"watch -n 5 {ALEMBIC}",
    f"eval '{ALEMBIC}'",
    f"ssh prod 'cd api && {ALEMBIC}'",
    f"heroku run -a api {ALEMBIC}",
    f"kubectl exec -it pod -- {ALEMBIC}",
    "alembic down''grade base",
    'alembic "down"grade base',
    "alembic downgrade ba\\se",
    f"psql <<< '{DROP_DB} mydb'",
    "psql -c 'DROP SCHEMA public CASCADE'",
    "psql -c 'TRUNCATE TABLE items'",
    "echo 'truncate items cascade;' | psql",
]
SILENT_WRAPPED = [
    "docker compose run --rm api alembic upgrade head",
    "docker compose build api",
    "bash -lc 'alembic upgrade head'",
    "bash scripts/migrate.sh",
    "uv run --env-file .env alembic downgrade -1",
    "timeout 60 pytest",
    "ssh prod 'tail -n 100 /var/log/api.log'",
    "command -v dropdb",
    f"git commit -m 'fix: docker compose run api {ALEMBIC} docs'",
    f"grep -rn \"bash -lc '{ALEMBIC}'\" docs/",
    f"echo \"ssh prod '{ALEMBIC}'\"",
    "psql -c \"select 'drop schema x cascade' as note\"",
    "psql -f truncate_old_rows.sql",
    "truncate -s 0 logs/api.log",
    "psql <<< 'SELECT 1'",
]


class TestBashGuard:
    @pytest.mark.parametrize("cmd", ASKED)
    def test_destructive_asks_the_user(self, cmd, fastapi_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, fastapi_project))
        assert code == 0, f"the guard asks, it never exits 2: {cmd}"
        h = hso(out)
        assert h.get("permissionDecision") == "ask", f"expected ask for: {cmd!r}"
        assert err.strip() == ""

    @pytest.mark.parametrize("cmd", ASKED)
    def test_no_override_token_is_shown_to_the_model(self, cmd, fastapi_project):
        _, out, err = run_hook("pre_bash_guard.py", bash(cmd, fastapi_project))
        text = out + err
        assert "ALLOW_FASTAPI_DESTRUCTIVE" not in text
        assert "override" not in text.lower()

    @pytest.mark.parametrize("cmd", ASKED[:5])
    def test_in_command_token_no_longer_bypasses(self, cmd, fastapi_project):
        for variant in (cmd + " # ALLOW_FASTAPI_DESTRUCTIVE", "ALLOW_FASTAPI_DESTRUCTIVE=1 " + cmd):
            _, out, _ = run_hook("pre_bash_guard.py", bash(variant, fastapi_project))
            assert hso(out).get("permissionDecision") == "ask", variant

    @pytest.mark.parametrize("cmd", SILENT)
    def test_harmless_commands_are_silent(self, cmd, fastapi_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, fastapi_project))
        assert code == 0
        assert out.strip() == "" and err.strip() == "", f"expected silence for: {cmd!r}"

    @pytest.mark.parametrize("cmd", ASKED_WRAPPED)
    def test_wrapped_and_quote_split_forms_ask(self, cmd, fastapi_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, fastapi_project))
        assert code == 0 and err.strip() == ""
        assert hso(out).get("permissionDecision") == "ask", f"expected ask for: {cmd!r}"

    @pytest.mark.parametrize("cmd", SILENT_WRAPPED)
    def test_wrapped_harmless_forms_are_silent(self, cmd, fastapi_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, fastapi_project))
        assert code == 0
        assert out.strip() == "" and err.strip() == "", f"expected silence for: {cmd!r}"

    @pytest.mark.parametrize("cmd", [f"docker compose run --rm api {ALEMBIC}",
                                     f"bash -lc '{ALEMBIC}'", "psql -c 'DROP SCHEMA public CASCADE'"])
    def test_wrapped_forms_stay_project_scoped(self, cmd, plain_dir):
        code, out, _ = run_hook("pre_bash_guard.py", bash(cmd, plain_dir), cwd=plain_dir)
        assert code == 0 and out.strip() == ""

    def test_shared_shell_section_matches_django_copy(self):
        other = HOOKS_DIR.parent.parent / "django-plugin" / "hooks" / "pre_bash_guard.py"
        if not other.is_file():
            pytest.skip("django-plugin is not checked out next to this plugin")

        def shared(path):
            text = path.read_text(encoding="utf-8")
            start = text.index("# " + "-" * 75 + " shell")
            body = text[start:text.index("\n# " + "-" * 75 + " ", start + 10)]
            return body.replace("fastapi-plugin/", "PEER/").replace("django-plugin/", "PEER/")

        assert shared(HOOKS_DIR / "pre_bash_guard.py") == shared(other)

    @pytest.mark.parametrize("cmd", ["dropdb mydb", f"alembic {DOWN_BASE}"])
    def test_silent_outside_a_fastapi_project(self, cmd, plain_dir):
        code, out, _ = run_hook("pre_bash_guard.py", bash(cmd, plain_dir), cwd=plain_dir)
        assert code == 0 and out.strip() == ""

    def test_requirements_directory_counts(self, tmp_path):
        (tmp_path / "requirements").mkdir()
        (tmp_path / "requirements" / "base.txt").write_text("FastAPI[standard]==0.115\n")
        _, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", tmp_path), cwd=tmp_path)
        assert hso(out).get("permissionDecision") == "ask"

    def test_project_dir_with_nested_service_counts(self, tmp_path):
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "requirements.txt").write_text("fastapi\n")
        other = tmp_path / "docs"
        other.mkdir()
        _, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", other), cwd=other,
                             env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert hso(out).get("permissionDecision") == "ask"

    @pytest.mark.parametrize("env", [{"CLAUDE_PLUGIN_OPTION_DESTRUCTIVE_GUARD": "false"},
                                     {"ALLOW_FASTAPI_DESTRUCTIVE": "1"}])
    def test_user_opt_out_from_the_hook_environment(self, env, fastapi_project):
        code, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", fastapi_project),
                                env_extra=env)
        assert code == 0 and out.strip() == ""

    def test_alembic_stamp_is_advisory(self, fastapi_project):
        code, out, _ = run_hook("pre_bash_guard.py", bash("alembic stamp head", fastapi_project))
        assert code == 0
        assert "stamp" in advice(out)

    @pytest.mark.parametrize("raw", ["not json", "", "[]", '{"tool_input": {"command": 7}}'])
    def test_fails_open_on_bad_input(self, raw, fastapi_project):
        code, out, _ = run_hook("pre_bash_guard.py", None, cwd=fastapi_project, raw=raw)
        assert code == 0 and out.strip() == ""


# ─── pre_write_guard.py (advisory only — always exit 0) ───────────

class TestWriteGuard:
    def test_blocking_calls_in_async_warn(self):
        content = ("import requests, time\n"
                   "async def handler():\n"
                   "    time.sleep(1)\n"
                   "    requests.get('https://api.example.com')\n")
        code, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert code == 0
        assert "time.sleep" in advice(out) and "requests" in advice(out)

    def test_sync_route_is_silent(self):
        content = ("import requests, time\n"
                   "def handler():\n"
                   "    time.sleep(1)\n"
                   "    requests.get('https://api.example.com')\n")
        code, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert code == 0 and out.strip() == ""

    def test_sync_def_next_to_async_def_is_silent(self):
        content = ("import time\n"
                   "async def handler():\n"
                   "    return {'ok': True}\n\n"
                   "def sync_worker():\n"
                   "    time.sleep(1)\n")
        code, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert code == 0 and out.strip() == ""

    def test_nested_sync_helper_inside_async_is_silent(self):
        content = ("import time\n"
                   "async def handler():\n"
                   "    def work():\n"
                   "        time.sleep(1)\n"
                   "    return await run_in_threadpool(work)\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert out.strip() == ""

    def test_from_time_import_sleep_is_caught(self):
        content = "from time import sleep\nasync def handler():\n    sleep(2)\n"
        _, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert "time.sleep" in advice(out)

    def test_unparseable_hunk_falls_back_to_regex(self):
        content = "    async def handler(:\n        time.sleep(1)\n"
        _, out, _ = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert "time.sleep" in advice(out)

    @pytest.mark.parametrize("content", [
        'SECRET_KEY = "supersecretliteralvalue123"\n',
        'class Settings(BaseSettings):\n    secret_key: str = "changeme-literal"\n',
        'class Settings(BaseSettings):\n    db_password: SecretStr = "hunter2-literal"\n',
        'class Settings(BaseSettings):\n    jwt_secret: str = r"raw-literal"\n',
    ])
    def test_hardcoded_secret_in_config_warns(self, content):
        code, out, _ = run_hook("pre_write_guard.py", write_payload("app/core/config.py", content))
        assert code == 0
        assert "hardcoded secret" in advice(out)

    @pytest.mark.parametrize("content", [
        "from pydantic_settings import BaseSettings\nclass Settings(BaseSettings):\n"
        "    secret_key: str\n    database_url: str\n",
        'class Settings(BaseSettings):\n    secret_key: str = os.getenv("SECRET_KEY", "dev")\n',
        'class Settings(BaseSettings):\n    token_url: str = "/auth/token"\n',
        'class Settings(BaseSettings):\n    max_tokens: int = 512\n',
    ])
    def test_env_driven_or_non_secret_settings_are_silent(self, content):
        code, out, _ = run_hook("pre_write_guard.py", write_payload("app/core/config.py", content))
        assert code == 0 and out.strip() == ""

    def test_wildcard_cors_with_credentials_warns(self):
        content = ("from fastapi.middleware.cors import CORSMiddleware\n"
                   "app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True)\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("app/main.py", content))
        assert "allow_origins" in advice(out)

    def test_scoped_cors_is_silent(self):
        content = ("from fastapi.middleware.cors import CORSMiddleware\n"
                   "app.add_middleware(CORSMiddleware, allow_origins=['https://app.example.com'], "
                   "allow_credentials=True)\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("app/main.py", content))
        assert out.strip() == ""

    def test_empty_downgrade_warns(self):
        content = ("def upgrade():\n    op.add_column('t', sa.Column('c', sa.String()))\n\n"
                   "def downgrade():\n    pass\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("alembic/versions/ab12_x.py", content))
        assert "downgrade" in advice(out)

    def test_real_downgrade_is_silent(self):
        content = ("def upgrade():\n    op.add_column('t', sa.Column('c', sa.String()))\n\n"
                   "def downgrade():\n    op.drop_column('t', 'c')\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("alembic/versions/ab12_x.py", content))
        assert out.strip() == ""

    def test_multiedit_edits_are_checked(self):
        payload = {"tool_input": {"file_path": "app/routers/x.py", "edits": [
            {"old_string": "a", "new_string": "async def h():\n    time.sleep(1)\n"}]}}
        _, out, _ = run_hook("pre_write_guard.py", payload)
        assert "time.sleep" in advice(out)

    def test_non_python_file_ignored(self):
        code, out, _ = run_hook("pre_write_guard.py", write_payload("README.md", 'SECRET_KEY = "x"'))
        assert code == 0 and out.strip() == ""

    @pytest.mark.parametrize("raw", ["not json", "", '{"tool_input": []}'])
    def test_fails_open_on_bad_input(self, raw):
        code, out, _ = run_hook("pre_write_guard.py", None, raw=raw)
        assert code == 0 and out.strip() == ""
