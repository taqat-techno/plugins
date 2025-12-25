---
title: 'Repository Resolver'
read_only: false
type: 'resolver'
description: 'Automatically resolve repository names to IDs for PR and branch operations'
---

# Repository Name to ID Resolver

## Purpose

Azure DevOps APIs require repository **GUIDs** (not names) for:
- Creating pull requests
- Creating branches
- Listing branches
- Getting repository details

This resolver automatically converts user-friendly repository names to GUIDs.

## Problem Solved

```
User: "Create PR in relief-center-api"
Claude: repo_create_pull_request({ repositoryId: "relief-center-api", ... })
Error: Repository not found (because "relief-center-api" is a NAME, not a GUID)
```

---

## Resolution Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│              REPOSITORY RESOLUTION WORKFLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Input: "relief-center-api"                                │
│                                                                  │
│  STEP 1: Is it already a GUID?                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GUID Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      │    │
│  │                                                         │    │
│  │ if (isGUID(input)) → Use directly                       │    │
│  │ else → Continue to Step 2                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: Check session cache                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ if (cache[project][name]) → Return cached GUID          │    │
│  │ else → Continue to Step 3                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: Query Azure DevOps API                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ // Option A: Direct lookup by name                      │    │
│  │ repo_get_repo_by_name_or_id({                           │    │
│  │   project: currentProject,                              │    │
│  │   repositoryNameOrId: "relief-center-api"               │    │
│  │ })                                                      │    │
│  │                                                         │    │
│  │ // Option B: List and match (if direct fails)           │    │
│  │ repos = repo_list_repos_by_project({                    │    │
│  │   project: currentProject                               │    │
│  │ })                                                      │    │
│  │ match = repos.find(r => r.name === input)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: Handle resolution result                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ if (found) {                                            │    │
│  │   cache[project][name] = repo.id                        │    │
│  │   return repo.id                                        │    │
│  │ } else {                                                │    │
│  │   → Fuzzy match                                         │    │
│  │   → Show suggestions                                    │    │
│  │ }                                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Tools for Resolution

### Primary: Direct Lookup

```javascript
// Best method - direct lookup by name
mcp__azure-devops__repo_get_repo_by_name_or_id({
  "project": "Relief Center",
  "repositoryNameOrId": "relief-center-api"
})
```

**Response**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "relief-center-api",
  "url": "https://dev.azure.com/TaqaTechno/Relief%20Center/_git/relief-center-api",
  "defaultBranch": "refs/heads/main",
  "size": 12345678,
  "remoteUrl": "https://TaqaTechno@dev.azure.com/TaqaTechno/Relief%20Center/_git/relief-center-api"
}
```

### Fallback: List and Match

```javascript
// If direct lookup fails, list all repos
mcp__azure-devops__repo_list_repos_by_project({
  "project": "Relief Center",
  "repoNameFilter": "relief"  // Optional filter
})
```

**Response**:
```json
{
  "value": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "relief-center-api",
      "defaultBranch": "refs/heads/main"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "name": "relief-center-web",
      "defaultBranch": "refs/heads/main"
    }
  ]
}
```

---

## GUID Detection

```javascript
// Pattern to detect if input is already a GUID
const GUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isGUID(input) {
  return GUID_PATTERN.test(input);
}

// Examples:
isGUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")  // true
isGUID("relief-center-api")                      // false
isGUID("A1B2C3D4-E5F6-7890-ABCD-EF1234567890")  // true (case-insensitive)
```

---

## Resolution Strategies

### Strategy 1: Exact Match

```javascript
// Case-insensitive exact match
const match = repos.find(r =>
  r.name.toLowerCase() === input.toLowerCase()
);
```

### Strategy 2: Fuzzy Match (Contains)

```javascript
// If exact fails, try contains
const fuzzyMatches = repos.filter(r =>
  r.name.toLowerCase().includes(input.toLowerCase())
);

// Example:
// Input: "relief-api"
// Matches: "relief-center-api", "relief-api-v2"
```

### Strategy 3: Alias Resolution

```javascript
// Check known aliases
const aliases = {
  "relief": "relief-center-api",
  "relief-api": "relief-center-api",
  "khairgate": "khairgate-backend",
  "kg-backend": "khairgate-backend"
};

const resolvedName = aliases[input.toLowerCase()] || input;
```

---

## Example Flows

### Example 1: Direct Resolution (Success)

**User**: "Create PR in relief-center-api from feature/login to main"

**Claude**:
```
Resolving repository "relief-center-api"...

Step 1: Not a GUID, need to resolve
Step 2: Calling API...
```

```javascript
mcp__azure-devops__repo_get_repo_by_name_or_id({
  "project": "Relief Center",
  "repositoryNameOrId": "relief-center-api"
})
// Returns: { id: "a1b2c3d4-...", name: "relief-center-api" }
```

```
Step 3: ✅ Resolved: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Creating PR...
```

```javascript
mcp__azure-devops__repo_create_pull_request({
  "repositoryId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  // ← GUID!
  "sourceRefName": "refs/heads/feature/login",
  "targetRefName": "refs/heads/main",
  "title": "Feature: Login implementation"
})
```

### Example 2: Fuzzy Match (Multiple Results)

**User**: "List branches in relief repo"

**Claude**:
```
Resolving repository "relief"...

Step 1: Not a GUID, need to resolve
Step 2: Searching for "relief"...
```

```javascript
mcp__azure-devops__repo_list_repos_by_project({
  "project": "Relief Center",
  "repoNameFilter": "relief"
})
// Returns: 2 matches
```

```
Found multiple repositories matching "relief":

1. relief-center-api (a1b2c3d4-...)
2. relief-center-web (b2c3d4e5-...)

