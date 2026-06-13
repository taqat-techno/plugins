# Layout Patterns Reference

## 20+ Common UI Layout Patterns

### 1. Holy Grail (Header + Sidebar + Content + Footer)
```
┌──────────────────────────────────────┐
│              Header                  │
├──────────┬──────────────┬────────────┤
│          │              │            │
│  Left    │   Content    │   Right    │
│  Sidebar │   Area       │   Sidebar  │
│          │              │            │
├──────────┴──────────────┴────────────┤
│              Footer                  │
└──────────────────────────────────────┘
CSS: display: grid;
     grid-template: "header header header" auto
                    "left   content right"  1fr
                    "footer footer  footer" auto
                    / 250px 1fr     250px;
```

### 2. Sidebar Layout (Admin/Dashboard Standard)
```
┌──────────┬───────────────────────────┐
│          │  Top Bar            [U]   │
│  Side    ├───────────────────────────┤
│  bar     │                           │
│          │       Main Content        │
│  Nav     │                           │
│  Items   │                           │
│          │                           │
└──────────┴───────────────────────────┘
Mobile: sidebar becomes hamburger overlay
```

### 3. Split View (50/50 or 40/60)
```
┌──────────────────┬───────────────────┐
│                  │                   │
│   Left Panel     │   Right Panel     │
│   (Image/List)   │   (Content/Form)  │
│                  │                   │
│                  │                   │
└──────────────────┴───────────────────┘
Common use: login pages, master-detail, comparison
Mobile: stacks vertically
```

### 4. Card Grid
```
┌────────┐ ┌────────┐ ┌────────┐
│ [img]  │ │ [img]  │ │ [img]  │
│ Title  │ │ Title  │ │ Title  │
│ Desc   │ │ Desc   │ │ Desc   │
│ [CTA]  │ │ [CTA]  │ │ [CTA]  │
└────────┘ └────────┘ └────────┘
┌────────┐ ┌────────┐ ┌────────┐
│ [img]  │ │ [img]  │ │ [img]  │
│ ...    │ │ ...    │ │ ...    │
└────────┘ └────────┘ └────────┘
CSS: display: grid;
     grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
     gap: 24px;
```

### 5. Hero + Content Sections
```
┌──────────────────────────────────────┐
│           Navigation Bar             │
├──────────────────────────────────────┤
│                                      │
│         HERO SECTION                 │
│    Large Headline Text               │
│    Supporting description            │
│         [Primary CTA]               │
│                                      │
├──────────────────────────────────────┤
│  Feature 1  │  Feature 2  │  Feat 3 │
├──────────────────────────────────────┤
│  Content Section (alternating)       │
│  Image Left / Text Right            │
├──────────────────────────────────────┤
│  Text Left / Image Right            │
├──────────────────────────────────────┤
│           Footer                     │
└──────────────────────────────────────┘
```

### 6. Sticky Header + Scrollable Content
```
┌──────────────────────────────────────┐
│  Header (position: sticky; top: 0)   │
├──────────────────────────────────────┤
│                                      │
│  Scrollable Content                  │
│  ┌──────────────────────────────┐    │
│  │  Item 1                      │    │
│  ├──────────────────────────────┤    │
│  │  Item 2                      │    │
│  ├──────────────────────────────┤    │
│  │  Item 3                      │    │
│  └──────────────────────────────┘    │
│  ... (scrolls)                       │
└──────────────────────────────────────┘
```

### 7. Fixed Sidebar + Scrollable Main
```
┌──────────┬───────────────────────────┐
│ Sidebar  │                           │
│ (fixed)  │   Main Content            │
│          │   (scrollable)            │
│  Nav 1   │   ┌──────────────────┐    │
│  Nav 2   │   │ Content Block 1  │    │
│  Nav 3   │   └──────────────────┘    │
│  Nav 4   │   ┌──────────────────┐    │
│          │   │ Content Block 2  │    │
│          │   └──────────────────┘    │
└──────────┴───────────────────────────┘
```

### 8. Dashboard Grid
```
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ KPI  │ │ KPI  │ │ KPI  │ │ KPI  │
│ $42K │ │ 1.2K │ │ 89%  │ │ ▲12% │
└──────┘ └──────┘ └──────┘ └──────┘
┌──────────────────┐ ┌──────────────┐
│                  │ │              │
│   Line Chart     │ │  Pie Chart   │
│                  │ │              │
└──────────────────┘ └──────────────┘
┌──────────────────────────────────────┐
│  Data Table                          │
│  Name │ Status │ Amount │ Date │ ⋯  │
│  ─────┼────────┼────────┼──────┼─── │
│  ...  │  ...   │  ...   │ ...  │    │
└──────────────────────────────────────┘
```

