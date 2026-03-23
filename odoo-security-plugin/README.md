# Odoo Security Plugin (v2.1)

A comprehensive security auditing plugin for Odoo modules (versions 14-19). Performs static analysis across all security layers: model access rules, HTTP route authentication, sudo() usage patterns, SQL injection risks, and record rule completeness.

## Features

- **Multi-layer analysis**: Checks Odoo's 3-layer security model simultaneously
- **Severity grading**: Issues classified as CRITICAL / HIGH / MEDIUM / LOW
- **Version support**: Works with Odoo 14, 15, 16, 17, 18, and 19
- **Actionable output**: Every issue includes a specific remediation code snippet
- **CI/CD integration**: Exit codes and JSON output for pipeline integration
- **File system hooks**: Automatic suggestions when creating models or controllers
- **Standalone scripts**: Each auditor can run independently
- **Configurable**: Customize sensitive models, excluded paths, and severity thresholds

---

## Installation

### Option 1: Claude Code Plugin (Recommended)

Place the plugin directory in your Claude plugins folder:

```bash
# Clone or copy the plugin
cp -r odoo-security-plugin ~/.claude/plugins/odoo-security-plugin

# Or on Windows:
xcopy /E /I odoo-security-plugin "%USERPROFILE%\.claude\plugins\odoo-security-plugin"
```

The plugin will be automatically available in Claude Code sessions. The AI will:
- Suggest security checks when you create or edit files in `models/`
- Suggest route auditing when you create or edit files in `controllers/`
- Suggest access validation when you edit `ir.model.access.csv`

### Option 2: Standalone Python Scripts

No installation needed. Run directly from the scripts directory:

```bash
# Run directly (Python 3.8+ required, no additional packages)
python odoo-security/scripts/security_auditor.py /path/to/your/module
```

---

## Quick Start

### Run a Full Audit

```bash
# Full security audit on a module
python odoo-security/scripts/security_auditor.py /path/to/my_module

# Only HIGH+ issues
python odoo-security/scripts/security_auditor.py /path/to/my_module --min-severity HIGH

# JSON report for tooling
python odoo-security/scripts/security_auditor.py /path/to/my_module --json --output report.json
```

### Unified Command (in Claude Code)

All security checks are accessible through `/odoo-security` with `--layer` and `--severity` flags:

```bash
# Full audit (all layers, all severities)
/odoo-security /path/to/module

# Audit only access rules, show HIGH+ issues
/odoo-security /path/to/module --layer=access --severity=high

# Audit only routes layer
/odoo-security /path/to/module --layer=routes

# Audit only sudo usage, CRITICAL only
/odoo-security /path/to/module --layer=sudo --severity=critical

# SQL injection scan
/odoo-security /path/to/module --layer=sql
```

### Natural Language

You can also trigger security audits using plain English:

- "Check if all models have proper access rules in my module"
- "Audit HTTP routes in my module for authentication issues"
- "Find all places where sudo() is used without proper context"
- "Scan my module for SQL injection vulnerabilities"
- "Run a complete security audit on my HR module"

### Run Individual Auditors

```bash
python odoo-security/scripts/access_checker.py /path/to/module
python odoo-security/scripts/route_auditor.py /path/to/module
python odoo-security/scripts/sudo_finder.py /path/to/module
python odoo-security/scripts/sql_scanner.py /path/to/module
```

---

## Configuration

Create `.odoo-security.json` in your module root (or project root) to customize behavior:

```json
{
  "sensitive_models_add": ["custom.sensitive.model"],
  "sensitive_models_remove": ["mail.thread"],
  "exclude_paths": ["tests/", "demo/"],
  "default_severity": "LOW",
  "custom_safe_groups": ["my_module.group_special"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sensitive_models_add` | list | Models to add to the built-in sensitive models set |
| `sensitive_models_remove` | list | Models to remove from the built-in sensitive models set |
| `exclude_paths` | list | Glob patterns for paths to skip during scanning |
| `default_severity` | string | Minimum severity to report (CRITICAL/HIGH/MEDIUM/LOW) |
| `custom_safe_groups` | list | Groups to treat as known/valid (suppresses unknown group warnings) |

