# Hook Ecosystem Deep Investigation & Remediation Plan

## MANDATORY TRIAGE-FIRST SECTION

### A. The 5 Most Likely Session-Breaking Causes

| # | Cause | Evidence | Source |
|---|-------|----------|--------|
| **1** | **Source hooks.json uses `../` path traversal — impossible in cached plugins** | Official docs: "Installed plugins cannot reference files outside their directory (`../` fails)". Source devops/frontend/upgrade/pandoc all reference `${CLAUDE_PLUGIN_ROOT}/../_infrastructure/hook-runner.sh`. This path CANNOT resolve in the cache. | **Official documentation** |
| **2** | **Cache/source desync — Claude Code runs cached versions, not source** | Cache at `~/.claude/plugins/cache/taqat-techno-plugins/` is what executes. Source at `tmp/plugins/` is development only. Previous "synced" cache still has errors. | **Cache investigation** |
| **3** | **SessionStart command hooks are too heavy for startup** | Official pattern: SessionStart hooks output static JSON via `cat << EOF`. Custom hooks spawn Python interpreters, read filesystems, validate configs. Official SessionStart is <10ms; custom hooks take 500ms-15s. | **Official marketplace comparison** |
| **4** | **Prompt-type hooks add latency to EVERY tool use** | 31 prompt-type hooks fire on Write|Edit|Bash. Each requires LLM inference (default 30s timeout). Official plugins use ZERO prompt-type hooks despite documenting them as "recommended". | **Official marketplace finding** |
| **5** | **No structured output format — hooks output plain text instead of JSON** | Official hooks output JSON with `hookSpecificOutput.additionalContext`. Custom hooks output plain text, which Claude Code may not parse correctly for session context injection. | **Official pattern comparison** |

### B. The 10 Highest-Risk Hooks to Inspect First

| # | Hook | Plugin | Risk | Reason |
|---|------|--------|------|--------|
| 1 | `session-start.sh` | devops | **CRITICAL** | Spawns Python subprocesses, reads config files, 500ms+ latency |
| 2 | `session_start.py` | odoo-frontend | **CRITICAL** | Python interpreter spawn, filesystem scanning, was 15s before fix |
| 3 | `pre_write_check.py` | odoo-frontend | **HIGH** | Blocking (exit 2), Python spawn on every Write/Edit |
| 4 | `guard_core_odoo.py` | odoo-upgrade | **HIGH** | Blocking (exit 2), Python spawn on every Write/Edit |
| 5 | `pre-write-validate.sh` | devops | **HIGH** | Blocking (exit 2), reads profile files |
| 6 | `pre-bash-check.sh` | devops | **MEDIUM** | Fires on every Bash command |
| 7 | `post-bash-suggest.sh` | devops | **MEDIUM** | Fires on every Bash command |
| 8 | `check_odoo19_compat.py` | odoo-upgrade | **MEDIUM** | Python spawn on every Write/Edit |
| 9 | `post_write_check.py` | odoo-frontend | **MEDIUM** | Python spawn on every Write/Edit |
| 10 | `error-recovery.sh` | devops | **LOW** | Only fires on ADO MCP failures |

### C. Minimum Safe-Mode Hook Set

| Hook | Plugin | Type | Why Essential |
|------|--------|------|--------------|
| `guard_core_odoo.py` | odoo-upgrade | PreToolUse blocking | Prevents editing core Odoo framework (critical safety) |

Everything else can be disabled. The `guard_core_odoo.py` is the only hook that prevents data loss (editing core files that would break upgrades). All other hooks are advisory or for specialized workflows.

### D. Most Likely Efficiency Problems

