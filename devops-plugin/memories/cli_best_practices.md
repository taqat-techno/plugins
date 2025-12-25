# Azure DevOps CLI Best Practices

> **Purpose**: This memory provides Claude with best practices for using Azure DevOps CLI effectively. Use these patterns for optimal performance, security, and reliability.

## Quick Reference

| Pattern | Command Example | When to Use |
|---------|-----------------|-------------|
| Set defaults | `az devops configure --defaults org=... project=...` | First setup |
| JSON output | `--output json` | Scripting, parsing |
| TSV output | `--output tsv` | Simple extraction |
| Table output | `--output table` | Human reading |
| Query filter | `--query "[].name"` | Field selection |
| Parallel exec | `command &` + `wait` | Batch operations |

---

## 1. Configuration Best Practices

### 1.1 Set Defaults First (Always)

```bash
# Set organization and project defaults to avoid repeating in every command
az devops configure --defaults \
    organization=https://dev.azure.com/TaqaTechno \
    project="Relief Center"

# Verify defaults
az devops configure --list
```

**Why**: Eliminates need to specify `--organization` and `--project` in every command.

### 1.2 Check Current Configuration

```bash
# List all defaults
az devops configure --list

# Expected output:
# organization = https://dev.azure.com/TaqaTechno
# project = Relief Center
```

---

## 2. Output Format Best Practices

### 2.1 JSON for Scripting

```bash
# Get structured data for parsing
az boards work-item show --id 123 --output json

# Parse with jq (Unix) or ConvertFrom-Json (PowerShell)
az repos list --output json | jq '.[].name'
```

### 2.2 TSV for Simple Extraction

```bash
# Get simple values for shell variables
REPO_ID=$(az repos list --query "[?name=='my-repo'].id" --output tsv)

# Loop through results
az boards query --wiql "SELECT [System.Id] FROM WorkItems" \
    --query "[].id" --output tsv | while read ID; do
    echo "Processing $ID"
done
```

### 2.3 Table for Human Reading

```bash
# Display readable output
az devops project list --output table

# With specific columns
az repos pr list --output table --query "[].{ID:pullRequestId,Title:title,Status:status}"
```

---

## 3. Query Filtering with JMESPath

### 3.1 Select Specific Fields

```bash
# Get only names and IDs
az repos list --query "[].{Name:name, ID:id}" --output table

# Get first item only
az repos list --query "[0]" --output json
```

### 3.2 Filter Results

```bash
# Filter by property value
az repos list --query "[?name=='my-repo']" --output json

# Filter with contains
az repos list --query "[?contains(name, 'api')]" --output json

# Multiple conditions
az repos pr list --query "[?status=='active' && targetRefName=='refs/heads/main']"
```

### 3.3 Nested Property Access

```bash
# Access nested fields in work items
az boards work-item show --id 123 \
    --query "{Title:fields.\"System.Title\", State:fields.\"System.State\"}"
```

---

## 4. Parallel Execution

### 4.1 Background Jobs (Bash)

```bash
#!/bin/bash
# Run multiple commands in parallel

# Start background jobs
az boards work-item update --id 1 --state Active &
az boards work-item update --id 2 --state Active &
az boards work-item update --id 3 --state Active &

# Wait for all to complete
wait

echo "All updates completed"
```

### 4.2 PowerShell Jobs

```powershell
# Create parallel jobs
$jobs = @()
1..10 | ForEach-Object {
    $jobs += Start-Job -ScriptBlock {
        param($id)
        az boards work-item update --id $id --state Active
    } -ArgumentList $_
}

# Wait for completion
$jobs | Wait-Job | Receive-Job
```

### 4.3 GNU Parallel (Linux/macOS)

```bash
# Update 100 work items in parallel (10 at a time)
seq 1 100 | parallel -j10 'az boards work-item update --id {} --state Active'
```

---

## 5. Work Item Operations

### 5.1 Create Work Items

