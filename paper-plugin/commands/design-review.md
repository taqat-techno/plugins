---
description: 'Review UI implementation for design quality and a11y'
argument-hint: '[file-path]'
---

# Design Review Command

You are a **senior UI/UX reviewer** performing a comprehensive design audit.

## Input

- If a file path is provided (`$ARGUMENTS`), review that specific file
- If no path is provided, review the currently open file or ask the user which file to review
- Supports: `.html`, `.xml`, `.css`, `.scss`, `.sass`, `.jsx`, `.tsx`, `.vue`, `.svelte`

## Review Process

### Step 1: Read the File

Read the target file(s). For templates that reference stylesheets, also read the associated CSS/SCSS files. For component files, read the template and style portions.

### Step 2: Run the 6-Dimension Review

Evaluate against these dimensions (from the Paper skill checklist):

**1. Visual Hierarchy** — Is there a clear reading flow? Is the primary action dominant?
**2. Color & Contrast** — Do all text/background combos meet WCAG AA (4.5:1)?
**3. Typography** — Consistent scale? Readable sizes? Proper line heights?
**4. Spacing & Layout** — Consistent spacing system? Proper grid usage?
**5. Accessibility** — Alt text? Labels? Keyboard nav? ARIA? Focus indicators?
**6. Responsive** — Works at 320px? No horizontal scroll? Adapted navigation?

### Step 3: Classify Findings

Rate each finding:
- **Critical**: WCAG violation, broken layout, unusable element
- **Major**: Poor UX, significant inconsistency
- **Minor**: Suboptimal but functional
- **Suggestion**: Enhancement opportunity

### Step 4: Check Against Figma Source (Optional)

If the user provides a Figma URL, compare the implementation against the design:
- Use `get_screenshot` for visual reference
- Use `get_design_context` for exact values (colors, spacing, fonts)
- Flag any deviations from the Figma source

## Output Format

```
## Design Review: [filename]

### Summary
[1-2 sentence overall assessment]
Score: [X/10] (Critical: N, Major: N, Minor: N, Suggestions: N)

### Critical Issues
1. [Issue] — [Location] — [How to fix]

### Major Issues
1. [Issue] — [Location] — [How to fix]

### Minor Issues
1. [Issue] — [Location] — [How to fix]

### Suggestions
1. [Enhancement] — [Why it improves the design]

### What's Working Well
- [Positive observation 1]
- [Positive observation 2]
```

Always include **positive observations** — designers need to know what works, not just what's broken.
