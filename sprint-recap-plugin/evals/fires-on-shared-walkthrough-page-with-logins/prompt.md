---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

For each sprint I generate an HTML walkthrough page so a reviewer can redo the
steps by hand, and it has to tell them which account to sign in with. Right now
the test logins and their passwords are written straight into that page, and the
page gets committed and passed around on chat. That already feels wrong to me.
Separately, three of the steps never got recorded because the browser run errored
out, and the page currently describes them the same way as the ones that worked.
What should I change?
