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

## D-003 - advise becomes the default mode

Date: 2026-10-19 · Status: accepted · Amends: D-001 (default only), D-002 (default only)

Context:

The 2026-10-19 public-readiness audit (ASG-P1-03) found that shipping `enforce` as the
default imposes one author's test policy on every project that installs the plugin: a stranger
running `pytest` in an unrelated repository is denied with no prior configuration. D-002's
reverse-only criterion was "make `advise` the default only if the user asks". The user approved
that change as part of the audit's Wave 2.

Decision:

1. With `TEST_SCOPE_GUARD` unset, the guard runs in `advise` mode: the whole-suite run happens
   and the guidance arrives with its result.
2. `enforce` is opt-in. Set `TEST_SCOPE_GUARD=enforce` to restore the D-001 behaviour.
3. A value that is set but not recognised still means `enforce`. Someone tried to change the
   default, so the stricter reading is the safe one.
4. Everything else in D-001 and D-002 is unchanged: `FULL_SUITE=1`, fail open, a content-free
   decision log.

Consequence for existing installs:

Anyone who relied on the old default (including the author) gets advise behaviour after
updating until they set `TEST_SCOPE_GUARD=enforce`.


## D-004 - the classifier ignores info commands; the override must be an env prefix

Date: 2026-10-19 · Status: accepted · Amends: D-001 (override parsing, classification only)

Context:

The 2026-10-19 audit (ASG-P1-02, F-ASG-02, F-ASG-05) found two defects. Commands that run no
tests (`pytest --help`, `pytest --collect-only`, `jest --version`, `playwright test --list`)
and scripts that are not the whole suite (`npm run test:unit`, `npm run testing-docs`) were
classified as whole-suite runs. And any `FULL_SUITE=1` substring passed the guard, including
one inside a shell comment or an `echo`.

Decision:

1. Info-only invocations (`--help`, `-h`, `--version`, `-V`, `--co`, `--collect-only`, `--list`,
   `--listTests`, `--showConfig`, `--fixtures`, `--markers`) are never classified.
2. `npm|pnpm|yarn|bun run <script>` counts as a whole-suite run only for the script names
   `test`, `test:run`, `test:all`, `test:ci`, plus names listed in `TEST_SCOPE_FULL_SCRIPTS`
   or the `full_suite_scripts` plugin option.
3. `FULL_SUITE=1` is honoured only as an environment assignment in front of the test command
   (`FULL_SUITE=1 pytest`, `env FULL_SUITE=1 ...`), or as a preceding `export FULL_SUITE=1` /
   PowerShell `$env:FULL_SUITE=1` statement in the same command line.
4. The tokenizer keeps backslashes, so `C:\venv\Scripts\python.exe -m pytest` is classified,
   and `npx -y`, `npm --prefix/-w`, `pnpm --filter`, `yarn workspace` are recognised.
5. The mode can also come from the `test_scope_guard` plugin option; `TEST_SCOPE_GUARD` wins.

The guard stays a productivity speed bump, not a security control: the deny reason still
names the override, because the model is expected to use it when the user asked for a full run.


## D-005 - `ask` is a mode of its own

Date: 2026-10-19 · Status: accepted · Amends: D-003 (point 3, for the value `ask` only)

Context:

The 2026-10-19 re-audit (RA-ASG-01) found that the sibling guards in git-safety and
release-safety use `advise|ask|off`, where `ask` returns `permissionDecision: "ask"`. Here,
`TEST_SCOPE_GUARD=ask` fell under D-003 point 3 (an unrecognised value means `enforce`) and
silently denied. A user configuring all three plugins the same way got a deny where they
expected a question. PLUGIN_STANDARDS 1.6 prefers ask over deny.

Decision:

1. `ask` (alias `confirm`) is recognised. For a whole-suite run the hook returns
   `permissionDecision: "ask"` with the changed files and a scoped command, so the user
   approves or declines before the run starts.
2. Scoped runs, info commands and the `FULL_SUITE=1` prefix pass untouched, as in every mode.
3. The decision log records `ask`, still without command text.
4. Every other unrecognised value still means `enforce` (D-003 point 3 is otherwise unchanged).
   The default stays `advise`.
