<!-- Curated GitHub issue draft. Supersedes the auto-generated P-012 ("MCP error
phrases") as the canonical rag-plugin hook issue. File to: taqat-techno/plugins.
A companion host-side report (the ${CLAUDE_PLUGIN_ROOT} non-expansion itself)
belongs with the Claude Code / Cowork product team — the plugin uses the
documented variable correctly. -->

# [rag-plugin] advisory UserPromptSubmit hooks can block prompts when hook script path resolution fails

**Target repo:** `taqat-techno/plugins`
**Severity:** High (Critical if runtime logs confirm the trigger fired)
**Affected versions:** all with the UserPromptSubmit hooks — **≥ v0.3.0, including v0.15.0**. Fixed in **v0.15.1**.
**Labels:** `bug`, `hooks`, `severity:high`, `source:rag-plugin`

## Summary

The two advisory `UserPromptSubmit` hooks were invoked as the raw
`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py`. If the host does not expand
`${CLAUDE_PLUGIN_ROOT}` (reported on **Cowork / headless Windows**), the variable
is unset, or the script is missing, **Python cannot open the file and exits 2**.
Per the Claude Code hook spec, **exit `2` on `UserPromptSubmit` is a *blocking*
error**, so the prompt is **cancelled before the model request** — the user sees
a spinner / no response / no model call. The scripts' own `sys.exit(0)`
fail-safe **cannot run because the file never loads**; the failure is one layer
above the script, at the command-invocation layer, which was unguarded.

## Why v0.15.0 was still affected (NOT a stale, v0.13.2-only issue)

`git log -p -- rag-plugin/hooks/hooks.json` shows the `command` strings were
**only ever** the `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` form,
introduced in `e87b4d0` (v0.3.0) and **byte-identical through v0.15.0**. The
v0.13.2 report described the same pattern that current code still shipped — it
was a live vulnerability, not a fixed one.

## Proven mechanism (repo code + official spec + empirical tests)

1. Python's exit code for "can't open the script file" is **2** — reproduced for
   unset var, literal `${CLAUDE_PLUGIN_ROOT}`, and missing paths.
2. Claude Code hook spec: **exit `2` = "Blocking error"**, including
   `UserPromptSubmit` (`plugin-dev/hook-development` SKILL.md:294–298).
3. `hooks.json` registered **two** `UserPromptSubmit` hooks in the raw form
   (`hooks.json:21,30`).
4. Script-level `sys.exit(0)` fail-safes run **only once the script loads** — the
   failure happens before any script code executes.
5. On real Windows, `python3` resolves (`…\WindowsApps\python3`), so the
   dangerous exit-2 branch is reachable (a missing `python3` would be exit 127 —
   non-blocking).

The symptom fingerprint ("spinner / no response / no model call") matches the
*blocking* (exit 2) branch, not the non-blocking missing-interpreter branch.

## What still needs Cowork runtime logs (the one unproven link)

Whether **Cowork specifically** is the host that fails to expand
`${CLAUDE_PLUGIN_ROOT}` is a host behavior that cannot be proven from the plugin
repo. To confirm Cowork-specifically, capture (privacy-safe): the hook **stderr**
showing literal `${CLAUDE_PLUGIN_ROOT}` + `[Errno 2]`, the recorded **exit code
2**, and evidence the **prompt was cancelled before the model request**. The fix
below is applied regardless — an advisory hook must never be *able* to block.

## Fix (shipped in v0.15.1, D-031)

- `hooks.json` advisory commands now run an inline `python3 -c` bootstrap.
  Because `-c` takes **no script-file argument**, the "can't open file → exit 2"
  branch is structurally impossible. The bootstrap resolves the plugin root from
  the `CLAUDE_PLUGIN_ROOT` **runtime env var** (host-expanded path as a fallback)
  and runs `hooks/hook_launcher.py` only if it exists; otherwise it exits 0.
- `hooks/hook_launcher.py` runs the real target beside its own `__file__` via
  `runpy` (stdin/stdout pass through — `additionalContext` injection preserved)
  and returns exit `0` in every failure case, normalizing even a target
  `sys.exit(2)` to `0`.
- The intentionally-blocking PreToolUse lock-conflict hook is **deliberately not**
  routed through the launcher.
- Report-engine detector **`P-013`** flags any advisory `hooks.json` command that
  is not fail-open (High; Critical with runtime evidence). It **supersedes the
  generic `P-012`**, which (being an "MCP error phrases" session-text signal)
  could never have detected this hook-fatal failure.

## Tests added

- `hooks/test_hook_launcher.py` — 16 tests: the real bootstrap returns exit `0`
  (never `2`) under unresolved literal `${CLAUDE_PLUGIN_ROOT}`, unset/nonexistent
  root, missing target, target raising, target `sys.exit(2)`, malformed/empty
  payload, service-down, Windows-style paths, project-focus target, fallback
  recovery; plus stdout pass-through, wiring guards, and a `shell=True` full
  command-string parse smoke test.
- `scripts/test_rag_report.py` — 14 tests for the analyzer + P-013 (High /
  Critical / absent / outranks-P-012) + `hook-path-fatal` signal precision +
  a regression guard that this plugin's own hooks stay fail-open.

## Privacy-safe reproduction (without Cowork)

Reproduce the *blocking mechanism* on any machine where `python3` resolves:

```
# unset var (POSIX) — bad path -> exit 2
env -u CLAUDE_PLUGIN_ROOT python3 "${CLAUDE_PLUGIN_ROOT}/hooks/prompt_retrieval_reminder.py" </dev/null; echo $?
# literal var (cmd.exe style) — bad path -> exit 2
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/prompt_retrieval_reminder.py" </dev/null; echo $?
```

Both print `2` (blocking). After the fix, the v0.15.1 bootstrap prints `0`
(fail-open) under the same conditions — see `hooks/test_hook_launcher.py`.

Do **not** attach raw session content; the stderr line + exit code + the
prompt-cancellation event are sufficient and contain no prompt text.
