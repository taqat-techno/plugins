"""Execute agent.py inside the runtime that hosts a local service.

One entry point, `call(runtime, distro, request)`:

* runtime "wsl" from Windows -> `wsl.exe -d <distro> -- bash -s`, the script on STDIN.
  No command text is ever quoted through `bash -lc "..."`: the request travels as
  base64 JSON in an exported variable and the agent source as a quoted heredoc.
* runtime "wsl"/"linux" when this server already runs on Linux -> `bash -s` locally.
* runtime "windows" -> the current Python runs agent.py by path.

Output is decoded as UTF-8; the result is the last `ODOO_LOCAL_RESULT=` line.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.join(HERE, "agent.py")
MARK = "ODOO_LOCAL_RESULT="
HEREDOC = "ODOO_LOCAL_AGENT_EOF"


class RunnerError(Exception):
    pass


def _b64(request: dict) -> str:
    return base64.b64encode(json.dumps(request).encode("utf-8")).decode("ascii")


def build_script(request: dict) -> str:
    """The bash script piped to `bash -s`. Pure function (unit-tested)."""
    with open(AGENT, encoding="utf-8") as fh:
        source = fh.read()
    if HEREDOC in source:
        raise RunnerError("agent source contains the heredoc terminator")
    return (
        "set -euo pipefail\n"
        "export ODOO_LOCAL_ARGS='%s'\n"  # base64 alphabet has no quote characters
        "exec python3 - <<'%s'\n%s\n%s\n" % (_b64(request), HEREDOC, source, HEREDOC)
    )


def parse_output(stdout: str, stderr: str, rc: int) -> dict:
    for line in reversed(stdout.splitlines()):
        if line.startswith(MARK):
            try:
                return json.loads(line[len(MARK):])
            except ValueError:
                break
    tail = (stderr or stdout).strip().splitlines()[-5:]
    return {"ok": False, "error": "agent gave no result (rc %s): %s" % (rc, " | ".join(tail) or "no output")}


def _exec(argv, stdin_bytes, timeout, env=None) -> dict:
    try:
        p = subprocess.run(argv, input=stdin_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, env=env)
    except FileNotFoundError:
        return {"ok": False, "error": "cannot run %s (not installed?)" % argv[0]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timed out after %ss; long work must go through a background job" % timeout}
    return parse_output(p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), p.returncode)


def call(runtime: str, distro, request: dict, timeout: int = 90) -> dict:
    if runtime in ("wsl", "linux"):
        script = build_script(request).encode("utf-8")
        if sys.platform == "win32":
            if not distro:
                return {"ok": False, "error": "a wsl service needs wsl_distro"}
            argv = ["wsl.exe", "-d", distro, "--", "bash", "-s"]
        else:
            argv = ["bash", "-s"]
        return _exec(argv, script, timeout)
    if runtime == "windows":
        env = dict(os.environ, ODOO_LOCAL_ARGS=_b64(request), PYTHONIOENCODING="utf-8")
        return _exec([sys.executable, AGENT], None, timeout, env=env)
    return {"ok": False, "error": "runtime %r is not managed by odoo-local (docker: use the odoo docker skill)" % runtime}


def list_distros() -> list:
    if sys.platform != "win32":
        return []
    try:
        p = subprocess.run(["wsl.exe", "-l", "-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    raw = p.stdout
    text = raw.decode("utf-16-le", "replace") if raw[:2] == b"\xff\xfe" or b"\x00" in raw[:10] else raw.decode("utf-8", "replace")
    return [d.strip().lstrip("﻿") for d in text.splitlines()
            if d.strip() and not d.strip().lstrip("﻿").startswith("docker-desktop")]
