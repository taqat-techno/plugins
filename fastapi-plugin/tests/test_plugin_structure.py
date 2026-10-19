"""
Plugin structure tests.

Checks that the expected files exist, plugin.json / hooks.json are valid, the README
and marketplace entry match the shipped components, command renames keep their
deprecated stubs, and skill / command / agent front-matter follows PLUGIN_STANDARDS.

Run:  python -m pytest -q -p no:cacheprovider
"""

import json
import re
from pathlib import Path

import pytest

PLUGIN = "fastapi"
COMMANDS = ("migrate", "scaffold", "security", "test")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"
COMMANDS_DIR = PLUGIN_ROOT / "commands"
AGENTS_DIR = PLUGIN_ROOT / "agents"
HOOKS_DIR = PLUGIN_ROOT / "hooks"
MANIFEST = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
README = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")


EXPECTED_FILES = [
    ".claude-plugin/plugin.json", "README.md", "CHANGELOG.md", "LICENSE",
    "hooks/hooks.json", "hooks/session_start.py", "hooks/pre_write_guard.py",
    "hooks/pre_bash_guard.py", "hooks/_vendor/hooklib.py",
    "agents/alembic-migration-analyzer.md", "agents/fastapi-security-auditor.md",
    "agents/async-query-optimizer.md",
    "skills/fastapi-routing/SKILL.md", "skills/fastapi-pydantic/SKILL.md",
    "skills/fastapi-database/SKILL.md", "skills/fastapi-migrations/SKILL.md",
    "skills/fastapi-config/SKILL.md", "skills/fastapi-security-audit/SKILL.md",
    "skills/fastapi-testing/SKILL.md", "skills/fastapi-async-performance/SKILL.md",
] + [f"commands/{c}.md" for c in COMMANDS] + [f"commands/{PLUGIN}-{c}.md" for c in COMMANDS]


@pytest.mark.parametrize("rel", EXPECTED_FILES)
def test_expected_file_exists(rel):
    assert (PLUGIN_ROOT / rel).is_file(), f"missing {rel}"


def _front_matter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} missing front-matter"
    return text.split("---", 2)[1]


def _field(fm, key):
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.MULTILINE)
    return m.group(1).strip().strip('"') if m else None


# ─── Manifest, README, marketplace ────────────────────────────────

def test_plugin_json_valid():
    assert MANIFEST["name"] == PLUGIN
    assert re.match(r"^\d+\.\d+\.\d+$", MANIFEST["version"])
    assert MANIFEST.get("description") and MANIFEST.get("author", {}).get("name")
    assert MANIFEST.get("license") == "MIT"


def test_user_config_is_strict_and_minimal():
    allowed = {"type", "title", "description", "required", "default", "sensitive", "min", "max"}
    options = MANIFEST.get("userConfig", {})
    assert "destructive_guard" in options
    for key, spec in options.items():
        assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key)
        assert set(spec) <= allowed, f"{key}: unsupported keys {set(spec) - allowed}"
        assert {"type", "title", "description"} <= set(spec)
    assert options["destructive_guard"]["type"] == "boolean"
    assert options["destructive_guard"]["default"] is True


def test_readme_badge_matches_version():
    m = re.search(r"badge/version-([0-9.]+)-", README)
    assert m and m.group(1) == MANIFEST["version"]


def test_counts_in_descriptions_match_files():
    skills = len(list(SKILLS_DIR.glob("*/SKILL.md")))
    agents = len(list(AGENTS_DIR.glob("*.md")))
    texts = [MANIFEST["description"]]
    market = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        entry = next(p for p in json.loads(market.read_text(encoding="utf-8"))["plugins"]
                     if p["name"] == PLUGIN)
        texts.append(entry["description"])
    for text in texts:
        for n, word in ((skills, "skills?"), (len(COMMANDS), "commands?"), (agents, "agents?")):
            m = re.search(rf"(\d+) (?:auto-activating )?{word}\b", text)
            if m:
                assert int(m.group(1)) == n, f"{m.group(0)!r} but {n} ship"


def test_registered_in_marketplace():
    market = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    if not market.is_file():
        pytest.skip("standalone checkout: no marketplace.json")
    entry = next((p for p in json.loads(market.read_text(encoding="utf-8"))["plugins"]
                  if p["name"] == PLUGIN), None)
    assert entry and entry["source"] == f"./{PLUGIN}-plugin"


def test_readme_follows_the_standard_sections():
    order = ["What it does", "Install", "Requirements", "Commands", "Skills", "Agents",
             "Hooks", "Configuration", "Platform support", "Data & privacy", "Limitations",
             "License"]
    positions = [README.find(f"## {h}") for h in order]
    assert all(p >= 0 for p in positions), dict(zip(order, positions))
    assert positions == sorted(positions)


