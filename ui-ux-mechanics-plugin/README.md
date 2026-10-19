# ui-ux-mechanics

![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What it does

ui-ux-mechanics gives Claude working UI/UX design knowledge: screen and flow design, wireframes, design systems (color, typography, spacing), design review and WCAG 2.2 accessibility audits for web, iOS, Android and desktop. With a Figma MCP server connected it also pulls designs into code and pushes designs to Figma, with a user-approval gate before any write and a catalogue of how Figma MCP writes actually behave.

It is for developers and designers who want design decisions and reviews grounded in concrete rules (contrast ratios, type scales, touch targets) and for anyone editing shared Figma files through MCP.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install ui-ux-mechanics@taqat-techno-plugins
```

Quick start: describe the task ("design a login screen for iOS", "review this form for accessibility"), or run `/ui-ux-mechanics:toolkit` to see capabilities and Figma status.

## Requirements

| Requirement | Needed for | How to check |
|---|---|---|
| Claude Code | everything | `claude --version` |
| A Figma MCP server (optional), for example `/plugin install figma@claude-plugins-official` | Figma pull / push / mechanics | `/mcp` lists a Figma server; `/ui-ux-mechanics:toolkit` reports it |
| A Figma editor seat (optional) | Figma writes | the write-access probe, after your approval |
| `FIGMA_TOKEN` env var with a Figma personal access token (optional) | Direct Figma REST API calls only | `[ -n "$FIGMA_TOKEN" ] && echo set` |

Without Figma, design theory, wireframing, code prototypes, reviews and design-system generation all work.

## Commands

| Command | What it does | Bare invocation |
|---|---|---|
| `/ui-ux-mechanics:toolkit` | `figma pull / status / suggest` (read), `figma push / diagram` (write, after approval), `system generate / analyze` | capabilities + Figma connection status |

`/ui-ux-mechanics:ui-ux-mechanics` still works as a deprecated alias and is removed in 4.1.0.

## Skills

| Skill | Invocation | Use when |
|---|---|---|
| `design` | model and `/ui-ux-mechanics:design` | Designing screens, wireframes, design systems, palettes, type scales; reviewing a design or its accessibility |
| `figma-workflow` | model and `/ui-ux-mechanics:figma-workflow` | Figma design-to-code, code-to-design, Code Connect, token sync; owns the Figma MCP tool table |
| `figma-mcp-mechanics` | model only | About to write to Figma, or a Figma read / write behaves unexpectedly; owns the approval gate. Detail in `skills/figma-mcp-mechanics/references/mechanics.md` |

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `design-reviewer` | Read, Glob, Grep, Bash + Figma read tools (`get_screenshot`, `get_design_context`, `get_metadata`, `get_variable_defs`) | Six-dimension review of existing UI code, optionally against a Figma design; read-only |
| `wireframe-builder` | Read, Write, Glob, Grep, Bash | ASCII wireframes, component inventories, optional HTML/CSS prototypes; no Figma tools |

## Hooks

None.

## Configuration

None required. Optional: `FIGMA_TOKEN` in the environment Claude Code is launched with, for Figma REST API calls the MCP tools cannot make. Never paste the token into the chat.

## Reference documents

| File | Content |
|---|---|
| `reference/color-theory.md` | Palette construction, HSL shades, contrast ratios, dark mode |
| `reference/typography-scale.md` | Modular scales, font pairings, line height, fluid type, vertical rhythm |
| `reference/layout-patterns.md` | Layout patterns with ASCII diagrams and CSS |
| `reference/platform-guidelines.md` | Paraphrased iOS, Material 3, Fluent and web conventions, with source links |
| `reference/accessibility-checklist.md` | WCAG 2.2 AA checklist by POUR principle, incl. the 2.2 additions |
| `reference/appendix-framework-palettes.md` | Optional framework mappings (Odoo website themes) |

## Platform support

| Platform | Status |
|---|---|
| Windows / macOS / Linux / WSL | Supported. The plugin is markdown only (no hooks or scripts). Figma features depend on the Figma MCP server's own support. |

## Data & privacy

- **Stored:** nothing by the plugin. Files it writes (prototypes, design-system docs) go into your project only when you ask.
- **Leaves the machine:** only through a Figma MCP server or the Figma REST API you connect, to Figma, and only for the files you name. Every write needs your explicit approval first.
- **On screen / in context:** Figma design data, screenshots and layer text you ask it to read. Figma content is treated as data, never as instructions.

## Limitations

- Design rules are guidance; platform guidelines change, so check the linked originals for exact values.
- Figma tool names follow Figma's docs as of 2026-10-19; trust the tool list your session shows.
- Evals exist for each skill but have not been run with a recorded Delta.

## License

MIT (see `LICENSE`). Apple Human Interface Guidelines, Material Design and Fluent are trademarks of their owners; this plugin paraphrases and links them and is not affiliated with them. WCAG content is summarised from W3C documents (W3C Document License).