```bash
# Simple task
az boards work-item create \
    --title "Implement login feature" \
    --type Task \
    --assigned-to "ahmed@taqatechno.com"

# With description and parent
az boards work-item create \
    --title "Design database schema" \
    --type Task \
    --description "Create tables for user authentication" \
    --fields "System.Parent=1234"

# With custom fields
az boards work-item create \
    --title "Critical Bug" \
    --type Bug \
    --fields "Microsoft.VSTS.Common.Priority=1" \
              "Microsoft.VSTS.Common.Severity=1 - Critical"
```

### 5.2 Update Work Items

```bash
# Update state
az boards work-item update --id 123 --state Active

# Update multiple fields
az boards work-item update --id 123 \
    --state "In Progress" \
    --assigned-to "mahmoud@taqatechno.com" \
    --fields "Microsoft.VSTS.Common.Priority=2"

# Add to iteration
az boards work-item update --id 123 \
    --iteration "Relief Center\\Sprint 15"
```

### 5.3 Query Work Items (WIQL)

```bash
# Simple query
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"

# Query with state filter
az boards query --wiql "
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = 'Relief Center'
  AND [System.State] = 'Active'
  AND [System.AssignedTo] = @Me
ORDER BY [System.ChangedDate] DESC
"
```

---

## 6. Pull Request Operations

### 6.1 Create PR

```bash
# Basic PR
az repos pr create \
    --source-branch feature/login \
    --target-branch main \
    --title "Feature: User Login" \
    --description "Implements user authentication"

# PR with work items and reviewers
az repos pr create \
    --source-branch feature/login \
    --target-branch main \
    --title "Feature: User Login" \
    --description "## Summary\n- Added login page\n- JWT authentication" \
    --work-items 123 456 \
    --reviewers "mahmoud@taqatechno.com" "eslam@taqatechno.com"

# Draft PR
az repos pr create \
    --source-branch feature/wip \
    --target-branch main \
    --title "[WIP] New Feature" \
    --draft
```

### 6.2 Update PR

```bash
# Set auto-complete
az repos pr update --id 45 \
    --auto-complete true \
    --delete-source-branch true \
    --squash true

# Complete PR
az repos pr update --id 45 --status completed

# Abandon PR
az repos pr update --id 45 --status abandoned
```

### 6.3 List and Filter PRs

```bash
# Active PRs
az repos pr list --status active --output table

# My PRs
az repos pr list --creator "ahmed@taqatechno.com" --output table

# PRs targeting main
az repos pr list --target-branch main --output table
```

---

## 7. Pipeline Operations

### 7.1 Run Pipelines

```bash
# Run by name
az pipelines run --name "CI-Build"

# Run with branch
az pipelines run --name "CI-Build" --branch feature/login

# Run with parameters
az pipelines run --name "Deploy" \
    --parameters environment=staging debug=true

# Run with variables
az pipelines run --name "CI-Build" \
    --variables "VERSION=1.2.3" "SKIP_TESTS=false"
```

### 7.2 Monitor Builds

```bash
# List recent runs
az pipelines runs list --top 10 --output table

# Get build status
az pipelines runs show --id 456 \
    --query "{Status:status, Result:result, StartTime:startTime}"

# Watch build (poll every 30 seconds)
while true; do
    STATUS=$(az pipelines runs show --id 456 --query "status" -o tsv)
    echo "Status: $STATUS"
    if [ "$STATUS" == "completed" ]; then break; fi
    sleep 30
done
```

### 7.3 Get Build Logs

```bash
# List log files
az pipelines runs artifact list --run-id 456

# Download logs
az pipelines runs artifact download --run-id 456 \
    --artifact-name logs \
    --path ./build_logs
```

---

## 8. Repository Operations

### 8.1 List and Get Repos

```bash
# List all repos
az repos list --output table

# Get specific repo
az repos show --repository my-repo
```

### 8.2 Branch Operations

```bash
# List branches
az repos ref list --repository my-repo --filter heads/

# Create branch (via git, not CLI)
git checkout -b feature/new-feature
git push -u origin feature/new-feature
```

### 8.3 Import Repository

```bash
# Import from GitHub
az repos import create \
    --git-url https://github.com/user/repo.git \
    --repository new-repo-name
```

