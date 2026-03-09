# Paper - UI/UX Design Specialist Plugin for Claude Code

> **Version:** 1.0.0 | **Author:** TaqaTechno | **License:** MIT

Paper transforms Claude into a **professional UI/UX designer** capable of designing screens, wireframes, and full design systems for any platform — web, mobile (iOS/Android), or desktop applications.

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

## Prerequisites

<!--
  Paper itself has NO external dependencies.
  It works standalone for design theory, wireframing, design reviews, and code generation.

  The Figma MCP plugin is OPTIONAL — it adds the ability to:
    - Read designs directly from Figma files
    - Push designs to Figma
    - Sync component mappings (Code Connect)
    - Generate FigJam diagrams

  Without Figma MCP, Paper still works for:
    - All design theory and principles
    - ASCII wireframes and HTML prototypes
    - Design system generation from code analysis
    - Design reviews of existing HTML/CSS/SCSS
    - Color palette and typography generation
-->

- **Required:** Claude Code CLI (any version)
- **Optional:** Figma MCP plugin for Figma integration
  ```bash
  # Install Figma MCP plugin (optional, for Figma integration)
  claude plugin install figma@claude-plugins-official
  ```

---

## Installation

<!--
  INSTALLATION OVERVIEW:
  =====================
  Paper is a local plugin. Claude Code discovers plugins by finding
  .claude-plugin/plugin.json files in configured plugin directories.

  There are TWO ways to install:

  Option A: Copy to a project directory (project-specific)
  Option B: Copy to global plugins directory (available everywhere)

  For most users, Option A is recommended — it keeps the plugin
  scoped to the project where you need design capabilities.
-->

### Option A: Project-Level Installation (Recommended)

<!--
  This installs Paper for a specific project only.
  The plugin will be available when Claude Code is opened in this project.
  Other projects won't see it unless you copy it there too.
-->

```bash
# Step 1: Navigate to your project root
cd /path/to/your/project

# Step 2: Create a plugins directory if it doesn't exist
#          (this is where your project's local plugins live)
mkdir -p .claude/plugins

# Step 3: Copy the paper plugin directory
#          The entire 'paper/' folder must be copied, preserving the structure:
#            paper/
#            ├── .claude-plugin/plugin.json   ← Claude Code finds this to register
#            ├── skills/paper/SKILL.md        ← Core design knowledge
#            ├── commands/                    ← Slash commands (/design, /wireframe, etc.)
#            ├── agents/                      ← Subagents (design-reviewer, wireframe-builder)
#            ├── hooks/hooks.json             ← Auto-suggestions on HTML/CSS edits
#            └── reference/                   ← Deep reference docs (loaded on-demand)
cp -r /path/to/paper .claude/plugins/paper
```

### Option B: Global Installation

<!--
  This installs Paper globally — available in ALL projects.
  Use this if you want design capabilities everywhere.
  Global plugins live in ~/.claude/plugins/
-->

```bash
# Step 1: Copy to global plugins directory
cp -r /path/to/paper ~/.claude/plugins/paper

# Step 2: Verify the plugin.json is at the right path
#          Claude Code looks for: ~/.claude/plugins/paper/.claude-plugin/plugin.json
ls ~/.claude/plugins/paper/.claude-plugin/plugin.json
```

### Option C: Install from Current Location

<!--
  If the plugin is already at C:\TQ-WorkSpace\odoo\tmp\plugins\paper\,
  you can register it directly with Claude Code.
-->

```bash
# Register the plugin from its current location
claude plugin add /c/TQ-WorkSpace/odoo/tmp/plugins/paper
```

### Verify Installation

<!--
  After installation, verify that Claude Code has discovered the plugin.
  Start a new Claude Code session and check:
-->

```bash
# List installed plugins (should show 'paper')
claude plugin list

# Or in a Claude Code session, try a command:
/design help
```

---

## Available Commands

<!--
  COMMANDS are invoked with a slash (/) prefix in Claude Code.
  They are defined in the commands/ directory as markdown files.
  Each command has a specific purpose and accepts arguments.
-->

### `/design <what> [for <platform>]`

**Main entry point** — Design any screen, page, or component.

