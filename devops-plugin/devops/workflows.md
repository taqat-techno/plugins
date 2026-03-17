# Skill-Handled Workflows Reference

This file contains the full workflow instructions for operations handled directly by the devops skill through natural language detection. These were previously standalone commands and are now triggered contextually.

---

## Profile-Aware Preamble (All Workflows)

Before executing any workflow below, check for the user's profile:

```
1. Try to Read ~/.claude/devops.md
2. If found → parse YAML frontmatter:
   - currentUser = identity (name, email, guid)
   - teamLookup = Map(alias → {name, email, guid}) from teamMembers
   - Include "me"/"myself" → current user
   - defaultProject = profile.defaultProject
3. If NOT found → fall back to API-based resolution
```

**Impact on workflows**:
- **Update Work Item**: "assign to me" resolves instantly from profile
- **Add Comment**: @mentions resolve from teamMembers cache before API
- **Switch Project**: defaultProject is pre-set from profile
- **Create PR**: Use profile's project repos for repository resolution
- **All workflows**: currentUser identity available without API call

---

## Workflow 1: Update Work Item

**Trigger patterns**: "mark #ID as done", "resolve bug #ID", "close #ID", "change state of #ID", "update #ID", "move #ID to Active"

**Guards**: `guards/write_operation_guard.md`, `validators/state_transition_validator.md`, `errors/error_recovery.md`

### Two-Layer Protection System

1. **Layer 1 — Proactive Prevention**: Check requirements BEFORE attempting updates
2. **Layer 2 — Reactive Recovery**: Transform any errors into actionable guidance

### Pre-Flight Validation (MANDATORY)

```
+---------------------------------------------------------------+
|              NEVER UPDATE STATE WITHOUT VALIDATION              |
+---------------------------------------------------------------+
|                                                                |
|  BEFORE changing state:                                       |
|  1. FETCH work item to check current state and fields         |
|  2. LOOKUP required fields for the transition                 |
|  3. CHECK if required fields are populated                    |
|  4. ASK user for missing values (if any)                      |
|  5. ONLY THEN execute the update                              |
|                                                                |
+---------------------------------------------------------------+
```

### Step 0: Role-Based Permission Check (MANDATORY)

Before ANY state transition:

```
1. Load profile from ~/.claude/devops.md
2. Read statePermissions.{WorkItemType}
3. Check: is "{currentState} → {targetState}" in allowed[]?
   - YES → proceed to Step 0.5
   - BLOCKED → show blockedMessage + suggest correct role
   - NO PROFILE → warn and allow (graceful fallback)

Reference: data/state_permissions.json for complete role→permission mapping
```

### Step 0.5: Profile-Aware Assignment

If the update includes an assignment (e.g., "assign to me", "assign to mahmoud"):

```
1. Check profile cache:
   - "me"/"myself" → use currentUser.guid from profile (INSTANT)
   - "@name" or "name" → check teamLookup by alias (INSTANT if cached)
2. If not in cache → fall back to core_get_identity_ids API
3. Include the assignment field in the update payload:
   { "path": "/fields/System.AssignedTo", "value": resolvedEmail }
```

### Step 1: Fetch Current Work Item

```javascript
mcp__azure-devops__wit_get_work_item({
  "id": workItemId,
  "project": currentProject,
  "fields": [
    "System.Id", "System.Title", "System.State", "System.WorkItemType",
    "Microsoft.VSTS.Scheduling.OriginalEstimate",
    "Microsoft.VSTS.Scheduling.CompletedWork",
    "Microsoft.VSTS.Scheduling.RemainingWork",
    "Microsoft.VSTS.Common.ResolvedReason"
  ]
})
```

### Step 2: Check Required Fields

**Task (In Progress → Done)**:
- Required: `OriginalEstimate`, `CompletedWork`
- Auto-set: `RemainingWork = 0`

**Bug (In Progress → Resolved)**:
- Required: `ResolvedReason` (default: "Fixed")
- Valid reasons: Fixed, As Designed, Cannot Reproduce, Deferred, Duplicate, Not a Bug, Obsolete

**PBI (In Progress → Ready For QC → Done)**:
- **BLOCKED** if current state is "In Progress"
- Must go through "Ready For QC" first
- Required path: In Progress → Ready For QC → Done

**User Story (New → Committed → Done)**:
- Must go through "Committed" first
- Required path: New → Committed → Done

**Enhancement (Committed → Done → Closed)**:
- Must go through "Committed" before "Done"
- Only PM/Lead can transition Done → Closed

### Step 3: Handle Missing Fields

If Task -> Done and missing hours:
```
Cannot mark task #1234 as Done yet.

Missing Required Fields:
- Original Estimate (hours): Not set
- Completed Work (hours): Not set

Please provide:
1. How many hours did you estimate for this task?
2. How many hours did you actually spend?

I'll automatically set Remaining Work to 0.
```

