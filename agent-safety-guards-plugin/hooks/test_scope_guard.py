#!/usr/bin/env python3
"""test-scope guard (agent-safety-guards).

One script, two modes:

  track   PostToolUse(Write|Edit|MultiEdit|NotebookEdit), async. Records the edited
          file path for this session so the guard can name what actually changed.
  check   PreToolUse(Bash|PowerShell). If the command runs a WHOLE test suite, deny it
          with a reason naming the files changed this session and a scoped command.
          A command carrying FULL_SUITE=1 passes untouched.

Why a deny and not an advisory: on PreToolUse, plain stdout/stderr with exit 0 is not
fed to the model. A permissionDecision "deny" reason is, and it holds in every
permission mode. The deny is a speed bump, not a wall: FULL_SUITE=1 is the documented
override for when the user asked for the full suite or a user-invoked gate needs it.

Fails OPEN everywhere: bad input, an unknown shape, an exception or a slow filesystem
all end in exit 0 with no output, so the tool call proceeds exactly as without the hook.
Disable entirely with the environment variable TEST_SCOPE_GUARD=off.

Policy lives in skills/test-scope/SKILL.md. This script only classifies and reports.
Stdlib only. `--self-test` runs the built-in classification table.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
import threading
import time

OVERRIDE = "FULL_SUITE=1"
MAX_LISTED = 8
MAX_TRACKED = 200
STATE_TTL_SECONDS = 7 * 24 * 3600
LOG_CAP_BYTES = 1_000_000

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# --------------------------------------------------------------------------- state

def _data_dir() -> str:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        os.path.expanduser("~"), ".claude", "agent-safety-guards")
    return os.path.join(base, "test-scope")


def _session_file(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "unknown")[:80]
    return os.path.join(_data_dir(), "sessions", safe + ".json")


def _load_files(session_id: str) -> list[str]:
    try:
        with open(_session_file(session_id), encoding="utf-8") as fh:
            data = json.load(fh)
        files = data.get("files", [])
        return [f for f in files if isinstance(f, str)]
    except Exception:
        return []


def _atomic_write(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)


def _prune_old_sessions() -> None:
    folder = os.path.join(_data_dir(), "sessions")
    cutoff = time.time() - STATE_TTL_SECONDS
    try:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.getmtime(full) < cutoff:
                os.remove(full)
    except Exception:
        pass


def _log(runner: str, decision: str) -> None:
    """Decision log without command text: commands can carry secrets."""
    path = os.path.join(_data_dir(), "decisions.jsonl")
    try:
        if os.path.exists(path) and os.path.getsize(path) > LOG_CAP_BYTES:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"ts": int(time.time()), "runner": runner,
                                 "decision": decision}) + "\n")
    except Exception:
        pass


def track(data: dict) -> None:
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(path, str) or not path:
        return
    sid = str(data.get("session_id") or "unknown")
    files = _load_files(sid)
    if not files:
        _prune_old_sessions()
    if path in files:
        return
    files.append(path)
    _atomic_write(_session_file(sid), {"files": files[-MAX_TRACKED:]})


# ---------------------------------------------------------------- classification

PYTEST_BROAD = {".", "./", "tests", "tests/", "./tests", "./tests/", "test", "test/",
                "src", "src/"}
PYTEST_VALUE_FLAGS = {"-m", "-c", "-p", "-o", "-n", "-W", "--rootdir", "--ds",
                      "--cov", "--cov-report", "--maxfail", "--tb", "--durations",
                      "--junitxml", "--basetemp", "--log-level", "--timeout",
                      "--confcutdir", "--dist", "--import-mode", "--override-ini"}
PYTEST_SCOPING_FLAGS = {"-k", "--lf", "--last-failed", "--sw", "--stepwise",
                        "--testmon", "--deselect"}
DJANGO_VALUE_FLAGS = {"--settings", "--pythonpath", "--testrunner", "-v",
                      "--verbosity", "--exclude-tag"}
DJANGO_SCOPING_FLAGS = {"-k", "--tag"}
JS_VALUE_FLAGS = {"-c", "--config", "--project", "--reporter", "-j", "--workers",
                  "--shard", "--root", "--dir", "--environment", "--pool",
                  "--coverage.reporter", "--outputFile", "--timeout", "--retries"}
JS_SCOPING_FLAGS = {"-t", "--testNamePattern", "--grep", "-g", "--findRelatedTests",
                    "-o", "--onlyChanged", "--changed", "--changedSince",
                    "--lastCommit", "--last-failed", "--only-changed",
                    "--testPathPattern", "--testPathPatterns", "--related"}
VITEST_SUBCOMMANDS = {"run", "watch", "dev", "bench"}


def _tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=True, posix=True)
    except ValueError:
        return segment.split()


def _base(token: str) -> str:
    return re.split(r"[\\/]", token)[-1].lower()


def _positionals(args: list[str], value_flags: set[str]) -> tuple[list[str], set[str]]:
    """Split args into positionals and the set of flag names present."""
    positionals: list[str] = []
    flags: set[str] = set()
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg == "--":
            continue
        if arg.startswith("-") and len(arg) > 1:
            name = arg.split("=", 1)[0]
            flags.add(name)
            if "=" not in arg and name in value_flags:
                skip = True
            continue
        positionals.append(arg)
    return positionals, flags


def _django(args: list[str]) -> str:
    # --parallel takes an optional value: swallow a following number or "auto".
    cleaned: list[str] = []
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        cleaned.append(arg)
        if arg == "--parallel" and i + 1 < len(args) and (
                args[i + 1].isdigit() or args[i + 1] == "auto"):
            skip = True
    positionals, flags = _positionals(cleaned, DJANGO_VALUE_FLAGS)
    if positionals or flags & DJANGO_SCOPING_FLAGS:
        return "scoped"
    return "full"


def _pytest(args: list[str]) -> str:
    positionals, flags = _positionals(args, PYTEST_VALUE_FLAGS)
    if flags & PYTEST_SCOPING_FLAGS:
        return "scoped"
    if any(p not in PYTEST_BROAD for p in positionals):
        return "scoped"
    return "full"


def _flag_value(tokens: list[str], names: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for i, tok in enumerate(tokens):
        for name in names:
            if tok == name and i + 1 < len(tokens):
                values.append(tokens[i + 1])
            elif tok.startswith(name + "="):
                values.append(tok.split("=", 1)[1])
    return values


def _odoo(tokens: list[str]) -> str:
    modules: list[str] = []
    for value in _flag_value(tokens, ("-u", "-i", "--update", "--init")):
        modules.extend(m.strip() for m in value.split(",") if m.strip())
    if "all" in modules:
        return "full"
    tag_values = _flag_value(tokens, ("--test-tags",))
    specs = [s.strip() for v in tag_values for s in v.split(",") if s.strip()]
    includes = [s for s in specs if not s.startswith("-")]
    if includes:
        if all(re.search(r"/[A-Za-z0-9_]+", s) for s in includes):
            return "scoped"
        return "scoped" if modules else "full"
    # --test-enable with no tags: scoped to the updated modules, else every module.
    return "scoped" if modules else "full"


def _js_generic(args: list[str]) -> str:
    positionals, flags = _positionals(args, JS_VALUE_FLAGS)
    if flags & JS_SCOPING_FLAGS or positionals:
        return "scoped"
    return "full"


def _vitest(args: list[str]) -> str:
    rest = list(args)
    if rest and rest[0] == "related":
        return "scoped"
    if rest and rest[0] in VITEST_SUBCOMMANDS:
        rest = rest[1:]
    return _js_generic(rest)


# Tokens that sit in front of the real command: launchers, interpreters, env tools.
WRAPPERS = {"sudo", "time", "env", "nice", "nohup", "exec", "uv", "run", "poetry",
            "pipenv", "hatch", "pdm", "rye", "npx", "bunx", "pnpx", "dlx", "wsl",
            "python", "python3", "py", "coverage", "timeout", "call"}
WRAPPER_FLAGS = {"-3", "-m", "-e", "--", "-u", "-X", "-W"}
_ENV_ASSIGN = re.compile(r"^\$?(env:)?[A-Za-z_][A-Za-z0-9_]*=")


def _command_start(tokens: list[str]) -> int:
    """Index of the real command after env assignments and wrapper tokens."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        low = _base(tok).removesuffix(".exe")
        if _ENV_ASSIGN.match(tok):
            i += 1
        elif low in WRAPPERS or tok in WRAPPER_FLAGS or re.fullmatch(r"\d+[smh]?", tok):
            i += 1
        elif low in ("pnpm", "yarn", "bun") and i + 1 < len(tokens) and tokens[i + 1] in ("exec", "dlx", "x"):
            i += 2
        else:
            break
    return i


