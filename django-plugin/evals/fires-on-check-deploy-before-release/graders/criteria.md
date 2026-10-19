---
type: llm
---
PASS if the reply recommends running manage.py check --deploy against the production settings module and covers the settings posture (DEBUG off, a strong SECRET_KEY from the environment, explicit ALLOWED_HOSTS, HTTPS redirect / HSTS / secure cookies) plus at least two code-level review areas such as raw SQL injection, csrf_exempt views, IDOR / object ownership, or mass-assignment of privileged fields, and organizes findings by severity or as a pass/fail verdict.
FAIL if the reply never mentions check --deploy, or gives only generic web-security advice (use HTTPS, strong passwords) without Django-specific settings.
