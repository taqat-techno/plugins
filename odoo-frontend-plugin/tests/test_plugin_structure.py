"""
Plugin structure tests for the Odoo Frontend plugin.

Validates that all expected files exist, deleted files are gone,
plugin.json is valid, hooks are consistent, and cross-references are clean.
"""

import json
import pytest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).parent.parent
DATA_DIR = PLUGIN_ROOT / "data"
SKILLS_DIR = PLUGIN_ROOT / "skills"
COMMANDS_DIR = PLUGIN_ROOT / "commands"
HOOKS_DIR = PLUGIN_ROOT / "hooks"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"


# ─── File Existence ──────────────────────────────────────────────


class TestFileExistence:
    """Verify all expected files exist."""

    @pytest.mark.parametrize("path", [
        ".claude-plugin/plugin.json",
        "agents/theme-generator.md",
        "rules/core-odoo-guard.md",
        "rules/scss-load-order.md",
        "skills/theme-create/SKILL.md",
        "skills/theme-scss/SKILL.md",
        "skills/theme-scss/REFERENCE.md",
        "skills/theme-design/SKILL.md",
        "skills/theme-snippets/SKILL.md",
        "skills/theme-snippets/REFERENCE.md",
        "skills/frontend-js/SKILL.md",
        "commands/create-theme.md",
        "commands/odoo-frontend.md",
        "hooks/hooks.json",
        "hooks/pre_write_check.py",
        "hooks/post_write_check.py",
        "hooks/session_start.py",
        "data/color_palettes.json",
        "data/theme_templates.json",
        "data/typography_defaults.json",
        "data/version_mapping.json",
        "data/figma_prompts.json",
        "scripts/bootstrap_mapper.py",
        "scripts/version_detector.py",
        "README.md",
    ])
    def test_expected_file_exists(self, path):
        assert (PLUGIN_ROOT / path).exists(), f"Expected file missing: {path}"


class TestDeletedFilesGone:
    """Verify obsolete files from pre-v8.1 are deleted."""

    @pytest.mark.parametrize("path", [
        "scripts/create_theme.py",
        "scripts/devtools_extractor.py",
        "scripts/pwa_generator.py",
        "scripts/figma_converter.py",
        "scripts/theme_mirror_generator.py",
        "templates/theme_module/__manifest__.py.template",
    ])
    def test_deleted_file_absent(self, path):
        full = PLUGIN_ROOT / path
        assert not full.exists(), f"Obsolete file should be deleted: {path}"


# ─── Plugin JSON ─────────────────────────────────────────────────


