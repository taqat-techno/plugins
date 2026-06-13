# Ui Ux Mechanics Plugin

**Package:** `ui-ux-mechanics` · **Version:** `3.1.0` · **Category:** design · **License:** MIT · **Source:** [`ui-ux-mechanics-plugin/`](../../ui-ux-mechanics-plugin/)

> **Renamed in this cycle.** This plugin was previously published as `paper` (directory `paper-plugin/`, command `/paper`). It is now `ui-ux-mechanics` (directory `ui-ux-mechanics-plugin/`, command `/ui-ux-mechanics`). Update any saved references.

## Purpose

Transform Claude into a **professional UI/UX designer** with **safe Figma MCP execution mechanics**. The plugin handles screen design, wireframing, design reviews, design systems, and Figma synchronization for web, iOS, Android, and desktop platforms. Enforces WCAG 2.1 AA accessibility. The Figma write path is hardened against the common failure modes of automated design edits.

## What it does

| Capability | Skill | Output |
|---|---|---|
| **Screen design** | `design` | Wireframe + HTML/CSS prototype for any platform |
| **Design system generation** | `design` | Complete token-set (colors, typography, spacing, components) |
| **Design review** | `design-reviewer` agent | 6-dimension UI audit with WCAG 2.1 AA compliance report |
| **Wireframing** | `wireframe-builder` agent | Rapid ASCII wireframes + HTML/CSS prototypes |
| **Figma sync** | `figma-workflow` skill | Design-to-code and code-to-design via external Figma MCP |
| **Safe Figma MCP writes** | `figma-mcp-mechanics` skill | Write-access probing, metadata-lossiness handling, auto-layout / variant mechanics, prototype-link-safe edits |

## How it works

The plugin split the previous monolithic skill into **focused skills** (`design` + `figma-workflow` + `figma-mcp-mechanics`), stripped Odoo-specific content, tightened hook filters to specific file types, and slimmed the command to a pure dispatcher.

- **One command** (`/ui-ux-mechanics`) dispatches to skills and agents based on the user's phrasing.
- **Skills:**
  - `skills/design/` — screen design, wireframes, design systems, accessibility audits. Does not require Figma.
  - `skills/figma-workflow/` — read-from and write-to Figma via an external Figma MCP. Requires the user to install the Figma MCP separately (not shipped by ui-ux-mechanics-plugin).
  - `figma-mcp-mechanics` — the safe-write layer for Figma MCP edits: probes write access before mutating, handles metadata lossiness on round-trips, applies auto-layout and component-variant mechanics correctly, and keeps prototype links intact across edits.
- **Two agents:**
  - `design-reviewer` — systematic 6-dimension UI review.
  - `wireframe-builder` — ASCII wireframes with HTML/CSS companion code.
- **Hooks:** filter by file type (only fire on design-relevant files), advisory-only.
- **Reference library:** `reference/` holds color-theory primers, typography scales, WCAG checklists, spacing grids.

## Command

| Command | Purpose |
|---|---|
| `/ui-ux-mechanics` | Status + Figma connection check + dispatcher for all design and Figma-mechanics workflows |

The command is intentionally a single entry point; behavior lives in skills. Users don't memorize design-specific flags — they describe what they need.

## Agents

| Agent | Role |
|---|---|
| `design-reviewer` | Runs a 6-dimension review (layout, typography, color, accessibility, consistency, responsive) against WCAG 2.1 AA |
| `wireframe-builder` | Builds ASCII wireframes for rapid iteration + HTML/CSS prototypes for higher fidelity |

## Inputs and outputs

**Inputs:**
- Natural-language description of the screen or component.
- Optional platform hint (`iOS`, `Android`, `web`, `desktop`).
- Optional existing design to review (HTML/CSS, screenshot, Figma link).

**Outputs:**
- ASCII wireframe (for rapid review).
- HTML/CSS code for the design.
- Design system document (color/typography/spacing tokens + component library).
- Accessibility audit report with WCAG 2.1 AA compliance scoring.
- Figma sync diff (when `figma-workflow` skill is active).
- Safe Figma write results — auto-layout/variant edits applied with write-access checked first and prototype links preserved (`figma-mcp-mechanics` skill).

## Configuration

- **Figma MCP** (external, user-installed) — required only for Figma pull/push and code-to-design workflows.
- **Design system defaults** live in `reference/`. Users can override by providing their own tokens.
- **Hook filters** in `hooks/hooks.json` — restrict hook firing to design files (`.html`, `.css`, `.tsx`, `.figma`, etc.) rather than every file.

## Dependencies

- Node.js for any HTML/CSS generation that uses modern tooling.
- Figma MCP (installed separately by the user) for Figma-integrated workflows.
- No lock-in — the plugin works without Figma if you only need design + wireframe + review.

## Usage examples

```
"Design a login page for iOS"
→ design skill generates wireframe + HTML/CSS with iOS-appropriate typography and spacing

"Wireframe an admin dashboard"
→ wireframe-builder agent produces ASCII wireframe first, HTML prototype on request

"Review this template for accessibility"
→ design-reviewer agent runs the 6-dimension review; flags WCAG 2.1 AA issues

"Generate a design system for our brand"
→ design skill produces color palette, typography scale, spacing grid, component tokens

"Sync this design to Figma"
→ figma-workflow skill (requires Figma MCP installed)

"Push these component variants into Figma safely"
→ figma-mcp-mechanics skill probes write access, applies variant/auto-layout edits, preserves prototype links
```

## Known limitations

- **Figma MCP is external.** Install it separately; ui-ux-mechanics-plugin does not bundle Figma tooling.
- **WCAG audit is heuristic.** Auto-checks catch common issues; final compliance requires manual verification with real screen readers + live user testing.
- **No animation tooling.** The plugin is for static design. For animated UI/video narration, use [[Remotion Plugin|Remotion-Plugin]].
- **Platform-specific components are template-based.** Generated iOS/Android code is a starting scaffold, not final production code.
- **Figma write mechanics depend on the MCP surface.** `figma-mcp-mechanics` makes writes safer (access probing, lossiness handling, prototype-link preservation) but cannot recover capabilities the external Figma MCP does not expose.

## Related plugins and integrations

- **pandoc** — export design documents (Markdown spec + design system tokens) to PDF / Word.
- **remotion** — turn design walkthroughs into narrated video tours.

## See also

- Source: [`ui-ux-mechanics-plugin/README.md`](../../ui-ux-mechanics-plugin/README.md) — full feature list + platform notes
- Rename + version note in [`ui-ux-mechanics-plugin/README.md`](../../ui-ux-mechanics-plugin/README.md) (top of file)
- `ui-ux-mechanics-plugin/reference/` — color theory, typography, accessibility checklists
