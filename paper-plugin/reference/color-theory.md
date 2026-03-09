# Color Theory Reference

## Color Wheel & Relationships

```
                    Yellow (60°)
                   /            \
        Yellow-Green              Yellow-Orange
              /                          \
      Green (120°)                  Orange (30°)
              \                          /
        Blue-Green                Red-Orange
                   \            /
                    Blue (240°)     Red (0°/360°)
                        \          /
                     Blue-Violet  Red-Violet
                          \      /
                        Violet (270°)
```

## Palette Generation Algorithms

### Complementary (High Contrast)
- Two colors opposite on the wheel (180° apart)
- Use: CTA buttons against backgrounds, error states
- Example: Blue (#2563EB) + Orange (#EA580C)

### Analogous (Harmonious)
- 3 colors adjacent on the wheel (30° apart)
- Use: Related content sections, gradients
- Example: Blue (#2563EB) + Blue-Violet (#7C3AED) + Violet (#9333EA)

### Triadic (Vibrant)
- 3 colors equally spaced (120° apart)
- Use: Balanced designs needing variety
- Example: Red (#DC2626) + Blue (#2563EB) + Green (#16A34A)

### Split-Complementary (Balanced)
- Base color + 2 colors adjacent to its complement
- Use: Designs needing contrast with less tension than complementary
- Example: Blue (#2563EB) + Yellow-Orange (#F59E0B) + Red-Orange (#EA580C)

### Tetradic/Rectangle (Rich)
- 4 colors forming a rectangle on the wheel
- Use: Complex UIs with many states
- Caution: One color should dominate (60-30-10 rule)

## The 60-30-10 Rule

```
60% — Dominant color (backgrounds, large surfaces)
30% — Secondary color (cards, sections, supporting areas)
10% — Accent color (CTAs, links, highlights, badges)
```

## HSL Manipulation for Generating Shades

Starting from a base color, generate a full scale:

```
Base: hsl(220, 90%, 50%)  — Primary Blue

Scale generation:
  50:  hsl(220, 95%, 97%)  — Lightest (backgrounds)
  100: hsl(220, 90%, 93%)  — Light hover
  200: hsl(220, 85%, 85%)  — Light active
  300: hsl(220, 80%, 70%)  — Mid-light
  400: hsl(220, 85%, 60%)  — Mid
  500: hsl(220, 90%, 50%)  — BASE
  600: hsl(220, 85%, 42%)  — Mid-dark
  700: hsl(220, 80%, 35%)  — Dark
  800: hsl(220, 75%, 25%)  — Darker
  900: hsl(220, 70%, 15%)  — Darkest (text)
  950: hsl(220, 65%, 8%)   — Near-black
```

**Pattern**: As you go darker, reduce saturation slightly and reduce lightness significantly.

## Semantic Color Meanings

| Color | Meaning | Usage |
|-------|---------|-------|
| **Blue** | Trust, stability, professionalism | Links, primary actions, info |
| **Green** | Success, growth, positive | Success messages, confirm, positive metrics |
| **Red** | Danger, error, urgency | Error messages, delete, critical alerts |
| **Yellow/Amber** | Warning, caution, attention | Warning messages, pending states |
| **Orange** | Energy, warmth, action | CTAs, highlights, notifications |
| **Purple** | Luxury, creativity, premium | Premium features, creative tools |
| **Gray** | Neutral, professional, secondary | Text, borders, disabled states, backgrounds |

## Dark Mode Color Rules

### Surface Layers
```
Light Mode:              Dark Mode:
white (#FFFFFF)     →    gray-900 (#111827)   — Base surface
gray-50 (#F9FAFB)  →    gray-800 (#1F2937)   — Surface 1
gray-100 (#F3F4F6) →    gray-700 (#374151)   — Surface 2
gray-200 (#E5E7EB) →    gray-600 (#4B5563)   — Surface 3 / borders
```

### Text Colors
```
Light Mode:              Dark Mode:
gray-900 (#111827) →    gray-50 (#F9FAFB)    — Primary text
gray-600 (#4B5563) →    gray-300 (#D1D5DB)   — Secondary text
gray-400 (#9CA3AF) →    gray-500 (#6B7280)   — Muted text
```

### Brand Colors in Dark Mode
- Increase lightness +10-15%
- Reduce saturation -5-10%
- Verify contrast against dark surfaces
- Example: #2563EB (light mode) → #3B82F6 (dark mode)

## Contrast Ratio Quick Reference

| Ratio | WCAG Level | Valid For |
|-------|-----------|-----------|
| 3:1 | AA Large | Text >= 18px bold or >= 24px, UI components |
| 4.5:1 | AA Normal | All body text < 18px bold |
| 7:1 | AAA Normal | Enhanced accessibility (optional) |

**Quick mental math**: White text on colored background — the color needs lightness <= 45% in HSL.

## Odoo Color System

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