class TestPluginJson:
    """Verify plugin.json is valid and up-to-date."""

    @pytest.fixture(scope="class")
    def plugin_config(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            return json.load(f)

    def test_version_is_8(self, plugin_config):
        assert plugin_config["version"].startswith("8."), f"Plugin version should be 8.x, got {plugin_config['version']}"

    def test_has_name(self, plugin_config):
        assert plugin_config["name"] == "odoo-frontend"

    def test_has_author(self, plugin_config):
        assert "author" in plugin_config

    def test_has_keywords(self, plugin_config):
        assert "keywords" in plugin_config
        assert isinstance(plugin_config["keywords"], list)
        assert len(plugin_config["keywords"]) >= 5


# ─── JSON Syntax ─────────────────────────────────────────────────


class TestJsonSyntax:
    """Verify all JSON data files parse correctly."""

    @pytest.mark.parametrize("path", [
        "data/color_palettes.json",
        "data/theme_templates.json",
        "data/typography_defaults.json",
        "data/version_mapping.json",
        "data/figma_prompts.json",
        "hooks/hooks.json",
        ".claude-plugin/plugin.json",
    ])
    def test_json_parses(self, path):
        full = PLUGIN_ROOT / path
        with open(full) as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{path} should parse to a dict"


# ─── Hooks Consistency ───────────────────────────────────────────


class TestHooksConsistency:
    """Verify hooks.json references existing scripts."""

    @pytest.fixture(scope="class")
    def hooks_config(self):
        with open(HOOKS_DIR / "hooks.json") as f:
            return json.load(f)

    def test_has_pre_tool_use(self, hooks_config):
        assert "PreToolUse" in hooks_config.get("hooks", {}), "Should have PreToolUse hooks"

    def test_has_post_tool_use(self, hooks_config):
        assert "PostToolUse" in hooks_config.get("hooks", {}), "Should have PostToolUse hooks"

    def test_has_session_start(self, hooks_config):
        assert "SessionStart" in hooks_config.get("hooks", {}), "Should have SessionStart hook"

    def test_hook_scripts_exist(self, hooks_config):
        for event_name, event_hooks in hooks_config.get("hooks", {}).items():
            for hook_group in event_hooks:
                for hook in hook_group.get("hooks", []):
                    command = hook.get("command", "")
                    # Extract .py script references
                    for part in command.split():
                        if part.endswith('.py"') or part.endswith(".py"):
                            script_name = part.strip('"').split("/")[-1]
                            assert (HOOKS_DIR / script_name).exists(), (
                                f"hooks.json references missing script: {script_name}"
                            )


# ─── Version Mapping ─────────────────────────────────────────────


class TestVersionMapping:
    """Verify version_mapping.json covers all Odoo versions."""

    @pytest.fixture(scope="class")
    def version_map(self):
        with open(DATA_DIR / "version_mapping.json") as f:
            return json.load(f)

    @pytest.mark.parametrize("version", ["14", "15", "16", "17", "18", "19"])
    def test_odoo_version_exists(self, version_map, version):
        versions = version_map.get("odoo_versions", {})
        assert version in versions, f"Missing Odoo version {version} in version_mapping.json"

    def test_each_version_has_bootstrap(self, version_map):
        for ver, config in version_map.get("odoo_versions", {}).items():
            assert "bootstrap_version" in config, f"Version {ver} missing bootstrap_version"

    def test_bootstrap_4_for_old_versions(self, version_map):
        versions = version_map.get("odoo_versions", {})
        for ver in ["14", "15"]:
            if ver in versions:
                bs = versions[ver]["bootstrap_version"]
                assert bs.startswith("4."), f"Odoo {ver} should use Bootstrap 4, got {bs}"

    def test_bootstrap_5_for_new_versions(self, version_map):
        versions = version_map.get("odoo_versions", {})
        for ver in ["16", "17", "18", "19"]:
            if ver in versions:
                bs = versions[ver]["bootstrap_version"]
                assert bs.startswith("5."), f"Odoo {ver} should use Bootstrap 5, got {bs}"


# ─── Color Palettes ──────────────────────────────────────────────


class TestColorPalettes:
    """Verify color_palettes.json has correct structure."""

    @pytest.fixture(scope="class")
    def palettes(self):
        with open(DATA_DIR / "color_palettes.json") as f:
            return json.load(f)

    def test_has_5_semantic_colors(self, palettes):
        colors = palettes.get("semantic_colors", {})
        for i in range(1, 6):
            key = f"o-color-{i}"
            assert key in colors, f"Missing semantic color: {key}"

    def test_has_preset_palettes(self, palettes):
        presets = palettes.get("preset_palettes", {})
        assert len(presets) >= 3, f"Should have at least 3 preset palettes, got {len(presets)}"

    def test_presets_have_hex_values(self, palettes):
        for name, palette in palettes.get("preset_palettes", {}).items():
            colors = palette.get("colors", {})
            for color_key, hex_val in colors.items():
                assert hex_val.startswith("#"), f"Palette {name}.{color_key} should be hex, got {hex_val}"


# ─── Skill References ────────────────────────────────────────────


class TestSkillReferences:
    """Verify skills don't reference deleted files."""

    DELETED_SCRIPTS = [
        "scripts/create_theme",
        "scripts/devtools_extractor",
        "scripts/pwa_generator",
        "scripts/figma_converter",
    ]

    def test_skills_no_deleted_references(self):
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            content = skill_file.read_text(encoding="utf-8")
            for deleted in self.DELETED_SCRIPTS:
                assert deleted not in content, (
                    f"{skill_dir.name}/SKILL.md references deleted {deleted}"
                )


# ─── Command Files ───────────────────────────────────────────────


class TestCommandFiles:
    """Verify command files have required structure."""

    EXPECTED_COMMANDS = ["create-theme", "odoo-frontend"]

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_exists(self, cmd):
        assert (COMMANDS_DIR / f"{cmd}.md").exists(), f"Command file missing: {cmd}.md"

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_has_frontmatter(self, cmd):
        content = (COMMANDS_DIR / f"{cmd}.md").read_text(encoding="utf-8")
        assert "title:" in content, f"{cmd}.md missing title in frontmatter"
        assert "type:" in content, f"{cmd}.md missing type in frontmatter"


# ─── SessionStart Hook ───────────────────────────────────────────


class TestSessionStartHook:
    """Verify SessionStart hook is properly configured."""

    def test_session_start_script_exists(self):
        assert (HOOKS_DIR / "session_start.py").exists(), "hooks/session_start.py not found"

    def test_hooks_json_has_session_start(self):
        with open(HOOKS_DIR / "hooks.json") as f:
            config = json.load(f)
        assert "SessionStart" in config.get("hooks", {}), "hooks.json missing SessionStart"

    def test_session_start_has_version_detection(self):
        content = (HOOKS_DIR / "session_start.py").read_text(encoding="utf-8")
        has_detection = "version" in content.lower() or "detect" in content.lower() or "odoo" in content.lower()
        assert has_detection, "session_start.py should contain version detection logic"


# ─── Figma Prompts ───────────────────────────────────────────────


class TestFigmaPrompts:
    """Verify figma_prompts.json has required prompts."""

    @pytest.fixture(scope="class")
    def prompts(self):
        with open(DATA_DIR / "figma_prompts.json") as f:
            return json.load(f)

    def test_has_prompts_key(self, prompts):
        assert "prompts" in prompts

    @pytest.mark.parametrize("prompt_type", [
        "basic_html", "odoo_component", "page_template",
        "color_extraction", "typography_extraction", "layout_extraction",
    ])
    def test_has_required_prompts(self, prompts, prompt_type):
        assert prompt_type in prompts["prompts"], f"Missing prompt: {prompt_type}"

    def test_prompts_have_placeholders(self, prompts):
        for name, text in prompts["prompts"].items():
            if name in ["basic_html", "odoo_component", "page_template", "typography_extraction", "layout_extraction"]:
                assert "{bootstrap_version}" in text, f"Prompt {name} missing {{bootstrap_version}} placeholder"


# ─── Rules ───────────────────────────────────────────────────────


RULES_DIR = PLUGIN_ROOT / "rules"
AGENTS_DIR = PLUGIN_ROOT / "agents"


class TestRulesExist:
    """Verify rules files exist and contain key terms."""

    def test_core_odoo_guard_exists(self):
        assert (RULES_DIR / "core-odoo-guard.md").exists()

    def test_core_odoo_guard_content(self):
        content = (RULES_DIR / "core-odoo-guard.md").read_text(encoding="utf-8")
        assert "NEVER" in content, "core-odoo-guard should contain NEVER"
        assert "odoo/" in content, "core-odoo-guard should reference odoo/ directory"

    def test_scss_load_order_exists(self):
        assert (RULES_DIR / "scss-load-order.md").exists()

    def test_scss_load_order_content(self):
        content = (RULES_DIR / "scss-load-order.md").read_text(encoding="utf-8")
        assert "map-merge" in content, "scss-load-order should mention map-merge"
        assert "prepend" in content, "scss-load-order should mention prepend"
        assert "H6" in content, "scss-load-order should mention H6 baseline"

    def test_skills_reference_rules(self):
        """Skills should reference rules/ instead of embedding full rule text."""
        for skill_name in ["theme-create", "theme-scss"]:
            content = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")
            assert "rules/" in content, f"{skill_name} should reference rules/ directory"


# ─── Agent Structure ─────────────────────────────────────────────


class TestAgentStructure:
    """Verify agent files have correct frontmatter."""

    def test_theme_generator_exists(self):
        assert (AGENTS_DIR / "theme-generator.md").exists()

    def test_theme_generator_has_model(self):
        content = (AGENTS_DIR / "theme-generator.md").read_text(encoding="utf-8")
        assert "model: sonnet" in content, "theme-generator should use sonnet model"

    def test_theme_generator_has_tools(self):
        content = (AGENTS_DIR / "theme-generator.md").read_text(encoding="utf-8")
        assert "tools:" in content, "theme-generator should declare tools"
        assert "Write" in content, "theme-generator needs Write tool"
        assert "Bash" in content, "theme-generator needs Bash tool"

    def test_theme_generator_references_rules(self):
        content = (AGENTS_DIR / "theme-generator.md").read_text(encoding="utf-8")
        assert "rules/" in content, "theme-generator should reference rules/"

    def test_theme_generator_has_mcp_fallback(self):
        content = (AGENTS_DIR / "theme-generator.md").read_text(encoding="utf-8")
        assert "Fallback" in content or "fallback" in content, "theme-generator should document MCP fallback"
        assert "color_palettes.json" in content, "fallback should reference preset palettes"


# ─── Progressive Disclosure ──────────────────────────────────────


class TestProgressiveDisclosure:
    """Verify large skills use REFERENCE.md for heavy content."""

    def test_theme_scss_has_reference(self):
        assert (SKILLS_DIR / "theme-scss" / "REFERENCE.md").exists()

    def test_theme_scss_skill_points_to_reference(self):
        content = (SKILLS_DIR / "theme-scss" / "SKILL.md").read_text(encoding="utf-8")
        assert "REFERENCE.md" in content, "theme-scss SKILL.md should point to REFERENCE.md"

    def test_theme_scss_skill_is_compact(self):
        content = (SKILLS_DIR / "theme-scss" / "SKILL.md").read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) < 100, f"theme-scss SKILL.md should be <100 lines (got {len(lines)})"

    def test_theme_snippets_has_reference(self):
        assert (SKILLS_DIR / "theme-snippets" / "REFERENCE.md").exists()

    def test_theme_snippets_skill_points_to_reference(self):
        content = (SKILLS_DIR / "theme-snippets" / "SKILL.md").read_text(encoding="utf-8")
        assert "REFERENCE.md" in content, "theme-snippets SKILL.md should point to REFERENCE.md"

    def test_theme_scss_reference_has_115_keys(self):
        content = (SKILLS_DIR / "theme-scss" / "REFERENCE.md").read_text(encoding="utf-8")
        assert "115+" in content, "REFERENCE.md should mention 115+ keys"

    def test_theme_snippets_reference_has_inventory(self):
        content = (SKILLS_DIR / "theme-snippets" / "REFERENCE.md").read_text(encoding="utf-8")
        assert "s_banner" in content, "REFERENCE.md should contain snippet inventory"
