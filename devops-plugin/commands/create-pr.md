---
title: 'Create PR'
read_only: false
type: 'command'
description: 'Create a pull request with automatic repository ID resolution'
---

# Create Pull Request

Create a pull request in Azure DevOps with **automatic repository name-to-ID resolution**.

## 🔗 Repository Resolution Integration

**Reference**: `resolvers/repository_resolver.md`

This command automatically resolves repository names to GUIDs before creating the PR.

```
┌─────────────────────────────────────────────────────────────────┐
│           REPOSITORY RESOLUTION BEFORE PR CREATION               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User can provide:                                              │
│  • Repository NAME: "relief-center-api" → Auto-resolved         │
│  • Repository ALIAS: "relief" → Auto-resolved                   │
│  • Repository GUID: "a1b2c3d4-..." → Used directly              │
│                                                                  │
│  Claude MUST resolve to GUID before calling API!                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

```
/create-pr relief-center-api feature/login main "Add login feature"
/create-pr kg develop main "Hotfix: Fix payment bug"
/create-pr --repo relief-api --source feature/auth --target main --title "Auth implementation"
```

### Natural Language

```
"Create a PR in relief-center-api from feature/login to main"
"Create PR for my feature branch in Project Beta backend"
"Open a pull request from develop to main in the relief repo"
```

## Complete Workflow

### Step 1: Parse User Request

```javascript
// Extract components from user request
const request = {
  repository: "relief-center-api",  // Name or alias (NOT GUID yet!)
  sourceBranch: "feature/login",
  targetBranch: "main",
  title: "Feature: Login implementation"
};
```

### Step 2: Resolve Repository (MANDATORY)

```javascript
// Check if already a GUID
const GUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

if (GUID_PATTERN.test(request.repository)) {
  // Already a GUID, use directly
  repositoryId = request.repository;
} else {
  // Must resolve name/alias to GUID
  const repo = await mcp__azure-devops__repo_get_repo_by_name_or_id({
    "project": currentProject,  // From project context
    "repositoryNameOrId": request.repository
  });

  if (!repo || !repo.id) {
    // Resolution failed - show available repos
    return showAvailableRepositories(currentProject);
  }

  repositoryId = repo.id;
}
```

### Step 3: Validate Branches

```javascript
// Verify source branch exists
const sourceBranch = await mcp__azure-devops__repo_get_branch_by_name({
  "repositoryId": repositoryId,  // ← GUID!
  "branchName": request.sourceBranch
});

if (!sourceBranch) {
  return `Branch "${request.sourceBranch}" not found. Check branch name.`;
}

// Verify target branch exists
const targetBranch = await mcp__azure-devops__repo_get_branch_by_name({
  "repositoryId": repositoryId,
  "branchName": request.targetBranch
});

if (!targetBranch) {
  return `Target branch "${request.targetBranch}" not found.`;
}
```

### Step 4: Create Pull Request

```javascript
// Create PR with RESOLVED repository ID
const pr = await mcp__azure-devops__repo_create_pull_request({
  "repositoryId": repositoryId,  // ← MUST be GUID!
  "sourceRefName": `refs/heads/${request.sourceBranch}`,
  "targetRefName": `refs/heads/${request.targetBranch}`,
  "title": request.title,
  "description": request.description || "",
  "isDraft": false
});
```

### Step 5: Confirm to User

```
✅ Pull Request Created!

PR #${pr.pullRequestId}: ${pr.title}
Repository: ${repoName} (${repositoryId})
Source: ${sourceBranch} → Target: ${targetBranch}
Status: Active

🔗 Link: https://dev.azure.com/YOUR-ORG/${project}/_git/${repoName}/pullrequest/${pr.pullRequestId}

Next steps:
• Add reviewers: "add @mahmoud as reviewer to PR #${pr.pullRequestId}"
• Link work item: "link PR #${pr.pullRequestId} to #1234"
• Set auto-complete: "set auto-complete on PR #${pr.pullRequestId}"
```

## Example Flows

### Example 1: Using Repository Name

**User**: "Create PR in relief-center-api from feature/login to main titled 'Add login feature'"

**Claude**:
```
📁 Project: Project Alpha

Resolving repository "relief-center-api"...
✅ Resolved: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Validating branches...
✅ Source: feature/login exists
✅ Target: main exists

Creating pull request...
```

```javascript
mcp__azure-devops__repo_create_pull_request({
  "repositoryId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sourceRefName": "refs/heads/feature/login",
  "targetRefName": "refs/heads/main",
  "title": "Add login feature"
})
```

```
✅ Pull Request Created!

PR #123: Add login feature
Repository: relief-center-api
Source: feature/login → Target: main
Status: Active

