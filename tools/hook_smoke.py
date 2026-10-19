#!/usr/bin/env python3
"""Run every registered hook command once with an empty payload and expect exit 0.

This catches the launch failures that are invisible in daily use: an interpreter name
that doesn't exist on this OS, an unquoted path, a script that isn't executable, or a hook
that crashes instead of failing open. Hooks receive `{}` on stdin, a temporary HOME and
CLAUDE_PLUGIN_DATA, and no network, so they should all decide there is nothing to do.

    python tools/hook_smoke.py [plugin-dir ...]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 30


def hooks_of(plugin: Path):
    path = plugin / "hooks" / "hooks.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    yield event, group.get("matcher", ""), hook


def run_hook(plugin: Path, event: str, hook: dict, tmp: Path) -> tuple[int, str]:
    root = plugin.resolve().as_posix()
    data = tmp / "data" / plugin.name
    data.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=root, CLAUDE_PLUGIN_DATA=data.as_posix(),
               CLAUDE_PROJECT_DIR=tmp.as_posix(), HOME=tmp.as_posix(), USERPROFILE=str(tmp),
               NOTIFICATION_DRY_RUN="1")
    payload = json.dumps({"hook_event_name": event, "session_id": "smoke", "cwd": tmp.as_posix()})
    sub = lambda s: s.replace("${CLAUDE_PLUGIN_ROOT}", root).replace("${CLAUDE_PLUGIN_DATA}", data.as_posix())
    if hook.get("args") is not None:  # exec form: no shell involved
        argv = [sub(hook["command"])] + [sub(a) for a in hook["args"]]
        exe = shutil.which(argv[0])
        if exe is None:
            return 127, f"interpreter {argv[0]!r} not found on PATH"
        argv[0] = exe
    else:
        bash = shutil.which("bash")
        if bash is None:
            return 0, "skipped: no bash"
        argv = [bash, "-c", hook["command"]]
    try:
        proc = subprocess.run(argv, input=payload.encode("utf-8"), capture_output=True,
                              env=env, cwd=tmp, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    tail = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
    return proc.returncode, tail[0][:200]


def main(argv: list[str]) -> int:
    plugins = [ROOT / a for a in argv] if argv else sorted(ROOT.glob("*-plugin"))
    failures = 0
    with tempfile.TemporaryDirectory(prefix="hook-smoke-") as t:
        tmp = Path(t)
        for plugin in plugins:
            for event, matcher, hook in hooks_of(plugin):
                code, note = run_hook(plugin, event, hook, tmp)
                ok = code == 0
                failures += not ok
                label = f"{plugin.name} {event}{'/' + matcher if matcher else ''}"
                print(f"{'ok  ' if ok else 'FAIL'} {label}" + (f"  (exit {code}: {note})" if not ok else ""))
    print(f"hook smoke: {'ok' if not failures else f'{failures} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
