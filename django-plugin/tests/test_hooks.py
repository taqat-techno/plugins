"""
Behavioral tests for the Django plugin hooks.

Each hook is invoked as a subprocess with a PreToolUse/SessionStart JSON payload
on stdin (exactly as Claude Code calls it), and we assert on exit code, the
stderr block reason, and the advisory JSON on stdout.

Run:  pytest django-plugin/tests/test_hooks.py
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


def advice(out: str) -> str:
    """additionalContext from a PreToolUse advisory ("" when the hook stayed silent).

    Enforces the channel contract: exit-0 stderr/plain stdout never reach Claude,
    so an advisory must be hookSpecificOutput JSON with hookEventName set and no
    permissionDecision (the normal permission flow stays untouched).
    """
    if not out.strip():
        return ""
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in hso
    return hso["additionalContext"]


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

    def test_silent_when_not_a_django_project(self):
        # Run from a dir without manage.py -> empty context, never crashes.
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
        "python manage.py flush",
        "python manage.py sqlflush",
        "./manage.py reset_db",
        "dropdb mydb",
        'psql -c "DROP DATABASE mydb"',
    ]
    ALLOWED = [
        "python manage.py migrate",
        "python manage.py makemigrations orders",
        "python manage.py test",
        "python manage.py runserver",
        "python manage.py migrate orders 0001 --fake-initial",
    ]

    @pytest.mark.parametrize("cmd", BLOCKED)
    def test_destructive_blocked(self, cmd):
        code, out, err = run_hook("pre_bash_guard.py", bash_payload(cmd))
        assert code == 2, f"expected block for: {cmd}"
        assert "BLOCKED" in err

    @pytest.mark.parametrize("cmd", BLOCKED)
    def test_override_token_allows(self, cmd):
        code, _, _ = run_hook("pre_bash_guard.py", bash_payload(cmd + " # ALLOW_DJANGO_DESTRUCTIVE"))
        assert code == 0, f"override should allow: {cmd}"

    @pytest.mark.parametrize("cmd", ALLOWED)
    def test_safe_commands_allowed(self, cmd):
        code, _, _ = run_hook("pre_bash_guard.py", bash_payload(cmd))
        assert code == 0, f"expected allow for: {cmd}"

    def test_migrate_fake_is_advisory_not_blocking(self):
        code, out, err = run_hook("pre_bash_guard.py", bash_payload("python manage.py migrate app 0001 --fake"))
        assert code == 0  # advisory, never blocks
        assert "advisory" in advice(out) and "--fake" in advice(out)

    def test_fake_initial_alone_is_silent(self):
        code, out, err = run_hook("pre_bash_guard.py", bash_payload("python manage.py migrate --fake-initial"))
        assert code == 0
        assert out.strip() == "" and err.strip() == ""


# ─── pre_write_guard.py (advisory only — always exit 0) ───────────

class TestWriteGuard:
    def test_hardcoded_debug_and_secret_warn(self):
        content = 'DEBUG = True\nSECRET_KEY = "abc123literal"\nALLOWED_HOSTS = ["*"]\n'
        code, out, err = run_hook("pre_write_guard.py", write_payload("config/settings/prod.py", content))
        assert code == 0  # advisory never blocks
        assert "DEBUG = True" in advice(out)
        assert "SECRET_KEY" in advice(out)
        assert "ALLOWED_HOSTS" in advice(out)

    def test_env_driven_settings_are_silent(self):
        content = 'DEBUG = env.bool("DEBUG", default=False)\nSECRET_KEY = os.environ["SECRET_KEY"]\n'
        code, out, err = run_hook("pre_write_guard.py", write_payload("config/settings/prod.py", content))
        assert code == 0
        assert out.strip() == "" and err.strip() == ""

    def test_runpython_without_reverse_warns(self):
        content = "from app.models import Order\noperations = [migrations.RunPython(forwards)]\n"
        code, out, err = run_hook("pre_write_guard.py", write_payload("orders/migrations/0003_x.py", content))
        assert code == 0
        assert "RunPython" in advice(out)
        assert "apps.get_model" in advice(out)  # also flags the real-model import

    def test_reversible_migration_is_silent_on_reverse_rule(self):
        content = (
            "def fwd(apps, se):\n    pass\n"
            "operations = [migrations.RunPython(fwd, migrations.RunPython.noop)]\n"
        )
        code, out, err = run_hook("pre_write_guard.py", write_payload("orders/migrations/0004_y.py", content))
        assert code == 0
        assert "has no reverse" not in advice(out)

    def test_fields_all_warns_in_serializer(self):
        content = 'class S(ModelSerializer):\n    class Meta:\n        fields = "__all__"\n'
        code, out, err = run_hook("pre_write_guard.py", write_payload("orders/serializers.py", content))
        assert code == 0
        assert "__all__" in advice(out)

    def test_non_python_file_ignored(self):
        code, out, err = run_hook("pre_write_guard.py", write_payload("README.md", "DEBUG = True"))
        assert code == 0
        assert out.strip() == "" and err.strip() == ""
