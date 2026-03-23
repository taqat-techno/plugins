---
name: odoo-i18n
description: |
  Comprehensive Odoo i18n toolkit for extracting translatable strings, validating .po files, generating translation reports, managing Arabic/RTL layouts, and handling multilingual deployments across Odoo 14-19.


  <example>
  Context: User wants to extract translatable strings
  user: "Extract all translatable strings from my Odoo 17 module to a .pot file"
  assistant: "I will use the odoo-i18n skill to scan Python _() calls, XML translate attributes, and field strings, then generate a properly structured .pot template file."
  <commentary>Core trigger - translation extraction workflow.</commentary>
  </example>

  <example>
  Context: User wants Arabic translation
  user: "Generate an Arabic .po file for my Odoo module"
  assistant: "I will use the odoo-i18n skill to create an ar.po file with RTL-aware formatting and placeholder translations for all extractable strings."
  <commentary>Language-specific trigger - Arabic/RTL translation generation.</commentary>
  </example>

  <example>
  Context: User wants to validate a translation file
  user: "Validate my Arabic .po file for errors"
  assistant: "I will use the odoo-i18n skill to check syntax, encoding, empty translations, fuzzy entries, and RTL-specific issues."
  <commentary>Validate trigger - .po file validation.</commentary>
  </example>

  <example>
  Context: User wants to find missing translations
  user: "Find all strings missing Arabic translation in my module"
  assistant: "I will compare the .pot template against ar.po and report all untranslated or fuzzy entries."
  <commentary>Missing trigger - translation gap analysis.</commentary>
  </example>

  <example>
  Context: User wants RTL/SCSS help
  user: "Fix the RTL layout issues in my Odoo theme for Arabic"
  assistant: "I will use the odoo-i18n skill to apply CSS logical properties, [dir='rtl'] overrides, and Font Awesome icon swaps for Arabic support."
  <commentary>RTL trigger - Arabic layout and styling guidance.</commentary>
  </example>
license: "MIT"
metadata:
  mode: "codebase"
  supported-versions: ["14","15","16","17","18","19"]
  primary-languages: ["ar","en","tr","fr"]
  categories: [i18n, translation, rtl, arabic]
  filePattern: ["**/i18n/*.po", "**/i18n/*.pot", "**/*.po", "**/*.pot"]
  bashPattern: ["i18n_extractor", "i18n_validator", "i18n_reporter", "i18n_converter", "i18n-export", "i18n-import", "load-language"]
---

# Odoo i18n Skill

Provides deep expertise in Odoo internationalization (i18n) and localization (l10n) across Odoo 14-19.

## Critical Translation Rules

1. **NEVER** use f-strings inside `_()` — use `%` formatting: `_('Record %s') % name`
2. **NEVER** concatenate strings inside `_()` — give the translator the full sentence
3. **Use `_lt()`** for class-level strings (selection values, class attributes)
4. **NEVER wrap** `string=` field attributes in `_()` — they are auto-translated by Odoo
5. **Save `.po` files as UTF-8** without BOM
6. **Arabic** `.po` files must have `nplurals=6` in Plural-Forms header
7. **Always update the module** after editing `.po` files: `-u module --stop-after-init`

## Workflow

### 1. Extract translatable strings

```bash
python <plugin>/odoo-i18n/scripts/i18n_extractor.py --module /path/to/module --lang ar
```

Scans Python `_()` / `_lt()`, XML `string=` / text nodes, JS `_t()` / `_lt()`.
Generates `module/i18n/module.pot` (template) and `module/i18n/ar.po` (language file).

### 2. Translate the strings

Open the `.po` file and fill in `msgstr` entries.

### 3. Validate

```bash
python <plugin>/odoo-i18n/scripts/i18n_validator.py --po-file module/i18n/ar.po --lang ar
```

Checks: encoding, headers, format specifiers, Arabic-specific issues (mojibake, nplurals, BIDI).

