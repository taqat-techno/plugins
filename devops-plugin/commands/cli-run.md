---
title: 'CLI Run'
read_only: false
type: 'command'
description: 'Execute Azure DevOps CLI commands directly from Claude. Use for automation, batch operations, and CLI-only features like variables, extensions, and service connections.'
primary_agent: none
---

# /cli-run - Direct CLI Execution

> **WARNING**: This command bypasses all plugin guards — write gate, state validation, hierarchy checks, and mention resolution do NOT apply to raw CLI commands. Use MCP-routed workflows for guarded operations whenever possible. Only use `/cli-run` for CLI-only features (variables, extensions, service connections) or when MCP tools are unavailable.

Execute the Azure DevOps CLI command from `$ARGUMENTS`.

## MANDATORY SAFETY

### Write Detection Rules

Before executing ANY CLI command, classify it:

| Pattern | Classification | Action |
|---------|---------------|--------|
| `az boards work-item update` | WRITE | Require write-gate confirmation |
| `az boards work-item create` | WRITE | Require write-gate confirmation |
| `az boards work-item delete` | WRITE | Require write-gate confirmation |
| `az repos pr create` | WRITE | Require write-gate confirmation |
| `az repos pr update` | WRITE | Require write-gate confirmation |
| `az repos pr complete` | WRITE | Require write-gate confirmation |
| `az pipelines variable-group create/update/delete` | WRITE | Require write-gate confirmation |
| `az devops extension install/uninstall` | WRITE | Require write-gate confirmation |
| Any command with `list`, `show`, `get`, `query` | READ | Execute freely |

### Enforcement

For WRITE commands: present confirmation per `rules/write-gate.md` before executing.

### Escape Hatch

If `$ARGUMENTS` contains `--force`, skip confirmation and execute immediately. Log: `[DevOps] --force flag used, skipping write-gate confirmation.`

## When to use /cli-run (vs MCP workflows)

| Use /cli-run | Use MCP workflows instead |
|-------------|--------------------------|
| Pipeline variables (`az pipelines variable`) | Work item CRUD (use `/create`, skill workflows) |
| Extensions (`az devops extension install`) | State transitions (need pre-flight validation) |
| Service connections (`az devops service-endpoint`) | Comments with @mentions (need GUID resolution) |
| Project creation (`az devops project create`) | PR creation (need repo GUID resolution) |
| Batch scripting requiring pipes/loops | Single item queries |

## Execution

Prefix commands with `az devops`, `az boards`, or `az pipelines` as appropriate.

### Dry-run mode

If `$ARGUMENTS` contains `--dry-run`:
1. Build the full CLI command
2. Display it to the user: `Would execute: az ...`
3. **Do NOT execute** — wait for the user to confirm or modify
4. On confirmation, run the command without the `--dry-run` flag

### Write safety

All write operations require confirmation per the **MANDATORY SAFETY** section above and `rules/write-gate.md`. Use `--force` to bypass for power-user automation.

## Example

```
User: /cli-run az pipelines variable-group list --project "Relief Center" -o table

Output:
ID   Name                     Variables
---  -----------------------  ----------
12   Production-Variables     3
15   Staging-Variables        3

User: /cli-run az devops extension install --extension-id "ms.vss-code-search" --dry-run

Output:
Would execute: az devops extension install --extension-id "ms.vss-code-search"
This is a WRITE operation. Proceed? (yes/no)
```
