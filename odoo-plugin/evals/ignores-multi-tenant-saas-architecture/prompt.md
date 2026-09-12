---
max_turns: 8
allowed_tools: [Skill]
tags: [routing]
---

In a generic multi-tenant SaaS app I'm building with Node.js and Postgres, what's a common way to isolate tenant data: separate databases per tenant, separate schemas, or a shared table with a tenant_id column? What are the trade-offs?
