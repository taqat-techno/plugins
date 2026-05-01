---
description: Scan an Odoo module for version compatibility issues (read-only, no modifications). Bare invocation auto-detects the module from the current working directory.
argument-hint: "[<module-path>] [target-version]"
---

# /precheck

Perform a read-only compatibility scan on an Odoo module. Reports issues by severity. **Never modifies files.**

## Bare-invocation behavior (no args)

When invoked with no arguments, auto-detect the target module:

1. Walk up from `$CWD` until a `__manifest__.py` is found.
2. If found → use that directory as the module path; read `target-version` from the manifest's `version` field if present.
3. If `$CWD` contains multiple direct subdirectories that each have a `__manifest__.py`, list them and ask the user which to scan.
4. If no manifest is found in `$CWD`, parents, or direct subdirectories → tell the user the bare form needs a module to work and offer the explicit form `/precheck <module-path>`.

This makes `/precheck` work from inside any module directory without arguments.

## Explicit form

```
/precheck <module-path> [target-version]
```

`<module-path>` overrides auto-detection. `target-version` defaults to the latest Odoo version the plugin knows about (currently 19) when not provided.

## What the scan looks for

Scan every file in the module for:

- **XML**: `<tree>` tags, `<group>` in search views, `kanban-box` templates, `numbercall` fields, `active_id` in contexts, `//tree` XPaths, `website.snippet_options` inheritance
- **Python**: `openerp` imports, `type='json'` in routes, `tree` in view_mode, deprecated slug/url_for imports
- **JavaScript**: `useService("rpc")`, `@web/core/network/rpc_service` imports, OWL 1.x lifecycle methods
- **SCSS**: deprecated variable names (`$headings-font-weight` etc.)

## Output

Report issues grouped by severity:

- **CRITICAL**: Will cause installation to fail
- **HIGH**: Will likely cause runtime errors
- **MEDIUM**: Should fix for full compatibility
- **LOW**: Minor, optional improvements

For each issue, show the file path, line number, and a brief description of what needs to change.

## See also

- `/quickfix` — apply safe mechanical fixes for the issues this command surfaces
- `/upgrade` — full upgrade workflow with backup, transforms, and validation
