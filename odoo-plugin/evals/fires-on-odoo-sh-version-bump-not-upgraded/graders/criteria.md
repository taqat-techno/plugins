---
type: llm
---
PASS if the reply explains that Odoo.sh upgrades a module only when its manifest version
changes (so an unchanged or identical version, including one brought in by the merge, deploys
the files without loading them), tells the user to bump the version, and proves the deploy by
asking the instance (ir.module.module latest_version / write_date, or the field's presence in
the database) rather than trusting the green build or an HTTP 200.
FAIL if it only suggests clearing the browser cache, restarting, or re-pushing without a
version check, or treats the green build as proof of the deploy.
