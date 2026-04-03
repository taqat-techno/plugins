#!/usr/bin/env bash
# PostToolUseFailure hook: Azure DevOps error recovery guidance
# Reads JSON on stdin. Matches error output against known patterns.
# Exit 0 always. Stdout = JSON hookSpecificOutput.

# ── Internal timeout: fail-open after 8 seconds ──────────────────────────
( sleep 8 && kill -9 $$ 2>/dev/null ) &
_TIMEOUT_PID=$!
trap "kill $_TIMEOUT_PID 2>/dev/null" EXIT

# ── JSON output helper ───────────────────────────────────────────────────
emit_json() {
  local msg="$1"
  if command -v python3 &>/dev/null; then
    python3 -c "import json; print(json.dumps({'hookSpecificOutput':{'additionalContext':'''$msg'''.strip()}}))" 2>/dev/null && return
  fi
  echo "{\"hookSpecificOutput\":{\"additionalContext\":\"$msg\"}}"
}

INPUT=$(cat)

# MCP server unavailable
if echo "$INPUT" | grep -qiE 'MCP.*unavailable|server.*not.*running|connection.*refused|ECONNREFUSED'; then
  emit_json "[DevOps] MCP server appears unavailable. Quick fix: Run /init to reinstall. CLI fallback: use /cli-run for basic operations."
  exit 0
fi

# Authentication errors (401)
if echo "$INPUT" | grep -qiE '401|Unauthorized|authentication.failed|token.expired'; then
  emit_json "[DevOps] Authentication error. Your PAT may have expired. Regenerate at dev.azure.com/{org}/_usersSettings/tokens."
  exit 0
fi

# Permission errors (403)
if echo "$INPUT" | grep -qiE '403|Forbidden|permission.denied|access.denied'; then
  emit_json "[DevOps] Permission denied. Verify PAT scopes: Code (Read/Write), Work Items (Read/Write), Build (Read/Execute)."
  exit 0
fi

# Not found errors (404)
if echo "$INPUT" | grep -qiE '404|Not.Found|does.not.exist|TF401019'; then
  emit_json "[DevOps] Resource not found. Verify project name, work item ID, and repository name."
  exit 0
fi

# Work item validation errors
if echo "$INPUT" | grep -qiE 'VS403507|field.validation|required.field'; then
  emit_json "[DevOps] Work item validation failed. Check required fields (OriginalEstimate, CompletedWork for Done; Severity, Priority for Bugs)."
  exit 0
fi

# Rate limiting (429)
if echo "$INPUT" | grep -qiE '429|rate.limit|too.many.requests'; then
  emit_json "[DevOps] Rate limit reached. Wait before retrying or batch operations."
  exit 0
fi

# WIQL query errors
if echo "$INPUT" | grep -qiE 'WIQL|query.syntax|invalid.query'; then
  emit_json "[DevOps] WIQL query error. Use @Me for user, @Today for date, [] for field names, single quotes for strings."
  exit 0
fi

# Build failures
if echo "$INPUT" | grep -qiE 'build.failed|pipeline.failed|test.failure'; then
  emit_json "[DevOps] Build/pipeline failure. Check build logs, review test results, consider creating a bug."
  exit 0
fi

# No match -- output nothing (don't add noise)
exit 0
