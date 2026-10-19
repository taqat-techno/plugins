---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Our importer matches incoming payments to customer accounts. To be forgiving we lowercase
and strip punctuation from the reference before comparing, and when exactly one account
matches the normalised reference we bind the payment to it automatically. Two accounts,
"ACME-01" and "acme 01", now exist. Is this matching design fine to ship?
