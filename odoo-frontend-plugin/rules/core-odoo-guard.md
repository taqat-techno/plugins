# Core Odoo Guard

NEVER modify files under `odoo/` or `odoo/addons/` directories. All customizations MUST go in `projects/{PROJECT}/{module}/`. Use model/view inheritance instead of direct modifications.

This applies to:
- Python models (use `_inherit` to extend)
- XML views (use `<xpath>` to modify)
- SCSS variables (override via theme's `primary_variables.scss`)
- JavaScript (extend via `publicWidget` or Owl inheritance)
