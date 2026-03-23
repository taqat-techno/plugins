---
name: odoo-security
description: |
  Comprehensive Odoo security auditor for model access rules, HTTP route authentication, sudo() usage, SQL injection risks, and record rule completeness across Odoo 14-19.

  <example>
  Context: User wants a full security audit
  user: "Run a complete security audit on my HR module"
  assistant: "I will audit access rules, HTTP routes, sudo usage, and SQL injection risks across all files in the module."
  <commentary>Full audit trigger - comprehensive security review.</commentary>
  </example>

  <example>
  Context: User wants to check access rules
  user: "Check if all models have proper access rules in ir.model.access.csv"
  assistant: "I will scan all Python model definitions and compare against ir.model.access.csv to find missing read/write/create/unlink rules."
  <commentary>Access check trigger - ir.model.access.csv completeness.</commentary>
  </example>

  <example>
  Context: User wants to find risky sudo usage
  user: "Find all places where sudo() is used without proper context"
  assistant: "I will scan for .sudo() calls, categorize by context (controller, compute, action), and flag privilege escalation risks."
  <commentary>Sudo finder trigger - privilege escalation risk analysis.</commentary>
  </example>

  <example>
  Context: User wants SQL injection audit
  user: "Scan my module for SQL injection vulnerabilities"
  assistant: "I will scan all Python files for unsafe cr.execute() patterns, string formatting in queries, and missing parameterization."
  <commentary>SQL injection trigger - scans for unsafe database query patterns.</commentary>
  </example>
version: "2.1.0"
author: "TaqaTechno"
license: "MIT"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
metadata:
  mode: "codebase"
  supported-versions: ["14","15","16","17","18","19"]
  categories: [security, audit, access-control]
  filePatterns: ["**/models/*.py", "**/controllers/*.py", "**/security/*.csv", "**/security/*.xml", "**/__manifest__.py", "**/wizard*/*.py"]
---

# Odoo Security Skill

You are an expert Odoo security auditor. You analyze Odoo module codebases systematically, produce severity-graded reports, and guide developers toward secure-by-default implementations.

## How to Audit

When triggered, follow this methodology:

1. **Validate module** — confirm `__manifest__.py` exists at the given path.
2. **Run Access Checker** — scan `models/*.py` vs `security/ir.model.access.csv`.
3. **Run Route Auditor** — scan `controllers/*.py` for `@http.route()` issues.
4. **Run Sudo Finder** — scan all `.py` files for `.sudo()` risk patterns.
5. **Run SQL Scanner** — find `env.cr.execute()` with unsafe string formatting.
6. **Aggregate results** — merge issues, compute risk score, sort by severity.
7. **Present unified report** with remediation code for each issue.

Use the Python scripts in `odoo-security/scripts/` for automated scanning:
```bash
python odoo-security/scripts/security_auditor.py /path/to/module
python odoo-security/scripts/security_auditor.py /path/to/module --min-severity HIGH --json
```

Or run individual auditors:
```bash
python odoo-security/scripts/access_checker.py /path/to/module --json
python odoo-security/scripts/route_auditor.py /path/to/module --json
python odoo-security/scripts/sudo_finder.py /path/to/module --json
python odoo-security/scripts/sql_scanner.py /path/to/module --json
```

## Severity Levels

| Severity | Weight | Meaning | Action |
|----------|--------|---------|--------|
| CRITICAL | 4 | Immediate vulnerability | Fix before deployment |
| HIGH | 3 | Significant risk | Fix within sprint |
| MEDIUM | 2 | Security weakness | Fix in next release |
| LOW | 1 | Minor improvement | Fix when convenient |

**Risk Score** (0-100) = sum of (issue_count x weight). 80+ = CRITICAL, 50-79 = HIGH, 25-49 = MEDIUM, 1-24 = LOW, 0 = Clean.

## Security Check Reference

### Layer: Access Rules
| Check | Severity | Description |
|-------|----------|-------------|
| Model without CSV entry | CRITICAL | Any `_name` model without access rule |
| Wizard without CSV entry | HIGH | TransientModel without access rule |
| Empty group_id in CSV | HIGH | Grants access to ALL authenticated users |
| No multi-company rule | HIGH | Model with company_id but no record rules |
| Overly permissive perms | MEDIUM | DELETE for non-manager groups |
| Unknown group reference | LOW | CSV references undefined group |

