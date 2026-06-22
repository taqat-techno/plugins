"""
Plugin structure tests for the Django plugin.

Validates that all expected files exist, plugin.json / hooks.json / marketplace
registration are valid, and skill/command/agent front-matter is well-formed.

Run:  pytest django-plugin/tests/test_plugin_structure.py
"""

import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"
COMMANDS_DIR = PLUGIN_ROOT / "commands"
AGENTS_DIR = PLUGIN_ROOT / "agents"
HOOKS_DIR = PLUGIN_ROOT / "hooks"


# ─── File existence ───────────────────────────────────────────────

EXPECTED_FILES = [
    ".claude-plugin/plugin.json",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "hooks/hooks.json",
    "hooks/session_start.py",
    "hooks/pre_write_guard.py",
    "hooks/pre_bash_guard.py",
    "commands/django-scaffold.md",
    "commands/django-migrate.md",
    "commands/django-test.md",
    "commands/django-security.md",
    "agents/migration-safety-analyzer.md",
    "agents/django-security-auditor.md",
    "agents/orm-query-optimizer.md",
    "skills/django-orm-models/SKILL.md",
    "skills/django-migrations/SKILL.md",
    "skills/django-views-drf/SKILL.md",
    "skills/django-settings-config/SKILL.md",
    "skills/django-security-audit/SKILL.md",
    "skills/django-testing/SKILL.md",
    "skills/django-performance/SKILL.md",
]


@pytest.mark.parametrize("rel", EXPECTED_FILES)
def test_expected_file_exists(rel):
    assert (PLUGIN_ROOT / rel).is_file(), f"missing {rel}"


# ─── Manifest ─────────────────────────────────────────────────────

def test_plugin_json_valid():
    manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "django"
    assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"]), "version must be semver"
    assert manifest.get("description")
    assert manifest.get("author", {}).get("name")


def test_registered_in_marketplace():
    market = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    names = {p["name"] for p in market["plugins"]}
    assert "django" in names, "django not registered in marketplace.json"
    entry = next(p for p in market["plugins"] if p["name"] == "django")
    assert entry["source"] == "./django-plugin"


# ─── Hooks wiring ─────────────────────────────────────────────────

def test_hooks_json_valid_and_points_at_real_files():
    hooks = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    events = hooks["hooks"]
    assert "SessionStart" in events and "PreToolUse" in events
    # Every referenced script must exist on disk.
    blob = json.dumps(events)
    for script in re.findall(r"hooks/([\w_]+\.py)", blob):
        assert (HOOKS_DIR / script).is_file(), f"hook references missing script {script}"


# ─── Front-matter ─────────────────────────────────────────────────

def _front_matter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} missing front-matter"
    return text.split("---", 2)[1]


@pytest.mark.parametrize("skill", sorted(SKILLS_DIR.glob("*/SKILL.md")))
def test_skill_front_matter(skill):
    fm = _front_matter(skill)
    for key in ("name:", "description:", "version:"):
        assert key in fm, f"{skill.parent.name} skill missing {key}"


@pytest.mark.parametrize("cmd", sorted(COMMANDS_DIR.glob("*.md")))
def test_command_front_matter(cmd):
    fm = _front_matter(cmd)
    assert "description:" in fm, f"{cmd.name} missing description"


@pytest.mark.parametrize("agent", sorted(AGENTS_DIR.glob("*.md")))
def test_agent_front_matter(agent):
    fm = _front_matter(agent)
    assert "name:" in fm and "description:" in fm, f"{agent.name} missing name/description"
