# Platform-Specific Design Guidelines

## iOS — Human Interface Guidelines (HIG)

### Core Principles
1. **Clarity**: Text is legible, icons precise, decorations subtle and appropriate
2. **Deference**: Content is the focus, chrome is minimal
3. **Depth**: Visual layers and realistic motion provide hierarchy

### Navigation Patterns

| Pattern | When to Use | Max Items |
|---------|-------------|-----------|
| **Tab Bar** (bottom) | Top-level destinations, persistent | 2-5 |
| **Navigation Bar** (top) | Hierarchical drill-down (push/pop) | N/A |
| **Sidebar** (iPad) | iPad apps with rich navigation | Unlimited |
| **Modal** | Focused tasks, self-contained workflows | N/A |

### Key Measurements
- Touch target: **44x44 points** minimum
- Navigation bar height: **44pt** (standard), **96pt** (large title)
- Tab bar height: **49pt**
- Status bar: **47pt** (notch), **20pt** (legacy)
- Safe area: always respect `safeAreaInsets`

### Typography (SF Pro)
```
Large Title:  34pt Bold    — Landing screens
Title 1:      28pt Bold    — Primary headings
Title 2:      22pt Bold    — Section headings
Title 3:      20pt Semibold — Sub-sections
Headline:     17pt Semibold — List items
Body:         17pt Regular  — Content text
Callout:      16pt Regular  — Secondary text
Subheadline:  15pt Regular  — Supporting info
Footnote:     13pt Regular  — Small details
Caption 1:    12pt Regular  — Labels, timestamps
Caption 2:    11pt Regular  — Smallest text
```

### iOS Conventions
- Use SF Symbols for icons (2,500+ symbols)
- Support Dynamic Type (user-adjustable text sizes)
- Swipe gestures: swipe-to-delete, swipe-to-reveal-actions
- Pull-to-refresh for list/feed content
- Long press → context menu
- Haptic feedback on meaningful interactions
- Rounded corners: 10-20pt radius on cards/buttons

---

## Android — Material Design 3

### Core Principles
1. **Adaptive**: Responsive across devices and screen sizes
2. **Expressive**: Dynamic color, motion, and shape convey brand
3. **Personal**: Material You — personalized through wallpaper-based themes

### Navigation Patterns

| Pattern | When to Use | Max Items |
|---------|-------------|-----------|
| **Bottom Navigation** | 3-5 top-level destinations | 3-5 |
| **Navigation Drawer** | 5+ destinations, deep hierarchy | Unlimited |
| **Tabs** | Related content at same level | 2-7 |
| **Bottom App Bar** | Primary actions + FAB | 4 + FAB |

### Key Measurements
- Touch target: **48x48dp** minimum (with 8dp spacing between)
- Top app bar height: **64dp**
- Bottom navigation height: **80dp**
- FAB size: **56dp** (standard), **40dp** (small), **96dp** (large)
- Corner radius: small (4dp), medium (12dp), large (16dp), extra-large (28dp)

### Elevation System (Tone-based in M3)
```
Level 0: Surface (no elevation)  — Main background
Level 1: +1 tonal shift          — Cards, sheets
Level 2: +2 tonal shift          — Navigation bars
Level 3: +3 tonal shift          — Search bars
Level 4: +4 tonal shift          — App bars
Level 5: +5 tonal shift          — FAB, overlays
```

### Material Design 3 Color Roles
```
Primary         → CTAs, active states, emphasis
On Primary      → Text/icons on primary surfaces
Primary Container → Filled buttons/cards at lower emphasis
Secondary       → Less prominent actions
Tertiary        → Accent, complementary color
Surface         → Background
Surface Variant → Secondary backgrounds
Error           → Error states
Outline         → Borders, dividers
```

### Android Conventions
- FAB for the single most important action per screen
- Snackbar for brief feedback (max 2 lines)
- Bottom sheets for supplementary content
- Chips for filters, tags, actions
- Edge-to-edge design (content extends under system bars)
- Predictive back gesture support

---

## Windows — Fluent Design System

### Core Principles
1. **Light**: Acrylic material — translucent layers
2. **Depth**: Parallax, layering, z-depth
3. **Motion**: Connected animations, transitions
4. **Material**: Acrylic (blur), Reveal (highlight on hover)
5. **Scale**: Responsive across devices

### Key Measurements
- Touch target: **40x40px** minimum (32x32px for mouse-first)
- Title bar height: **32px**
- Navigation pane width: **320px** (expanded), **48px** (compact)
- Command bar height: **48px**

### Navigation
- **NavigationView**: Hamburger sidebar (primary navigation)
- **TabView**: Browser-like tabs
- **BreadcrumbBar**: Hierarchical path display
- **CommandBar**: Toolbar with actions

### Windows Conventions
- Right-click context menus for advanced actions
- Keyboard shortcuts for all primary actions (Ctrl+S, Ctrl+Z, etc.)
- Multi-window support
- Light/Dark theme following system preference
- Mica material for app background

---

## Web Conventions

### Standard Layout Elements

| Element | Position | Height | Content |
|---------|----------|--------|---------|
| **Navbar** | Top, fixed or sticky | 56-72px | Logo, nav links, search, user menu |
| **Hero** | Below navbar | 400-600px | Headline, subtext, CTA, media |
| **Content** | Main area | Flexible | Sectioned with consistent spacing |
| **Footer** | Bottom | 200-400px | Links, legal, social, newsletter |
| **Breadcrumb** | Below navbar | 40px | Path: Home > Category > Page |
| **Sidebar** | Left (nav) or Right (filters) | Full height | Navigation or contextual info |

### Standard Components

| Component | Usage | Key Variants |
|-----------|-------|-------------|
| **Button** | Actions | Primary, secondary, ghost, danger, icon-only |
| **Input** | Data entry | Text, email, password, number, search |
| **Select** | Choice from list | Single, multi, searchable, grouped |
| **Card** | Content container | Basic, clickable, with image, horizontal |
| **Modal** | Focused task | Small (400px), medium (600px), large (800px) |
| **Toast/Alert** | Feedback | Success, warning, error, info; dismissible |
| **Badge** | Status/count | Dot, number, text; colors for status |
| **Avatar** | User identity | Circle, rounded, sizes (sm/md/lg/xl) |
| **Table** | Structured data | Sortable, filterable, selectable, expandable |
| **Pagination** | Navigate pages | Numbered, prev/next, load more |
| **Breadcrumb** | Path display | Separator: >, /, → |
| **Tabs** | Content sections | Horizontal, vertical, pills, underline |

### Responsive Web Conventions
- Mobile-first CSS (`min-width` media queries)
- Hamburger menu on mobile (< 768px)
- Collapsible sidebar at tablet breakpoint
- Fluid images: `max-width: 100%; height: auto;`
- Container max-widths: 540 / 720 / 960 / 1140 / 1320px
- Stack columns on mobile: grid goes from multi-column to single-column