If PBI -> Done from In Progress:
```
Cannot mark PBI #1000 as Done directly.

Reason: PBIs must pass through "Ready For QC" before Done.
Current State: In Progress
Required Path: In Progress -> Ready For QC -> Done

Would you like me to:
1. Move to "Ready For QC" now
2. Move through both states (Ready For QC -> Done)
```

If User Story -> Done from New:
```
Cannot mark User Story #1000 as Done directly.

Reason: User Stories must pass through "Committed" before Done.
Current State: New
Required Path: New -> Committed -> Done

Would you like me to:
1. Move to "Committed" now
2. Move through both states (Committed -> Done)
```

### Step 3.5: MANDATORY Confirmation (WRITE OPERATION GATE)

```
READY TO UPDATE: #{id} {title}
---------------------------------
State:     {currentState} -> {newState}
Fields:    {list of fields being set with values}
Hours:     Est: {orig}h / Done: {comp}h (if applicable)

Proceed? (yes/no)
```

### Step 4: Execute Update

```javascript
mcp__azure-devops__wit_update_work_item({
  "id": workItemId,
  "updates": [
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },
    { "path": "/fields/System.State", "value": "Done" }
  ]
})
```

### Step 5: Auto-Prompt Time Logging

When state changes to Done/Closed/Resolved, offer to log hours in work tracker:
1. Note the CompletedWork hours
2. Ask: "Would you like me to log {hours}h for #{id} in your work tracker?"
3. If agreed: update `~/.claude/work-tracker-data.json` timeLog entry
4. Run compliance check and report

### Step 5.5: [Dev-Internal-fix] QC FYI Check

When completing a `[Dev-Internal-fix]` Task, verify that QC was notified:

```
1. Check if Task title starts with "[Dev-Internal-fix]"
2. If YES:
   a. Check if a FYI comment was already posted (search comments for "FYI: Developer-identified fix")
   b. If NO comment found:
      - Find QC member from profile (role = "tester" or "qa")
      - Post FYI mention: "@{QC} FYI: [Dev-Internal-fix] completed. #{id} - {title}"
   c. Ask: "Does this fix change any user-facing behavior?"
      - If YES → Post ATTENTION escalation to QA Lead for regression assessment
      - If NO → Done, FYI was sufficient
3. If NOT a [Dev-Internal-fix] Task → skip this step
```

### State Machine Diagrams (TaqaTechno Scrum Process)

**Task**: To Do → In Progress → Done → Closed → Removed
**Bug**: New → Approved → In Progress → Resolved → Done → Closed → Removed (with Return loop: Resolved ↔ Return ↔ In Progress)
**PBI**: New → Approved → Committed → In Progress → Ready For QC → Done → Removed (with Return loop: Ready For QC ↔ Return ↔ In Progress)
**User Story**: New → Committed → Done
**Enhancement**: New → Committed → Done → Closed (with Return loop: Committed ↔ Return)

### Return Loop Workflow (Bug, PBI, Enhancement)

When QA returns an item:

```
1. QA transitions to "Return" state
2. MANDATORY: Add comment explaining WHY it's being returned
3. Developer sees Return in their /workday dashboard
4. Developer moves Return → In Progress (Bug/PBI) or Return → Committed (Enhancement)
5. Developer fixes the issue
6. Developer moves back to Resolved (Bug) / Ready For QC (PBI) / Done (Enhancement)
7. QA re-verifies
```

Return comment format:
```
"RETURNED by {QA_NAME}: {reason}"
```

### Return Loop State Details

**Bug Return Loop**:
```
In Progress → Resolved → (QA reviews)
                           ↓
                        Return ← QA posts mandatory comment
                           ↓
                        In Progress → (Developer fixes) → Resolved → (QA re-verifies)
```

**PBI Return Loop**:
```
In Progress → Ready For QC → (QA reviews)
                                ↓
                             Return ← QA posts mandatory comment
                                ↓
                             In Progress → (Developer fixes) → Ready For QC → (QA re-verifies)
```

**Enhancement Return Loop**:
```
Committed → (QA reviews)
               ↓
            Return ← QA posts mandatory comment
               ↓
            Committed → (Developer fixes) → Done
```

### Error Recovery (Layer 2)

| Error Code | User Message | Recovery Action |
|------------|-------------|-----------------|
| `VS403507` | "Task needs {field} to be marked {state}" | Ask for field value, retry |
| `TF401347` | "{Type} must go through {intermediate}" | Offer two-step transition |
| `TF401019` | "Work item #{id} not found" | Suggest searching |
| `VS403403` | "Permission denied" | Show required PAT scopes |
| `VS403323` | "Update conflict" | Refresh and retry |

