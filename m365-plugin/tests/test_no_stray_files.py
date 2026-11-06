"""No junk may be created inside the plugin by the test run (a stripped environment once made Windows create a
'%SystemDrive%' folder here, and it was committed by mistake)."""
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent


def test_plugin_folder_holds_only_expected_top_level_entries():
    expected = {".claude-plugin", ".mcp.json", "CHANGELOG.md", "LICENSE", "README.md", "commands", "data", "docs", "hooks",
                "scripts", "server", "skills", "tests", ".pytest_cache", "__pycache__"}
    extra = {p.name for p in PLUGIN.iterdir()} - expected
    assert not extra, f"unexpected entries in the plugin folder: {sorted(extra)}"


def test_no_stray_files_are_tracked_by_git():
    out = subprocess.run(["git", "ls-files", "--", str(PLUGIN)], capture_output=True, text=True, cwd=str(PLUGIN))
    if out.returncode != 0:
        return  # not a git checkout (an exported copy): nothing to check
    bad = [f for f in out.stdout.splitlines() if "%" in f or f.endswith((".db", ".pyc", ".tmp"))]
    assert not bad, bad
