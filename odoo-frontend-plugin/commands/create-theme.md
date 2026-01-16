---
title: 'Create Theme'
read_only: false
type: 'command'
description: 'Create a complete Odoo website theme by extracting design system variables from Figma via Chrome browser automation'
---

# /create-theme - Figma-to-Odoo Theme Generator

Generate a professional, production-ready Odoo website theme by **extracting design system variables directly from Figma** via Chrome browser automation, then creating all theme files, testing installation, and auto-fixing any issues.

## Overview

This command provides an end-to-end workflow:

1. **Open Figma Design** in Chrome browser
2. **Extract Design Variables**:
   - Primary and secondary colors from the design
   - Font family (body and headings)
   - Font sizes for H1-H6 hierarchy
   - Additional display sizes if design has more than 6 levels
3. **Generate Theme Files** following Odoo best practices
4. **Test Installation** in Odoo
5. **Auto-Fix Issues** if installation fails

## Usage

### Interactive Mode with Figma URL (Recommended)
```
/create-theme --figma <figma_url>
```
Opens Figma, extracts design variables, and guides through theme creation.

### Full Arguments
```
/create-theme <theme_name> <project_path> --figma <figma_url> --version=17
```

### Manual Mode (No Figma)
```
/create-theme <theme_name> <project_path> --colors="#207AB7,#FB9F54,#F6F4F0,#FFFFFF,#191A19"
```

## Complete Workflow

### Phase 1: Figma Design Extraction via Chrome

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: FIGMA DESIGN EXTRACTION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  STEP 1: Open Figma in Chrome                                                │
│  ─────────────────────────────                                               │
│  Using Claude-in-Chrome MCP tools:                                           │
│  1. Get browser tab context                                                  │
│  2. Create new tab if needed                                                 │
│  3. Navigate to Figma URL                                                    │
│  4. Wait for design to load                                                  │
│                                                                               │
│  STEP 2: Extract Colors                                                      │
│  ─────────────────────────                                                   │
│  Look for:                                                                   │
│  • Primary color: Usually the dominant brand color                           │
│  • Secondary color: Accent/CTA color                                         │
│  • Background colors: Light backgrounds (o-color-3)                          │
│  • White/base color (o-color-4)                                              │
│  • Dark/text color (o-color-5)                                               │
│                                                                               │
│  STEP 3: Extract Typography                                                  │
│  ──────────────────────────                                                  │
│  Extract from text styles:                                                   │
│  • Font family (body text)                                                   │
│  • Font family (headings if different)                                       │
│  • H1 size (largest heading)                                                 │
│  • H2 size                                                                   │
│  • H3 size                                                                   │
│  • H4 size                                                                   │
│  • H5 size                                                                   │
│  • H6 size (defaults to 16px if not found)                                   │
│  • Display sizes (if > 6 heading levels exist)                               │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Chrome Browser Automation Steps

```javascript
// Step 1: Get tab context
mcp__claude-in-chrome__tabs_context_mcp({ createIfEmpty: true })

// Step 2: Create new tab
mcp__claude-in-chrome__tabs_create_mcp()

// Step 3: Navigate to Figma
mcp__claude-in-chrome__navigate({ url: figmaUrl, tabId: tabId })

// Step 4: Wait for design to load
mcp__claude-in-chrome__computer({ action: "wait", duration: 5, tabId: tabId })

// Step 5: Take screenshot to analyze design
mcp__claude-in-chrome__computer({ action: "screenshot", tabId: tabId })

// Step 6: Read page to find color/font information
mcp__claude-in-chrome__read_page({ tabId: tabId, filter: "all" })

// Step 7: Look for specific design elements
mcp__claude-in-chrome__find({ query: "color palette", tabId: tabId })
mcp__claude-in-chrome__find({ query: "typography", tabId: tabId })
```

#### Figma Design Panel Navigation

To extract design variables, Claude will:

