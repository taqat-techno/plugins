---
name: odoo-sh
description: >-
  Use when a project deploys to Odoo.sh: a module change pushed to a staging or production
  branch builds green but the new field, view or translation is missing (module not
  upgraded), a staging build was rebuilt and its database name or API key changed, a stage
  build might call production integrations, someone wants to run a daemon, worker, MCP
  server or long job on Odoo.sh, a build fails on an unknown or uninstallable dependency,
  vendoring OCA modules into an Odoo.sh repo, merging branches with reverted history, or
  proving which code an Odoo.sh build is actually running.
license: "MIT"
metadata:
  version: "1.0.0"
  author: "TaqaTechno"
  odoo-versions: ["16", "17", "18", "19"]
  categories: [odoo-sh, deployment, release, repository]
---

# Odoo.sh platform, release and repository rules

## Scope and example requests

Platform behaviour of Odoo.sh that ordinary Odoo knowledge does not predict: when modules
upgrade, what a staging rebuild resets, what the platform cannot host, how to prove a deploy,
and how to keep the repository buildable.

Example requests:

- "I pushed to the staging branch, the build is green, but my new field is not there"
- "The staging database name changed and my API key stopped working"
- "Can I run our sync worker / MCP server inside Odoo.sh?"
- "The Odoo.sh build says a dependency is unknown, but the module is in the repo"
- "How do I add two OCA modules to our Odoo.sh repo?"

Related: live record checks go through the `odoo` data MCP (skill `odoo-live-instance`);
upgrade scripts and migrations belong to the `odoo-upgrade` skill; local servers to
`odoo-service`.

## 1. A module upgrades only when its version changes

Odoo.sh runs the update for a module only when the `version` in its manifest differs from
the one the database runs. Same version: the files deploy, nothing loads (no new fields,
views, data or model translations), and the build is still green.

- **Bump every module you changed**, including a module whose only change is `i18n/*.po`.
- **Check after every merge, not before.** Merging the target branch into yours can bring
  its own bump of the same module; if both sides chose the same number, git merges it with
  no conflict and the module ships unloaded. For each changed module: files differ from the
  target branch but versions are equal means a collision.
- **The instance is the truth, the branch is a claim.** Capture `ir.module.module`
  `latest_version` for the changed modules before the push and compare after (section 4).

## 2. Odoo.sh cannot host daemons or long jobs

Four platform mechanisms stack against any long-running process (an MCP server, a sync
worker, a queue consumer, a websocket bridge):

1. The acceptable-use policy forbids daemons.
2. Only port 443 is reachable, through a proxy you cannot configure.
3. The filesystem outside the filestore does not survive a rebuild.
4. `limit_time_real` kills an HTTP worker that holds a request too long (about two
   minutes by default); staging and dev builds run a single worker, and production
   restarts on every push.

Run stateful processes outside the platform and connect over XML-RPC / JSON-2. Inside
Odoo.sh allow only short, stateless controllers (for example `auth='bearer'` endpoints)
that finish well under the worker limit and write nothing to local disk.

## 3. Staging builds are disposable copies of production

A rebuild of a staging branch, or a push to it, creates a new build from a fresh copy of
production; the previous build is dropped with no backup, and staging builds expire.

- **The database name changes on every build** (`<project>-stage-<build>`, or similar), so
  a saved connection points at a database that no longer exists. Symptom: "database does
  not exist", or worse, a count of 0 that looks like an empty database. The data MCP's
  `"db": "auto"` follows the rotation; check `odoo_status` first.
- **API keys and users created inside an old build are gone.** Create integration users
  and keys in production so every staging build inherits them.
- **A repair done on one staging build is lost on the next.** Keep provisioning and data
  fixes as idempotent scripts in the project (a re-run creates nothing), not in temp folders.
- **Warn before pushing to or rebuilding staging during UAT**, and state the build's expiry.

### Neutralize integrations on every stage build

