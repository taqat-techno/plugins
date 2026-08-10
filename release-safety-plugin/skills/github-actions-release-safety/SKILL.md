---
name: github-actions-release-safety
description: >-
  Owns the AUTHORING-side safety of CI workflows and tag-driven releases -- everything that decides
  whether a green check or a published tag means anything. Covers the report-only gate (a step
  carrying `|| true`, `continue-on-error: true`, or a soft-fail flag swallows its non-zero exit, so
  the UI is green whether the check passed or found problems and was told to pass anyway -- audit
  every gate for a swallowed exit code before trusting a green PR, and prove a gate blocks by
  feeding it input that must exit non-zero); the `workflow_dispatch` default-branch rule (dispatchable
  workflows are read from the DEFAULT branch, so a release workflow added on a feature branch runs on
  push/PR but has no Run button and rejects `gh workflow run` -- it reads as a broken button); the
  `timeout-minutes` scope trap (it bounds EXECUTION and starts when the job starts, so a job queued
  on a retired or nonexistent runner label is never bounded and sits to the 24-hour ceiling while
  withholding the whole run's downloadable logs); the push-wait-tag ordering (a tag is a promise the release workflow
  acts on immediately, and in a fan-out release one failing platform yields a PARTIAL release rather
  than none); the secret-presence guard that self-matches (a sibling CI system expands `$(SECRET)`
  inside script bodies, so a literal-macro comparison always reports "set", and an undefined variable
  stays literal so `-z` is equally useless -- map through `env:` and assert on decoded SHAPE, never
  the literal, never printed); and removing the moving-ref / daemon dependency under a gate whose
  verdict matters by running its tool from a pinned standalone binary. Activates on concrete
  artifacts: a CI workflow or pipeline YAML (`.github/workflows/*.yml` or a sibling CI's pipeline
  file) being written, edited, or reviewed; a green check about to be cited as merge evidence; a tag
  or release about to be pushed, or a branch and its tag pushed together; a missing "Run workflow"
  button or a rejected `gh workflow run`; a job that hangs, queues, or reports an empty `runner_name`;
  a runner label or matrix leg being added or changed; a secret-presence guard being written, or one
  reporting an answer the platform's own variable list contradicts. NOT for "is the fix live in the
  environment?" (that is release-verification) and NOT for authoring application tests (that is the
  framework testing skills) -- this skill governs only the workflow file, the gate, and the tag.
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - the AUTHORING-time application of the report-only-gate rule (sweep every workflow file for swallowed exit codes before a green PR is used as evidence) and the prove-it-blocks procedure -- release-verification owns the rule's statement and its deploy-time application
  - the `workflow_dispatch` default-branch rule (a dispatchable workflow must exist on the default branch)
  - the `timeout-minutes` scope rule (bounds execution, not queue time) and the runner-label liveness check
  - the `needs` contamination rule (a job that cannot fail the release must not sit in a gate's `needs`, because `needs` waits on queue time)
  - the push -> wait for CI -> tag ordering, and the partial-release mechanism in a fan-out release
  - the tag-withdrawal procedure (cancel, confirm nothing published, delete local + remote, re-tag)
  - the secret-presence guard contract (map via `env:`, assert on decoded SHAPE, never on the literal macro, never print)
  - removing the moving-ref / daemon dependency under a load-bearing gate by running its tool from a pinned standalone binary (SHA-pinning an unavoidable action reference is the devops plugin's, not this skill's)
defers_to:
  - release-verification skill for the deploy-side question ("is the fix actually live in the target environment?"), the deployed-SHA reconciliation, and report-only-gate detection AT DEPLOY TIME -- this skill catches the swallowed exit code while the workflow is being written or reviewed; that one catches it while verifying a release
  - agent-safety skill for the credential-compromise response when a secret value actually appears in the session
  - the devops plugin's CI_HARDENING checklist for SHA-pinning third-party actions, for "an approval-looking YAML block is not the gate" (enforcement lives in branch/environment protection settings, not in the file), and for the renamed-required-check trap
  - references/gate-audit.md for the per-CI soft-fail token catalog and sweep command, the prove-it-blocks recipe, the shape-assertion patterns, the tag-withdrawal command sequence, and the queue-vs-execution triage table
  - the user for every tag push, release publish, and default-branch change
user_invocable: false
---

# github-actions-release-safety

## Purpose

A green check and a published tag are the two signals a team actually trusts, and both are cheap to
fake by accident. A gate that swallows its exit code looks identical to one that passed. A tag pushed
alongside its branch starts the release before the tests that would have stopped it. This skill holds
the authoring-side reflexes that keep those two signals honest — written at the moment the workflow
file or the tag command is being composed, not after a bad release has to be withdrawn.

## When to use

Activate when any of these appear:

- A workflow file (`.github/workflows/*.yml` or a sibling CI's pipeline YAML) is being written, edited, or reviewed.
- A PR is green and about to be merged, and the green is being used as evidence.
- A release is about to be tagged, or a branch and its tag are about to be pushed together.
- A "Run workflow" button is missing, or `gh workflow run` reports the workflow has no `workflow_dispatch` trigger.
- A job hangs, queues forever, never starts, or shows an empty `runner_name`.
- A runner label, image label, or matrix leg is added or changed.
- A secret-presence / "is this variable set?" guard is being written, or one is reporting an answer that contradicts the platform's variable list.
- A gate is being wired to a third-party action or a container-based tool.

Do NOT use this to answer "is the fix live in the environment?" — that is the **release-verification**
skill. This skill governs the workflow file and the tag; that one governs the deployed artifact.

Do NOT use this to write or shape application tests. The must-fail input in rule 1 is a throwaway
probe of the *gate*, reverted immediately; it is not a test to keep. Test authoring belongs to the
framework testing skills (django-testing, fastapi-testing, and the Odoo test skill).

## The rules

### 1. A gate that swallows its exit code is REPORT-ONLY and cannot block a merge

A CI step is **enforcing only if its non-zero exit can fail the run.** Append `|| true`, set
`continue-on-error: true` on the step or job, or flip the tool's own soft-fail switch, and the
non-zero exit is discarded. The step still runs, still annotates, still writes its findings into the
log — and the run goes green regardless. That is the whole trap: **"the lint/security/test job is
green" then means either "it passed" or "it found problems and was told to pass anyway", and the UI
renders both identically.** (**release-verification** owns this rule's statement and its deploy-time
application. What follows is the authoring-time application only — do not restate the rule there or
this procedure here.)

- **Sweep before trusting.** Run the soft-fail sweep across every workflow / pipeline file and
  classify each hit as *intentional advisory* (fine, but its green is informational) or *accidental
  report-only* (a gate someone believes blocks). The token catalog and the ready-made grep are in
  `references/gate-audit.md` §1, and it reaches past the three obvious flags — a multi-line `run:`
  without `set -e` takes only the LAST command's status as the step's status, and a pipeline without
  `pipefail` takes only the last stage's, so a failing command in the middle is invisible with no
  soft-fail flag written anywhere. Sweep before a green PR is used as evidence, not after.
- **Prove a gate blocks — do not assume it.** Reading the YAML cannot see the two ways a
  syntactically perfect gate passes vacuously: **a selector that collects zero files** (the tool exits
  0 because it ran on nothing, which looks identical to a clean pass) and **a job that is not in the
  required-checks list** (it can go red all it likes without blocking anything, because blocking is
  configured in branch protection, not in the workflow file). One probe run answers both: feed the
  gate input it must reject, and a red run proves the selector collected something, while the PR then
  showing that check as a *required* failure proves membership. Recipe in
  `references/gate-audit.md` §2. **A gate you have never seen fail is an unproven gate.**
- A report-only gate in another job's `needs` still gates *ordering* — it will never gate *merge*,
  because `needs` only decides what starts when, while merge blocking is a branch-protection setting
  the file cannot express. Ordering dependency reads like enforcement in the graph view and is not.

### 2. `workflow_dispatch` is read from the DEFAULT branch

The list of manually dispatchable workflows is built from the **default branch's** copy of the
workflow file. A workflow added on a feature branch is fully live for `push` and `pull_request`
(those events carry the branch's own definition) but **is not dispatchable until the file exists on
the default branch** — no "Run workflow" button in the UI, and `gh workflow run` / the dispatch API
reject it as having no `workflow_dispatch` trigger. This reads as a broken button and sends people
hunting for a permissions or syntax bug that is not there.

- A release workflow that is meant to be triggered by hand must be **merged to the default branch
  before anyone can trigger it by hand.** Plan the merge before planning the release.
- The `inputs:` definition is read from the default branch too, so a feature branch that adds a new
  dispatch input cannot be dispatched *with* that input until it merges.

### 3. `timeout-minutes` bounds EXECUTION, not queue time

The `timeout-minutes` clock **starts when the job starts.** A job that never starts is never bounded.
A job requesting a **retired or nonexistent runner label is not rejected** — it simply queues, up to
the platform's 24-hour ceiling, with `runner_name` empty, while sibling matrix legs on live labels get
allocated in seconds. The wall-clock you budgeted is blown without the timeout ever tripping.

The second-order damage is worse than a wasted runner: the downloadable log archive is only assembled
when the **run** finishes, so while one job sits in the queue `gh run view --log` refuses ("still in
progress") for the entire run — **one unstartable job withholds the CLI-readable diagnosis of a
genuinely failed sibling**, leaving only per-job live scrolling in the UI to debug from.

- **Verify a runner label is still allocated before using it.** Retired image labels (an aging
  `macos-13`-style Intel label whose replacement now carries an `-intel` suffix) do not error — they
  hang. Check the platform's current runner-image list when adding or bumping a label.
- **Never let a job that cannot fail the release sit in a gate's `needs`** — `needs` waits on queue
  time too, so an unstartable dependency stalls the gate indefinitely without ever failing it.
- Set `timeout-minutes` anyway (it bounds a hung *execution*), but do not read it as a wall-clock
  guarantee for the job or the run.

### 4. Push the branch, wait for CI, THEN tag

Pushing a branch and its tag in the same breath starts the test workflow and the release workflow
**simultaneously** — the release is already building while the thing that would have stopped it is
still running. A tag is not a bookmark; it is **a promise the release workflow acts on immediately,
and it is the ref people trust.**

The failure is amplified by the common **fan-out release** shape — one job creates the Release and the
other platform jobs upload their assets to it. **A single failing platform does not stop the release;
it produces a PARTIAL one**, published with only the assets of whichever legs happened to succeed.
Nothing errors loudly; a real, downloadable, incomplete release just exists.

- Push the branch. Let the test workflow **finish green**. Only then tag.
- If a tag must be withdrawn, the ORDER is the rule: **cancel the run first**, then **confirm nothing
  was published**, then delete the tag locally and remotely, then re-tag. Deleting the tag first does
  not stop an in-flight publish — the run already resolved the tag to a commit when it started and no
  longer needs the ref, so it keeps building and can still publish a release for a tag that no longer
  exists. Command sequence in `references/gate-audit.md` §4.
- Tag deletion and release deletion are **user decisions**, because a pushed tag is a public ref:
  consumers, package managers, and mirrors may already have fetched or pinned it, so withdrawing it
  breaks whoever downstream resolved it, and re-tagging the same version leaves two different builds
  sharing one name. Surface the state and the commands; do not withdraw a published ref unasked.

### 5. A secret-presence guard must assert on decoded SHAPE, never on the literal macro

The sibling-CI instance of this class: **Azure Pipelines expands `$(SECRET)` inside script bodies.**
So the natural-looking guard

```
if [ "${MY_SECRET}" = '$(MY_SECRET)' ]; then echo "not set"; fi
```

has **both sides expand to the secret value** — it self-matches, reports "not set" on a correctly
configured pipeline, and turns a healthy build red with a diagnosis that is exactly backwards. The
documented half of the rule (secret variables are not auto-exposed as env vars and must be mapped
explicitly via `env: MY_SECRET: $(MY_SECRET)`) is true, and is what makes the trap plausible.

The other direction closes the escape: when a variable genuinely does **not** exist, the platform
leaves `$(NAME)` as a **literal string** rather than substituting empty — so a bare `[ -z "$VAR" ]`
check also passes, and the real failure surfaces much later as an opaque
`git exit 128 / Invalid username or token`. **Neither the macro comparison nor `-z` is a valid
presence test.**

- **Map the secret through `env:` explicitly**, then assert on **decoded shape** — a length
  threshold, a known prefix, a blob that decodes cleanly, a decoded first line. Shape is the only
  test that survives both failure directions at once, because it is computed *from the value* rather
  than compared against a token whose substitution is exactly the thing in doubt. Concrete assertions
  in `references/gate-audit.md` §3.
- **Never print the value**, not even truncated, and never echo it "just to confirm": CI logs and
  annotations are retained after the run ends, are readable by everyone with repo read access, and
  get copied into artifacts and re-run views — so a one-line debug echo outlives the debugging
  session and converts a guard bug into a mandatory rotation. If a value does reach a log or the
  transcript it is compromised, and the response belongs to the **agent-safety** skill.
- When a pipeline claims a secret is missing, **verify against the platform's variable list / REST
  definition before touching the variable — the guard is the more likely culprit.** Two red builds
  and a wrong diagnosis is the standard cost of skipping that step.
- The same class exists wherever a CI system interpolates into script text (`${{ }}` expressions
  inlined into a `run:` body). Assume interpolation happens before the shell sees the line.

### 6. Run a load-bearing gate's tool from a pinned binary, so nothing can pressure you into softening it

For a gate whose verdict is load-bearing, install the linter/validator as a **real downloaded binary
at a known version** rather than reaching it through a third-party action reference or a `docker run`
invocation. Both indirections attach a dependency the gate itself does not need:

- An action reference resolves through a ref **someone else controls**, so the same workflow file can
  change verdict between runs with no diff in your repo — yesterday's green is not reproducible.
  (When an action reference is unavoidable, SHA-pinning is the mitigation; that rule is owned by the
  devops plugin's `CI_HARDENING.md` — cross-reference it, do not re-derive it here.)
- A container invocation adds a runtime dependency (a working Docker daemon on the runner) that can
  fail for reasons that have nothing to do with the code under test. When it does fail under release
  pressure, the fix people reach for is a soft-fail flag — which silently converts the gate to
  report-only (rule 1). **The binary is preferred not because containers are bad, but because
  removing the flaky dependency removes the incentive that quietly destroys the gate.**

## Decision framework

Trustworthiness ladder for a green run — each rung must hold before the next means anything:

| # | Question | Failing answer means |
|---|---|---|
| 1 | Does the gate's exit code reach the run? | `\|\| true` / `continue-on-error` / soft-fail present -> REPORT-ONLY, green proves nothing |
| 2 | Has that gate ever been seen to fail? | Never proven -> unproven gate; feed it must-fail input before trusting |
| 3 | Did every required job actually START? | Empty `runner_name` / queued -> retired or nonexistent runner label; `timeout-minutes` will not save you |
| 4 | Is any non-blocking job in a gate's `needs`? | Yes -> the gate waits on its queue time and can stall forever without failing |
| 5 | Did the test workflow finish green BEFORE the tag was pushed? | No -> the release is already building; a failing leg yields a PARTIAL release |
| 6 | Is the workflow meant to be dispatched by hand on the default branch? | No -> no Run button, dispatch API rejects it; not a permissions bug |
| 7 | Does any secret guard compare against a literal macro or use `-z`? | Yes -> self-matching / literal-passthrough; assert on decoded shape instead |

Ambiguity resolver — **green is evidence only when rungs 1-4 hold.** If any rung is unverified, the
correct report is "not proven", not "passed". Fail closed.

## Validation checklist

- [ ] Soft-fail sweep (`references/gate-audit.md` §1) run over every workflow / pipeline file; each hit classified intentional-advisory vs accidental-report-only.
- [ ] At least one enforcing gate proven to fail on deliberately bad input, and its selector confirmed to collect a non-zero number of files.
- [ ] Every gate believed to block confirmed present in the required-checks / branch-protection list (the file cannot express that).
- [ ] Any workflow intended for manual dispatch exists on the **default branch** (and its `inputs:` too).
- [ ] Every runner / image label confirmed as currently allocated, not retired.
- [ ] `timeout-minutes` set on long jobs, and no job that cannot fail the release appears in a gate's `needs`.
- [ ] Branch pushed and the test workflow green **before** any tag was created or pushed.
- [ ] For a fan-out release, confirmed which job creates the Release and which only upload — the partial-release risk named explicitly.
- [ ] No secret-presence guard compares against `$(NAME)` / `${{ }}` literal text or relies on `-z`; secrets mapped via `env:` and asserted on decoded shape.
- [ ] No secret value printed, echoed, or written to a log or annotation.
- [ ] Load-bearing validators pinned as versioned binaries, not moving action refs or daemon-dependent containers.

## Anti-patterns

| Pattern | Why it fails | Do instead |
|---|---|---|
| "The security/lint job is green, ship it" | A step with `\|\| true` / `continue-on-error` discards the non-zero exit; green means "passed" OR "found problems and was told to pass" | Grep for swallowed exit codes; treat report-only greens as informational |
| Add `continue-on-error: true` to unblock a flaky gate | Permanently converts the gate to report-only; nobody re-tightens it | Fix the flake, or split the flaky part into a separate explicitly-advisory job |
| Assume a gate blocks because it exists | Its selector may collect zero files (green because nothing ran), or the job may not be in required-checks at all | Feed it must-fail input once, watch the run go red, and confirm the check is required |
| Add a `workflow_dispatch` release workflow on a feature branch and expect a Run button | Dispatchable workflows are read from the default branch only | Merge to the default branch first; then dispatch |
| Debug a missing Run button as a permissions/PAT problem | The trigger is simply not on the default branch; permissions are a red herring | Check the default branch's copy of the file first |
| Rely on `timeout-minutes` to cap a job's wall clock | The clock starts at job START; a queued job is unbounded, to a 24h ceiling | Verify the runner label is live; treat queueing as a separate failure mode |
| Copy a runner label from an old workflow | Retired image labels queue silently instead of erroring, with empty `runner_name` | Check the current runner-image list when adding or bumping a label |
| Put an optional/advisory job in a gate's `needs` | `needs` waits on queue time, so an unstartable job stalls the gate without ever failing it | Keep non-blocking jobs out of `needs`; gate only on jobs that can fail |
| `git push origin main --tags` in one breath | Tests and Release start simultaneously; the release is building before the tests can stop it | Push the branch, wait for green, then tag |
| Assume a failing platform aborts the release | In a fan-out release one job creates the Release and others upload — a failing leg yields a PARTIAL published release | Gate the release-creating job on all legs, or tag only after tests are green |
| Delete the bad tag first to stop a release | The in-flight run keeps going and can still publish | `gh run cancel`, confirm with `gh release view <tag>`, then delete local + remote and re-tag |
| `[ "$S" = '$(S)' ]` to test whether a secret is set | The macro is expanded inside the script body — both sides become the value, so it always self-matches | Map via `env:`, assert on decoded shape (length / prefix / decoded first line) |
| `[ -z "$VAR" ]` to test whether a CI variable is set | An undefined variable stays as the literal `$(NAME)` string, not empty — so `-z` never fires | Same shape assertion; verify presence against the platform's variable list |
| Echo a secret (even truncated) to debug a guard | Leaks it into logs and annotations, which outlive the run | Assert on shape and report only the verdict |
| Edit the variable because the guard says it's missing | The guard is the more likely culprit; you break a working path chasing a false report | Confirm against the variable list / REST definition before changing anything |
| Wire a load-bearing gate to a third-party action ref | A ref someone else controls changes the verdict with no diff in your repo | Pin a versioned standalone binary; if the action ref is unavoidable, SHA-pin it (devops `CI_HARDENING.md`) |
| Reach for `docker run <linter>` on the runner | Adds a daemon dependency that fails for reasons unrelated to the code; the fix people reach for is a soft-fail flag (rule 1) | Download and pin the standalone binary |

## Cross-references

- `release-verification` (skill, this plugin) — owns the deploy side: is the fix actually live in the
  target environment (deployed-SHA reconciliation, code-marker liveness probe, env-secret diff,
  per-service SHA), **and the statement of the report-only-gate rule plus its deploy-time
  application**. This skill applies that rule while the workflow is being authored or reviewed and
  adds the authoring-time sweep and the prove-it-blocks procedure. Do not restate either side in the
  other.
- `agent-safety` (skill, agent-safety-guards-plugin) — owns what to do when a secret *value* actually
  appears in the session (compromised: revoke + reissue least-scope, never reuse or echo). This skill
  only owns how a workflow *tests* for a secret without printing it.
- `devops/CI_HARDENING.md` (checklist, devops plugin) — owns SHA-pinning third-party actions and
  steps, the "an approval-looking YAML block is only a pointer — enforcement lives in branch /
  environment protection settings" rule, and the renamed-required-check trap (a renamed job orphans
  the required check, so protection passes vacuously). Rules 1 and 6 here assume those and do not
  repeat them.
- `references/gate-audit.md` — §1 soft-fail token catalog + sweep command, §2 prove-it-blocks recipe,
  §3 shape-assertion patterns, §4 tag-withdrawal command sequence, §5 queue-vs-execution triage.