### 9. Wizard / Stepper
```
   Step 1        Step 2        Step 3        Step 4
   (●)───────────(●)───────────(○)───────────(○)
  Account       Profile      Preferences    Review

┌──────────────────────────────────────┐
│                                      │
│  Current Step Content                │
│  Form fields for this step           │
│                                      │
│          [Back]    [Continue]         │
└──────────────────────────────────────┘
```

### 10. Tabs Layout
```
┌────────┬──────────┬──────────┬───────┐
│Overview│ Activity │ Settings │ Logs  │
├────────┴──────────┴──────────┴───────┤
│                                      │
│  Tab Content Area                    │
│  (changes based on selected tab)     │
│                                      │
└──────────────────────────────────────┘
Mobile: tabs become scrollable or dropdown
```

### 11. Masonry Grid
```
┌────────┐ ┌────────┐ ┌────────┐
│        │ │  Tall  │ │        │
│ Short  │ │  Card  │ │ Medium │
│        │ │        │ │        │
└────────┘ │        │ │        │
┌────────┐ └────────┘ └────────┘
│  Tall  │ ┌────────┐ ┌────────┐
│  Card  │ │        │ │  Tall  │
│        │ │ Short  │ │        │
│        │ │        │ │        │
│        │ └────────┘ │        │
└────────┘            └────────┘
CSS: columns: 3; or CSS Grid with masonry (experimental)
```

### 12. Full-Bleed Hero
```
┌──────────────────────────────────────┐
│  [Nav overlaid on hero image]        │
│                                      │
│      FULL WIDTH BACKGROUND           │
│      IMAGE OR VIDEO                  │
│                                      │
│      Title on overlay                │
│      [CTA Button]                    │
│                                      │
├──────────────────────────────────────┤
│  ┌──────────────────────────────┐    │
│  │  Contained content below     │    │
│  │  max-width: 1140px           │    │
│  └──────────────────────────────┘    │
└──────────────────────────────────────┘
```

### 13. Z-Pattern (Marketing/Landing)
```
┌──────────────────────────────────────┐
│  [Logo]──────────────────────[CTA]   │  ← Eye moves L→R
│       \                      /       │
│        \                    /        │  ← Eye moves R→L (diagonal)
│         \                  /         │
│  [Feature Image]────[Feature Text]   │  ← Eye moves L→R
│                                      │
│  [Testimonial]──────────────[CTA2]   │  ← Eye moves L→R
└──────────────────────────────────────┘
Best for: landing pages, simple marketing sites
```

### 14. F-Pattern (Content/Articles)
```
┌──────────────────────────────────────┐
│  ████████████████████████████████    │  ← Full scan (headline)
│  ████████████████████                │  ← Partial scan (subheading)
│  █████████                           │  ← Short scan
│  ████████████████                    │  ← Short scan
│  ████████                            │  ← Short scan
│  █████                               │  ← Diminishing attention
└──────────────────────────────────────┘
Best for: text-heavy pages, articles, search results
Key: Front-load important info at top-left
```

### 15. Modal/Dialog Overlay
```
┌──────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░┌──────────────────────────┐░░░░░│
│░░░░│  Modal Title          [X]│░░░░░│
│░░░░├──────────────────────────┤░░░░░│
│░░░░│                          │░░░░░│
│░░░░│  Modal Content           │░░░░░│
│░░░░│                          │░░░░░│
│░░░░├──────────────────────────┤░░░░░│
│░░░░│       [Cancel] [Confirm] │░░░░░│
│░░░░└──────────────────────────┘░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
└──────────────────────────────────────┘
░ = backdrop overlay (semi-transparent)
```

### 16. Form Layout (Single Column)
```
┌──────────────────────────────────────┐
│  Form Title                          │
│  Description text                    │
│                                      │
│  Label *                             │
│  ┌──────────────────────────────┐    │
│  │  Input field                 │    │
│  └──────────────────────────────┘    │
│  Helper text                         │
│                                      │
│  Label                               │
│  ┌──────────────────────────────┐    │
│  │  Input field                 │    │
│  └──────────────────────────────┘    │
│                                      │
│  Label *                             │
│  ┌──────────────────────────────┐    │
│  │                              │    │
│  │  Textarea                    │    │
│  │                              │    │
│  └──────────────────────────────┘    │
│                                      │
│          [Cancel]  [Submit]          │
└──────────────────────────────────────┘
Max width: 600px centered (col-lg-6 offset-lg-3)
```

