---
title: 'CLI Run'
read_only: false
type: 'command'
description: 'Execute Azure DevOps CLI commands directly from Claude. Use for automation, batch operations, and CLI-only features like variables, extensions, and service connections. Includes pipeline variable management and extension installation recipes.'
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
/cli-run az devops project show --project "Project Alpha"
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
| `'az' is not recognized` | CLI not installed | Run `/init setup --cli` |
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

## Pipeline Variables Recipe (formerly /setup-pipeline-vars)

Manage pipeline variables and variable groups using Azure DevOps CLI. Variable management is a **CLI-only feature** - MCP does not support this.

### WRITE OPERATION GATE

**Reference**: `guards/write_operation_guard.md`

For ALL write sub-commands (`create`, `add`, `secret`, `update`, `delete`, `pipeline-var`), you MUST present a confirmation summary and wait for explicit user approval before executing the CLI command. The `list`, `show`, and `info` sub-commands are read-only and do not require confirmation.

```
READY TO {ACTION}: Pipeline Variable
──────────────────────────────────────
Action:    {create/add/update/delete}
Group:     {group-name}
Variable:  {key} = {value} (or [SECRET])
Pipeline:  {pipeline-name} (if pipeline-var)

This affects shared infrastructure.
Proceed? (yes/no)
```

**Only execute the CLI command after the user explicitly says "yes".**

### Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `list` | List all variable groups |
| `show <group-name>` | Show variables in a group |
| `create <group-name>` | Create new variable group |
| `add <group-name> <key> <value>` | Add variable to group |
| `secret <group-name> <key>` | Add secret variable (prompts for value) |
| `update <group-name> <key> <value>` | Update existing variable |
| `delete <group-name> <key>` | Delete variable from group |
| `pipeline-var <pipeline> <key> <value>` | Set pipeline-specific variable |

### Examples

#### List Variable Groups

```
/cli-run az pipelines variable-group list --output table
```

**Sample Output:**
```
ID    Name                  Variables
----  --------------------  -----------
1     Common-Settings       3
2     Production-Secrets    5
3     Staging-Settings      4
```

#### Show Variables in Group

```bash
az pipelines variable-group show --group-id <id> --output table
```

**Sample Output:**
```
Name           Value                    IsSecret
-------------  -----------------------  --------
API_URL        https://api.example.com  False
API_KEY        ****                     True
DATABASE_URL   ****                     True
```

#### Create Variable Group

```bash
az pipelines variable-group create \
    --name "My-Variables" \
    --variables placeholder=temp \
    --authorize true \
    --output json
```

**Notes:**
- Creates a new variable group with a placeholder variable
- `--authorize true` allows all pipelines to use this group
- The placeholder can be deleted after adding real variables

#### Add Variable to Group

```bash
# First, get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Then add variable
az pipelines variable-group variable create \
    --group-id $GROUP_ID \
    --name API_URL \
    --value "https://api.example.com"
```

#### Add Secret Variable

```bash
# Get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Add secret variable (prompts for value or uses provided value securely)
az pipelines variable-group variable create \
    --group-id $GROUP_ID \
    --name API_KEY \
    --secret true
```

**Important:**
- Secret variables are encrypted at rest
- Values are never displayed in logs or UI
- Claude will prompt for the secret value or you can provide it

#### Update Variable

```bash
# Get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Update variable
az pipelines variable-group variable update \
    --group-id $GROUP_ID \
    --name API_URL \
    --value "https://new-api.example.com"
```

#### Delete Variable

```bash
# Get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Delete variable
az pipelines variable-group variable delete \
    --group-id $GROUP_ID \
    --name OLD_VAR \
    --yes
```

#### Set Pipeline-Specific Variable

```bash
az pipelines variable create \
    --name ENVIRONMENT \
    --value "staging" \
    --pipeline-name "CI-Build"
```

**Notes:**
- Pipeline variables are specific to one pipeline
- Use variable groups for shared variables across pipelines

### Variable Group Best Practices

#### Naming Convention

| Environment | Group Name Pattern |
|-------------|-------------------|
| Common | `Common-Settings` |
| Development | `Dev-Settings`, `Dev-Secrets` |
| Staging | `Staging-Settings`, `Staging-Secrets` |
| Production | `Prod-Settings`, `Prod-Secrets` |

#### Separate Settings from Secrets

```bash
# Settings (non-sensitive)
az pipelines variable-group create --name "Prod-Settings" --variables placeholder=temp --authorize true
# Then add: API_URL, LOG_LEVEL

# Secrets (sensitive)
az pipelines variable-group create --name "Prod-Secrets" --variables placeholder=temp --authorize true
# Then add with --secret true: API_KEY, DATABASE_PASSWORD
```

### Using Variable Groups in Pipelines

#### YAML Pipeline

```yaml
variables:
  - group: Common-Settings
  - group: Prod-Secrets

stages:
  - stage: Deploy
    jobs:
      - job: DeployApp
        steps:
          - script: |
              echo "Deploying to $(API_URL)"
              # $(API_KEY) is available but hidden in logs
```

#### Classic Pipeline

1. Go to Pipeline > Edit > Variables
2. Click "Variable groups"
3. Link the desired groups
4. Variables are automatically available

### Security Considerations

