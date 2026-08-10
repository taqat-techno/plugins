# release-safety

Prove a release is actually safe before you trust it. `release-safety` verifies that a fix is **really deployed to the target environment** (not just merged), diffs environment secrets before promotion, detects migration drift, and runs risky cutovers and migrations through a fixed, reversible skeleton — all **provider-neutral**, across any Git host, CI system, hosting provider, database, and ORM.

## Why this exists

The two most expensive release failures are quiet ones:

1. **"It's fixed" when it is only merged.** The PR is green, the branch is merged, everyone moves on — but the environment the user is hitting is still running the old commit. A merge is not a deploy.
2. **A destructive migration that destroys more than intended.** A "small" schema change drops a column in the same step it adds one, a bulk delete bypasses a soft-delete, or a cascade foreign key silently erases audit/financial history.

This plugin makes both failures hard to commit by accident.

## What it does

- **Reconciles the deployed commit SHA to the environment.** "FIXED" means *proven in the target environment*: the fix commit must be **contained** in the branch that runs there AND that branch must **map** to that environment per the deploy config. Both, or it is not proven.
- **Guards against silent local fallback.** A remote DB command can quietly fall back to a local DB / sqlite when the public connection URL is empty — and then "succeed" against the wrong target. The plugin makes you print the **resolved connection host/name first** and abort on a local fallback.
- **Diffs env-driven secrets before promotion.** Compares required env keys between source and target **by name and presence only** (never values). A migration or feature needing a key the target lacks is caught before the deploy, not during it.
- **Catches lockfile / package-manager mismatches.** A lockfile drift or a package-manager MAJOR-version mismatch breaks CI installs on the runner.
- **Detects migration drift before deploy.** Un-applied migrations, out-of-order history, and model-vs-schema gaps are deploy-blocking findings.
- **Runs risky migrations/cutovers through a safe skeleton.** discover (read-only, both sides) -> timestamped backups -> build+validate in a staging copy -> additive-then-cutover-last -> archive old artifacts by rename (never delete).
- **Keeps a green check and a published tag honest.** A gate that swallows its exit code renders identically to one that passed, and a branch pushed together with its tag starts the release before the tests that would have stopped it. The plugin sweeps for swallowed exit codes, makes you prove a gate can fail, and enforces push -> wait for green -> tag.
- **Reviews destructive / CASCADE risk.** A soft-delete override at the instance level does **not** protect bulk / admin / QuerySet / cascade deletes; cascade FKs pointing at financial / audit / historical tables are flagged, with `RESTRICT` / `SET NULL` preferred over `CASCADE`.

## Command

### `/release-verify`

The entry point. **Works with no arguments** — a bare `/release-verify` runs the full pre-promotion checklist and reports each item as PROVEN / UNPROVEN / NOT-APPLICABLE with the evidence behind it.

Pass an optional argument (a commit SHA, branch, environment, or a short description of what you are releasing) to route straight to the relevant concern. The argument is a shortcut, never required.

## Skills

### `release-verification`

Owns the "FIXED means proven in the target environment, not merged" discipline. It reconciles the deployed SHA (containment AND branch->environment mapping), diffs env secrets by name, forces the resolved connection target to be printed first, and checks lockfile / package-manager parity. It also names the specific deploy-liveness failure modes — a `/health` 200 served by the OLD build during a cold rebuild (gate on a code marker, not a ping), a multi-service deploy that skips/stalls one service (verify EACH service's SHA), a "deploy from source" CLI that ships the working tree not the commit, and an SSO/401-walled frontend (verify via the platform API) — plus a CI env-var false-FAILURE that masks a real test failure, and report-time-vs-deploy-time triage. Detailed procedures live in:

- `references/deployed-sha-reconciliation.md` — read the running SHA, prove containment, confirm branch->environment mapping, and the deploy-liveness failure modes (code-marker probe, per-service SHA, deploy-from-source working tree, walled-frontend platform API).
- `references/env-secret-diff.md` — diff env keys by name/presence, resolve the connection target without printing it, and the local-fallback guard.

### `migration-safety`

Owns the risky-migration / cutover skeleton, drift detection (including environment-vs-environment schema drift), and destructive/CASCADE review. For a cross-system data migration it builds the extractor from the live `information_schema` (not committed schema/migration files, which drift) and flags that a DB dump is not a full migration when binaries live on app-server local disk (check the Dockerfile `VOLUME` / bind-mount / backup scope). Detailed procedures live in:

- `references/cutover-skeleton.md` — the expand/contract runbook (discover -> backup -> stage -> additive -> cutover-last -> archive-by-rename).
- `references/destructive-checks.md` — the soft-delete-layer audit, the bulk-delete bypass paths, and the cascade-FK inventory.

### `github-actions-release-safety`

Owns the **authoring** side of the two signals a team actually trusts — a green check and a published tag. It sweeps workflow files for gates that swallow their exit code (`|| true`, `continue-on-error`, a tool's own soft-fail flag, or a multi-line `run:` without `set -e`) and makes you prove a gate blocks instead of assuming it. It also covers the `workflow_dispatch` default-branch rule (a dispatchable workflow added on a feature branch has no Run button), the `timeout-minutes` scope trap (it bounds execution, not queue time, so a retired runner label queues silently and withholds the run's logs), the push -> wait for green -> tag ordering and the fan-out **partial release**, the tag-withdrawal order, and the secret-presence guard that self-matches when a CI system expands its own macro inside a script body (assert on decoded shape, never the literal, never printed). Detailed procedures live in:

- `references/gate-audit.md` — the soft-fail token catalog and sweep command, the prove-it-blocks recipe, the shape-assertion patterns, the tag-withdrawal sequence, and the queue-vs-execution triage.

`release-verification` owns the report-only-gate rule's statement and its deploy-time application; this skill applies it while the workflow is being written. Neither restates the other.

## Hook

A **non-blocking `SessionStart` advisory**. At session start it prints a single short line reminding you to verify in the target environment before calling a fix done or running a risky migration. It is advisory only: it never blocks, never prompts, and never mutates anything.

## Scope / non-goals

This plugin is about **release safety and verification**. It is **not**:

- a deployment tool that promotes or rolls out for you (it verifies and advises; you act),
- a database migration *runner* (it owns the safe *procedure*, not a specific engine's tooling),
- a local-environment doctor (that is a separate concern) or a CI configuration tool.

## Portability

`release-safety` is built to run for **any project, on any stack**. Its behaviour never depends on a specific Git host, CI system, hosting provider, database, ORM, company, repo, or credential.

- The Git host, CI system, hosting provider, database engine, ORM, and migration tool are **adapter inputs discovered at run time**.
- Vendor- and engine-specific command text lives in the reference docs; the skills stay platform-neutral.
- No absolute user paths, no hard-coded hosts, no project assumptions are baked into behaviour. **No secret values are ever printed** — env keys are compared by name and presence only.

---

> Example (illustrative — not required): a user reports a fix "isn't working" in staging. `/release-verify` reads the SHA staging is running, finds the fix commit is on `main` but staging tracks a `staging` branch that does not contain it yet, diffs env keys (all present), and returns NOT PROVEN with the exact branch-containment evidence — without printing any secret from the deploy config.
