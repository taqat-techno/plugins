# django-plugin

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-beta-yellow.svg)

Reusable **Django / Django REST Framework** engineering toolkit for Claude Code — ORM & model design, migration safety (zero-downtime), views & DRF API patterns, settings/12-factor config, security auditing, testing, and performance. Generic and **adapter-driven**: project layout, settings module, database backend, and test runner are project-supplied inputs, not assumptions.

The plugin is opinionated about the things that bite Django projects in production — N+1 queries, unsafe migrations against live tables, `DEBUG=True` and committed secrets, mass-assignment, and untested query counts — and stays out of your way otherwise.

## Skills

Auto-activating from natural-language symptoms (no command needed). None are user-invocable; they fire when their domain comes up.

| Skill | Activates when… |
|-------|-----------------|
| `django-orm-models` | Designing/editing a model, writing or reviewing ORM queries, diagnosing slow/duplicated queries, choosing `select_related` vs `prefetch_related`, or placing a transaction boundary. Owns the N+1 rule, DB-level constraints, bulk ops, and locking/`on_commit`. |
| `django-migrations` | Running `makemigrations`/`migrate`, reviewing a migration, or planning a schema change against live data. Owns the review gate, reversibility, schema-vs-data split, and **expand-contract** sequencing for add/rename/drop/type-change. |
| `django-views-drf` | Writing/reviewing a view, DRF serializer, ViewSet, permission, or pagination — or when an endpoint over-fetches, leaks/over-accepts fields, or mis-validates. Owns view-style choice, serializer field discipline, object-level authz, and default-deny pagination. |
| `django-settings-config` | Editing a settings module, adding config, wiring an env var/`.env`, or standing up an environment. Owns the base/dev/prod split, env-driven config, secret handling, and per-environment correctness. |
| `django-security-audit` | Reviewing for security, hardening before release, or responding to a suspected vuln/leaked secret. Renders the **pass/fail security verdict** — settings posture, injection, CSRF, IDOR/mass-assignment, secrets, uploads, dependency CVEs — with a severity rubric. |
| `django-testing` | Writing/reviewing tests, choosing a base class or fixture strategy, or diagnosing flaky/slow/leaky tests. Owns `TestCase` vs `TransactionTestCase`, `factory_boy` over fixtures, mocking at the boundary, and `assertNumQueries` regression coverage. |
| `django-performance` | An endpoint/job is slow (past N+1), adding caching, planning for scale, or batching a backfill. Owns measure-first, DB-side `annotate`/`aggregate`/`F()`, indexing for the real query shape, caching layers + invalidation, `CONN_MAX_AGE`, keyset pagination, and offloading. |

## Commands

| Command | Description |
|---------|-------------|
| `/django-init [--path DIR] [--refresh]` | Read-only orientation — detect version, settings layout, apps, DB, DRF, test runner, migration health; cache adapter inputs to `.django-kit.local.json`. |
| `/django-scaffold [app] [--model Name] [--api]` | Scaffold an app or model surface (model + admin + migration + tests, optional DRF serializer/viewset/urls), applying every skill. Plans the diff and waits for approval. |
| `/django-migrate [app] [--make\|--apply\|--plan\|--check]` | Drive the migration safety gate — make, review the SQL, check reversibility/locking, then apply. Produces an expand-contract plan for risky changes; never blind-applies. |
| `/django-test [app-or-path] [--keepdb] [--parallel] [--cov] [--failed]` | Run the suite with the detected runner and **test** settings, classify failures (regression vs fragile vs env), and surface coverage gaps. |
| `/django-security [app-or-path] [--deploy-only] [--deps] [--fix]` | Run `check --deploy` + a code/settings audit; severity-rated findings with fixes. `--fix` applies only unambiguous low-risk remediations. Defensive only. |

## Agents

Read-only, return findings tables — they report, they don't mutate.

| Agent | Use for |
|-------|---------|
| `migration-safety-analyzer` | Classify unapplied migrations by lock/rewrite risk and reversibility before applying to live data; produce an expand-contract step plan. |
| `django-security-auditor` | Deep defensive security audit of a codebase/app; severity-rated findings with `file:line` and fixes. |
| `orm-query-optimizer` | Hunt N+1s, over-fetch, write loops, Python-side aggregation, and offset-pagination at scale, with confirmation/evidence per finding. |

## Safety Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| Version & layout detection | SessionStart | Detects Django/DRF version and settings layout; injects a context line. Read-only. |
| Risky-edit guard | PreToolUse (Write/Edit) | **ADVISORY** (never blocks) — nudges on hardcoded `DEBUG=True` / secrets / `ALLOWED_HOSTS=['*']` in settings, `RunPython` without a reverse or importing real models in migrations, and `fields = "__all__"` in serializers. Silent on env-driven config. |
| Destructive-command guard | PreToolUse (Bash) | **BLOCKS** `manage.py flush`/`sqlflush`/`reset_db`, `dropdb`, and `DROP DATABASE` unless the override token `ALLOW_DJANGO_DESTRUCTIVE` is present in the same command. **ADVISORY** on `migrate --fake`. |

## Installation

From the TAQAT Techno marketplace:

```
/plugin marketplace add taqat-techno/plugins
/plugin install django@taqat-techno-plugins
```

## Usage

Start by orienting in a project so the other commands have their adapter inputs:

```
/django-init
```

Then the skills activate automatically as you work (review a queryset → `django-orm-models`; touch a migration → `django-migrations`; edit settings → `django-settings-config`). Use the commands for explicit workflows and the agents for read-only sweeps:

```
/django-migrate --check
/django-security --deploy-only
@orm-query-optimizer audit the orders app
```

## Requirements

- A Django project (a `manage.py` at the root). DRF is optional — API features activate only when `rest_framework` is present.
- Python 3 available for the hooks (stdlib only; no third-party deps).
- For runnable checks (`check --deploy`, `makemigrations --check`, the test suite), a working project environment.

## Limitations

- The plugin **does not run `migrate` or destructive commands for you blindly** — that's by design.
- Security review is **defensive**: it describes vulnerabilities and fixes, never working exploits.
- `.django-kit.local.json` is a local cache — add it to `.gitignore`.
- Skill rules are framework-level; project-specific conventions (base models, error envelopes, auth scheme) are adapter inputs you supply.

## Development & testing

The plugin ships a pytest suite under [`tests/`](./tests/) covering plugin structure (file existence, valid `plugin.json` / `hooks.json`, marketplace registration, skill/command/agent front-matter) and the behavior of all three hooks (block/allow/advisory paths, override token, fail-open on bad input):

```
pytest django-plugin/tests/ -q
```

Structural validation (no pytest required):

```
python validate_plugin.py django-plugin
```

## License

MIT License — see [`LICENSE`](./LICENSE).

## Credits

Built by **TAQAT Techno**. Part of the [taqat-techno/plugins](https://github.com/taqat-techno/plugins) marketplace.
