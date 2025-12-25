---
title: 'Add Comment'
read_only: false
type: 'command'
description: 'Add comment to work item with validated @mentions'
---

# Add Comment

Add a comment to a work item with **validated @mentions** that properly notify users.

## 🚫 CRITICAL: No Fake Mentions

**Reference**: `processors/mention_processor.md`

```
┌─────────────────────────────────────────────────────────────────┐
│           ⚠️ ABSOLUTE RULE: VALIDATE ALL MENTIONS                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE posting any comment with @mentions:                     │
│                                                                  │
│  ✅ RESOLVE every @mention via API                               │
│  ✅ VALIDATE each resolution returned a GUID                     │
│  ✅ CONVERT to HTML format                                       │
│                                                                  │
│  IF ANY mention fails:                                          │
│  ❌ DO NOT post the comment                                      │
│  ❌ DO NOT use plain text @name                                  │
│  ✅ ASK user for clarification                                   │
│  ✅ SUGGEST known team members                                   │
│                                                                  │
│  Plain text "@mahmoud" does NOT notify anyone!                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

```
/add-comment #1234 "Please review this @mahmoud"
/add-comment #1234 "Great work @eslam @ahmed"
/add-comment #1234 "Simple comment without mentions"
```

## Mention Validation Workflow

### Step 1: Extract Mentions

```javascript
// Pattern to detect @mentions
const pattern = /@([a-zA-Z0-9._-]+)/g;

// Example
const text = "Please review @mahmoud and @eslam";
const mentions = ["mahmoud", "eslam"];
```

### Step 2: Resolve Each Mention via API

**MANDATORY - Never skip this step!**

```javascript
// For EACH mention, call the API
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"
})
```

**Success Response**:
```json
{
  "identities": [{
    "id": "6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "displayName": "Team Member",
    "uniqueName": "redacted@example.com"
  }]
}
```

**Failure Response** (no match):
```json
{
  "identities": []
}
```

### Step 3: Handle Resolution Results

#### All Mentions Resolved ✅

```javascript
// All resolved - format and post
const htmlComment = `Please review <a href="#" data-vss-mention="version:2.0,guid:6011f8b0-...">@Team Member</a>`;

mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": htmlComment,
  "format": "html"
})
```

#### Any Mention Failed ❌

**DO NOT POST! Ask user for clarification:**

```
⚠️ I couldn't find a user matching "@bob" in Azure DevOps.

Did you mean one of these team members?
• Team Member (@mahmoud)
• Eslam Hafez (@eslam)
• Team Member (@ahmed)
• Team Member (@mohamed)
• Team Member (@yussef)

Please provide the correct name or email address.
```

### Step 4: Post with HTML Format

**Only after ALL mentions validated!**

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "...",
  "format": "html"  // REQUIRED for mentions to work
})
```

## Complete Example Flows

### Example 1: Successful Comment with Mention

**User**: "Add comment on #1234 mentioning @mahmoud to review"

**Claude**:
```
Processing comment for #1234...

Step 1: Found mention: @mahmoud
Step 2: Resolving @mahmoud...
```

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"
})
// Returns: { id: "6011f8b0-...", displayName: "Team Member" }
```

```
Step 3: ✅ Resolved: Team Member
Step 4: Posting comment...
```

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:6011f8b0-...\">@Team Member</a> please review this.",
  "format": "html"
})
```

```
✅ Comment added to #1234!
   Team Member will receive a notification.
```

### Example 2: Failed Resolution - Ask User

**User**: "Comment on #1234: @johnny please check this"

**Claude**:
```
Processing comment for #1234...

Step 1: Found mention: @johnny
Step 2: Resolving @johnny...
```

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "johnny"
})
// Returns: { identities: [] }  // No match!
```

```
⚠️ I couldn't find a user matching "@johnny" in Azure DevOps.

I won't post the comment with an unresolved mention because:
• Plain text "@johnny" won't notify anyone
• The mention would appear broken

Did you mean one of these team members?

| Name | Search Terms |
|------|--------------|
| Team Member | @mahmoud |
| Eslam Hafez | @eslam |
| Team Member | @ahmed |
| Team Member | @mohamed |
| Team Member | @yussef |
| Team Member | @hossam |

Or provide:
• Full name (e.g., "John Smith")
• Email address (e.g., "john@company.com")
```

**User**: "I meant @mahmoud"

**Claude**:
```
Resolving @mahmoud...
✅ Found: Team Member

Posting comment...

✅ Comment added to #1234!
   Team Member will receive a notification.
```

### Example 3: Multiple Mentions (Mixed Results)

**User**: "Comment on #1234: @mahmoud and @xyz please review"

**Claude**:
```
Processing comment for #1234...

Step 1: Found mentions: @mahmoud, @xyz
Step 2: Resolving mentions...
  • @mahmoud → ✅ Team Member
  • @xyz → ❌ No user found

⚠️ I resolved 1 of 2 mentions, but couldn't find "@xyz".

I won't post the comment until all mentions are resolved.

For @xyz, did you mean:
• Eslam Hafez (@eslam)
• Team Member (@ahmed)
• Or someone else?
```

### Example 4: Comment Without Mentions

**User**: "Add comment to #1234: The fix looks good, merging now"

**Claude**:
```
Processing comment for #1234...

No @mentions detected.
Posting comment...
```

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "The fix looks good, merging now",
  "format": "html"
})
```

```
✅ Comment added to #1234!
```

## Team Members Quick Reference

| Name | Email | Common Search Terms |
|------|-------|---------------------|
| Team Member | redacted@example.com | @ahmed, @alakosha |
| Eslam Hafez | redacted@example.com | @eslam, @ehafez |
| Team Member | redacted@example.com | @mahmoud, @melshahed |
| Team Member | redacted@example.com | @mohamed, @mafifi |
| Team Member | redacted@example.com | @yussef, @yhussein |
| Team Member | redacted@example.com | @sameh, @sabdlal |
| Team Member | redacted@example.com | @hossam, @hmoussa |
| Team Member | redacted@example.com | @amr, @asaber |

## HTML Mention Format

```html
<a href="#" data-vss-mention="version:2.0,guid:GUID_HERE">@Display Name</a>
```

**Example**:
```html
<a href="#" data-vss-mention="version:2.0,guid:6011f8b0-1234-5678-9abc-def012345678">@Team Member</a>
```

## Validation Checklist

Before posting any comment with mentions:

- [ ] All @mentions extracted from text
- [ ] Each mention resolved via `core_get_identity_ids` API call
- [ ] All API calls returned valid identity with GUID
- [ ] No failed/empty resolutions
- [ ] User clarified any unresolved mentions
- [ ] All mentions converted to HTML `<a>` format
- [ ] Comment uses `format: "html"` parameter

**If ANY checkbox fails → DO NOT POST → Ask user first!**

## Error Handling

### API Error

```
If core_get_identity_ids fails (network error):

"I couldn't verify the @mention due to a connection issue.
Would you like me to:
1. Retry the lookup
2. Post without the mention
3. Cancel"
```

### Multiple Matches

```
If API returns multiple identities:

"Found multiple users matching '@mo':
1. Team Member (redacted@example.com)
2. Team Member (redacted@example.com)

Which one did you mean?"
```

---

*Part of DevOps Plugin v3.0*
*Mention Validation: Enabled*
*Never post fake mentions!*
