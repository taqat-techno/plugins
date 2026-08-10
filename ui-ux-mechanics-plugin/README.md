# ui-ux-mechanics - UI/UX Design Specialist Plugin for Claude Code

> **Version:** 3.1.0 | **Author:** TaqaTechno | **License:** MIT

ui-ux-mechanics transforms Claude into a **professional UI/UX designer** capable of designing screens, wireframes, and full design systems for any platform — web, mobile (iOS/Android), or desktop applications.

> **Migration Note (v3.0):** In v3.0, the monolithic skill was split into 2 focused skills (`design` + `figma-workflow`), all project-specific content was removed, and the command was slimmed to a pure dispatcher. Reference docs are now explicitly connected to skills and agents. (The file-type-scoped hooks were subsequently emptied — the plugin now ships none; see [Hooks](#hooks).)

---

## What ui-ux-mechanics Does

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
1. /ui-ux-mechanics                 (check status + Figma connection)
2. Just describe what you need:
   - "Design a login page for iOS"
   - "Wireframe an admin dashboard"
   - "Review this template for accessibility"
3. For Figma sync:
   /ui-ux-mechanics figma pull <figma-url>
4. For design systems:
   /ui-ux-mechanics system generate
```

---

## Prerequisites

- **Required:** Claude Code CLI
- **Optional:** Figma MCP plugin for Figma integration
  ```bash
  claude plugin install figma@claude-plugins-official
  ```

---

## Installation

### Option A: Project-Level (Recommended)

```bash
cd /path/to/your/project
mkdir -p .claude/plugins
cp -r /path/to/ui-ux-mechanics-plugin .claude/plugins/ui-ux-mechanics-plugin
```

### Option B: Global

```bash
cp -r /path/to/ui-ux-mechanics-plugin ~/.claude/plugins/ui-ux-mechanics-plugin
```

### Option C: Register from Current Location

```bash
claude plugin add /path/to/ui-ux-mechanics-plugin
```

### Verify

```bash
claude plugin list    # should show 'ui-ux-mechanics'
/ui-ux-mechanics      # in a session, shows status
```

---

## Skills

### `design` (Core)

**Activates when:** You describe a design task in natural language — "design a login page", "wireframe the checkout flow", "review this for accessibility", "create a color palette".

Covers: color theory, typography scales, spacing systems, layout fundamentals, multi-platform design (web/iOS/Android/desktop), design review checklists, and anti-patterns.

### `figma-workflow`

**Activates when:** You mention Figma, provide a Figma URL, or ask to sync designs between code and Figma.

Covers: Figma MCP tools reference, design-to-code workflow, code-to-design workflow, design system sync, asset handling rules. Requires the Figma MCP plugin.

### `figma-mcp-mechanics`

**Activates when:** You are about to *write* to a Figma file via MCP — creating, editing, repositioning, relabeling, or variant-swapping nodes — or when `get_metadata` reports a file looks empty, an auto-layout collapses after a resize, a font-not-loaded error rolls back a write, a cloned RTL frame renders tofu, `setReactionsAsync` rejects an action, a design "keeps looking corrupted", prototype links may be at risk, or you need the Figma REST API.

Covers the fifteen mechanics: the net-zero write-access probe, `get_metadata` lossiness handling, component/instance discovery plus "systemic"-finding triage, geometry-and-locale QA, exhaustive enumeration, auto-layout child-order/resize/variant-swap mechanics, atomic-write rollback, prototype-link-safe repositioning, the X-Figma-Token REST path, loading every font before a text write, explicit target fonts on blank/cloned RTL nodes, cloning (never hand-building) reactions for `setReactionsAsync` plus BFS reachability as the wiring proof, page-load timing before trusting `page.children.length`, relabeling by node-id / full title phrase with an old→new echo, and per-finding before/after capture that distinguishes a broken export from a corrupt source. Tool-mechanics companion to `figma-workflow`. Requires the Figma MCP plugin.

---

## Command: `/ui-ux-mechanics`

The single unified command for Figma and design system operations.

| Sub-command | Description |
|-------------|-------------|
| *(none)* | Show status + Figma connection + help |
| `figma pull <url>` | Read a Figma design and generate code |
| `figma push <description>` | Push a design description to Figma |
| `figma status <url>` | Check which components are mapped |
| `figma suggest <url>` | Get AI-suggested component mappings |
| `figma diagram <description>` | Generate a FigJam diagram |
| `system generate` | Generate a complete design system |
| `system analyze` | Analyze existing CSS/SCSS for design patterns |

---

## Agents

### design-reviewer

**Triggered when:** You ask to review, audit, or check existing UI code.

Performs a systematic 6-dimension review: Visual Hierarchy, Color & Contrast, Typography, Spacing & Layout, Accessibility, Responsive Behavior. Produces a scored report with severity ratings.

### wireframe-builder

**Triggered when:** You ask to wireframe, mockup, sketch, or prototype a screen.

Creates ASCII wireframes, component inventories, responsive behavior specs, and optional HTML/CSS prototypes.

---

## Hooks

**This plugin ships no active hooks.** `hooks/hooks.json` is intentionally empty (`{"hooks":{}}`), so editing a UI file triggers **no** automatic design reminder. Design guidance is delivered through the skills and agents above — invoke the `design` skill or the `design-reviewer` agent when you want a review.

The empty `hooks/hooks.json` is a placeholder you can populate yourself (see [Customization](#add-a-design-check-hook) below); nothing is wired by default.

---

## Reference Documentation

| Document | Content |
|----------|---------|
| [color-theory.md](reference/color-theory.md) | Color wheel, palette algorithms, HSL shade generation, contrast ratios, dark mode rules |
| [typography-scale.md](reference/typography-scale.md) | 7 modular scales, 12 font pairings, line height guide, fluid typography, vertical rhythm |
| [layout-patterns.md](reference/layout-patterns.md) | 21 layout patterns with ASCII diagrams and CSS |
| [platform-guidelines.md](reference/platform-guidelines.md) | iOS HIG, Material Design 3, Windows Fluent, Web conventions |
| [accessibility-checklist.md](reference/accessibility-checklist.md) | WCAG 2.1 AA organized by POUR principles, testing methods, ARIA patterns |

Reference docs are used by skills and agents when detailed guidance is needed.

---

## Customization

### Add a design-check hook

`hooks/hooks.json` ships empty (`{"hooks":{}}`) — no hooks run by default. To add a file-type-scoped design check, define your own `PostToolUse` entry in `hooks/hooks.json` matching the file types you care about. Nothing fires unless you add it.

### Add framework-specific knowledge

Create a new skill directory under `skills/` with a `SKILL.md` containing framework-specific patterns. Add its path to the `skills` array in `.claude-plugin/plugin.json`.

Example: to add support for a specific UI framework, create `skills/<framework>-design/SKILL.md` with that framework's patterns and register it in the manifest.

### Extend reference docs

Add new `.md` files to `reference/` and reference them from your skill's SKILL.md.

---

## Project Structure

```
ui-ux-mechanics-plugin/
├── .claude-plugin/
│   └── plugin.json                    # Plugin manifest
├── skills/
│   ├── design/
│   │   └── SKILL.md                   # Core design knowledge
│   ├── figma-workflow/
│   │   └── SKILL.md                   # Figma design-to-code / code-to-design workflow
│   └── figma-mcp-mechanics/
│       └── SKILL.md                   # Figma MCP tool-execution mechanics
├── agents/
│   ├── design-reviewer.md             # UI quality audit agent
│   └── wireframe-builder.md           # Wireframe + prototype agent
├── commands/
│   └── ui-ux-mechanics.md             # /ui-ux-mechanics — unified command
├── hooks/
│   └── hooks.json                     # empty placeholder — no active hooks
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
