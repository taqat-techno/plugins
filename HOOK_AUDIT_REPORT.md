# Complete Hook Ecosystem Audit Report

---

## TRIAGE SECTION

### A. Plugins Found: **13** (12 plugins + 1 _infrastructure pseudo-plugin)
- 9 cached/active in Claude Code runtime
- 4 source-only (ntfy, pandoc, paper, remotion — not running)

### B. Hooks Found: **45 total**
- 10 command-type hooks (spawn subprocess)
- 32 prompt-type hooks (LLM inference)
- 3 SessionStart hooks (2 command, 1 prompt)
- 5 PreToolUse hooks (3 command, 2 prompt from uncached plugins)
- 33 PostToolUse hooks (3 command, 30 prompt)
- 1 PostToolUseFailure hook (1 command)

### C. 10 Highest-Risk Hooks

| # | Hook | Plugin | Risk | Reason |
|---|------|--------|------|--------|
| 1 | `session-start.sh` | devops | **CRITICAL** | Spawns Python subprocesses, reads config files, 500ms+ |
| 2 | `session_start.py` | odoo-frontend | **CRITICAL** | Python spawn, directory scanning, JSON output dependency |
| 3 | `pre_write_check.py` | odoo-frontend | **HIGH** | Blocking (exit 2), fires on every Write/Edit |
| 4 | `guard_core_odoo.py` | odoo-upgrade | **HIGH** | Blocking (exit 2), fires on every Write/Edit, config file load |
| 5 | `pre-write-validate.sh` | devops | **HIGH** | Blocking (exit 2), reads profile, role-based logic |
| 6 | `pre-bash-check.sh` | devops | **MEDIUM** | Fires on EVERY Bash command, no `if` filter |
| 7 | `post-bash-suggest.sh` | devops | **MEDIUM** | Fires on EVERY Bash command, no `if` filter |
| 8 | `check_odoo19_compat.py` | odoo-upgrade | **MEDIUM** | Python spawn on every Write/Edit, plain text output |
| 9 | `post_write_check.py` | odoo-frontend | **MEDIUM** | Python spawn on every Write/Edit, plain text output |
| 10 | `error-recovery.sh` | devops | **LOW** | Only fires on ADO MCP failures (rare event) |

### D. 5 Most Likely Session-Breaking Hooks

| # | Hook | Why It Breaks Sessions |
|---|------|----------------------|
| 1 | `session-start.sh` (devops) | Spawns 2+ Python subprocesses; if Python unavailable or config corrupt → error |
| 2 | `session_start.py` (odoo-frontend) | Python3 dependency; if missing → "command not found" |
| 3 | `session-check.sh` (pandoc, SOURCE ONLY) | References `../_infrastructure/hook-runner.sh` — path traversal blocked in cache |
| 4 | `pandoc-context.sh` (pandoc, SOURCE ONLY) | Same `../` path traversal issue |
| 5 | Upgrade SessionStart prompt | `"matcher": "startup|resume"` — fires on resume too, potential double-fire |

### E. 5 Most Overlapping/Redundant Hooks

| # | Pattern | Plugins | Issue |
|---|---------|---------|-------|
| 1 | Bash command monitoring | devops (pre + post), odoo-service (2 prompts) | 4 hooks fire on every Bash command |
| 2 | Write\|Edit general | odoo-frontend (pre + post), odoo-upgrade (pre + post) | 4 command hooks fire on every file edit |
| 3 | `__manifest__.py` advisory | odoo-service prompt | Was 4 plugins, now 1 — dedup already done |
| 4 | `models/*.py` advisory | odoo-service prompt | Was 3 plugins, now 1 — dedup already done |
| 5 | `**/tests/test_*.py` | odoo-test (2 prompts: edit + write) | Both fire on Write to test files |

### F. Minimum Stable Hook Set