1. **Never log secret values** - They are automatically masked
2. **Use secret type for sensitive data** - Passwords, keys, tokens
3. **Rotate secrets regularly** - Update via variable update commands
4. **Limit group authorization** - Only authorize needed pipelines
5. **Audit variable access** - Check Azure DevOps audit logs

---

## Extension Management Recipe (formerly /install-extension)

Install extensions from the Azure DevOps Marketplace using CLI. Extension management is a **CLI-only feature** - MCP does not support this.

### WRITE OPERATION GATE

**Reference**: `guards/write_operation_guard.md`

For write sub-commands (`install`, `uninstall`, `enable`, `disable`), you MUST present a confirmation summary and wait for explicit user approval before executing the CLI command. The `search`, `list`, and `info` sub-commands are read-only and do not require confirmation.

```
READY TO {INSTALL/UNINSTALL}: Extension
─────────────────────────────────────────
Action:    {install/uninstall/enable/disable}
Extension: {publisher}.{extension-id}
Name:      {extension name}

This affects the entire organization.
Proceed? (yes/no)
```

**Only execute the CLI command after the user explicitly says "yes".**

### Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `install <publisher>.<extension-id>` | Install specific extension |
| `search <query>` | Search marketplace for extensions |
| `list` | List installed extensions |
| `info <publisher>.<extension-id>` | Get extension details |
| `uninstall <publisher>.<extension-id>` | Remove extension |
| `enable <publisher>.<extension-id>` | Enable disabled extension |
| `disable <publisher>.<extension-id>` | Disable extension |

### Examples

#### Install Extension

```bash
az devops extension install \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension
```

#### Search Extensions

```bash
az devops extension search --search-query "time tracker" --output table
```

**Sample Output:**
```
Publisher       Extension ID              Name                    Version
--------------  -----------------------  ----------------------  --------
ms-devlabs      timetracker              Time Tracker            1.5.0
7pace           Timetracker              7pace Timetracker       5.1.0
techtalk        timelog                  TimeLog                 2.3.1
```

#### List Installed Extensions

```bash
az devops extension list --output table
```

#### Get Extension Info

```bash
az devops extension show \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension \
    --output yaml
```

#### Uninstall Extension

```bash
az devops extension uninstall \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension \
    --yes
```

#### Enable/Disable Extensions

```bash
# Disable extension temporarily
az devops extension disable --publisher-id ms-devlabs --extension-id timetracker

# Re-enable extension
az devops extension enable --publisher-id ms-devlabs --extension-id timetracker
```

### Popular Extensions

#### Work Item Enhancements

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| Feature Timeline | `ms-devlabs.workitem-feature-timeline-extension` | Visualize features on timeline |
| Work Item Visualization | `ms-devlabs.vsts-extensions-workitem-vis` | Visualize work item relationships |
| Estimate | `ms-devlabs.estimate` | Planning poker for estimation |
| Retrospectives | `ms-devlabs.team-retrospectives` | Sprint retrospective tool |

#### Pipeline Enhancements

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| GitFlow | `ms.vss-services-gitflow` | GitFlow branching visualization |
| Pull Request Manager | `ms-devlabs.pull-request-manager` | Advanced PR management |
| Build Quality Checks | `ms-devlabs.vss-extensions-buildqualitychecks` | Quality gates for builds |

#### Time Tracking

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| 7pace Timetracker | `7pace.Timetracker` | Enterprise time tracking |
| Time Tracker | `ms-devlabs.timetracker` | Simple time tracking |

#### Testing & Quality

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| Test & Feedback | `ms.vss-exploratorytesting-web` | Exploratory testing |
| Code Coverage | `ms-devlabs.codecoveragesummary` | Code coverage summary |

### Bulk Installation

```bash
# DevOps essentials bundle
EXTENSIONS=(
    "ms-devlabs.workitem-feature-timeline-extension"
    "ms-devlabs.estimate"
    "ms-devlabs.team-retrospectives"
    "ms-devlabs.vss-extensions-buildqualitychecks"
)

for EXT in "${EXTENSIONS[@]}"; do
    PUBLISHER=$(echo $EXT | cut -d. -f1)
    EXTID=$(echo $EXT | cut -d. -f2-)
    echo "Installing $EXT..."
    az devops extension install --publisher-id $PUBLISHER --extension-id $EXTID
done
```

### Extension Discovery Workflow

1. **Search** for extensions matching your need:
   ```bash
   az devops extension search --search-query "retrospective" --output table
   ```

2. **Get info** on promising extensions:
   ```bash
   az devops extension show --publisher-id ms-devlabs --extension-id team-retrospectives --output yaml
   ```

3. **Check reviews** in Azure DevOps Marketplace web UI

4. **Install** the extension:
   ```bash
   az devops extension install --publisher-id ms-devlabs --extension-id team-retrospectives
   ```

5. **Verify** installation:
   ```bash
   az devops extension list --output table
   ```

### Permission Requirements

| Permission | Level |
|------------|-------|
| Organization Owner | Full access |
| Project Collection Admin | Full access |
| Extension Manager | Can install/uninstall |
| Regular User | Can request extensions |

---

## Related Commands

- `/init setup` - Install and configure CLI
- `/init status` - Check CLI status

> Previously: /setup-pipeline-vars, /install-extension

---

*Part of DevOps Plugin v4.0*
