# Hybrid Routing - When to Use CLI vs MCP

> **Purpose**: This memory helps Claude intelligently route Azure DevOps tasks to either CLI or MCP for optimal performance.

## Quick Decision Matrix

| Task Type | Use CLI | Use MCP | Reason |
|-----------|:-------:|:-------:|--------|
| Batch work item updates | **Y** | | CLI scripting is faster for loops |
| Single work item query | | **Y** | MCP more convenient |
| Create multiple items | **Y** | | CLI parallel execution |
| PR code review threads | | **Y** | MCP has dedicated tools |
| Create service connections | **Y** | | CLI only feature |
| Install extensions | **Y** | | CLI only feature |
| Manage pipeline variables | **Y** | | CLI only feature |
| Run pipelines | **Y** | Y | CLI better for CI/CD |
| Test plan management | | **Y** | MCP only feature |
| Security alerts | | **Y** | MCP only feature |
| Search code/wiki | | **Y** | MCP only feature |
| Create projects | **Y** | | CLI better |
| Daily standup queries | | **Y** | MCP more natural |
| Sprint reports | | **Y** | MCP queries sufficient |
| Automated scripts | **Y** | | CLI scriptable |
| Team capacity | | **Y** | MCP only feature |
| Interactive conversation | | **Y** | MCP natural language |

---

## Routing Rules for Claude

### ALWAYS Use CLI When:

1. **User says "automate", "script", or "batch"**
   - Indicates need for scriptable operations
   - CLI can be composed into scripts

2. **Creating infrastructure**
   - Projects: `az devops project create`
   - Repositories: `az repos create`
   - Service connections: `az devops service-endpoint azurerm create`

3. **Managing pipeline variables**
   - Variable groups: `az pipelines variable-group`
   - Pipeline variables: `az pipelines variable`

4. **Extension management**
   - Install: `az devops extension install`
   - Search: `az devops extension search`

5. **Part of CI/CD pipeline**
   - Running in Azure Pipelines with `$(System.AccessToken)`

6. **Multiple parallel operations**
   - Creating many work items at once
   - Updating multiple items in bulk

### ALWAYS Use MCP When:

1. **User asks a question (query-style)**
   - "What are my tasks?"
   - "Show me the sprint progress"

2. **Code review operations**
   - PR threads: `repo_list_pull_request_threads`
   - PR comments: `repo_reply_to_comment`
   - Thread resolution: `repo_resolve_comment`

3. **Test management**
   - Test plans: `testplan_list_test_plans`
   - Test cases: `testplan_create_test_case`
   - Test results: `testplan_show_test_results_from_build_id`

4. **Security monitoring**
   - Security alerts: `advsec_get_alerts`
   - Alert details: `advsec_get_alert_details`

5. **Searching content**
   - Code search: `search_code`
   - Wiki search: `search_wiki`
   - Work item search: `search_workitem`

6. **Natural language interaction**
   - Conversational requests
   - Exploratory queries

7. **Team capacity planning**
   - `work_get_team_capacity`
   - `work_update_team_capacity`

### Use BOTH When:

1. **Complex multi-step workflows**
   - CLI for creation, MCP for verification

2. **Batch operations with validation**
   - CLI for bulk updates
   - MCP to confirm results

3. **Sprint planning**
   - CLI to create iterations
   - MCP for capacity and work items

---

## CLI vs MCP Feature Comparison

### Features Available in BOTH

| Feature | CLI Command | MCP Tool |
|---------|-------------|----------|
| List projects | `az devops project list` | `core_list_projects` |
| List work items | `az boards query` | `wit_my_work_items` |
| Create work item | `az boards work-item create` | `wit_create_work_item` |
| Update work item | `az boards work-item update` | `wit_update_work_item` |
| List PRs | `az repos pr list` | `repo_list_pull_requests_by_repo_or_project` |
| Create PR | `az repos pr create` | `repo_create_pull_request` |
| Run pipeline | `az pipelines run` | `pipelines_run_pipeline` |
| List builds | `az pipelines runs list` | `pipelines_get_builds` |
| Wiki pages | `az devops wiki page` | `wiki_get_page_content` |

### CLI-Only Features

| Feature | CLI Command |
|---------|-------------|
| Create project | `az devops project create` |
| Create repository | `az repos create` |
| Delete repository | `az repos delete` |
| Import repository | `az repos import create` |
| Variable groups | `az pipelines variable-group create` |
| Pipeline variables | `az pipelines variable create` |
| Service connections | `az devops service-endpoint azurerm create` |
| Extensions | `az devops extension install` |
| Create pipeline | `az pipelines create` |
| Manage agents | `az pipelines agent list` |
| Configure defaults | `az devops configure` |

### MCP-Only Features

