# Profile Loader & Project Context

## Profile Loading (Every Session)

At session start or first DevOps operation:

```
1. Read ~/.claude/devops.md
2. If found:
   a. Parse YAML frontmatter
   b. Build lookup tables:
      - currentUser = identity (name, email, guid)
      - teamByAlias = Map(alias -> {name, email, guid, role})
        Include "me"/"myself" -> current user
      - teamByEmail = Map(email -> {name, guid, role})
      - projectsByName = Map(name -> {role, team, repos})
      - statePerms = from profile statePermissions section
   c. Set defaultProject from profile
   d. Set taskPrefix from preferences
   e. Log: "Profile loaded: {displayName} ({role}) -- {defaultProject}"
3. If NOT found:
   a. Show: "No DevOps profile found. Run /init profile for faster operations."
   b. Fall back to API-based resolution
   c. Continue (graceful degradation)
```

## Profile-Aware Shortcuts

| User Says | Without Profile | With Profile |
|-----------|----------------|--------------|
| "assign to me" | API call | Instant: use `identity.guid` |
| "@mahmoud" | API call | Cache lookup -> instant if found |
| /create "Fix bug" | Infer prefix | Use `preferences.taskPrefix` |
| (session start) | Auto-detect project | Use `defaultProject` |

## Cache-First Resolution

For any operation needing a user identity:

1. "me"/"myself"/"I" -> return currentUser from profile
2. Check teamByAlias -> if found, return cached {name, email, guid}
3. Check teamByEmail -> if found, return cached
4. Fall back to API: `core_get_identity_ids({ searchFilter: name })`
5. If API fails -> ask user for clarification

---

## Project Context Management

### Core Rule: User should never have to repeat project name

**Context persists** throughout the conversation session.

### Context Rules

| Action | Behavior |
|--------|----------|
| "switch to PROJECT" | Changes default permanently for session |
| "tasks in PROJECT" | One-time override, default unchanged |
| "all my tasks across all projects" | Query all, default unchanged |
| No context set + no project specified | Auto-detect most active project, confirm with user |

### Initial Context Setup

If no context and no project specified:
1. Check profile `defaultProject` -> use it
2. If no profile -> query `core_list_projects`, check `wit_my_work_items` per project
3. Pick most active, confirm with user: "I'll use {project} as default. Say 'switch to [project]' to change."

### Switch Triggers

"switch to", "use", "change project to", "set project", "work on" -> permanent context change.