1. **Navigate to Design Panel**:
   - Look for the right sidebar (Design tab)
   - Click on text elements to see typography styles
   - Click on colored elements to see fill colors

2. **Extract Color Values**:
   - Primary: Most prominent brand color (buttons, headers)
   - Secondary: Accent color (CTAs, highlights)
   - Look for color style definitions in the Styles panel

3. **Extract Typography Values**:
   - Click on heading text to inspect font properties
   - Record font-family, font-size, font-weight, line-height
   - Map sizes to H1-H6 hierarchy

### Phase 2: Typography Hierarchy Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TYPOGRAPHY HIERARCHY MAPPING                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  STANDARD HIERARCHY (H1-H6):                                                 │
│  ───────────────────────────                                                 │
│  From design, extract font sizes and convert to multipliers (base = 16px):  │
│                                                                               │
│  H1: 64px  → (64 / 16) = 4.0    (Hero/Page titles)                          │
│  H2: 48px  → (48 / 16) = 3.0    (Section headers)                           │
│  H3: 32px  → (32 / 16) = 2.0    (Sub-section headers)                       │
│  H4: 24px  → (24 / 16) = 1.5    (Card headers)                              │
│  H5: 20px  → (20 / 16) = 1.25   (Small headers)                             │
│  H6: 16px  → (16 / 16) = 1.0    (Captions) **DEFAULT**                      │
│                                                                               │
│  EXTENDED HIERARCHY (Display Classes):                                       │
│  ─────────────────────────────────────                                       │
│  If design has > 6 heading levels, add Bootstrap display classes:           │
│                                                                               │
│  display-1: 96px → 6.0    (Extra large hero)                                │
│  display-2: 88px → 5.5    (Large hero)                                      │
│  display-3: 80px → 5.0    (Hero)                                            │
│  display-4: 72px → 4.5    (Sub-hero)                                        │
│  display-5: 64px → 4.0    (Same as H1)                                      │
│  display-6: 56px → 3.5    (Between H1 and H2)                               │
│                                                                               │
│  MAPPING RULES:                                                              │
│  ─────────────                                                               │
│  • H6 MUST be 16px (1rem) - This is the base font size                      │
│  • Sizes larger than H1 become display-* classes                            │
│  • Maintain visual hierarchy with consistent ratios                          │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### SCSS Variable Generation

```scss
// === Typography Hierarchy from Figma ===
// Font Family
$o-theme-font-family: '{{FONT_FAMILY}}', sans-serif;
$o-theme-headings-font-family: '{{HEADINGS_FONT}}', sans-serif;

// Heading Size Multipliers (relative to 16px base)
$o-theme-h1-font-size-multiplier: ({{H1_SIZE}} / 16); // {{H1_SIZE}}px
$o-theme-h2-font-size-multiplier: ({{H2_SIZE}} / 16); // {{H2_SIZE}}px
$o-theme-h3-font-size-multiplier: ({{H3_SIZE}} / 16); // {{H3_SIZE}}px
$o-theme-h4-font-size-multiplier: ({{H4_SIZE}} / 16); // {{H4_SIZE}}px
$o-theme-h5-font-size-multiplier: ({{H5_SIZE}} / 16); // {{H5_SIZE}}px
$o-theme-h6-font-size-multiplier: (16 / 16);          // 16px (FIXED)

// Display Sizes (for extended hierarchy)
{{#if HAS_DISPLAY_SIZES}}
$display-font-sizes: (
  1: {{DISPLAY_1_SIZE}}px,
  2: {{DISPLAY_2_SIZE}}px,
  3: {{DISPLAY_3_SIZE}}px,
  4: {{DISPLAY_4_SIZE}}px,
  5: {{DISPLAY_5_SIZE}}px,
  6: {{DISPLAY_6_SIZE}}px,
);
{{/if}}

// Font Weights
$o-theme-headings-font-weight: {{HEADINGS_WEIGHT}};
$o-theme-font-weight-normal: 400;
$o-theme-font-weight-medium: 500;
$o-theme-font-weight-semibold: 600;
$o-theme-font-weight-bold: 700;

// Line Heights
$o-theme-headings-line-height: {{HEADINGS_LINE_HEIGHT}};
$o-theme-line-height-base: {{BODY_LINE_HEIGHT}};
```