All fields are optional. The config uses additive/subtractive patterns so built-in defaults are never lost.

---

## Usage Reference

### security_auditor.py (Orchestrator)

```
Usage: python security_auditor.py <module_path> [options]

Options:
  --min-severity {CRITICAL,HIGH,MEDIUM,LOW}
                        Minimum severity to report (default: LOW)
  --exit-on-issues      Exit with code 1 if issues found (CI integration)
  --json                Output as machine-readable JSON
  --output <file>       Write report to file
  --skip-auditor {access,routes,sudo,sql}
                        Skip specific sub-auditor (repeatable)

Exit codes:
  0 = No issues found at min-severity or above
  1 = Issues found at min-severity or above
  2 = Usage error (invalid path, etc.)
```

### access_checker.py

Checks: Models without CSV entries (CRITICAL), wizards without rules (HIGH), empty group_id (HIGH), overly permissive permissions (MEDIUM), missing multi-company rules (HIGH), unknown group references (LOW).

### route_auditor.py

Checks: auth='none' without validation (CRITICAL), missing auth= (HIGH), sudo() + sensitive model in public (HIGH), csrf=False on user routes (HIGH), mixed GET/POST (MEDIUM).

### sudo_finder.py

Checks: sudo() in public route + sensitive model (CRITICAL), sudo() in public (HIGH), sudo() on sensitive model (HIGH), sudo() in loop (MEDIUM), unscoped sudo() (MEDIUM).

### sql_scanner.py

Checks: f-strings in cr.execute() (CRITICAL), .format() in cr.execute() (CRITICAL), string concatenation (HIGH), % operator (HIGH), variable queries (MEDIUM), _where_calc without _apply_ir_rules (LOW).

---

## Sample Output

```
Running security audit on: /path/to/my_module
  Running access_checker... 2 CRITICAL, 1 HIGH
  Running route_auditor...  1 HIGH
  Running sudo_finder...    1 MEDIUM
  Running sql_scanner...    CLEAN

======================================================================
  ODOO SECURITY AUDIT REPORT
======================================================================
  Module:    my_module
  Path:      /path/to/my_module
  Risk Score: 72/100 — Significant vulnerabilities present

  SUMMARY
  ----------------------------------------
  CRITICAL      2 issues
  HIGH          2 issues
  MEDIUM        1 issue
  TOTAL         5 issues

  ISSUES (sorted by severity)
  ======================================================================

  [CRITICAL] models/my_model.py:15
    Model 'my.model' has no access rules in ir.model.access.csv.
    FIX: Add: access_my_model_user,my.model user,model_my_model,[group],1,1,1,0

  [HIGH] controllers/main.py:34
    Route ['/orders'] uses auth='none' but no API key validation detected.
    FIX: Add API key validation or change auth='user'.
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Odoo Security Audit
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run Security Audit
        run: |
          python ./odoo-security/scripts/security_auditor.py \
            ./projects/my_project/my_module \
            --min-severity HIGH \
            --exit-on-issues \
            --json \
            --output security-report.json
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: security-report.json
```

### Pre-commit Hook

```bash
#!/bin/bash
AUDITOR="./odoo-security/scripts/security_auditor.py"
CHANGED_MODULES=$(git diff --cached --name-only | grep -E '^projects/' | awk -F'/' '{print $1"/"$2"/"$3}' | sort -u)

for MODULE in $CHANGED_MODULES; do
    if [ -f "$MODULE/__manifest__.py" ]; then
        python "$AUDITOR" "$MODULE" --min-severity CRITICAL --exit-on-issues || exit 1
    fi
done
```

---

## Plugin Structure

