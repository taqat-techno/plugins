"""
Behavioral tests for the Django plugin hooks.

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
              "ALLOW_DJANGO_DESTRUCTIVE", "HOOKLIB_DEBUG")
# Built from parts so that this file's own text never trips a live guard.
FLUSH = "fl" + "ush"
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
def django_project(tmp_path):
    (tmp_path / "manage.py").write_text("# manage\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def plain_dir(tmp_path):
    d = tmp_path / "not-django"
    d.mkdir()
    return d


def bash(command, cwd):
    return {"cwd": str(cwd), "tool_input": {"command": command}}


def write_payload(file_path, content):
    return {"tool_input": {"file_path": file_path, "content": content}}


# ─── session_start.py ─────────────────────────────────────────────

class TestSessionStart:
    def test_silent_outside_a_django_project(self, plain_dir):
        code, out, err = run_hook("session_start.py", {"cwd": str(plain_dir)}, cwd=plain_dir)
        assert code == 0
        assert out.strip() == "" and err.strip() == ""

    def test_context_json_in_a_django_project(self, django_project):
        (django_project / "requirements.txt").write_text("Django==5.1.2\ndjangorestframework\n")
        code, out, _ = run_hook("session_start.py", {"cwd": str(django_project)}, cwd=django_project)
        assert code == 0
        h = hso(out)
        assert h["hookEventName"] == "SessionStart"
        assert "Django ~5.1.2" in h["additionalContext"]
        assert "DRF present" in h["additionalContext"]
        assert "/django:migrate" in h["additionalContext"]

    def test_detects_monorepo_backend(self, tmp_path):
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "manage.py").write_text("# manage\n")
        code, out, _ = run_hook("session_start.py", {"cwd": str(tmp_path)}, cwd=tmp_path)
        assert code == 0
        assert "backend/manage.py" in hso(out)["additionalContext"]

    def test_handles_garbage_stdin(self, plain_dir):
        code, out, _ = run_hook("session_start.py", None, cwd=plain_dir, raw="not json at all")
        assert code == 0 and out.strip() == ""


# ─── pre_bash_guard.py ────────────────────────────────────────────

ASKED = [
    f"python manage.py {FLUSH}",
    f"python manage.py {FLUSH} --noinput",
    f"python -m django {FLUSH}",
    f"django-admin {FLUSH} --settings=config.settings.dev",
    "python manage.py sql" + FLUSH,
    "./manage.py reset_db",
    "python manage.py migrate orders zero",
    "dropdb mydb",
    "sudo -u postgres dropdb mydb",
    "mysqladmin -u root drop mydb",
    f'psql -h db.example.com -c "{DROP_DB} mydb"',
    f'echo "{DROP_DB} mydb;" | psql',
    f"psql <<EOF\n{DROP_DB} mydb;\nEOF",
    f'python manage.py dbshell -- -c "{DROP_DB} mydb"',
    f"bash -c 'python manage.py {FLUSH} --noinput'",
    f"docker compose exec web python manage.py {FLUSH}",
    f"poetry run python manage.py {FLUSH}",
    f"cd backend && ./manage.py {FLUSH}",
    f"echo $(dropdb mydb)",
    "if true; then dropdb mydb; fi",
]
SILENT = [
    "python manage.py migrate",
    "python manage.py makemigrations orders",
    "python manage.py test",
    "python manage.py runserver",
    "python manage.py migrate orders 0001 --fake-initial",
    "python manage.py migrate orders zero --plan",
    "grep -rn dropdb scripts/",
    "git log --grep dropdb",
    f'git commit -m "docs: never {DROP_DB} in prod"',
    f'echo "python manage.py {FLUSH} is dangerous"',
    f"python manage.py {FLUSH} --help",
    "python manage.py help " + FLUSH,
    "dropdb --help",
    f"rg '{DROP_DB}' docs/",
    f"python manage.py shell  # never run {FLUSH} here",
    f"pytest -k {FLUSH}",
]


class TestBashGuard:
    @pytest.mark.parametrize("cmd", ASKED)
    def test_destructive_asks_the_user(self, cmd, django_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, django_project))
        assert code == 0, f"the guard asks, it never exits 2: {cmd}"
        h = hso(out)
        assert h.get("permissionDecision") == "ask", f"expected ask for: {cmd!r}"
        assert h["hookEventName"] == "PreToolUse"
        assert err.strip() == ""

    @pytest.mark.parametrize("cmd", ASKED)
    def test_no_override_token_is_shown_to_the_model(self, cmd, django_project):
        _, out, err = run_hook("pre_bash_guard.py", bash(cmd, django_project))
        text = out + err
        assert "ALLOW_DJANGO_DESTRUCTIVE" not in text
        assert "override" not in text.lower()

    @pytest.mark.parametrize("cmd", ASKED[:6])
    def test_in_command_token_no_longer_bypasses(self, cmd, django_project):
        for variant in (cmd + " # ALLOW_DJANGO_DESTRUCTIVE", "ALLOW_DJANGO_DESTRUCTIVE=1 " + cmd):
            _, out, _ = run_hook("pre_bash_guard.py", bash(variant, django_project))
            assert hso(out).get("permissionDecision") == "ask", variant

    @pytest.mark.parametrize("cmd", SILENT)
    def test_harmless_commands_are_silent(self, cmd, django_project):
        code, out, err = run_hook("pre_bash_guard.py", bash(cmd, django_project))
        assert code == 0
        assert out.strip() == "" and err.strip() == "", f"expected silence for: {cmd!r}"

    @pytest.mark.parametrize("cmd", ["dropdb mydb", f"python manage.py {FLUSH}",
                                     f'psql -c "{DROP_DB} x"'])
    def test_silent_outside_a_django_project(self, cmd, plain_dir):
        code, out, _ = run_hook("pre_bash_guard.py", bash(cmd, plain_dir), cwd=plain_dir)
        assert code == 0 and out.strip() == ""

    def test_project_dir_with_nested_manage_py_counts(self, tmp_path, plain_dir):
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "manage.py").write_text("# manage\n")
        _, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", plain_dir), cwd=plain_dir,
                             env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert hso(out).get("permissionDecision") == "ask"

    def test_walks_up_from_a_subdirectory(self, django_project):
        sub = django_project / "orders" / "tests"
        sub.mkdir(parents=True)
        _, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", sub), cwd=sub)
        assert hso(out).get("permissionDecision") == "ask"

    @pytest.mark.parametrize("env", [{"CLAUDE_PLUGIN_OPTION_DESTRUCTIVE_GUARD": "false"},
                                     {"ALLOW_DJANGO_DESTRUCTIVE": "1"}])
    def test_user_opt_out_from_the_hook_environment(self, env, django_project):
        code, out, _ = run_hook("pre_bash_guard.py", bash("dropdb mydb", django_project),
                                env_extra=env)
        assert code == 0 and out.strip() == ""

    def test_migrate_fake_is_advisory(self, django_project):
        code, out, _ = run_hook("pre_bash_guard.py",
                                bash("python manage.py migrate app 0001 --fake", django_project))
        assert code == 0
        assert "--fake" in advice(out)

    def test_fake_with_fake_initial_still_advises(self, django_project):
        _, out, _ = run_hook("pre_bash_guard.py",
                             bash("python manage.py migrate app --fake-initial --fake", django_project))
        assert "--fake" in advice(out)

    def test_zero_with_fake_is_advisory_not_ask(self, django_project):
        _, out, _ = run_hook("pre_bash_guard.py",
                             bash("python manage.py migrate app zero --fake", django_project))
        assert "--fake" in advice(out)

    @pytest.mark.parametrize("raw", ["not json", "", "[]", '{"tool_input": {"command": 7}}'])
    def test_fails_open_on_bad_input(self, raw, django_project):
        code, out, _ = run_hook("pre_bash_guard.py", None, cwd=django_project, raw=raw)
        assert code == 0 and out.strip() == ""

    def test_unbalanced_quote_fails_open(self, django_project):
        code, out, _ = run_hook("pre_bash_guard.py", bash("dropdb 'oops", django_project))
        assert code == 0 and out.strip() == ""


# ─── pre_write_guard.py (advisory only — always exit 0) ───────────

class TestWriteGuard:
    def test_hardcoded_debug_and_secret_warn(self):
        content = 'DEBUG = True\nSECRET_KEY = "abc123literal"\nALLOWED_HOSTS = ["*"]\n'
        code, out, _ = run_hook("pre_write_guard.py", write_payload("config/settings/prod.py", content))
        assert code == 0
        text = advice(out)
        assert "DEBUG = True" in text and "SECRET_KEY" in text and "ALLOWED_HOSTS" in text

    @pytest.mark.parametrize("path", ["myproj/test_settings.py", "config/settings/dev.py",
                                      "config/settings/local.py", "myproj/settings_test.py"])
    def test_dev_and_test_settings_skip_debug(self, path):
        code, out, _ = run_hook("pre_write_guard.py",
                                write_payload(path, 'DEBUG = True\nALLOWED_HOSTS = ["*"]\n'))
        assert code == 0 and out.strip() == ""

    def test_env_driven_settings_are_silent(self):
        content = 'DEBUG = env.bool("DEBUG", default=False)\nSECRET_KEY = os.environ["SECRET_KEY"]\n'
        code, out, _ = run_hook("pre_write_guard.py", write_payload("config/settings/prod.py", content))
        assert code == 0 and out.strip() == ""

    def test_runpython_without_reverse_warns(self):
        content = "from app.models import Order\noperations = [migrations.RunPython(forwards)]\n"
        _, out, _ = run_hook("pre_write_guard.py", write_payload("orders/migrations/0003_x.py", content))
        assert "RunPython" in advice(out) and "apps.get_model" in advice(out)

    def test_reversible_migration_is_silent_on_reverse_rule(self):
        content = ("def fwd(apps, se):\n    pass\n"
                   "operations = [migrations.RunPython(fwd, migrations.RunPython.noop)]\n")
        _, out, _ = run_hook("pre_write_guard.py", write_payload("orders/migrations/0004_y.py", content))
        assert "has no reverse" not in advice(out)

    def test_fields_all_warns_in_serializer(self):
        content = 'class S(ModelSerializer):\n    class Meta:\n        fields = "__all__"\n'
        _, out, _ = run_hook("pre_write_guard.py", write_payload("orders/serializers.py", content))
        assert "__all__" in advice(out)

    def test_edit_new_string_is_checked(self):
        payload = {"tool_input": {"file_path": "orders/serializers.py", "old_string": "x",
                                  "new_string": 'fields = "__all__"'}}
        _, out, _ = run_hook("pre_write_guard.py", payload)
        assert "__all__" in advice(out)

    def test_multiedit_edits_are_checked(self):
        payload = {"tool_input": {"file_path": "config/settings/prod.py", "edits": [
            {"old_string": "a", "new_string": "DEBUG = True"}]}}
        _, out, _ = run_hook("pre_write_guard.py", payload)
        assert "DEBUG = True" in advice(out)

    def test_non_python_file_ignored(self):
        code, out, _ = run_hook("pre_write_guard.py", write_payload("README.md", "DEBUG = True"))
        assert code == 0 and out.strip() == ""

    @pytest.mark.parametrize("raw", ["not json", "", '{"tool_input": []}'])
    def test_fails_open_on_bad_input(self, raw):
        code, out, _ = run_hook("pre_write_guard.py", None, raw=raw)
        assert code == 0 and out.strip() == ""
