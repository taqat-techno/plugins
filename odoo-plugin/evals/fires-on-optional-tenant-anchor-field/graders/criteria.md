---
type: llm
---
PASS if the reply warns that making the contract relation optional lets the related company_id field become NULL, explains that a nullable tenant anchor silently disables isolation (for example an ir.rule NULL-escape branch becoming world-visible, or cross-tenant reads/writes no longer being blocked), and recommends re-anchoring company_id to a new required source in the SAME change rather than leaving it nullable until a later migration.
FAIL if the reply only raises generic nullable-field or None-handling concerns (add a null check, handle None in your code) without naming the tenant-isolation consequence, or suggests it is fine to re-anchor the field in a follow-up change.