A stage build inherits production configuration, including outgoing integration URLs and
credentials (`ir.config_parameter`, integration config records, webhooks, payment and
shipping providers). A manual "sync now" on staging can write into the production system.
Odoo.sh neutralizes mail and crons, not your custom integrations.

- Before any sync or outbound call on staging, read the target URL and confirm it is not
  production.
- Put neutralization in code (a neutralize hook or a stage-only script run after each
  build) so it cannot be forgotten.

## 4. HTTP 200 is not proof of a deploy

Odoo.sh posts no commit status and no check runs to the Git host, and the old build can
answer 200 while the new one is starting. Ask the application:

- `ir.module.module` `latest_version` and `write_date` for the changed modules (changed
  modules carry a fresh timestamp; untouched ones keep the old one).
- For a migration, check the schema both ways: the new column present **and** the old one
  gone (a rename versus a new field beside orphaned data).
- State the limit of the evidence: a staging database with zero rows proves structure, not
  data preservation.

## 5. "Unknown" dependency on a build

A dependency can show as `unknown` in `ir.module.module` although its code is deployed,
when the build's Apps list was not refreshed after the commit that added it.

1. Compare the deployed commit with your local and remote branches.
2. Run `ir.module.module.update_list()` ("Update Apps List") and re-query.
3. Only then treat the code as missing.

A missing manifest `depends` hides locally when another installed module pulls the model
in, and fails on a fresh build (`unknown comodel_name`). Before promoting, install all custom
and vendored modules together with `-i ... --stop-after-init` on a throwaway fresh database
from the merged state: the local equivalent of a new build.

## 6. CI: GitHub Actions cannot build Enterprise

Actions has no access to the Enterprise source, so ephemeral-Odoo jobs fail for Enterprise
projects. Keep Actions to static gates (linters, manifest/XML/Python checks, secrets and
dependency scans); Odoo.sh is the authoritative build and test. Confirm the Git root
(`git rev-parse --show-toplevel`; on Odoo.sh repos the modules usually sit at the root) and
the exact branch-name casing before writing workflow triggers: branch filters are
case-sensitive.

## 7. OCA dependencies: vendor module by module

Whole-repository submodules pull dozens of unused modules (and their dependencies) into
every build and can make it unbuildable.

- Copy only the modules you depend on into `oca/` at the repository root.
- Record provenance in `oca/README.md`: source repository, branch, commit, module version
  and licence for each module.
- **Never edit vendored code**; inherit it from a custom module. Updating means re-copying
  from a newer upstream commit and updating the README row.
- Point the local `addons_path` at `oca/`, not at full OCA clones, so only one copy loads.

## 8. Reverted shared history makes auto-merge destructive

When one branch reverted a large merge that the other branch built on, git sees the revert
as deletions and **auto-merges** them silently; the conflicts are not the danger, the
cleanly merged files are. Tell-tale: a module version going backwards on one branch.

- Merge in the direction you can test first (production into staging), resolve there,
  then fast-forward.
- Audit auto-merged files too: compare blobs per file (`git rev-parse <rev>:<path>`).
- Decisive check: `git rev-parse HEAD^{tree}` versus `origin/<branch>^{tree}`. Identical trees
  mean the merge introduced nothing and the earlier green run still certifies it.
- Production only fast-forwards from staging; enforce it with branch protection.

## 9. Module-set changes auto-install notification bridges

Installing ordinary apps (sales, stock, accounting, payment) auto-installs bridge modules
(`auto_install: True`) such as WhatsApp and SMS connectors, which can ship active templates
whose company-level gates are already open, so customers get messages nobody configured.
After any change to the installed module set:

- List modules installed since the change whose `auto_install` pulled them in.
- Audit company notification toggles and active message templates; switch them off in
  configuration (company settings), not by patching code.
- Recheck company currency and other defaults that a newly loaded chart of accounts or
  localisation may have changed.