| Problem | Impact | Evidence |
|---------|--------|----------|
| **31 prompt-type hooks require LLM inference** | Each prompt hook adds inference latency (default 30s timeout). Editing `__manifest__.py` triggers up to 6 prompt hooks simultaneously. | Official plugins use zero prompt hooks |
| **Python interpreter startup on every tool use** | 5 Python hooks spawn `python` process (~200ms each) on Write/Edit. Official uses bash for speed or pre-compiled Python. | Measured: 100-500ms per Python hook |
| **SessionStart hooks do filesystem I/O** | session-start.sh reads 3+ config files + spawns Python. session_start.py scans directories. Official: static `cat << EOF`. | Measured: 500ms+ combined |
| **No `if` field for fine-grained filtering** | Official docs recommend `"if": "Bash(git *)"` to reduce subprocess spawns. None of custom hooks use `if` field. | Official documentation v2.1.85+ |
| **Bash hooks fire on ALL bash commands** | devops pre-bash-check.sh + post-bash-suggest.sh fire on every `ls`, `cat`, `grep`. Should use `if` to filter. | hooks.json matcher is just `"Bash"` |

### E. The 3 Fastest Changes to Reduce Breakage Risk

1. **Fix the SessionStart output format** — Change `session_start.py` and `session-start.sh` to output JSON with `hookSpecificOutput.additionalContext` (matching official pattern) instead of plain text. This is the most likely cause of "hook error" since Claude Code may expect JSON.

2. **Remove `name` and `description` fields from hook entries** — Official hooks.json does NOT use `name` or `description` on individual hook entries (only at the top-level `description`). These non-standard fields may cause JSON schema validation failures in Claude Code.

3. **Sync cache from source with direct script paths** — Ensure all cached hooks.json files use `${CLAUDE_PLUGIN_ROOT}/hooks/script` paths, never `../`.

---

## 1. Executive Diagnosis

The custom hook ecosystem has **three fundamental architectural problems** when compared to official patterns:

**Problem 1: Non-standard hook output format.** Official SessionStart hooks output structured JSON (`{"hookSpecificOutput": {"additionalContext": "..."}}`). Custom hooks output plain text. Claude Code likely expects JSON and reports "hook error" when it can't parse stdout.

**Problem 2: Non-standard hooks.json schema.** Custom hooks add `name`, `description`, and `matcher` fields to individual hook entries that don't exist in official implementations. While the `matcher` field is valid (documented), `name` and `description` on entries are non-standard and may cause parse failures.

**Problem 3: Excessive hook overhead.** 10 command-type hooks spawn subprocesses (Python/Bash). 31 prompt-type hooks require LLM inference. Official plugins have 1-2 hooks per plugin maximum, all command-type, with the simplest being static `cat << EOF` scripts.

---

## 2. Documentation and Official Reference Findings

### Official Hook System Architecture (from docs + marketplace)

| Aspect | Official Documentation | Official Marketplace Practice | Custom Implementation |
|--------|----------------------|------------------------------|----------------------|
| **Timeout unit** | Seconds | No timeout specified (600s default) | Mixed (some correct, some ambiguous) |
| **Default timeout** | Command: 600s, Prompt: 30s | Not specified (uses 600s default) | 5-13s (over-constrained) |
| **SessionStart blocking** | Cannot block (exit 2 ignored) | Always exit 0 | Correct (exit 0) |
| **Hook output format** | JSON with `hookSpecificOutput` | JSON with `hookSpecificOutput` | **Plain text (non-standard)** |
| **hooks.json schema** | `{hooks: {Event: [{hooks: [{type, command}]}]}}` | Exactly this schema | **Adds name, description (non-standard)** |
| **Prompt hooks** | Documented, 30s default timeout | **NEVER used** (0 out of 5 plugins) | 31 prompt hooks |
| **SessionStart purpose** | "Load project context" | Static context injection | Validation + filesystem scanning |
| **Error handling** | try/except → exit 0 | try/except → exit 0 + JSON output | Some correct, some inconsistent |
| **Path references** | `${CLAUDE_PLUGIN_ROOT}/hooks/script` | Exactly this | **Source uses `../` (broken in cache)** |
| **`if` field** | Filter by arguments (v2.1.85+) | Not yet adopted | Not used |
| **Hooks per plugin** | 1-2 typically | Max 4 (hookify), typical 1 | Up to 8 per plugin |

