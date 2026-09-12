---
type: llm
---
PASS if the reply states that the rpc service was removed from frontend/public components in Odoo 19, so useService('rpc') is not available there, and recommends replacing it with a manual JSON-RPC style helper built on fetch that handles the CSRF token itself.
FAIL if the reply suggests continuing to use useService('rpc') in some other form, tells the user to import a backend-only session or service without addressing why it is unavailable, or gives generic fetch/AJAX advice without naming the Odoo 19-specific removal of the rpc service from public components.
