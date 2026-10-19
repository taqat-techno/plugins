---
type: llm
---
PASS if the reply treats this as a local environment problem and gives a structured
diagnostic path: confirm which config file and scope the server was added to and that the
session was restarted or reloaded after the edit, check that the command or binary
resolves on PATH for the process that launches it, and look at the MCP status or logs for
a startup error, without asking the user to paste any secret values.

FAIL if the reply gives only a generic guess (reinstall Claude Code) with no step that
checks the config location, a restart or reload, or the server's own startup output.
