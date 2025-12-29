---
title: 'Create User Story'
read_only: false
type: 'command'
description: 'Create a user story with structured How/What/Why format'
---

# Create User Story

Create a well-structured User Story or Product Backlog Item with mandatory context.

## Hierarchy Requirement

**IMPORTANT**: User Stories/PBIs MUST be under a Feature.

```
Epic
  +--- Feature           <-- Parent for User Story
        +--- User Story  <-- This is what we're creating
              +--- Task
```

## REQUIRED: Story Format (How? -> What? -> Why?)

Every User Story MUST include these three sections in this specific order:

### 1. HOW? (Implementation Approach) - FIRST
- How will this be implemented?
- What technical approach?
- What components are affected?

### 2. WHAT? (Requirements) - SECOND
- What needs to be done?
- What is the deliverable?
- What are the acceptance criteria?

### 3. WHY? (Business Value) - THIRD
- Why is this needed?
- What problem does it solve?
- What value does it deliver?

## Description Template

```markdown
## How (Implementation Approach)
[Technical approach description - HOW this will be built]

### Affected Components
- Component 1
- Component 2

### Technical Notes
- Technical detail 1
- Technical detail 2

## What (Requirements)
[Description of what needs to be done - WHAT the deliverable is]

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Why (Business Value)
[Business justification - WHY this is needed]

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
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "workItemType": ["Feature"],
  "state": ["New", "Active"]
})
```

### Step 2: Gather Story Information (In Order!)

Ask user for information in this SPECIFIC order:

1. **HOW**: "How should this be implemented? (technical approach)"
2. **WHAT**: "What needs to be done? (requirements, acceptance criteria)"
3. **WHY**: "Why is this important? (business value)"

### Step 3: Create User Story
```
mcp__azure-devops__wit_create_work_item({
  "project": "ProjectName",
  "workItemType": "Product Backlog Item",
  "fields": [
    {"name": "System.Title", "value": "Story title"},
    {"name": "System.Description", "value": "Formatted description with How/What/Why", "format": "Html"}
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
2. Gathers How/What/Why information **in that order**
3. Creates PBI with structured description:

```markdown
## How (Implementation Approach)
Use CSS custom properties (variables) for theming with JavaScript toggle control. Store preference in localStorage for persistence.

### Affected Components
- Settings/Preferences page
- CSS theme variables file (variables.scss)
- Local storage handler utility
- All styled components (buttons, cards, inputs, navigation, footer)

### Technical Notes
- Use CSS variables for all color values
- Implement prefers-color-scheme media query for system theme detection
- Add CSS transition for smooth theme switching animation
- Create ThemeProvider context for React/Vue components

## What (Requirements)
Users need the ability to switch between light and dark themes for better accessibility and visual comfort.

### Acceptance Criteria
- [ ] Toggle switch visible in user settings
- [ ] Theme preference persists across sessions (stored in localStorage)
- [ ] Smooth transition animation when switching themes (300ms)
- [ ] All UI components properly styled in both themes
- [ ] System theme detection for automatic mode
- [ ] Works on all supported browsers (Chrome, Firefox, Safari, Edge)

## Why (Business Value)
Improves user experience and accessibility for users who prefer dark interfaces, especially in low-light environments.

### Impact
- **User Benefit**: Reduced eye strain, improved accessibility, personalized experience
- **Business Benefit**: Increased user satisfaction, modern UI appearance, competitive feature parity
- **Metric**: Expected 15% increase in evening session duration
```

4. Links to parent Feature
5. Confirms: "PBI #1234 created under Feature #500. Would you like to create tasks for this story?"

## Quick Reference

| Step | Action | Tool |
|------|--------|------|
| 1 | Find/Select Feature | `search_workitem` |
| 2 | Gather How/What/Why | Ask user questions |
| 3 | Create PBI | `create_work_item` |
| 4 | Link to Feature | `work_items_link` |
| 5 | Suggest next steps | Offer to create tasks |

## Common Issues

### "User Story" type disabled
Use "Product Backlog Item" instead - same hierarchy level.

### No Features exist
Create a Feature first under an Epic, then create the story.

### Missing Epic
Guide user to create the full hierarchy: Epic -> Feature -> PBI -> Tasks

## Integration

This command follows rules from:
- `rules/business_rules.md` - Rule 1 (Hierarchy) and Rule 2 (Story Format)

---

*User Story Command v2.0*
*How -> What -> Why Format*
*TaqaTechno - December 2025*
