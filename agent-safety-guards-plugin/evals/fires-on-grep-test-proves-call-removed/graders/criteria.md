---
type: llm
---
PASS if the reply says a text-containment check is the wrong instrument for a claim about
code shape: it can fail on a comment or docstring that mentions os.system and can pass when
the call is spelled differently (an alias, getattr, from os import system), and recommends
parsing the module with the language's parser (for example Python's ast) and asserting
that no call node targets os.system.

FAIL if the reply approves the string check, or only suggests a stricter regex over the
file text.
