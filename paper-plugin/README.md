# Paper - UI/UX Design Specialist Plugin for Claude Code

> **Version:** 2.0.0 | **Author:** TaqaTechno | **License:** MIT

Paper transforms Claude into a **professional UI/UX designer** capable of designing screens, wireframes, and full design systems for any platform — web, mobile (iOS/Android), or desktop applications.

> **Migration Note (v2.0):** In v2.0, 5 commands (`/design`, `/wireframe`, `/design-review`, `/design-system`, `/figma-sync`) were consolidated into 1 unified command: `/paper`. Design, wireframe, and review tasks are now skill-driven — just describe what you need in natural language.

---

## What Paper Does

| Capability | Description |
|-----------|-------------|
| **Screen Design** | Design any screen with wireframe + code for web, iOS, Android, desktop |
| **Design Systems** | Generate complete design systems (colors, typography, spacing, components) |
| **Design Review** | Audit existing UI for quality, accessibility (WCAG 2.1 AA), responsiveness |
| **Wireframing** | Rapid ASCII wireframes + HTML/CSS prototypes |
| **Figma Integration** | Read from / write to Figma via MCP (requires Figma plugin separately) |

---

## Quick Start

```
1. /paper                          (check status + Figma connection)
2. Just describe what you need:
   - "Design a login page for iOS"
   - "Wireframe an admin dashboard"
   - "Review this template for accessibility"
3. For Figma sync:
   /paper figma pull <figma-url>
4. For design systems:
   /paper system generate
```

---

## Prerequisites

- **Required:** Claude Code CLI (any version)
- **Optional:** Figma MCP plugin for Figma integration
  ```bash
  # Install Figma MCP plugin (optional, for Figma integration)
  claude plugin install figma@claude-plugins-official
  ```

---

## Installation

### Option A: Project-Level Installation (Recommended)

```bash
# Navigate to your project root
cd /path/to/your/project

# Create a plugins directory if it doesn't exist
mkdir -p .claude/plugins

# Copy the paper-plugin directory
cp -r /path/to/paper-plugin .claude/plugins/paper-plugin
```

### Option B: Global Installation

```bash
# Copy to global plugins directory
cp -r /path/to/paper-plugin ~/.claude/plugins/paper-plugin

# Verify the plugin.json is at the right path
ls ~/.claude/plugins/paper-plugin/.claude-plugin/plugin.json
```

### Option C: Install from Current Location

```bash
# Register the plugin from its current location
claude plugin add /c/TQ-WorkSpace/odoo/tmp/plugins/paper-plugin
```

### Verify Installation

```bash
# List installed plugins (should show 'paper')
claude plugin list

# Or in a Claude Code session, try the command:
/paper
```

---

## Command: `/paper`

The single unified command for all design operations. Use sub-commands for specific Figma and design system tasks.

### Sub-commands

| Sub-command | Description | Example |
|-------------|-------------|---------|
| `figma pull <url>` | Read a Figma design and generate code | `/paper figma pull https://figma.com/design/abc123/...` |
| `figma push <description>` | Push a design description to Figma | `/paper figma push "hero section with gradient"` |
| `figma status <url>` | Check which components are mapped | `/paper figma status https://figma.com/design/abc123/...` |
| `figma suggest <url>` | Get AI-suggested component mappings | `/paper figma suggest https://figma.com/design/abc123/...` |
| `figma diagram <description>` | Generate a FigJam diagram | `/paper figma diagram user registration flow` |
| `system generate` | Generate a complete design system | `/paper system generate` |
| `system analyze` | Analyze existing CSS/SCSS for design patterns | `/paper system analyze` |

Running `/paper` with no sub-command shows status and Figma connection info.

---

## Natural Language Design

Design, wireframe, and review tasks no longer require specific slash commands. Simply describe what you need and Paper's skill handles it automatically:

```
"Design a login page for iOS with biometric auth"
"Wireframe a multi-step checkout flow"
"Review this homepage template for accessibility issues"
"Create a product card component for Android"
"Audit views/login.xml for WCAG AA compliance"
```

