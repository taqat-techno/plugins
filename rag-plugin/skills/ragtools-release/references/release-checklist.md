# Release checklist — the six permanent invariants

Six invariants that every ragtools release must satisfy before it ships. Derived from the TAQAT Techno release-lifecycle discipline: the app/data boundary, schema versioning discipline, dev-mode isolation, manual-test discipline on upgrade paths, uninstall opt-in correctness, and canonical-doc accuracy.

**Important:** this checklist lives in the `rag-plugin` (the operator console). The canonical source-of-truth for ragtools release rules is `docs/RELEASE_LIFECYCLE.md` in the upstream `rag` product repo. When the two disagree, upstream wins — and the plugin's checklist needs updating. See the "Updating this checklist" section at the bottom.

## Invariant 1 — No user data into the install directory

**Statement:** no code path writes user data (config, indexed content, state DB, project-specific files, logs) into the installer's `{app}\` directory. All user data lives in `%LOCALAPPDATA%\RAGTools\` on Windows, `~/Library/Application Support/RAGTools/` on macOS, or `$XDG_DATA_HOME/RAGTools/` on Linux.

**Why it matters:** the install directory is *replaceable* — an upgrade or reinstall may delete and recreate it. If user data lived there, every upgrade would wipe the index. The `{app}` vs `{userdata}` split is what makes in-place upgrades safe.

