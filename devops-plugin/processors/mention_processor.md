# @Mention Auto-Processor

## Purpose

This processor automatically detects and resolves @mentions in comments to proper Azure DevOps format. It ensures users receive notifications when mentioned.

**CRITICAL RULE**: **NEVER** post a comment with an unresolved/fake mention. If a mention cannot be resolved, **ASK the user** to clarify before posting.

---

## 🚫 ABSOLUTE RULE: No Fake Mentions

```
┌─────────────────────────────────────────────────────────────────┐
│                    ⚠️ CRITICAL: MENTION VALIDATION               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE posting any comment with @mentions:                     │
│                                                                  │
│  1. DETECT all @mentions in text                                │
│  2. RESOLVE each mention to GUID via API                        │
│  3. VALIDATE resolution succeeded                               │
│                                                                  │
│  IF ANY mention fails to resolve:                               │
│    → DO NOT POST the comment                                    │
│    → ASK USER: "I couldn't find user '@name'. Did you mean...?" │
│    → WAIT for user clarification                                │
│    → RETRY resolution                                           │
│                                                                  │
│  NEVER post "@mahmoud" as plain text hoping it works!           │
│  Plain text mentions DO NOT send notifications!                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mention Resolution Workflow

### Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MENTION PROCESSING WORKFLOW                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: "Hey @mahmoud, please review. Also @eslam"              │
│                                                                  │
│  STEP 1: EXTRACT MENTIONS                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Pattern: @([a-zA-Z0-9._-]+)                             │    │
│  │ Found: ["mahmoud", "eslam"]                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: RESOLVE EACH TO GUID (parallel API calls)              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ core_get_identity_ids({ searchFilter: "mahmoud" })      │    │
│  │   → Found: { id: "6011f8b0-...", name: "Mahmoud E." }   │    │
│  │                                                         │    │
│  │ core_get_identity_ids({ searchFilter: "eslam" })        │    │
│  │   → Found: { id: "7022g9c1-...", name: "Eslam Hafez" }  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: VALIDATE ALL RESOLUTIONS                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ mahmoud → ✅ Resolved (GUID found)                       │    │
│  │ eslam   → ✅ Resolved (GUID found)                       │    │
│  │                                                         │    │
│  │ ALL RESOLVED? → Proceed to Step 4                       │    │
│  │ ANY FAILED?   → STOP! Go to Step 3b                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3b: HANDLE FAILED RESOLUTION (if any)                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "I couldn't find user '@unknown'. Did you mean:         │    │
│  │  • Team Member (@mahmoud)                          │    │
│  │  • Team Member (@mohamed)                             │    │
│  │  • [Someone else - please provide full name/email]"     │    │
│  │                                                         │    │
│  │ WAIT for user response before proceeding!               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: CONVERT TO HTML FORMAT                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @mahmoud → <a href="#" data-vss-mention="version:2.0,   │    │
│  │            guid:6011f8b0-...">@Team Member</a>     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 5: POST COMMENT                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ wit_add_work_item_comment({                             │    │
│  │   project: "Relief Center",                             │    │
│  │   workItemId: 1234,                                     │    │
│  │   comment: processedHtml,                               │    │
│  │   format: "html"                                        │    │
│  │ })                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Implementation

### Step 1: Extract Mentions from Text

```javascript
// Detection Pattern
const mentionPattern = /@([a-zA-Z0-9._-]+)/g;

// Example
const text = "Hey @mahmoud, please review. Also @eslam";
const mentions = [...text.matchAll(mentionPattern)].map(m => m[1]);
// Result: ["mahmoud", "eslam"]
```

**Detected Patterns**:
- `@mahmoud` → Extract "mahmoud"
- `@eslam.hafez` → Extract "eslam.hafez"
- `@ahmed_tech` → Extract "ahmed_tech"
- `@user123` → Extract "user123"

### Step 2: Resolve Each Mention to GUID

**MUST use API to resolve - never guess!**

```javascript
// For EACH extracted mention, call the API
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"  // Use extracted username
})

// Expected Response (SUCCESS):
{
  "identities": [
    {
      "id": "6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "displayName": "Team Member",
      "uniqueName": "redacted@example.com"
    }
  ]
}

// Expected Response (FAILURE - no match):
{
  "identities": []
}
```

### Step 3: Validate ALL Resolutions

```javascript
// Validation Logic
const resolutions = await Promise.all(
  mentions.map(m => resolveIdentity(m))
);

const failed = resolutions.filter(r => !r.found);

if (failed.length > 0) {
  // DO NOT PROCEED - Ask user for clarification
  return askUserForClarification(failed);
}

// Only proceed if ALL mentions resolved successfully
```

### Step 3b: Handle Failed Resolution

**CRITICAL: If ANY mention fails, DO NOT post the comment!**

```
User: "Add comment mentioning @bob"

Claude (after failed resolution):
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ I couldn't find a user matching "@bob" in Azure DevOps.       │
│                                                                  │
│ Did you mean one of these team members?                         │
│                                                                  │
│ • Team Member (@mahmoud, redacted@example.com)        │
│ • Eslam Hafez (@eslam, redacted@example.com)                  │
│ • Team Member (@ahmed, redacted@example.com)          │
│ • Team Member (@yussef, redacted@example.com)            │
│ • Team Member (@mohamed)                                      │
│                                                                  │
│ Or please provide:                                              │
│ • Full name (e.g., "Bob Smith")                                 │
│ • Email address (e.g., "bob@company.com")                       │
│                                                                  │
│ I won't post the comment until I can properly resolve the       │
│ mention so the user receives a notification.                    │
└─────────────────────────────────────────────────────────────────┘
```

### Step 4: Convert to HTML Format

**Only after ALL mentions are validated!**

```javascript
// HTML Mention Format (Azure DevOps standard)
function formatMention(guid, displayName) {
  return `<a href="#" data-vss-mention="version:2.0,guid:${guid}">@${displayName}</a>`;
}

