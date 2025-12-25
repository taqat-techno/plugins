# TaqaTechno Team Workflows

> **Purpose**: This memory provides TaqaTechno-specific workflows, conventions, and best practices for Azure DevOps usage. These patterns reflect how the team operates and should be followed for consistency.

## Organization Overview

| Property | Value |
|----------|-------|
| Organization | TaqaTechno |
| URL | https://dev.azure.com/TaqaTechno |
| Primary Projects | Relief Center, KhairGate, TAQAT Property |
| Team Size | 5-15 members |
| Methodology | Scrum (2-week sprints) |

---

## 1. Work Item Hierarchy

### 1.1 Standard Hierarchy

```
Epic
  └── Feature
        └── User Story
              └── Task
              └── Bug
```

### 1.2 Hierarchy Rules

| Rule | Description |
|------|-------------|
| Epics contain Features | Group related features under epics |
| Features contain User Stories | Break down features into deliverable stories |
| User Stories contain Tasks | Technical breakdown of stories |
| Bugs can be standalone | Or linked to User Stories if feature-related |

### 1.3 Required Parent Links

| Item Type | Required Parent |
|-----------|-----------------|
| Task | User Story or Feature |
| Bug | Optional (User Story for feature bugs) |
| User Story | Feature |
| Feature | Epic |

**Enforcement**: The `/create-task` and `/create-bug` commands enforce parent links.

---

## 2. Work Item Conventions

### 2.1 Title Patterns

| Type | Pattern | Example |
|------|---------|---------|
| User Story | `As a [role], I want [feature] so that [benefit]` | "As a user, I want to reset my password so that I can regain access" |
| Task | `[Action] [component/feature]` | "Implement password reset API endpoint" |
| Bug | `[Symptom] when [action]` | "Login fails when using special characters" |
| Feature | `[Noun]: [Description]` | "Authentication: User login and registration" |

### 2.2 Description Templates

#### User Story Template (What/How/Why)
```html
<h3>What</h3>
<p>[What the user needs to do]</p>

<h3>How</h3>
<p>[How the feature should work]</p>

<h3>Why</h3>
<p>[Business value and user benefit]</p>

<h3>Acceptance Criteria</h3>
<ul>
<li>[ ] Criterion 1</li>
<li>[ ] Criterion 2</li>
</ul>
```

#### Bug Template
```html
<h3>Steps to Reproduce</h3>
<ol>
<li>Step 1</li>
<li>Step 2</li>
</ol>

<h3>Expected Result</h3>
<p>[What should happen]</p>

<h3>Actual Result</h3>
<p>[What actually happens]</p>

<h3>Environment</h3>
<ul>
<li>Browser: Chrome 120</li>
<li>OS: Windows 11</li>
<li>Version: 1.2.0</li>
</ul>
```

### 2.3 Priority Definitions

| Priority | Response Time | Description |
|----------|--------------|-------------|
| 1 - Critical | Immediate | Production down, data loss, security breach |
| 2 - High | 24 hours | Major feature broken, significant user impact |
| 3 - Medium | This sprint | Normal priority, planned work |
| 4 - Low | Backlog | Nice to have, minor improvements |

### 2.4 State Workflow

```
New → Active → In Progress → Code Review → Done → Closed
         ↓                        ↓
      Blocked                  Rejected → Active
```

| State | Description | Who Changes |
|-------|-------------|-------------|
| New | Just created, not started | System |
| Active | Assigned and ready to work | Developer |
| In Progress | Currently being worked on | Developer |
| Code Review | PR created, waiting for review | Developer |
| Done | Completed, verified | Developer/Tester |
| Closed | Sprint closed, archived | Scrum Master |
| Blocked | Cannot proceed | Developer |

---

## 3. Sprint Workflow

### 3.1 Sprint Timeline (2 Weeks)

| Day | Activity |
|-----|----------|
| Day 1 | Sprint Planning (assign items, set capacity) |
| Day 2-9 | Development (daily standups) |
| Day 10 | Code freeze, testing |
| Day 11 | Bug fixes |
| Day 12 | Sprint Review |
| Day 13 | Sprint Retrospective |
| Day 14 | Sprint closes, next sprint prep |

### 3.2 Sprint Planning Workflow