Which repository did you mean?
```

### Example 3: Not Found

**User**: "Create branch in myrepo"

**Claude**:
```
Resolving repository "myrepo"...

Step 1: Not a GUID, need to resolve
Step 2: Searching for "myrepo"...
```

```javascript
mcp__azure-devops__repo_list_repos_by_project({
  "project": "Relief Center"
})
// No match found
```

```
⚠️ Repository "myrepo" not found in Relief Center.

Available repositories:
• relief-center-api
• relief-center-web
• relief-center-docs

Please specify the correct repository name.
```

### Example 4: Already a GUID (Bypass)

**User**: "List branches in a1b2c3d4-e5f6-7890-abcd-ef1234567890"

**Claude**:
```
Input is already a GUID. Using directly.
```

```javascript
mcp__azure-devops__repo_list_branches_by_repo({
  "repositoryId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
})
```

---

## Session Cache Structure

```javascript
// Cache stored during conversation session
const repositoryCache = {
  "Relief Center": {
    // name -> { id, defaultBranch }
    "relief-center-api": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "defaultBranch": "refs/heads/main"
    },
    "relief-center-web": {
      "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "defaultBranch": "refs/heads/main"
    }
  },
  "KhairGate": {
    "khairgate-backend": {
      "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
      "defaultBranch": "refs/heads/develop"
    }
  }
};

// Cache benefits:
// 1. Faster resolution on subsequent calls
// 2. Reduced API calls
// 3. Default branch info available
```

---

## Integration with Commands

### Required for These Operations

| Operation | API Tool | Needs Repository ID |
|-----------|----------|---------------------|
| Create PR | `repo_create_pull_request` | ✅ Yes |
| List PRs | `repo_list_pull_requests_by_repo_or_project` | ✅ Yes |
| Get PR | `repo_get_pull_request_by_id` | ✅ Yes |
| Create Branch | `repo_create_branch` | ✅ Yes |
| List Branches | `repo_list_branches_by_repo` | ✅ Yes |
| Get Branch | `repo_get_branch_by_name` | ✅ Yes |
| Search Commits | `repo_search_commits` | ✅ Yes |
| Link Work Item to PR | `wit_link_work_item_to_pull_request` | ✅ Yes |

### Resolution Wrapper Pattern

```javascript
// Before any repo operation:
async function withResolvedRepository(repoNameOrId, project, operation) {
  // Step 1: Check if GUID
  if (isGUID(repoNameOrId)) {
    return operation(repoNameOrId);
  }

  // Step 2: Check cache
  if (repositoryCache[project]?.[repoNameOrId]) {
    return operation(repositoryCache[project][repoNameOrId].id);
  }

  // Step 3: Resolve via API
  const repo = await resolveRepository(repoNameOrId, project);

  if (!repo) {
    throw new Error(`Repository "${repoNameOrId}" not found`);
  }

  // Step 4: Cache and execute
  repositoryCache[project] = repositoryCache[project] || {};
  repositoryCache[project][repoNameOrId] = {
    id: repo.id,
    defaultBranch: repo.defaultBranch
  };

  return operation(repo.id);
}
```

---

## Known Repository Mappings

Pre-configured mappings for TaqaTechno projects:

| Project | Repository Name | Common Aliases |
|---------|-----------------|----------------|
| Relief Center | relief-center-api | relief, relief-api, rc-api |
| Relief Center | relief-center-web | relief-web, rc-web |
| KhairGate | khairgate-backend | khairgate, kg, kg-backend |
| KhairGate | khairgate-frontend | kg-frontend, kg-web |
| Property Management | property-management | property, pm |
| TAQAT HR | taqat-hr | hr, taqat-hr-backend |
| Beneshty | beneshty | children |
| OkSouq | oksouq | souq, marketplace |
| Arcelia | arcelia | arcelia-crm, crm |
| Ittihad Club | ittihadclub | ittihad, club |

---

## Error Handling

### Resolution Failed

```
If repository cannot be resolved:

⚠️ Could not find repository "{input}" in {project}.

Possible reasons:
1. Repository name is misspelled
2. Repository doesn't exist in this project
3. You don't have access to this repository

Available repositories in {project}:
• repo-1
• repo-2
• repo-3

Please specify the correct name or use the full GUID.
```

### API Error

```
If API call fails:

⚠️ Could not resolve repository due to connection issue.

Would you like me to:
1. Retry the lookup
2. Use cached repositories (if available)
3. Enter GUID manually
```

### Permission Error

```
If user lacks access:

⚠️ You don't have access to repository "{name}".

Repositories you have access to:
• accessible-repo-1
• accessible-repo-2

Please check your permissions or contact your administrator.
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              REPOSITORY RESOLUTION QUICK REFERENCE              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT TYPES:                                                   │
│  • GUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890 → Use directly    │
│  • Name: relief-center-api → Resolve via API                    │
│  • Alias: relief → Resolve to relief-center-api                 │
│                                                                  │
│  RESOLUTION ORDER:                                              │
│  1. Is GUID? → Use directly                                     │
│  2. In cache? → Use cached GUID                                 │
│  3. Direct lookup → repo_get_repo_by_name_or_id                 │
│  4. List + match → repo_list_repos_by_project                   │
│  5. Fuzzy match → Partial name matching                         │
│  6. Not found → Show suggestions                                │
│                                                                  │
│  CACHE:                                                         │
│  • Per project, per session                                     │
│  • Stores GUID + default branch                                 │
│  • Expires on session end                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Part of DevOps Plugin v3.0*
*Repository Resolver: Enabled*
*Always resolve names to GUIDs before API calls!*
