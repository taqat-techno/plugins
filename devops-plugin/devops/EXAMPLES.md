# Azure DevOps - Usage Examples

Real-world examples of using the DevOps skill for common scenarios.

## Table of Contents

1. [Daily Standup](#daily-standup)
2. [Sprint Planning](#sprint-planning)
3. [Code Review Workflow](#code-review-workflow)
4. [Bug Triage](#bug-triage)
5. [Build Monitoring](#build-monitoring)
6. [Release Management](#release-management)

---

## Daily Standup

### Scenario
Prepare notes for daily standup meeting.

### User Request
```
"Prepare my standup notes"
```

### Claude's Approach
1. Query work items assigned to user
2. Identify items changed in last 2 days
3. Categorize by state (completed, in progress, blocked)
4. Format as standup notes

### Expected Output
```markdown
## Daily Standup - December 11, 2025

### Yesterday (Completed)
- [Bug] #1234: Fixed authentication timeout
  - Merged PR #45, deployed to staging
- [Task] #1235: Updated API documentation
  - Added new endpoint docs

### Today (In Progress)
- [Task] #1236: Implement password reset flow
  - 60% complete, working on email template
- [Bug] #1237: Investigate payment errors
  - Reproducing issue locally

### Blockers
- Need access to production logs for #1237
- Waiting for design review on #1238

### Notes
- PR #46 ready for review
- Meeting with DevOps team at 2 PM
```

---

## Sprint Planning

### Scenario
Plan work for upcoming sprint.

### User Request
```
"Help me plan Sprint 16"
```

### Claude's Approach
1. Get team capacity for sprint
2. Review backlog items
3. Calculate velocity from previous sprints
4. Recommend items based on priority and capacity

### Expected Output
```markdown
## Sprint 16 Planning

### Sprint Details
- Duration: Dec 11 - Dec 25, 2025
- Team Capacity: 80 hours (4 developers × 20 hrs)

### Previous Sprint Velocity
- Sprint 15: 34 story points
- Sprint 14: 38 story points
- Average: 36 points

### Recommended Items (Priority Order)

| ID | Type | Title | Points | Assignee |
|----|------|-------|--------|----------|
| #1240 | Story | User profile page | 8 | Ahmed |
| #1241 | Bug | Fix search indexing | 5 | Sara |
| #1242 | Task | Database optimization | 13 | Mohammed |
| #1243 | Story | Export to PDF | 8 | Ahmed |

**Total: 34 points** (within capacity)

### Deferred to Next Sprint
| ID | Type | Title | Points | Reason |
|----|------|-------|--------|--------|
| #1245 | Story | Dashboard redesign | 21 | Too large |
| #1246 | Task | Legacy cleanup | 5 | Lower priority |

### Risks
- #1241 may need backend support
- #1242 requires production access

### Action Items
1. Break down #1245 into smaller stories
2. Request production access for Mohammed
```

---

## Code Review Workflow

### Scenario
Review a pull request and provide feedback.

### User Request
```
"Review PR #45"
```

### Claude's Approach
1. Get PR details
2. Get linked work items
3. List files changed
4. Review code changes
5. Add review comments

### Expected Output
```markdown
## PR #45 Review: Add user authentication

### PR Details
- Author: Ahmed
- Branch: feature/auth → main
- Status: Active
- Created: Dec 10, 2025

### Linked Work Items
- [Story] #1200: User authentication system
- [Task] #1201: Implement login endpoint

### Files Changed (5 files, +245 -12)
1. `src/auth/login.py` (+120)
2. `src/auth/middleware.py` (+80)
3. `tests/test_auth.py` (+45)
4. `docs/api.md` (+12 -12)
5. `requirements.txt` (+3)

### Review Summary

**Approved with comments**

#### Positive
- Good test coverage
- Clear documentation
- Follows coding standards

#### Suggestions
1. **login.py:45** - Consider rate limiting
   ```python
   # Add rate limit decorator
   @rate_limit(max_requests=5, window=60)
   ```

2. **middleware.py:23** - Token expiry should be configurable
   ```python
   # Use config instead of hardcoded value
   TOKEN_EXPIRY = settings.TOKEN_EXPIRY_SECONDS
   ```

### Next Steps
- [ ] Address review comments
- [ ] Update documentation
- [ ] Merge when approved
```

---

## Bug Triage

### Scenario
Triage and organize incoming bugs.

### User Request
```
"Triage new bugs from last week"
```

### Claude's Approach
1. Query bugs created in last 7 days
2. Categorize by severity
3. Identify duplicates
4. Assign priorities
5. Recommend assignments

### Expected Output
```markdown
## Bug Triage Report - Dec 4-11, 2025

### Summary
- New Bugs: 12
- Critical: 2
- High: 4
- Medium: 4
- Low: 2

### Critical (Severity 1) - Needs Immediate Attention

| ID | Title | Reported By | Recommendation |
|----|-------|-------------|----------------|
| #1250 | Payment processing fails | Customer | Assign to Sara, Sprint 16 |
| #1251 | Data loss on save | QA Team | Assign to Mohammed, Hotfix |

### High (Severity 2) - Sprint Priority

| ID | Title | Duplicate? | Recommendation |
|----|-------|------------|----------------|
| #1252 | Login timeout too short | No | Sprint 16 |
| #1253 | Search returns wrong results | Yes (#1180) | Close as duplicate |
| #1254 | Export fails for large files | No | Sprint 16 |
| #1255 | Missing validation on form | No | Sprint 16 |

### Medium/Low - Backlog

| ID | Title | Severity | Recommendation |
|----|-------|----------|----------------|
| #1256 | UI alignment issue | Medium | Backlog |
| #1257 | Slow loading on dashboard | Medium | Backlog |
| #1258 | Typo in error message | Low | Backlog |
| #1259 | Minor CSS issue | Low | Backlog |

### Duplicates Found
- #1253 duplicates #1180 (search issue)
- #1258 possibly duplicates #1190

### Action Items
1. Close #1253 as duplicate of #1180
2. Create hotfix branch for #1251
3. Schedule #1250 for Sprint 16
4. Review #1258 for duplicate status
```

---

## Build Monitoring

### Scenario
Investigate failed build and diagnose issues.

### User Request
```
"Why did build #789 fail?"
```

### Claude's Approach
1. Get build details
2. Get build logs
3. Identify error patterns
4. Analyze test results
5. Suggest fixes

### Expected Output
```markdown
## Build #789 Failure Analysis

### Build Details
- Pipeline: CI-Main
- Status: Failed
- Duration: 3m 45s (vs avg 5m)
- Triggered: PR merge to main
- Branch: main
- Commit: abc123f

### Failure Point
Stage: Test → Job: Unit Tests → Step: pytest

### Error Summary
```
FAILED tests/test_auth.py::TestLogin::test_invalid_credentials
AssertionError: Expected 401 but got 500

FAILED tests/test_auth.py::TestLogin::test_token_expiry
TimeoutError: Database connection timed out
```

### Analysis

**Root Cause: Database Connection Issue**

The test failures appear to be caused by a database connection timeout, not code issues:

1. `test_invalid_credentials` - Got 500 (server error) instead of 401
2. `test_token_expiry` - Explicit timeout error

**Evidence:**
- Tests passed in previous build #788
- No code changes to auth module
- Similar timeout pattern in logs

### Recommended Actions

1. **Immediate**: Re-run build (likely transient issue)
   ```
   "Re-run build #789"
   ```

2. **If persists**: Check database service
   - Verify test database is running
   - Check connection pool settings

3. **If code issue**: Review recent commits
   - Commit abc123f by Ahmed (Dec 11)
   - Changes: 3 files, +45 -12

### Related
- Previous failure: Build #785 (same issue, 3 days ago)
- Similar bug: #1200 (DB timeout in production)
```

---

## Release Management

### Scenario
Prepare for a production release.

### User Request
```
"Prepare release notes for v2.5.0"
```

### Claude's Approach
1. Get completed work items since last release
2. Categorize by type (features, bugs, improvements)
3. Check all PRs are merged
4. Verify builds passing
5. Generate release notes

### Expected Output
```markdown
## Release Notes - v2.5.0

**Release Date:** December 11, 2025
**Previous Version:** v2.4.0 (November 28, 2025)

### Release Checklist
- [x] All PRs merged
- [x] All tests passing
- [x] Documentation updated
- [x] Staging deployment verified
- [ ] Production deployment pending

### New Features
- **User Authentication** (#1200)
  - OAuth 2.0 support
  - Two-factor authentication
  - Password reset flow

- **Export Enhancements** (#1180)
  - PDF export with formatting
  - Batch export support
  - Custom templates

### Bug Fixes
- Fixed payment processing timeout (#1150)
- Fixed search indexing for special characters (#1145)
- Fixed session expiry handling (#1140)
- Fixed export failing for large files (#1135)

### Improvements
- Improved dashboard loading speed by 40%
- Enhanced error messages
- Updated dependencies

### Breaking Changes
- API v1 endpoints deprecated (use v2)
- Minimum browser version: Chrome 90+

### Known Issues
- Export may be slow for files > 100MB
- Safari: Minor CSS alignment issue

### Contributors
- Ahmed (12 commits)
- Sara (8 commits)
- Mohammed (6 commits)

### Deployment Notes
1. Run database migration: `python manage.py migrate`
2. Clear cache: `python manage.py clear_cache`
3. Restart services

### Rollback Plan
If issues arise:
1. Revert to v2.4.0 image
2. Rollback database migration
3. Notify team in #releases channel
```

---

## Quick Reference

### Common Commands

| Action | Command |
|--------|---------|
| My tasks | "Show my work items" |
| Create bug | "Create bug: [description]" |
| Sprint status | "Sprint summary" |
| PR review | "Review PR #ID" |
| Build status | "Show recent builds" |
| Search code | "Find [query] in code" |

### Useful WIQL Queries

```sql
-- My high priority items
SELECT * FROM WorkItems
WHERE [System.AssignedTo] = @Me
AND [Microsoft.VSTS.Common.Priority] <= 2

-- Bugs without owners
SELECT * FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
AND [System.AssignedTo] = ''

-- Recently updated
SELECT * FROM WorkItems
WHERE [System.ChangedDate] >= @Today - 3
ORDER BY [System.ChangedDate] DESC
```
