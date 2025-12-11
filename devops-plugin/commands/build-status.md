---
title: 'Build Status'
read_only: true
type: 'command'
description: 'Check recent build status from Azure DevOps pipelines'
---

# Build Status

Check the status of recent builds and pipelines.

## Instructions

1. List recent builds (last 10)
2. Show status, duration, and result
3. Highlight any failures
4. Provide quick actions for failed builds

## Output Format

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
| 787 | Deploy-Staging | Succeeded | 8m 10s | main | Manual |

### Failed Builds

#### Build #788 - CI-Main
- **Error**: Test failure in UserAuthTests
- **Branch**: feature/x
- **Triggered by**: Ahmed

Quick Actions:
1. View full logs
2. View test results
3. Re-run build
4. Create bug for failure
```

## Example

```
User: Build status

Response:
## Recent Builds (Last 24 hours)

### Summary
- Succeeded: 8
- Failed: 2
- In Progress: 1

### Latest Builds

| Build | Pipeline | Status | Duration | Branch |
|-------|----------|--------|----------|--------|
| #789 | CI-Main | Succeeded | 5m 23s | main |
| #788 | CI-Main | Failed | 2m 15s | feature/login |
| #787 | Deploy-Prod | Succeeded | 12m 45s | main |

### Failed Build Details

Build #788 failed with:
- 3 test failures in AuthenticationTests
- Error: "Expected 200 but got 401"

Would you like to:
1. View full logs for #788
2. Re-run build #788
3. Create bug for this failure
```
