---
description: Run a Django security audit — manage.py check --deploy plus a code/settings review for injection, CSRF, auth/authorization bypass (IDOR, mass-assignment), secret exposure, file-upload safety, and dependency CVEs. Produces severity-rated findings with fixes. Defensive review only.
argument-hint: "[app-or-path] [--deploy-only] [--deps] [--fix]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# /django-security — Security audit

You run an authorized defensive security audit of the user's own Django codebase, applying the `django-security-audit` skill (severity rubric + checklist). You describe vulnerabilities and their fixes — you do **not** write working exploits or weaponized payloads.

## Step 0 — Context

Read `.django-kit.local.json` for `managePrefix`, `settingsModules`, `localApps`, `drf`, `dbBackend`. If absent, detect them yourself (read-only): locate `manage.py` and its invocation prefix, the settings modules, local apps, DRF presence, and the database backend. Establish which environment's settings are in scope (prod-bound settings make `DEBUG=True`, weak `SECRET_KEY`, and `ALLOWED_HOSTS=["*"]` critical).

## Step 1 — Deploy check

Run `<managePrefix> check --deploy --settings=<prod settings module>` (use the prod-intended settings). Capture and classify each warning by the severity rubric. `--deploy-only` stops after this.

## Step 2 — Code & settings review

Grep + read for the checklist patterns (cite `file:line` for each hit):

- **Settings posture:** `DEBUG`, `SECRET_KEY` (literal/known/in-source), `ALLOWED_HOSTS`, HTTPS/HSTS/secure-cookie/`X_FRAME_OPTIONS`/nosniff settings, password validators.
- **Injection:** `raw(`, `extra(`, `RawSQL`, `cursor.execute(` with string interpolation; `mark_safe`, `|safe`, `format_html` over user data; `os.system`, `subprocess(..., shell=True)`, `eval`/`exec` on request data.
- **CSRF:** `@csrf_exempt` on state-changing views; missing token on forms.
- **Authz / IDOR:** views fetching by URL id without an ownership/object-permission check; permissive default DRF permission; detail/update/delete with only view-level permission.
- **Mass-assignment:** serializers/forms exposing `is_staff`, `is_superuser`, `owner`, `price`, `status`, `role` as writable; `fields = "__all__"`.
- **Secrets/leakage:** secrets in source/history, in logs, in responses; debug/settings reachable in prod.
- **File upload / deserialization:** unvalidated uploads, client-filename trust (path traversal), `pickle.loads`, `yaml.load` (non-safe), untrusted `eval`.

## Step 3 — Dependencies (`--deps`)

Run `pip-audit` (or `safety check`) if available, against the project's pinned deps. Surface known-vulnerable packages with CVE id and the fixed version. **Report — do not silently bump** unless `--fix` is set and the user confirms.

## Step 4 — Report

Output a findings table sorted by severity, then a one-line verdict:

```
DJANGO SECURITY AUDIT  (scope: project · prod settings: config.settings.prod)

SEV       CATEGORY        LOCATION                     FINDING                              FIX
CRITICAL  settings        config/settings/prod.py:8    DEBUG=True in prod settings          drive from env; default False
CRITICAL  injection       orders/reports.py:73         raw() with f-string user input       parameterize: raw(sql, [params])
HIGH      authz/IDOR      orders/views.py:40           get(pk=pk) no owner check            scope to request.user / object perm
HIGH      mass-assign     accounts/serializers.py:12   is_staff writable                    read_only=True
MEDIUM    hardening       config/settings/prod.py      no HSTS / SSL redirect               set SECURE_HSTS_SECONDS, SSL redirect
LOW       deps            requirements.txt             Django 4.2.1 (CVE-XXXX)              bump to 4.2.latest

VERDICT: NOT deploy-ready — 2 Critical, 2 High.
```

## --fix mode

With `--fix`, apply only the **unambiguous, low-risk** remediations (add a missing security setting, set a field `read_only`, parameterize a raw query) — one change at a time, each shown to the user. Do **not** auto-rotate secrets, auto-bump dependencies across majors, or change auth logic without confirmation; for those, output the steps for the user to perform. A committed secret always requires rotation — flag it, never just delete the line.