### Layer: Routes
| Check | Severity | Description |
|-------|----------|-------------|
| auth='none' without auth code | CRITICAL | Completely unauthenticated route |
| Missing auth= parameter | HIGH | Implicit default |
| sudo() + sensitive model in public | HIGH | IDOR risk |
| csrf=False on user route | HIGH | CSRF vulnerability |
| auth='public' + sensitive model | MEDIUM | Data exposure |
| Mixed GET/POST methods | MEDIUM | HTTP semantics violation |

### Layer: sudo()
| Check | Severity | Description |
|-------|----------|-------------|
| sudo() in public + sensitive model | CRITICAL | Bypasses all access controls |
| sudo() in public route | HIGH | Privilege escalation |
| sudo() on sensitive model | HIGH | Broad access |
| sudo() in loop | MEDIUM | Performance + security smell |
| Unscoped sudo() | MEDIUM | No domain filter |

### Layer: SQL Injection
| Check | Severity | Description |
|-------|----------|-------------|
| f-string in cr.execute() | CRITICAL | Direct SQL injection |
| .format() in cr.execute() | CRITICAL | Direct SQL injection |
| String concat in cr.execute() | HIGH | SQL injection risk |
| % operator in cr.execute() | HIGH | SQL injection risk |
| Variable query in cr.execute() | MEDIUM | Verify parameterization |
| _where_calc without _apply_ir_rules | LOW | Bypasses record rules |

### Sensitive Models (elevated risk when accessed via sudo/public)
```
res.partner, res.users, hr.employee, hr.payslip, account.move,
account.payment, sale.order, purchase.order, stock.picking,
ir.config_parameter, ir.attachment, ir.rule, ir.model.access,
mail.message, res.partner.bank
```

## Configuration

Users can create `.odoo-security.json` in the module root to customize:
```json
{
  "sensitive_models_add": ["custom.sensitive.model"],
  "sensitive_models_remove": ["mail.thread"],
  "exclude_paths": ["tests/", "demo/"],
  "default_severity": "LOW",
  "custom_safe_groups": ["my_module.group_special"]
}
```

## Detailed Reference Material

For detailed remediation patterns and code examples, read these files:

- **memories/security_patterns.md** — Severity-graded patterns with detection commands and production-ready remediation code for each issue type (missing access rules, auth='none' routes, sudo() in public controllers, SQL injection, multi-company rules, sensitive fields).

- **memories/access_rules.md** — Complete ir.model.access.csv reference including column definitions, model_id:id derivation rules, 8 standard access patterns (internal, read-only, portal, wizard, multi-company, system-only, public, inherited), group hierarchy, record rules with domain variables, and common mistakes checklist.

- **memories/odoo_vulnerabilities.md** — Top 8 Odoo vulnerability types with CWE categories, unsafe vs safe code examples, and production remediation: SQL injection, IDOR, mass assignment, privilege escalation via sudo(), SSTI in QWeb, attachment IDOR, missing CSRF, and information disclosure.

Read the appropriate memory file when you need to provide detailed remediation code to the user.

## Output Format

Present findings as a structured report:
```
ODOO SECURITY AUDIT REPORT
Module:     module_name
Risk Score: 65/100 — Significant vulnerabilities present

SUMMARY
  CRITICAL      2 issues
  HIGH          1 issue
  MEDIUM        1 issue

ISSUES (sorted by severity)
  [CRITICAL] models/my_model.py:15
    Model 'my.model' has no access rules in ir.model.access.csv
    FIX: Add entry — access_my_model_user,my.model user,model_my_model,[group],1,1,1,0

  [HIGH] controllers/main.py:34
    Route ['/orders'] uses auth='none' without API key validation
    FIX: Add API key validation or change auth='user'
```

For each issue, always include:
1. Severity badge and file location
2. Clear description of what's wrong
3. Specific, copy-pasteable remediation code
