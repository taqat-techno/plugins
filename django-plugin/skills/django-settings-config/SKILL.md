---
name: django-settings-config
description: Django settings architecture and 12-factor configuration — splitting base/dev/prod settings, driving config from the environment, keeping secrets out of source, and the per-environment correctness of DEBUG, ALLOWED_HOSTS, DATABASES, CACHES, static/media, and logging. Activates when creating or editing a settings module, adding a new configuration value, wiring an environment variable or .env, setting up a new environment, or reviewing settings for environment-correctness. Defers the security verdict on settings to django-security-audit.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - settings layout rule (base + per-env overrides; one settings module per environment)
  - environment-driven config rule (read config from env; typed/validated; sane defaults only for dev)
  - secret-handling rule (secrets never in source/VCS; SECRET_KEY/DB creds/API keys from env or a secret store)
  - per-environment setting correctness (DEBUG, ALLOWED_HOSTS, DATABASES, CACHES, EMAIL, LOGGING, static/media)
  - DJANGO_SETTINGS_MODULE selection rule across manage.py / wsgi / asgi / tests
defers_to:
  - django-security-audit (the pass/fail security verdict on a settings file)
  - django-performance (cache backend tuning, connection pooling/CONN_MAX_AGE values)
  - django-migrations (nothing settings-side, but DB routing config interacts)
  - project secret-store choice (Vault / SSM / Doppler / .env — adapter input)
user_invocable: false
---

# django-settings-config

## Purpose

Settings are where one file silently decides whether the app is debuggable in dev and safe in prod. The recurring failures are structural: a single `settings.py` with `if DEBUG:` branches, secrets committed to the repo, and config that can't change per environment without editing code. This skill owns the layout, the environment-driven config discipline, and the per-environment correctness of the high-stakes settings.

## When to use

Activate when:

- Creating or editing a settings module, or adding a new configuration value.
- Wiring an environment variable, `.env`, or secret into the app.
- Standing up a new environment (staging, CI, prod) or its config.
- Reviewing settings for environment-correctness (is this safe in prod? does dev still work?).

Defer the explicit **security pass/fail** on a settings file to `django-security-audit`; this skill is about *structure and config correctness*, that one renders the verdict.

## Inputs (adapter)

1. **Settings layout already in use** — single file, a `settings/` package (`base.py` + `dev.py`/`prod.py`), or a library like `django-environ` / `pydantic-settings` / `python-decouple`. Match it; don't impose a new one unasked.
2. **Secret store** — `.env` (local), environment variables (containers), or a managed store (Vault, AWS SSM, Doppler). Determines *where* secrets come from.
3. **Environments** — which exist (dev / CI / staging / prod) and how `DJANGO_SETTINGS_MODULE` is selected for each.

## Settings layout rule

Prefer a settings *package* over one file:

```
project/settings/
    __init__.py
    base.py        # everything common; no secrets, no env-specific values
    dev.py         # from .base import *; DEBUG=True; local conveniences
    prod.py        # from .base import *; DEBUG=False; strict; reads secrets from env
    test.py        # from .base import *; fast hashers, in-memory/locmem where safe
```

- `base.py` holds shared structure and reads required config from the environment. It should not contain real secrets or `DEBUG=True`.
- Per-env modules import base and override. Avoid sprinkling `if DEBUG:` across one giant file — the environment, not a runtime branch, should determine behavior.
- Select the module via `DJANGO_SETTINGS_MODULE` consistently across **`manage.py`, `wsgi.py`, `asgi.py`, and the test runner** — a mismatch (e.g. tests on dev settings, wsgi on prod) is a classic "works locally, breaks in prod" source.

## Environment-driven config rule

- Read configuration from the environment, with **types and validation**: `env.bool("DEBUG", default=False)`, `env.int(...)`, `env.db()` (URL → `DATABASES`), `env.list("ALLOWED_HOSTS")`. A bare `os.environ["X"]` everywhere is untyped and crashes late.
- **Defaults are for dev only and must be safe.** `DEBUG` defaults to `False`. `SECRET_KEY` has **no** insecure default in prod — missing means fail fast at startup, not fall back to a known key.
- Fail loudly on missing required config at boot (a missing `SECRET_KEY`/`DATABASE_URL` should raise immediately), not at the first request that needs it.

## Secret-handling rule

- **No secret ever in source or VCS.** `SECRET_KEY`, database passwords, API keys, signing keys → environment or secret store. `.env` files are gitignored; commit a `.env.example` with **placeholder** values and the variable names only.
- Rotating `SECRET_KEY` invalidates sessions, password-reset tokens, and signed cookies — note that when advising a rotation. Use `SECRET_KEY_FALLBACKS` to rotate without instant logout where supported.
- If a secret was ever committed, rotating it is mandatory — removing it from the latest commit does not remove it from history. (Hand the incident response to `django-security-audit`.)

## Per-environment correctness

| Setting | Dev | Prod |
|---|---|---|
| `DEBUG` | `True` | **`False`** (never True in prod — leaks tracebacks/settings) |
| `ALLOWED_HOSTS` | `["*"]` or localhost | explicit host list (empty + `DEBUG=False` → every request 400s) |
| `SECRET_KEY` | dev value via env ok | from secret store; no fallback |
| `DATABASES` | local/SQLite ok | real DB from `DATABASE_URL`; set `CONN_MAX_AGE` deliberately |
| `CACHES` | `locmem` fine | real backend (Redis/Memcached); `locmem` is per-process, not shared |
| `EMAIL_BACKEND` | console backend | real SMTP/provider |
| `STATIC`/`MEDIA` | `runserver` serves them | `collectstatic` + a real server/CDN; never serve media via Django in prod |
| `LOGGING` | verbose to console | structured, leveled, no secrets in logs, errors to a sink |
| Security headers | relaxed | `SECURE_SSL_REDIRECT`, HSTS, secure cookies (→ `django-security-audit` owns the checklist) |

## Static / media note

`runserver` serving static files is a dev-only convenience (`DEBUG=True`). In prod, run `collectstatic` and serve via WhiteNoise/CDN/web server. Never route user-uploaded **media** through Django's static machinery — it's a different concern with different access-control needs.

## Red flags

- A single `settings.py` with `DEBUG = True` hardcoded, or `DEBUG` not driven by env.
- A real `SECRET_KEY`, password, or API key literal in any settings file.
- `SECRET_KEY` with an insecure fallback default that prod could silently use.
- `ALLOWED_HOSTS = ["*"]` in a prod-intended module.
- `.env` not in `.gitignore`, or no `.env.example` to document required vars.
- `DJANGO_SETTINGS_MODULE` differing between `wsgi`/`asgi`, `manage.py`, and tests.
- `locmem` cache in prod, or a cache assumed shared that is per-process.

## Report format

When reviewing settings, produce a **per-setting × per-environment** table flagging each value that's wrong/unsafe for its environment, and a **secrets inventory**: every secret-shaped value, where it currently comes from, and whether it's exposed in source. Hand any confirmed exposure to `django-security-audit`.