// Example
const html = formatMention(
  "6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "Team Member"
);
// Result: <a href="#" data-vss-mention="version:2.0,guid:6011f8b0-...">@Team Member</a>
```

### Step 5: Post Comment with HTML

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "Hey <a href=\"#\" data-vss-mention=\"version:2.0,guid:6011f8b0-xxxx\">@Team Member</a>, please review.",
  "format": "html"  // IMPORTANT: Must specify html format
})
```

---

## Team Members Cache (TaqaTechno)

Pre-defined team members for faster resolution and suggestion:

| Display Name | Search Terms | Email | Status |
|--------------|--------------|-------|--------|
| Team Member | ahmed, alakosha | redacted@example.com | Active |
| Team Member | eslam, ehafez | redacted@example.com | Active |
| Team Member | yussef, yhussein | redacted@example.com | Active |
| Team Member | sameh, sabdlal | redacted@example.com | Active |
| Team Member | mahmoud, melshahed | redacted@example.com | Active |
| Team Member | mohamed, mafifi | redacted@example.com | Active |
| Team Member | hossam, hmoussa | redacted@example.com | Active |
| Team Member | amr, asaber | redacted@example.com | Active |
| Team Member | sara, sahmed | redacted@example.com | Active |
| Team Member | omar, okhaled | redacted@example.com | Active |

**Note**: GUIDs are NOT cached - always resolve via API to ensure accuracy.

---

## Validation Rules

### Rule 1: Never Post Unresolved Mentions

```
IF mention resolution returns empty:
  → DO NOT format as @username in plain text
  → DO NOT guess the GUID
  → DO NOT post comment
  → ASK user for clarification
```

### Rule 2: Verify Single Match

```
IF resolution returns multiple matches:
  → Present options to user
  → "Found multiple users matching '@mo':
     1. Team Member
     2. Moussa Hassan
     Which one did you mean?"
  → WAIT for user selection
```

### Rule 3: Confirm Before Posting

```
IF user provides partial name and match is uncertain:
  → "I found 'Team Member'. Is this correct?"
  → WAIT for confirmation
  → Only then proceed with comment
```

### Rule 4: Handle API Errors Gracefully

```
IF API call fails (network error, timeout):
  → "I couldn't verify the user mention due to a connection issue.
     Would you like me to:
     1. Retry the lookup
     2. Post comment without the mention
     3. Cancel"
```

---

## Complete Example Flow

### Successful Flow

**User**: "Add a comment on #1234 mentioning @mahmoud to review"

**Claude**:
```
Step 1: Extracting mentions... found: @mahmoud

Step 2: Resolving @mahmoud...
```

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"
})
// Returns: { id: "6011f8b0-...", displayName: "Team Member" }
```

```
Step 3: ✅ @mahmoud resolved to Team Member

Step 4: Posting comment...
```

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:6011f8b0-xxxx\">@Team Member</a> please review this.",
  "format": "html"
})
```

```
✅ Comment added to #1234!
   Team Member will receive a notification.
```

### Failed Flow (Unresolved Mention)

**User**: "Add a comment on #1234 mentioning @bob"

**Claude**:
```
Step 1: Extracting mentions... found: @bob

Step 2: Resolving @bob...
```

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "bob"
})
// Returns: { identities: [] }  // No match!
```

```
⚠️ I couldn't find a user matching "@bob" in Azure DevOps.

Did you mean one of these team members?
• Team Member (@ahmed)
• Eslam Hafez (@eslam)
• Team Member (@mahmoud)
• Team Member (@mohamed)
• Team Member (@yussef)

Please provide the correct name or email, and I'll add the comment.
```

**User**: "I meant @mahmoud"

**Claude**:
```
Step 2: Resolving @mahmoud...
✅ Found: Team Member

Posting comment...

✅ Comment added to #1234!
   Team Member will receive a notification.
```

---

## API Reference

### Identity Resolution

```javascript
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "search_term"  // Name, email, or username
})
```

**Response Structure**:
```json
{
  "identities": [
    {
      "id": "guid-here",
      "displayName": "Full Name",
      "uniqueName": "email@domain.com"
    }
  ]
}
```

### Add Comment with HTML

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Project Name",
  "workItemId": 1234,
  "comment": "HTML content with <a> tags for mentions",
  "format": "html"  // Required for mentions to work
})
```

---

## Checklist Before Posting Comment

- [ ] All @mentions extracted from text
- [ ] Each mention resolved via `core_get_identity_ids` API
- [ ] All resolutions returned valid GUIDs
- [ ] No failed/empty resolutions
- [ ] User confirmed any ambiguous matches
- [ ] Mentions converted to HTML `<a>` format
- [ ] Comment posted with `format: "html"`

**If ANY checkbox fails → DO NOT POST → Ask user for clarification**

---

## Integration Points

This processor integrates with:

1. **SKILL.md** - Main skill file references this processor
2. **data/team_members.json** - Cached team member info for suggestions
3. **commands/add-comment.md** - Uses processor for all comments

---

*Mention Processor v1.0*
*Part of DevOps Plugin v3.0 Enhancement*
*TaqaTechno - December 2025*
