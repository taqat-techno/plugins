---
description: Scan an Odoo module for version compatibility issues (read-only, no modifications)
argument-hint: <module-path> [target-version]
---

Perform a read-only compatibility scan on the Odoo module at: $ARGUMENTS

DO NOT modify any files. Only read and report.

Scan all files in the module for:
- **XML**: `<tree>` tags, `<group>` in search views, `kanban-box` templates, `numbercall` fields, `active_id` in contexts, `//tree` XPaths, `website.snippet_options` inheritance
- **Python**: `openerp` imports, `type='json'` in routes, `tree` in view_mode, deprecated slug/url_for imports
- **JavaScript**: `useService("rpc")`, `@web/core/network/rpc_service` imports, OWL 1.x lifecycle methods
- **SCSS**: deprecated variable names (`$headings-font-weight` etc.)

Report all issues grouped by severity:
- **CRITICAL**: Will cause installation to fail
- **HIGH**: Will likely cause runtime errors
- **MEDIUM**: Should fix for full compatibility
- **LOW**: Minor, optional improvements

For each issue, show the file path, line number, and a brief description of what needs to change.
