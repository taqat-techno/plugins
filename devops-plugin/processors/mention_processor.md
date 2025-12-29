# @Mention Auto-Processor (v2.0 - Strict Enforcement)

## Purpose

This processor automatically detects and resolves @mentions in comments to proper Azure DevOps format. It ensures users receive notifications when mentioned.

**CRITICAL RULE**: **NEVER** post a comment with an unresolved/fake mention. If a mention cannot be resolved, **ASK the user** to clarify before posting.

---

## Why MCP is Better Than CLI for Mentions

After deep research, **MCP is the ONLY reliable way** to handle mentions:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **MCP `core_get_identity_ids`** | Direct GUID resolution, official API | None | **USE THIS** |
| CLI `az devops user list` | Available | No direct identity search, slow | Don't use |
| Hardcoded GUIDs | Fast | GUIDs change, unreliable | **NEVER** |
| Plain text @mentions | Easy | NO notifications sent | **NEVER** |

**Conclusion**: Always use `mcp__azure-devops__core_get_identity_ids` for mention resolution.

---

## Strict Enforcement Guard

```
┌─────────────────────────────────────────────────────────────────┐
│         MENTION VALIDATION GUARD (MANDATORY CHECK)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE calling wit_add_work_item_comment:                      │
│                                                                  │
│  1. SCAN comment text for @mentions                             │
│  2. IF mentions found:                                          │
│     a. Call core_get_identity_ids for EACH mention              │
│     b. IF ANY resolution fails → STOP, ASK USER                 │
│     c. IF ALL resolved → Convert to HTML format                 │
│  3. ONLY THEN post the comment with format: "html"              │
│                                                                  │
│  BLOCKING RULE:                                                 │
│  If step 2b fails, you MUST NOT post the comment.               │
│  Ask user for clarification instead.                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

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

## Common Mention Failures and Fixes

### Issue 1: API Returns Empty Array

**Problem**: `core_get_identity_ids` returns empty identities array.

**Causes**:
1. Search term too short (use at least 3 characters)
2. User not in organization
3. Typo in name

**Fix**:
```javascript
// Try with email if name fails
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "melshahed@pearlpixels.com"  // Try full email
})

// Or try with full name
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "Mahmoud Elshahed"  // Try display name
})
```

### Issue 2: Multiple Matches

**Problem**: API returns multiple identities.

**Fix**: Present options to user and wait for selection.

```
Found multiple users matching "ahmed":
1. Ahmed Abdelkhaleq (alakosha@pearlpixels.com)
2. Ahmed Mohamed (amohamed@pearlpixels.com)

Which one did you mean?
```

### Issue 3: HTML Not Rendering

**Problem**: Mention appears as text, not clickable.

**Fix**: Ensure `format: "html"` is specified:
```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:xxx\">@Name</a>",
  "format": "html"  // ← REQUIRED!
})
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
│  │  • Mahmoud Elshahed (@mahmoud)                          │    │
│  │  • Mohamed Afifi (@mohamed)                             │    │
│  │  • [Someone else - please provide full name/email]"     │    │
│  │                                                         │    │
│  │ WAIT for user response before proceeding!               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: CONVERT TO HTML FORMAT                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @mahmoud → <a href="#" data-vss-mention="version:2.0,   │    │
│  │            guid:6011f8b0-...">@Mahmoud Elshahed</a>     │    │
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
      "displayName": "Mahmoud Elshahed",
      "uniqueName": "melshahed@pearlpixels.com"
    }
  ]
}

// Expected Response (FAILURE - no match):
{
  "identities": []
}
```

**Fallback Strategy if First Attempt Fails**:

```
1. Try with username: @mahmoud → searchFilter: "mahmoud"
2. If fails, try with FULL EMAIL from team_members.json  ← MOST RELIABLE!
3. If fails, try with full display name
4. If all fail → ASK USER (do not post!)

