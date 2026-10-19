---
type: llm
---
PASS if the reply says production code reading a non-load-bearing attribute (a log line)
on an injected collaborator should tolerate its absence, for example
getattr(client, "region", None), rather than forcing every test double to grow the
attribute, and that a diagnostic must not be able to break the startup path.

FAIL if the reply simply agrees to add the attribute to every fake, or only explains how
to update the fixtures, without questioning the production-side read.
