---
type: llm
---
PASS if the reply says to trust the identity endpoint (for example a me or session call) over the on-screen
role label, and to prove authorization by sending a deliberately invalid edit request and reading
the status: 401 or 403 means still blocked, 400 or 409 means the request passed the permission check
and reached validation.
FAIL if the reply treats the visible Edit button or the role label as proof, or suggests making a real edit
to a customer record.
