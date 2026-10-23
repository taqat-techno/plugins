# odoo

![Version](https://img.shields.io/badge/version-3.0.2-blue.svg)

## What it does

An Odoo development toolkit for Claude Code, covering Odoo 14-19: module upgrades, code
review and technical debt, website themes and SCSS, OWL front-ends, testing, security
audits, translations (with strong Arabic/RTL support), QWeb reports and email templates,
Docker stacks, local server lifecycle, spreadsheet dashboards, and a bundled MCP server
that queries a running Odoo instance under a read/write safety gate.

It is for Odoo integrators and module developers working on Community or Enterprise,
self-hosted or in Docker.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install odoo@taqat-techno-plugins
```

Restart Claude Code (or run `/plugins`) if the plugin does not appear.

## Requirements

| Requirement | Needed for | How to check |
|---|---|---|
| Python 3.10+ as `python3`, `python` or `py -3` | hooks, scripts, MCP server (all stdlib) | `python3 --version` (or `python --version`, `py -3 --version`) |
| A POSIX shell (Git Bash on Windows) | the hook launcher | Claude Code on Windows uses Git Bash for hooks; `bash --version` |
| An Odoo source checkout or virtualenv | `/start`, `/stop`, `/init`, `/db`, `/scaffold`, `/test` | `python -m odoo --version` or `./odoo-bin --version` |
| PostgreSQL client tools (`psql`, `pg_dump`, `createdb`, `dropdb`) | `/db` | `psql --version` |
| Docker with Compose v2 | `/docker`, Docker-based stacks | `docker compose version` |
| A reachable Odoo with an API key | the MCP server | `/mcp-setup test` |
| Optional: `psutil` | faster, more reliable process lookup in `/start`, `/stop` | `python -c "import psutil"` |
| Optional: `wkhtmltopdf` (the version your Odoo expects) | PDF reports | `wkhtmltopdf --version` |
| Optional: Node.js + Playwright | `/test e2e` | `npx playwright --version` |
| Optional: a Figma MCP server | `/create-theme --figma` | listed by `/mcp` |

The MCP server starts as `python`. If that name does not resolve on your system, set
`ODOO_MCP_PYTHON` to the interpreter (for example `python3`).

## Commands

Each command runs with no arguments (it detects the module, project or config from the
working directory, or asks).

| Command | Arguments | What it does |
|---|---|---|
| `/odoo:create-theme` | `[theme_name] [project_path] [--figma <url>] [--version=17] [--colors=...] [--font=...]` | Generate a website theme module from Figma or manual specs |
| `/odoo:db` | `<backup\|restore\|create\|drop\|list\|reset-admin\|modules> [options]` | Database backup, restore, create, drop, list, admin password reset |
| `/odoo:docker` | `[init\|compose\|deploy\|build\|up\|down\|logs\|shell\|status\|update] [args...]` | Docker infrastructure and containers for Odoo 14-19 |
| `/odoo:frontend` | none | Frontend environment status and capabilities |
| `/odoo:i18n` | `[extract\|validate\|missing\|export] [args...]` | Extract, validate, find missing and export translations |
| `/odoo:ide` | `[vscode\|pycharm\|all] [--config CONFIG]` | PyCharm and VS Code configuration for Odoo |
| `/odoo:init` | `[--version V] [--project NAME] [--port PORT] [--docker] [--db DB] [--no-venv]` | Create venv, config file and directories; check prerequisites |
| `/odoo:mcp-setup` | `[status\|check\|add\|bind\|local\|migrate\|unlock\|audit\|doctor] [project/instance]` | Connect, check, migrate, unlock and repair the live-instance MCP connections |
| `/odoo:official-skills` | `[install\|update\|status\|remove] [--branch 20.0\|master] [--force]` | Install Odoo's official agent skills (20.0+) into the project; refuses on 14-19 |
| `/odoo:owl` | `[lint\|decide\|doctor\|rules] [module-path]` | Lint OWL code for silent anti-patterns, choose a UI shape, diagnose code that never ran |
| `/odoo:precheck` | `[module-path] [target-version]` | Read-only version-compatibility scan |
| `/odoo:quickfix` | `[module-path]` | Safe mechanical compatibility fixes |
| `/odoo:report` | `[create\|validate\|migrate\|analyze\|preview] [args...]` | Email templates and QWeb reports |
| `/odoo:scaffold` | `[module_name] [project] [--version N]` | New module skeleton with models, views, security and tests |
| `/odoo:security` | `[module] [--severity=...] [--layer=access\|routes\|sudo\|all] [--fix] [--json]` | Module security audit |
| `/odoo:service` | `[start\|stop\|init\|db\|docker\|ide\|scaffold] [args...]` | Server lifecycle overview and router |
| `/odoo:start` | `[CONFIG] [--dev] [--workers N] [--docker]` | Start the Odoo server |
| `/odoo:stop` | `[--port PORT] [--docker] [--all] [--force]` | Stop the server on 8069/8072, graceful first; `--all` asks before stopping every server |
| `/odoo:test` | `[--all \| generate\|data\|run\|coverage\|e2e] [model\|module] [args...]` | Test what changed by default; generate, mock data, run, coverage, E2E |
| `/odoo:upgrade` | `[module-path] [target-version]` | Full upgrade pipeline to a target version; the backup is a zip, never a second installable copy |

## Skills

Skills load on their own when the request matches; each can also be invoked as
`/odoo:<directory>`.

| Skill (directory) | Use it when |
|---|---|
| `docker` | Building, deploying or debugging an Odoo stack on Docker: compose files, nginx, CI image builds, tuning, a container that keeps restarting |
| `frontend-js` | Website JavaScript: publicWidget, Owl on the website, `_t()`, Bootstrap 4 to 5 |
| `i18n` | Extracting, creating, validating, exporting or loading translations; Arabic/RTL layout |
| `i18n-audit` | A filled msgstr still shows the source language, a language 500s after a `.po` edit, or a `.po` diff needs review |
| `mcp` | The question is about what is in the live database: records, stored values, effective access, whether a migration landed |
| `multi-tenancy-isolation` | Designing tenant anchors, record rules, uniqueness, host gates and ACLs for several tenants or brands on one instance |
| `owl-app-structure` | Building a standalone full-page OWL app (POS or kiosk style): layout, bundles, boot, stores, data loading |
| `owl-architecture` | Choosing between a backend view, a client action and a self-rooted OWL app |
| `owl-diagnostics` | An OWL or asset change has no effect and shows no error |
| `owl-extending` | Patching core OWL components, templates, services or registries from an addon |
| `owl-state-data` | Deciding where OWL state lives and how server data reaches it |
| `report` | Email templates and QWeb PDF reports, wkhtmltopdf, RTL and bilingual output |
| `reviewer` | Reviewing or estimating technical debt in Odoo 17/19 code |
| `security` | Auditing access rules, record rules, routes, `sudo()` and SQL in a module |
| `service` | Starting, stopping and setting up a local project; databases; module scaffolds; IDE setup |
| `spreadsheet-dashboards` | Building, restyling or auditing `spreadsheet.dashboard` workbooks |
| `stack-doctor` | A stack that starts but is wrong: orphaned volumes, Postgres that will not boot, upgrades that changed nothing, blank themes, unsafe restarts or DB clones |
| `test` | Planning, writing, reviewing, running or debugging tests, including CI |
| `theme-create` | Creating a new website theme module |
| `theme-design` | Turning a Figma or visual design into Odoo templates |
| `theme-scss` | Theme SCSS variables, palettes, fonts and load-order errors |
| `theme-snippets` | Creating or customizing website snippets |
| `upgrade` | Migrating modules or themes between 14 and 19, and errors that appear after an upgrade |

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `security-auditor` | Read, Glob, Grep, Bash | Read-only security scan of a module; returns a structured report |
| `test-analyzer` | Read, Glob, Grep, Bash | Read-only test-coverage gap analysis |
| `upgrade-analyzer` | Read, Glob, Grep, Bash | Read-only version-compatibility analysis |
| `theme-generator` | Read, Write, Bash, Glob, Grep | Generates a theme module for `/create-theme` |

## MCP server

`.mcp.json` registers one stdio server, `odoo` (`mcp/server.py`, stdlib only). Its tools
appear as `mcp__plugin_odoo_odoo__<tool>`. It acts as the authenticated Odoo user: Odoo's
own access rights and record rules apply to every call, and it has no SQL, shell,
filesystem or module-install path.

Connections live in one file, `~/.odoo-mcp/profiles.json` (one per Windows account). It holds
**projects**: each one lists its folders and its **instances** (local, stage, prod...). The
session's folder picks the project; git worktrees count as their main checkout. Every tool
takes an optional `instance` (`"prod"`, or `"project/instance"`). Every result starts with
`[project/instance · database · access]`.

| Tool | What it does | Gate |
|---|---|---|
| `odoo_status` | This folder's project, its instances and default; version, user and access of the target | read |
| `odoo_session` | `list` the project's instances; `unlock` / `lock` production writes for this session | unlock needs the developer's verbatim yes; never above `access` |
| `odoo_list_models` | List models | read |
| `odoo_inspect_model` | Field metadata (stored, computed, related, groups) | read |
| `odoo_search` | Search and read records | read |
| `odoo_count` | Count records for a domain | read |
| `odoo_read_group` | Grouped aggregates | read |
| `odoo_call` | Call a public model method | methods on the read-only allowlist always pass; any other method is gated like a write (hard-denied models, `full` for `unlink`) |
| `odoo_create` | Create records | access `write`, plus an unlock on prod; hard-denied models refused |
| `odoo_write` | Update records | access `write`, plus an unlock on prod; hard-denied models refused |
| `odoo_unlink` | Delete records | access `full`, plus an unlock on prod |

Gating, in short:

- **Every instance has a `tier`** (`local`, `stage`, `prod`) and an **`access`** (`read`,
  `write`, `full`).
  - A remote instance must state its tier, and `local` requires a loopback URL.
  - `access` is the limit. Local and stage instances work at it.
  - A prod instance stays read-only until `odoo_session action=unlock`, given on the
    developer's verbatim yes. The unlock lasts 30 minutes by default (120 at most), stays in
    memory for this session, and is audited.
- **The file is changed only through `scripts/mcp/odoo_mcp.py`.**
  - Every write is validated, backed up and replaced atomically.
  - A change that widens a remote instance (more access, another host, prod relabelled
    stage) needs the developer's yes and is audited.
  - A hook blocks direct edits.
- **Databases.** `db: "auto"` (local and stage) follows an Odoo.sh rebuild in memory. A fixed
  database, and every production database, is never followed.
- Privilege-escalation and code-execution models (for example `res.users`,
  `ir.config_parameter`, `ir.ui.view`, `ir.cron`) are refused for writes unless the
  instance lists them in `allow_write_models`. The same list covers `website.page`
  (it `_inherits` `ir.ui.view`) and wizards that reach those models (`base.module.upgrade`,
  `res.config.settings`, `change.password.*`). Private methods, install methods, string
  domains and unsafe context keys are refused.
- x2many command tuples nested in create/write values (`[0, 0, vals]`, `[1, id, vals]`,
  `[2, id]`, `[4, id]`, `[6, 0, ids]`, ...) get the same checks at every level: the
  comodel is resolved with `fields_get`, a command reaching a refused model is refused,
  a delete (`[2, id]`, or unlink/clear/set on an existing record's one2many) needs
  access `full`, and commands on a field whose comodel cannot be resolved are refused.
- `access` in the file is the hard limit. Odoo's own access rights still apply, so use an
  API key for a user with only the rights you want Claude to have.

Setup and the full configuration reference: `/odoo:mcp-setup` and
[`mcp/README.md`](mcp/README.md).

## Hooks

All hooks are Python scripts started through a portable launcher (`python3`, then
`python`, then `py -3`); a missing interpreter or script means the hook is skipped. Every
hook fails open: bad input, an exception or its watchdog timeout lets the tool call
proceed.

| Hook | Event / matcher | What it does | Can it block? |
|---|---|---|---|
| `hooks/frontend/session_start.py` | SessionStart (`startup`) | When the workspace holds an Odoo source tree (`odooNN/`), tells Claude the Odoo, Bootstrap and Owl versions. Silent in any other project | No |
| `hooks/upgrade/guard_core_odoo.py` | PreToolUse `Write\|Edit\|MultiEdit` | Refuses edits to core Odoo framework files (patterns in `config/odoo-upgrade.config.json`, overridable per project) and to the MCP connection file `~/.odoo-mcp/profiles.json` and its backups (change it with `scripts/mcp/odoo_mcp.py`) | Yes: denies the write with the reason |
| `hooks/frontend/pre_write_check.py` | PreToolUse `Write\|Edit\|MultiEdit` | Refuses inline executable `<script>` code in an Odoo module's XML; JSON-LD, templates and `src`-only tags pass; XML outside a module passes | Yes: denies the write (`ODOO_INLINE_SCRIPT_CHECK=warn` makes it a note, `off` disables it) |
| `hooks/pre_odoo_volume_guard.py` | PreToolUse `Bash` | On an Odoo stack, asks you before commands that destroy data: `docker compose down -v`, `docker volume rm`/`prune`, `docker system prune --volumes`, `db_manager.py drop`/`reset-admin`/`restore --no-create`, `dropdb`, `psql -c "DROP DATABASE ..."`, `server_manager.py stop --all --yes`, also when run through `sudo -u`, `env`, `timeout`, `nohup`, `xargs`, `eval`, `bash -lc`, `powershell -Command` or inside a container (`docker exec`, `docker compose exec\|run`) | Yes: asks you to approve (`ODOO_DESTRUCTIVE_GUARD=off` disables it) |
| `hooks/pre_odoo_restart_guard.py` | PreToolUse `Bash` | Advisory note on an unbounded `curl --retry-connrefused` readiness poll, a `pkill ... && ... odoo-bin` chain (self-kill, exit 144), and a `psql ... TEMPLATE` clone (no filestore) | No: advisory only |

The guards match the command that will run, not text inside quotes, comments, `echo` or
`grep` patterns.

## Configuration

This plugin has no `userConfig` options.

| Setting | Where | Effect |
|---|---|---|
| `ODOO_MCP_PYTHON` | environment | Interpreter for the MCP server (default `python`) |
| `ODOO_MCP_HOME` | environment | Moves the MCP store from `~/.odoo-mcp/` (tests) |
| `~/.odoo-mcp/profiles.json` | your file, changed with `scripts/mcp/odoo_mcp.py` | Every MCP project, instance, key and access level (example: `config/odoo-mcp.profiles.json.example`) |
| `<project>/odoo-upgrade.config.json` | your file | Overrides the core-file patterns used by the core-file guard hook |
| `<project>/.claude/odoo-service.local.md` | your file (git-ignore it) | Author, website, license and DB defaults for `/scaffold` and `/init` |
| `config/odoo-docker.local.md.example` | example | Per-project Docker defaults for `/docker` |
| `ODOO_INLINE_SCRIPT_CHECK` | environment, `warn` or `off` | Relaxes the inline-script hook |
| `ODOO_DESTRUCTIVE_GUARD` | environment, `off` | Disables the destructive-command hook |
| `ODOO_UPGRADE_BACKUP_DIR` | environment | Where `/upgrade` writes its zip backups (default `.odoo-upgrade-backups/` beside the module) |
| `GITHUB_TOKEN` or `GH_TOKEN` | environment, optional | Read-only token for `/official-skills`, sent only to `api.github.com` to avoid rate limits |
| `ODOO_ADMIN_NEW_PASSWORD` | environment, optional | New password for `/db reset-admin` (or pipe it with `--password-stdin`) |
| `FULL_SUITE=1` | prefix on a test command | Allows a test run over every installed module |

Set environment variables before starting Claude Code.

## Platform support

| Platform | Status |
|---|---|
| Linux | Supported. If only `python3` exists, set `ODOO_MCP_PYTHON=python3` for the MCP server |
| macOS | Supported. Same note on `python3` |
| Windows | Supported. Hooks need Git Bash (Claude Code's default hook shell on Windows). Process lookup in `/start` and `/stop` works best with `psutil`; without it the scripts fall back to `netstat` and PowerShell CIM |
| WSL | Supported. A Windows-side process can hold a port that WSL wants; `stack-doctor` covers the symptom |

The workspace layout `odooNN/` + `projects/<project>/` + `conf/<project>.conf` is the
default that `/init`, `/scaffold`, `/ide`, `/create-theme` and the SessionStart hook
expect. Other layouts (OCA checkouts, pip-installed Odoo, Doodba) work, but you may have
to give paths explicitly.

## Data & privacy

Stored on your machine:

- **`~/.odoo-mcp/profiles.json`**: every MCP project and instance, meaning URL, database,
  user name and API key.
  - Keys are in plain text unless written as a `${VAR}` reference. The file lives in your
    user profile; on Linux/macOS it is written `0600` in a `0700` folder.
  - Local instances added by `odoo_mcp.py local` carry an expiring key and are pruned
    automatically.
- **`~/.odoo-mcp/backups/`**: the last 10 versions of `profiles.json`, plus `profiles-v1.json`
  and copies of the project files `migrate` changed. They hold the same secrets; keep them
  private.
- **`~/.odoo-mcp/audit.log`** (rotated at 1 MB to `audit.log.1`): one JSON line per event.
  - It records production unlocks and locks with the approval text you gave (first 200
    characters), access widenings with their approval, config changes, migrations, and for
    non-local writes the operation, model and record count.
  - It never records record values or credentials.
- `.odoo-upgrade-backups/` (or `ODOO_UPGRADE_BACKUP_DIR`): zip backups made by `/upgrade`.
- `<project>/.claude/skills/odoo-*`: Odoo's official skills, if you install them, each
  with a `.odoo-official.json` marker recording branch, commit and licence.
- Database dumps you create with `/db backup`, wherever you point them.

What leaves the machine:

- MCP calls go only to the URL of the instance they name (or the project default),
  authenticated with that instance's API key.
  Record data returned by Odoo enters the Claude conversation.
- `/official-skills` downloads from GitHub (`api.github.com`, `raw.githubusercontent.com`,
  repository `odoo/odoo`), sending `GITHUB_TOKEN` only to `api.github.com` when set.
- `/create-theme --figma` reads the design through your Figma MCP server, under that
  server's own terms.
- Docker commands pull images from the registries your compose files name.

Nothing is sent to the plugin authors. On screen: `/db reset-admin` takes the new password from stdin or
`ODOO_ADMIN_NEW_PASSWORD` and never prints it; MCP errors are redacted of credentials.

## Limitations

- Upgrade transforms target 14 to 19; 20.0 rules come from Odoo's official skills through
  `/official-skills`, which refuses to install them on 14-19.
- The reviewer skill is written for Odoo 17 and 19; it is useful on 18 but not tuned for it.
- Odoo.sh is mentioned but not tooled; service commands assume a self-hosted or Docker
  stack.
- Spreadsheet dashboards are an Enterprise feature; that skill assumes Odoo 16+.
- The production unlock and `--approved-by` record the developer's answer but cannot prove a
  human gave it. `access` in `profiles.json` is the real limit, and a process that runs as
  you could still change the file through a shell. Keep production at `access: read` unless
  you need writes.
- A session can name another project's instance (`"project/instance"`), which lets it read
  that project's data, including production. Bind folders and name instances deliberately.
- Trigger evals exist for every skill (`evals/`) but have not yet been run with a recorded
  baseline delta.

## License

MIT (`LICENSE`). Component provenance, including the report component's relicensing from
LGPL-3.0, is in [`LICENSES.md`](LICENSES.md). Odoo is a trademark of Odoo S.A.; this plugin
bundles no Odoo source code. Odoo's official agent skills installed by `/official-skills`
are LGPL-3.0 and are fetched, not redistributed.
