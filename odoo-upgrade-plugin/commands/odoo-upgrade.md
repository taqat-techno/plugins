---
description: Upgrade an Odoo module to a target version with full transformation pipeline
argument-hint: <module-path> [target-version]
---

Perform a complete Odoo module upgrade for the path and target version specified in: $ARGUMENTS

Follow this workflow:

1. **Analyze**: Read the module's `__manifest__.py` to determine the current version. Scan all Python, XML, JavaScript, and SCSS files to identify compatibility issues.

2. **Report Issues**: Present a summary of all issues found, grouped by severity (CRITICAL, HIGH, MEDIUM, LOW). Ask the user to confirm before proceeding with fixes.

3. **Backup**: Before making any changes, create a backup of the module directory.

4. **Apply Transforms** (in order):
   - Update manifest version string and add missing required fields
   - XML: tree->list, search group removal, kanban-box->card, numbercall removal, active_id->id, XPath //tree->//list, attrs->inline
   - Python: openerp->odoo imports, slug/url_for wrappers, type='json'->type='jsonrpc', view_mode tree->list
   - JavaScript: RPC service replacement with _jsonRpc helper, OWL lifecycle hook renames, @odoo-module annotation
   - SCSS: variable renames for Odoo theme conventions

5. **Validate**: After all transforms, validate syntax of all modified files (Python AST, XML parsing, JS bracket balance).

6. **Report**: Generate a summary of all changes made, files modified, and any remaining issues that need manual attention.

Use the odoo-upgrade skill for transformation patterns and version-specific knowledge. You can also run the upgrade scripts directly:

```bash
# Read-only scan
python "${CLAUDE_PLUGIN_ROOT}/odoo-upgrade/scripts/cli.py" precheck <path> --target <version>

# Full upgrade pipeline
python "${CLAUDE_PLUGIN_ROOT}/odoo-upgrade/scripts/cli.py" upgrade <path> --target <version>
```
