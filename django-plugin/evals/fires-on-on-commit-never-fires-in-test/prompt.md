---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My Django view sends a webhook inside transaction.on_commit(lambda: send_webhook(order.id)). In production it works, but in my test (a normal django.test.TestCase using the test client) the mocked send_webhook is never called, so the assertion fails. Why does the callback never run in tests?