def _split_segments(command: str) -> list[str]:
    """Split on && || ; | and newlines, but never inside quotes."""
    segments, buf, quote, i = [], [], "", 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif command.startswith(("&&", "||"), i):
            segments.append("".join(buf))
            buf = []
            i += 1
        elif ch in ";|\n":
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return [s for s in segments if s.strip()]


def _classify_segment(segment: str) -> tuple[str | None, str | None]:
    tokens = _tokens(segment)
    i = _command_start(tokens)
    if i >= len(tokens):
        return None, None
    tok = tokens[i]
    low = _base(tok).removesuffix(".exe")
    nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
    if low in ("bash", "sh", "zsh") and nxt == "-c" and i + 2 < len(tokens):
        return classify(tokens[i + 2])
    if low == "manage.py" and nxt == "test":
        return "django", _django(tokens[i + 2:])
    if low in ("pytest", "py.test"):
        return "pytest", _pytest(tokens[i + 1:])
    if (low.startswith("odoo-bin") or low in ("odoo", "odoo.py")) and any(
            t.startswith(("--test-enable", "--test-tags")) for t in tokens):
        return "odoo", _odoo(tokens)
    if low in ("npm", "pnpm", "yarn", "bun"):
        if nxt in ("test", "t"):
            return "js", _js_generic(tokens[i + 2:])
        if nxt == "run" and i + 2 < len(tokens) and tokens[i + 2].startswith("test"):
            return "js", _js_generic(tokens[i + 3:])
        if low in ("yarn", "bun") and nxt and not nxt.startswith("-"):
            return _classify_segment(" ".join(shlex.quote(t) for t in tokens[i + 1:]))
        return None, None
    if low == "vitest":
        return "vitest", _vitest(tokens[i + 1:])
    if low == "jest":
        return "jest", _js_generic(tokens[i + 1:])
    if low == "playwright" and nxt == "test":
        return "playwright", _js_generic(tokens[i + 2:])
    return None, None