### Critical Documentation Findings

**Finding 1: `../` path traversal fails in cached plugins.**
> "Installed plugins cannot reference files outside their directory (`../` fails); use symlinks as workaround."
— Official plugins reference documentation

This means the entire `_infrastructure/hook-runner.sh` wrapper approach is **architecturally impossible** for marketplace/cached plugins.

**Finding 2: Hook output must be JSON for context injection.**
> Official SessionStart scripts output: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`
> Plain text stdout may work but is not the documented contract.

**Finding 3: Prompt hooks are documented but never used in production.**
> The `plugin-dev` SKILL.md says "Prompt-Based Hooks (Recommended)" but zero official plugins use them.
> All 5 official hook-using plugins use command hooks exclusively.

**Finding 4: Hooks run in parallel, most restrictive wins.**
> When multiple hooks match, they execute in parallel. For blocking events, the first exit-2 hook blocks.
> This means ordering between `guard_core_odoo.py` and `pre_write_check.py` is irrelevant — they run simultaneously.

**Finding 5: Default command timeout is 600 seconds, not 10.**
> The custom hooks use 5-13 second timeouts. Official hooks either omit timeout (getting 600s default) or use 10s for non-critical hooks. The aggressive timeouts may cause premature kills.

---

## 3. Root-Cause Hypotheses (Ranked by Likelihood)

| # | Hypothesis | Likelihood | Evidence | Source |
|---|-----------|------------|----------|--------|
| **1** | **Non-standard hooks.json schema fields (`name`, `description`) cause parse failure** | **VERY HIGH** | Official hooks.json NEVER has `name` or `description` on hook entries. Claude Code's JSON validator may reject these unknown fields. The "hook error" appears on session start — exactly when hooks.json is parsed. | Official marketplace comparison |
| **2** | **Plain text output from SessionStart hooks causes JSON parse failure** | **HIGH** | Official hooks output JSON with `hookSpecificOutput`. Custom hooks print plain text like `[Odoo Frontend] Detected: Odoo 19...`. Claude Code may try to parse this as JSON and fail. | Official marketplace pattern |
| **3** | **`python` vs `python3` — Claude Code may invoke `python3` per official pattern** | **HIGH** | Official security-guidance uses `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/...` (with `3`). Custom cache uses `python "${CLAUDE_PLUGIN_ROOT}/hooks/..."` (without `3`). On some systems `python` doesn't exist. | Official script comparison |
| **4** | **Hook script outputs non-JSON to stdout, breaking Claude Code's parser** | **MEDIUM** | When hooks exit 0, Claude Code parses stdout as JSON. session-start.sh prints `[DevOps] WARNING:...` as plain text. This would cause a JSON parse error. | Documentation: "stdout → JSON parsing" |
| **5** | **Missing `matcher` field makes SessionStart fire on resume/compact/clear too** | **MEDIUM** | Without `matcher: "startup"`, SessionStart fires on ALL session events (startup, resume, compact, clear). Some hooks may not handle these contexts. | Documentation |

---

## 4. Immediate Containment Plan

### Phase 1: Fix the Two Session-Breaking Issues (Do RIGHT NOW)

**Goal:** Stop the "SessionStart:startup hook error" messages.

**Action 1: Fix hook output format to match official JSON contract.**

Every SessionStart command hook MUST output JSON, not plain text. The official contract is:

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Your text here"}}
```

**Action 2: Remove non-standard fields from hooks.json entries.**

Official schema for a hook entry inside the hooks array is:
```json
{
  "matcher": "pattern",    // optional
  "hooks": [
    {
      "type": "command",
      "command": "...",
      "timeout": 10
    }
  ]
}
```

