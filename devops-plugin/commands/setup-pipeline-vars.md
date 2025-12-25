---
title: 'Setup Pipeline Variables'
read_only: false
type: 'command'
description: 'Configure pipeline variables and variable groups using Azure DevOps CLI. This is a CLI-only feature not available through MCP.'
---

# Setup Pipeline Variables

Manage pipeline variables and variable groups using Azure DevOps CLI. Variable management is a **CLI-only feature** - MCP does not support this.

## Usage

```
/setup-pipeline-vars <sub-command> [options]
```

## Sub-Commands

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

---

## Examples

### List Variable Groups

```
/setup-pipeline-vars list
```

**Execution:**
```bash
az pipelines variable-group list --output table
```

**Sample Output:**
```
ID    Name                  Variables
----  --------------------  -----------
1     Common-Settings       3
2     Production-Secrets    5
3     Staging-Settings      4
```

---

### Show Variables in Group

```
/setup-pipeline-vars show "Production-Secrets"
```

**Execution:**
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

---

### Create Variable Group

```
/setup-pipeline-vars create "My-Variables"
```

**Execution:**
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

---

### Add Variable to Group

```
/setup-pipeline-vars add "Production-Secrets" API_URL "https://api.example.com"
```

**Execution:**
```bash
# First, get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Then add variable
az pipelines variable-group variable create \
    --group-id $GROUP_ID \
    --name API_URL \
    --value "https://api.example.com"
```

---

### Add Secret Variable

```
/setup-pipeline-vars secret "Production-Secrets" API_KEY
```

**Execution:**
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

---

### Update Variable

```
/setup-pipeline-vars update "Production-Secrets" API_URL "https://new-api.example.com"
```

**Execution:**
```bash
# Get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Update variable
az pipelines variable-group variable update \
    --group-id $GROUP_ID \
    --name API_URL \
    --value "https://new-api.example.com"
```

---

### Delete Variable

```
/setup-pipeline-vars delete "Production-Secrets" OLD_VAR
```

**Execution:**
```bash
# Get group ID
GROUP_ID=$(az pipelines variable-group list --query "[?name=='Production-Secrets'].id" -o tsv)

# Delete variable
az pipelines variable-group variable delete \
    --group-id $GROUP_ID \
    --name OLD_VAR \
    --yes
```

---

### Set Pipeline-Specific Variable

```
/setup-pipeline-vars pipeline-var "CI-Build" ENVIRONMENT "staging"
```

**Execution:**
```bash
az pipelines variable create \
    --name ENVIRONMENT \
    --value "staging" \
    --pipeline-name "CI-Build"
```

**Notes:**
- Pipeline variables are specific to one pipeline
- Use variable groups for shared variables across pipelines

---

## Variable Group Best Practices

### 1. Naming Convention

| Environment | Group Name Pattern |
|-------------|-------------------|
| Common | `Common-Settings` |
| Development | `Dev-Settings`, `Dev-Secrets` |
| Staging | `Staging-Settings`, `Staging-Secrets` |
| Production | `Prod-Settings`, `Prod-Secrets` |

### 2. Separate Settings from Secrets

```
# Settings (non-sensitive)
/setup-pipeline-vars create "Prod-Settings"
/setup-pipeline-vars add "Prod-Settings" API_URL "https://api.example.com"
/setup-pipeline-vars add "Prod-Settings" LOG_LEVEL "info"

# Secrets (sensitive)
/setup-pipeline-vars create "Prod-Secrets"
/setup-pipeline-vars secret "Prod-Secrets" API_KEY
/setup-pipeline-vars secret "Prod-Secrets" DATABASE_PASSWORD
```

### 3. Use Descriptive Names

```
# Good
API_BASE_URL
DATABASE_CONNECTION_STRING
STORAGE_ACCOUNT_KEY

# Avoid
URL
CONN
KEY
```

---

## Using Variable Groups in Pipelines

### YAML Pipeline

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

### Classic Pipeline

1. Go to Pipeline → Edit → Variables
2. Click "Variable groups"
3. Link the desired groups
4. Variables are automatically available

---

## Authorization

### Authorize All Pipelines

```bash
az pipelines variable-group create \
    --name "Shared-Settings" \
    --variables KEY=VALUE \
    --authorize true
```

### Authorize Specific Pipeline

```bash
# Get pipeline ID
PIPELINE_ID=$(az pipelines show --name "CI-Build" --query "id" -o tsv)

# Authorize variable group for pipeline
az pipelines variable-group update \
    --group-id <group-id> \
    --authorize true \
    --pipeline-ids $PIPELINE_ID
```

---

## Bulk Operations

### Create Multiple Variables

```bash
# Create group with multiple variables at once
/cli-run az pipelines variable-group create \
    --name "App-Settings" \
    --variables \
        API_URL=https://api.example.com \
        LOG_LEVEL=info \
        MAX_RETRIES=3 \
        TIMEOUT=30 \
    --authorize true
```

### Export Variables to JSON

```bash
# Export for backup
/cli-run az pipelines variable-group show --group-id 1 --output json > variables-backup.json
```

---

## Common Patterns

### Environment-Specific Variables

```
# Development
/setup-pipeline-vars create "Dev-Settings"
/setup-pipeline-vars add "Dev-Settings" ENVIRONMENT "development"
/setup-pipeline-vars add "Dev-Settings" API_URL "https://dev-api.example.com"
/setup-pipeline-vars add "Dev-Settings" DEBUG "true"

# Staging
/setup-pipeline-vars create "Staging-Settings"
/setup-pipeline-vars add "Staging-Settings" ENVIRONMENT "staging"
/setup-pipeline-vars add "Staging-Settings" API_URL "https://staging-api.example.com"
/setup-pipeline-vars add "Staging-Settings" DEBUG "false"

# Production
/setup-pipeline-vars create "Prod-Settings"
/setup-pipeline-vars add "Prod-Settings" ENVIRONMENT "production"
/setup-pipeline-vars add "Prod-Settings" API_URL "https://api.example.com"
/setup-pipeline-vars add "Prod-Settings" DEBUG "false"
```

### Feature Flags

```
/setup-pipeline-vars create "Feature-Flags"
/setup-pipeline-vars add "Feature-Flags" FEATURE_NEW_UI "true"
/setup-pipeline-vars add "Feature-Flags" FEATURE_DARK_MODE "false"
/setup-pipeline-vars add "Feature-Flags" FEATURE_BETA_API "true"
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Variable group not found" | Wrong name | Check spelling, use `list` to verify |
| "Access denied" | Not authorized | Add `--authorize true` or check permissions |
| "Variable already exists" | Duplicate | Use `update` instead of `add` |
| "Pipeline not found" | Wrong pipeline name | Verify with `az pipelines list` |

---

## Security Considerations

1. **Never log secret values** - They are automatically masked
2. **Use secret type for sensitive data** - Passwords, keys, tokens
3. **Rotate secrets regularly** - Update via `/setup-pipeline-vars update`
4. **Limit group authorization** - Only authorize needed pipelines
5. **Audit variable access** - Check Azure DevOps audit logs

---

## Related Commands

- `/cli-run` - Execute any CLI command
- `/devops setup` - Install CLI
- `/install-extension` - Install extensions
