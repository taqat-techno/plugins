---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I added a record rule and tightened the ACL on stock.picking in our custom Odoo module so warehouse clerks only see their own warehouse. I ran my module's tests as admin with -u my_module and they are all green. Other modules in the same repo also use stock.picking. Is that enough testing to call this done?
