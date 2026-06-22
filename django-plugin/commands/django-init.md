---
description: Detect and report a Django project's layout, version, settings structure, database, DRF presence, and test runner — a read-only orientation pass that caches adapter inputs for the other Django commands.
argument-hint: "[--path DIR] [--refresh]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash
---

# /django-init — Orient in a Django project

You are performing a **read-only** orientation of a Django project. Detect how it is built, report it, and cache the adapter inputs the other Django commands and skills rely on. Create no source files; the only thing you may write is the adapter cache.

## Bare-invocation behavior (no args)

Operate on the current working directory. If `--path DIR` is given, use that as the project root.

## Step 0 — Read the adapter cache

Look for `.django-kit.local.json` in the project root.

- If present and `--refresh` was not passed, load it and report a short summary; offer to re-detect with `--refresh`.
- Otherwise, run detection below and (re)write it.

## Step 1 — Detect the project

Find, without modifying anything:

1. **`manage.py`** location and the invocation prefix the project uses (`python manage.py`, `poetry run ./manage.py`, `uv run manage.py`, container exec). If a virtualenv/poetry/uv/pipenv is detected, record the right prefix.
2. **Django version** — from the installed package (`python -c "import django; print(django.get_version())"` if the env is available), else from `requirements*.txt` / `pyproject.toml` / `Pipfile` / lockfiles.
3. **Settings structure** — single `settings.py` vs a `settings/` package (`base/dev/prod/test`). Find the value(s) of `DJANGO_SETTINGS_MODULE` referenced in `manage.py`, `wsgi.py`, `asgi.py`, and any test config. Flag mismatches.
4. **Apps** — local apps in `INSTALLED_APPS` and their directories; distinguish first-party from third-party.
5. **Database backend** — from `DATABASES`/`DATABASE_URL` (Postgres/MySQL/SQLite/other). Do not print credentials.
6. **DRF** — is `rest_framework` installed/in `INSTALLED_APPS`? Note version if so. Check for `django-filter`, a default pagination/permission/throttle config.
7. **Test runner** — `pytest` + `pytest-django` (`pytest.ini`/`pyproject`/`setup.cfg` with `DJANGO_SETTINGS_MODULE`) vs `manage.py test`. Note `factory_boy`/`model_bakery`, `coverage`.
8. **Async / tasks** — Celery/RQ/Dramatiq config, ASGI server, channels.
9. **Migrations health** — run `manage.py makemigrations --check --dry-run` if the env is runnable; report whether models and migrations are in sync (read-only check, makes no files).

## Step 2 — Write the adapter cache

Write `.django-kit.local.json` (gitignored — tell the user to add it if missing) with the detected, non-secret facts:

```json
{
  "managePrefix": "python manage.py",
  "djangoVersion": "5.x",
  "settingsLayout": "package",
  "settingsModules": { "default": "config.settings.dev", "prod": "config.settings.prod", "test": "config.settings.test" },
  "localApps": ["accounts", "orders"],
  "dbBackend": "postgresql",
  "drf": { "present": true, "version": "3.x", "djangoFilter": true },
  "testRunner": "pytest-django",
  "tasks": "celery"
}
```

Never write secrets, passwords, or `DATABASE_URL` values into this file.

## Step 3 — Report

Print a concise orientation:

```
DJANGO PROJECT
  Manage:        python manage.py        (poetry env)
  Django:        5.x
  Settings:      package  →  config.settings.{base,dev,prod,test}
                 ⚠ wsgi.py uses config.settings.prod but tests use config.settings.dev
  Apps (local):  accounts, orders, billing
  Database:      postgresql
  DRF:           3.x  (+ django-filter; default perm: IsAuthenticated; pagination: PageNumber/20)
  Tests:         pytest-django  (+ factory_boy, coverage)
  Tasks:         celery
  Migrations:    ✅ in sync     (or ⚠ models changed without a migration in: orders)

Next: /django-migrate · /django-test · /django-security · /django-scaffold <app>
```

Surface every mismatch or risk you found (settings-module divergence, out-of-sync migrations, `DEBUG`/`SECRET_KEY` smells) as a flagged line — but fix nothing here. Hand security concerns to `/django-security`.
