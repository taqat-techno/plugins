# Changelog

All notable changes to this plugin are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
