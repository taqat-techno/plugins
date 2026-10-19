---
type: llm
---
PASS if the reply states that useService('rpc') fails because rpc is no longer a registered service in Odoo 19 (it is not available in frontend/public components), and replaces it with either the rpc function imported from @web/core/network/rpc or a fetch-based JSON-RPC helper that sends the CSRF token, calling the user's own controller route declared with auth='public' (type='jsonrpc' on 19).
FAIL if the reply suggests continuing to use useService('rpc') in some other form, routes anonymous visitors through the orm service or /web/dataset/call_kw, tells the user to import a backend-only session or service without addressing why rpc is unavailable, or gives generic fetch/AJAX advice with no Odoo-specific explanation.
