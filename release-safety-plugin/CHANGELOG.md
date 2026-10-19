# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.2] - 2026-10-19

Skill triggering tuned against real eval results. Measured with `claude plugin eval --runs 1 --model claude-sonnet-5-5`; the no-plugin baseline is the 2026-10-19 run, and Δ counts the criteria grader only.

### Changed
- `migration-safety` description opens with reviewing a rename or drop plan on a large, constantly-read production table, especially one migration that adds, copies and drops in a single deploy. The "Covers" list is shortened to stay under 1,024 characters.

### Eval results
- Must-fire: 2/3 -> 3/3. Must-not-fire: 3/3 quiet before and after. Mean Δ: +0.00 -> +0.00.

## [0.5.1] - 2026-10-19

### Fixed
- **Push guard recognises the tag pushes it used to miss (RA-REL-01).** Variable tags (`git push origin "$TAG"`, `"v$VERSION"`, `$(git describe --tags)`, and any `$X` when the same command creates or names a tag), moving major tags (`v1`; `latest`/`stable` when force-pushed), `git push origin tag <name>`, commands wrapped in `bash -c` / `sh -c` / `pwsh -Command`, `$(...)` bodies, and `gh -R/--repo owner/repo release create|delete`. The parser now matches git-safety's: `${...}`/`$(...)` are opaque words, more wrappers are skipped, gh global flags are skipped.
- **Branch-shaped refs are no longer read as tags (RA-REL-02).** `release-1.2`, `release/1.2`, a two-part `17.0`, `refs/heads/...`, `$BRANCH`-style expansions and the checked-out branch (read from `.git/HEAD`, no git process) are branches. `git push origin tag v1.2.0` is a tag push, not a branch-plus-tag push.

### Added
- Rules `push-mirror` (`git push --mirror`, RA-REL-03) and `tag-move` (a tag pushed with `-f`/`--force`/`+ref`).
- `--self-test` grows from 22 to 54 cases (23 positive and 9 negative new rows); new offline hook tests for ask mode on the new shapes, branch-shaped refs, and the checked-out-branch exemption. The README documents exactly what counts as a tag.

## [0.5.0] - 2026-10-19

### Added
- **`scripts/check_release.py` (REL-P2-04).** Read-only tag / version check: the tag matches the manifest version (package.json, pyproject.toml, Cargo.toml, .claude-plugin/plugin.json, VERSION), the CHANGELOG has an entry, and the version is greater than every earlier tag in its series (`v*` or `<pkg>-v*`). Exit 0 / 1 / 2, `--json`. Only runs `git tag --list` and `git describe --tags --exact-match`.
- **`references/tag-version-correctness.md`**: the four tag checks, tag-on-the-green-commit, and rollback readiness (previous build and the action that redeploys it). Wired into `github-actions-release-safety` rule 4, the `release-verification` safety gates and checklist, and `/release-verify` checklist items 8 and 9.
- **`references/action-pinning-and-protection.md`**: SHA-pinning actions and images, "an approval-looking YAML block is not the gate", and the renamed-required-check trap, now in this plugin instead of deferring to the devops plugin's `CI_HARDENING.md`.
- **`hooks/release_push_guard.py` (REL-P2-03)**, PreToolUse on `Bash|PowerShell`: branch and tag pushed together, `--tags`/`--follow-tags`, release-tag pushes, `gh release create`, and remote tag / release deletion. Default `advise` (reminder, which arrives with the tool result); opt-in `ask` via the new `guard_mode` option or `RELEASE_SAFETY_MODE`. `--self-test` runs its table.
- Plugin options `guard_mode` and `session_hint`.
- Offline tests (REL-P2-06): `tests/test_check_release.py`, `tests/test_hooks.py`.
- Evals: `fires-on-merged-fix-not-live-on-staging` (release-verification), `fires-on-drop-column-in-same-migration` (migration-safety), `ignores-explain-semver-meaning`, `ignores-write-sql-join-query`.

### Changed
- **SessionStart reminder is conditional (REL-P2-05, default behaviour change).** It speaks only in a project with CI, deploy or release-tool configuration, at most once per project (marker under `${CLAUDE_PLUGIN_DATA}/session-hint/`), as SessionStart `additionalContext` JSON, and names the namespaced `/release-safety:release-verify`. Silence it with `session_hint` = false or `RELEASE_SAFETY_HINT=off`.
- Hooks use the vendored `hooks/_vendor/hooklib.py`.
- Skill descriptions trimmed to under 1,024 characters, starting with "Use when" (REL-P3-07). Cross-references to `agent-safety-guards` and `django` are conditional on those plugins being installed.
- README restructured to the marketplace template, with requirements, the "nothing here blocks" statement and how to silence the hooks (REL-P1-02).

