---
description: Apply safe mechanical fixes for common Odoo version compatibility issues. Bare invocation auto-detects the module from the current working directory.
argument-hint: "[<module-path>]"
---

# /quickfix

Apply quick, safe, mechanical fixes to an Odoo module. Always shows a preview and asks for confirmation before modifying files.

## Bare-invocation behavior (no args)

Auto-detect the target module the same way `/precheck` does:

1. Walk up from `$CWD` until a `__manifest__.py` is found → use that directory.
2. Multiple direct subdirectories each with a manifest → list and ask which.
3. None found → tell the user the bare form needs a module and offer `/quickfix <module-path>`.

## Explicit form

```
/quickfix <module-path>
```

## What it applies

Safe mechanical fixes from the `odoo-upgrade` skill ("XML/View Transformations" section). These include tag renames, attribute removals, and deterministic replacements that cannot change semantic meaning.

**Never applies** complex transforms that require judgment (RPC migration, attrs-to-inline, OWL lifecycle). Those go through `/upgrade`.

## Workflow

1. Show a dry-run preview of all proposed changes.
2. Ask for confirmation before writing.
3. Apply the safe transforms.
4. Report what was changed.

## See also

- `/precheck` — read-only scan with no modifications
- `/upgrade` — full upgrade workflow including the complex transforms
