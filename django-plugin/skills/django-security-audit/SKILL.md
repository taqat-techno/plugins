---
name: django-security-audit
description: Django security auditing and hardening — settings posture (DEBUG, SECRET_KEY, ALLOWED_HOSTS, HTTPS/HSTS/secure cookies), injection (SQL via raw/extra, template/HTML, command), CSRF, authentication & authorization (permission bypass, IDOR/object ownership, mass-assignment), file-upload safety, secret exposure, and dependency CVEs. Activates when reviewing Django code/settings for security, hardening before a release, responding to a suspected vulnerability or leaked secret, or running deploy/security checks. Renders the security pass/fail verdict; consumes patterns from the other Django skills.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - the security pass/fail verdict on Django settings & code (severity-rated findings)
  - injection review (raw()/extra()/RawSQL, mark_safe/|safe, os.system/subprocess from input)
  - CSRF review (csrf_exempt, missing token, unsafe SameSite/cookie flags)
  - authn/authz review (permission bypass, IDOR / object-ownership, mass-assignment of privileged fields)
  - secret-exposure review (committed secrets, DEBUG=True in prod, traceback/data leakage)
  - file-upload & deserialization safety, and dependency/CVE surfacing
defers_to:
  - django-settings-config (the structural how-to of settings; this skill judges them)
  - django-views-drf (correct permission/serializer construction; this skill audits for bypass)
  - django-orm-models (correct ORM use; this skill audits for raw-SQL injection)
  - project threat model & compliance scope (what's in scope — adapter input)
user_invocable: false
---

# django-security-audit

## Purpose

This skill is the security *judge* for Django code. The other skills teach the right construction; this one assumes the worst and looks for the ways it breaks: a debug page leaking settings, an endpoint that trusts an object id without checking ownership, a `raw()` call concatenating user input, a secret in the repo. It produces severity-rated findings, not vague advice.

## When to use

Activate when:

- Reviewing Django code or settings specifically for security.
- Hardening an app before a release or deploy.
- Responding to a suspected vulnerability, a leaked secret, or an incident.
- Running `manage.py check --deploy` or interpreting its output.

This is authorized defensive review of the user's own codebase. Do not produce working exploits or weaponized payloads — describe the vulnerability, its impact, and the fix.

## Inputs (adapter)

1. **Environment in scope** — auditing prod-bound settings vs dev. `DEBUG=True` is a critical finding in prod, a non-issue in dev.
2. **Auth model** — how authentication and per-object authorization are *supposed* to work, so "bypass" is judged against intended policy.
3. **Threat model / compliance scope** — public internet vs internal, PII/PCI/regulated data — calibrates severity.

## Severity rubric

- **Critical** — remote exploitation, data breach, or full bypass: `DEBUG=True` in prod, secret committed to VCS, SQL injection via `raw()`, auth bypass, IDOR exposing other users' data.
- **High** — likely exploited under realistic conditions: missing object-level authz on write, CSRF disabled on a state-changing view, mass-assignment of privileged fields, unsafe file upload (path traversal / executable), `pickle`/`yaml.load` on untrusted input.
- **Medium** — defense-in-depth gaps: missing HSTS/secure-cookie/SSL-redirect, weak password validators, verbose error leakage, missing rate limiting on auth.
- **Low / Info** — hardening opportunities, outdated-but-unexploited dependency, missing security header with low impact.

## Audit checklist

### 1. Settings posture (run `check --deploy` first)

- `DEBUG = False` in prod. **Critical** if True. (`DEBUG=True` exposes tracebacks, settings, SQL.)
- `SECRET_KEY` strong, from env/secret store, not in source, not a known/default value.
- `ALLOWED_HOSTS` set explicitly (not `["*"]` in prod).
- HTTPS: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` (+ `INCLUDE_SUBDOMAINS`, `PRELOAD`), `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER` if behind a proxy.
- Cookies: `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`, `CSRF_COOKIE_HTTPONLY` as appropriate.
- `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "DENY"` (clickjacking), CSP if applicable.
- Password validators (`AUTH_PASSWORD_VALIDATORS`) configured, not empty.

### 2. Injection

- **SQL:** `raw()`, `extra()`, `RawSQL`, or `cursor.execute()` with **string-interpolated** user input → SQL injection. Parameterized queries (`%s` placeholders + params) only. The ORM is safe by default; the raw escapes are where it breaks.
- **HTML/template:** `mark_safe()`, `|safe`, `format_html` misuse, or `autoescape off` over user-controlled data → stored/reflected XSS.
- **Command:** `os.system`, `subprocess` with `shell=True`, `eval`/`exec` on request data → RCE.

### 3. CSRF

- `@csrf_exempt` on any state-changing view is a finding — justify or remove. DRF `SessionAuthentication` enforces CSRF; token/JWT-only APIs are exempt by design (note which auth applies).
- Forms render `{% csrf_token %}`; AJAX sends the token.

### 4. Authentication & authorization

- **IDOR / object ownership:** any view fetching by id from the URL must verify the requester may access *that* object — `get_object_or_404(Model, pk=pk, owner=request.user)` or an object-level permission. Filtering only by pk is the classic IDOR.
- **Permission bypass:** view-level permission without object-level check on detail/update/delete; a permissive default permission class (→ construction owned by `django-views-drf`, the bypass is judged here).
- **Mass-assignment:** a serializer/form that lets a user set `is_staff`, `is_superuser`, `owner`, `price`, `status` — privileged fields writable from the request.
- Auth flows: rate-limited login, secure password reset, session fixation handled on login (`cycle_key`), no user-enumeration via differential responses/timing.

### 5. Secrets & data leakage

- Secrets in source/VCS history, in logs, in error pages, in API responses. A committed secret is **Critical** and requires rotation (history removal alone is insufficient).
- Sensitive fields excluded from serializers/admin/logs; `settings` not reachable via a debug view in prod.

### 6. File upload & deserialization

- Uploads: validate type/size, store outside the web root or via storage backend, never trust the client filename (path traversal), never serve uploads as executable.
- Deserialization: no `pickle.loads`, `yaml.load` (use `safe_load`), or untrusted `eval` on request data.

### 7. Dependencies

- Surface known-vulnerable packages (`pip-audit` / `safety` / advisory DB) and pinned-but-outdated security-relevant deps. Report; don't silently bump.

## Workflow

1. Run `python manage.py check --deploy` (settings posture) and capture output.
2. Grep the codebase for the injection/bypass patterns above (raw SQL, `mark_safe`, `csrf_exempt`, `is_superuser` assignment, `shell=True`, `pickle`, `yaml.load`).
3. Trace object-fetch-by-id paths for ownership checks.
4. Scan for committed secrets and `DEBUG`/`SECRET_KEY` handling.
5. Run / recommend a dependency audit.

## Report format

Output a findings table — **severity · category · location (file:line) · description · impact · remediation** — sorted by severity, plus a one-line verdict (e.g. "Not deploy-ready: 2 Critical, 3 High"). Be specific with file/line; never report a vulnerability without the fix. Do not include working exploit payloads.
