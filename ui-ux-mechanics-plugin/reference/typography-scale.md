# Typography Scale Reference

## Modular Type Scales

All scales calculated from base size of 16px (1rem).

| Scale Name | Ratio | Sizes (px): xs / sm / base / lg / xl / 2xl / 3xl / 4xl |
|-----------|-------|--------------------------------------------------------|
| Minor Second | 1.067 | 14 / 15 / **16** / 17 / 18 / 19 / 21 / 22 |
| Major Second | 1.125 | 13 / 14 / **16** / 18 / 20 / 23 / 25 / 29 |
| Minor Third | 1.200 | 11 / 13 / **16** / 19 / 23 / 28 / 33 / 40 |
| Major Third | 1.250 | 10 / 13 / **16** / 20 / 25 / 31 / 39 / 49 |
| Perfect Fourth | 1.333 | 9 / 12 / **16** / 21 / 28 / 38 / 50 / 67 |
| Augmented Fourth | 1.414 | 8 / 11 / **16** / 23 / 32 / 45 / 64 / 90 |
| Perfect Fifth | 1.500 | 7 / 11 / **16** / 24 / 36 / 54 / 81 / 121 |

### When to Use Each Scale

| Scale | Best For | Character |
|-------|----------|-----------|
| Minor/Major Second (1.067-1.125) | Dense data UIs, dashboards, admin panels | Subtle hierarchy |
| Minor Third (1.200) | General-purpose apps, balanced content | Most versatile |
| Major Third (1.250) | Marketing pages, blogs, readability focus | Clear hierarchy |
| Perfect Fourth (1.333) | Editorial, magazine layouts, landing pages | Strong drama |
| Perfect Fifth+ (1.500+) | Posters, hero sections, display-heavy | Maximum impact |

## CSS Implementation

```css
:root {
  /* Scale: Major Third (1.250) — base 16px */
  --text-xs:   0.64rem;   /* 10.24px */
  --text-sm:   0.80rem;   /* 12.80px */
  --text-base: 1.00rem;   /* 16.00px */
  --text-lg:   1.25rem;   /* 20.00px */
  --text-xl:   1.563rem;  /* 25.00px */
  --text-2xl:  1.953rem;  /* 31.25px */
  --text-3xl:  2.441rem;  /* 39.06px */
  --text-4xl:  3.052rem;  /* 48.83px */
  --text-5xl:  3.815rem;  /* 61.04px */
}
```

## Proven Font Pairings

### Serif + Sans-Serif (Classic Contrast)

| Display (Headings) | Body (Text) | Vibe |
|-------------------|-------------|------|
| Playfair Display | Source Sans Pro | Editorial, elegant |
| Merriweather | Open Sans | Warm, readable |
| Lora | Roboto | Classic meets modern |
| DM Serif Display | DM Sans | Contemporary editorial |
| Libre Baskerville | Nunito Sans | Literary, scholarly |
| Cormorant Garamond | Proza Libre | Refined luxury |

### Sans-Serif + Sans-Serif (Modern)

| Display (Headings) | Body (Text) | Vibe |
|-------------------|-------------|------|
| Montserrat | Source Sans Pro | Modern professional |
| Raleway | Lato | Clean tech |
| Oswald | Open Sans | Bold impact |
| Poppins | Inter | Friendly professional |
| Space Grotesk | Inter | Technical, developer-focused |
| Work Sans | Nunito | Approachable, startup |

## Line Height Guidelines

| Content Type | Line Height | Explanation |
|-------------|-------------|-------------|
| Body text (16-18px) | 1.5 - 1.75 | Optimal reading comfort |
| Large body (20-24px) | 1.4 - 1.6 | Slightly tighter for larger text |
| Headings (24-48px) | 1.1 - 1.3 | Tight for visual compactness |
| Display text (48px+) | 1.0 - 1.2 | Very tight, almost solid |
| UI labels, buttons | 1.2 - 1.4 | Compact for interface elements |
| Code blocks | 1.6 - 1.8 | Extra space for scannability |
| Captions, footnotes | 1.4 - 1.6 | Comfortable at small sizes |

## Optimal Line Length

```
Ideal: 45-75 characters per line (including spaces)

For web:
  max-width: 65ch;  /* ~65 characters — optimal */
  max-width: 75ch;  /* Maximum acceptable */

Bootstrap equivalents:
  col-lg-8 offset-lg-2  — roughly 60-70 chars at desktop
  col-md-10 offset-md-1 — roughly 55-65 chars at tablet
```

## Fluid Typography (No Breakpoints)

```css
/* Scales smoothly from 16px at 320px viewport to 20px at 1200px */
html {
  font-size: clamp(1rem, 0.5rem + 1.5vw, 1.25rem);
}

/* Heading that scales from 24px to 48px */
h1 {
  font-size: clamp(1.5rem, 1rem + 3vw, 3rem);
}

/* Subheading that scales from 18px to 28px */
h2 {
  font-size: clamp(1.125rem, 0.75rem + 1.5vw, 1.75rem);
}
```

## Font Weight Usage

| Weight | CSS Value | Usage |
|--------|-----------|-------|
| Thin | 100 | Display text only, decorative |
| Light | 300 | Subtitles, large pull quotes |
| Regular | 400 | Body text, descriptions |
| Medium | 500 | Subheadings, emphasis, UI labels |
| Semi-Bold | 600 | Section headings, nav links |
| Bold | 700 | Page headings, CTAs, important info |
| Extra-Bold | 800 | Hero headlines, display text |
| Black | 900 | Ultra-impact display only |

## Letter Spacing Guidelines

| Text Type | Letter Spacing | Reason |
|-----------|---------------|--------|
| Body text | 0 (default) | Already optimized |
| ALL CAPS labels | +0.05em to +0.1em | Improves readability of uppercase |
| Large headings (40px+) | -0.02em to -0.01em | Tighten for visual compactness |
| Small text (12px) | +0.01em to +0.03em | Open up for legibility |

## Vertical Rhythm

Maintain consistent vertical spacing using a baseline grid:

```
Base unit: 8px (0.5rem)

Spacing between elements:
  Same group:     8px  (1 unit)
  Related blocks: 16px (2 units)
  Sections:       32px (4 units)
  Major sections: 48px (6 units)
  Page sections:  64px (8 units)

Line height should be a multiple of the base:
  16px text × 1.5 line-height = 24px (3 × 8px) ✓
  20px text × 1.2 line-height = 24px (3 × 8px) ✓
```

## Bootstrap 5 Typography Classes

```
Font sizes:  .fs-1 (2.5rem) → .fs-6 (1rem)
Weights:     .fw-bold .fw-semibold .fw-normal .fw-light
Style:       .fst-italic .fst-normal
Alignment:   .text-start .text-center .text-end
Transform:   .text-uppercase .text-lowercase .text-capitalize
Wrapping:    .text-wrap .text-nowrap .text-truncate
Display:     .display-1 → .display-6 (larger heading sizes)
Lead:        .lead (larger paragraph text, 1.25rem)
```