---

## Workflow 2: Add Comment

**Trigger patterns**: "comment on #ID", "tell @name about #ID", "add note to #ID", "mention @name on #ID"

**Guards**: `guards/write_operation_guard.md`, `processors/mention_processor.md`

### CRITICAL: No Fake Mentions

```
+---------------------------------------------------------------+
|           ABSOLUTE RULE: VALIDATE ALL MENTIONS                 |
+---------------------------------------------------------------+
|                                                                |
|  BEFORE posting any comment with @mentions:                   |
|                                                                |
|  1. RESOLVE every @mention via API                            |
|  2. VALIDATE each resolution returned a GUID                  |
|  3. CONVERT to HTML format                                    |
|                                                                |
|  IF ANY mention fails:                                        |
|  - DO NOT post the comment                                    |
|  - DO NOT use plain text @name                                |
|  - ASK user for clarification                                 |
|  - SUGGEST known team members                                 |
|                                                                |
|  Plain text "@name" does NOT notify anyone!                   |
|                                                                |
+---------------------------------------------------------------+
```

### Step 1: Extract Mentions

```javascript
const pattern = /@([a-zA-Z0-9._-]+)/g;
const mentions = text.match(pattern); // ["mahmoud", "eslam"]
```

### Step 2: Resolve Each Mention via API

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"
})
```

### Step 3: Handle Resolution Results

**All resolved**: Format as HTML and post
**Any failed**: DO NOT POST. Ask user for clarification, suggest known team members.

### Step 3.5: MANDATORY Confirmation (WRITE OPERATION GATE)

```
READY TO ADD COMMENT: #{workItemId}
------------------------------------
Target:    #{id} - {workItemTitle}
Content:   {first 150 chars of comment}...
Mentions:  {resolved @mentions or "None"}

Proceed? (yes/no)
```

### Step 4: Post with HTML Format

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": currentProject,
  "workItemId": workItemId,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:GUID\">@Display Name</a> please review.",
  "format": "html"
})
```

### HTML Mention Format

```html
<a href="#" data-vss-mention="version:2.0,guid:GUID_HERE">@Display Name</a>
```

---

## Workflow 3: Switch Project

**Trigger patterns**: "switch to PROJECT", "use PROJECT", "work on PROJECT", "change project to PROJECT", "set project PROJECT"

**Guards**: None (read-only operation)

### Project Aliases

Users can use short names or aliases. The skill resolves them from `data/project_defaults.json`.

### Workflow

1. **Parse input**: Extract project name or alias
2. **Resolve alias**: Check against project_defaults.json aliases (case-insensitive)
3. **Validate**: Optionally verify project exists via `core_list_projects`
4. **Update context**: Set new default project for session
5. **Confirm**:
```
Switched project context

Previous: Project Beta
Current: Project Alpha

All subsequent commands will use Project Alpha.
```

### Context Rules

- **Session-based**: Context persists throughout conversation
- **Explicit switch**: "switch to X" changes permanently
- **One-time override**: "tasks in Project Gamma" doesn't change default
- **Multi-project**: "all my tasks across all projects" queries everything

### Unknown Project

```
Couldn't find a project matching "xyz".

Available projects:
- Project Alpha (aliases: relief, rc, disaster)
- Project Beta (aliases: kg, beneficiary)
- Project Gamma (aliases: property, pm)

Please specify the correct project name or alias.
```

---

## Workflow 4: Build Status

**Trigger patterns**: "build status", "any failing builds?", "check CI", "pipeline health", "recent builds", "check pipelines"

**Guards**: None (read-only)

### Workflow

1. List recent builds (last 10)
2. Show status, duration, and result
3. Highlight any failures with error details
4. Provide quick actions for failed builds

### Output Format

```markdown
## Recent Builds

### Summary
- Succeeded: X
- Failed: Y
- In Progress: Z

### Build List

| # | Pipeline | Status | Duration | Branch | Triggered |
|---|----------|--------|----------|--------|-----------|
| 789 | CI-Main | Succeeded | 5m 23s | main | PR merge |
| 788 | CI-Main | Failed | 2m 15s | feature/x | Push |

### Failed Build Details

Build #788 failed with:
- 3 test failures in AuthenticationTests
- Error: "Expected 200 but got 401"

Quick Actions:
1. View full logs
2. View test results
3. Re-run build
4. Create bug for failure
```

---

## Workflow 5: Create PR

**Trigger patterns**: "create PR from BRANCH to BRANCH", "open pull request", "PR for my feature branch", "create PR in REPO"

**Guards**: `guards/write_operation_guard.md`, `resolvers/repository_resolver.md`

### Repository Resolution (MANDATORY)

