---
name: admin-rtl-ltr
description: Direction-aware admin UI for mixed RTL/LTR locales. Owns the "use logical CSS properties, not physical" rule, the html dir-attribute placement, the icon-mirroring catalogue (which mirror, which don't), and the LTR-locked content rule (code, charts, numeric tables). Activates when adding any spacing, alignment, icon, modal, drawer, or any UI that could read incorrectly in an RTL locale. Generic and portable — locale list is project-supplied.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - dir attribute placement (html level)
  - logical CSS properties usage (`margin-inline-start` over `margin-left`)
  - Tailwind logical-utility convention (`ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`)
  - icon-mirroring catalogue (which icons flip, which stay)
  - LTR-locked content (code, charts, numeric tables, dates in technical contexts)
  - text-align: start/end vs left/right
  - keyboard focus order in RTL
defers_to:
  - admin-shell (where the direction wrapper is mounted)
  - admin-crud (table column alignment per content type)
  - admin-states (toast position in RTL)
  - project locale config (which locales are RTL)
user_invocable: false
---

# admin-rtl-ltr

## Purpose

Adding a second locale to an admin panel built without direction awareness leads to weeks of "the icon is on the wrong side, the modal opens from the wrong edge, the search input pushes the chips off-screen." This skill front-loads the rules so a future second locale costs nothing.

The rule is one sentence: **use logical CSS properties everywhere; let the browser do the flip.** This skill is the catalogue of where that applies.

## When to use

Activate when:

- Adding any spacing, alignment, or positioning to an admin component.
- Adding an icon next to text.
- Adding a modal, drawer, popover, tooltip.
- Adding a chart, code block, numeric table, or technical display.
- Configuring the i18n provider (which locales are RTL).
- Auditing existing UI before adding an RTL locale.

Skip when:

- The application is permanently single-locale and that locale is LTR. (Still good practice though — costs nothing.)

## Inputs (adapter)

1. **RTL locale list** — empty if no RTL locale. Common RTL locales: Arabic (`ar*`), Hebrew (`he`), Persian/Farsi (`fa`), Urdu (`ur`).
2. **CSS framework** — Tailwind (use logical utilities), CSS Modules / vanilla CSS (use logical properties directly), CSS-in-JS (same).
3. **Icon library** — react-icons, lucide, heroicons, FontAwesome, custom SVGs. The library matters for icon mirroring.

## Read-only investigation steps

1. **Is `<html dir="...">` set anywhere?** If yes, by what? If no, add it.
2. **Does the codebase already use logical utilities (`ms-`/`me-`)** or physical (`ml-`/`mr-`)? Audit one large component to learn the pattern.
3. **Are icons inside buttons aligned via `margin-left: 8px` or `margin-inline-start: 0.5rem`?** Physical = breaks in RTL; logical = fine.
4. **Where do toasts appear?** Hardcoded `bottom: 16px; right: 16px` breaks in RTL. Should be `bottom: 16px; inset-inline-end: 16px`.

## Decision framework

### `<html dir="...">` placement

```tsx
// In the admin shell, derive direction from locale
const isRtl = RTL_LOCALES.includes(currentLocale)
return (
  <html lang={currentLocale} dir={isRtl ? 'rtl' : 'ltr'}>
    ...
  </html>
)
```

- The `dir` attribute goes on `<html>` (or `<body>` if framework forces). Setting it deeper (per component) is allowed but rarely correct.
- The `dir` value is driven by locale: locale changes → direction changes → layout flips. No additional component logic needed.
- For server-rendered apps: the locale must be known on first paint to avoid the LTR-flash-then-RTL.

### Logical CSS properties

Replace physical with logical everywhere:

| Physical | Logical | Notes |
|---|---|---|
| `margin-left` | `margin-inline-start` | |
| `margin-right` | `margin-inline-end` | |
| `padding-left` | `padding-inline-start` | |
| `padding-right` | `padding-inline-end` | |
| `left: 16px` | `inset-inline-start: 16px` | |
| `right: 16px` | `inset-inline-end: 16px` | |
| `text-align: left` | `text-align: start` | |
| `text-align: right` | `text-align: end` | |
| `border-left` | `border-inline-start` | |
| `border-right` | `border-inline-end` | |
| `float: left` | `float: inline-start` | |
| `float: right` | `float: inline-end` | |

### Tailwind logical utilities

| Physical | Logical |
|---|---|
| `ml-4` | `ms-4` (margin-start) |
| `mr-4` | `me-4` (margin-end) |
| `pl-4` | `ps-4` (padding-start) |
| `pr-4` | `pe-4` (padding-end) |
| `left-0` | `start-0` |
| `right-0` | `end-0` |
| `text-left` | `text-start` |
| `text-right` | `text-end` |
| `border-l` | `border-s` |
| `border-r` | `border-e` |
| `rounded-l-md` | `rounded-s-md` |
| `rounded-r-md` | `rounded-e-md` |

Configure your Tailwind to support logical utilities (modern Tailwind has them built-in; older versions need a plugin).

### Icon mirroring catalogue

| Icon category | Mirror in RTL? |
|---|---|
| Directional arrows (back, forward, next, previous) | YES |
| Chevrons in pagination, breadcrumbs, menu indicators | YES |
| Reply / forward (email actions) | YES |
| "Continue" / "Submit" arrow on buttons | YES |
| Hamburger menu (≡) | NO (symmetric) |
| Checkmark, X, settings gear | NO (symbol, not directional) |
| Logos, branding | NO |
| Numbers, currency symbols, code | NO (these stay LTR — see below) |
| Play / pause / stop (media) | NO (universally understood) |
| Search icon | NO (universally understood) |
| Trash, edit pencil | NO |
| Tick / cross for progress | NO |
| Sort indicators (▲▼) | NO (the arrow points to the action's direction, not flow) |

Mirror by CSS `transform: scaleX(-1)` on the icon, conditionally applied via the `[dir="rtl"]` selector:

```css
[dir="rtl"] .icon-directional {
  transform: scaleX(-1);
}
```

Or with Tailwind:

```html
<ArrowRight className="rtl:scale-x-[-1]" />
```

### LTR-locked content

Some content stays LTR even in RTL locales:

| Content | Direction | Why |
|---|---|---|
| Source code blocks | LTR | Code is LTR semantics regardless of UI language |
| Mathematical / scientific notation | LTR | `e = mc²` reads LTR everywhere |
| Currency amounts in tables | LTR | Numerals read left-to-right by convention; column alignment is right-align for numbers |
| File paths, URLs, UUIDs | LTR | Technical identifiers |
| Phone numbers (international format) | LTR | `+966 50 ...` reads LTR |
| Chart axes (default) | LTR | Most charting libraries assume LTR; mirror only if explicitly required by domain |
| Date in technical contexts (`2026-05-28T14:30:00Z`) | LTR | ISO-8601 reads LTR |
| Date in human contexts (`28 May 2026`) | follows locale | Locale-formatted dates respect direction |

Apply `<div dir="ltr">` around these elements regardless of the surrounding direction. Many tooling defaults are already correct (e.g., `<pre><code>` is naturally LTR in most browsers; verify).

### Text alignment by content type

| Cell content | Alignment (start/end vs explicit) |
|---|---|
| Free text (names, addresses, descriptions) | `text-align: start` (respects direction) |
| Numbers, currency | `text-align: end` (numbers align right in LTR; behavior consistent across directions) |
| Status badges, icons | `text-align: center` |
| Headings | `text-align: start` |
| Action buttons in table cells | `text-align: end` (trailing) |

### Modal / drawer positioning

| Element | Physical | Logical |
|---|---|---|
| Right-side drawer in LTR | `right: 0` | `inset-inline-end: 0` |
| Left-side drawer in LTR | `left: 0` | `inset-inline-start: 0` |
| Bottom-right toast | `bottom: 16px; right: 16px` | `bottom: 16px; inset-inline-end: 16px` |
| Tooltip pointing right | `right: -8px` | `inset-inline-end: -8px` |

A "right-side drawer in LTR" becomes a "left-side drawer in RTL" — this is correct behavior because the trailing edge of the screen mirrors with direction.

### Focus order

Browser handles focus order via DOM order — `dir` attribute does NOT reverse focus traversal. If a layout has visual order that differs from DOM order (e.g., `flex-direction: row-reverse`), focus traversal will not match visual flow. Fix by using `flex-direction: row` (the default) with logical alignment; let the browser flip via `dir`.

### Forms in RTL

- Input fields render with text from the appropriate edge based on `dir`.
- Numbers in input fields render LTR even within an RTL form (use `dir="ltr"` on the input, OR set `type="number"`).
- Labels naturally align with `text-align: start`.
- Inline form layouts (label-input on the same row) use logical gap utilities (`gap-`, not `margin-left`).

## Safety gates

- **Never** use physical CSS properties (`margin-left`, `padding-right`, `left:`, `right:`) in new code.
- **Never** hardcode `text-align: left` or `text-align: right` for prose; use `start` / `end`.
- **Never** mirror non-directional icons (logos, branding, currency symbols, code symbols).
- **Never** apply `dir="rtl"` to LTR-locked content (code, paths, ISO dates).
- **Never** rely on a `flex-direction: row-reverse` trick to "fix RTL" — this breaks focus order.
- **Never** set the dir attribute deeper than the shell unless you have a specific block-of-text reason (e.g., quoting a string in the opposite direction).
- **Never** add an RTL locale to the locale list without auditing existing physical properties first.

## Validation checklist

Before committing a UI change:

- [ ] No new `ml-`, `mr-`, `pl-`, `pr-`, `left-`, `right-`, `text-left`, `text-right` (Tailwind) — use logical equivalents.
- [ ] No new `margin-left`, `padding-right`, `left:`, `right:`, `text-align: left|right` in CSS files — use logical properties.
- [ ] Directional icons (arrows, chevrons) mirror via `[dir="rtl"]` rule.
- [ ] Non-directional icons (search, settings, trash) do NOT mirror.
- [ ] Code blocks, URLs, paths, ISO timestamps wrapped in `dir="ltr"` blocks.
- [ ] Numeric table columns right-aligned via `text-end` (not `text-right`).
- [ ] Toasts positioned with `inset-inline-end`.
- [ ] Drawers / popovers use logical positioning.
- [ ] Manually tested in both LTR and one RTL locale if any RTL locale exists in the project.
- [ ] No `flex-direction: row-reverse` for direction flipping.

## Output format

When scaffolding a component, ensure output includes:

```
DIRECTION-AWARE STYLES
  Spacing: ms-/me-/ps-/pe- (or margin-inline-*)
  Positioning: start-/end-/inset-inline-* (no left/right)
  Text-align: text-start / text-end (no text-left/right)
  Icons: directional → mirror; non-directional → no mirror
  LTR-locked: <list any embedded code/URL/numeric blocks>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| `ml-4` on every spacing | RTL layouts squeeze on the wrong side | `ms-4` |
| `flex-direction: row-reverse` to "fix RTL" | Breaks focus order; surprises future devs | Use logical properties; let `dir` do it |
| Mirror the search icon for RTL | Magnifying glass is universal; users do not expect it flipped | Do not mirror non-directional icons |
| Code block inside an `<div dir="rtl">` page renders as `;)(args(foo` | Code is LTR semantics | Wrap code in `dir="ltr"` |
| `<html>` has no `dir` attribute | Browser defaults to LTR even for Arabic content | Set `dir` from locale |
| Toast position hardcoded `right: 16px` | Toast goes off-screen in RTL | `inset-inline-end: 16px` |
| `dir` applied per-component instead of per-page | Some areas flip, others do not; inconsistent | One `<html dir>` per locale |
| Mirror an arrow that means "go up" or "go down" | Vertical arrows are not flow-directional | Do not mirror |
| Hardcoded `font-family: 'Arial'` for English, 'Tahoma' for Arabic | One per locale doubles the maintenance | Use a font with broad script support, or use `font-family` fallback chain |

## Portability rationale

Logical CSS properties are supported in all modern browsers. The rules apply to:

- Tailwind (with logical utilities enabled — default in modern versions)
- CSS Modules
- Vanilla CSS
- CSS-in-JS
- Any framework that renders to HTML/CSS

The skill does not depend on a specific React component library, icon library, or i18n library.

## Cross-references

- `admin-shell` — where the direction wrapper / `<html dir>` is mounted.
- `admin-crud` — table column alignment per content type.
- `admin-states` — toast position; skeleton direction; partial-error indicator position.
- `admin-forms` — input direction handling.
- `admin-route-auditor` (agent) — greps for physical-property usage and flags as RTL risk.