🔗 https://dev.azure.com/YOUR-ORG/Relief%20Center/_git/relief-center-api/pullrequest/123
```

### Example 2: Using Alias

**User**: "Create PR from develop to main in kg"

**Claude**:
```
📁 Project: Project Beta

Resolving repository "kg"...
Alias "kg" → "project-beta"
✅ Resolved: b2c3d4e5-f6a7-8901-bcde-f23456789012

Creating pull request...
```

### Example 3: Repository Not Found

**User**: "Create PR in myrepo from feature to main"

**Claude**:
```
📁 Project: Project Alpha

Resolving repository "myrepo"...
⚠️ Repository "myrepo" not found in Project Alpha.

Available repositories:
• relief-center-api (aliases: relief, relief-api)
• relief-center-web (aliases: relief-web)
• relief-center-docs

Please specify the correct repository name.
```

### Example 4: With Work Item Link

**User**: "Create PR for task #1234 in relief-center-api from feature/auth to develop"

**Claude**:
```
📁 Project: Project Alpha

Resolving repository...
✅ Resolved: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Creating pull request linked to #1234...
```

```javascript
// Create PR
const pr = await mcp__azure-devops__repo_create_pull_request({
  "repositoryId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sourceRefName": "refs/heads/feature/auth",
  "targetRefName": "refs/heads/develop",
  "title": "Feature: Auth implementation",
  "workItems": "1234"  // Link to work item
});
```

### Example 5: Draft PR

**User**: "Create draft PR in relief from feature/wip to main"

**Claude**:
```javascript
mcp__azure-devops__repo_create_pull_request({
  "repositoryId": "a1b2c3d4-...",  // Resolved from "relief"
  "sourceRefName": "refs/heads/feature/wip",
  "targetRefName": "refs/heads/main",
  "title": "WIP: Work in progress",
  "isDraft": true
});
```

```
✅ Draft Pull Request Created!

PR #125: WIP: Work in progress
Status: Draft (not ready for review)
```

## Advanced Options

### Add Reviewers

```javascript
// After PR creation, add reviewers
const reviewerId = await resolveUserIdentity("mahmoud");

mcp__azure-devops__repo_update_pull_request_reviewers({
  "repositoryId": repositoryId,
  "pullRequestId": pr.pullRequestId,
  "reviewerIds": [reviewerId],
  "action": "add"
});
```

### Set Auto-Complete

```javascript
mcp__azure-devops__repo_update_pull_request({
  "repositoryId": repositoryId,
  "pullRequestId": pr.pullRequestId,
  "autoComplete": true,
  "deleteSourceBranch": true,
  "mergeStrategy": "Squash"
});
```

### Link Work Items

```javascript
mcp__azure-devops__wit_link_work_item_to_pull_request({
  "projectId": projectId,  // Must be GUID!
  "repositoryId": repositoryId,  // Must be GUID!
  "pullRequestId": pr.pullRequestId,
  "workItemId": 1234
});
```

## Error Handling

### Repository Resolution Failed

```
⚠️ Could not resolve repository "{name}".

Troubleshooting:
1. Check spelling of repository name
2. Verify repository exists in project "{project}"
3. Check you have access to the repository

Available repositories:
• repo-1
• repo-2
```

### Branch Not Found

```
⚠️ Branch "{branch}" not found in repository "{repo}".

Available branches:
• main
• develop
• feature/existing-feature

Tip: Use "list branches in {repo}" to see all branches.
```

### Permission Denied

```
⚠️ Permission denied to create PR in "{repo}".

You need "Contribute to pull requests" permission.
Contact your repository administrator.
```

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              CREATE PR QUICK REFERENCE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REQUIRED:                                                      │
│  • Repository (name, alias, or GUID)                            │
│  • Source branch                                                │
│  • Target branch                                                │
│  • Title                                                        │
│                                                                  │
│  OPTIONAL:                                                      │
│  • Description                                                  │
│  • Work item IDs to link                                        │
│  • isDraft (true/false)                                         │
│  • Reviewers                                                    │
│                                                                  │
│  RESOLUTION ORDER:                                              │
│  1. Resolve repository name → GUID                              │
│  2. Validate source branch exists                               │
│  3. Validate target branch exists                               │
│  4. Create PR with GUID                                         │
│                                                                  │
│  NEVER pass repository NAME to repositoryId!                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Related Commands

| Command | Description |
|---------|-------------|
| `/list-prs` | List pull requests in a repository |
| `/review-pr` | Review and comment on a PR |
| `/merge-pr` | Complete/merge a pull request |
| `/list-branches` | List branches in a repository |
| `/create-branch` | Create a new branch |

---

*Part of DevOps Plugin v3.0*
*Repository Resolution: Enabled*
*Always resolve names to GUIDs before API calls!*
