# Hook Ownership Registry

Each file pattern has exactly **one** PostToolUse owner plugin. New plugins must check
this registry before adding hooks for existing patterns.

**Rule:** If plugin B wants to add advice for a pattern owned by plugin A, contribute
text to A's prompt rather than adding a duplicate hook.

## PostToolUse File Pattern Ownership

| File Pattern | Owner Plugin | What It Covers |
|-------------|-------------|----------------|
| `**/__manifest__.py` | odoo-service | Version bump, security file order, report data, module update, tests |
| `**/models/*.py` | odoo-service | __init__.py import, access rules, sudo() audit, test generation, module update |
| `**/controllers/*.py` | odoo-security | Route auth, CSRF, HttpCase test suggestion |
| `**/wizard*/*.py` | odoo-security | TransientModel access rules |
| `**/ir.model.access.csv` | odoo-security | Format validation, AccessError tests |
| `**/tests/test_*.py` | odoo-test | Coverage, SavepointCase removal, __init__.py import |
| `**/docker-compose*.{yml,yaml}` | odoo-docker | Container recreation |
| `**/Dockerfile*` | odoo-docker | Image rebuild |
| `**/nginx*.conf` | odoo-docker | Reverse proxy config + reload |
| `**/.env` | odoo-docker | Container recreation (not restart) |
| `**/entrypoint*.sh` | odoo-docker | chmod +x, rebuild vs restart |
| `**/requirements*.txt` | odoo-service | pip install (local) + Docker rebuild |
| `**/conf/*.conf` | odoo-service | Server restart (local + Docker), critical settings |
| `*.po, *.pot` | odoo-i18n | Translation validation, missing strings |
| New files (Write only) | odoo-i18n | i18n checklist (Python _(), XML string=, JS _t, SCSS logical props) |
| `**/data/mail_template*.xml` | odoo-report | Email template validation (body_html, inline_template, t-out) |
| `**/report*/**/*.xml` | odoo-report | QWeb report structure, page breaks, Arabic/RTL |
| `*.tsx, *.jsx` | remotion | <Audio> placement, voice generation |
| `generate_voice.py` | remotion | Audio measurement follow-up |
| `concat_audio.py` | remotion | Segment-to-Sequence mapping |
| `timeline*.json` | remotion | Duration validation |
| `*.html,xml,jsx,tsx,vue,svelte` | paper | Semantic tags, alt text, form labels |
| `*.css,scss,sass,less` | paper | Contrast, rem/em units, focus styles |

## PreToolUse Ownership (Blocking)

| Matcher | Owner Plugin | What It Blocks |
|---------|-------------|---------------|
| `Write\|Edit` (core paths) | odoo-upgrade | Core Odoo file modifications |
| `Write\|Edit` (inline JS) | odoo-frontend | Inline JavaScript in XML |
| Azure DevOps MCPs | devops | Unauthorized state transitions |

## Bash Tool Ownership

| Concern | Owner Plugin | Notes |
|---------|-------------|-------|
| Git workflow (commit, PR) | devops | Pre + Post |
| pip install/uninstall | odoo-service | Post only |
| Port 8069/8072 conflicts | odoo-service | Post only |
| Odoo version compat errors | odoo-upgrade | Post only (prompt) |
| Long-running task notify | ntfy | Post only (prompt) |
| Pandoc best practices | pandoc | Pre only |

## SessionStart Ownership

| Plugin | Type | Purpose |
|--------|------|---------|
| devops | command | Profile validation, staleness check |
| odoo-frontend | command | Odoo version + Bootstrap/Owl detection |
| pandoc | command | pandoc/LaTeX availability |
| odoo-docker | prompt | Docker file detection |
| odoo-upgrade | prompt | Plugin welcome message |
| ntfy | prompt | Config validation |