```mermaid
1. Create Sprint Iteration (CLI)
   az boards iteration project create --name "Sprint 15"

2. Assign to Team (MCP)
   work_assign_iterations()

3. Set Team Capacity (MCP)
   work_update_team_capacity()

4. Move Items to Sprint (MCP)
   wit_update_work_item() with IterationPath

5. Assign to Team Members (MCP)
   wit_update_work_item() with AssignedTo
```

### 3.3 Daily Standup Format

```markdown
## Daily Standup - [Date]

### Yesterday
- [Task #123] Completed login API
- [Bug #456] Fixed validation error

### Today
- [Task #124] Implement logout
- [Task #125] Add session management

### Blockers
- None / [Issue description]
```

Use `/standup` command to generate automatically.

---

## 4. Code Review Workflow

### 4.1 PR Creation Checklist

- [ ] Branch naming: `feature/[task-id]-description` or `bugfix/[bug-id]-description`
- [ ] PR title matches work item title
- [ ] Description includes summary and test plan
- [ ] Work items linked
- [ ] Reviewers assigned (minimum 2)
- [ ] All tests passing

### 4.2 PR Title Pattern

```
[Type]: [Description] (#WorkItemId)
```

Examples:
- `Feature: Add user authentication (#123)`
- `Bugfix: Fix login validation error (#456)`
- `Refactor: Optimize database queries (#789)`

### 4.3 PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- Added X
- Modified Y
- Removed Z

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Edge cases covered

## Screenshots (if UI changes)
[Add screenshots]

