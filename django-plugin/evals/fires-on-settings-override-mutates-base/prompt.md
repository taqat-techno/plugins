---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

In my Django project, dev.py starts with from .base import * and then does LOGGING['loggers']['django']['level'] = 'DEBUG'. Now production (which also does from .base import * in prod.py) is logging at DEBUG too, but only when both modules get imported in the same process, like in a management script. Why would changing dev settings leak into prod?