```
# Examples:
/design login page for web
/design admin dashboard with KPI cards
/design user profile screen for ios
/design settings page for android
/design checkout flow for mobile
/design product card component
```

**What it produces:**
1. Visual direction (style, color palette, typography)
2. ASCII wireframe
3. Component inventory with states
4. Production-ready code (Bootstrap 5 for web by default)
5. Responsive behavior notes
6. Accessibility notes

---

### `/design-review [file-path]`

**Review existing UI** for design quality, accessibility, and responsiveness.

```
# Examples:
/design-review src/templates/homepage.html
/design-review views/login.xml
/design-review                              # reviews current file
```

**What it produces:**
- Score (X/10) with severity breakdown
- Critical, Major, Minor issues with line numbers and fixes
- Positive observations (what's working well)
- Optional: comparison against Figma source (if URL provided)

---

### `/design-system [generate|analyze]`

**Create or extract** a design system for your project.

```
# Generate a new design system:
/design-system generate

# Analyze existing CSS/SCSS for implicit design patterns:
/design-system analyze
```

**Generate mode produces:**
- Complete color palette (with contrast ratios)
- Typography scale (fonts, sizes, weights)
- Spacing tokens (4px/8px grid)
- Component inventory
- CSS custom properties / SCSS variables
- For Odoo: `$o-website-values-palettes` structure

**Analyze mode produces:**
- Inventory of all colors, fonts, spacing values found
- Inconsistency report (duplicate colors, irregular spacing)
- Recommended design token consolidation

---

### `/figma-sync [pull|push|status|suggest|diagram]`

**Sync between Figma and code** using Figma MCP tools.

<!--
  IMPORTANT: This command requires the Figma MCP plugin to be installed.
  If Figma MCP is not available, the command will inform you how to install it.

  The Figma MCP plugin provides 13 tools that this command orchestrates:
    - get_design_context: read design data from Figma
    - get_screenshot: capture visual reference
    - get_metadata: get node structure
    - get_variable_defs: extract design tokens
    - get_code_connect_map: check existing mappings
    - get_code_connect_suggestions: AI-suggested mappings
    - send_code_connect_mappings: create mappings
    - add_code_connect_map: add single mapping
    - create_design_system_rules: generate rules
    - generate_figma_design: create designs in Figma
    - get_figjam: read FigJam boards
    - generate_diagram: create FigJam diagrams
    - whoami: check authentication
-->

```
# Read a Figma design and generate code:
/figma-sync pull https://figma.com/design/abc123/MyFile?node-id=42-15

# Push a design description to Figma:
/figma-sync push "hero section with gradient background and CTA"

# Check which components are mapped:
/figma-sync status https://figma.com/design/abc123/MyFile?node-id=1-1

# Get AI-suggested component mappings:
/figma-sync suggest https://figma.com/design/abc123/MyFile?node-id=1-1

# Generate a FigJam diagram:
/figma-sync diagram user registration flow
```

---

### `/wireframe <description> [--platform=web|ios|android|desktop]`

**Quick wireframe generation** — ASCII art + optional HTML prototype.

```
# Examples:
/wireframe e-commerce product listing page
/wireframe onboarding flow with 4 steps --platform=ios
/wireframe CRM dashboard with pipeline kanban
/wireframe multi-step checkout form
/wireframe settings page with grouped sections --platform=android
```

**What it produces:**
1. ASCII wireframe with box-drawing characters
2. Component inventory
3. Responsive behavior notes
4. Optional: HTML/CSS prototype file

---

## Agents

<!--
  AGENTS are autonomous subprocesses that handle complex tasks.
  They are defined in the agents/ directory as markdown files.
  Claude automatically triggers them based on the task context,
  or you can explicitly request them.
-->

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

<!--
  HOOKS are automatic checks that run after Claude edits files.
  They are defined in hooks/hooks.json.

  Paper includes 2 PostToolUse hooks that trigger when you
  edit HTML/XML or CSS/SCSS files. They display a quick design
  checklist reminder to help maintain quality.

  These are NON-BLOCKING — they show a suggestion, they don't
  prevent the edit from happening.
-->

| Hook | Triggers On | What It Does |
|------|------------|--------------|
| HTML/XML Design Check | Write/Edit of `.html`, `.xml` | Reminds: semantic tags, alt text, ARIA, heading hierarchy, touch targets |
| CSS/SCSS Design Check | Write/Edit of `.css`, `.scss`, `.sass` | Reminds: contrast ratios, relative units, max-width, spacing grid, focus styles |

---

## Reference Documentation

<!--
  Reference docs live in the reference/ directory.
  They are NOT loaded into the system prompt automatically.
  They are loaded ON-DEMAND when Claude needs deep reference
  material for a specific topic.

  This keeps the main skill lightweight while providing
  deep expertise when needed.
-->

| Document | Content |
|----------|---------|
| [color-theory.md](reference/color-theory.md) | Color wheel, palette algorithms, HSL shade generation, semantic colors, dark mode rules, Odoo o-color mapping |
| [typography-scale.md](reference/typography-scale.md) | 7 modular scales with calculations, 12 font pairings, line height guide, fluid typography, vertical rhythm |
| [layout-patterns.md](reference/layout-patterns.md) | 21 layout patterns with ASCII diagrams (dashboard, sidebar, hero, form, kanban, wizard, tabs, settings, etc.) |
| [platform-guidelines.md](reference/platform-guidelines.md) | Condensed iOS HIG, Material Design 3, Windows Fluent Design, and Web conventions |
| [accessibility-checklist.md](reference/accessibility-checklist.md) | WCAG 2.1 AA organized by POUR principles, quick testing methods, common ARIA patterns |

---

## Skill: Core Design Knowledge

<!--
  The main SKILL.md (skills/paper/SKILL.md) is the "brain" of Paper.
  It gets loaded into the system prompt when design tasks are detected.

  It contains 5 sections:
  1. Design System Fundamentals — color, typography, spacing, layout, atomic design
  2. Figma MCP Workflow — how to use all 13 Figma tools for design-to-code
  3. Multi-Platform Screen Design — web, iOS, Android, desktop patterns
  4. Odoo/Bootstrap Special Patterns — theme architecture, QWeb, publicWidget
  5. Design Review Checklist — 6-dimension quality review with severity ratings

  The skill is designed to make Claude think like a designer:
  - Visual hierarchy and spatial relationships
  - Color contrast and accessibility
  - Platform-appropriate patterns
  - Responsive behavior
  - Component reuse and consistency
-->

---

## Integration with Odoo

Paper has built-in knowledge of **Odoo website theme development**:

- **Bootstrap 5.1.3** utilities and grid system
- **Mirror model architecture** (`theme.ir.ui.view` → `ir.ui.view`)
- **Color system**: `o-color-1` through `o-color-5` palette structure
- **Asset bundles**: `web.assets_frontend`, `web._assets_primary_variables`
- **QWeb templates**: `t-call="website.layout"`, `oe_structure` sections
- **publicWidget**: JavaScript component pattern with `editableMode` handling

When working on Odoo projects, Paper automatically adapts:
- Uses Bootstrap 5 classes and utilities
- Generates Odoo-compatible QWeb XML templates
- Produces `$o-website-values-palettes` SCSS for theme colors
- Follows Odoo's asset bundle conventions

---

## Project Structure

```
paper/
├── .claude-plugin/
│   └── plugin.json                    # Plugin manifest (name, version, author)
├── skills/
│   └── paper/
│       └── SKILL.md                   # Core design knowledge (600+ lines)
├── agents/
│   ├── design-reviewer.md             # UI quality audit agent
│   └── wireframe-builder.md           # Wireframe + prototype agent
├── commands/
│   ├── design.md                      # /design — design screens/pages/components
│   ├── design-review.md               # /design-review — audit existing UI
│   ├── design-system.md               # /design-system — generate/analyze tokens
│   ├── figma-sync.md                  # /figma-sync — Figma MCP orchestration
│   └── wireframe.md                   # /wireframe — quick wireframes
├── hooks/
│   └── hooks.json                     # PostToolUse design checks on HTML/CSS
├── reference/
│   ├── color-theory.md                # Color palettes, contrast, dark mode
│   ├── typography-scale.md            # Type scales, font pairing, vertical rhythm
│   ├── layout-patterns.md             # 21 layout patterns with ASCII diagrams
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
