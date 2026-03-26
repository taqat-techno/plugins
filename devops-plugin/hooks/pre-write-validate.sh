#!/usr/bin/env bash
# PreToolUse hook: Inject validation context for Azure DevOps write operations
# Reads JSON on stdin (tool_name + tool_input from Claude Code)
# Exit 0 = allow with context, Exit 2 = block with message
#
# Design: Hooks inject REMINDERS. The LLM + rules/ + data/ do the actual validation.
# Only hard-block for clear violations detectable in bash (bug creation authority).

INPUT=$(cat)

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="$HOME/.claude/devops.md"

# Extract tool name
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"tool_name"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

case "$TOOL_NAME" in
  mcp__azure-devops__wit_update_work_item)
    # Extract target state if this is a state change
    TARGET_STATE=""
    if echo "$INPUT" | grep -q '"System\.State"'; then
      TARGET_STATE=$(echo "$INPUT" | grep -oE '"value"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"value"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')
    fi

    # HARD BLOCK: Close/Remove restriction (universalRules)
    if [ -n "$TARGET_STATE" ] && [ -f "$PROFILE" ]; then
      USER_ROLE=$(grep -E '^role:' "$PROFILE" | head -1 | sed 's/^role:[[:space:]]*//' | sed 's/[[:space:]]*$//' | tr -d '"')
      case "$TARGET_STATE" in
        Closed|Removed)
          case "$USER_ROLE" in
            pm|lead) ;; # allowed
            *)
              echo "[DevOps] BLOCKED: Role '$USER_ROLE' cannot transition to '$TARGET_STATE'. Only PM/Lead can close or remove work items. See data/state_machine.json universalRules."
              exit 2
              ;;
          esac
          ;;
      esac
    fi

    # Soft reminder for other state changes
    if [ -n "$TARGET_STATE" ]; then
      echo "[DevOps] State change to '$TARGET_STATE' detected. Follow data/state_machine.json pre-flight: check role permissions, required fields, and confirm via rules/write-gate.md."
    fi
    exit 0
    ;;

  mcp__azure-devops__wit_create_work_item)
    # Extract work item type
    WI_TYPE=$(echo "$INPUT" | grep -oE '"workItemType"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"workItemType"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

    # HARD BLOCK: Bug creation authority (developers cannot create bugs)
    if [ "$WI_TYPE" = "Bug" ] && [ -f "$PROFILE" ]; then
      USER_ROLE=$(grep -E '^role:' "$PROFILE" | head -1 | sed 's/^role:[[:space:]]*//' | sed 's/[[:space:]]*$//' | tr -d '"')
      case "$USER_ROLE" in
        developer|backend|fullstack|frontend|devops)
          echo "[DevOps] BLOCKED: Role '$USER_ROLE' cannot create Bugs. Create a [Dev-Internal-fix] Task instead. See data/state_machine.json businessRules.bugCreationAuthority."
          exit 2
          ;;
      esac
    fi

    # Hierarchy reminder for child types
    case "$WI_TYPE" in
      Task|Bug|Enhancement)
        echo "[DevOps] Creating $WI_TYPE — ensure parent User Story/PBI is linked per data/hierarchy_rules.json." ;;
      "User Story"|"Product Backlog Item")
        echo "[DevOps] Creating $WI_TYPE — ensure parent Feature is linked per data/hierarchy_rules.json." ;;
      Feature)
        echo "[DevOps] Creating Feature — ensure parent Epic is linked per data/hierarchy_rules.json." ;;
    esac
    exit 0
    ;;

  mcp__azure-devops__wit_add_work_item_comment)
    # HARD BLOCK: Unresolved @mentions
    if echo "$INPUT" | grep -qE '@[a-zA-Z]'; then
      if ! echo "$INPUT" | grep -q 'data-vss-mention'; then
        echo "[DevOps] BLOCKED: Unresolved @mentions detected. Resolve to GUIDs and use HTML format before posting. See rules/guards.md Guard 2."
        exit 2
      fi
    fi
    exit 0
    ;;

  mcp__azure-devops__repo_create_pull_request)
    # Check if repositoryId is a name instead of GUID
    REPO_ID=$(echo "$INPUT" | grep -oE '"repositoryId"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"repositoryId"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')
    if [ -n "$REPO_ID" ]; then
      if ! echo "$REPO_ID" | grep -qiE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
        echo "[DevOps] repositoryId '$REPO_ID' is not a GUID. Resolve per rules/guards.md Guard 3."
      fi
    fi
    exit 0
    ;;

  *)
    exit 0
    ;;
esac
