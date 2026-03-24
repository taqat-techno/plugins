---
title: 'Init'
read_only: false
type: 'command'
description: 'Complete Azure DevOps integration - installs CLI, configures MCP, and enables hybrid mode for best performance. Use when user asks about DevOps setup, configuration, or status via /init.'
---

# /init - Azure DevOps Integration Setup

Set up the complete Azure DevOps integration.

Use the devops skill for the full setup workflow:
1. Check if `az devops` CLI is installed, install if missing
2. Configure PAT authentication
3. Set default organization and project
4. Configure MCP server connection
5. Generate user profile (team GUIDs, project IDs)
6. Cache profile to `~/.claude/devops.md`
7. Verify hybrid mode (test both CLI and MCP)

Key commands:
```bash
az extension add --name azure-devops
az devops configure --defaults organization=https://dev.azure.com/ORG project=PROJECT
az devops login --organization https://dev.azure.com/ORG
```

The devops skill contains the complete hybrid routing logic, profile generation templates, and MCP tool catalog.
