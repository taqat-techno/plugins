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

## Complete primary_variables.scss Template

```scss
// ===================================================================
// Theme: {{THEME_DISPLAY_NAME}}
// Generated from Figma: {{FIGMA_URL}}
// Generated by TAQAT Techno /create-theme command
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

// === Website Values Palette ===
$o-website-values-palettes: (
    (
        'color-palettes-name': '{{PALETTE_NAME}}',

        // Typography
        'font': '{{BODY_FONT}}',
        'headings-font': '{{HEADINGS_FONT}}',
        'navbar-font': '{{NAVBAR_FONT}}',
        'buttons-font': '{{BUTTONS_FONT}}',
        'headings-line-height': {{HEADINGS_LINE_HEIGHT}},
        'line-height-base': {{BODY_LINE_HEIGHT}},

        // Header
        'header-template': '{{HEADER_TEMPLATE}}',
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
        'footer-template': '{{FOOTER_TEMPLATE}}',
        'footer-scrolltop': true,

        // Links
        'link-underline': 'never',
    ),
);

// === Color Palette from Figma ===
// o-color-1: Primary brand color
// o-color-2: Secondary/accent color
// o-color-3: Light backgrounds
// o-color-4: White/body base
// o-color-5: Dark text/headings
$o-color-palettes: map-merge($o-color-palettes, (
    '{{PALETTE_NAME}}': (
        'o-color-1': {{COLOR_1}},  // Primary: {{COLOR_1_NAME}}
        'o-color-2': {{COLOR_2}},  // Secondary: {{COLOR_2_NAME}}
        'o-color-3': {{COLOR_3}},  // Light BG
        'o-color-4': {{COLOR_4}},  // White/Base
        'o-color-5': {{COLOR_5}},  // Dark Text
        'menu': 1,
        'footer': 1,
        'copyright': 5,
    ),
));

// === Font Configuration ===
$o-theme-font-configs: map-merge($o-theme-font-configs, (
    '{{BODY_FONT}}': (
        'family': ('{{BODY_FONT}}', sans-serif),
        'url': '{{FONT_URL}}',
        'properties': (
            'base': (
                'font-size-base': 1rem,
                'line-height-base': {{BODY_LINE_HEIGHT}},
            ),
        ),
    ),
));

// === Extended Color System ===
$o-white: #FFFFFF !default;
$o-black: {{COLOR_5}} !default;
$o-success: #28a745 !default;
$o-info: #17a2b8 !default;
$o-warning: #ffc107 !default;
$o-danger: #dc3545 !default;

// === Background Shapes ===
$o-bg-shapes: change-shape-colors-mapping('web_editor', 'Wavy/21', (2: 1));
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

## Notes

- Figma account access required (logged in via Chrome)
- H6 is always fixed at 16px (1rem) as the base reference
- Display classes extend the hierarchy for designs with large hero text
- Auto-fix attempts 3 times before reporting failure
- All generated code follows TaqaTechno standards

---

*TAQAT Techno - Figma to Odoo Theme Generator v4.0*
*Supports Odoo 14-19 with intelligent design extraction*
