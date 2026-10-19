---
type: llm
---
PASS if the reply extracts the file key from the URL path and converts the node-id from 12-34 to 12:34, then
fetches the frame through Figma MCP read tools (design context, screenshot, variable definitions)
and maps the Figma variables onto the project's existing tokens instead of hard-coding values.
FAIL if the reply ignores the node id (or passes it with the hyphen unchanged), suggests exporting images or
copying CSS by hand, or never maps Figma variables onto the project's tokens.