IMPORTANT: Full email (user@domain.com) has highest success rate!
Tested: "alakosha" failed, "alakosha@pearlpixels.com" succeeded
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
│ • Mahmoud Elshahed (@mahmoud, melshahed@pearlpixels.com)        │
│ • Eslam Hafez (@eslam, ehafez@pearlpixels.com)                  │
│ • Ahmed Abdelkhaleq (@ahmed, alakosha@pearlpixels.com)          │
│ • Yussef Hussein (@yussef, yhussein@pearlpixels.com)            │
│ • Mohamed Afifi (@mohamed)                                      │
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
  "Mahmoud Elshahed"
);
// Result: <a href="#" data-vss-mention="version:2.0,guid:6011f8b0-...">@Mahmoud Elshahed</a>
```

### Step 5: Post Comment with HTML

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "Hey <a href=\"#\" data-vss-mention=\"version:2.0,guid:6011f8b0-xxxx\">@Mahmoud Elshahed</a>, please review.",
  "format": "html"  // IMPORTANT: Must specify html format
})
```

---

## Team Members Cache (TaqaTechno)

Pre-defined team members for faster resolution and suggestion:

| Display Name | Search Terms | Email | Status |
|--------------|--------------|-------|--------|
| Ahmed Abdelkhaleq | ahmed, alakosha | alakosha@pearlpixels.com | Active |
| Eslam Hafez Mohamed | eslam, ehafez | ehafez@pearlpixels.com | Active |
| Yussef Hussein | yussef, yhussein | yhussein@pearlpixels.com | Active |
| Sameh Abdlal | sameh, sabdlal | sabdlal@pearlpixels.com | Active |
| Mahmoud Elshahed | mahmoud, melshahed | melshahed@pearlpixels.com | Active |
| Mohamed Afifi | mohamed, mafifi | mafifi@pearlpixels.com | Active |
| Hossam Moussa | hossam, hmoussa | hmoussa@pearlpixels.com | Active |
| Amr Saber | amr, asaber | asaber@pearlpixels.com | Active |
| Sara Ahmed | sara, sahmed | sahmed@pearlpixels.com | Active |
| Omar Khaled | omar, okhaled | okhaled@pearlpixels.com | Active |

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
     1. Mohamed Afifi
     2. Moussa Hassan
     Which one did you mean?"
  → WAIT for user selection
```

### Rule 3: Confirm Before Posting

```
IF user provides partial name and match is uncertain:
  → "I found 'Mahmoud Elshahed'. Is this correct?"
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
// Returns: { id: "6011f8b0-...", displayName: "Mahmoud Elshahed" }
```

```
Step 3: ✅ @mahmoud resolved to Mahmoud Elshahed

Step 4: Posting comment...
```

```javascript
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Relief Center",
  "workItemId": 1234,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:6011f8b0-xxxx\">@Mahmoud Elshahed</a> please review this.",
  "format": "html"
})
```

```
✅ Comment added to #1234!
   Mahmoud Elshahed will receive a notification.
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
• Ahmed Abdelkhaleq (@ahmed)
• Eslam Hafez (@eslam)
• Mahmoud Elshahed (@mahmoud)
• Mohamed Afifi (@mohamed)
• Yussef Hussein (@yussef)

Please provide the correct name or email, and I'll add the comment.
```

**User**: "I meant @mahmoud"

**Claude**:
```
Step 2: Resolving @mahmoud...
✅ Found: Mahmoud Elshahed

Posting comment...

✅ Comment added to #1234!
   Mahmoud Elshahed will receive a notification.
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

## Debugging Mention Issues

### Debug Checklist

```
□ 1. Is searchFilter at least 3 characters?
□ 2. Did API return any identities?
□ 3. Is the GUID valid format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)?
□ 4. Is format: "html" specified in comment API?
□ 5. Is the HTML properly escaped in the comment string?
□ 6. Does the data-vss-mention attribute have correct format?
```

### Test Command

To test if mentioning is working:

```
"Add a test comment on work item #[ID] mentioning @ahmed"
```

Expected behavior:
1. Claude should call `core_get_identity_ids({ searchFilter: "ahmed" })`
2. Claude should receive a GUID
3. Claude should format HTML with the GUID
4. Claude should post with `format: "html"`
5. Ahmed should receive an Azure DevOps notification

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
4. **rules/business_rules.md** - Overall business rules

---

*Mention Processor v2.0 - Strict Enforcement*
*Part of DevOps Plugin v3.0 Enhancement*
*TaqaTechno - December 2025*
