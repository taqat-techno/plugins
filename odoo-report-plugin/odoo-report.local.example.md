---
default_version: 17
author: "TaqaTechno"
website: "https://www.taqatechno.com/"
support: "info@taqatechno.com"
default_layout: "mail.mail_notification_layout"
auto_delete: true
---

# Odoo Report Plugin - Local Configuration

Copy this file to `odoo-report.local.md` in your project's `.claude/` directory and customize the YAML frontmatter above.

## Settings

- **default_version**: Odoo version to use when auto-detection is ambiguous (14-19)
- **author**: Author name for `__manifest__.py` in generated modules
- **website**: Website URL for manifest
- **support**: Support email for manifest
- **default_layout**: Default `email_layout_xmlid` for new email templates
- **auto_delete**: Default `auto_delete` value for email templates