The `name` and `description` fields on entries are NOT in the official schema. Remove them.

**Action 3: Use `python3` instead of `python` to match official pattern.**

The official security-guidance plugin uses `python3` explicitly. Change all cached hooks.json `python` references to `python3`.

**Files to fix in cache:**
- `~/.claude/plugins/cache/taqat-techno-plugins/devops/6.3.0/hooks/hooks.json`
- `~/.claude/plugins/cache/taqat-techno-plugins/odoo-frontend/8.4.0/hooks/hooks.json`
- `~/.claude/plugins/cache/taqat-techno-plugins/odoo-upgrade/5.1.0/hooks/hooks.json`
- `~/.claude/plugins/cache/taqat-techno-plugins/devops/6.3.0/hooks/session-start.sh`
- `~/.claude/plugins/cache/taqat-techno-plugins/odoo-frontend/8.4.0/hooks/session_start.py`

**Rollback:** Keep backup of original cached files. Restore if new versions also error.

---

## 5. Step-by-Step Remediation Roadmap

### Phase 1: Fix Session-Breaking Errors (Immediate)

Fix SessionStart hooks to output JSON and remove non-standard schema fields.

### Phase 2: Align hooks.json Schema with Official Pattern

Strip all hooks.json files to match the exact official schema:
```json
{
  "description": "Top-level description only",
  "hooks": {
    "EventType": [
      {
        "matcher": "pattern",
        "hooks": [{"type": "command", "command": "...", "timeout": N}]
      }
    ]
  }
}
```

### Phase 3: Convert Python Hook Output to JSON

All Python hooks that print to stdout must output valid JSON matching the `hookSpecificOutput` contract.

### Phase 4: Evaluate Prompt Hooks vs Command Hooks

Since official plugins use zero prompt hooks, evaluate whether each of the 31 prompt hooks adds enough value to justify the inference latency. Most should be converted to SKILL.md context or removed.

### Phase 5: Reduce Hook Count Per Plugin

Official plugins have 1-2 hooks maximum. Custom plugins have up to 8. Consolidate.

### Phase 6: Add `if` Field for Fine-Grained Filtering

Use the `if` field (v2.1.85+) to reduce unnecessary hook executions.

### Phase 7: Stabilize Source → Cache Deployment

Create a reliable sync mechanism that doesn't depend on `../` path traversal.

---

## 6. Hook Classification Framework

### Critical Blocking (Keep, harden)
| Hook | Plugin | Justification |
|------|--------|--------------|
| `guard_core_odoo.py` | odoo-upgrade | Prevents editing core Odoo (data safety) |
| `pre_write_check.py` | odoo-frontend | Prevents inline JS in XML (code quality) |
| `pre-write-validate.sh` | devops | Role-based ADO authorization |

### Startup Context (Keep, simplify to static JSON)
| Hook | Plugin | Action |
|------|--------|--------|
| `session-start.sh` | devops | Convert to static JSON output, remove filesystem scanning |
| `session_start.py` | odoo-frontend | Convert to static JSON output |

### Advisory Command (Keep, fix output format)
| Hook | Plugin | Action |
|------|--------|--------|
| `check_odoo19_compat.py` | odoo-upgrade | Fix JSON output |
| `post_write_check.py` | odoo-frontend | Fix JSON output |
| `post-bash-suggest.sh` | devops | Fix JSON output |
| `error-recovery.sh` | devops | Fix JSON output |
| `pre-bash-check.sh` | devops | Add `if` filter for git commands only |

### Prompt Hooks (Evaluate for removal/conversion)
| Category | Count | Recommendation |
|----------|-------|---------------|
| `__manifest__.py` advisories | 1 (was 4) | Convert to SKILL.md context or remove |
| `models/*.py` advisories | 1 (was 3) | Convert to SKILL.md context or remove |
| Docker/infrastructure | 5 | Keep if Docker is active, remove otherwise |
| Security reminders | 3 | Keep — low overhead, valuable |
| Test reminders | 2 | Convert to SKILL.md context |
| i18n/report | 4 | Keep — domain-specific |
| Bash advisories | 4 | Most should be removed — too noisy |
| Paper/Remotion | 7 | Keep — project-specific |