### 17. Form Layout (Multi-Column)
```
┌──────────────────────────────────────┐
│  Form Title                          │
│                                      │
│  First Name *        Last Name *     │
│  ┌──────────────┐   ┌──────────────┐│
│  │              │   │              ││
│  └──────────────┘   └──────────────┘│
│                                      │
│  Email *             Phone           │
│  ┌──────────────┐   ┌──────────────┐│
│  │              │   │              ││
│  └──────────────┘   └──────────────┘│
│                                      │
│  Address                             │
│  ┌──────────────────────────────────┐│
│  │                                  ││
│  └──────────────────────────────────┘│
│                                      │
│  City       State      Zip          │
│  ┌────────┐ ┌────────┐ ┌──────────┐│
│  │        │ │   [v]  │ │          ││
│  └────────┘ └────────┘ └──────────┘│
│                                      │
│           [Cancel]  [Submit]         │
└──────────────────────────────────────┘
Mobile: all fields stack to single column
```

### 18. Pricing Table
```
┌───────────┐ ┌───────────┐ ┌───────────┐
│   Basic   │ │ ★ Pro ★   │ │Enterprise │
│           │ │ POPULAR   │ │           │
│  $9/mo    │ │  $29/mo   │ │  $99/mo   │
│           │ │           │ │           │
│  ✓ Feat 1 │ │  ✓ Feat 1 │ │  ✓ Feat 1 │
│  ✓ Feat 2 │ │  ✓ Feat 2 │ │  ✓ Feat 2 │
│  ✗ Feat 3 │ │  ✓ Feat 3 │ │  ✓ Feat 3 │
│  ✗ Feat 4 │ │  ✗ Feat 4 │ │  ✓ Feat 4 │
│           │ │           │ │           │
│ [Choose]  │ │ [Choose]  │ │ [Contact] │
└───────────┘ └───────────┘ └───────────┘
Middle card: slightly larger, highlighted border/shadow
```

### 19. Timeline / Activity Feed
```
  ● ── 2:30 PM ── John updated the status to "In Progress"
  │
  ● ── 1:15 PM ── Sarah added a comment
  │               "Looking great, just a few tweaks..."
  │
  ● ── 11:00 AM ── File uploaded: design-v2.fig
  │
  ● ── 9:30 AM ── Task created by Admin
```

### 20. Kanban Board
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  To Do   │ │In Progress│ │  Review  │ │   Done   │
│  (5)     │ │   (3)     │ │   (2)    │ │   (8)    │
├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤
│┌────────┐│ │┌────────┐│ │┌────────┐│ │┌────────┐│
││ Card 1 ││ ││ Card 3 ││ ││ Card 6 ││ ││ Card 8 ││
│└────────┘│ │└────────┘│ │└────────┘│ │└────────┘│
│┌────────┐│ │┌────────┐│ │┌────────┐│ │┌────────┐│
││ Card 2 ││ ││ Card 4 ││ ││ Card 7 ││ ││ Card 9 ││
│└────────┘│ │└────────┘│ │└────────┘│ │└────────┘│
│          │ │┌────────┐│ │          │ │          │
│ [+ Add]  │ ││ Card 5 ││ │          │ │          │
│          │ │└────────┘│ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
Cards: draggable between columns
Mobile: horizontal scroll or stacked with swipe
```

### 21. Settings Page (Grouped)
```
┌──────────────────────────────────────┐
│  Settings                            │
├──────────────────────────────────────┤
│  ACCOUNT                             │
│  ┌──────────────────────────────────┐│
│  │ Display Name      [Jordan      ] ││
│  ├──────────────────────────────────┤│
│  │ Email             jordan@ex.com  ││
│  ├──────────────────────────────────┤│
│  │ Language           [English ▾]  ││
│  └──────────────────────────────────┘│
│                                      │
│  NOTIFICATIONS                       │
│  ┌──────────────────────────────────┐│
│  │ Email alerts          [====]ON  ││
│  ├──────────────────────────────────┤│
│  │ Push notifications    [    ]OFF ││
│  ├──────────────────────────────────┤│
│  │ Weekly digest         [====]ON  ││
│  └──────────────────────────────────┘│
│                                      │
│  DANGER ZONE                         │
│  ┌──────────────────────────────────┐│
│  │ Delete account     [Delete...]  ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```