### Security
- The three skills and the command treat deploy logs, CI logs, platform API responses, migration output and release notes as data: instructions found there are quoted to the user, never acted on.
- Removed `evals/results/`, which held an empty run with absolute machine paths.

Not done: running the evals (REL-P2-06) costs money and is left to the maintainer. The skill rename suggested in REL-P3-07 (`ci-release-safety`) was not made: renaming a skill breaks existing eval targets and references for no behaviour gain.

## [0.4.2] - 2026-10-19

### Fixed
- **The SessionStart hook now names an interpreter (REL-P0-01).** It executed `session_start_release_advisory.py` directly, which needs the executable bit and a shebang-capable host; it failed on macOS/Linux checkouts with mode 100644 and on any root containing a space.
- **Hook launch is portable and space-safe (Wave 1, QW #2/#3).** `hooks/hooks.json` now runs each python hook through one POSIX-sh launcher: the `${CLAUDE_PLUGIN_ROOT}` path is quoted (a plugin root containing a space no longer hands python a truncated path, which exited 2 and blocked the call), the interpreter is picked from `python3` -> `python` -> `py -3` with the `command -v` builtin (guards no longer fail open where `python3` is not the name), a missing script or unresolved root exits 0, and the hook's own exit code is propagated unchanged. Known limit: on Windows without Git Bash, Claude Code runs shell-form hooks in PowerShell, where the launcher does not parse and the hook fails open (non-blocking).

### Tests
- `tests/test_hook_launcher.py` proves quoting, exit-2 propagation from a root with a space, unresolved root -> 0, and no python on PATH -> 0.

## [0.4.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (1 must-fire case + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-workflow-dispatch-missing-run-button` targets `github-actions-release-safety`
- `ignores-github-actions-cache-speedup` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.4.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 3 skills (previously inert).

## [Unreleased] — CI-workflow and tag authoring safety

### Added

- **github-actions-release-safety skill (0.1.0)** — the authoring side of the two signals a team trusts (a green check, a published tag): the report-only-gate sweep and prove-it-blocks procedure at authoring/review time; the `workflow_dispatch` default-branch rule (a dispatchable workflow added on a feature branch has no Run button); the `timeout-minutes` scope trap (bounds execution, not queue time — a retired runner label queues silently to the 24-hour ceiling and withholds the run's downloadable logs); the push -> wait for green -> tag ordering and the fan-out PARTIAL-release mechanism; the tag-withdrawal order (cancel, confirm, delete, re-tag); the secret-presence guard that self-matches when a CI system expands its own macro inside script bodies (assert on decoded SHAPE, never the literal, never printed); and running a load-bearing gate's tool from a pinned standalone binary so a flaky daemon cannot create pressure to soften the gate.
  - `references/gate-audit.md` — soft-fail token catalog + sweep command, prove-it-blocks recipe, shape-assertion patterns, tag-withdrawal sequence, queue-vs-execution triage.
  - Boundaries: defers the report-only-gate rule statement and its deploy-time application to `release-verification`; the credential-compromise response to `agent-safety`; and SHA-pinning / approval-block / renamed-required-check rules to the devops plugin's `CI_HARDENING.md`.

### Changed

- `plugin.json` bumped to 0.3.0; description extended to cover the workflow/tag authoring side and keywords `github-actions`, `workflow-safety`, `release-tagging` added. Marketplace entry description updated to match.
- `README.md` — added the `github-actions-release-safety` skill section and a "What it does" bullet for the green-check / tag signals.
- `/release-verify` command — routes to the new skill and gained checklist item 7 (report-only gates, push → wait for green → tag). The "two skills" wording is now skill-count-neutral.
- `release-verification` skill — the prove-it-blocks procedure is now a cross-reference to `github-actions-release-safety` rather than a restatement, and the sibling skill was added to its `defers_to` and Cross-references.

## [0.2.0] — 2026-07-23 — Deploy-liveness failure modes, cross-system migration, env drift

### Added

- **release-verification skill (0.3.0)** — names the specific "is it actually deployed?" failure modes so a green deploy is not mistaken for a live one:
  - A DB-free `/health/` 200 can be answered by the **OLD deployment** during a cold rebuild — liveness is now gated on a direct probe of a **code marker** (a removed API/schema field asserting absent, or an added field asserting present), not a health ping.
  - A multi-service deploy can silently **SKIP** or stall one service (WAITING / stopped) — the skill verifies **each** service's deployed SHA, not one.
  - A CLI "deploy from source" (e.g. a `railway up --ci --detach`-style command) uploads the local **working tree**, not the git commit — diff the tree against the intended commit first; a stuck-deploy "fix" can ship uncommitted/parallel changes, and a `redeploy` may refuse a stuck deployment.
  - An SSO / deployment-protection-walled frontend (401) cannot be HTTP-verified — read the platform API (`state:READY` + commit SHA).
  - Added the **CI env-var false-FAILURE** case (a red env/setup error that masks a real test failure underneath — the complement of the report-only false-PASS already covered).
  - Added the **rolled-back reproduction** framing for walled frontends with a reachable DB (in-process auth + always-rollback transaction), deferring the concrete recipe to the `django-testing` skill.
  - Added **report-time vs deploy-time** triage to separate already-fixed client reports from genuinely new bugs.
  - `references/deployed-sha-reconciliation.md` — new "Deploy-liveness failure modes" section (code-marker probe, per-service reconciliation, deploy-from-source working tree, walled-frontend platform API).
- **migration-safety skill (0.2.0)** — extends discovery for cross-system moves and environment drift:
  - Cross-system extraction is built from the **live `information_schema`** / system catalog, never from committed schema or migration files (e.g. `schema.prisma`, an ORM model folder) that drift from the real database.
  - A DB dump is flagged as **not a full migration** when binary assets live on app-server local disk — check the Dockerfile `VOLUME`, container bind-mounts, storage config, and the backup job's scope; copy binaries separately.
  - Migration drift detection now includes **environment-vs-environment schema drift** (a constraint / index / column present in one environment's live schema and missing in another).
  - New adapter inputs `schema_source_of_truth` and `binary_asset_locations`; report fields `Schema source`, `Binary assets`, and `Env drift`.

### Validation

- `python validate_plugin.py release-safety-plugin` -> 0 errors.
- Genericness sweep: provider names (Railway / Vercel / Prisma) appear only as clearly-labeled illustrative examples; the rules are stated provider-neutral. No company, client, or project names; no hostnames, URLs, credentials, or machine-specific paths. No secret values printed — env keys compared by name and presence only.

## [0.1.0] — 2026-06-13 — Initial release

### Added

- **release-verification skill** — encodes the "FIXED means PROVEN IN THE TARGET ENVIRONMENT, not merged" discipline. Reconciles the deployed commit SHA to the environment (fix commit contained in the branch AND that branch mapped to the environment per the deploy config); diffs env-driven secrets between source and target by key name and presence only before promoting; forces the resolved connection host/name to be printed FIRST to guard against a silent fallback to a local DB / sqlite when the public connection URL is empty; and checks lockfile / package-manager MAJOR parity that breaks CI installs. Ships a RELEASE VERIFICATION REPORT contract and a verdict table.
  - `references/deployed-sha-reconciliation.md` — read the running SHA, prove containment, confirm branch->environment mapping (provider-neutral query variants).
  - `references/env-secret-diff.md` — diff env keys by name/presence, resolve the connection target without printing it, and the local-fallback guard.
- **migration-safety skill** — the risky-migration / cutover skeleton (read-only discovery of both sides -> timestamped backups -> build+validate in a staging copy -> additive-then-cutover-last -> archive old artifacts by rename, never delete), the destructive/CASCADE review (an instance-level soft-delete does NOT protect bulk / admin / QuerySet / cascade deletes; cascade FKs reaching financial / audit / historical tables are flagged, preferring RESTRICT / SET NULL), and migration DRIFT detection before deploy. Ships a MIGRATION SAFETY REPORT contract.
  - `references/cutover-skeleton.md` — the expand/contract runbook with provider-neutral command slots and a per-step rollback posture.
  - `references/destructive-checks.md` — the soft-delete-layer audit, the bulk-delete bypass table, and the cascade-FK inventory procedure.
- **/release-verify command** — runs with a sensible no-argument default (full pre-promotion checklist, each item marked PROVEN / UNPROVEN / NOT-APPLICABLE with evidence); an optional argument routes straight to the relevant skill. Never required.
- **SessionStart advisory hook** — non-blocking advisory that reminds the user to verify in the target environment before calling a fix done or running a risky migration. It never blocks, delays, or fails the session; it only advises.

### Validation

- `python validate_plugin.py release-safety-plugin` -> 0 errors.
- Genericness sweep: no company, client, or project names; no business-domain terms; no production/staging hostnames or URLs; no private repo names; no credentials, tokens, OTPs, or reset codes; no machine-specific identifiers. No secret values are printed anywhere — env keys are compared by name and presence only. Any concrete example is clearly labeled illustrative and is not required for plugin behavior.
