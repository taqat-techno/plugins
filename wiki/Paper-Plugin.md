# Paper Plugin

**Package:** `paper` · **Version:** `3.0.0` · **Category:** design · **License:** MIT · **Source:** [`paper-plugin/`](../../paper-plugin/)

## Purpose

Transform Claude into a **professional UI/UX designer**. Paper handles screen design, wireframing, design reviews, design systems, and Figma synchronization for web, iOS, Android, and desktop platforms. Enforces WCAG 2.1 AA accessibility.

## What it does

| Capability | Skill | Output |
|---|---|---|
| **Screen design** | `design` | Wireframe + HTML/CSS prototype for any platform |
| **Design system generation** | `design` | Complete token-set (colors, typography, spacing, components) |
| **Design review** | `design-reviewer` agent | 6-dimension UI audit with WCAG 2.1 AA compliance report |
| **Wireframing** | `wireframe-builder` agent | Rapid ASCII wireframes + HTML/CSS prototypes |
| **Figma sync** | `figma-workflow` skill | Design-to-code and code-to-design via external Figma MCP |

## How it works

v3.0 split the previous monolithic skill into **two focused skills** (`design` + `figma-workflow`), stripped Odoo-specific content, tightened hook filters to specific file types, and slimmed the command to a pure dispatcher.

- **One command** (`/paper`) dispatches to skills and agents based on the user's phrasing.
- **Two skills:**
  - `skills/design/` — screen design, wireframes, design systems, accessibility audits. Does not require Figma.
  - `skills/figma-workflow/` — read-from and write-to Figma via an external Figma MCP. Requires the user to install the Figma MCP separately (not shipped by paper-plugin).
- **Two agents:**
  - `design-reviewer` — systematic 6-dimension UI review.
  - `wireframe-builder` — ASCII wireframes with HTML/CSS companion code.
- **Hooks:** filter by file type (only fire on design-relevant files), advisory-only.
- **Reference library:** `reference/` holds color-theory primers, typography scales, WCAG checklists, spacing grids.

## Command

| Command | Purpose |
|---|---|
| `/paper` | Status + Figma connection check + dispatcher for all design workflows |

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

## Configuration

- **Figma MCP** (external, user-installed) — required only for `/figma-sync` and code-to-design workflows.
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
```

## Known limitations

- **Figma MCP is external.** Install it separately; paper-plugin does not bundle Figma tooling.
- **WCAG audit is heuristic.** Auto-checks catch common issues; final compliance requires manual verification with real screen readers + live user testing.
- **No animation tooling.** Paper is for static design. For animated UI/video narration, use [[Remotion Plugin|Remotion-Plugin]].
- **Platform-specific components are template-based.** Generated iOS/Android code is a starting scaffold, not final production code.

## Related plugins and integrations

- **pandoc** — export design documents (Markdown spec + design system tokens) to PDF / Word.
- **remotion** — turn design walkthroughs into narrated video tours.

## See also

- Source: [`paper-plugin/README.md`](../../paper-plugin/README.md) — full feature list + platform notes
- v3.0 migration note in [`paper-plugin/README.md`](../../paper-plugin/README.md) (top of file)
- `paper-plugin/reference/` — color theory, typography, accessibility checklists
