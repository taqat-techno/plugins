# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