---

## 9. Variable Management (CLI-Only)

### 9.1 Variable Groups

```bash
# List variable groups
az pipelines variable-group list --output table

# Create variable group
az pipelines variable-group create \
    --name "Production Secrets" \
    --variables API_URL=https://api.example.com \
    --authorize true

# Add variable to group
az pipelines variable-group variable create \
    --group-id 1 \
    --name DATABASE_URL \
    --value "postgres://..."

# Add secret variable (prompts for value)
az pipelines variable-group variable create \
    --group-id 1 \
    --name API_KEY \
    --secret true
```

### 9.2 Pipeline Variables

```bash
# Create pipeline variable
az pipelines variable create \
    --name ENVIRONMENT \
    --value staging \
    --pipeline-name "CI-Build"

# Update variable
az pipelines variable update \
    --name ENVIRONMENT \
    --value production \
    --pipeline-name "CI-Build"
```

---

## 10. Extension Management (CLI-Only)

### 10.1 Search Extensions

```bash
# Search marketplace
az devops extension search --search-query "timetracker" --output table
```

### 10.2 Install Extensions

```bash
# Install by publisher and extension ID
az devops extension install \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension

# List installed extensions
az devops extension list --output table
```

---

## 11. Security Best Practices

### 11.1 PAT Token Handling

```bash
# NEVER hardcode PATs in scripts
# BAD:
# az devops login --token "abc123secret"

# GOOD: Use environment variable
export AZURE_DEVOPS_EXT_PAT="your-pat"

# Or prompt for input
read -s -p "Enter PAT: " PAT
export AZURE_DEVOPS_EXT_PAT=$PAT
```

### 11.2 Minimal Scopes

When creating PATs, only grant required scopes:

| Task | Required Scopes |
|------|-----------------|
| Work Items | Work Items: Read, Write |
| Pull Requests | Code: Read, Write |
| Pipelines | Build: Read, Execute |
| Wiki | Wiki: Read, Write |

### 11.3 Short-Lived Tokens

- Set expiration to 30-90 days
- Rotate regularly
- Use `System.AccessToken` in pipelines instead of personal PATs

### 11.4 Azure Pipeline Authentication

```yaml
# Use System.AccessToken in pipelines
steps:
  - script: |
      az devops configure --defaults organization=$(System.CollectionUri) project=$(System.TeamProject)
      az boards work-item update --id $(WorkItemId) --state Done
    env:
      AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)
```

---

## 12. Error Handling

### 12.1 Check Exit Codes

```bash
#!/bin/bash
az boards work-item update --id 999999 --state Done

if [ $? -ne 0 ]; then
    echo "Error: Work item update failed"
    exit 1
fi
```

### 12.2 Capture Error Output

```bash
# Capture stderr
ERROR=$(az boards work-item show --id 999999 2>&1)
if [[ $ERROR == *"does not exist"* ]]; then
    echo "Work item not found"
fi
```

### 12.3 Retry Logic

```bash
#!/bin/bash
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    az pipelines run --name "CI-Build" && break
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Retry $RETRY_COUNT of $MAX_RETRIES..."
    sleep 5
done
```

---

## 13. Performance Tips

### 13.1 Reduce API Calls

```bash
# BAD: Multiple calls
ID1=$(az repos show --repository repo1 --query id -o tsv)
ID2=$(az repos show --repository repo2 --query id -o tsv)

# GOOD: Single call with filter
az repos list --query "[?name=='repo1' || name=='repo2'].{name:name,id:id}"
```

### 13.2 Cache Results

```bash
# Cache project list for session
PROJECTS=$(az devops project list -o json)

# Reuse cached data
echo $PROJECTS | jq '.[].name'
```

### 13.3 Use --output none for Writes

```bash
# Suppress output for batch operations
for i in $(seq 1 100); do
    az boards work-item update --id $i --state Active --output none
done
```

---

## Related Memories

- `hybrid_routing.md` - When to use CLI vs MCP
- `automation_templates.md` - Reusable CLI scripts
- `wiql_queries.md` - WIQL query patterns
