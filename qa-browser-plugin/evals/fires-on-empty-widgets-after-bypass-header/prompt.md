---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

For QA against our protected staging deployment, I set our preview-bypass secret as a
header on every request the browser context makes. Now the page shell loads fine, but
every data widget on the dashboard stays empty, and the console is full of errors
saying a request header is not allowed by Access-Control-Allow-Headers. What is going
on?