def classify(command: str) -> tuple[str | None, str | None]:
    """Return (runner, 'full' | 'scoped') for the first test run found, else (None, None)."""
    found: tuple[str | None, str | None] = (None, None)
    for segment in _split_segments(command or ""):
        runner, kind = _classify_segment(segment)
        if kind == "full":
            return runner, kind
        if runner and found == (None, None):
            found = (runner, kind)
    return found


# ------------------------------------------------------------------------ hints

def _nearest_marker_dir(path: str, markers: tuple[str, ...], limit: int = 8) -> str | None:
    folder = os.path.dirname(os.path.abspath(path))
    for _ in range(limit):
        if any(os.path.isfile(os.path.join(folder, m)) for m in markers):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent
    return None


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def suggestion(runner: str, files: list[str]) -> str:
    code = [f for f in files if not f.lower().endswith((".md", ".txt", ".json", ".lock"))]
    head = code[:MAX_LISTED]
    tests = [f for f in head if re.search(r"(^|[\\/])(test_[^\\/]*|[^\\/]*_test\.py|[^\\/]*\.(test|spec)\.[jt]sx?)$", f)]
    if runner == "odoo":
        mods = _unique([os.path.basename(d) for d in
                        (_nearest_marker_dir(f, ("__manifest__.py",)) for f in head) if d])
        if mods:
            tags = ",".join("/" + m for m in mods)
            return ("--test-tags %s on a warm DB (no -u) for Python-only changes; "
                    "add -u %s when a manifest, XML, CSV/ACL or model field changed"
                    % (tags, ",".join(mods)))
        return "--test-tags /<module>[:Class[.test_method]] for the module you changed"
    if runner == "django":
        apps = _unique([os.path.basename(d) for d in
                        (_nearest_marker_dir(f, ("apps.py",)) for f in head) if d])
        if apps:
            return "python manage.py test %s --keepdb" % " ".join(apps)
        return "python manage.py test <app>[.tests.TestClass[.test_method]] --keepdb"
    if runner == "pytest":
        if tests:
            return "pytest %s" % " ".join(tests)
        return "pytest <tests for the changed modules> (path::Class::test), or pytest --lf"
    if runner in ("vitest", "js") and head:
        return "npx vitest related --run %s" % " ".join(head)
    if runner == "jest" and head:
        return "npx jest --findRelatedTests %s" % " ".join(head)
    if runner == "playwright":
        return "npx playwright test <spec for the changed flow> (or --last-failed / --only-changed)"
    return "the tests that cover the files you changed"


def deny_reason(runner: str, files: list[str]) -> str:
    listed = ", ".join(files[:MAX_LISTED]) if files else "(none recorded this session)"
    more = " (+%d more)" % (len(files) - MAX_LISTED) if len(files) > MAX_LISTED else ""
    return (
        "test-scope: this command runs the WHOLE %s test suite. Policy: the full suite "
        "runs only when the user explicitly asked for it, or at a gate a user-invoked "
        "workflow defines (release/integration). During development run the tests for "
        "what changed.\n"
        "Files changed this session: %s%s\n"
        "Scoped alternative: %s\n"
        "Widen to the affected modules/apps (T2) before calling the task done. If the "
        "user did ask for the full suite, re-run the same command prefixed with %s."
        % (runner, listed, more, suggestion(runner, files), OVERRIDE)
    )


