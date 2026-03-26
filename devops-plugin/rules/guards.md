# Pre-Execution Guards

Three mandatory guards that run before specific operations. Each is a checklist, not a workflow.

---

## Guard 1: Tool Selection

**Problem**: `search_workitem` is TEXT SEARCH only. It ignores `assignedTo`, `state`, and `iteration` filters — returning 0 results for filtered queries.

### Decision Table

| User Intent | Correct Tool | NEVER Use |
|-------------|-------------|-----------|
| "My tasks" / "assigned to me" | `wit_my_work_items` | `search_workitem` |
| "Search for [text] in items" | `search_workitem` | — |
| Filter by state/type/assignee | CLI `az boards query --wiql` | `search_workitem` |
| Specific item #123 | `wit_get_work_item` | — |
| Multiple items by ID | `wit_get_work_items_batch_by_ids` | — |
| Sprint items / iteration | `wit_get_work_items_for_iteration` | `search_workitem` |

### Auto-Correction Rules

Before executing `search_workitem`, check:
1. Does intent match "my items" trigger phrases? -> Redirect to `wit_my_work_items`
2. Does call include `assignedTo`, `state`, or `iteration` params? -> Warn and redirect to WIQL
3. Is `searchText` a wildcard `*`? -> This is a filtered query, not text search -> Redirect

---

## Guard 2: Mention Processing

**Rule**: NEVER post a comment with an unresolved @mention. Plain text "@name" does NOT send notifications.

### Checklist Before Posting Comment

1. **Extract** all @mentions from text (pattern: `@([a-zA-Z0-9._-]+)`)
2. **Check profile cache first** — `~/.claude/devops.md` teamMembers aliases (fast path)
3. **Resolve** uncached mentions via `core_get_identity_ids`
4. **Validate** ALL resolutions returned GUIDs
   - If ANY failed -> DO NOT POST -> ask user for clarification
   - If multiple matches -> present options, wait for selection
5. **Convert** to HTML format:
   ```html
   <a href="#" data-vss-mention="version:2.0,guid:GUID_HERE">@Display Name</a>
   ```
6. **Post** with `format: "html"` parameter

### Fallback Strategy

1. Try username -> 2. Try full email -> 3. Try display name -> 4. ASK USER (do not post)

---

## Guard 3: Repository Resolution

**Problem**: Azure DevOps APIs require repository GUIDs, not names. Passing a name to `repositoryId` fails.

### Resolution Steps

1. **Is it a GUID?** (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) -> Use directly
2. **Check profile cache** — repos stored in `~/.claude/devops.md`
3. **API lookup** — `repo_get_repo_by_name_or_id({ repositoryNameOrId: name })`
4. **Fallback** — `repo_list_repos_by_project` + fuzzy match
5. **Not found** -> List available repos, ask user to pick

### Required For

All PR operations, branch operations, commit searches, work-item-to-PR links.
