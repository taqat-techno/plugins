"""Runs the node:test suite for scripts/ado-events.js and checks its CLI contract offline."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
SCRIPT = PLUGIN / "scripts" / "ado-events.js"

pytestmark = pytest.mark.skipif(not NODE, reason="node not installed")


def test_node_suite_passes():
    p = subprocess.run([NODE, "--test", str(PLUGIN / "tests" / "ado_events.test.js")],
                       capture_output=True, timeout=120, cwd=str(PLUGIN))
    assert p.returncode == 0, (p.stdout + p.stderr).decode(errors="replace")[-3000:]


def _cli(args, env):
    return subprocess.run([NODE, str(SCRIPT), *args], capture_output=True, timeout=30,
                          env={"SystemRoot": "C:\\Windows", **env})


def test_cli_requires_since():
    p = _cli([], {"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t"})
    assert p.returncode == 1 and b"--since" in p.stderr


def test_cli_refuses_without_a_token_and_never_calls_out():
    p = _cli(["--since", "now"], {"ADO_ORGANIZATION": "contoso"})
    assert p.returncode == 1 and b"Personal Access Token" in p.stderr


def test_cli_rejects_a_bad_cursor_without_echoing_the_token():
    p = _cli(["--since", "garbage"], {"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "s3cr3t-value"})
    assert p.returncode == 1 and b"not valid" in p.stderr and b"s3cr3t-value" not in p.stdout + p.stderr


def test_cli_reads_the_pat_from_a_file_and_names_a_missing_one(tmp_path):
    p = _cli(["--since", "now"], {"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN_FILE": str(tmp_path / "nope.txt")})
    assert p.returncode == 1 and b"nope.txt" in p.stderr


def test_script_is_read_only_by_construction():
    src = SCRIPT.read_text(encoding="utf-8")
    assert '"PUT"' not in src and '"PATCH"' not in src and '"DELETE"' not in src
    # The only POST is the work item query (WIQL), which reads.
    assert src.count('request("POST"') == 1 and "/_apis/wit/wiql" in src
    assert "writeFile" not in src and "appendFile" not in src