def check(data: dict) -> dict | None:
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or tool_input.get("script") or ""
    if not isinstance(command, str) or not command:
        return None
    if OVERRIDE in command.replace(" ", "") or re.search(r"FULL_SUITE\s*=\s*['\"]?1", command):
        runner, kind = classify(command)
        if runner:
            _log(runner, "override")
        return None
    runner, kind = classify(command)
    if kind != "full":
        return None
    files = _load_files(str(data.get("session_id") or "unknown"))
    _log(runner or "unknown", "deny")
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": deny_reason(runner or "unknown", files),
    }}


# ---------------------------------------------------------------------- self-test

SELF_TEST = [
    ("python manage.py test", "django", "full"),
    ("python manage.py test --keepdb --parallel 4", "django", "full"),
    ("python manage.py test users --keepdb", "django", "scoped"),
    ("python manage.py test users.tests.test_api.ApiTest.test_list", "django", "scoped"),
    ("python manage.py test -k login", "django", "scoped"),
    ("cd backend && python manage.py test --settings=config.test", "django", "full"),
    ("pytest", "pytest", "full"),
    ("pytest -q -x", "pytest", "full"),
    ("python -m pytest tests/", "pytest", "full"),
    ("uv run pytest tests/test_auth.py::test_login", "pytest", "scoped"),
    ("pytest -k refund", "pytest", "scoped"),
    ("pytest --lf", "pytest", "scoped"),
    ("pytest -m 'not slow'", "pytest", "full"),
    ("./odoo-bin -c odoo.conf -d db --test-enable --stop-after-init", "odoo", "full"),
    ("python odoo-bin -c c.conf -d db -u all --test-enable --stop-after-init", "odoo", "full"),
    ("odoo-bin -d db --test-tags post_install --stop-after-init", "odoo", "full"),
    ("odoo-bin -d db --test-tags /sale_ext --stop-after-init", "odoo", "scoped"),
    ("odoo-bin -d db --test-tags=/sale_ext:TestOrder.test_confirm --stop-after-init", "odoo", "scoped"),
    ("odoo-bin -d db -u sale_ext --test-enable --stop-after-init", "odoo", "scoped"),
    ("npm test", "js", "full"),
    ("npm run test:run", "js", "full"),
    ("npm run test -- src/cart.test.ts", "js", "scoped"),
    ("npx vitest run", "vitest", "full"),
    ("npx vitest related --run src/cart.ts", "vitest", "scoped"),
    ("npx vitest run --changed", "vitest", "scoped"),
    ("npx jest", "jest", "full"),
    ("npx jest --findRelatedTests src/a.ts", "jest", "scoped"),
    ("npx playwright test", "playwright", "full"),
    ("npx playwright test e2e/login.spec.ts", "playwright", "scoped"),
    ("bash -c 'cd app && pytest'", "pytest", "full"),
    ("bash -c 'cd app && pytest tests/test_a.py'", "pytest", "scoped"),
    ("wsl -e bash -c \"cd /x && ./odoo-bin -d db --test-enable --stop-after-init\"", "odoo", "full"),
    ("DJANGO_SETTINGS_MODULE=cfg.test py -3 manage.py test", "django", "full"),
    ("coverage run -m pytest", "pytest", "full"),
    ("timeout 600 python -m pytest tests/unit/test_x.py", "pytest", "scoped"),
    ("C:/venv/Scripts/python.exe manage.py test orders", "django", "scoped"),
    ("yarn vitest run", "vitest", "full"),
    ("pnpm exec vitest related src/a.ts --run", "vitest", "scoped"),
    ("$env:CI='1'; npm test", "js", "full"),
    ("npm run test:e2e -- --grep checkout", "js", "scoped"),
    ("pytest tests/unit | tail -5", "pytest", "scoped"),
    ("pytest  # run everything", "pytest", "full"),
    ("git status", None, None),
    ("python manage.py migrate", None, None),
    ("grep -r pytest .", None, None),
    ("echo odoo-bin", None, None),
]


def self_test() -> int:
    failures = 0
    for command, runner, kind in SELF_TEST:
        got = classify(command)
        if got != (runner, kind):
            failures += 1
            print("FAIL %-60s expected %s got %s" % (command, (runner, kind), got))
    if check({"tool_input": {"command": "FULL_SUITE=1 pytest"}}) is not None:
        failures += 1
        print("FAIL override was not honoured")
    print("%d/%d classification cases passed" % (len(SELF_TEST) - failures, len(SELF_TEST)))
    return 1 if failures else 0


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--self-test":
        return self_test()
    if os.environ.get("TEST_SCOPE_GUARD", "").lower() in ("off", "0", "false", "disabled"):
        return 0
    watchdog = threading.Timer(3.0, lambda: os._exit(0))
    watchdog.daemon = True
    watchdog.start()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return 0
        mode = argv[1] if len(argv) > 1 else "check"
        if mode == "track":
            track(data)
            return 0
        result = check(data)
        if result:
            sys.stdout.write(json.dumps(result))
            sys.stdout.flush()
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
