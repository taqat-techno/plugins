---
description: 'Sync designs between Figma and code via MCP'
argument-hint: '[pull|push|status|suggest|diagram] [figma-url]'
---

# Figma Sync Command

Orchestrate Figma MCP tools for bidirectional design-code synchronization.

## Prerequisites

This command requires the **Figma MCP plugin** to be installed and authenticated.
If Figma MCP tools are not available, inform the user:
```
Figma MCP is not connected. To set up:
  claude plugin install figma@claude-plugins-official
Then restart Claude Code and authenticate when prompted.
```

## Sub-Commands

### `/figma-sync pull <figma-url>`

**Read a Figma design and generate code:**

1. Parse the Figma URL to extract `fileKey` and `nodeId`
   - URL format: `https://figma.com/design/:fileKey/:fileName?node-id=1-2`
2. Call `get_metadata(fileKey, nodeId)` to understand the design structure
3. Call `get_screenshot(fileKey, nodeId)` to capture a visual reference
4. Call `get_design_context(fileKey, nodeId)` to fetch structured design data
5. Call `get_variable_defs(fileKey, nodeId)` to extract design tokens
6. Translate the design into the project's framework (detect from context or ask)
7. Generate production-ready code with:
   - Semantic HTML
   - Framework-specific classes (Bootstrap 5, Tailwind, etc.)
   - Design tokens mapped to project tokens
   - Responsive breakpoints
   - Accessibility attributes
8. Offer to register the mapping with `add_code_connect_map`

### `/figma-sync push <description> [figma-url]`

**Send a design from code/description to Figma:**

1. If a Figma URL is provided, push to that file
2. If no URL, create in a new Figma file
3. Call `generate_figma_design(description, targetFileUrl)`
4. Call `get_screenshot` to verify the result
5. Show the result and offer iteration

### `/figma-sync status <figma-url>`

**Check current component mapping status:**

1. Parse the Figma URL
2. Call `get_code_connect_map(fileKey, nodeId)`
3. Display which components are mapped and which are unmapped:
   ```
   Component Mapping Status:
   Connected:
     Button (42:15) → src/components/Button.tsx
     Card (42:20) → src/components/Card.tsx

   Unmapped:
     SearchBar (42:25) — no code match found
     Avatar (42:30) — no code match found
   ```

### `/figma-sync suggest <figma-url>`

**Get AI-suggested component mappings:**

1. Parse the Figma URL (convert `node-id=1-2` to `nodeId=1:2`)
2. Call `get_code_connect_suggestions(fileKey, nodeId)`
3. Search the codebase for matching components
4. Present suggestions for user approval
5. On approval, call `send_code_connect_mappings(fileKey, nodeId, mappings)`

### `/figma-sync diagram <description>`

**Generate a FigJam diagram from a description:**

1. Convert the natural language description to Mermaid syntax
2. Call `generate_diagram(mermaidSyntax)`
3. Supported types: flowcharts, sequence diagrams, state diagrams, Gantt charts

Examples:
- `/figma-sync diagram user registration flow`
- `/figma-sync diagram payment processing sequence`
- `/figma-sync diagram order state machine`

### `/figma-sync` (no sub-command)

Show available sub-commands:
```
Figma Sync Commands:
  /figma-sync pull <url>         — Read Figma design, generate code
  /figma-sync push <desc> [url]  — Send design to Figma
  /figma-sync status <url>       — Check component mapping status
  /figma-sync suggest <url>      — Get AI-suggested component mappings
  /figma-sync diagram <desc>     — Generate a FigJam diagram
```
