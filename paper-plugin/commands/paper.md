---
description: 'UI/UX Design toolkit - Figma sync, design system management, and capabilities overview'
argument-hint: '[figma|system] [sub-command] [args...]'
---

# Paper - Unified Design Toolkit

Parse `$ARGUMENTS` and dispatch:

| Arguments | Action |
|-----------|--------|
| *(empty)* | Show capabilities + status |
| `figma pull <url>` | Extract design from Figma URL |
| `figma push <desc> [url]` | Push design to Figma/FigJam |
| `figma status <url>` | Compare code vs Figma design |
| `figma suggest <url>` | Get improvement suggestions from Figma |
| `figma diagram <desc>` | Create diagram in FigJam |
| `system generate` | Generate design system from codebase |
| `system analyze` | Analyze existing design patterns |

Use the paper skills for:
- **design skill**: Color theory, typography scales, accessibility (WCAG), layout patterns, platform guidelines (iOS HIG, Material Design 3)
- **figma-workflow skill**: Figma MCP integration, design-to-code pipelines, Code Connect

If arguments don't match any route, infer intent from natural language.