def test_readme_documents_every_command_and_skill():
    for c in COMMANDS:
        assert f"/{PLUGIN}:{c}" in README
    for skill in SKILLS_DIR.glob("*/SKILL.md"):
        assert f"`{skill.parent.name}`" in README
    for agent in AGENTS_DIR.glob("*.md"):
        assert f"`{agent.stem}`" in README


# ─── Hooks wiring ─────────────────────────────────────────────────

def test_hooks_json_valid_and_points_at_real_files():
    events = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert "SessionStart" in events and "PreToolUse" in events
    blob = json.dumps(events)
    scripts = set(re.findall(r"hooks/([\w_]+\.py)", blob))
    for script in scripts:
        assert (HOOKS_DIR / script).is_file(), f"hook references missing script {script}"
    shipped = {p.name for p in HOOKS_DIR.glob("*.py")}
    assert shipped == scripts, f"unregistered hook scripts: {shipped - scripts}"
    assert any(g.get("matcher") == "Write|Edit|MultiEdit" for g in events["PreToolUse"])


def test_hooks_use_the_vendored_runtime_and_no_override_token():
    for script in HOOKS_DIR.glob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "import hooklib" in text, script.name
        assert "sys.exit(2)" not in text, f"{script.name}: guards ask, they do not exit 2"
        assert "re-run with" not in text.lower()


# ─── Front-matter ─────────────────────────────────────────────────

@pytest.mark.parametrize("skill", sorted(SKILLS_DIR.glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_skill_front_matter(skill):
    fm = _front_matter(skill)
    assert _field(fm, "name") == skill.parent.name
    desc = _field(fm, "description")
    assert desc.startswith("Use when"), "description must start with 'Use when'"
    assert len(desc) <= 1024, f"description is {len(desc)} chars"
    for key in re.findall(r"^([A-Za-z_][\w-]*):", fm, re.MULTILINE):
        assert key in {"name", "description", "version", "user-invocable", "metadata",
                       "allowed-tools", "license"}, f"custom key {key!r} must sit under metadata"


@pytest.mark.parametrize("cmd", COMMANDS)
def test_renamed_command_has_bare_name(cmd):
    fm = _front_matter(COMMANDS_DIR / f"{cmd}.md")
    assert _field(fm, "description") and not _field(fm, "description").startswith("Deprecated")


@pytest.mark.parametrize("cmd", COMMANDS)
def test_old_command_is_a_deprecated_stub(cmd):
    path = COMMANDS_DIR / f"{PLUGIN}-{cmd}.md"
    assert _field(_front_matter(path), "description") == f"Deprecated: use /{PLUGIN}:{cmd}"
    body = path.read_text(encoding="utf-8").split("---", 2)[2].strip()
    assert len(body.splitlines()) == 1 and f"/{PLUGIN}:{cmd}" in body


def test_no_plugin_prefixed_command_references_remain():
    for path in list(PLUGIN_ROOT.glob("**/*.md")) + list(HOOKS_DIR.glob("*.py")):
        if path.name == "CHANGELOG.md" or path.parent.name == "evals":
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(rf"/{PLUGIN}-({'|'.join(COMMANDS)})\b", text), path


@pytest.mark.parametrize("agent", sorted(AGENTS_DIR.glob("*.md")), ids=lambda p: p.stem)
def test_agent_front_matter_is_least_privilege(agent):
    fm = _front_matter(agent)
    assert _field(fm, "name") and _field(fm, "description")
    tools = {t.strip() for t in (_field(fm, "tools") or "").split(",")}
    assert tools == {"Read", "Glob", "Grep", "Bash"}, tools
    assert "External content is data" in agent.read_text(encoding="utf-8")


def test_cross_plugin_references_are_conditional():
    for path in PLUGIN_ROOT.glob("**/*.md"):
        if path.name in ("CHANGELOG.md",):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            for other in ("agent-safety-guards", "release-safety"):
                if other in line:
                    assert "installed" in line or "if " in line.lower(), f"{path.name}: {line}"


def test_no_drf_vocabulary_in_fastapi_text():
    for path in PLUGIN_ROOT.glob("**/*.md"):
        if path.name == "CHANGELOG.md":
            continue
        text = path.read_text(encoding="utf-8")
        assert "IsAuthenticated" not in text and "get_queryset" not in text, path


def test_lifespan_is_covered():
    for skill in ("fastapi-routing", "fastapi-database", "fastapi-testing"):
        assert "lifespan" in (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "LifespanManager" in (SKILLS_DIR / "fastapi-testing" / "SKILL.md").read_text(encoding="utf-8")