**Source of truth:**
- `src/ragtools/config.py` — `get_config_write_path()` returns the persistent-user-data path, never `{app}\`.
- `src/ragtools/service/routes.py` — the HTTP endpoints that persist user data route through `get_config_write_path()`.
- Installer scripts (Inno Setup `.iss` on Windows, macOS tarball build) — must not `WriteReg`, `WriteINI`, or `FileCopy` user data into `{app}\`.

**Pre-check heuristic for this skill:**
- If the release has no user-data boundary changes (Phase 1 answer 6) → PASS.
- If new file-write paths were added → UNCERTAIN; maintainer confirms each writer targets a persistent-user-data path.

**Red flags:**
- New code in `src/ragtools/integration/` or `src/ragtools/service/` that opens a file for writing using a relative path or a hardcoded `{app}\` path.
- Installer routines that copy files into `{app}\` from user input.
- A "default config" shipped inside `{app}\` that the service then writes to.

## Invariant 2 — Schema changes bump version AND ship migration

**Statement:** any change to a persistent schema (config file, SQLite state DB, Qdrant collection, encoder output dimension) must bump its version constant AND ship a forward-migration step. Reverse migrations are optional but documented.

**Why it matters:** users upgrade across versions. If v2.5.0 wrote config in format X and v2.5.1 reads format Y without a migration, upgrade is silent data loss. Version constants let the service detect the mismatch and run the migration (or refuse to start with a clear error).

**Source of truth (what each schema change requires):**

| Schema | Version constant | Migration location |
|---|---|---|
| Config file (`config.toml`) | `src/ragtools/config.py` → `CONFIG_VERSION` | `src/ragtools/migrations/config/` |
| SQLite state DB | `PRAGMA user_version` in `src/ragtools/state/schema.py` | `src/ragtools/migrations/state/` |
| Qdrant collection | encoder output dim in `src/ragtools/embed/*.py` | Full reindex required; documented in CHANGELOG |
| Index schema (chunk/metadata shape) | `INDEX_SCHEMA_VERSION` | Reindex strategy: incremental migrate vs full rebuild |

**Pre-check heuristic:**
- If the release has no schema-touching changes (Phase 1 answer 4 = no) → PASS. Version bumps not required.
- If yes → UNCERTAIN; maintainer confirms each changed schema has both a version bump and a migration.

**Red flags:**
- A diff in `src/ragtools/state/schema.py` without a corresponding `PRAGMA user_version` bump and migration file.
- An encoder model change (e.g. `all-MiniLM-L6-v2` → `all-mpnet-base-v2`) without a full-reindex note in the CHANGELOG and a `Qdrant collection` version bump.
- A new field in `config.toml` without a `CONFIG_VERSION` bump (new fields are technically backward-compatible, but the version bump makes the read-vs-write divergence explicit).

## Invariant 3 — Dev-mode isolation

**Statement:** dev-mode startup (running `rag serve` or `rag service start` from a source checkout with `pip install -e .`) does not touch `%LOCALAPPDATA%\RAGTools\` and does not register a Windows Startup task. Dev-mode is fully contained in the checkout's `./data/` directory.

**Why it matters:** a developer running from source should not corrupt the installed-version's state, and should not have their dev process auto-start on every login. The separation is a local-dev safety measure.

**Source of truth:**
- `run.py` — the `is_packaged()` guard (typically around lines 68 and 85 in v2.5.x) gates startup-task registration to packaged mode only.
- `src/ragtools/config.py` — `get_config_write_path()` branches on the install mode; dev mode returns `./ragtools.toml` (CWD-relative), packaged mode returns the platform-absolute path.

**Pre-check heuristic:**
- If the release does not change `is_packaged()` or any caller → PASS.
- If yes → UNCERTAIN; maintainer confirms dev-mode still isolates from `{userdata}` and does not register a Startup task.

**Red flags:**
- Any removal of the `is_packaged()` guard.
- New code that reads `%LOCALAPPDATA%` without a matching packaged-mode branch.
- A test that runs in dev mode but writes to `{userdata}`.

## Invariant 4 — Upgrade-path manual test

**Statement:** the built installer is manually exercised on a machine that already has the immediately previous version installed. The upgrade path preserves user data (index + config + projects) with zero manual intervention.

**Why it matters:** structural tests can't catch installer-upgrade-path bugs. The v2.5.0 `ForceKillRagProcesses` fix in v2.5.1 is a textbook example — nothing in the unit-test or integration-test suites catches "installer refuses to proceed because `rag.exe` is still running in memory". Only a manual install from a running v2.5.0 state verifies the fix.

**Source of truth:**
- The downloaded (not locally-built) installer artifact.
- A machine (VM, laptop, or clean Windows user profile) with the previous version already installed, running, with real indexed projects.

**Ack options:**
- `yes, will manually test before promote` → release ships as **pre-release** on GitHub. Promote to latest only after the manual test passes. This is the default safe path for installer-touching changes.
- `yes, already tested` → maintainer names the machine, the date, and the outcome. That evidence goes in the release ack log.
- Any other answer → **blocked**. Release does not ship until the manual test is complete or the maintainer commits to doing it before promote.

**Red flags:**
- Shipping a release with installer changes and no manual-upgrade test.
- Relying on automated CI for upgrade-path coverage. CI installs on a clean image, not on a pre-upgraded image — CI cannot reproduce the running-previous-version scenario.

## Invariant 5 — Uninstall opt-in prompt

**Statement:** uninstall correctly handles both the "full wipe" path (delete `{app}\` and `{userdata}\`) and the "keep data" path (delete `{app}\` only). Both branches are manually validated whenever the uninstall code path is touched.

**Why it matters:** the uninstaller is the last-chance data-preservation surface. A bug that silently wipes user data on what-was-supposed-to-be the "keep data" path is catastrophic and irreversible.

**Source of truth:**
- Inno Setup `[UninstallRun]` section + `[Code]` Pascal script in `packaging/ragtools.iss`.
- macOS uninstall shell script.

**Pre-check heuristic:**
- If the release has no installer-touching changes → PASS (same code path as the previous validated release).
- If installer touched the uninstall path → UNCERTAIN; maintainer exercises both uninstall branches on a test machine.

**Red flags:**
- Uninstall code change without manual test evidence.
- A new uninstall-prompt option added without a matching manual-test of each option's branch.

## Invariant 6 — `RELEASE_LIFECYCLE.md` accurate

**Statement:** the upstream `docs/RELEASE_LIFECYCLE.md` in the `rag` product repo accurately describes the app/data boundary, the supported platforms, the artifact types, and the invariants this checklist enforces. New platforms or artifact types are reflected in the doc.

**Why it matters:** the doc is the canonical release-lifecycle rulebook. If it drifts from reality, future maintainers (or external contributors) will get wrong answers. The plugin's checklist is downstream of that doc — divergence is a bug somewhere.

**Source of truth:**
- `docs/RELEASE_LIFECYCLE.md` in the upstream `rag` product repo.

**Pre-check heuristic:**
- If the release adds no new platforms or artifact types AND no boundary changes → PASS.
- If new platforms shipped (e.g. Linux arm) or the boundary model shifted → UNCERTAIN; maintainer confirms the doc covers the new surface.

**Red flags:**
- A release adding a new platform (e.g. `macos-amd64`) without a doc update.
- A release changing the replaceable-app vs persistent-user-data model (e.g. moving logs from `{userdata}\logs` to `{app}\logs`) without an ADR.

## Updating this checklist

New permanent invariants are added here when:

1. A pattern of cross-release bugs establishes that an invariant is load-bearing (not one-off).
2. An ADR lands in the upstream `docs/RELEASE_LIFECYCLE.md` codifying the new invariant.
3. The plugin version bumps (minor — user-visible gate surface changed) to signal the new coverage.

Existing invariants are not rewritten in place. If an invariant's reasoning changes, supersede with a new version of the checklist (e.g. `release-checklist-v2.md`) and retire the old one with a pointer.

One-off checks specific to a single release (e.g. "v2.6.0 introduces a new encoder; verify Qdrant collection resize is idempotent") go in the release notes for that version, not here.

## See also

- The skill at `skills/ragtools-release/SKILL.md` — walks this checklist with the maintainer
- The upstream `docs/RELEASE_LIFECYCLE.md` — canonical release-lifecycle doc
- `docs/decisions.md` in this plugin — binding plugin decisions; append D-NNN when adding new invariants here
