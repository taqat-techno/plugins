#!/usr/bin/env bash
# PostToolUseFailure hook: Azure DevOps error recovery guidance
# Reads JSON on stdin. Matches error output against known patterns.
# Exit 0 always. Stdout becomes conversation context.

INPUT=$(cat)

# MCP server unavailable
if echo "$INPUT" | grep -qiE 'MCP.*unavailable|server.*not.*running|connection.*refused|ECONNREFUSED'; then
  echo "[DevOps] MCP server appears unavailable. See devops/MCP_FAILURE_MODES.md for recovery."
  echo "Quick fix: Run /init to reinstall. CLI fallback: use /cli-run for basic operations."
  exit 0
fi

# Authentication errors (401)
if echo "$INPUT" | grep -qiE '401|Unauthorized|authentication.failed|token.expired'; then
  echo "[DevOps] Authentication error. Your Personal Access Token (PAT) may have expired."
  echo "Regenerate at: https://dev.azure.com/{org}/_usersSettings/tokens"
  echo "Check ~/.claude/devops.md for your organization name."
  exit 0
fi

# Permission errors (403)
if echo "$INPUT" | grep -qiE '403|Forbidden|permission.denied|access.denied'; then
  echo "[DevOps] Permission denied. Verify your PAT has required scopes:"
  echo "  - Code (Read/Write)"
  echo "  - Work Items (Read/Write)"
  echo "  - Build (Read/Execute)"
  exit 0
fi

# Not found errors (404)
if echo "$INPUT" | grep -qiE '404|Not.Found|does.not.exist|TF401019'; then
  echo "[DevOps] Resource not found. Verify:"
  echo "  1) Project name is correct"
  echo "  2) Work item ID exists"
  echo "  3) Repository name matches exactly"
  exit 0
fi

# Work item validation errors
if echo "$INPUT" | grep -qiE 'VS403507|field.validation|required.field'; then
  echo "[DevOps] Work item validation failed. Check required fields:"
  echo "  - For tasks marked Done: OriginalEstimate and CompletedWork are required"
  echo "  - For bugs: Severity and Priority are often required"
  exit 0
fi

# Rate limiting (429)
if echo "$INPUT" | grep -qiE '429|rate.limit|too.many.requests'; then
  echo "[DevOps] Rate limit reached. Wait a moment before retrying, or batch operations together."
  exit 0
fi

# WIQL query errors
if echo "$INPUT" | grep -qiE 'WIQL|query.syntax|invalid.query'; then
  echo "[DevOps] WIQL query error. Common fixes:"
  echo "  - Use @Me for current user"
  echo "  - Use @Today for today's date"
  echo "  - Enclose field names in []"
  echo "  - Use single quotes for string values"
  exit 0
fi

# Build failures
if echo "$INPUT" | grep -qiE 'build.failed|pipeline.failed|test.failure'; then
  echo "[DevOps] Build/pipeline failure detected. To investigate:"
  echo "  1) Check build logs"
  echo "  2) Review test results"
  echo "  3) Consider creating a bug to track the fix"
  exit 0
fi

# No match -- output nothing (don't add noise)
exit 0
