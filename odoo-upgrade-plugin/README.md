# Odoo Upgrade Plugin for Claude Code

Upgrade Odoo ERP modules between versions 14-19 with automated pattern recognition, transformation scripts, and real-time compatibility hooks.

## Installation

Clone or copy this plugin into your Claude Code plugins directory:

```bash
# Option 1: Clone into plugins directory
git clone https://github.com/taqat-techno/odoo-upgrade-plugin ~/.claude/plugins/odoo-upgrade-plugin

# Option 2: Copy manually
cp -r odoo-upgrade-plugin ~/.claude/plugins/
```

## What It Does

- **3 slash commands**: `/odoo-upgrade`, `/odoo-precheck`, `/odoo-quickfix`
- **1 skill**: Comprehensive upgrade knowledge (XML, Python, JS, SCSS, migration scripts)
- **1 agent**: `upgrade-analyzer` for parallel module scanning
- **4 hooks**: Core file protection (PreToolUse), compatibility checking (PostToolUse), error detection (PostToolUseFailure), session greeting (SessionStart)

## Usage

### Scan for issues (read-only)
```
/odoo-precheck path/to/module
```

### Apply safe mechanical fixes
```
/odoo-quickfix path/to/module
```

### Full upgrade pipeline
```
/odoo-upgrade path/to/module 19
```

### Natural language
```
"Upgrade my Odoo 17 module to Odoo 19"
"Fix the tree view errors in my module"
"Generate migration scripts for my field rename"
```

## Plugin Structure

```
odoo-upgrade-plugin/
├── .claude-plugin/plugin.json     # Plugin manifest (v5.1.0)
├── odoo-upgrade.config.json       # Default configuration (user-overridable)
├── hooks/
│   ├── hooks.json                 # Hook definitions
│   ├── config_loader.py           # Shared config loader for hooks
│   ├── guard_core_odoo.py         # Blocks writes to core Odoo files
│   └── check_odoo19_compat.py     # Warns about version compat issues
├── commands/
│   ├── odoo-upgrade.md            # Full upgrade workflow
│   ├── odoo-precheck.md           # Read-only compatibility scan
│   └── odoo-quickfix.md           # Safe mechanical fixes
├── agents/
│   └── upgrade-analyzer.md        # Module scanning agent
└── odoo-upgrade/                  # Skill directory
    ├── SKILL.md                   # Upgrade knowledge base
    ├── reference/
    │   ├── odoo18_to_19.md        # Detailed 18->19 patterns
    │   └── error_catalog.md       # Error -> solution mapping
    └── scripts/                   # Python upgrade tools
        ├── cli.py                 # Unified CLI entry point
        ├── utils.py               # Shared utilities
        ├── transforms/            # Transformation modules
        │   ├── xml_transforms.py  # XML fixes (tree->list, etc.)
        │   ├── js_transforms.py   # JS fixes (RPC, OWL)
        │   ├── py_transforms.py   # Python fixes (imports, routes)
        │   └── manifest.py        # Manifest version updates
        ├── precheck.py            # Compatibility scanner
        ├── upgrade.py             # Full upgrade orchestrator
        └── validate.py            # Syntax validator
```

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `guard_core_odoo.py` | PreToolUse (Write/Edit) | **Blocks** writes to core Odoo framework files |
| `check_odoo19_compat.py` | PostToolUse (Write/Edit) | **Warns** about version compat issues in modified files |
| Compatibility error detector | PostToolUseFailure (Bash) | **Suggests** upgrade skill when errors look version-related |
| Session greeting | SessionStart | **Announces** available commands on session start |

## Configuration

The plugin ships with `odoo-upgrade.config.json` containing default settings. To customize for your workspace, copy it to your project root:

```bash
cp ~/.claude/plugins/odoo-upgrade-plugin/odoo-upgrade.config.json ./
```

### Configuration Keys

| Key | Type | Description |
|-----|------|-------------|
| `core_path_patterns` | `string[]` | Regex patterns identifying core Odoo files (never modified) |
| `target_version_path_patterns` | `object` | Maps version numbers to path patterns for version detection |
| `default_target_version` | `int\|null` | Fallback version when path detection fails. Set to `null` to skip |

### Example: Custom Workspace Layout

If your Odoo installations use `~/odoo-17.0/` instead of `odoo17/`:

```json
{
  "target_version_path_patterns": {
    "19": ["odoo-19\\.0", "my-v19-project"],
    "17": ["odoo-17\\.0", "my-v17-project"]
  }
}
```

## Scripts (Standalone Usage)

Run from the plugin's `odoo-upgrade/` directory:

```bash
cd path/to/odoo-upgrade-plugin/odoo-upgrade

# Pre-check (read-only scan)
python -m scripts.cli precheck path/to/module --target 19

# Full upgrade
python -m scripts.cli upgrade path/to/module --target 19

# Validate syntax
python -m scripts.cli validate path/to/module

# Update manifests only
python -m scripts.cli manifest path/to/module --target 19
```

## Extending

### Add patterns for a new Odoo version
1. Add a reference file: `reference/odoo19_to_20.md`
2. Add version-gated transforms to `scripts/transforms/xml_transforms.py` etc.
3. Update `SKILL.md` with the new version's breaking changes
4. Add path patterns to `odoo-upgrade.config.json`

### Add a new transform type
1. Create a new file in `scripts/transforms/`
2. Follow the pattern: class with `target_version` param, `_apply_to_*_files()` helper, and individual fix methods
3. Import it in `scripts/transforms/__init__.py`
4. Wire it into `scripts/upgrade.py`

### Customize hooks
Override `odoo-upgrade.config.json` at your project root to adjust path patterns without modifying plugin source.

## Version History

- **v5.1.0** - Configurable hooks, version-aware scripts, broader path patterns, SessionStart hook, deduplication cleanup
- **v5.0.0** - Complete rewrite: proper Claude Code hooks, slash commands, agent, script consolidation, SKILL.md trimmed from 1036 to ~220 lines
- **v4.0.0** - Added data migration scripts, OWL lifecycle, attrs-to-inline
- **v3.0.0** - Added Odoo 19 support, RPC service migration, 100+ patterns
- **v2.0.0** - Added Odoo 18 support, slug compatibility
- **v1.0.0** - Initial release with Odoo 14-17 support

## License

MIT
