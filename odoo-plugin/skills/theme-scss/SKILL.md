---
name: theme-scss
description: >-
  Use when configuring or debugging an Odoo theme's SCSS variables: $o-theme-font-configs
  and Google Fonts, $o-color-palettes and o-color-1 to o-color-5, $o-website-values-palettes
  keys for typography, buttons, headers and footers, SCSS load order, or an 'Undefined
  variable' error in a theme.
license: "MIT"
metadata:
  version: "8.0.0"
  author: "TaqaTechno"
  allowed-tools: "Read, Grep, Glob"
---

# Odoo Theme SCSS Variable Reference

## Scope and example requests

Complete SCSS variable reference for Odoo themes. Covers all three core variable systems:
$o-theme-font-configs (Google Fonts), $o-color-palettes (color system with 5 semantic
colors), and $o-website-values-palettes (115+ keys for typography, buttons, inputs, headers,
footers, layout). Includes SCSS load order rules and color derivation.

Example requests:

- "What SCSS variables can I configure in my Odoo theme?" (Variable reference lookup)
- "How do I set up o-color-1 through o-color-5?" (Color palette configuration)
- "I get 'Undefined variable $o-color-palettes' in my theme" (SCSS debugging - load order issue)
- "How do I add Google Fonts to my Odoo theme?" (Font configuration)

## Critical Load Order Rule

`Undefined variable $o-color-palettes` is a load-order error: your SCSS reads the variable
before core defines it. Core defines `$o-color-palettes` (html_editor/web_editor, `!default`,
then website `map-merge`s into it), `$o-website-values-palettes` and `$o-theme-font-configs`
(website, `!default`) inside the `web._assets_primary_variables` bundle.

- **Fix:** put palette and website-values variables in the theme's `primary_variables.scss`,
  **appended** to `web._assets_primary_variables` (no `('prepend', ...)`), and extend the
  palette with `$o-color-palettes: map-merge($o-color-palettes, ('my-palette': (...)));`, then
  select it with `'color-palettes-name': 'my-palette'` in `$o-website-values-palettes`. This
  is what Odoo's own `theme_*` modules do.
- **Causes:** the file is prepended (so `map-merge` runs before the definition), or it is in
  `web.assets_frontend` / an `@import` outside the primary-variables bundle.
- **Not fixes:** adding `!default`, or redefining `$o-color-palettes` standalone (that drops
  the stock `base-*` palettes that website itself reads).
- A prepended file may only set `$o-theme-font-configs` / `$o-website-values-palettes`
  standalone and must never read a core variable.

Full rule with examples and manifest syntax: `rules/scss-load-order.md`.

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

Color combinations: `o_cc1`-`o_cc5` CSS classes for section backgrounds. Add a custom palette with `map-merge` in an appended primary-variables file, and select it (or a stock one) with `'color-palettes-name'` in `$o-website-values-palettes`.

### 3. `$o-website-values-palettes` -- Master Configuration (115+ Keys)
Controls typography (13 keys), font sizes (13), line heights (11), margins (22), buttons (17), inputs (12), header (13), footer (3), links (1), layout (3), colors (5), Google Fonts (2).

### Typography Multipliers
H1=4.0, H2=3.0, H3=2.0, H4=1.5, H5=1.25, **H6=1.0 (FIXED -- 16px, never change)**.

---

For the complete 115+ key reference with all categories, examples, font aliases, color derivation rules, and the Modern Corporate Theme example, see **REFERENCE.md** in this skill directory.