### 4. Check coverage

```bash
python <plugin>/odoo-i18n/scripts/i18n_reporter.py --module /path/to/module --lang ar
```

Reports: total strings, translated %, missing entries grouped by file. Supports `--format json|csv` and `--min-pct` threshold.

### 5. Merge / clean .po files

```bash
python <plugin>/odoo-i18n/scripts/i18n_converter.py --action merge --base ar.po --new ar_new.po --output ar_merged.po
python <plugin>/odoo-i18n/scripts/i18n_converter.py --action clean --po ar.po
python <plugin>/odoo-i18n/scripts/i18n_converter.py --action stats --po ar.po
python <plugin>/odoo-i18n/scripts/i18n_converter.py --action convert --po ar.po --output ar_fixed.po
```

### 6. Load into Odoo

```bash
python -m odoo -c conf/project.conf -d db -u module --stop-after-init
```

Or use Odoo's built-in export/import for database-level strings:
```bash
# Export
python odoo-bin -c conf.conf -d db --i18n-export --modules=module --language=ar --output=ar.po --stop-after-init
# Import
python odoo-bin -c conf.conf -d db --i18n-import=ar.po --language=ar --modules=module --stop-after-init
```

## Commands

| Command | Description |
|---------|-------------|
| `/odoo-i18n extract --module <path> --lang <code>` | Extract strings, generate .pot/.po |
| `/odoo-i18n validate --po-file <path> [--lang <code>] [--strict]` | Validate .po file |
| `/odoo-i18n missing --module <path> --lang <code> [--format text\|json\|csv]` | Coverage report |
| `/odoo-i18n export` | Export/import via Odoo CLI reference |

## Configurable Branding

Generated .pot/.po files use configurable author/email. Set environment variables:
```bash
export ODOO_I18N_COPYRIGHT="Your Company"
export ODOO_I18N_BUGS_EMAIL="you@example.com"
```

## Detailed Reference (Memory Files)

For comprehensive patterns beyond this skill summary, the plugin includes memory files:

- **`memories/translation_patterns.md`** — Python `_()` / `_lt()` patterns, XML attribute translation, JS `_t()` patterns, .po file structure, email template translation
- **`memories/rtl_patterns.md`** — RTL activation, Bootstrap RTL, CSS logical properties, SCSS overrides, Flexbox in RTL, JS RTL detection, QWeb report RTL, common RTL fixes
- **`memories/language_codes.md`** — Language codes, date/time formats, number formats, currency display, Hijri calendar notes, timezone reference

## Odoo Version Differences

| Feature | Odoo 14-15 | Odoo 16-17 | Odoo 18-19 |
|---------|-----------|-----------|-----------|
| JS translation import | `import { _t } from "web.core"` | `import { _t } from "@web/core/l10n/translation"` | Same as 16 |
| Bootstrap version | 4.x | 5.1.3 (RTL built-in) | 5.1.3+ |
| Translation storage | `ir.translation` table | JSON terms (internal) | JSON terms |
| View type for lists | `<tree>` | `<tree>` | `<list>` (19 only) |
| Controller type | `type='json'` | `type='json'` | `type='jsonrpc'` (19 only) |
| Visibility attrs | `attrs={'invisible': ...}` | `attrs={'invisible': ...}` | Inline `invisible="expr"` (19 only) |

## Common Issues

**Translations not showing**: Update the module with `-u module --stop-after-init`, then clear browser cache.

**Arabic text garbled (mojibake)**: File saved as Latin-1. Run `i18n_converter.py --action convert` to fix encoding.

**Format specifier error**: Ensure `%s`/`%d`/`%(name)s` count matches between msgid and msgstr.

**Website shows English for Arabic users**: Check (1) Arabic language installed, (2) user language set, (3) module updated after adding translations.

**Fuzzy entries**: Open .po, verify translation, remove `#, fuzzy` flag from approved entries.
