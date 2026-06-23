---
name: fastapi-security-audit
description: FastAPI security auditing and hardening — authentication & token handling (OAuth2/JWT algorithm & expiry & signature verification), authorization (missing dependency, IDOR/object ownership, mass-assignment of privileged fields), injection (raw SQL via text()/string SQL, command), CORS misconfiguration, secret exposure, docs/debug exposure in prod, file-upload safety, and dependency CVEs. Activates when reviewing FastAPI code/config for security, hardening before a release, or responding to a suspected vulnerability or leaked secret. Renders the security pass/fail verdict; consumes patterns from the other FastAPI skills.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - the security pass/fail verdict on FastAPI code & config (severity-rated findings)
  - auth/token review (JWT alg confusion, missing signature/expiry verification, weak secret, token in URL)
  - authz review (missing auth dependency, IDOR / object-ownership, mass-assignment of privileged fields)
  - injection review (text()/raw string SQL with interpolation, os.system/subprocess/eval on input)
  - CORS / exposure review (wildcard-with-credentials, /docs & /openapi.json open on private prod)
  - secret-exposure review (committed secrets, debug leakage) and dependency/CVE surfacing
defers_to:
  - fastapi-config (the structural how-to of settings; this skill judges them)
  - fastapi-routing (correct dependency/response construction; this skill audits for bypass)
  - fastapi-pydantic (correct schema construction; this skill audits for field leaks/over-accept)
  - fastapi-database (correct ORM use; this skill audits for raw-SQL injection)
  - project threat model & compliance scope (what's in scope — adapter input)
user_invocable: false
---

# fastapi-security-audit

## Purpose

This skill is the security *judge* for FastAPI code. The other skills teach the right construction; this one assumes the worst and looks for the ways it breaks: a JWT verified with `verify_signature=False` or accepting `alg: none`, an endpoint that trusts an object id without checking ownership, a `text()` query concatenating user input, CORS open to the world with credentials, a secret in the repo, `/docs` exposing a private API's whole surface. It produces severity-rated findings, not vague advice.

## When to use

Activate when:

- Reviewing FastAPI code or config specifically for security.
- Hardening an app before a release or deploy.
- Responding to a suspected vulnerability, a leaked secret, or an incident.

This is authorized defensive review of the user's own codebase. Do not produce working exploits or weaponized payloads — describe the vulnerability, its impact, and the fix.

## Inputs (adapter)

1. **Environment in scope** — prod-bound config vs dev. `debug=True`, a weak/committed `SECRET_KEY`, and open `/docs` are critical in prod, minor in dev.
2. **Auth model** — how authentication and per-object authorization are *supposed* to work (OAuth2 password + JWT, API key, session), so "bypass" is judged against intended policy.
3. **Threat model / compliance scope** — public internet vs internal, PII/PCI/regulated data — calibrates severity.

## Severity rubric

- **Critical** — remote exploitation, data breach, or full bypass: committed secret / weak JWT signing key, JWT signature or expiry not verified (or `alg: none`/algorithm confusion), SQL injection via `text()` interpolation, auth bypass, IDOR exposing other users' data, `debug` tracebacks in prod.
- **High** — likely exploited under realistic conditions: an endpoint with no auth dependency that should require one, missing object-level ownership check on write, mass-assignment of privileged fields, CORS `allow_origins=["*"]` with `allow_credentials=True`, unsafe file upload (path traversal / executable), `pickle`/`yaml.load` on untrusted input.
- **Medium** — defense-in-depth gaps: `/docs`/`/openapi.json` exposed on a private prod API, no rate limiting on auth, overly broad CORS without credentials, verbose error leakage, missing security headers.
- **Low / Info** — hardening opportunities, outdated-but-unexploited dependency, minor header gaps.

## Audit checklist

### 1. Authentication & tokens (JWT)

- **Signature verified** — `jwt.decode(token, key, algorithms=[...])` with a real key; never `options={"verify_signature": False}` on a trust path.
- **Algorithm pinned** — pass an explicit `algorithms=["HS256"]`/`["RS256"]` allowlist. Never accept `alg: none`; never allow an asymmetric verifier to be tricked into HMAC with the public key (algorithm-confusion).
- **Expiry checked** — `exp` claim present and validated (don't disable `verify_exp`). Reasonable token lifetime; refresh handled.
- **Strong signing secret** from the environment (→ `fastapi-config`), not a literal/short/default. Tokens carried in the `Authorization` header, **never in the URL/query string** (logged, cached, referer-leaked).
- Passwords hashed with a real algorithm (bcrypt/argon2 via passlib), never stored or compared in plaintext.

### 2. Authorization

- **Missing auth dependency** — an endpoint that should require auth but declares no `Depends(get_current_user)` (or equivalent) is an accidental public endpoint. Check every state-changing and data-returning route.
- **IDOR / object ownership** — any route fetching by id from the path must verify the caller may access *that* object (filter by `owner_id == current_user.id`, or an object-permission check). Fetching by pk alone is the classic IDOR.
- **Mass-assignment** — a request schema that lets a client set `id`, `is_admin`, `is_superuser`, `owner_id`, `role`, `price`, `status` (→ construction owned by `fastapi-pydantic`; the bypass is judged here).

### 3. Injection

- **SQL:** `text()` / raw SQL strings / `connection.execute` with **f-string or `%`-interpolated** user input → SQL injection. Use bound parameters (`text("... WHERE id = :id"), {"id": id}`) or the ORM expression API. The ORM is safe by default; the raw escapes are where it breaks.
- **Command:** `os.system`, `subprocess(..., shell=True)`, `eval`/`exec` on request data → RCE.

### 4. CORS & exposure

- **CORS:** `allow_origins=["*"]` with `allow_credentials=True` is invalid and unsafe — exposes authenticated responses cross-origin. Explicit origin allowlist when credentials are used. Wildcard methods/headers are a smaller smell.
- **Docs:** `/docs`, `/redoc`, `/openapi.json` open on a private/internal prod API leak the full surface — gate behind auth or disable (→ `fastapi-config`).
- **Debug:** `debug=True` / verbose exception output in prod leaks internals.

### 5. Secrets & data leakage

- Secrets in source/VCS history, in logs, in error responses. A committed secret is **Critical** and requires rotation (history removal alone is insufficient).
- Sensitive fields (`hashed_password`, tokens) excluded from response models (→ `fastapi-pydantic`); not logged.

### 6. File upload & deserialization

- Uploads (`UploadFile`): validate type/size, never trust the client filename (path traversal), store outside any served path, never serve as executable.
- Deserialization: no `pickle.loads`, `yaml.load` (use `safe_load`), or untrusted `eval` on request data.

### 7. Dependencies

- Surface known-vulnerable packages (`pip-audit` / `safety`) and pinned-but-outdated security-relevant deps (FastAPI/Starlette/Pydantic/python-jose/PyJWT). Report; don't silently bump.

## Workflow

1. Establish the prod-bound config and check `debug`, `SECRET_KEY` source, `/docs` exposure, CORS.
2. Grep the codebase for the patterns above (`verify_signature`, `algorithms=`, `alg`, `text(`, `shell=True`, `pickle`, `yaml.load`, `allow_origins`, `is_admin`/`is_superuser` writable).
3. Trace object-fetch-by-id paths for ownership checks; check every route for a present/absent auth dependency.
4. Scan for committed secrets and token handling.
5. Run / recommend a dependency audit.

## Report format

Output a findings table — **severity · category · location (file:line) · description · impact · remediation** — sorted by severity, plus a one-line verdict (e.g. "Not deploy-ready: 2 Critical, 3 High"). Be specific with file/line; never report a vulnerability without the fix. Do not include working exploit payloads.
