# Changelog

## v2.1.0 (2026-03-26)

- Added `model: sonnet` to skill frontmatter
- Replaced bash SessionStart hook with cross-platform prompt hook
- Progressive disclosure: extracted sections 8-14 to `reference/advanced-topics.md`
- Enhanced `/odoo-docker` status with real diagnostics
- Added `requirements-changed` PostToolUse hook
- Added deploy validation step (`docker compose config` + `nginx -t`)

## v2.0.0

- Initial plugin release
- Supports Odoo 14-19, Python 3.8-3.12, PostgreSQL 12-15
- 7 templates: Dockerfile, docker-compose (dev/prod), nginx, entrypoint, odoo.conf, .env
- 7 hooks: SessionStart detection + 6 PostToolUse file watchers
- 4 reference docs: version-matrix, troubleshooting, production-checklist, docker-patterns

---

## How to Update When Adding a New Odoo Version

When a new Odoo version is released (e.g., Odoo 20), update these files:

| File | What to add |
|------|-------------|
| `reference/version-matrix.md` | New row with Python, Debian, PostgreSQL, Node.js, wkhtmltopdf, gevent key, entry point |
| `odoo-docker/SKILL.md` section 5 | New row in the key lookup table |
| `templates/Dockerfile.template` | New version case in the build args comments |
| `templates/entrypoint.sh` | Verify entry point detection still works |
| `odoo-docker/SKILL.md` frontmatter | Add version to `odoo-versions` array |
