# Changelog

All notable changes to the `agent-safety-guards` plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-09-27

Test the change, not the system. Adds a test-scope policy and a hook that enforces it.

### Added
- **`skills/test-scope`** - a four-tier ladder:
  - T0: static checks on the touched files, per edit.
  - T1: the tests for the changed units plus new tests, once per coherent change.
  - T2: each touched module's suite, before calling a task done.
  - T3: the full suite, **only when the user asks, or in CI**.

  Also covers escalation triggers that widen T2 without jumping to T3, batching, the
  `FULL_SUITE=1` override semantics, test-file hygiene (extend before creating, scratch
  probes outside the repo, every new test must bite and be collected), and a report block
  that says what was not run. `references/runner-recipes.md` adds change-scoped selection
  for pytest, vitest (`related`, `--changed`), jest (`--findRelatedTests`, `-o`),
  playwright (`--only-changed`, `--last-failed`) and npm scripts, including the vitest
  watch-mode trap.
- **`hooks/test_scope_guard.py`**:
  - `track` (PostToolUse `Write|Edit`, async) records the files edited per session under
    `${CLAUDE_PLUGIN_DATA}`.
  - `check` (PreToolUse `Bash|PowerShell`) **denies** a whole-suite run. It recognises
    Django `manage.py test` without labels, bare `pytest`, `odoo-bin --test-enable` without
    module tags or with `-u all`, `npm test`, `vitest run`, `jest` and `playwright test`.
    The deny reason lists the changed files and a scoped command.
  - `FULL_SUITE=1` in the command passes it. `TEST_SCOPE_GUARD=off` disables it.
  - It fails open, and its decision log never stores command text.
  - Covered by `--self-test` (46 classification cases) and `tests/test_test_scope_guard.py`
    (10 end-to-end cases).
- `docs/decisions.md` D-001 records why a deny is used: it is the only PreToolUse output
  guaranteed to reach the model.
- Evals: `fires-on-full-suite-after-small-fix`, `ignores-junit-report-config`.

### Changed
- `test-double-seams`: the checklist item "the full suite was run after the change" now
  reads "the consumers' tests ran". A seam change widens T2 to every module injecting the
  collaborator, and recommends the full suite when that set is unknown.
- `workflow-reliability`: verifying an agent's claim now runs the new tests plus the
  affected modules' suites (T2), not "the regression suite". Re-runs after a failure report
  start from the reported failures.
- README and the `hooks.json` description now say that the plugin has one denying hook.

## [0.2.3] - 2026-09-27

### `defensive-failure-design` - rule 7

- **An idempotent skip must not skip a side effect later steps depend on.** A re-runnable loader that skipped an "already exists" phase also skipped the lookup map built inside it, and the next phase silently defaulted almost every row. Lookup maps belong in an always-run step reading live state; a missing lookup is a hard error, not a default; reconcile per group, not only on totals. No `description` change.

## [0.2.2] - 2026-09-12

Absorbs five recorded lessons into the two skills that already own their mechanisms. No new skill, no `description` change, no behaviour removed.

### `test-result-evidence` - three new evidence rules

- **Rule 8 - prove the instrument FIRED, not just that it ran on the right artifact.** Rule 2 asks *which* artifact a control touched; rule 8 asks whether the command ran at all. A before/after comparison of two no-ops always reports "identical" - observed when a seeding command was launched from the wrong working directory, so both sides were the untouched baseline. Any identical / unchanged / no-op claim now requires the exit path, the cwd printed by the command itself, and one observable side effect. The producer side of this stays with `workflow-reliability`; `defers_to` now names that boundary explicitly.
- **Rule 9 - a mass failure is evidence about the instrument.** A fresh checker firing on most of a mature corpus is far likelier wrong than the corpus. Two shapes: uniform failure across every check (something upstream is broken), and mass failure with plausible findings (a validator reported 13 FAIL + 4 WARN, all false positives - a "don't name the plugin" rule fired because for framework plugins the plugin name *is* the technology a user must say, and `\w+\.(js|md)` matched `Next.js`). Read the flagged artifacts before changing either side; narrow the rule to the hazard rather than loosening it.
- **Rule 10 - when a narrow green and a wide red disagree, the wide one wins.** The failure lives outside the narrow test's reach. Instrument the boundaries *between* pipeline stages - observed where a data loss happened during the data-file load, in the gap between `pre` and `post`, not inside either. Then move the assertion onto the real mechanism.

