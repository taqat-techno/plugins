---
title: 'CLI Run'
read_only: false
type: 'command'
description: 'Execute Azure DevOps CLI commands directly from Claude. Use for automation, batch operations, and CLI-only features like variables, extensions, and service connections.'
---

# CLI Run - Execute Azure DevOps CLI Commands

Execute Azure DevOps CLI commands directly through Claude for powerful automation and scripting capabilities.

## Usage

```
/cli-run <command>
/cli-run help
```

## Examples

```
/cli-run az boards work-item create --title "New Task" --type Task
/cli-run az pipelines run --name "CI-Build"
/cli-run az repos pr list --status active
/cli-run az devops project list
```

---

## Command Categories

### Work Items

```bash
# Create work item
/cli-run az boards work-item create --title "Task Title" --type Task --assigned-to "user@email.com"

# Update work item
/cli-run az boards work-item update --id 123 --state Active

# Query work items
/cli-run az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"

# Show work item details
/cli-run az boards work-item show --id 123
```

### Pull Requests

```bash
# List PRs
/cli-run az repos pr list --status active --output table

# Create PR
/cli-run az repos pr create --source-branch feature/login --target-branch main --title "Feature: Login"

# Update PR
/cli-run az repos pr update --id 45 --auto-complete true --squash true

# Complete PR
/cli-run az repos pr update --id 45 --status completed
```

### Pipelines

```bash
# Run pipeline
/cli-run az pipelines run --name "CI-Build" --branch main

# List builds
/cli-run az pipelines runs list --top 10 --output table

# Get build status
/cli-run az pipelines runs show --id 456

# List pipeline definitions
/cli-run az pipelines list --output table
```

### Repositories

```bash
# List repos
/cli-run az repos list --output table

# Show repo details
/cli-run az repos show --repository my-repo

# List branches
/cli-run az repos ref list --repository my-repo --filter heads/
```

### Projects

```bash
# List projects
/cli-run az devops project list --output table

# Create project (CLI only)
/cli-run az devops project create --name "New Project" --description "Project description"

# Show project details
/cli-run az devops project show --project "Relief Center"
```

---

## CLI-Only Features

These features are **only available via CLI**, not MCP:

### Variable Groups

```bash
# List variable groups
/cli-run az pipelines variable-group list --output table

# Create variable group
/cli-run az pipelines variable-group create --name "Production Secrets" --variables API_URL=https://api.example.com --authorize true

# Add variable to group
/cli-run az pipelines variable-group variable create --group-id 1 --name DATABASE_URL --value "connection-string"

# Add secret variable (will prompt for value)
/cli-run az pipelines variable-group variable create --group-id 1 --name API_KEY --secret true
```

### Pipeline Variables

```bash
# Create pipeline variable
/cli-run az pipelines variable create --name ENVIRONMENT --value staging --pipeline-name "CI-Build"

# Update pipeline variable
/cli-run az pipelines variable update --name ENVIRONMENT --value production --pipeline-name "CI-Build"

# List pipeline variables
/cli-run az pipelines variable list --pipeline-name "CI-Build"
```

### Extensions

```bash
# Search extensions
/cli-run az devops extension search --search-query "timetracker" --output table

# Install extension
/cli-run az devops extension install --publisher-id ms-devlabs --extension-id workitem-feature-timeline-extension

# List installed extensions
/cli-run az devops extension list --output table
```

### Service Connections

```bash
# List service connections
/cli-run az devops service-endpoint list --output table

# Create Azure RM service connection
/cli-run az devops service-endpoint azurerm create --name "Azure Production" --azure-rm-subscription-id "sub-id" --azure-rm-subscription-name "Production"
```

---

## Execution Flow

When you use `/cli-run`, Claude will:

1. **Parse Command**: Extract the CLI command from your input
2. **Validate**: Ensure it's a valid `az devops` or `az boards/repos/pipelines` command
3. **Execute**: Run the command using the Bash tool
4. **Format Output**: Present results in a readable format
5. **Handle Errors**: Provide troubleshooting if command fails

---

## Output Formats

Control output format with `--output` flag:

| Format | Use Case | Example |
|--------|----------|---------|
| `table` | Human-readable | `--output table` |
| `json` | Scripting, parsing | `--output json` |
| `tsv` | Shell variables | `--output tsv` |
| `yaml` | Configuration | `--output yaml` |

```bash
# Table format (default for display)
/cli-run az devops project list --output table

# JSON format (for parsing)
/cli-run az repos list --output json

# TSV format (for scripts)
/cli-run az repos list --query "[].name" --output tsv
```

---

## Query Filtering (JMESPath)

Use `--query` to filter and transform output:

```bash
# Get specific fields
/cli-run az repos list --query "[].{Name:name, ID:id}" --output table

# Filter by property
/cli-run az repos pr list --query "[?status=='active']" --output table

# Get first item
/cli-run az pipelines runs list --query "[0]" --output json

# Count items
/cli-run az boards query --wiql "SELECT [System.Id] FROM WorkItems" --query "length(@)"
```

---

## Batch Operations

Execute multiple commands for bulk operations:

### Sequential Execution

```bash
# Update multiple work items
/cli-run az boards work-item update --id 1 --state Done && az boards work-item update --id 2 --state Done
```

### Parallel Execution (Bash)

```bash
# Run in parallel (use with caution)
/cli-run az boards work-item update --id 1 --state Active & az boards work-item update --id 2 --state Active & wait
```

---

## Environment Variables

The CLI uses these environment variables:

| Variable | Purpose |
|----------|---------|
| `AZURE_DEVOPS_EXT_PAT` | PAT token for authentication |
| `AZURE_DEVOPS_ORGANIZATION` | Default organization |
| `AZURE_DEVOPS_PROJECT` | Default project |

Check current defaults:
```bash
/cli-run az devops configure --list
```

---

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `'az' is not recognized` | CLI not installed | Run `/devops setup --cli` |
| `Please run 'az login'` | Not authenticated | Set `AZURE_DEVOPS_EXT_PAT` or run `az devops login` |
| `TF400813: Resource not available` | Wrong org/project | Check `az devops configure --list` |
| `TF401019: Work item does not exist` | Invalid ID | Verify work item ID exists |
| `Extension not installed` | Missing extension | Run `az extension add --name azure-devops` |

---

## Security Notes

1. **Never include PAT tokens** in commands - use environment variables
2. **Avoid `--output json` with secrets** - may expose sensitive data
3. **Use `--secret true`** for sensitive variables
4. **Check command** before execution if modifying data

---

## When to Use /cli-run vs MCP

| Use /cli-run | Use MCP Tools |
|--------------|---------------|
| Batch operations | Single item queries |
| Variable management | PR code reviews |
| Extension installation | Test plan management |
| Service connections | Search operations |
| Project creation | Security alerts |
| Scripted workflows | Natural language queries |

---

## Related Commands

- `/devops setup` - Install and configure CLI
- `/devops status` - Check CLI status
- `/setup-pipeline-vars` - Manage pipeline variables
- `/install-extension` - Install marketplace extensions