Paper detects your intent and activates the appropriate workflow — producing wireframes, production code, design reviews, or design systems as needed.

---

## Agents

### design-reviewer

**Triggered when:** You ask to review, audit, or check existing UI code.

Performs a systematic 6-dimension review:
1. Visual Hierarchy
2. Color & Contrast (WCAG AA compliance)
3. Typography
4. Spacing & Layout
5. Accessibility
6. Responsive Behavior

Produces a scored report with severity ratings (Critical/Major/Minor/Suggestion).

### wireframe-builder

**Triggered when:** You ask to wireframe, mockup, sketch, or prototype a screen.

Creates:
- ASCII wireframes with proper platform conventions
- Component inventories with states
- Responsive behavior specifications
- Optional HTML/CSS code prototypes
- Multi-screen flow diagrams

---

## Hooks

| Hook | Triggers On | What It Does |
|------|------------|--------------|
| HTML/XML Design Check | Write/Edit of `.html`, `.xml` | Reminds: semantic tags, alt text, ARIA, heading hierarchy, touch targets |
| CSS/SCSS Design Check | Write/Edit of `.css`, `.scss`, `.sass` | Reminds: contrast ratios, relative units, max-width, spacing grid, focus styles |

---

## Reference Documentation

| Document | Content |
|----------|---------|
| [color-theory.md](reference/color-theory.md) | Color wheel, palette algorithms, HSL shade generation, semantic colors, dark mode rules, Odoo o-color mapping |
| [typography-scale.md](reference/typography-scale.md) | 7 modular scales with calculations, 12 font pairings, line height guide, fluid typography, vertical rhythm |
| [layout-patterns.md](reference/layout-patterns.md) | 21 layout patterns with ASCII diagrams (dashboard, sidebar, hero, form, kanban, wizard, tabs, settings, etc.) |
| [platform-guidelines.md](reference/platform-guidelines.md) | Condensed iOS HIG, Material Design 3, Windows Fluent Design, and Web conventions |
| [accessibility-checklist.md](reference/accessibility-checklist.md) | WCAG 2.1 AA organized by POUR principles, quick testing methods, common ARIA patterns |

---

## Integration with Odoo

Paper has built-in knowledge of **Odoo website theme development**:

- **Bootstrap 5.1.3** utilities and grid system
- **Mirror model architecture** (`theme.ir.ui.view` → `ir.ui.view`)
- **Color system**: `o-color-1` through `o-color-5` palette structure
- **Asset bundles**: `web.assets_frontend`, `web._assets_primary_variables`
- **QWeb templates**: `t-call="website.layout"`, `oe_structure` sections
- **publicWidget**: JavaScript component pattern with `editableMode` handling

---

## Project Structure

```
paper-plugin/
├── .claude-plugin/
│   └── plugin.json                    # Plugin manifest (name, version, author)
├── skills/
│   └── paper/
│       └── SKILL.md                   # Core design knowledge (600+ lines)
├── agents/
│   ├── design-reviewer.md             # UI quality audit agent
│   └── wireframe-builder.md           # Wireframe + prototype agent
├── commands/
│   └── paper.md                       # /paper — unified command with sub-commands
├── hooks/
│   └── hooks.json                     # PostToolUse design checks on HTML/CSS
├── reference/
│   ├── color-theory.md                # Color palettes, contrast, dark mode
│   ├── typography-scale.md            # Type scales, font pairing, vertical rhythm
│   ├── layout-patterns.md            # 21 layout patterns with ASCII diagrams
│   ├── platform-guidelines.md         # iOS HIG, Material 3, Fluent, Web
│   └── accessibility-checklist.md     # WCAG 2.1 AA complete checklist
└── README.md                          # This file
```

---

## Credits

Built by **TaqaTechno** (info@taqatechno.com) for the Claude Code ecosystem.

Design knowledge synthesized from:
- Apple Human Interface Guidelines
- Google Material Design 3
- Microsoft Fluent Design System
- W3C WCAG 2.1 Accessibility Guidelines
- Bootstrap 5 Documentation
- Odoo Theme Development Documentation
