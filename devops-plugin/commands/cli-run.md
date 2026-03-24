---
title: 'CLI Run'
read_only: false
type: 'command'
description: 'Execute Azure DevOps CLI commands directly from Claude. Use for automation, batch operations, and CLI-only features like variables, extensions, and service connections.'
---

# /cli-run - Direct CLI Execution

Execute the Azure DevOps CLI command from `$ARGUMENTS`.

Use the devops skill for:
- CLI command reference and syntax
- Pipeline variable management
- Extension installation recipes
- Service connection configuration
- Batch operation patterns
- CLI vs MCP routing (prefer CLI for batch, MCP for interactive)

Prefix commands with `az devops`, `az boards`, or `az pipelines` as appropriate.
Use the write operation gate for commands that modify state.
