---
name: figma-workflow
description: >-
  Use when the user wants to work with Figma designs: pulling designs from Figma
  to generate code, pushing code/descriptions to Figma, checking component mappings,
  creating FigJam diagrams, or syncing design tokens. Requires the Figma MCP plugin.
  Also use when user mentions "Figma", "figma pull", "figma push", "component mapping",
  "design-to-code", "code-to-design", "FigJam diagram", or provides a figma.com URL.

  <example>
  Context: User wants to implement a Figma design
  user: "Implement this Figma design: https://figma.com/design/abc123/MyApp?node-id=42-15"
  assistant: "I will use the figma-workflow skill to fetch the design context, extract tokens, and generate production code matching the Figma layout."
  <commentary>Design-to-code trigger - Figma URL provided for implementation.</commentary>
  </example>

  <example>
  Context: User wants to push a design to Figma
  user: "Create a Figma design for this hero section"
  assistant: "I will use the figma-workflow skill to generate a Figma design from the description using the MCP generate tool."
  <commentary>Code-to-design trigger - creating a Figma design from description.</commentary>
  </example>

  <example>
  Context: User wants to check component mappings
  user: "Which Figma components are mapped to code in this file?"
  assistant: "I will use the figma-workflow skill to fetch the code connect map and show which components have code mappings."
  <commentary>Component mapping trigger - checking Figma-to-code connections.</commentary>
  </example>
---
<!-- Last updated: 2026-03-26 -->

# Figma MCP Workflow Integration

## Prerequisites

This skill requires the **Figma MCP plugin** to be installed and authenticated.

**If Figma MCP tools are not available**, inform the user:
```
Figma MCP is not connected. To set up:
  claude plugin install figma@claude-plugins-official
Then restart Claude Code and authenticate when prompted.
```

Without Figma MCP, the Paper plugin still works for design theory, wireframing, code-based prototyping, design reviews, and design system generation.

---

## MCP Tools Reference

| Tool | Type | Purpose |
|------|------|---------|
| `whoami` | Read | Check authentication / connection |
| `get_metadata` | Read | File/node structure and hierarchy |
| `get_screenshot` | Read | Visual capture of a node or frame |
| `get_design_context` | Read | Structured design data (layout, styles, constraints) |
| `get_variable_defs` | Read | Design tokens (colors, spacing, typography variables) |
| `get_code_connect_map` | Read | Current component-to-code mappings |
| `get_code_connect_suggestions` | Read | AI-suggested mappings |
| `add_code_connect_map` | Write | Register a single component mapping |
| `send_code_connect_mappings` | Write | Batch-register component mappings |
| `generate_figma_design` | Write | Create/update a Figma design from description |
| `generate_diagram` | Write | Create a FigJam diagram from Mermaid syntax |
| `create_design_system_rules` | Write | Generate framework-aware design rules |
| `get_figjam` | Read | Read FigJam board content |

---

## URL Parsing Rules

All Figma operations that accept a URL must extract:

- **`fileKey`** — the path segment after `/design/` or `/file/`
- **`nodeId`** — from the `node-id` query parameter, converting hyphens to colons

```
https://figma.com/design/:fileKey/:fileName?node-id=1-2
                          ^^^^^^^^                  ^^^
                          fileKey                   nodeId -> 1:2
```

If `node-id` is absent, operate on the entire file (omit `nodeId`).

---

## Design-to-Code Workflow

**When you have a Figma URL and need to implement it as code:**

1. **Parse URL** — Extract `fileKey` and `nodeId`.
2. **Get metadata** — Call `get_metadata(fileKey, nodeId)` to understand the design structure.
3. **Capture screenshot** — Call `get_screenshot(fileKey, nodeId)` for visual reference.
4. **Fetch design context** — Call `get_design_context(fileKey, nodeId)` for layout, typography, colors, spacing.
5. **Extract design tokens** — Call `get_variable_defs(fileKey, nodeId)` for color/spacing/typography tokens.
6. **Detect framework** — Inspect the project to determine target framework (Bootstrap, Tailwind, React, Vue, etc.). If ambiguous, ask the user.
7. **Generate code** — Translate the Figma design into production-ready code with:
   - Semantic HTML structure
   - Framework-specific classes and components
   - Design tokens mapped to the project's token system
   - Responsive breakpoints (mobile-first)
   - Accessibility attributes (`alt`, `aria-label`, `role`, keyboard navigation)
   - Separate JS and CSS files (no inline scripts or styles)
8. **Offer mapping** — Ask if the user wants to register the component mapping. On approval, call `add_code_connect_map(fileKey, nodeId, componentPath)`.

---

## Code-to-Design Workflow

**When you have code/description and want to create a Figma design:**

1. **Define the UI** — Describe the screen, page, or component in natural language. Include layout, colors, typography, content, interactions.
2. **Generate in Figma** — Call `generate_figma_design(description, targetFileUrl)`.
3. **Review and iterate** — Call `get_screenshot(fileKey, nodeId)` to verify. Refine and regenerate if needed.
4. **Create diagrams** (for flow documentation) — Call `generate_diagram(mermaidSyntax)`. Supports flowcharts, sequence diagrams, state diagrams, Gantt charts.

---

## Design System Sync Workflow

1. **Check connection** — Call `whoami()` to verify Figma authentication.
2. **Extract tokens** — Call `get_variable_defs(fileKey, nodeId)` and map to CSS custom properties or framework tokens.
3. **Generate project rules** — Call `create_design_system_rules(clientLanguages, clientFrameworks)` and save to project documentation.
4. **Map components** — Call `get_code_connect_suggestions(fileKey, nodeId)`, review suggestions, then call `send_code_connect_mappings(fileKey, nodeId, mappings)` for approved matches.

---

## Asset Handling Rules

- If Figma MCP returns a `localhost` URL for an image/SVG — **use it directly**
- **NEVER** import new icon packages — all assets come from the Figma payload
- **NEVER** create placeholder images if a localhost source is provided
- Assets are served through the Figma MCP server's built-in endpoint
