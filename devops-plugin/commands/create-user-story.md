---
title: 'Create User Story'
read_only: false
type: 'command'
description: 'Create a user story with structured What/How/Why format'
---

# Create User Story

Create a well-structured User Story or Product Backlog Item with mandatory context.

## Hierarchy Requirement

**IMPORTANT**: User Stories/PBIs MUST be under a Feature.

```
Epic
  └── Feature           ← Parent for User Story
        └── User Story  ← This is what we're creating
              └── Task
```

## REQUIRED: Story Format (What? How? Why?)

Every User Story MUST include these three sections:

### 1. WHAT? (Requirements)
- What needs to be done?
- What is the deliverable?
- What are the acceptance criteria?

### 2. HOW? (Approach)
- How will this be implemented?
- What technical approach?
- What components are affected?

### 3. WHY? (Business Value)
- Why is this needed?
- What problem does it solve?
- What value does it deliver?

## Description Template

```markdown
## What (Requirements)
[Description of what needs to be done]

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## How (Implementation Approach)
[Technical approach description]

### Affected Components
- Component 1
- Component 2

## Why (Business Value)
[Business justification]

### Impact
- User benefit
- Business benefit
```

## Instructions

### Step 1: Identify Parent Feature (MANDATORY)
Before creating the story, ask:
- "Which Feature should this story be under?"
- If user doesn't know, list available Features:
```
mcp__azure-devops__wit_query_workitems({
  "project": "ProjectName",
  "query": "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.WorkItemType] = 'Feature' AND [System.State] <> 'Closed' ORDER BY [System.CreatedDate] DESC"
})
```

### Step 2: Gather Story Information
Ask user for:
1. **Title**: Brief descriptive title
2. **What**: What needs to be done?
3. **How**: How should it be implemented?
4. **Why**: Why is this important?

### Step 3: Create User Story
```
mcp__azure-devops__wit_create_work_item({
  "project": "ProjectName",
  "workItemType": "Product Backlog Item",
  "fields": [
    {"name": "System.Title", "value": "Story title"},
    {"name": "System.Description", "value": "Formatted description with What/How/Why"}
  ]
})
```

**Note**: Use "Product Backlog Item" as User Story type may be disabled in some projects.

### Step 4: Link to Parent Feature (MANDATORY)
```
mcp__azure-devops__wit_work_items_link({
  "project": "ProjectName",
  "updates": [{
    "id": NEW_PBI_ID,
    "linkToId": FEATURE_ID,
    "type": "child"
  }]
})
```

### Step 5: Confirm Creation
Return:
- Story ID and URL
- Parent Feature link
- Next steps suggestion (create tasks)

## Example

**User**: "Create user story for implementing dark mode"

**Claude**:
1. Asks which Feature this should be under
2. Gathers What/How/Why information
3. Creates PBI with structured description:

```markdown
## What (Requirements)
Users need the ability to switch between light and dark themes for better accessibility and visual comfort.

### Acceptance Criteria
- [ ] Toggle switch visible in user settings
- [ ] Theme preference persists across sessions (stored in local storage/database)
- [ ] Smooth transition animation when switching themes
- [ ] All UI components properly styled in both themes
- [ ] System theme detection for automatic mode

## How (Implementation Approach)
Implement CSS custom properties (variables) for theming with JavaScript toggle control.

### Affected Components
- Settings/Preferences page
- CSS theme variables file
- Local storage handler
- All styled components (buttons, cards, inputs, etc.)
- Navigation bar and footer

### Technical Notes
- Use CSS variables for color values
- Implement prefers-color-scheme media query support
- Add transition effects for smooth switching

## Why (Business Value)
Improves user experience and accessibility for users who prefer dark interfaces, especially in low-light environments.

### Impact
- **User Benefit**: Reduced eye strain, improved accessibility, personalized experience
- **Business Benefit**: Increased user satisfaction, modern UI appearance, competitive feature parity
```

4. Links to parent Feature
5. Confirms: "PBI #1234 created under Feature #500. Would you like to create tasks for this story?"

## Quick Reference

| Step | Action | Tool |
|------|--------|------|
| 1 | Find/Select Feature | `query_workitems` with WIQL |
| 2 | Gather What/How/Why | Ask user questions |
| 3 | Create PBI | `create_work_item` |
| 4 | Link to Feature | `work_items_link` |
| 5 | Suggest next steps | Offer to create tasks |

## Common Issues

### "User Story" type disabled
Use "Product Backlog Item" instead - same hierarchy level.

### No Features exist
Create a Feature first under an Epic, then create the story.

### Missing Epic
Guide user to create the full hierarchy: Epic → Feature → PBI → Tasks
