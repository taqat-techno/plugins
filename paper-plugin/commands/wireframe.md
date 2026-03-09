---
description: 'Create a wireframe for a screen or page'
argument-hint: '<description> [--platform=web|ios|android|desktop]'
---

# Wireframe Command

Rapidly generate wireframes for any screen, page, or component.

## Parse Input

- **Description**: What to wireframe (e.g., "admin dashboard", "user profile page", "checkout flow")
- **Platform**: web (default), ios, android, desktop — detected from `--platform=` flag or context

## Output

### 1. ASCII Wireframe

Always produce a clear ASCII wireframe first. Use box-drawing characters:

```
Symbols:
  ┌─┐ └─┘ ├─┤ ┬ ┴  — boxes and borders
  │                  — vertical lines
  ─                  — horizontal lines
  [Button]           — interactive elements
  (o) ( )            — radio buttons
  [x] [ ]            — checkboxes
  [____]             — text inputs
  [v]                — dropdown selects
  ===                — dividers
  ...                — truncated content
  [img]              — image placeholder
  [icon]             — icon placeholder
```

### 2. Component List

After the wireframe, list all components identified:
```
Components:
  - Header: logo + nav links + user avatar
  - Search: input + filter dropdown + submit button
  - Card: image + title + description + action buttons
  - Pagination: prev/next + page numbers
```

### 3. Responsive Notes

Describe what changes at each breakpoint:
```
Responsive:
  Mobile (< 768px):  Cards stack vertically, hamburger menu
  Tablet (768-992px): 2-column card grid, collapsible sidebar
  Desktop (> 992px):  3-column card grid, persistent sidebar
```

### 4. Code Prototype (Optional)

If the user wants code, generate a minimal HTML/CSS prototype:
- Bootstrap 5 for web (default)
- Platform-appropriate patterns for mobile/desktop
- Include a `<style>` block for quick preview
- Add realistic content (not Lorem ipsum)

## Platform-Specific Wireframe Patterns

### Web
```
┌──────────────────────────────────────┐
│  Logo    Nav1  Nav2  Nav3    [Login]  │
├──────────────────────────────────────┤
│  Content area                        │
└──────────────────────────────────────┘
```

### iOS
```
┌──────────────────────┐
│ ◄ Back    Title    ⋯ │  ← Navigation Bar
├──────────────────────┤
│                      │
│  Content area        │
│                      │
├──────────────────────┤
│ 🏠   🔍   ➕   👤   ⚙ │  ← Tab Bar
└──────────────────────┘
```

### Android
```
┌──────────────────────┐
│ ☰  App Title      🔍 │  ← Top App Bar
├──────────────────────┤
│                      │
│  Content area        │
│                      │
│                 [+]  │  ← FAB
├──────────────────────┤
│ 🏠   🔍   👤         │  ← Bottom Navigation
└──────────────────────┘
```

### Desktop Application
```
┌──────────────────────────────────────┐
│ File  Edit  View  Help               │  ← Menu Bar
├────────────────────────────┬─────────┤
│ [icon] [icon] [icon]  | search... |  │  ← Toolbar
├──────────┬─────────────────┤         │
│ Tree     │  Main Content   │ Props   │
│ View     │                 │ Panel   │
│          │                 │         │
├──────────┴─────────────────┴─────────┤
│ Status: Ready          Ln 1, Col 1   │  ← Status Bar
└──────────────────────────────────────┘
```

## Examples

`/wireframe e-commerce product listing page`
`/wireframe mobile onboarding flow --platform=ios`
`/wireframe settings page with user preferences --platform=android`
`/wireframe CRM dashboard with pipeline view`
`/wireframe login form with social auth options`
