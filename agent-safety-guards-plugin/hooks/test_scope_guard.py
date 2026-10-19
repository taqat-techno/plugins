#!/usr/bin/env python3
"""test-scope guard (agent-safety-guards).

One script, two modes:

  track   PostToolUse(Write|Edit|MultiEdit|NotebookEdit), async. Records the edited
          file path for this session so the guard can name what actually changed.
  check   PreToolUse(Bash|PowerShell). When the command runs a WHOLE test suite, react
          according to TEST_SCOPE_GUARD:
            advise (default)   let the run happen and attach the guidance (files changed
                               this session, a scoped command) as PreToolUse
                               additionalContext. Claude reads it with the result, so it
                               steers the NEXT run, not this one.
            enforce            deny, with the same reason. The run does not happen.
            off                do nothing.
          FULL_SUITE=1 as an environment prefix of the test command (`FULL_SUITE=1 pytest`,
          `env FULL_SUITE=1 npm test`, `export FULL_SUITE=1; pytest`, PowerShell
          `$env:FULL_SUITE=1; npm test`) passes untouched in every mode. The same text in a
          comment, an echo or a quoted string does not.
          Mode comes from the TEST_SCOPE_GUARD environment variable, else the plugin option
          `test_scope_guard` (CLAUDE_PLUGIN_OPTION_TEST_SCOPE_GUARD), else advise.

Not a security control: it is a productivity speed bump, and the model can read the
override in the deny reason. Info-only invocations (--help, --version, --collect-only,
--list, --listTests, --showConfig) and test scripts other than the configured
whole-suite names (default: test, test:run, test:all, test:ci; extend with
TEST_SCOPE_FULL_SCRIPTS=a,b or the `full_suite_scripts` option) are never classified.

Both outputs reach the model: a permissionDecision "deny" reason, and
hookSpecificOutput.additionalContext with hookEventName "PreToolUse" (verified on Claude
Code 2.1.282). Plain stdout/stderr with exit 0 does not. See docs/decisions.md D-002.

Fails OPEN everywhere: bad input, an unknown shape, an exception or a slow filesystem
all end in exit 0 with no output, so the tool call proceeds exactly as without the hook.

Policy lives in skills/test-scope/SKILL.md. This script only classifies and reports.
Stdlib only. `--self-test` runs the built-in classification table.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

OVERRIDE = "FULL_SUITE=1"
MAX_LISTED = 8
MAX_TRACKED = 200
STATE_TTL_SECONDS = 7 * 24 * 3600
LOG_CAP_BYTES = 1_000_000

DEFAULT_FULL_SCRIPTS = ("test", "test:run", "test:all", "test:ci")
INFO_FLAGS = {"--help", "-h", "--version", "-V", "--co", "--collect-only", "--list", "--listTests",
              "--list-tests", "--showConfig", "--show-config", "--fixtures", "--markers"}


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
    tool_input = hooklib.tool_input(data)
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
    """Whitespace split with quotes removed and unquoted # comments dropped. Backslashes
    are kept, so Windows paths such as C:\\venv\\Scripts\\python.exe survive."""
    tokens, buf, quote, has = [], [], "", False
    for i, ch in enumerate(segment):
        if quote:
            if ch == quote:
                quote = ""
            else:
                buf.append(ch)
            continue
        if ch in ("'", '"'):
            quote, has = ch, True
            continue
        if ch == "#" and not buf and not has:
            break
        if ch.isspace():
            if buf or has:
                tokens.append("".join(buf))
            buf, has = [], False
            continue
        buf.append(ch)
    if buf or has:
        tokens.append("".join(buf))
    return tokens


def _quote(token: str) -> str:
    return "'" + token.replace("'", "") + "'" if (not token or re.search(r"\s", token)) else token


def full_scripts() -> set[str]:
    names = set(DEFAULT_FULL_SCRIPTS)
    for key in ("TEST_SCOPE_FULL_SCRIPTS", "CLAUDE_PLUGIN_OPTION_FULL_SUITE_SCRIPTS"):
        names |= {n.strip() for n in os.environ.get(key, "").split(",") if n.strip()}
    return names


def _info_only(args: list[str]) -> bool:
    return any(a.split("=", 1)[0] in INFO_FLAGS for a in args)


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
        elif low in ("npx", "bunx", "pnpx") or tok in ("-y", "--yes"):
            i += 1
        else:
            break
    return i


PM_VALUE_FLAGS = {"--prefix", "-w", "--workspace", "--filter", "-F", "-C", "--dir", "--cwd"}


def _pm_args(tokens: list[str], i: int) -> int:
    """Skip package-manager options that sit before the subcommand (npm --prefix web test,
    pnpm --filter web test, yarn workspace web test)."""
    j = i + 1
    while j < len(tokens):
        tok = tokens[j]
        if tok in PM_VALUE_FLAGS:
            j += 2
        elif tok.split("=", 1)[0] in PM_VALUE_FLAGS or tok in ("-r", "--recursive", "-s", "--silent"):
            j += 1
        elif _base(tokens[i]) == "yarn" and tok == "workspace" and j + 1 < len(tokens):
            j += 2
        else:
            break
    return j


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
    if _base(tokens[i]).removesuffix(".exe") not in ("bash", "sh", "zsh") and _info_only(tokens[i + 1:]):
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
        j = _pm_args(tokens, i)
        nxt = tokens[j] if j < len(tokens) else ""
        if nxt in ("test", "t"):
            return "js", _js_generic(tokens[j + 1:])
        if nxt in ("run", "run-script") and j + 1 < len(tokens):
            if tokens[j + 1] in full_scripts():
                return "js", _js_generic(tokens[j + 2:])
            return None, None
        if low in ("yarn", "pnpm", "bun") and nxt in full_scripts():
            return "js", _js_generic(tokens[j + 1:])
        if low in ("yarn", "bun") and nxt and not nxt.startswith("-"):
            return _classify_segment(" ".join(_quote(t) for t in tokens[j:]))
        return None, None
    if low == "vitest":
        return "vitest", _vitest(tokens[i + 1:])
    if low == "jest":
        return "jest", _js_generic(tokens[i + 1:])
    if low == "playwright" and nxt == "test":
        return "playwright", _js_generic(tokens[i + 2:])
    return None, None


_OVERRIDE_TOKEN = re.compile(r"^(?:\$env:)?FULL_SUITE=1$", re.I)
_OVERRIDE_STMT = re.compile(r"^\s*(?:export\s+|set\s+|\$env:)?FULL_SUITE\s*=\s*['\"]?1['\"]?\s*$", re.I)


def _prefix_override(segment: str) -> bool:
    """True when FULL_SUITE=1 is an environment assignment in front of the command."""
    for tok in _tokens(segment):
        if _OVERRIDE_TOKEN.match(tok):
            return True
        if _ENV_ASSIGN.match(tok) or _base(tok) in ("env", "sudo", "time", "nohup"):
            continue
        return False
    return False


def scan(command: str) -> tuple[str | None, str | None, bool]:
    """Return (runner, kind, overridden) for the first whole-suite run, else the first run."""
    found: tuple[str | None, str | None, bool] = (None, None, False)
    exported = False
    for segment in _split_segments(command or ""):
        if _OVERRIDE_STMT.match(segment):
            exported = True
            continue
        runner, kind = _classify_segment(segment)
        overridden = exported or _prefix_override(segment)
        if kind == "full":
            return runner, kind, overridden
        if runner and found[0] is None:
            found = (runner, kind, overridden)
    return found


def classify(command: str) -> tuple[str | None, str | None]:
    """Return (runner, 'full' | 'scoped') for the first test run found, else (None, None)."""
    runner, kind, _ = scan(command)
    return runner, kind


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


def guard_mode() -> str:
    """advise | enforce | off, from TEST_SCOPE_GUARD (docs/decisions.md D-003).

    Unset means advise. A value that is set but not recognised means enforce: someone
    tried to change the default, and the stricter reading is the safe one."""
    value = (os.environ.get("TEST_SCOPE_GUARD", "").strip()
             or os.environ.get("CLAUDE_PLUGIN_OPTION_TEST_SCOPE_GUARD", "").strip()).lower()
    if not value or value in ("advise", "advice", "warn", "soft"):
        return "advise"
    if value in ("off", "0", "false", "disabled"):
        return "off"
    return "enforce"


def advise_text(runner: str, files: list[str]) -> str:
    listed = ", ".join(files[:MAX_LISTED]) if files else "(none recorded this session)"
    more = " (+%d more)" % (len(files) - MAX_LISTED) if len(files) > MAX_LISTED else ""
    return (
        "test-scope (advise mode): the command you just ran is the WHOLE %s test suite. "
        "Unless the user asked for it or a user-invoked release/integration gate requires "
        "it, the next run should cover only what changed.\n"
        "Files changed this session: %s%s\n"
        "Scoped alternative: %s\n"
        "Widen to the affected modules/apps (T2) before calling the task done."
        % (runner, listed, more, suggestion(runner, files))
    )


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
    tool_input = hooklib.tool_input(data)
    command = tool_input.get("command") or tool_input.get("script") or ""
    if not isinstance(command, str) or not command:
        return None
    runner, kind, overridden = scan(command)
    if kind != "full":
        return None
    if overridden:
        _log(runner or "unknown", "override")
        return None
    files = _load_files(str(data.get("session_id") or "unknown"))
    if guard_mode() == "advise":
        _log(runner or "unknown", "advise")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": advise_text(runner or "unknown", files),
        }}
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
    ("npm run test:e2e -- --grep checkout", None, None),
    ("npm run test:unit", None, None),
    ("npm run testing-docs", None, None),
    ("npm run test:all", "js", "full"),
    ("pytest --help", None, None),
    ("pytest --co -q", None, None),
    ("python -m pytest --collect-only -q", None, None),
    ("npx jest --version", None, None),
    ("npx playwright test --list", None, None),
    ("npx jest --listTests", None, None),
    ("C:\\venv\\Scripts\\python.exe -m pytest", "pytest", "full"),
    ("C:\\venv\\Scripts\\python.exe -m pytest tests\\test_a.py", "pytest", "scoped"),
    ("npx -y vitest run", "vitest", "full"),
    ("npx --yes jest", "jest", "full"),
    ("npm --prefix web test", "js", "full"),
    ("npm -w web run test", "js", "full"),
    ("pnpm --filter web test", "js", "full"),
    ("yarn workspace web test", "js", "full"),
    ("pnpm --filter web run test:unit", None, None),
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
    for command in ("FULL_SUITE=1 pytest", "env FULL_SUITE=1 npm test", "export FULL_SUITE=1; pytest",
                    "$env:FULL_SUITE=1; npm test"):
        if not scan(command)[2]:
            failures += 1
            print("FAIL override was not honoured: %s" % command)
    for command in ("pytest # FULL_SUITE=1", "echo FULL_SUITE=1; pytest", "pytest -k 'FULL_SUITE=1' ."):
        if scan(command)[1] == "full" and scan(command)[2]:
            failures += 1
            print("FAIL override honoured outside an env prefix: %s" % command)
    print("%d/%d classification cases passed" % (len(SELF_TEST) - failures, len(SELF_TEST)))
    return 1 if failures else 0


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--self-test":
        return self_test()
    if guard_mode() == "off":
        return 0
    hooklib.watchdog(3)
    data = hooklib.read_payload()
    if data is None:
        return 0
    if (argv[1] if len(argv) > 1 else "check") == "track":
        track(data)
        return 0
    result = check(data)
    if result:
        out = result["hookSpecificOutput"]
        if out.get("permissionDecision") == "deny":
            hooklib.deny(out["permissionDecisionReason"])
        else:
            hooklib.context("PreToolUse", out["additionalContext"])
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    hooklib.run(lambda: main(sys.argv))
