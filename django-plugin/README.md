# django-plugin

![Version](https://img.shields.io/badge/version-0.5.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-beta-yellow.svg)

## What it does

A Django / Django REST Framework engineering toolkit for Claude Code: ORM and model design, migration safety (zero-downtime expand-contract), views and DRF API patterns, settings and 12-factor config, security auditing, testing and performance. It is adapter-driven: the project layout, settings modules, database backend and test runner are detected per project, not assumed.

It is for developers working in any Django 4.2 LTS or newer codebase, with or without DRF. It is opinionated about what breaks Django projects in production (N+1 queries, unsafe migrations on live tables, `DEBUG=True` and committed secrets, mass-assignment, untested query counts) and stays quiet otherwise.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install django@taqat-techno-plugins
```

## Requirements

| Requirement | Needed for | Check |
|---|---|---|
| Python 3.8+ as `python3`, `python` or `py -3` | the three hooks (stdlib only) | `python3 --version` |
| A POSIX shell (`sh`; Git Bash on Windows) | the hook launcher | `sh -c 'echo ok'` |
| A Django project (`manage.py`) | the hooks fire only in one; commands work on it | `ls manage.py` |
| A runnable project environment | `check --deploy`, `makemigrations --check`, the test suite | `python manage.py check` |
| Optional: `pip-audit` or `safety` | `/django:security --deps` | `pip-audit --version` |
| Optional: DRF | API features in `/django:scaffold` | `pip show djangorestframework` |

## Commands

| Command | What it does | Bare invocation |
|---|---|---|
| `/django:migrate [app] [--make\|--apply\|--plan\|--check]` | Migration safety gate: make, read every migration, `sqlmigrate`, check reversibility and locking, confirm the target database, then apply. Risky changes get an expand-contract plan instead. | `--check` (`makemigrations --check --dry-run`) |
| `/django:scaffold [app] [--model Name] [--api\|--no-api]` | Scaffold an app or model surface (model, admin, migration, tests, optional DRF serializer/viewset/urls). Plans the file diff and waits for approval. | asks for the model |
| `/django:test [app-or-path\|--all] [--keepdb] [--parallel] [--cov] [--failed]` | Runs the tests for what changed (T1, then T2), with the detected runner and test settings, and classifies failures. | tests the changed files |
| `/django:security [app-or-path] [--deploy-only] [--deps] [--fix]` | `check --deploy` plus a code and settings audit; severity-rated findings with fixes. `--fix` applies only unambiguous low-risk fixes. Defensive only. | full audit, report only |

The old names `/django:django-migrate`, `/django:django-scaffold`, `/django:django-test` and `/django:django-security` still work as deprecated aliases and will be removed in 0.6.0.

## Skills

Model-invoked from what you are doing; none is a slash command.

| Skill | Use when |
|---|---|
| `django-orm-models` | Designing a model, writing or reviewing ORM queries, N+1 / over-fetch, `select_related` vs `prefetch_related`, constraints, transactions, silent data drift (group-by counts inflated by `Meta.ordering`, partial `UniqueConstraint`). |
| `django-migrations` | `makemigrations` / `migrate`, reviewing a migration, data migrations, schema changes against live data, conflicts and drift. |
| `django-views-drf` | Views, DRF serializers, ViewSets, permissions, pagination, filtering, throttling, error shaping. |
| `django-settings-config` | Settings modules, env-driven config, secrets, per-environment `DEBUG` / `ALLOWED_HOSTS` / `DATABASES`. |
| `django-security-audit` | Security review, release hardening, suspected vulnerability or leaked secret. Renders the pass/fail verdict. |
| `django-testing` | Writing tests, base-class and fixture choice, test DB, mocking, `assertNumQueries`, scoped runs, flaky tests. |
| `django-performance` | Slow endpoints beyond N+1, caching and invalidation, pagination at scale, `CONN_MAX_AGE`, offloading, batched backfills. |

## Agents

Read-only analyzers that return findings tables. Each has `tools: Read, Glob, Grep, Bash`. Bash is there only for read-only inspection (`showmigrations`, `sqlmigrate`, `makemigrations --check --dry-run`, `check --deploy`, `pip-audit`); the agents are instructed never to write, and the destructive-command guard still applies to anything they run.

| Agent | Use for |
|---|---|
| `migration-safety-analyzer` | Classify unapplied migrations by lock/rewrite risk and reversibility before they reach live data; produce an expand-contract plan. |
| `django-security-auditor` | Deep defensive audit of a codebase or app; severity-rated findings with `file:line` and fixes. |
| `orm-query-optimizer` | Hunt N+1s, over-fetch, write loops, Python-side aggregation and offset pagination at scale, with evidence per finding. |

## Hooks

| Hook | Event (matcher) | What it does | Can block? |
|---|---|---|---|
| `session_start.py` | SessionStart (`startup`) | Finds `manage.py` in the session directory or up to two levels below it, then adds one context line: Django version, DRF, settings layout. Prints nothing outside a Django project. | No |
| `pre_write_guard.py` | PreToolUse (`Write\|Edit\|MultiEdit`) | Advisory: hardcoded `DEBUG = True` or `ALLOWED_HOSTS = ['*']` in prod-bound settings (not `test_settings.py`, `settings/dev.py`, `settings/local.py`), hardcoded secret literals, `RunPython` without a reverse, data migrations importing real models, `fields = "__all__"` in serializers. | No |
| `pre_bash_guard.py` | PreToolUse (`Bash`) | In a Django project only, asks you to confirm `flush`, `sqlflush`, `reset_db` (also via `call_command` in `manage.py shell`), `migrate <app> zero`, `dropdb`, `mysqladmin drop`, and `DROP DATABASE`, `DROP SCHEMA ... CASCADE` or `TRUNCATE` sent to a SQL client or `dbshell` (argument, pipe, heredoc or `<<<` here-string). It sees through `sudo`, `env`, `nice`, `nohup`, `timeout`, `watch`, `eval`, `poetry`/`uv`/`pipenv`/`pdm run` (with their options), `docker`/`podman`/`docker compose` `run` and `exec`, `kubectl exec --`, `bash`/`sh`/`zsh -c` (also `-lc`, `-ec`), `ssh host '...'` and `heroku run`, and applies shell quote removal first (`fl''ush` is `flush`). It parses the command, so quoted text, comments, `echo`, `grep` patterns, commit messages and `--help` never trigger it. Advisory on `migrate --fake`. | Asks you (`permissionDecision: "ask"`); it never denies |

A Django project, for the bash guard, is a `manage.py` found walking up from the working directory (or a `cd` target in the command), or up to two levels below `CLAUDE_PROJECT_DIR`. Hooks fail open: bad input, a missing Python or an internal error lets the tool call through.

## Configuration

| Setting | Where | Effect |
|---|---|---|
| `destructive_guard` (boolean, default `true`) | plugin option, set in `/config` or when enabling the plugin | `false` turns off the bash guard's confirmation prompts. Advisories stay on. |
| `ALLOW_DJANGO_DESTRUCTIVE=1` | environment of the Claude Code process, set before launching it | Same as `destructive_guard: false`. Kept for users of the 0.4 token. Writing the name inside a command no longer does anything. |
| `.claude/django.local.json` | project root, created by `/django:scaffold` only if you agree | Caches detected non-secret inputs (`managePrefix`, `localApps`, `settingsModules`, `dbBackend`, `drf`, `testRunner`, `baseModel`). The schema is in `commands/scaffold.md`. The legacy `.django-kit.local.json` is still read. Add either to `.gitignore`. |

## Platform support

| Platform | Status |
|---|---|
| Linux, macOS | Supported. |
| Windows with Git Bash | Supported. The launcher tries `python3`, `python`, then `py -3`, and skips the Microsoft Store `python3` stub. |
| Windows without Git Bash | Claude Code runs shell-form hooks in PowerShell, where the launcher does not parse; the hooks fail open, so the guard is inactive. Skills, commands and agents work. |
| WSL | Supported. |
| Django | Content targets Django 4.2 LTS and newer; DRF is optional. |

## Data & privacy

- The hooks read the hook payload (the command or the file content being written) and, for project detection, file names and dependency files in your project. They make no network calls and store nothing.
- `.claude/django.local.json` is written only with your consent and holds non-secret layout data. Commands never write a secret, password or database URL into it.
- `/django:migrate --apply` prints the target database's engine, host, port and name, never its password.
- `/django:security --deps` runs `pip-audit` or `safety` if you have them; those tools query their vulnerability databases over the network.
- Nothing is sent anywhere by the plugin itself.

## Limitations

- The bash guard sees only the command text. It cannot see SQL inside a file passed with `psql -f`, a script, an alias, a shell variable (`C=flush; ... $C`) or arguments fed through `xargs`, and it does not see `call_command` run from `python -c` or ORM deletes in your own code.
- The write guard sees only the new text of an Edit, so a `RunPython` whose reverse sits outside the hunk can be misjudged.
- The plugin never runs `migrate` or a destructive command on its own; the commands stop for review by design.
- Security review is defensive: it describes vulnerabilities and fixes, never working exploits.
- Optional companions: if `agent-safety-guards` is installed, its `test-scope` skill and hook add stricter test-tier rules; `/django:test` works the same without it.

Development: `python -m pytest -q -p no:cacheprovider` from this directory runs the offline suite; `python validate_plugin.py django-plugin` from the repository root checks the structure.

## License

MIT, see [`LICENSE`](./LICENSE). No third-party code is bundled.
