#!/usr/bin/env python3
"""
Consistency Check -- Plugin structure validation for odoo-frontend-plugin.

Validates file existence, JSON syntax, hook references, version info,
and critical data rules.

Usage:
    python tests/consistency_check.py
    python tests/consistency_check.py --verbose

Exit codes:
    0 = all checks pass
    1 = one or more checks failed
"""

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv


def log_verbose(msg: str):
    if VERBOSE:
        print(f"    {msg}")


def check_file_existence() -> list:
    """Verify all expected files exist."""
    errors = []
    expected = [
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
    ]
    for path in expected:
        if (PLUGIN_ROOT / path).exists():
            log_verbose(f"{path}: exists")
        else:
            errors.append(f"Missing: {path}")
    return errors


def check_json_syntax() -> list:
    """Verify all JSON files parse correctly."""
    errors = []
    json_files = [
        "data/color_palettes.json",
        "data/theme_templates.json",
        "data/typography_defaults.json",
        "data/version_mapping.json",
        "data/figma_prompts.json",
        "hooks/hooks.json",
        ".claude-plugin/plugin.json",
    ]
    for path in json_files:
        full = PLUGIN_ROOT / path
        if not full.exists():
            continue
        try:
            with open(full) as f:
                json.load(f)
            log_verbose(f"{path}: valid JSON")
        except json.JSONDecodeError as e:
            errors.append(f"{path}: invalid JSON - {e}")
    return errors


def check_hooks_references() -> list:
    """Verify hooks.json references existing scripts."""
    errors = []
    hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"
    if not hooks_path.exists():
        return ["hooks/hooks.json not found"]

    with open(hooks_path) as f:
        config = json.load(f)

    hooks_dir = PLUGIN_ROOT / "hooks"
    for event_name, event_hooks in config.get("hooks", {}).items():
        for hook_group in event_hooks:
            for hook in hook_group.get("hooks", []):
                command = hook.get("command", "")
                for part in command.split():
                    if part.endswith('.py"') or part.endswith(".py"):
                        script_name = part.strip('"').split("/")[-1]
                        if (hooks_dir / script_name).exists():
                            log_verbose(f"Hook '{event_name}' -> {script_name}: exists")
                        else:
                            errors.append(f"Hook '{event_name}' references missing: {script_name}")
    return errors


def check_plugin_version() -> list:
    """Verify plugin.json version is 8.x."""
    errors = []
    pj = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        return ["plugin.json not found"]
    with open(pj) as f:
        config = json.load(f)
    version = config.get("version", "")
    if version.startswith("8."):
        log_verbose(f"Plugin version: {version}")
    else:
        errors.append(f"Plugin version should be 8.x, got: {version}")
    return errors


def check_critical_data() -> list:
    """Verify critical data rules."""
    errors = []

    # H6 multiplier must be 1.0
    typo_path = PLUGIN_ROOT / "data" / "typography_defaults.json"
    if typo_path.exists():
        with open(typo_path) as f:
            typo = json.load(f)
        h6 = typo.get("heading_hierarchy", {}).get("h6", {})
        if h6.get("multiplier") == 1.0:
            log_verbose("H6 multiplier: 1.0 (correct)")
        else:
            errors.append(f"H6 multiplier should be 1.0, got: {h6.get('multiplier')}")

    # Version mapping covers Odoo 14-19
    vm_path = PLUGIN_ROOT / "data" / "version_mapping.json"
    if vm_path.exists():
        with open(vm_path) as f:
            vm = json.load(f)
        versions = vm.get("odoo_versions", {})
        for ver in ["14", "15", "16", "17", "18", "19"]:
            if ver in versions:
                log_verbose(f"Odoo {ver}: present")
            else:
                errors.append(f"Missing Odoo version {ver} in version_mapping.json")

    return errors


def check_deleted_files() -> list:
    """Verify obsolete files are deleted."""
    errors = []
    deleted = [
        "scripts/create_theme.py",
        "scripts/devtools_extractor.py",
        "scripts/pwa_generator.py",
        "scripts/figma_converter.py",
        "scripts/theme_mirror_generator.py",
        "templates/theme_module/__manifest__.py.template",
    ]
    for path in deleted:
        if (PLUGIN_ROOT / path).exists():
            errors.append(f"Obsolete file should be deleted: {path}")
        else:
            log_verbose(f"{path}: deleted (correct)")
    return errors


def main():
    print("Odoo Frontend Plugin Consistency Check")
    print("=" * 50)

    all_errors = []
    checks = [
        ("File Existence", check_file_existence),
        ("JSON Syntax", check_json_syntax),
        ("Hook References", check_hooks_references),
        ("Plugin Version", check_plugin_version),
        ("Critical Data Rules", check_critical_data),
        ("Deleted Files", check_deleted_files),
    ]

    for check_name, check_fn in checks:
        print(f"\n[CHECK] {check_name}")
        errors = check_fn()
        if errors:
            for err in errors:
                print(f"  FAIL: {err}")
            all_errors.extend(errors)
        else:
            print("  PASS")

    print("\n" + "=" * 50)
    if all_errors:
        print(f"RESULT: {len(all_errors)} error(s) found")
        return 1
    else:
        print("RESULT: All checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