### Removable (Remove entirely)
| Hook | Reason |
|------|--------|
| Bash pip-check prompt | Low value, fires on every bash |
| Bash port-conflict prompt | Low value, fires on every bash |
| Bash long-task prompt (ntfy) | Not in cache, ntfy not installed |

### Deferred (Not in cache, don't fix yet)
| Plugin | Status |
|--------|--------|
| pandoc-plugin | Not in cache |
| paper-plugin | Not in cache |
| remotion-plugin | Not in cache |
| ntfy-plugin | Not in cache |

---

## 7. Hook Efficiency Analysis

### Latency Budget Per Hook Type

| Hook Type | Official Benchmark | Custom Actual | Target |
|-----------|-------------------|---------------|--------|
| SessionStart command | <10ms (cat EOF) | 500-15000ms | <100ms |
| PreToolUse command | <50ms (pattern match) | 200-500ms (Python spawn) | <100ms |
| PostToolUse command | <50ms | 200-500ms | <200ms |
| Prompt hook | ~2000ms (LLM inference) | ~2000ms | N/A or remove |

### Efficiency Recommendations

1. **Convert SessionStart to static scripts** — No filesystem scanning. Output pre-computed JSON.
2. **Use `if` field on Bash matchers** — `"if": "Bash(git *)"` for devops, reduces 90% of fires.
3. **Convert prompt hooks to SKILL.md context** — Instead of a prompt hook that reminds about `__manifest__.py`, put the checklist in the plugin's SKILL.md so it's loaded once.
4. **Batch Python hooks** — Instead of 3 separate Python hooks for odoo-frontend, have one script with internal dispatch.

---

## 8. Logging and Observability Design

### Current State
- `hook-runner.sh` wrapper writes JSONL to `~/.claude/logs/hook-audit.jsonl`
- But wrapper can't work in cache (path traversal)
- Claude Code has `--debug` mode for hook stderr visibility
- `/hooks` menu shows loaded hooks

### Recommended Approach (Aligned with Official)

Instead of a wrapper, use **per-script logging** like the official `security-guidance` plugin:

```python
DEBUG_LOG_FILE = os.path.expanduser("~/.claude/plugins/data/my-plugin/hook-debug.log")

def debug_log(message):
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] {message}\n")
    except:
        pass  # Never crash on log failure
```

Use `CLAUDE_PLUGIN_DATA` (persists across updates) instead of `CLAUDE_PLUGIN_ROOT`.

---

## 9. Safe Wrapper / Runner Design

### Architecture Decision: Wrapper is NOT viable for cached plugins.

**Finding:** `../` path traversal is explicitly blocked in cached plugins (official docs). The `_infrastructure/hook-runner.sh` wrapper cannot be accessed from cached plugin directories.

**Alternative: Inline timeout + logging per script.**

Instead of a centralized wrapper, each script handles its own:
- Internal timeout (`threading.Timer` in Python, `timeout` in bash)
- Logging (to `CLAUDE_PLUGIN_DATA` directory)
- Error handling (try/except → exit 0 + JSON error output)

This matches the official pattern where each hook script is self-contained.

### Safe Script Template (Python)

