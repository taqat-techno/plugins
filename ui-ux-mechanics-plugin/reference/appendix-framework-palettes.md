# Appendix: framework-specific palette mappings

Optional examples of how the generic palette from `color-theory.md` maps onto one framework's theme variables. Nothing in the core design guidance depends on this file. If the `odoo` plugin is installed, its theme skills own the authoritative Odoo theming rules; prefer them.

## Odoo website themes

### o-color-1 through o-color-5

```
o-color-1: Primary brand         → Headers, primary buttons, links
o-color-2: Secondary/accent      → Hover states, badges, accents
o-color-3: Text/dark             → Headings, body text, dark backgrounds
o-color-4: Light background      → Card backgrounds, alternating rows
o-color-5: Border/muted          → Dividers, subtle borders, muted text
```

### Generating Odoo Palettes
```scss
$o-website-values-palettes: (
  'my-palette': (
    'o-color-1': #1E40AF,    // Deep blue — brand
    'o-color-2': #F59E0B,    // Amber — accent
    'o-color-3': #1F2937,    // Near-black — text
    'o-color-4': #F3F4F6,    // Light gray — backgrounds
    'o-color-5': #D1D5DB,    // Medium gray — borders
    'header': 'o-color-1',
    'footer': 'o-color-3',
    'copyright': 'o-color-5',
  ),
);
```
