---
type: llm
---
PASS if the reply uses a fresh browser context or cleared storage per role, logs in, visits every menu item
that role can see, captures a screenshot plus console and network for each page, and ends with a
cross-role consistency check of what each role could see.
FAIL if the reply reuses one logged-in browser session across roles, or captures no per-page evidence, or
skips any comparison between roles.
