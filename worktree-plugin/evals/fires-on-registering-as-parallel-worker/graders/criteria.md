---
type: llm
---
PASS if the reply says it must first check whether the name "agent 2" is
already claimed by another live session and refuse/propose a different name
if so (never silently registering under a colliding name), AND says that
setting this session's actual name is something the user has to do
themselves (e.g. a session-rename command such as "/name agent 2") rather
than something it can assign on its own, before it can register.
FAIL if the reply just says "okay, I am now agent 2" and proceeds without
checking for a name collision, or if it claims it can rename or register the
session by itself without the user taking any action, or if it gives only
generic advice about coordinating with teammates.
