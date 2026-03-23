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
version: "8.0.0"
author: "TaqaTechno"
license: "MIT"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Odoo Theme SCSS Variable Reference

## Critical Load Order Rule

Theme SCSS files load BEFORE core Odoo variables are defined:

```
1. YOUR theme's primary_variables.scss (via prepend)  ← FIRST
2. Odoo core primary_variables.scss                    ← SECOND

CONSEQUENCE: CANNOT use map-merge() with core variables!
```

**WRONG**: `$o-color-palettes: map-merge($o-color-palettes, (...));` → Undefined variable error
**RIGHT**: Define standalone variables without map-merge

---

## 1. $o-theme-font-configs — Google Fonts

```scss
$o-theme-font-configs: (
    '<Font Name>': (
        'family': (<CSS font-family list>),     // Required
        'url': '<Google Fonts query param>',     // Required — NOT the full URL!
        'properties': (                          // Optional: per-context overrides
            '<font-alias>': ( '<key>': <value> ),
        ),
    ),
);
```

**CRITICAL**: The `'url'` key contains **only the query parameter**:
```scss
// CORRECT
'url': 'Poppins:300,300i,400,400i,600,600i,700,700i'

// WRONG — do NOT include full URL
'url': 'https://fonts.googleapis.com/css?family=Poppins:300,400,700'
```

### Font Weight Format
```scss
'url': 'Poppins:300,300i,400,400i,600,600i,700,700i'
//      Light  Light-i  Regular Regular-i SemiBold ...
// Number alone = normal, Number + 'i' = italic
```

### Multi-word Font Names
```scss
'url': 'Open+Sans:300,300i,400,400i,700,700i'
'url': 'IBM+Plex+Sans+Arabic:100,200,300,400,500,600,700'
```

### Font Aliases (for 'properties')

| Alias | Maps To | Usage |
|-------|---------|-------|
| `'base'` | `'font'` | Body text |
| `'headings'` | `'headings-font'` | All headings |
| `'navbar'` | `'navbar-font'` | Navigation |
| `'buttons'` | `'buttons-font'` | Buttons |

### Complete Example

```scss
$o-theme-font-configs: (
    'Poppins': (
        'family': ('Poppins', sans-serif),
        'url': 'Poppins:300,300i,400,400i,500,500i,600,600i,700,700i',
        'properties': (
            'base': ( 'font-size-base': (15 / 16) * 1rem ),
        ),
    ),
    'Playfair Display': (
        'family': ('Playfair Display', serif),
        'url': 'Playfair+Display:400,400i,700,700i',
    ),
);
```

### Arabic/RTL Fonts
```scss
$o-theme-font-configs: (
    'IBM Plex Sans Arabic': (
        'family': ('IBM Plex Sans Arabic', sans-serif),
        'url': 'IBM+Plex+Sans+Arabic:100,200,300,400,500,600,700',
    ),
    'Cairo': (
        'family': ('Cairo', sans-serif),
        'url': 'Cairo:200,300,400,500,600,700,800,900',
    ),
);
```

---

## 2. $o-color-palettes — Color System

### The Five Semantic Colors