| Hook | Plugin | Type | Why Essential |
|------|--------|------|--------------|
| `guard_core_odoo.py` | odoo-upgrade | PreToolUse blocking | Prevents editing core Odoo (data safety) |
| `session_start.py` | odoo-frontend | SessionStart | Odoo version context injection |

**2 hooks.** Everything else can be disabled without safety impact. The `guard_core_odoo.py` prevents data loss. The `session_start.py` provides critical Odoo version context that affects code generation quality.

---

## 1. Executive Summary

The hook ecosystem has **45 hooks across 13 plugins**, but only **33 hooks across 9 plugins are actually running** (4 plugins aren't cached). The architecture is split between 10 command hooks (subprocess-based) and 32 prompt hooks (LLM inference).

**Key findings:**
- **2 of 10 command hooks output official JSON format** — the rest output plain text
- **32 prompt hooks have no explicit timeout** — relying on 600s default
- **4 hooks fire on every Bash command** — significant overhead
- **4 command hooks fire on every Write/Edit** — ~400-1000ms combined latency
- **26 hooks use non-standard `name`/`description` fields** — potential schema validation risk
- **0 hooks use the `if` field** for fine-grained argument filtering
- **2 hooks have internal timeout guards** — only in odoo-frontend plugin
- **3 blocking hooks are correctly implemented** — exit 2 with stderr messaging
- **Source has `../` references that break in cache** — pandoc plugin affected

---

## 2. Plugin Discovery Summary

| Plugin | Version | Cached | Hooks | Command | Prompt | Blocking |
|--------|---------|--------|-------|---------|--------|----------|
| devops-plugin | 6.3.0 | Yes | 5 | 5 | 0 | 1 |
| ntfy-plugin | 3.0.0 | **No** | 2 | 0 | 2 | 0 |
| odoo-docker-plugin | 2.1.0 | Yes | 6 | 0 | 6 | 0 |
| odoo-frontend-plugin | 8.4.0 | Yes | 3 | 3 | 0 | 1 |
| odoo-i18n-plugin | 2.0.0 | Yes | 2 | 0 | 2 | 0 |
| odoo-report-plugin | 2.1.0 | Yes | 2 | 0 | 2 | 0 |
| odoo-security-plugin | 2.1.0 | Yes | 3 | 0 | 3 | 0 |
| odoo-service-plugin | 3.0.0 | Yes | 6 | 0 | 6 | 0 |
| odoo-test-plugin | 2.0.0 | Yes | 2 | 0 | 2 | 0 |
| odoo-upgrade-plugin | 5.1.0 | Yes | 4 | 2 | 2 | 1 |
| pandoc-plugin | 2.1.0 | **No** | 2 | 2 | 0 | 0 |
| paper-plugin | 3.0.0 | **No** | 2 | 0 | 2 | 0 |
| remotion-plugin | 2.1.0 | **No** | 5 | 0 | 5 | 0 |
| **TOTAL** | | 9/13 | **44** | **10** | **32** | **3** |

---

## 3. Full Hook Inventory

### SessionStart Hooks (3 total)

| # | Plugin | Type | Matcher | Timeout | Output Format | Internal Guard | Risk |
|---|--------|------|---------|---------|---------------|----------------|------|
| 1 | devops | command | `startup` | 10s | JSON (hookSpecificOutput) | No | CRITICAL |
| 2 | odoo-frontend | command | `startup` | 10s | JSON (hookSpecificOutput) | Yes (8s) | CRITICAL |
| 3 | odoo-upgrade | prompt | `startup\|resume` | 5s | N/A (prompt) | N/A | LOW |

### PreToolUse Hooks (5 total, 3 cached)

| # | Plugin | Type | Matcher | Timeout | Blocking | Cached | Risk |
|---|--------|------|---------|---------|----------|--------|------|
| 1 | devops | command | `Bash` | 10s | No | Yes | MEDIUM |
| 2 | devops | command | ADO MCPs | 10s | **Yes** | Yes | HIGH |
| 3 | odoo-frontend | command | `Write\|Edit` | 10s | **Yes** | Yes | HIGH |
| 4 | odoo-upgrade | command | `Write\|Edit` | 10s | **Yes** | Yes | HIGH |
| 5 | pandoc | command | `Bash` | 13s | No | **No** | N/A |

### PostToolUse Hooks (33 total, 28 cached)

| # | Plugin | Type | Matcher | Path Filter | Timeout | Risk |
|---|--------|------|---------|-------------|---------|------|
| 1 | devops | command | Bash | — | 10s | MEDIUM |
| 2 | odoo-frontend | command | Write\|Edit | — | 10s | MEDIUM |
| 3 | odoo-upgrade | command | Write\|Edit | — | 10s | MEDIUM |
| 4 | odoo-upgrade | prompt | Bash | — | 10s | LOW |
| 5 | odoo-docker | prompt | startup (SS) | — | — | LOW |
| 6 | odoo-docker | prompt | Write\|Edit | docker-compose* | — | LOW |
| 7 | odoo-docker | prompt | Write\|Edit | Dockerfile* | — | LOW |
| 8 | odoo-docker | prompt | Write\|Edit | nginx*.conf | — | LOW |
| 9 | odoo-docker | prompt | Write\|Edit | .env | — | LOW |
| 10 | odoo-docker | prompt | Write\|Edit | entrypoint*.sh | — | LOW |
| 11 | odoo-i18n | prompt | Write\|Edit | *.po/*.pot | — | LOW |
| 12 | odoo-i18n | prompt | Write | (new files) | — | LOW |
| 13 | odoo-report | prompt | Write\|Edit | mail_template*.xml | — | LOW |
| 14 | odoo-report | prompt | Write\|Edit | report*/**/*.xml | — | LOW |
| 15 | odoo-security | prompt | Write\|Edit | controllers/*.py | — | LOW |
| 16 | odoo-security | prompt | Write\|Edit | ir.model.access.csv | — | LOW |
| 17 | odoo-security | prompt | Write\|Edit | wizard*/*.py | — | LOW |
| 18 | odoo-service | prompt | Write\|Edit | __manifest__.py | — | LOW |
| 19 | odoo-service | prompt | Write\|Edit | models/*.py | — | LOW |
| 20 | odoo-service | prompt | Write\|Edit | requirements*.txt | — | LOW |
| 21 | odoo-service | prompt | Write\|Edit | conf/*.conf | — | LOW |
| 22 | odoo-service | prompt | Bash | — | — | LOW |
| 23 | odoo-service | prompt | Bash | — | — | LOW |
| 24 | odoo-test | prompt | Write\|Edit | tests/test_*.py | — | LOW |
| 25 | odoo-test | prompt | Write | tests/test_*.py | — | LOW |
| *26* | *paper* | *prompt* | *Write\|Edit* | *html/xml/jsx...* | *—* | *N/A (not cached)* |
| *27* | *paper* | *prompt* | *Write\|Edit* | *css/scss/sass...* | *—* | *N/A* |
| *28-32* | *remotion* | *prompt* | *various* | *tsx/jsx/py/json* | *—* | *N/A* |
| *33* | *ntfy* | *prompt* | *Bash* | *—* | *—* | *N/A* |

### PostToolUseFailure Hooks (1 total)

| # | Plugin | Type | Matcher | Timeout | Risk |
|---|--------|------|---------|---------|------|
| 1 | devops | command | `mcp__azure-devops__.*` | 10s | LOW |

---

## 4. Hook Grading Table

| Hook | Plugin | Stability | Session Risk | Blocking Fit | Observability | Efficiency | Arch Fit | Disposition |
|------|--------|-----------|-------------|-------------|---------------|------------|----------|-------------|
| session-start.sh | devops | C | HIGH | N/A | B | D | C | **Optimize** |
| session_start.py | odoo-frontend | B | HIGH | N/A | A | B | B | **Keep** |
| pre-bash-check.sh | devops | B | LOW | Poor (never blocks) | C | D | D | **Add `if` filter** |
| pre-write-validate.sh | devops | B | LOW | Good | C | B | A | **Keep** |
| pre_write_check.py | odoo-frontend | A | LOW | Good | B | B | A | **Keep** |
| guard_core_odoo.py | odoo-upgrade | A | LOW | Good | C | B | A | **Keep** |
| post-bash-suggest.sh | devops | B | LOW | N/A | C | D | D | **Add `if` filter** |
| post_write_check.py | odoo-frontend | B | LOW | N/A | C | C | B | **Fix JSON output** |
| check_odoo19_compat.py | odoo-upgrade | B | LOW | N/A | C | C | B | **Fix JSON output** |
| error-recovery.sh | devops | B | LOW | N/A | C | A | A | **Keep** |
| All prompt hooks (32) | various | A | NONE | N/A | D | C* | C | **Evaluate for SKILL.md** |

*Prompt hooks: Zero subprocess risk but add LLM inference latency (default 30s timeout per prompt hook type).*

**Grades: A=Excellent, B=Good, C=Needs Improvement, D=Poor**

---

## 5. Highest-Risk Hooks Ranked

| Rank | Hook | Risk Score | Primary Risk | Mitigation |
|------|------|-----------|-------------|------------|
| 1 | devops/session-start.sh | 9/10 | Python subprocess spawns at startup | Convert to static JSON or reduce Python calls |
| 2 | odoo-frontend/session_start.py | 7/10 | Python3 dependency at startup | Already has timeout guard; consider static output |
| 3 | pandoc/session-check.sh (SOURCE) | 10/10 | `../` path traversal breaks in cache | Fix path or don't cache |
| 4 | pandoc/pandoc-context.sh (SOURCE) | 10/10 | `../` path traversal breaks in cache | Fix path or don't cache |
| 5 | odoo-frontend/pre_write_check.py | 5/10 | Blocking on every Write/Edit | Well-implemented; keep |
| 6 | odoo-upgrade/guard_core_odoo.py | 5/10 | Blocking on every Write/Edit | Config file dependency; keep |
| 7 | devops/pre-bash-check.sh | 4/10 | Fires on every Bash (overhead) | Add `if` filter |
| 8 | devops/post-bash-suggest.sh | 4/10 | Fires on every Bash (overhead) | Add `if` filter |
| 9 | odoo-upgrade/check_odoo19_compat.py | 3/10 | Python spawn on every Write/Edit | Plain text output |
| 10 | odoo-frontend/post_write_check.py | 3/10 | Python spawn on every Write/Edit | Plain text output |

---

## 6. Overlap and Duplication Findings

### Active Overlaps (cached plugins)

| Pattern | Hooks Firing | Combined Overhead |
|---------|-------------|-------------------|
| **Every Bash command** | devops pre-bash-check (cmd), devops post-bash-suggest (cmd), odoo-service venv-change (prompt), odoo-service port-conflict (prompt), odoo-upgrade bash-compat (prompt) | 2 subprocesses + 3 LLM inferences |
| **Every Write\|Edit** | odoo-frontend pre_write_check (cmd), odoo-upgrade guard_core_odoo (cmd), odoo-frontend post_write_check (cmd), odoo-upgrade check_odoo19_compat (cmd) | 4 Python subprocesses |
| **tests/test_*.py write** | odoo-test test-file-changed (prompt), odoo-test test-file-init-reminder (prompt) | 2 LLM inferences for same event |

### Previous Overlaps (already resolved)

| Pattern | Before | After | Status |
|---------|--------|-------|--------|
| `__manifest__.py` | 4 plugins | 1 (odoo-service) | Resolved |
| `models/*.py` | 3 plugins | 1 (odoo-service) | Resolved |
| `docker-compose*.yml` | 2 plugins | 1 (odoo-docker) | Resolved |
| `Dockerfile*` | 2 plugins | 1 (odoo-docker) | Resolved |
| `requirements*.txt` | 2 plugins | 1 (odoo-service) | Resolved |
| `conf/*.conf` | 2 plugins | 1 (odoo-service) | Resolved |
| `ir.model.access.csv` | 2 plugins | 1 (odoo-security) | Resolved |

---

## 7. SessionStart-Specific Findings

| Finding | Severity | Details |
|---------|----------|---------|
| **devops session-start.sh spawns Python** | HIGH | 2+ Python subprocesses for config validation. Should be pre-computed or static. |
| **Output format now compliant** | RESOLVED | Both command SessionStart hooks now output JSON with `hookSpecificOutput`. |
| **odoo-frontend has internal timeout** | GOOD | 8-second `threading.Timer` prevents hangs. |
| **devops has NO internal timeout** | MEDIUM | Relies solely on hooks.json 10s timeout. If Python subprocess hangs, it waits full 10s. |
| **odoo-upgrade SessionStart fires on resume** | LOW | `matcher: "startup|resume"` means prompt fires on both. Harmless but unnecessary. |
| **Official pattern: static cat << EOF** | REFERENCE | Official marketplace SessionStart hooks use zero-cost static output. Custom hooks do filesystem I/O. |

---

## 8. PreToolUse-Specific Findings

| Finding | Severity | Details |
|---------|----------|---------|
| **3 blocking hooks correctly implemented** | GOOD | All use exit 2 with stderr messaging. |
| **pre-bash-check.sh fires on ALL Bash** | MEDIUM | Should use `if` field to filter for `git` commands only. |
| **2 blocking hooks fire on every Write/Edit** | EXPECTED | guard_core_odoo + pre_write_check run in parallel (documented behavior). |
| **pre_write_check.py has fast-path** | GOOD | String check before regex avoids expensive path for non-XML files. |
| **guard_core_odoo.py loads config file** | MEDIUM | Reads `odoo-upgrade.config.json` on every invocation. Could be cached. |
| **No hooks use `if` field** | MEDIUM | The `if` field (v2.1.85+) would reduce subprocess spawns significantly. |

---

## 9. PostToolUse-Specific Findings

| Finding | Severity | Details |
|---------|----------|---------|
| **3 command hooks output plain text** | MEDIUM | post_write_check.py, check_odoo19_compat.py, post-bash-suggest.sh don't use hookSpecificOutput JSON. |
| **28 prompt hooks have no explicit timeout** | LOW | Default is 30s for prompt hooks (per docs). Acceptable for advisory. |
| **Bash matcher prompts fire on every command** | MEDIUM | 3 prompt hooks for Bash (service venv, service port, upgrade compat). |
| **Path-filtered prompts are well-targeted** | GOOD | odoo-docker, odoo-security, odoo-report use specific path patterns. |
| **Prompt hooks use non-standard fields** | LOW | `name`, `description`, `path`, `filePattern` may or may not cause issues. |

---

## 10. Efficiency and Latency Findings

### Per-Event Latency Budget

| Event | Subprocess Hooks | Prompt Hooks | Estimated Total Latency |
|-------|-----------------|-------------|------------------------|
| **SessionStart** | 2 (devops ~500ms, frontend ~100ms) | 1 (upgrade ~2s) | ~2.6s |
| **Bash command** | 2 (devops pre + post ~200ms each) | 3 (service + upgrade prompts) | ~6.4s |
| **Write\|Edit** | 4 (~200ms each) | up to 10 path-filtered prompts | ~1s (commands) + variable (prompts) |
| **ADO MCP write** | 1 (~100ms) | 0 | ~100ms |

### Efficiency Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| **4 Python spawns per Write/Edit** | ~800ms added latency | Combine into single script with dispatch |
| **2 Bash spawns per Bash command** | ~400ms added latency | Add `if` filter for `git` commands |
| **3 prompt hooks per Bash command** | ~6s LLM inference overhead | Remove or make conditional |
| **Config file load per Write/Edit** | ~50ms extra per guard_core_odoo | Cache config at session level |
| **No deduplication for same-event prompts** | Multiple LLM calls | Merge related prompt content |

---

## 11. Hooks That Should Remain Blocking

| Hook | Plugin | Justification |
|------|--------|--------------|
| `guard_core_odoo.py` | odoo-upgrade | **Essential safety.** Prevents editing core Odoo framework files that would break upgrades. Well-implemented with config-based patterns. |
| `pre_write_check.py` | odoo-frontend | **Code quality.** Prevents inline JavaScript in XML templates. Has fast-path optimization and internal timeout. |
| `pre-write-validate.sh` | devops | **Access control.** Enforces role-based restrictions on Azure DevOps operations. Only fires on specific MCP tools. |

---

## 12. Hooks That Should Become Warning-Only

| Hook | Plugin | Current | Recommended | Reason |
|------|--------|---------|-------------|--------|
| `pre-bash-check.sh` | devops | Advisory (exit 0 always) | **Add `if` filter** | Already advisory but fires on ALL Bash commands. Add `"if": "Bash(git *)"` to only fire on git commands. |

No other hooks need reclassification — the 3 blockers are appropriate, and all others are already advisory.

---

## 13. Hooks That Should Be Merged

| Merge Target | Source Hooks | Reason |
|-------------|-------------|--------|
| Single Bash post-hook | devops/post-bash-suggest.sh + odoo-service/venv-change + odoo-service/port-conflict | 3 hooks fire on every Bash command. Combine into one prompt that covers git workflow, pip changes, and port conflicts. |
| Single test advisory | odoo-test/test-file-changed + odoo-test/test-file-init-reminder | Both fire on test file writes. Merge into one prompt covering both edit reminders and __init__.py import warning. |

---

## 14. Hooks That Should Be Removed

| Hook | Plugin | Reason |
|------|--------|--------|
| odoo-service/venv-change prompt | odoo-service | Low value — fires on every Bash, most are not pip operations. Merge into post-bash-suggest or remove. |
| odoo-service/port-conflict prompt | odoo-service | Low value — fires on every Bash. Port conflicts are self-evident from error messages. |
| odoo-upgrade/bash-compat prompt | odoo-upgrade | Low value — fires on every Bash to check for compat errors that are already visible in output. |
| odoo-i18n/i18n-general-reminder prompt | odoo-i18n | Low value — fires on every new file Write. Too generic to be actionable. Better as SKILL.md context. |

**4 hooks recommended for removal.** All are prompt-type, so removal has zero stability risk.

---

## 15. Minimal Viable Stable Hook Set

| # | Hook | Plugin | Event | Type | Why Essential |
|---|------|--------|-------|------|--------------|
| 1 | `guard_core_odoo.py` | odoo-upgrade | PreToolUse | Blocking | Prevents core Odoo edits (data safety) |
| 2 | `session_start.py` | odoo-frontend | SessionStart | Context | Injects Odoo version info for code generation |
| 3 | `pre_write_check.py` | odoo-frontend | PreToolUse | Blocking | Prevents inline JS in XML (code quality) |

**3 hooks.** This set provides safety (core protection), quality (no inline JS), and context (version detection). All other hooks add value but are not essential for stable operation.

---

## 16. Recommended Remediation Priorities

### Priority 1: Fix Remaining Plain Text Output (HIGH)
**Hooks:** `post_write_check.py`, `check_odoo19_compat.py`, `post-bash-suggest.sh`, `pre-bash-check.sh`, `pre-write-validate.sh`, `error-recovery.sh`
**Action:** Convert stdout output to JSON `{"hookSpecificOutput": {"additionalContext": "..."}}` format.
**Risk:** LOW (only changes output format, not behavior)
**Impact:** Aligns with official Claude Code contract; may improve hook message delivery.

### Priority 2: Add `if` Filter to Bash Hooks (MEDIUM)
**Hooks:** `pre-bash-check.sh`, `post-bash-suggest.sh`
**Action:** Add `"if": "Bash(git *)"` to hooks.json entries.
**Risk:** NONE (reduces hook executions, doesn't change behavior when they do fire)
**Impact:** Eliminates ~90% of unnecessary subprocess spawns on Bash commands.

### Priority 3: Remove Low-Value Bash Prompt Hooks (MEDIUM)
**Hooks:** odoo-service/venv-change, odoo-service/port-conflict, odoo-upgrade/bash-compat
**Action:** Remove from hooks.json.
**Risk:** NONE (prompt hooks, advisory only)
**Impact:** Reduces LLM inference calls on every Bash command.

### Priority 4: Add Internal Timeout Guards (LOW)
**Hooks:** `session-start.sh`, `guard_core_odoo.py`, `check_odoo19_compat.py`
**Action:** Add `threading.Timer` / `timeout` guard matching odoo-frontend pattern.
**Risk:** NONE (fail-open on timeout)
**Impact:** Defense-in-depth against hangs.

### Priority 5: Fix Source `../` References (LOW)
**Files:** pandoc-plugin/hooks/hooks.json
**Action:** Replace `${CLAUDE_PLUGIN_ROOT}/../_infrastructure/hook-runner.sh` with direct `${CLAUDE_PLUGIN_ROOT}/hooks/script.sh` calls.
**Risk:** NONE (pandoc isn't cached anyway)
**Impact:** Prepares pandoc plugin for future caching.

---

## 17. Concrete Next Actions

### Do Now (5 minutes)
1. ✅ SessionStart hooks already output JSON (fixed in this session)
2. ✅ hooks.json schema already cleaned for cached plugins
3. ✅ `python3` already used in cached hooks

### Do Today
4. Remove 3 low-value Bash prompt hooks from cached `odoo-service/hooks.json` and `odoo-upgrade/hooks.json`
5. Add `"if": "Bash(git *)"` to devops pre-bash-check and post-bash-suggest in cached hooks.json
6. Merge odoo-test's 2 test file hooks into 1

### Do This Week
7. Convert remaining 6 command hooks to JSON output format
8. Add internal timeout guards to devops/session-start.sh and odoo-upgrade Python hooks
9. Fix pandoc-plugin source to use direct script paths
10. Update source to match all cache changes

### Do Later
11. Evaluate converting prompt hooks to SKILL.md context
12. Consider consolidating 4 per-Write/Edit Python hooks into 1 dispatcher
13. Implement `if` field filtering for fine-grained hook targeting

---

## 18. Implementation Snippets

### Add `if` filter to devops Bash hooks

```json
{
  "matcher": "Bash",
  "if": "Bash(git *)",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/pre-bash-check.sh\"",
      "timeout": 10
    }
  ]
}
```

### JSON output wrapper for command hooks

For bash hooks, append at the end:
```bash
# Collect output in RESULT variable throughout script
# At the end:
if [ -n "$PYTHON" ]; then
  $PYTHON -c "
import json
msg = '''$RESULT'''
print(json.dumps({'hookSpecificOutput':{'additionalContext': msg.strip()}}))
"
else
  echo "{\"hookSpecificOutput\":{\"additionalContext\":\"\"}}"
fi
exit 0
```

For Python hooks, wrap main output:
```python
import json
# ... hook logic ...
result = "Advisory message here"
print(json.dumps({"hookSpecificOutput": {"additionalContext": result}}))
sys.exit(0)
```

### Internal timeout guard for bash hooks

```bash
# Add near top of script, after INPUT=$(cat)
( sleep 8; kill -9 $$ 2>/dev/null ) &
TIMEOUT_PID=$!
trap "kill $TIMEOUT_PID 2>/dev/null" EXIT
```

### Merge odoo-test hooks into 1

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "prompt",
      "prompt": "Test file changed or created. Reminders:\n- Run coverage: /odoo-test coverage\n- SavepointCase removed in 16+, use TransactionCase\n- NEW files: ensure tests/__init__.py imports it (test runner won't discover without import)"
    }
  ]
}
```