Each rule also gains its row in every surface the skill uses to represent a rule: `owns:`, the decision framework, the control-run ladder (new step 0 - firing precedes identity), the validation checklist, and the anti-pattern table.

### `defensive-failure-design` - rule 6, the fail-closed counterpart to rule 2

A **restriction** resolver must fail CLOSED, which is the opposite of what rule 2 requires of a **narrowing hint**. The two look identical in code - a lookup that may not resolve - and differ only in what absence means: a missing hint costs precision, a missing restriction costs the restriction. Observed where a tool-profile resolver returned `undefined` for an unrecognised profile name and an undefined policy meant *no restriction applied*, so a typo silently granted the full tool surface. Assert the **resolved object**, not the presence of the config key; treat any nullable policy resolver as fail-open until proven otherwise, and grep the call sites rather than the definition.

## [0.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (2 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-old-tag-control-run-all-green` targets `test-result-evidence`
- `fires-on-structured-output-retry-loop` targets `agent-safety`
- `ignores-pytest-naming-convention` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 6 skills. The underscore form is not in Claude Code's skill frontmatter allowlist, so every one of those declarations was silently inert and the skills stayed user-invocable against their authored intent. Values preserved exactly.

## [Unreleased]

### Added

- `skills/structural-assertions` (+ `references/ast-probes.md`) — claims about the SHAPE of
  source go through the language's parser, never string containment; the `ast.walk`
  breadth-first ordering trap; the side-by-side old-file/new-file wiring probe; the negative
  universal over multi-exit functions; sweep-the-class; and reading a red pre-existing
  structural test as evidence about the design.
- `skills/test-result-evidence` — the epistemics of a test RESULT: the named discriminator,
  proving which artifact a control run imported (editable-install `sys.path` pinning), reading
  a collection-time `ImportError` as zero-tests-ran, comparing collected counts across
  versions, cleanup assertions on a closed resource rather than a deletable path, and the
  one-OS-flake reading.
- `skills/test-double-seams` — the two-sided contract at a test-double seam: the per-branch
  ledger enumerated from the production entry point, the "which side of this seam did the test
  call?" question, the seam-shape catalog, and the production-side rules (`getattr` for
  optional reads, no diagnostic with veto power over a startup path, no feature that requires
  existing doubles to grow methods).

### Changed

- `skills/agent-safety` (0.2.0) — added the consume side of the structured-output contract,
  the don't-route-around-a-permission-denial rule, refute-a-green-verdict-before-it-mutates,
  the production-data hard stops, and the reversibility test for autonomous shipping.
- `skills/workflow-reliability` (0.2.0) — added completion-gated aggregation (a crashed
  producer's zero is unverified, not clean), stale per-run artifact discard, the
  killed-subagent unknown-state rule, shared-runtime/concurrent-session standdown, and the
  recon-subagent prompt contract.

## [0.1.0] - 2026-06-13

### Added

- Initial release.
- `skills/agent-safety` — advisory single-session safety primitives: pasted-credential
  compromise response (revoke + reissue least-scope, never reuse), read-only /
  investigation immutability (no mutation during a survey, even to fix access),
  authorization verification (a cited override must exist in the conversation),
  no-fabrication discipline (never invent a permission, override, or tool/MCP
  availability), report-don't-silently-patch for incidental security findings, and the
  structured-output contract (required tool called exactly once, all fields mapped).
- `skills/workflow-reliability` — multi-agent fan-out reliability patterns: small
  sequential waves, null-safe reduce, journaled + idempotent long runs, disjoint file
  ownership with one canonical vocabulary, verify-the-claim main-thread scans, one
  subagent per long-form item, and the investigation-first audit shape.
- `hooks/credential_paste_advisory.py` — optional non-fatal UserPromptSubmit hook that
  prints a single reminder when the prompt contains a token-shaped string (common key
  prefixes, a `Bearer` marker, a long base64 run, or a PEM header). Never blocks, never
  echoes the matched value, exits 0 always. Stdlib only.