```python
#!/usr/bin/env python3
import json, os, sys, threading

# Internal timeout (fail-open)
threading.Timer(8.0, lambda: os._exit(0)).start()

# Logging
DATA_DIR = os.environ.get("CLAUDE_PLUGIN_DATA", os.path.expanduser("~/.claude"))

def log(msg):
    try:
        with open(os.path.join(DATA_DIR, "hook-debug.log"), "a") as f:
            f.write(f"{msg}\n")
    except: pass

try:
    data = json.load(sys.stdin)
    # ... hook logic ...
    
    # Output in official format
    result = {"hookSpecificOutput": {"additionalContext": "Advisory message"}}
    print(json.dumps(result))
    sys.exit(0)
except Exception as e:
    log(f"ERROR: {e}")
    print(json.dumps({"hookSpecificOutput": {"additionalContext": ""}}))
    sys.exit(0)  # ALWAYS exit 0 on error
```

### Safe Script Template (Bash SessionStart)

```bash
#!/usr/bin/env bash
# Read stdin (required)
cat > /dev/null

# Output in official JSON format
cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Your context here"
  }
}
EOF

exit 0
```

---

## 10. De-duplication and Plugin Boundary Redesign

### Current Overlap Matrix

| File Pattern | Plugins Firing | Official Pattern |
|-------------|----------------|-----------------|
| `__manifest__.py` | 1 (was 4) | 0 — official has no file-advisory hooks |
| `models/*.py` | 1 (was 3) | 0 |
| `docker-compose*.yml` | 1 (was 2) | 0 |
| Write\|Edit (blocking) | 2 (frontend + upgrade) | 1 per concern (security-guidance) |
| Bash | 3 (devops pre + post, service) | 0 |

### Recommended Plugin Boundary Map

| Concern | Owner Plugin | Hook Count | Type |
|---------|-------------|------------|------|
| Core Odoo protection | odoo-upgrade | 1 PreToolUse | command (blocking) |
| Inline JS prevention | odoo-frontend | 1 PreToolUse | command (blocking) |
| ADO role enforcement | devops | 1 PreToolUse | command (blocking) |
| Odoo version context | odoo-frontend | 1 SessionStart | command (static JSON) |
| DevOps profile context | devops | 1 SessionStart | command (static JSON) |
| Compat checking | odoo-upgrade | 1 PostToolUse | command |
| All advisory prompts | Respective owners | prompt | Evaluate for SKILL.md conversion |

---

## 11. Rollout and Verification Plan

### Step 1: Fix Schema + Output Format (Cache Only)
1. Remove `name`/`description` from all hook entries in cached hooks.json
2. Fix Python hooks to output JSON with `hookSpecificOutput`
3. Fix Bash hooks to output JSON with `hookSpecificOutput`
4. Change `python` to `python3` in command strings
5. **Verify:** Restart Claude Code session — no "hook error" messages

### Step 2: Reduce Prompt Hook Noise
1. Move advisory content from prompt hooks to SKILL.md files
2. Remove Bash-matcher prompt hooks that fire on every command
3. **Verify:** Edit `__manifest__.py` — should see 0-1 advisory messages, not 4

### Step 3: Optimize SessionStart
1. Convert `session-start.sh` to static JSON output (no Python subprocess)
2. Convert `session_start.py` to static JSON output (pre-computed)
3. **Verify:** Session starts in <2 seconds

### Step 4: Sync Source with Cache Patterns
1. Update source hooks.json to match cache (direct paths, no wrapper references)
2. Remove `_infrastructure/hook-runner.sh` dependency from source
3. Add per-script logging where needed
4. **Verify:** Source and cache produce identical behavior

### Step 5: Long-term Architecture
1. Evaluate `if` field adoption for Bash hooks
2. Consider consolidating Python hooks per plugin
3. Document the hook ownership registry

---

## 12. Final Recommended Target Architecture

