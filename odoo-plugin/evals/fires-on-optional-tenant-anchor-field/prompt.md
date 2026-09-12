---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

In my multi-tenant Odoo install, each order record currently gets its company_id through a related field pointing at its parent contract's company_id, stored on the order. I'm about to refactor so a contract is no longer required on every order. Anything I should worry about before I do that?
