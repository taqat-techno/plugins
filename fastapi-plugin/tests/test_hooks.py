"""
Behavioral tests for the FastAPI plugin hooks.

Each hook is invoked as a subprocess with a PreToolUse/SessionStart JSON payload
on stdin (exactly as Claude Code calls it), and we assert on exit code + stderr.

Run:  pytest fastapi-plugin/tests/test_hooks.py
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"


def run_hook(script: str, payload: dict):
    """Invoke a hook with `payload` as JSON stdin; return (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_payload(file_path: str, content: str) -> dict:
    return {"tool_input": {"file_path": file_path, "content": content}}


def bash_payload(command: str) -> dict:
    return {"tool_input": {"command": command}}


# ─── session_start.py ─────────────────────────────────────────────

class TestSessionStart:
    def test_emits_valid_json_and_exits_zero(self):
        code, out, _ = run_hook("session_start.py", {})
        assert code == 0
        doc = json.loads(out)
        assert doc["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_additional_context_present(self):
        code, out, _ = run_hook("session_start.py", {})
        assert code == 0
        assert "additionalContext" in out

    def test_handles_garbage_stdin(self):
        proc = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "session_start.py")],
            input="not json at all",
            capture_output=True, text=True, timeout=15,
        )
        assert proc.returncode == 0  # fail-open


# ─── pre_bash_guard.py ────────────────────────────────────────────

class TestBashGuard:
    BLOCKED = [
        "alembic downgrade base",
        "python -m alembic downgrade base",
        "poetry run alembic downgrade base",
        "dropdb mydb",
        'psql -c "DROP DATABASE mydb"',
    ]
    ALLOWED = [
        "alembic upgrade head",
        "alembic revision --autogenerate -m 'add item'",
        "alembic downgrade -1",
        "uvicorn app.main:app --reload",
        "pytest tests/",
    ]

    @pytest.mark.parametrize("cmd", BLOCKED)
    def test_destructive_blocked(self, cmd):
        code, _, err = run_hook("pre_bash_guard.py", bash_payload(cmd))
        assert code == 2, f"expected block for: {cmd}"
        assert "BLOCKED" in err

    @pytest.mark.parametrize("cmd", BLOCKED)
    def test_override_token_allows(self, cmd):
        code, _, _ = run_hook("pre_bash_guard.py", bash_payload(cmd + " # ALLOW_FASTAPI_DESTRUCTIVE"))
        assert code == 0, f"override should allow: {cmd}"

    @pytest.mark.parametrize("cmd", ALLOWED)
    def test_safe_commands_allowed(self, cmd):
        code, _, _ = run_hook("pre_bash_guard.py", bash_payload(cmd))
        assert code == 0, f"expected allow for: {cmd}"

    def test_alembic_stamp_is_advisory_not_blocking(self):
        code, _, err = run_hook("pre_bash_guard.py", bash_payload("alembic stamp head"))
        assert code == 0  # advisory, never blocks
        assert "advisory" in err and "stamp" in err

    def test_plain_downgrade_one_is_silent(self):
        code, _, err = run_hook("pre_bash_guard.py", bash_payload("alembic downgrade -1"))
        assert code == 0
        assert err.strip() == ""


# ─── pre_write_guard.py (advisory only — always exit 0) ───────────

class TestWriteGuard:
    def test_blocking_calls_in_async_warn(self):
        content = (
            "import requests, time\n"
            "async def handler():\n"
            "    time.sleep(1)\n"
            "    requests.get('http://x')\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert code == 0  # advisory never blocks
        assert "time.sleep" in err
        assert "requests" in err

    def test_sync_route_is_silent(self):
        content = (
            "import requests, time\n"
            "def handler():\n"          # sync def -> threadpool, blocking is fine
            "    time.sleep(1)\n"
            "    requests.get('http://x')\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/routers/x.py", content))
        assert code == 0
        assert err.strip() == ""

    def test_hardcoded_secret_in_config_warns(self):
        content = 'SECRET_KEY = "supersecretliteralvalue123"\n'
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/core/config.py", content))
        assert code == 0
        assert "SECRET_KEY" in err

    def test_env_driven_settings_are_silent(self):
        content = (
            "from pydantic_settings import BaseSettings\n"
            "class Settings(BaseSettings):\n"
            "    secret_key: str\n"
            "    database_url: str\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/core/config.py", content))
        assert code == 0
        assert err.strip() == ""

    def test_wildcard_cors_with_credentials_warns(self):
        content = (
            "from fastapi.middleware.cors import CORSMiddleware\n"
            "app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True)\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/main.py", content))
        assert code == 0
        assert "CORS" in err or "allow_origins" in err

    def test_scoped_cors_is_silent(self):
        content = (
            "from fastapi.middleware.cors import CORSMiddleware\n"
            "app.add_middleware(CORSMiddleware, allow_origins=['https://app.example.com'], allow_credentials=True)\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("app/main.py", content))
        assert code == 0
        assert err.strip() == ""

    def test_empty_downgrade_warns(self):
        content = (
            "def upgrade():\n    op.add_column('t', sa.Column('c', sa.String()))\n\n"
            "def downgrade():\n    pass\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("alembic/versions/ab12_x.py", content))
        assert code == 0
        assert "downgrade" in err

    def test_real_downgrade_is_silent(self):
        content = (
            "def upgrade():\n    op.add_column('t', sa.Column('c', sa.String()))\n\n"
            "def downgrade():\n    op.drop_column('t', 'c')\n"
        )
        code, _, err = run_hook("pre_write_guard.py", write_payload("alembic/versions/ab12_x.py", content))
        assert code == 0
        assert err.strip() == ""

    def test_non_python_file_ignored(self):
        code, _, err = run_hook("pre_write_guard.py", write_payload("README.md", "SECRET_KEY = \"x\""))
        assert code == 0
        assert err.strip() == ""
