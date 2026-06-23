---
description: Run a FastAPI security audit — a code/config review for auth & JWT handling, authorization bypass (missing dependency, IDOR, mass-assignment), injection, CORS misconfiguration, secret exposure, docs/debug exposure in prod, file-upload safety, and dependency CVEs. Produces severity-rated findings with fixes. Defensive review only.
argument-hint: "[path] [--deps] [--fix]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# /fastapi-security — Security audit

You run an authorized defensive security audit of the user's own FastAPI codebase, applying the `fastapi-security-audit` skill (severity rubric + checklist). You describe vulnerabilities and their fixes — you do **not** write working exploits or weaponized payloads.

## Step 0 — Context

Read `.fastapi-kit.local.json` for `appEntrypoint`, `settingsModule`, `localPackages`, `authModel`, `dbBackend`. If absent, detect them yourself (read-only): locate the app entrypoint and routers, the settings/config module, the auth scheme (OAuth2+JWT / API key / session), and the database backend. Establish which environment's config is in scope (prod-bound config makes `debug=True`, a weak/committed `SECRET_KEY`, open `/docs`, and wildcard CORS critical).

## Step 1 — Config & exposure posture

Read the prod-bound config/settings. Check and classify by the severity rubric:

- `debug` off in prod; tracebacks not leaked.
- `SECRET_KEY` (JWT signing) strong, from env/secret store, not a literal/known/default.
- `/docs`, `/redoc`, `/openapi.json` — gated or disabled on a private prod API.
- CORS — `allow_origins` not `["*"]` with `allow_credentials=True`; explicit origins when credentials used.

## Step 2 — Code review

Grep + read for the checklist patterns (cite `file:line` for each hit):

- **Auth / JWT:** `jwt.decode` without a key or with `verify_signature=False`; missing explicit `algorithms=[...]` allowlist; `alg`/algorithm-confusion; disabled `verify_exp`; tokens in the URL/query; plaintext password compare (no bcrypt/argon2).
- **Authorization / IDOR:** routes fetching by path id with no ownership/object check; **endpoints with no auth dependency** (`Depends(get_current_user)` absent where required); state-changing routes that are unintentionally public.
- **Mass-assignment:** request schemas accepting `id`, `is_admin`, `is_superuser`, `owner_id`, `role`, `price`, `status`; a table/ORM model used as the request body or `response_model`.
- **Injection:** `text(` / raw SQL strings / `.execute(` with f-string or `%` interpolation of user input; `os.system`, `subprocess(..., shell=True)`, `eval`/`exec` on request data.
- **Secrets/leakage:** secrets in source/history, in logs, in responses; `hashed_password`/tokens present on a response model.
- **File upload / deserialization:** unvalidated `UploadFile`, client-filename trust (path traversal), `pickle.loads`, `yaml.load` (non-safe), untrusted `eval`.

## Step 3 — Dependencies (`--deps`)

Run `pip-audit` (or `safety check`) if available, against the project's pinned deps. Surface known-vulnerable packages (FastAPI/Starlette/Pydantic/python-jose/PyJWT especially) with CVE id and the fixed version. **Report — do not silently bump** unless `--fix` is set and the user confirms.

## Step 4 — Report

Output a findings table sorted by severity, then a one-line verdict:

```
FASTAPI SECURITY AUDIT  (scope: app · prod config: app/core/config.py)

SEV       CATEGORY        LOCATION                     FINDING                              FIX
CRITICAL  auth/jwt        app/core/security.py:30      jwt.decode verify_signature=False    verify with key + algorithms=["HS256"]
CRITICAL  injection       app/services/report.py:54    text() with f-string user input      bind params: text("... :id"), {"id": id}
HIGH      authz/IDOR      app/routers/item.py:48       get(id) no owner check               scope to current_user / object check
HIGH      mass-assign     app/schemas/user.py:14       is_admin in UserCreate               remove from Create; server-set only
HIGH      cors            app/main.py:22               allow_origins=['*'] + credentials    explicit origin allowlist
MEDIUM    exposure        app/main.py                  /docs open on private prod API        gate behind auth / docs_url=None
LOW       deps            requirements.txt             python-jose 3.3.0 (CVE-XXXX)         bump to fixed version

VERDICT: NOT deploy-ready — 2 Critical, 3 High.
```

## --fix mode

With `--fix`, apply only the **unambiguous, low-risk** remediations (pin `algorithms=`, enable signature/expiry verification, set a field out of the Create schema, parameterize a `text()` query, tighten CORS origins) — one change at a time, each shown to the user. Do **not** auto-rotate secrets, auto-bump dependencies across majors, or change auth logic without confirmation; for those, output the steps for the user. A committed secret always requires rotation — flag it, never just delete the line.
