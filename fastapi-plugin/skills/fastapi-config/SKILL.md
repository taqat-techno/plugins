---
name: fastapi-config
description: FastAPI settings architecture and 12-factor configuration with pydantic-settings — a typed BaseSettings object, driving config from the environment, keeping secrets out of source, per-environment correctness (debug, docs exposure, CORS, database URL, secret key), and injecting settings via a cached dependency. Activates when creating or editing a settings module, adding a config value, wiring an environment variable or .env, standing up an environment, or reviewing config for environment-correctness. Defers the security verdict on settings to fastapi-security-audit.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - settings-object rule (one typed pydantic-settings BaseSettings; no scattered os.getenv)
  - environment-driven config rule (read from env; typed/validated; safe dev-only defaults)
  - secret-handling rule (secrets never in source/VCS; SECRET_KEY/DB creds/API keys from env or a secret store)
  - per-environment correctness (debug, /docs & /openapi.json exposure, CORS, DATABASE_URL, logging)
  - settings-injection rule (provide settings via a cached dependency / lru_cache, not import-time globals)
defers_to:
  - fastapi-security-audit (the pass/fail security verdict on a settings/config file)
  - fastapi-async-performance (connection-pool sizing, cache-backend tuning values)
  - fastapi-database (the DATABASE_URL consumer / engine construction)
  - project secret-store choice (Vault / SSM / Doppler / .env — adapter input)
user_invocable: false
---

# fastapi-config

## Purpose

Config is where one object silently decides whether the app is debuggable in dev and safe in prod. The recurring failures are structural: `os.getenv` scattered across modules with no types or validation, secrets committed to the repo, `/docs` and `/openapi.json` exposed in production, CORS wide open, and config that can't change per environment without editing code. This skill owns the typed settings object, the environment-driven discipline, and the per-environment correctness of the high-stakes values.

## When to use

Activate when:

- Creating or editing a settings module, or adding a new configuration value.
- Wiring an environment variable, `.env`, or secret into the app.
- Standing up a new environment (staging, CI, prod) or its config.
- Reviewing config for environment-correctness (is this safe in prod? does dev still work?).

Defer the explicit **security pass/fail** to `fastapi-security-audit`; this skill is about *structure and config correctness*, that one renders the verdict.

## Inputs (adapter)

1. **Settings library already in use** — `pydantic-settings` (`BaseSettings`, the standard for FastAPI), `dynaconf`, `python-decouple`, or bare `os.environ`. Match it; this skill assumes pydantic-settings unless told otherwise.
2. **Secret store** — `.env` (local), environment variables (containers), or a managed store (Vault, AWS SSM, Doppler). Determines *where* secrets come from.
3. **Environments** — which exist (dev / CI / staging / prod) and how they're selected (an `ENVIRONMENT`/`APP_ENV` variable, separate `.env` files).

## Settings-object rule

One typed `BaseSettings` object, read once, injected where needed:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "dev"
    debug: bool = False                       # safe default; True only via env in dev
    database_url: str                         # no default -> required; fails fast at boot
    secret_key: str                           # no default -> required in every env
    cors_origins: list[str] = []
    docs_enabled: bool = False                # gate /docs in prod

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- All config lives on **one typed object**, not `os.getenv("X")` sprinkled across modules (untyped, unvalidated, crashes late).
- Fields are **typed** — `bool`, `int`, `list[str]`, `PostgresDsn`, `AnyHttpUrl` — so pydantic-settings parses and validates env values at construction.
- **Required values have no default** — a missing `secret_key`/`database_url` raises at startup, not at the first request that needs it.

## Environment-driven config rule

- Read configuration from the environment with **types and validation** (pydantic-settings does this from the field annotations). A bare `os.environ["X"]` everywhere is untyped and fails late.
- **Defaults are for dev only and must be safe.** `debug` defaults to `False`. `docs_enabled` defaults to `False`. Secrets have **no** insecure default — missing means fail fast at boot, not fall back to a known value.
- Fail loudly on missing required config at boot. Construct `Settings()` at startup (via the cached dependency) so a misconfiguration crashes immediately and visibly.

## Secret-handling rule

- **No secret ever in source or VCS.** `SECRET_KEY` (JWT signing), database passwords, API keys → environment or secret store, read into `BaseSettings` fields. `.env` files are gitignored; commit a `.env.example` with **placeholder** values and the variable names only.
- Use `pydantic.SecretStr` for secret fields so they don't render in logs/`repr` accidentally.
- Rotating the JWT `SECRET_KEY` invalidates every issued token (forces re-login) — note that when advising a rotation.
- If a secret was ever committed, rotating it is mandatory — removing it from the latest commit does not remove it from history. (Hand the incident to `fastapi-security-audit`.)

## Per-environment correctness

| Setting | Dev | Prod |
|---|---|---|
| `debug` | `True` ok | **`False`** (don't leak tracebacks/internals) |
| `/docs`, `/redoc`, `/openapi.json` | exposed | gate behind auth or disable (`docs_url=None`) if the API is private |
| `SECRET_KEY` (JWT) | dev value via env ok | from secret store; no fallback default |
| `DATABASE_URL` | local/SQLite ok | real DB from env; pool sized deliberately (→ `fastapi-async-performance`) |
| CORS `allow_origins` | localhost / permissive ok | **explicit origin list**; never `["*"]` with credentials (→ `fastapi-security-audit`) |
| `LOGGING` | verbose to console | structured, leveled, **no secrets in logs** |
| `reload` (uvicorn) | `--reload` ok | never `--reload`; run under a process manager / gunicorn workers |

## Settings injection

- Provide settings via a **cached dependency** (`@lru_cache` on `get_settings`, injected with `Depends(get_settings)`) rather than a module-level global evaluated at import time. The cache means one instance; the dependency means it's overridable in tests (→ `fastapi-testing`).
- Don't read `os.environ` directly inside routes/services — inject the settings object so the source of truth is one place and tests can override it.

## Red flags

- `os.getenv(...)` scattered across modules instead of one typed `BaseSettings`.
- A real `SECRET_KEY`, DB password, or API key literal in any config file.
- A secret field with an insecure default that prod could silently fall back to.
- `debug=True` hardcoded, or `/docs`/`/openapi.json` exposed on a private prod API with no gate.
- CORS `allow_origins=["*"]` (especially with `allow_credentials=True`) in a prod config.
- `.env` not gitignored, or no `.env.example` documenting required vars.
- Settings constructed as an import-time global (not a cached dependency) — hard to override in tests, may read env before it's set.
- `uvicorn --reload` in a production start command.

## Report format

When reviewing config, produce a **per-setting × per-environment** table flagging each value wrong/unsafe for its environment, and a **secrets inventory**: every secret-shaped value, where it currently comes from, and whether it's exposed in source. Hand any confirmed exposure to `fastapi-security-audit`.