| Feature | MCP Tool |
|---------|----------|
| Test plans | `testplan_list_test_plans`, `testplan_create_test_plan` |
| Test cases | `testplan_create_test_case`, `testplan_update_test_case_steps` |
| Test results | `testplan_show_test_results_from_build_id` |
| Code search | `search_code` |
| Wiki search | `search_wiki` |
| Work item search | `search_workitem` |
| Security alerts | `advsec_get_alerts`, `advsec_get_alert_details` |
| PR threads | `repo_list_pull_request_threads` |
| PR thread comments | `repo_list_pull_request_thread_comments` |
| Reply to PR comment | `repo_reply_to_comment` |
| Resolve PR thread | `repo_resolve_comment` |
| Team capacity | `work_get_team_capacity`, `work_update_team_capacity` |
| Batch work item update | `wit_update_work_items_batch` |
| Work item comments | `wit_add_work_item_comment`, `wit_list_work_item_comments` |
| Add child work items | `wit_add_child_work_items` |
| Link to PR | `wit_link_work_item_to_pull_request` |
| Add artifact link | `wit_add_artifact_link` |
| Create branch | `repo_create_branch` |

---

## Routing Examples

### Example 1: Create Multiple Tasks

**User Request**: "Create 5 tasks for implementing login feature"

**Routing Decision**: **CLI** (batch operation)

**Reason**: Creating multiple items benefits from CLI's parallel execution.

**CLI Script**:
```bash
PARENT_ID=1234
TASKS=("Design UI" "Implement Backend" "Write Tests" "Add Validation" "Documentation")

for task in "${TASKS[@]}"; do
    az boards work-item create \
        --title "$task" \
        --type Task \
        --project "Relief Center" &
done
wait
echo "All tasks created"
```

---

### Example 2: Review Code Changes

**User Request**: "Review PR #45 and add comments"

**Routing Decision**: **MCP** (code review features)

**Reason**: MCP has dedicated tools for PR threads and comments.

**MCP Tools**:
```
1. repo_get_pull_request_by_id(repositoryId, pullRequestId=45)
2. repo_list_pull_request_threads(repositoryId, pullRequestId=45)
3. repo_create_pull_request_thread(repositoryId, pullRequestId=45, content="...")
4. repo_reply_to_comment(repositoryId, pullRequestId, threadId, content="...")
```

---

### Example 3: Sprint Planning

**User Request**: "Set up Sprint 15 with team capacity"

**Routing Decision**: **HYBRID**

**Reason**: CLI for iteration creation, MCP for capacity.

**Workflow**:
```
Step 1 (CLI): Create iteration
az boards iteration project create \
    --name "Sprint 15" \
    --path "\\Relief Center\\Iteration" \
    --start-date 2025-01-01 \
    --finish-date 2025-01-14

Step 2 (MCP): Set team capacity
work_get_team_capacity(project, team, iterationId)
work_update_team_capacity(project, team, teamMemberId, iterationId, activities)

Step 3 (MCP): Query work items
wit_get_work_items_for_iteration(project, iterationId)
```

---

### Example 4: Install Extensions

**User Request**: "Install the work item feature timeline extension"

**Routing Decision**: **CLI** (CLI only feature)

**CLI Command**:
```bash
# Search for extension
az devops extension search --search-query "feature timeline" --output table

# Install extension
az devops extension install \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension
```

---

### Example 5: Security Monitoring

**User Request**: "Check for security vulnerabilities in the khairgate repo"

**Routing Decision**: **MCP** (MCP only feature)

**MCP Tools**:
```
1. advsec_get_alerts(project="khairgate", repository="khairgate", alertType="Dependency")
2. advsec_get_alert_details(project, repository, alertId)
```

---

### Example 6: Configure Pipeline Variables

**User Request**: "Add a secret variable API_KEY to the production variable group"

**Routing Decision**: **CLI** (CLI only feature)

**CLI Commands**:
```bash
# Create variable group (if doesn't exist)
az pipelines variable-group create \
    --name "Production Secrets" \
    --variables placeholder=temp \
    --authorize true

# Add secret variable (prompt for value)
az pipelines variable-group variable create \
    --group-id 1 \
    --name API_KEY \
    --secret true
```

---

## Performance Considerations

### When CLI is Faster

1. **Bulk Operations**: CLI with parallel execution (`&` and `wait`)
2. **Scripted Workflows**: Pre-written scripts execute faster than multiple MCP calls
3. **Pipeline Integration**: CLI with `$(System.AccessToken)` is optimized

### When MCP is Faster

1. **Single Queries**: MCP direct API call vs CLI parsing
2. **Interactive Use**: No command composition needed
3. **Rich Responses**: MCP returns structured data directly

### Optimization Tips

1. **Use CLI defaults**: `az devops configure --defaults` to skip org/project params
2. **Batch MCP calls**: Multiple independent MCP calls can run concurrently
3. **Cache results**: Store project IDs, user GUIDs for reuse
4. **Use TSV output**: `--output tsv` for easier CLI parsing

---

## Environment Variables Reference

| Variable | Used By | Purpose |
|----------|---------|---------|
| `AZURE_DEVOPS_EXT_PAT` | CLI | PAT authentication for CLI |
| `ADO_PAT_TOKEN` | MCP | PAT authentication for MCP |
| `DEVOPS_HYBRID_MODE` | Plugin | Enables hybrid routing |

---

## Fallback Rules

1. **If CLI fails**: Fall back to MCP equivalent if available
2. **If MCP fails**: Check if CLI can accomplish the task
3. **If both fail**: Report error with troubleshooting steps
4. **If unsure**: Default to MCP for safer operations