```
+---------------------------------------------------------------+
|           REPOSITORY RESOLUTION BEFORE PR CREATION             |
+---------------------------------------------------------------+
|                                                                |
|  User can provide:                                            |
|  - Repository NAME: "relief-center-api" -> Auto-resolved      |
|  - Repository ALIAS: "relief" -> Auto-resolved                |
|  - Repository GUID: "a1b2c3d4-..." -> Used directly           |
|                                                                |
|  Claude MUST resolve to GUID before calling API!              |
|                                                                |
+---------------------------------------------------------------+
```

### Workflow

#### Step 1: Parse Request
Extract repository, source branch, target branch, title.

#### Step 2: Resolve Repository

```javascript
const GUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

if (!GUID_PATTERN.test(request.repository)) {
  const repo = await mcp__azure-devops__repo_get_repo_by_name_or_id({
    "project": currentProject,
    "repositoryNameOrId": request.repository
  });
  repositoryId = repo.id;
}
```

#### Step 3: Validate Branches

```javascript
const sourceBranch = await mcp__azure-devops__repo_get_branch_by_name({
  "repositoryId": repositoryId,
  "branchName": request.sourceBranch
});
```

#### Step 3.5: MANDATORY Confirmation

```
READY TO CREATE: Pull Request
------------------------------
Title:     {prTitle}
Repo:      {repoName} ({repositoryId})
Source:    {sourceBranch}
Target:    {targetBranch}
Draft:     {isDraft}
Work Items: {linked IDs or "None"}

Proceed? (yes/no)
```

#### Step 4: Create PR

```javascript
const pr = await mcp__azure-devops__repo_create_pull_request({
  "repositoryId": repositoryId,
  "sourceRefName": `refs/heads/${request.sourceBranch}`,
  "targetRefName": `refs/heads/${request.targetBranch}`,
  "title": request.title,
  "isDraft": false
});
```

#### Step 5: Confirm

```
Pull Request Created!

PR #123: Add login feature
Repository: relief-center-api
Source: feature/login -> Target: main
Status: Active

Link: https://dev.azure.com/YOUR-ORG/Project/_git/repo/pullrequest/123

Next steps:
- Add reviewers: "add @mahmoud as reviewer to PR #123"
- Link work item: "link PR #123 to #1234"
- Set auto-complete: "set auto-complete on PR #123"
```

### Advanced Options

**Add Reviewers**: `repo_update_pull_request_reviewers`
**Set Auto-Complete**: `repo_update_pull_request` with autoComplete, deleteSourceBranch, mergeStrategy
**Link Work Items**: `wit_link_work_item_to_pull_request`

---

## Workflow 6: CI/CD Setup

**Trigger patterns**: "set up CI/CD", "generate GitHub Actions", "CI pipeline for Odoo", "create deployment workflow"

**Guards**: `guards/write_operation_guard.md`

### Information to Gather

1. **Deployment target**: Self-hosted server OR Odoo.sh
2. **Odoo version(s)**: 14, 15, 16, 17, 18, 19
3. **Repo structure**: Monorepo or single-project
4. **Notification channel**: ntfy.sh, Slack, or none

### Case A: Odoo.sh (Custom Addons Only)

Generate **2 files**:
1. `.github/workflows/quality-gate.yml` — Lint, Bandit security scan, XML validation, manifest check
2. `odoo_tests.cfg` — Test enable configuration

Odoo.sh automatically handles tests and deployment.

### Case B: Self-Hosted Server

Generate **4 workflow files**:
1. `.github/workflows/1-lint.yml` — Pre-commit, Bandit, XML, manifest validation
2. `.github/workflows/2-test.yml` — Automated tests with PostgreSQL service, changed module detection, coverage
3. `.github/workflows/4-deploy-staging.yml` — SSH deploy to staging on push to main, with DB backup and health check
4. `.github/workflows/5-deploy-production.yml` — SSH deploy to production on tag push, with backup and rollback capability

### ntfy.sh Notification Step

Add to deploy jobs for push notification on completion/failure:
```yaml
- name: Notify via ntfy
  if: always()
  run: |
    STATUS="${{ job.status }}"
    curl -s -H "Title: Odoo Deploy $STATUS" -d "Branch: ${{ github.ref_name }}" https://ntfy.sh/${{ secrets.NTFY_TOPIC }}
```

### Output

After generation, confirm with user:
- Files generated in `.github/workflows/`
- GitHub Secrets needed
- Required GitHub Environment setup
- First-run checklist

---

*Part of DevOps Plugin v4.0 — Skill-Handled Workflows*
*These workflows are triggered by natural language, not slash commands.*
*Previously: /update-workitem, /add-comment, /switch-project, /build-status, /create-pr, /ci-setup*
