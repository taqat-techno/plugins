---
description: Apply safe mechanical fixes for common Odoo version compatibility issues
argument-hint: <module-path>
---

Apply quick, safe, mechanical fixes to the Odoo module at: $ARGUMENTS

These are well-understood, reversible transformations. Before applying:
1. Show a preview of what will change (dry-run style)
2. Ask for confirmation before modifying files

Apply the safe mechanical fixes defined in the odoo-upgrade skill (see the "XML/View Transformations" section for the complete pattern list). These include tag renames, attribute removals, and other deterministic replacements.

Do NOT apply complex transforms that require judgment (RPC migration, attrs-to-inline, OWL lifecycle). Those should use `/odoo-upgrade` instead.
