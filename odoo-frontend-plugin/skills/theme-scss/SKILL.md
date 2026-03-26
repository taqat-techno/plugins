---
name: theme-scss
description: |
  Complete SCSS variable reference for Odoo themes. Covers all three core variable systems: $o-theme-font-configs (Google Fonts), $o-color-palettes (color system with 5 semantic colors), and $o-website-values-palettes (115+ keys for typography, buttons, inputs, headers, footers, layout). Includes SCSS load order rules and color derivation.

  <example>
  Context: User asks about SCSS variables
  user: "What SCSS variables can I configure in my Odoo theme?"
  assistant: "I will use the theme-scss skill to show the complete variable reference."
  <commentary>Variable reference lookup.</commentary>
  </example>

  <example>
  Context: User wants to configure colors
  user: "How do I set up o-color-1 through o-color-5?"
  assistant: "I will explain the semantic color system and palette configuration."
  <commentary>Color palette configuration.</commentary>
  </example>

  <example>
  Context: User gets undefined variable error
  user: "I get 'Undefined variable $o-color-palettes' in my theme"
  assistant: "This is a SCSS load order issue. Theme files load BEFORE core variables."
  <commentary>SCSS debugging - load order issue.</commentary>
  </example>

  <example>
  Context: User wants to configure fonts
  user: "How do I add Google Fonts to my Odoo theme?"
  assistant: "Use $o-theme-font-configs with the font query parameter, not the full URL."
  <commentary>Font configuration.</commentary>
  </example>
license: "MIT"
metadata:
  version: "8.0.0"
  author: "TaqaTechno"
  allowed-tools: "Read, Grep, Glob"
---

# Odoo Theme SCSS Variable Reference

## Critical Load Order Rule

See `rules/scss-load-order.md` for the complete load order explanation, map-merge prohibition, and prepend requirement.

## Version Scope

The SCSS variable systems are **version-independent** -- they work identically across Odoo 14-19. Variable names, structure, and keys do not change between versions. What DOES change: Bootstrap utility classes (4.x vs 5.x) and asset bundle syntax. See `data/version_mapping.json`.

---

## Three Variable Systems

### 1. `$o-theme-font-configs` -- Google Fonts
Configures Google Fonts with family, URL query parameter (NOT full URL), and optional per-context properties. Font aliases: `'base'`, `'headings'`, `'navbar'`, `'buttons'`. Multi-word fonts use `+` separator.

### 2. `$o-color-palettes` -- 5 Semantic Colors
- `o-color-1`: Primary/Accent (brand color, buttons, links)
- `o-color-2`: Secondary
- `o-color-3`: Light background
- `o-color-4`: White (#FFFFFF)
- `o-color-5`: Dark/Text

Color combinations: `o_cc1`-`o_cc5` CSS classes for section backgrounds. In themes, use `$o-website-values-palettes` with `'color-palettes-name'` (NOT `map-merge`).

### 3. `$o-website-values-palettes` -- Master Configuration (115+ Keys)
Controls typography (13 keys), font sizes (13), line heights (11), margins (22), buttons (17), inputs (12), header (13), footer (3), links (1), layout (3), colors (5), Google Fonts (2).

### Typography Multipliers
H1=4.0, H2=3.0, H3=2.0, H4=1.5, H5=1.25, **H6=1.0 (FIXED -- 16px, never change)**.

---

For the complete 115+ key reference with all categories, examples, font aliases, color derivation rules, and the Modern Corporate Theme example, see **REFERENCE.md** in this skill directory.
