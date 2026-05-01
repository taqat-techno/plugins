---
title: 'Odoo Security'
read_only: true
type: 'command'
description: 'Comprehensive Odoo module security audit - access rules, routes, sudo, SQL injection'
argument-hint: '[<module>] [--severity=critical|high|medium|low] [--layer=access|routes|sudo|all] [--fix] [--json]'
---

# /security

## Bare-invocation behavior (no args)

When invoked with no arguments, auto-detect the target module:

1. Walk up from `$CWD` until a `__manifest__.py` is found → use that module.
2. If `$CWD` contains multiple direct subdirectories each with a manifest → list and ask which.
3. If none found → ask for the explicit form `/security <module>`.

Defaults applied when omitted: `--severity=low`, `--layer=all`, no `--fix`, no `--json`.

## Arguments

| Token | Type | Default | Description |
|-------|------|---------|-------------|
| First positional | path/name | _auto-detect from CWD_ | Module path or name |
| `--severity=` | enum | `low` | Minimum severity: `critical`, `high`, `medium`, `low` |
| `--layer=` | enum | `all` | Audit layer: `access`, `routes`, `sudo`, `sql`, `all` |
| `--fix` | flag | off | Generate and apply safe remediations |
| `--json` | flag | off | Machine-readable JSON output |

Use the odoo-security skill for:
- Severity scoring system (0-100 scale, CRITICAL/HIGH/MEDIUM/LOW)
- Layer-based audit patterns and OWASP-inspired checks
- Access rule validation rules
- Route authentication audit criteria
- sudo() privilege escalation detection patterns
- SQL injection pattern detection

Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/security/`:
- `security_auditor.py` - Unified orchestrator
- `access_checker.py` - ir.model.access.csv completeness
- `route_auditor.py` - HTTP route auth audit
- `sudo_finder.py` - Unsafe sudo() detection
- `sql_scanner.py` - SQL injection patterns

Run the appropriate script based on `--layer`, aggregate results, and present a severity-scored report. With `--fix`, generate safe remediations and ask for confirmation before applying.
