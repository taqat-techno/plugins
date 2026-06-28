# Rule: advisory hooks are fail-open by construction

**Contract owner:** `hooks/hooks.json` + `hooks/hook_launcher.py`. Decision: D-031.
Detector: `scripts/rag_report.py` finding `P-013`.

## The rule

1. **Advisory / injection / reminder hooks MUST be fail-open.** Any failure to
   resolve, load, or run them must yield exit `0` — never the blocking exit `2`
   (and preferably never any non-zero). An advisory hook must never be *able* to
   cancel a user prompt.
2. **A script's own `sys.exit(0)` is necessary but NOT sufficient.** It cannot
   run if the script file never loads (unresolved `${CLAUDE_PLUGIN_ROOT}`, unset
   var, missing file → Python exits `2`, a *blocking* error on
   `UserPromptSubmit`). The fail-open guarantee must live **above** the script,
   in the command-invocation layer.
3. **Any hook that can block a user prompt must be *intentionally* blocking and
   documented as such.** Never make an intentionally-blocking hook fail-open.

## How advisory hooks are wired (the safe pattern)

Every `hooks.json` `command` runs an inline `-c` bootstrap, NOT a
`python ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` script path:

- `python3 -c "<bootstrap>"` takes **no script-file argument**, so the
  "can't open file → exit 2" branch is structurally impossible.
- Each command chains interpreters: `python3 -c … || python -c … || py -3 -c …`,
  so the hook still runs where `python3` is not the name. Safe by spec — the only
  blocking code is `2`, so a missing interpreter (127) or a stray parse error is
  non-blocking; and the bootstrap exits 0 on every fail-open path, so the chain
  only advances when an interpreter is truly absent.
- The bootstrap resolves the plugin root from the `CLAUDE_PLUGIN_ROOT` runtime
  env var (host-expanded `${CLAUDE_PLUGIN_ROOT}` path as a fallback) and runs
  `hooks/hook_launcher.py` only if it exists; otherwise it exits 0.
- `hook_launcher.py` finds the real target beside its own `__file__` and runs it
  via `runpy` (stdin/stdout pass through, so `additionalContext` /
  `permissionDecision` injection still works).

## Two launcher modes

`hook_launcher.py` maps each target name to `(filename, mode)`:

- **advisory** (`retrieval-reminder`, `project-focus`) — normalizes **every**
  exit to `0`, even a target `sys.exit(2)`. These injectors can never block.
- **guarded** (`lock-conflict`) — **passes the target's own exit code through**
  so a deliberate decision (e.g. an `ask`, or a future exit-2 block) survives,
  but a *path-resolution failure* or an *unexpected exception* still fails open
  to `0`. This is for hooks that may legitimately influence their tool call.

To add a new hook: add a `name → (filename, mode)` entry to `_TARGETS` in
`hook_launcher.py`, and a `hooks.json` command that runs the bootstrap with the
new name. Do not invoke the script file directly.

## The lock-conflict hook (guarded)

The **PreToolUse lock-conflict hook** (`lock_conflict_check.py`) is routed through
the launcher in **guarded** mode. Its `ask` (D-007) and exit code pass through
unchanged, so its intended behavior is fully preserved — but an unresolved
`${CLAUDE_PLUGIN_ROOT}` (or a missing script) can no longer make it exit 2 and
falsely block **every Bash tool call**. Guarded mode = "fail open on
infrastructure failure, pass the decision through."

## Enforcement

`scripts/rag_report.py::analyze_advisory_hook_safety` reads `hooks.json` and emits
`P-013` for any advisory command that is not fail-open. `/report` surfaces it
(High; Critical with runtime evidence). `hooks/test_hook_launcher.py` asserts the
launcher returns `0` (never `2`) under every failure mode and that `hooks.json`
stays on the inline-bootstrap form.