| Color | Meaning | Typical Usage |
|-------|---------|---------------|
| `o-color-1` | **Primary/Accent** | Brand color, buttons, links |
| `o-color-2` | **Secondary** | Accent, secondary buttons |
| `o-color-3` | **Light Background** | Section backgrounds, cards |
| `o-color-4` | **White/Lightest** | Content background (#FFFFFF) |
| `o-color-5` | **Dark/Text** | Headings, footer, dark sections |

### Color Combinations (o_cc1 - o_cc5)

| Class | Background | Usage |
|-------|-----------|-------|
| `o_cc1` | `o-color-4` (White) | Main content |
| `o_cc2` | `o-color-3` (Light) | Alternate sections |
| `o_cc3` | `o-color-2` (Secondary) | Accent sections |
| `o_cc4` | `o-color-1` (Primary) | CTA sections |
| `o_cc5` | `o-color-5` (Dark) | Footer, dark |

### Palette Structure

```scss
$o-color-palettes: map-merge($o-color-palettes, (
    'my-palette': (
        'o-color-1': #09294F,
        'o-color-2': #FFA807,
        'o-color-3': #F6F4F0,
        'o-color-4': #FFFFFF,
        'o-color-5': #1B212C,

        // Component assignments
        'menu': 1,
        'footer': 5,
        'copyright': 5,

        // Color combination overrides
        'o-cc5-link': 'o-color-4',
        'o-cc5-btn-primary': 'o-color-2',
    ),
));
```

**NOTE**: `map-merge` with `$o-color-palettes` works ONLY in non-theme modules. In themes (which use prepend), use `$o-website-values-palettes` with `'color-palettes-name'` instead.

### HTML Usage

```xml
<section class="o_cc o_cc1 pt32 pb32"><!-- White bg --></section>
<section class="o_cc o_cc2 pt32 pb32"><!-- Light bg --></section>
<section class="o_cc o_cc5 pt32 pb32"><!-- Dark bg --></section>
```

### Color Derivation (when only 2 colors are available)

```
o-color-3 = lighten(primary, 45%)
o-color-4 = #FFFFFF
o-color-5 = darken(primary, 40%) or #191A19
```

---

## 3. $o-website-values-palettes — Master Configuration (115+ Keys)

### Quick Reference

| Category | Count | Description |
|----------|-------|-------------|
| Typography & Fonts | 13 | Font family configuration |
| Font Sizes | 13 | Base and heading sizes |
| Line Heights | 11 | Text spacing |
| Margins | 22 | Heading and paragraph margins |
| Buttons | 17 | Button styling |
| Inputs | 12 | Form field styling |
| Header | 13 | Header/navigation config |
| Footer | 3 | Footer config |
| Links | 1 | Underline behavior |
| Layout | 3 | Page layout |
| Colors & Gradients | 5 | Palette and gradients |
| Google Fonts | 2 | Additional font loading |

### 3.1 Typography & Fonts

| Key | Description |
|-----|-------------|
| `'font'` | Base font for entire site |
| `'headings-font'` | Font for H1-H6 |
| `'navbar-font'` | Navigation menu font |
| `'buttons-font'` | Button text font |
| `'h2-font'` to `'h6-font'` | Individual heading fonts |
| `'display-1-font'` to `'display-4-font'` | Display text fonts |

### 3.2 Font Sizes

| Key | Default | Description |
|-----|---------|-------------|
| `'font-size-base'` | `1rem` | Base font size (16px) |
| `'small-font-size'` | `0.875rem` | Small text (14px) |
| `'h1-font-size'` to `'h6-font-size'` | Calculated | Heading sizes |
| `'display-1-font-size'` to `'display-6-font-size'` | 5rem-2.5rem | Display sizes |

### 3.3 Line Heights & Margins

| Key | Default | Description |
|-----|---------|-------------|
| `'body-line-height'` | `1.5` | Body text |
| `'headings-line-height'` | `1.2` | All headings |
| `'h2-line-height'` to `'h6-line-height'` | Inherits | Individual |
| `'paragraph-margin-top'` | `0` | Paragraph top |
| `'paragraph-margin-bottom'` | `16px` | Paragraph bottom |
| `'headings-margin-top'` / `'headings-margin-bottom'` | `0` / `0.5rem` | Headings |

### 3.4 Buttons (17 Keys)

| Key | Description |
|-----|-------------|
| `'btn-padding-y'` / `'btn-padding-x'` | Default padding |
| `'btn-font-size'` | Font size |
| `'btn-padding-y-sm'` / `'btn-padding-x-sm'` | Small button |
| `'btn-padding-y-lg'` / `'btn-padding-x-lg'` | Large button |
| `'btn-border-width'` | Border thickness |
| `'btn-border-radius'` / `-sm` / `-lg` | Corner radius |
| `'btn-primary-outline'` | Primary as outline (bool) |
| `'btn-secondary-outline'` | Secondary as outline (bool) |
| `'btn-primary-flat'` / `'btn-secondary-flat'` | Flat style (bool) |
| `'btn-ripple'` | Material ripple effect (bool) |

### 3.5 Inputs (12 Keys)

| Key | Description |
|-----|-------------|
| `'input-padding-y'` / `'input-padding-x'` | Input padding |
| `'input-font-size'` | Input font size |
| `'input-border-width'` | Border thickness |
| `'input-border-radius'` / `-sm` / `-lg` | Corner radius |

### 3.6 Header & Navigation (13 Keys)

| Key | Values | Description |
|-----|--------|-------------|
| `'header-template'` | `'default'` / `'hamburger'` / `'vertical'` / `'sidebar'` | Header layout |
| `'header-links-style'` | `'default'` / `'fill'` / `'outline'` / `'pills'` / `'block'` / `'border-bottom'` | Link style |
| `'header-font-size'` | CSS length | Header text size |
| `'logo-height'` | CSS length | Logo height |
| `'fixed-logo-height'` | CSS length | Logo when fixed |
| `'hamburger-position'` | `'left'` / `'center'` / `'right'` | Desktop position |
| `'hamburger-position-mobile'` | `'left'` / `'center'` / `'right'` | Mobile position |

### 3.7 Footer (3 Keys)

| Key | Values | Description |
|-----|--------|-------------|
| `'footer-template'` | `'default'` / `'centered'` / `'minimalist'` / `'links'` / `'descriptive'` | Layout |
| `'footer-effect'` | `null` / `'slideout_slide_hover'` / `'slideout_shadow'` | Animation |
| `'footer-scrolltop'` | boolean | Scroll-to-top button |

### 3.8 Links & Layout

| Key | Values | Description |
|-----|--------|-------------|
| `'link-underline'` | `'never'` / `'hover'` / `'always'` | Underline behavior |
| `'layout'` | `'full'` / `'boxed'` | Page layout |
| `'body-image'` | URL | Background image |

### 3.9 Colors & Gradients

| Key | Description |
|-----|-------------|
| `'color-palettes-name'` | Active color palette name |
| `'menu-gradient'` | Menu background gradient |
| `'footer-gradient'` | Footer background gradient |

---

## Complete Example — Modern Corporate Theme

```scss
$o-website-values-palettes: (
    (
        'color-palettes-name': 'my-corporate-palette',

        // Typography
        'font': 'Inter',
        'headings-font': 'Inter',
        'navbar-font': 'Inter',
        'buttons-font': 'Inter',
        'font-size-base': 1rem,
        'headings-line-height': 1.3,
        'body-line-height': 1.6,

        // Header
        'header-template': 'default',
        'header-links-style': 'default',
        'logo-height': 48px,
        'fixed-logo-height': 36px,

        // Buttons
        'btn-padding-y': 0.75rem,
        'btn-padding-x': 1.5rem,
        'btn-border-radius': 8px,
        'btn-ripple': true,

        // Inputs
        'input-padding-y': 0.75rem,
        'input-border-radius': 8px,

        // Footer
        'footer-template': 'default',
        'footer-scrolltop': true,

        // Links
        'link-underline': 'hover',
        'layout': 'full',
    ),
);
```

## Typography Multipliers

```scss
$o-theme-h1-font-size-multiplier: (64 / 16); // 64px → 4.0
$o-theme-h2-font-size-multiplier: (48 / 16); // 48px → 3.0
$o-theme-h3-font-size-multiplier: (32 / 16); // 32px → 2.0
$o-theme-h4-font-size-multiplier: (24 / 16); // 24px → 1.5
$o-theme-h5-font-size-multiplier: (20 / 16); // 20px → 1.25
$o-theme-h6-font-size-multiplier: (16 / 16); // 16px → 1.0 (FIXED!)
```
