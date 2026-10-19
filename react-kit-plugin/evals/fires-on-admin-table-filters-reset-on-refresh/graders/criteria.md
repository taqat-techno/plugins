---
type: llm
---
PASS if the reply makes the URL query string the source of truth for filters, sort and page (read on load,
written on change), keeps pagination on the server, and treats an error state separately so the
paginator or result count is not shown under a failed request.
FAIL if the reply suggests persisting filters in localStorage or global state only, or never puts filters,
sort and page into the URL.
