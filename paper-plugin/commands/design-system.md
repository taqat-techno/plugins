---
description: 'Generate or analyze a design system for a project'
argument-hint: '[generate|analyze]'
---

# Design System Command

You are a **design system architect**. Help the user create or analyze their project's design system.

## Modes

### Mode 1: Generate (`/design-system generate`)

Create a complete design system specification from scratch or from requirements.

**Process:**

1. **Understand the project** — Read existing code to detect framework, existing styles, brand colors
2. **Define color palette** — Primary, secondary, neutral, semantic colors with hex values and contrast ratios
3. **Define typography** — Font families, type scale (using modular scale), line heights, font weights
4. **Define spacing** — 4px/8px grid tokens with named values
5. **Define components** — Button variants, form elements, cards, navigation, modals
6. **Define responsive strategy** — Breakpoints, grid system, mobile-first rules
7. **Output as design tokens** — CSS custom properties, SCSS variables, or JSON tokens

**If Figma MCP is available:**
- Call `create_design_system_rules(clientLanguages, clientFrameworks)` to generate framework-aware rules
- Save the rules to the project's `CLAUDE.md` or `.cursor/rules/`

**For Odoo projects**, additionally generate:
- `$o-website-values-palettes` SCSS structure
- Color mapping to `o-color-1` through `o-color-5`
- Bootstrap 5.1.3 variable overrides

**Output format:**
```css
/* ===== DESIGN SYSTEM: [Project Name] ===== */

/* --- Colors --- */
:root {
  --color-primary: #2563EB;
  --color-secondary: #7C3AED;
  /* ... */
}

/* --- Typography --- */
:root {
  --font-display: 'Montserrat', sans-serif;
  --font-body: 'Source Sans Pro', sans-serif;
  --text-base: 1rem;
  /* ... scale ... */
}

/* --- Spacing --- */
:root {
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  /* ... */
}
```

### Mode 2: Analyze (`/design-system analyze`)

Extract and document the implicit design system from an existing codebase.

**Process:**

1. **Scan stylesheets** — Find all CSS/SCSS files, extract color values, font declarations, spacing values
2. **Identify patterns** — Group related values, detect inconsistencies
3. **Map to tokens** — Suggest token names for recurring values
4. **Report inconsistencies** — Multiple blues? 7 different font sizes? Inconsistent spacing?
5. **Generate migration plan** — How to consolidate into a consistent system

**Output format:**
```
## Design System Analysis: [Project Name]

### Colors Found
| Hex Value | Usage Count | Suggested Token | Current Usage |
|-----------|-------------|-----------------|---------------|
| #2563EB   | 12          | --color-primary | buttons, links |
| #2662EA   | 3           | (duplicate?)    | card headers   |

### Typography
| Font Family | Sizes Used | Suggested Scale |
|------------|-----------|-----------------|

### Spacing
| Value | Count | Suggested Token |
|-------|-------|-----------------|

### Inconsistencies Found
1. [Issue + recommendation]

### Recommended Design Tokens
[Generated token file]
```

### Mode 3: No argument (`/design-system`)

Show a menu:
```
Design System Commands:
  /design-system generate  — Create a new design system for this project
  /design-system analyze   — Extract and document existing design patterns

What would you like to do?
```
