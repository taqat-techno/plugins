---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Can you sanity check our FastAPI auth before we ship? We decode tokens with payload = jwt.decode(token, settings.secret_key, options={'verify_exp': False}) using python-jose, and the token travels as ?token= in the URL for our websocket and download links. Anything risky here?