### Phase 3: Color Palette Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COLOR PALETTE MAPPING (Odoo Semantic)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ODOO COLOR SYSTEM:                                                          │
│  ──────────────────                                                          │
│  o-color-1: Primary brand color (buttons, links, headers)                   │
│  o-color-2: Secondary/accent color (CTAs, highlights)                       │
│  o-color-3: Light background (sections, cards)                              │
│  o-color-4: White/base (body background)                                    │
│  o-color-5: Dark text (headings, body text)                                 │
│                                                                               │
│  FROM FIGMA EXTRACTION:                                                      │
│  ──────────────────────                                                      │
│  Primary Color    → o-color-1                                               │
│  Secondary Color  → o-color-2                                               │
│  Light BG         → o-color-3 (or derive from primary at 10% opacity)       │
│  White            → o-color-4 (#FFFFFF)                                     │
│  Dark Text        → o-color-5 (or #191A19 default)                          │
│                                                                               │
│  AUTO-DERIVATION:                                                            │
│  ────────────────                                                            │
│  If only 2 colors found:                                                    │
│  • o-color-3 = lighten(primary, 45%)                                        │
│  • o-color-4 = #FFFFFF                                                      │
│  • o-color-5 = darken(primary, 40%) or #191A19                              │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 4: Theme Generation

After extracting all variables, generate the complete theme structure:

```
theme_{{name}}/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── data/
│   ├── assets.xml
│   ├── menu.xml
│   └── pages/
│       ├── home_page.xml
│       ├── aboutus_page.xml
│       ├── contactus_page.xml
│       └── services_page.xml
├── views/
│   ├── layout/
│   │   ├── header.xml
│   │   ├── footer.xml
│   │   └── templates.xml
│   └── snippets/
│       └── custom_snippets.xml
└── static/
    ├── description/
    │   ├── cover.png
    │   └── screenshot.png
    └── src/
        ├── scss/
        │   ├── primary_variables.scss    # From Figma extraction
        │   ├── bootstrap_overridden.scss
        │   └── theme.scss
        ├── js/
        │   ├── theme.js
        │   └── snippets_options.js
        └── img/
            └── .gitkeep
```

### Phase 5: Installation & Testing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 5: INSTALLATION & TESTING                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  STEP 1: Update Module List                                                  │
│  ─────────────────────────────                                               │
│  python -m odoo -c conf/{{PROJECT}}.conf -d {{DATABASE}} --update-list       │
│                                                                               │
│  STEP 2: Install Theme                                                       │
│  ────────────────────────                                                    │
│  python -m odoo -c conf/{{PROJECT}}.conf -d {{DATABASE}} \                   │
│      -i theme_{{NAME}} --stop-after-init                                     │
│                                                                               │
│  STEP 3: Check for Errors                                                    │
│  ─────────────────────────                                                   │
│  If installation fails, analyze error and auto-fix:                          │
│                                                                               │
│  Common Issues:                                                              │
│  • Missing dependencies → Add to __manifest__.py                             │
│  • Invalid XML syntax → Fix and retry                                        │
│  • Asset bundle errors → Fix asset paths                                     │
│  • SCSS syntax errors → Fix SCSS and retry                                   │
│                                                                               │
│  STEP 4: Verify Theme                                                        │
│  ────────────────────                                                        │
│  If installation succeeds:                                                   │
│  1. Navigate to Website → Configuration → Settings → Theme                   │
│  2. Activate the new theme                                                   │
│  3. Preview website                                                          │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Auto-Fix Patterns

| Error Pattern | Auto-Fix Action |
|---------------|-----------------|
| `SyntaxError in SCSS` | Parse error location, fix syntax |
| `Module not found` | Add dependency to manifest |
| `Invalid XML` | Fix XML structure |
| `Asset not found` | Fix asset path in manifest |
| `Template inheritance error` | Fix inherit_id reference |

## Implementation Details

### Chrome MCP Integration

The command uses Claude-in-Chrome MCP tools for browser automation:

```python
# Required MCP tools
mcp__claude-in-chrome__tabs_context_mcp
mcp__claude-in-chrome__tabs_create_mcp
mcp__claude-in-chrome__navigate
mcp__claude-in-chrome__computer
mcp__claude-in-chrome__read_page
mcp__claude-in-chrome__find
mcp__claude-in-chrome__javascript_tool
```

### Figma URL Patterns

Supported Figma URL formats:
```
https://www.figma.com/file/XXXX/Design-Name
https://www.figma.com/design/XXXX/Design-Name
https://www.figma.com/proto/XXXX/Design-Name
```

### Design Variable Extraction

Claude will visually analyze the Figma design to extract:

1. **Colors**: By taking screenshots and identifying prominent colors
2. **Typography**: By clicking on text elements and reading properties
3. **Spacing**: By analyzing component layouts

## ⚠️ CRITICAL: SCSS Load Order in Odoo

**IMPORTANT**: Theme SCSS files with `prepend` directive load **BEFORE** Odoo core variables are defined!

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCSS LOAD ORDER (CRITICAL!)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  1. Theme's primary_variables.scss (via prepend)                             │
│     ↓                                                                         │
│  2. Odoo core primary_variables.scss                                         │
│     (where $o-color-palettes, $o-theme-font-configs are FIRST defined)      │
│     ↓                                                                         │
│  3. Other SCSS files                                                         │
│                                                                               │
│  ⚠️ CONSEQUENCE:                                                             │
│  ──────────────                                                              │
│  • CANNOT use map-merge() with core variables (they don't exist yet!)       │
│  • MUST define standalone variables                                          │
│  • Use 'color-palettes-name': 'default-1' to reference existing palettes    │
│                                                                               │
│  ❌ WRONG (will cause "Undefined variable" error):                           │
│     $o-color-palettes: map-merge($o-color-palettes, (...));                 │
│     $o-theme-font-configs: map-merge($o-theme-font-configs, (...));         │
│                                                                               │
│  ✅ CORRECT (standalone definitions):                                        │
│     $o-theme-font-configs: ( 'FontName': (...) );                           │
│     $o-website-values-palettes: ( ( 'color-palettes-name': 'default-1' ) ); │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Complete primary_variables.scss Template (CORRECTED)

```scss
// ===================================================================
// Theme: {{THEME_DISPLAY_NAME}}
// Generated from Figma: {{FIGMA_URL}}
// Generated by TAQAT Techno /create-theme command v4.1
// ===================================================================
//
// ⚠️ IMPORTANT: This file is PREPENDED before Odoo core variables!
// DO NOT use map-merge() with core variables - they don't exist yet!
// ===================================================================

// === Typography from Figma ===
// Base font size: 16px (1rem)

// Heading Size Multipliers
$o-theme-h1-font-size-multiplier: ({{H1_SIZE}} / 16); // {{H1_SIZE}}px - Hero/Page titles
$o-theme-h2-font-size-multiplier: ({{H2_SIZE}} / 16); // {{H2_SIZE}}px - Section headers
$o-theme-h3-font-size-multiplier: ({{H3_SIZE}} / 16); // {{H3_SIZE}}px - Sub-sections
$o-theme-h4-font-size-multiplier: ({{H4_SIZE}} / 16); // {{H4_SIZE}}px - Card headers
$o-theme-h5-font-size-multiplier: ({{H5_SIZE}} / 16); // {{H5_SIZE}}px - Small headers
$o-theme-h6-font-size-multiplier: (16 / 16);          // 16px - Captions (FIXED)

// Font Weights
$o-theme-headings-font-weight: {{HEADINGS_WEIGHT}};
$o-theme-font-weight-normal: 400;
$o-theme-font-weight-medium: 500;
$o-theme-font-weight-semibold: 600;
$o-theme-font-weight-bold: 700;

// Line Heights
$o-theme-headings-line-height: {{HEADINGS_LINE_HEIGHT}};
$o-theme-line-height-base: {{BODY_LINE_HEIGHT}};

{{#if HAS_DISPLAY_SIZES}}
// === Extended Typography (Display Sizes) ===
// For designs with > 6 heading levels
$display-font-sizes: (
  1: {{DISPLAY_1}}rem,  // Extra large hero
  2: {{DISPLAY_2}}rem,  // Large hero
  3: {{DISPLAY_3}}rem,  // Hero
  4: {{DISPLAY_4}}rem,  // Sub-hero
  5: {{DISPLAY_5}}rem,  // Large heading
  6: {{DISPLAY_6}}rem,  // Medium heading
) !default;
{{/if}}

// === Font Configuration (STANDALONE - no map-merge!) ===
// Odoo's built-in font loading handles Google Fonts automatically
$o-theme-font-configs: (
    '{{BODY_FONT}}': (
        'family': ('{{BODY_FONT}}', sans-serif),
        'url': '{{BODY_FONT}}:300,300i,400,400i,500,500i,600,600i,700,700i',
    ),
{{#if HEADINGS_FONT_DIFFERENT}}
    '{{HEADINGS_FONT}}': (
        'family': ('{{HEADINGS_FONT}}', sans-serif),
        'url': '{{HEADINGS_FONT}}:300,300i,400,400i,500,500i,600,600i,700,700i',
    ),
{{/if}}
);

// === Website Values Palette ===
// Uses 'color-palettes-name': 'default-1' to reference existing Odoo palette
// This avoids the map-merge issue with $o-color-palettes
$o-website-values-palettes: (
    (
        // Reference existing palette (Odoo provides default-1 through default-20)
        'color-palettes-name': 'default-1',

        // Typography
        'font': '{{BODY_FONT}}',
        'headings-font': '{{HEADINGS_FONT}}',
        'navbar-font': '{{BODY_FONT}}',
        'buttons-font': '{{BODY_FONT}}',
        'headings-line-height': {{HEADINGS_LINE_HEIGHT}},

        // Header
        'header-template': 'default',
        'header-links-style': 'default',
        'hamburger-position': 'right',
        'logo-height': 3rem,
        'fixed-logo-height': 2rem,

        // Buttons
        'btn-padding-y': 0.75rem,
        'btn-padding-x': 2rem,
        'btn-padding-y-sm': 0.5rem,
        'btn-padding-x-sm': 1.5rem,
        'btn-padding-y-lg': 1rem,
        'btn-padding-x-lg': 3rem,
        'btn-border-radius': 0.5rem,
        'btn-border-radius-sm': 0.25rem,
        'btn-border-radius-lg': 0.75rem,
        'btn-font-weight': 500,

        // Inputs
        'input-padding-y': 0.75rem,
        'input-padding-x': 1rem,
        'input-border-radius': 0.5rem,

        // Footer
        'footer-template': 'default',
        'footer-scrolltop': true,

        // Links
        'link-underline': 'never',
    ),
);

// === Theme Colors (Custom Properties) ===
// Define as CSS custom properties for use in theme.scss
// These will be available AFTER Odoo core loads
:root {
    --theme-primary: {{COLOR_1}};
    --theme-secondary: {{COLOR_2}};
    --theme-light-bg: {{COLOR_3}};
    --theme-white: {{COLOR_4}};
    --theme-dark: {{COLOR_5}};
}
```

## assets.xml Template (CORRECTED)

**⚠️ IMPORTANT**: Do NOT use `ir.asset` records for Google Fonts! Use `$o-theme-font-configs` instead.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!--
    ⚠️ IMPORTANT: Google Fonts are loaded via $o-theme-font-configs in SCSS
    DO NOT create ir.asset records for external font URLs - this causes malformed URLs!

    ❌ WRONG (causes malformed @import URLs):
    <record id="google_fonts" model="ir.asset">
        <field name="path">https://fonts.googleapis.com/css2?family=...</field>
    </record>

    ✅ CORRECT: Fonts configured in primary_variables.scss via $o-theme-font-configs
    -->
</odoo>
```

## header.xml Template (CORRECTED XPath)

**⚠️ IMPORTANT**: Use simple XPath expressions that target high-level elements.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!--
    ⚠️ XPath Best Practices:
    - Keep expressions SIMPLE - target high-level elements
    - Avoid complex nested paths like //header//nav//ul
    - Odoo 17+ may have different HTML structures than expected

    ❌ WRONG (too specific, may not match):
    <xpath expr="//header//nav" position="attributes">

    ✅ CORRECT (simple, reliable):
    <xpath expr="//header" position="attributes">
    -->

    <!-- Add theme class to header -->
    <template id="header_style" inherit_id="website.layout" name="{{THEME_NAME}} Header">
        <xpath expr="//header" position="attributes">
            <attribute name="t-attf-class">o_{{THEME_SLUG}}_header #{header_class or ''}</attribute>
        </xpath>
    </template>
</odoo>
```

## footer.xml Template (CORRECTED XPath)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Add theme class to footer -->
    <template id="footer_style" inherit_id="website.layout" name="{{THEME_NAME}} Footer">
        <xpath expr="//footer" position="attributes">
            <attribute name="t-attf-class">o_{{THEME_SLUG}}_footer #{footer_class or ''}</attribute>
        </xpath>
    </template>
</odoo>
```

## Example Session

### User Request
```
/create-theme --figma https://www.figma.com/file/abc123/MyDesign
```

### Claude Response

```
╔══════════════════════════════════════════════════════════════╗
║           FIGMA DESIGN EXTRACTION                            ║
╠══════════════════════════════════════════════════════════════╣
║ Opening Figma in Chrome...                                   ║
║ URL: https://www.figma.com/file/abc123/MyDesign              ║
╚══════════════════════════════════════════════════════════════╝

Analyzing design...

╔══════════════════════════════════════════════════════════════╗
║           EXTRACTED DESIGN VARIABLES                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║ COLORS:                                                      ║
║ ├── Primary:   #2C5282 (Deep Blue)                          ║
║ ├── Secondary: #ED8936 (Orange)                             ║
║ ├── Light BG:  #F7FAFC                                      ║
║ ├── White:     #FFFFFF                                      ║
║ └── Dark Text: #1A202C                                      ║
║                                                              ║
║ TYPOGRAPHY:                                                  ║
║ ├── Font Family: Inter                                       ║
║ ├── Headings Font: Poppins                                   ║
║ ├── H1: 64px (4rem)                                          ║
║ ├── H2: 48px (3rem)                                          ║
║ ├── H3: 36px (2.25rem)                                       ║
║ ├── H4: 28px (1.75rem)                                       ║
║ ├── H5: 24px (1.5rem)                                        ║
║ ├── H6: 16px (1rem) [DEFAULT]                                ║
║ └── Headings Weight: 700                                     ║
║                                                              ║
║ DISPLAY SIZES (Extended):                                    ║
║ ├── Display 1: 96px (6rem) - Found in hero section          ║
║ └── Display 2: 80px (5rem) - Found in banner                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Enter theme name (snake_case): my_awesome_theme
Enter project path: projects/my_project
Target Odoo version [17]: 17

╔══════════════════════════════════════════════════════════════╗
║           GENERATING THEME FILES                             ║
╠══════════════════════════════════════════════════════════════╣
║ ✓ __manifest__.py                                            ║
║ ✓ __init__.py                                                ║
║ ✓ security/ir.model.access.csv                               ║
║ ✓ static/src/scss/primary_variables.scss                     ║
║ ✓ static/src/scss/bootstrap_overridden.scss                  ║
║ ✓ static/src/scss/theme.scss                                 ║
║ ✓ static/src/js/theme.js                                     ║
║ ✓ static/src/js/snippets_options.js                          ║
║ ✓ views/layout/header.xml                                    ║
║ ✓ views/layout/footer.xml                                    ║
║ ✓ views/layout/templates.xml                                 ║
║ ✓ views/snippets/custom_snippets.xml                         ║
║ ✓ data/assets.xml                                            ║
║ ✓ data/menu.xml                                              ║
║ ✓ data/pages/home_page.xml                                   ║
║ ✓ data/pages/aboutus_page.xml                                ║
║ ✓ data/pages/contactus_page.xml                              ║
║ ✓ data/pages/services_page.xml                               ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║           TESTING INSTALLATION                               ║
╠══════════════════════════════════════════════════════════════╣
║ Running: python -m odoo -c conf/my_project17.conf \          ║
║          -d my_project17 -i theme_my_awesome_theme \         ║
║          --stop-after-init                                   ║
╚══════════════════════════════════════════════════════════════╝

Installation successful!

╔══════════════════════════════════════════════════════════════╗
║           THEME CREATED SUCCESSFULLY!                        ║
╠══════════════════════════════════════════════════════════════╣
║ Theme Name:    theme_my_awesome_theme                        ║
║ Odoo Version:  17.0                                          ║
║ Bootstrap:     5.1.3                                         ║
║ Location:      projects/my_project/theme_my_awesome_theme/   ║
║ Source:        Figma Design (abc123)                         ║
╠══════════════════════════════════════════════════════════════╣
║ NEXT STEPS:                                                  ║
║ 1. Go to Website → Configuration → Settings → Theme          ║
║ 2. Select 'Theme My Awesome Theme'                           ║
║ 3. Preview and customize                                     ║
╚══════════════════════════════════════════════════════════════╝
```

## Version-Specific Adjustments

### Odoo 14-15 (Bootstrap 4)
- Use `ml-*`, `mr-*` classes (not `ms-*`, `me-*`)
- Different asset bundle syntax
- No snippet groups

### Odoo 16-17 (Bootstrap 5.1.3)
- Use `ms-*`, `me-*` classes
- Modern asset bundle syntax
- Simple snippet registration

### Odoo 18-19 (Bootstrap 5.1.3 + Snippet Groups)
- Use snippet groups in registration
- Owl v2 patterns available
- Enhanced website builder integration

## Troubleshooting Guide

### Common Issues and Solutions

Based on extensive production theme development, here are the most common issues and their solutions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TROUBLESHOOTING GUIDE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ISSUE #1: Undefined variable "$o-color-palettes"                            │
│  ───────────────────────────────────────────────────                        │
│  CAUSE: Using map-merge() with core variable in prepended SCSS              │
│  FIX: Remove map-merge(), use $o-website-values-palettes with               │
│       'color-palettes-name': 'default-1' instead                            │
│                                                                               │
│  ISSUE #2: Undefined variable "$o-theme-font-configs"                        │
│  ─────────────────────────────────────────────────────                      │
│  CAUSE: Same as above - core variable not defined yet                       │
│  FIX: Define $o-theme-font-configs as STANDALONE (no map-merge)             │
│                                                                               │
│  ISSUE #3: Malformed Google Fonts @import URL                                │
│  ──────────────────────────────────────────────                              │
│  CAUSE: Using ir.asset record for external font URL                         │
│  SYMPTOM: @import url("https://...https://...")                              │
│  FIX: Remove ir.asset, use $o-theme-font-configs in SCSS                    │
│                                                                               │
│  ISSUE #4: XPath error "Element cannot be located"                           │
│  ─────────────────────────────────────────────────                          │
│  CAUSE: Complex XPath like //header//nav doesn't match HTML structure       │
│  FIX: Use simple XPath: //header, //footer, //main                          │
│                                                                               │
│  ISSUE #5: CSS showing 0 rules (empty stylesheet)                            │
│  ──────────────────────────────────────────────                              │
│  CAUSE: SCSS compilation failed silently                                     │
│  DIAGNOSIS: Check browser console for "Style compilation failed"            │
│  FIX: Fix SCSS errors, clear asset cache                                    │
│                                                                               │
│  ISSUE #6: Asset cache not clearing                                          │
│  ────────────────────────────────                                            │
│  FIX: Clear via Odoo shell:                                                 │
│       >>> self.env['ir.attachment'].search([                                │
│       ...     ('url', 'like', '/web/assets/')                               │
│       ... ]).unlink()                                                        │
│       >>> self.env.cr.commit()                                              │
│                                                                               │
│  ISSUE #7: KeyError 'website.theme.asset'                                   │
│  ──────────────────────────────────────                                      │
│  CAUSE: Incorrect model name for assets                                     │
│  FIX: Use __manifest__.py assets dict, not ir.asset XML records             │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Debugging SCSS Issues

```bash
# Step 1: Check browser console for compilation errors
# Look for: "Style compilation failed" or SCSS error messages

# Step 2: Verify stylesheets loaded
# In browser console:
document.styleSheets[0].cssRules.length  # Should be > 0

# Step 3: If 0 rules, SCSS compilation failed - check for:
# - Undefined variable errors
# - Syntax errors
# - Invalid map-merge() calls

# Step 4: Clear asset cache after fixing
python odoo-bin shell -d {{DATABASE}}
>>> self.env['ir.attachment'].search([('url', 'like', '/web/assets/')]).unlink()
>>> self.env.cr.commit()

# Step 5: Restart server and hard refresh browser (Ctrl+Shift+R)
```

### Correct Asset Bundle Configuration

```python
# __manifest__.py - CORRECT asset bundle configuration
'assets': {
    # Primary variables - PREPENDED (loads before Odoo core)
    'web._assets_primary_variables': [
        ('prepend', 'theme_name/static/src/scss/primary_variables.scss'),
    ],
    # Bootstrap overrides - loads after helpers
    'web._assets_frontend_helpers': [
        'theme_name/static/src/scss/bootstrap_overridden.scss',
    ],
    # Main frontend assets
    'web.assets_frontend': [
        'theme_name/static/src/scss/theme.scss',
        'theme_name/static/src/js/theme.js',
    ],
    # Website editor assets (snippet options)
    'website.assets_wysiwyg': [
        'theme_name/static/src/js/snippets_options.js',
    ],
},
```

### Testing Checklist

Before considering a theme complete, verify:

- [ ] Fresh database creation works
- [ ] `base` + `website` module installation succeeds
- [ ] Theme module installs without errors
- [ ] Theme activation via website configurator works
- [ ] CSS compilation succeeds (check `document.styleSheets[n].cssRules.length > 0`)
- [ ] No SCSS compilation errors in browser console
- [ ] No JavaScript errors in browser console
- [ ] Header styling applies correctly
- [ ] Footer styling applies correctly
- [ ] Responsive layout works on mobile/tablet/desktop
- [ ] Website builder (edit mode) functions without errors

## Notes

- Figma account access required (logged in via Chrome)
- H6 is always fixed at 16px (1rem) as the base reference
- Display classes extend the hierarchy for designs with large hero text
- Auto-fix attempts 3 times before reporting failure
- All generated code follows TaqaTechno standards
- **NEVER use map-merge() with core Odoo variables in theme SCSS**
- **NEVER use ir.asset records for external font URLs**
- **ALWAYS use simple XPath expressions**

---

*TAQAT Techno - Figma to Odoo Theme Generator v4.1*
*Supports Odoo 14-19 with intelligent design extraction*
*Updated with lessons learned from production deployments*
