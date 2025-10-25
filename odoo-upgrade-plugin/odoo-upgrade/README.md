# Odoo Module Upgrade Skill

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Odoo](https://img.shields.io/badge/Odoo-14%20|%2015%20|%2016%20|%2017%20|%2018%20|%2019-purple.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Automatically upgrade custom Odoo modules and themes across major versions with intelligent code transformations, testing, and comprehensive reporting.

## 🚀 Features

- ✅ **Multi-Version Support**: Upgrade from Odoo 14/15/16/17/18 to 19
- ✅ **Cumulative Changes**: Handles multi-version jumps (e.g., 14→19)
- ✅ **Automatic Transformations**: Python, XML, JavaScript, SCSS
- ✅ **Safe Migration**: Creates backups before modifications
- ✅ **Testing**: Validates installation in target version
- ✅ **Detailed Reports**: Comprehensive documentation
- ✅ **Theme Support**: Bootstrap 5, SCSS, publicWidget
- ✅ **Tool Integration**: Runs `odoo-bin upgrade_code`

### 🆕 New in v2.0 (Odoo 19 Enhanced)
- **Pre-Check Tool**: Scan for issues before upgrading
- **Quick Fix Utility**: Apply targeted fixes for common problems
- **Enhanced Detection**: All Odoo 19 breaking changes covered
- **Act_window Fixes**: Automatic view_mode tree→list conversion
- **JS Class Cleanup**: Removes incompatible js_class attributes
- **Complete RPC Migration**: Full frontend RPC to fetch API conversion

## 📦 Installation

### As Part of Marketplace (Recommended)

```bash
# Clone marketplace to plugins directory
cd ~/.claude/plugins/marketplaces
git clone https://github.com/taqat-techno-eg/plugins.git taqat-techno-plugins

# All skills auto-discovered by Claude Code
```

### As Standalone Skill

```bash
# Copy just this skill
mkdir -p ~/.claude/skills
curl -o ~/.claude/skills/odoo-upgrade.md \
  https://raw.githubusercontent.com/taqat-techno-eg/plugins/main/odoo-development/odoo-upgrade/SKILL.md
```

### Windows Installation

```cmd
REM Marketplace method
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno-eg/plugins.git taqat-techno-plugins

REM Or standalone
curl -o %USERPROFILE%\.claude\skills\odoo-upgrade.md ^
  https://raw.githubusercontent.com/taqat-techno-eg/plugins/main/odoo-development/odoo-upgrade/SKILL.md
```

## 🎯 Usage

Simply ask Claude Code to upgrade your module:

```
"Upgrade custom_inventory module from odoo17 to odoo18"

"Migrate my theme_custom from version 14 to version 19"

"Upgrade the custom_pos module in TAQAT project from v16 to v19"
```

## 📋 What Gets Upgraded

### Python Code
- `name_get()` → `_compute_display_name()` (v17)
- Hook signatures: `pre_init_hook(env)` instead of `(cr)`
- Context keys: `active_id` → `id`
- Access control methods: `check_access()`, `has_access()`
- ORM changes and deprecated field removals

### XML/Views
- **Critical**: `attrs={}` → direct expressions (v17)
  ```xml
  <!-- Before -->
  <field name="color" attrs="{'invisible': [('state','=','done')]}"/>
  <!-- After -->
  <field name="color" invisible="state == 'done'"/>
  ```
- `<tree>` → `<list>` (v18)
- `states={}` → `invisible=` expressions
- Settings view restructure: `<app>`, `<block>`, `<setting>` tags

### JavaScript
- Legacy widgets → OWL v1/v2 components
- `odoo.define()` → ES6 imports
- Add `/** @odoo-module **/` annotations
- publicWidget framework for themes

### Themes
- Bootstrap 3/4 → Bootstrap 5 classes
- `.less` → `.scss` conversion
- Modern grid and utility classes

## 📚 Documentation

- [Full Skill Documentation](./SKILL.md)
- [Usage Examples](../examples/upgrade-example.md) *(coming soon)*
- [Changelog](./CHANGELOG.md) *(coming soon)*

## ⚠️ Limitations

The skill **cannot** automatically:
- Migrate database data (use OpenUpgrade separately)
- Rewrite complex custom business logic
- Fix third-party module compatibility
- Deploy to production

## 🔧 Requirements

- **Claude Code**: Latest version with skills support
- **Odoo Installations**: Multiple versions (e.g., odoo14/, odoo17/, odoo19/)
- **Directory Structure**: Custom modules in `projects/` (NOT `odoo/addons/`)
- **Python**: Version compatible with target Odoo
- **PostgreSQL**: For testing (13+)

## 📝 License

MIT License - See [LICENSE](../../../LICENSE)

---

**Part of**: [TAQAT Techno Plugins Marketplace](https://github.com/taqat-techno-eg/plugins)