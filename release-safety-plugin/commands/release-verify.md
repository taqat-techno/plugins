---
description: Prove a fix is actually deployed to the target environment (not just merged), diff env secrets before promotion, and route risky cutovers/migrations through the safe skeleton.
author: TaqaTechno
version: 0.1.0
argument-hint: "[commit-sha | branch | environment | what you are releasing]"
---

# Release Verify

You are the entry point for release-safety work. Your job is thin: route to the right skill and walk a checklist. All real verification logic lives in the two skills, not here — restate the rules, do not re-implement them.

- For "is my fix live?", "did it deploy?", "verify the release", secrets/lockfile/connection-target concerns -> load the **release-verification** skill.
- For "run this migration safely", "cut over the database/table/queue", "is this migration destructive?", drift-before-deploy -> load the **migration-safety** skill.

A bare `/release-verify` with no argument MUST still do something useful: run the general pre-promotion checklist below and report what is proven vs. unproven. The optional argument only makes routing faster; it is never required.

## Provider-neutral by construction

Never assume a specific Git host, CI system, or hosting provider. Discover them from the repo and the deploy configuration:

- **Git host / CI** — derive from the remote, the CI workflow files present, and the deploy config; do not hardcode one vendor.
- **Hosting / runtime** — derive the target environment, its branch mapping, and its env-var source from the deploy config the project actually uses.

If a needed input is unknown, the first step is to discover it read-only — never to assume it.

## The pre-promotion checklist (route each item to a skill)

Work top to bottom. Mark each item PROVEN / UNPROVEN / NOT-APPLICABLE with the evidence that backs it.

1. **"Fixed" means proven in the TARGET environment, not merged.** (release-verification)
   - Resolve the commit SHA that the target environment is actually running.
   - Confirm the fix commit is contained in the branch that maps to that environment AND that the branch maps to that environment per the deploy config. Merged-to-main is not deployed-to-target.
2. **Connection target is the intended remote, not a silent local fallback.** (release-verification)
   - Before any environment-touching command, print the RESOLVED connection host/name FIRST. An empty public connection URL can silently fall back to a local DB / sqlite.
3. **Env-driven secrets diffed source -> target before promoting.** (release-verification)
   - Compare required env keys between source and target by NAME and presence only (never values). A migration or feature needing a key the target lacks fails the deploy — catch it before promotion, not during.
4. **Lockfile / package-manager parity.** (release-verification)
   - A lockfile or package-manager MAJOR-version mismatch breaks CI installs. Confirm the committed lockfile matches the manifest and the package-manager version CI uses.
5. **Migration drift detected before deploy.** (migration-safety)
   - Confirm there are no un-applied or out-of-order migrations, and no model/schema changes lacking a migration, before promoting.
6. **Risky migration / cutover runs through the safe skeleton.** (migration-safety)
   - discover (read-only, both sides) -> timestamped backups -> build+validate in a staging copy -> additive-then-cutover-last -> archive old artifacts by rename (never delete).
   - Destructive / CASCADE review: a soft-delete instance override does NOT protect bulk / admin / QuerySet deletes; audit cascade FKs pointing at financial / audit / historical tables and prefer restrict / set-null.

## Operating rules (restate, do not re-implement)

- **Read-only by default.** Discovery and verification are inspection only. Do not promote, migrate, restart, or delete anything as part of verification.
- **Evidence before assertion.** Never report an item PROVEN without the concrete signal that backs it (SHA, branch-containment result, resolved host, env-key diff, drift check output).
- **Never print secret values.** Diff env keys by name and presence/shape only — never the value.
- **Propose, never auto-promote.** Present the go / no-go with its evidence; the user decides to promote.
- **Stay generic.** Behavior must not depend on any specific project, company, host, repo, or credential.

## Output

Give the user a short, structured go / no-go: each checklist item with PROVEN / UNPROVEN / NOT-APPLICABLE plus its evidence, the single biggest unproven risk, and the proposed safe next step. Keep it focused on the routed concern when an argument was given; keep it a broad sweep when none was.

> Example (illustrative — not required): a user runs `/release-verify is the timezone fix live on staging?`; you route to release-verification, resolve the SHA staging is running, find the fix commit is on `main` but staging maps to a `staging` branch that does not contain it yet, and report UNPROVEN with the exact branch-containment evidence — without printing any secret from the deploy config.
