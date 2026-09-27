# agent-safety-guards - decisions

Append-only log of binding decisions (house rule HR-4). Never rewrite an entry;
supersede it with a new dated entry that references the old one.

## D-001 - The test-scope guard denies whole-suite runs, with an in-command override

Date: 2026-09-27
Phase: Post-0.2
Status: binding
Ships in: v0.3.0

Decision:

1. `hooks/test_scope_guard.py check` runs on PreToolUse for `Bash|PowerShell`. When the
   command runs a WHOLE test suite, it returns `permissionDecision: "deny"` with a reason
   that lists the files edited this session and a scoped command.
2. A command containing `FULL_SUITE=1` always passes. The skill restricts its use to an
   explicit user request, or a full-suite gate defined by a workflow the user invoked.
3. `TEST_SCOPE_GUARD=off` (also `0`, `false`, `disabled`) disables the hook entirely.
4. Detection is best-effort and errs toward allowing. An unrecognised runner, a
   selector the classifier cannot parse, or any error means the call passes. The hook
   never rewrites a command (`updatedInput` is not used).
5. `track` runs on PostToolUse for `Write|Edit|MultiEdit|NotebookEdit` with
   `async: true`, and stores edited paths per session under
   `${CLAUDE_PLUGIN_DATA}/test-scope/`. The fallback location is
   `~/.claude/agent-safety-guards/test-scope/`, never the plugin root (HR-17). Session
   files older than 7 days are pruned.
6. The decision log (`decisions.jsonl`) records timestamp, runner and decision only.
   It never records command text, because commands can carry secrets.
7. The policy itself (tiers, triggers, hygiene) lives in `skills/test-scope/SKILL.md`.
   The hook classifies and reports; it does not decide what the right tests are
   (HR-3).

Rationale:

During development, whole-suite runs after small changes cost minutes per edit and
add no accuracy beyond a targeted run plus the affected modules. The user decided
(2026-09-27) that the full suite runs only on request or in CI, and chose enforcement
by deny-with-override over guidance alone.

A deny is used because it is the only PreToolUse output that is guaranteed to reach the
model. Plain stdout or stderr with exit 0, which the plugin's credential advisory and
several sibling plugins use, is shown in the transcript but not fed to Claude. A deny
reason is also honoured in every permission mode, including bypass. The override keeps
the deny a speed bump rather than a wall: a legitimate full run costs one re-issue.

Non-violation of prior decisions:

- The plugin previously stated that its hooks never block or deny. That statement
  described the credential advisory, which is unchanged: it still never blocks. The
  README and the `hooks.json` description now say that the test-scope guard denies.
- HR-6 (never block) governs UserPromptSubmit hooks. This hook is PreToolUse, and it
  keeps HR-6's other properties: silent pass on errors, exit 0, no MCP calls, a
  decision log with no content.

Reverse-only criteria:

Reverse, by superseding this entry, only if one of these holds:
- a measured week of the decision log shows most denials were followed by the same
  command re-issued with `FULL_SUITE=1`, meaning the policy is being bypassed rather than
  followed;
- Claude Code gains a reliable PreToolUse advisory channel that reaches the model
  without blocking, and that channel changes behaviour as well as the deny does.

Evals:

`evals/fires-on-full-suite-after-small-fix` (must-fire) and
`evals/ignores-junit-report-config` (must-not-fire) cover the skill. The hook is
covered by `tests/test_test_scope_guard.py` and `test_scope_guard.py --self-test`.