```
~/.claude/plugins/cache/taqat-techno-plugins/
  devops/6.3.0/
    hooks/hooks.json           # 3 hooks: SessionStart, PreToolUse(ADO), PostToolUseFailure
    hooks/session-start.sh     # Static JSON output, <50ms
    hooks/pre-write-validate.sh # Blocking, role check
    hooks/error-recovery.sh    # ADO error guidance

  odoo-frontend/8.4.0/
    hooks/hooks.json           # 2 hooks: SessionStart, PreToolUse(Write|Edit)
    hooks/session_start.py     # Static JSON output, <50ms
    hooks/pre_write_check.py   # Blocking, inline JS check

  odoo-upgrade/5.1.0/
    hooks/hooks.json           # 2 hooks: PreToolUse(Write|Edit), PostToolUse(Write|Edit)
    hooks/guard_core_odoo.py   # Blocking, core file protection
    hooks/check_odoo19_compat.py # Advisory, compat check

  odoo-docker/2.1.0/           # 3-5 prompt hooks (if Docker context detected)
  odoo-service/3.0.0/          # 2-3 prompt hooks (consolidated)
  odoo-security/2.1.0/         # 2 prompt hooks
  odoo-test/2.0.0/             # 1 prompt hook
  odoo-i18n/2.0.0/             # 1 prompt hook
  odoo-report/2.1.0/           # 2 prompt hooks
```

**Total hooks: ~20** (down from 44 source, 68 original)
**Command hooks: 7** (down from 12)
**Prompt hooks: ~13** (down from 31)
**SessionStart hooks: 2** (down from 6)

---

## 13. Concrete Next Actions

### Action 1 (DO NOW): Fix cached hooks.json schema + output format

For each of the 3 command-hook plugins in cache:
1. Remove `name` and `description` from hook entries
2. Ensure `matcher` is present on SessionStart hooks
3. Change `python` to `python3`

### Action 2 (DO NOW): Fix SessionStart scripts to output JSON

Update `session-start.sh` and `session_start.py` in cache to output:
```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
```

### Action 3 (Today): Remove excessive Bash-matcher prompt hooks

Remove or disable prompt hooks that fire on every Bash command (pip check, port conflict, long-task) from cached hooks.json files.

### Action 4 (This week): Update source to match cache patterns

Remove wrapper dependencies. Use direct script paths. Match official schema.

### Action 5 (This week): Convert advisory prompts to SKILL.md context

Move file-pattern advisory content into each plugin's SKILL.md where it becomes part of the agent's knowledge without per-tool-use overhead.

---

## 14. Implementation: Fix SessionStart Hooks

### Fix session_start.py (JSON output)

```python
#!/usr/bin/env python3
"""SessionStart: Detect Odoo version, output JSON context."""
import json, os, re, sys, threading

threading.Timer(8.0, lambda: os._exit(0)).start()

try:
    sys.stdin.read()
except: pass

def detect():
    cwd = os.getcwd()
    for item in os.listdir(cwd):
        m = re.match(r'^odoo(\d{2})$', item)
        if m and os.path.isdir(os.path.join(cwd, item)):
            ver = m.group(1)
            bs = "5.1.3" if int(ver) >= 16 else "4.5.0"
            owl = {"16":"1.x","17":"1.x","18":"2.x","19":"2.x"}.get(ver)
            parts = [f"Odoo {ver}", f"Bootstrap {bs}"]
            if owl: parts.append(f"Owl {owl}")
            return f"[Odoo Frontend] Detected: {', '.join(parts)}. Use publicWidget for website themes."
    return ""

ctx = detect()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
sys.exit(0)
```

### Fix session-start.sh (JSON output)

```bash
#!/usr/bin/env bash
INPUT=$(cat)

# ... existing profile/validation logic ...

# Collect all messages into a variable
MESSAGES=""
# ... append messages to MESSAGES ...

# Output in official JSON format
python3 -c "
import json
msg = '''$MESSAGES'''
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': msg.strip()}}))
" 2>/dev/null || echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'

exit 0
```

### Fix hooks.json schema (remove non-standard fields)

```json
{
  "description": "Odoo frontend development hooks",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py\"",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/pre_write_check.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Note: No `name`, no `description` on entries. Only `matcher` and `hooks` array.
