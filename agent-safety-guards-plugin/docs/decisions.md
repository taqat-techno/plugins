# agent-safety-guards - decisions

Append-only log of binding decisions (house rule HR-4). Never rewrite an entry;
supersede it with a new dated entry that references the old one.

## D-001 - The test-scope guard denies whole-suite runs, with an in-command override

> Rationale corrected and extended by **D-002** (2026-09-27). The decision itself (deny by
> default, `FULL_SUITE=1` override) stands.

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

## D-002 - Correction to D-001's rationale; add an advise mode

Date: 2026-09-27
Phase: Post-0.3
Status: binding
Ships in: v0.4.0
Supersedes: the rationale paragraph of D-001 (not its decision)

Decision:

1. **Correction.** D-001 said a deny reason is "the only PreToolUse output that is
   guaranteed to reach the model". That is false.
   `hookSpecificOutput.additionalContext` with `hookEventName: "PreToolUse"` also reaches
   Claude. This was verified on Claude Code 2.1.282 by the hook-advisory fix shipped the
   same day (odoo-plugin 2.11.0, and siblings). What does NOT reach the model is plain
   stdout or stderr from a PreToolUse hook that exits 0. D-001's statement about those
   stands.
2. **`TEST_SCOPE_GUARD` gains a third value.** `enforce` (the default) keeps D-001: deny.
   `advise` lets the run happen and attaches the same guidance (changed files, scoped
   command, T2 reminder) as `additionalContext`. `off` disables the hook. Unknown values
   mean `enforce`, so the hook fails safe, toward the user's chosen policy.
3. **The difference between the modes is stated wherever advise is offered.**
   `additionalContext` arrives alongside the tool result, so advise mode cannot save the run
   it reacts to. It only steers the next run. Enforce saves the current run.
4. `FULL_SUITE=1` passes untouched in every mode. The decision log records
   `deny` / `advise` / `override` and still never stores command text.

Rationale:

The default stays `enforce` because that is what the user chose on 2026-09-27. Advise mode
is for developers who want the guidance without the speed bump: pairing, a
full-suite-heavy phase, or a week of measuring through the decision log before enforcing.
D-001's reverse-only criteria named "a reliable PreToolUse advisory channel" as the
condition for revisiting. That condition is met. The right response is to offer the channel
as an option, not to silently change the policy the user picked.

Non-violation of prior decisions:

- D-001 decisions 1 to 7 are unchanged under the default mode.
- HR-6 properties are kept in both modes: fail open, exit 0, no MCP calls, content-free log.

Reverse-only criteria:

Make `advise` the default only if the user asks, or if a measured period of the decision
log shows advise-mode sessions rarely repeat a whole-suite run after the first advisory.