```
odoo-security-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata and configuration
├── odoo-security/
│   ├── SKILL.md                 # AI skill definition
│   └── scripts/
│       ├── _common.py           # Shared utilities and constants
│       ├── security_auditor.py  # Master orchestrator
│       ├── access_checker.py    # Model access rule checker
│       ├── route_auditor.py     # HTTP route security auditor
│       ├── sudo_finder.py       # sudo() risk classifier
│       └── sql_scanner.py       # SQL injection detector
├── commands/
│   └── odoo-security.md         # /odoo-security unified command
├── memories/
│   ├── security_patterns.md     # Severity-graded patterns with fixes
│   ├── access_rules.md          # Complete ir.model.access.csv reference
│   └── odoo_vulnerabilities.md  # Top 8 Odoo vulnerabilities
├── hooks/
│   └── hooks.json               # File-scoped PostToolUse triggers
└── README.md                    # This file
```

---

## What Gets Checked

### Access Control Layer

| Check | Severity | Description |
|-------|----------|-------------|
| Model without CSV entry | CRITICAL | Any model with `_name` but no access rule |
| Wizard without CSV entry | HIGH | TransientModel without access rule |
| Empty group_id in CSV | HIGH | Grants access to ALL authenticated users |
| Overly permissive perms | MEDIUM | DELETE for non-manager groups |
| No multi-company rule | HIGH | Model with company_id but no record rules |

### Route Security Layer

| Check | Severity | Description |
|-------|----------|-------------|
| auth='none' without auth code | CRITICAL | Completely unauthenticated route |
| Missing auth= parameter | HIGH | Implicit default |
| sudo() + sensitive model in public | HIGH | IDOR risk |
| csrf=False on user route | HIGH | CSRF vulnerability |
| SQL injection in controller | HIGH | String formatting in execute() |

### sudo() Usage Layer

| Check | Severity | Description |
|-------|----------|-------------|
| sudo() in public route + sensitive model | CRITICAL | Bypasses all access controls |
| sudo() in public route | HIGH | Privilege escalation |
| sudo() accessing sensitive model | HIGH | Unnecessary broad access |
| sudo() in loop | MEDIUM | Performance + security smell |
| Unscoped sudo() | MEDIUM | No domain filter applied |

### SQL Injection Layer

| Check | Severity | Description |
|-------|----------|-------------|
| f-string in cr.execute() | CRITICAL | Direct SQL injection |
| .format() in cr.execute() | CRITICAL | Direct SQL injection |
| String concatenation | HIGH | SQL injection risk |
| % operator formatting | HIGH | SQL injection risk |
| _where_calc without rules | LOW | Record rule bypass |

---

## Customization

### Adding Custom Checks

1. Identify the check category: access, routes, sudo, or sql
2. Add detection logic to the appropriate script
3. Return an issue dict with: `severity`, `type`, `file`, `line`, `message`
4. Add remediation to `generate_remediation()` in `security_auditor.py`
5. Document in `memories/security_patterns.md`

### Extending Sensitive Models

Create `.odoo-security.json` in your module root:
```json
{
  "sensitive_models_add": ["hr.contract", "hr.salary.rule"]
}
```

### Excluding Paths

```json
{
  "exclude_paths": ["tests/", "demo/", "data/demo_data.py"]
}
```

---

## Supported Odoo Versions

| Version | Status | Notes |
|---------|--------|-------|
| Odoo 14 | Supported | Legacy auth patterns detected |
| Odoo 15 | Supported | website auth_signup_token handling |
| Odoo 16 | Supported | Bootstrap 5 / ir.http refactor aware |
| Odoo 17 | Supported (Primary) | _check_access() API aware |
| Odoo 18 | Supported | OAuth 2.0 patterns recognized |
| Odoo 19 | Supported | REST API framework patterns |

## Requirements

- Python 3.8 or higher
- No external packages required (uses Python standard library only)
- Compatible with Windows, macOS, and Linux

---

## Author & License

**Author**: TaqaTechno
**Email**: info@taqatechno.com
**GitHub**: https://github.com/taqat-techno
**License**: MIT

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-check`
3. Add your security check to the appropriate script
4. Update SKILL.md with documentation for the new check
5. Test against an Odoo module with known issues
6. Submit a pull request