## Related Work Items
- Resolves #123
- Related to #456
```

### 4.4 Review Process

1. **Author** creates PR with description
2. **Reviewers** (2 minimum) review code
3. **Reviewers** approve or request changes
4. **Author** addresses feedback
5. **Author** sets auto-complete when approved
6. **System** merges when all policies pass

### 4.5 Review Comment Categories

| Prefix | Meaning | Action Required |
|--------|---------|-----------------|
| `[Required]` | Must fix before merge | Yes |
| `[Suggestion]` | Improvement idea | No |
| `[Question]` | Need clarification | Response |
| `[Nitpick]` | Minor style issue | No |
| `[FYI]` | Information only | No |

---

## 5. Branch Strategy

### 5.1 Branch Types

| Branch | Purpose | Naming |
|--------|---------|--------|
| `main` | Production code | Protected |
| `develop` | Integration branch | Protected |
| `feature/*` | New features | `feature/[id]-description` |
| `bugfix/*` | Bug fixes | `bugfix/[id]-description` |
| `hotfix/*` | Production fixes | `hotfix/[id]-description` |
| `release/*` | Release preparation | `release/v1.2.0` |

### 5.2 Branch Policies (main)

- Minimum 2 reviewers
- All comments resolved
- Build must succeed
- Work items linked
- No direct pushes

### 5.3 Merge Strategy

| Source → Target | Strategy |
|-----------------|----------|
| feature → develop | Squash merge |
| bugfix → develop | Squash merge |
| develop → main | Merge commit |
| hotfix → main | Merge commit |

---

## 6. Pipeline Conventions

### 6.1 Pipeline Naming

| Type | Pattern | Example |
|------|---------|---------|
| CI | `CI-[Project]` | `CI-ReliefCenter` |
| CD | `CD-[Project]-[Env]` | `CD-ReliefCenter-Staging` |
| Release | `Release-[Project]` | `Release-ReliefCenter` |

### 6.2 Environment Pipeline Order

```
CI Build → Deploy Staging → Manual Approval → Deploy Production
```

### 6.3 Variable Groups

| Group | Purpose | Contents |
|-------|---------|----------|
| `Common-Settings` | Shared across projects | API URLs, versions |
| `[Project]-Secrets` | Project-specific secrets | API keys, passwords |
| `[Env]-Settings` | Environment-specific | Connection strings |

---

## 7. Team Communication

### 7.1 @Mentions in Work Items

Use @mentions to notify team members:

```
@ahmed - Can you review the API design?
@mahmoud - This is blocked by infrastructure
@eslam - Ready for testing
```

The `/create-task` command processes @mentions automatically.

### 7.2 Discussion Threads

| Thread Type | When to Use |
|-------------|-------------|
| Work Item Comments | Design discussions, clarifications |
| PR Threads | Code-specific feedback |
| Wiki | Documentation, guides |

### 7.3 Notification Preferences

| Event | Notification |
|-------|--------------|
| Assigned to me | Email + Teams |
| @mentioned | Email + Teams |
| PR review requested | Email + Teams |
| Build failed | Email |
| Work item state change | Teams only |

---

## 8. Documentation Standards

### 8.1 Wiki Structure

```
/
├── Home
├── Architecture
│   ├── System Overview
│   ├── API Documentation
│   └── Database Schema
├── Development
│   ├── Setup Guide
│   ├── Coding Standards
│   └── Testing Guide
├── Operations
│   ├── Deployment Guide
│   └── Runbooks
└── Sprints
    ├── Sprint 15 Notes
    └── Sprint 14 Notes
```

### 8.2 Wiki Naming

- Use Title Case for page names
- Use hyphens for URLs
- Keep names short but descriptive

---

## 9. Reporting Cadence

### 9.1 Regular Reports

| Report | Frequency | Generated By |
|--------|-----------|--------------|
| Daily Standup | Daily | `/standup` command |
| Sprint Progress | Weekly | `/sprint` command |
| Build Status | On demand | `/build-status` command |
| Sprint Report | End of sprint | Manual |

### 9.2 Sprint Metrics

| Metric | Target |
|--------|--------|
| Sprint completion | 85%+ |
| Bug escape rate | <5% |
| PR review time | <24 hours |
| Build success rate | 90%+ |

---

## 10. Common Slash Commands

### 10.1 Daily Use

| Command | Purpose |
|---------|---------|
| `/my-tasks` | List my active work items |
| `/standup` | Generate standup notes |
| `/sprint` | Sprint progress summary |
| `/build-status` | Recent build status |

### 10.2 Creation

| Command | Purpose |
|---------|---------|
| `/create-task` | Create task with parent validation |
| `/create-bug` | Create bug with template |
| `/create-user-story` | Create story with What/How/Why |

### 10.3 Management

| Command | Purpose |
|---------|---------|
| `/sync-my-tasks` | Sync tasks to TODO list |
| `/devops status` | Check CLI + MCP status |

---

## 11. Project-Specific Settings

### 11.1 Relief Center

| Setting | Value |
|---------|-------|
| Default Team | Relief Center Team |
| Sprint Duration | 2 weeks |
| Area Path | Relief Center\\Development |
| Iteration Path | Relief Center\\2025\\Sprint [N] |

### 11.2 KhairGate

| Setting | Value |
|---------|-------|
| Default Team | KhairGate Team |
| Sprint Duration | 2 weeks |
| Area Path | KhairGate\\Development |
| REST API Integration | Yes |

### 11.3 TAQAT Property

| Setting | Value |
|---------|-------|
| Default Team | TAQAT Property Team |
| Sprint Duration | 2 weeks |
| Multiple Sub-Projects | Yes |

---

## 12. Quick Reference Commands

### 12.1 CLI Quick Commands

```bash
# My tasks
az boards query --wiql "SELECT * FROM WorkItems WHERE [System.AssignedTo] = @Me AND [System.State] <> 'Closed'" -o table

# Sprint items
az boards query --wiql "SELECT * FROM WorkItems WHERE [System.IterationPath] = @CurrentIteration" -o table

# Active bugs
az boards query --wiql "SELECT * FROM WorkItems WHERE [System.WorkItemType] = 'Bug' AND [System.State] = 'Active'" -o table
```

### 12.2 MCP Quick Tools

```javascript
// My work items
wit_my_work_items({ project: "Relief Center" })

// Create task
wit_create_work_item({ project: "Relief Center", workItemType: "Task", fields: [...] })

// Update state
wit_update_work_item({ id: 123, updates: [{ path: "/fields/System.State", value: "Done" }] })
```

---

## Related Memories

- `hybrid_routing.md` - When to use CLI vs MCP
- `cli_best_practices.md` - CLI patterns
- `mcp_best_practices.md` - MCP patterns
- `wiql_queries.md` - Query patterns
- `automation_templates.md` - Automation scripts
