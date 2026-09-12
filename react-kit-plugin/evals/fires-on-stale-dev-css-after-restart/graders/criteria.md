---
type: llm
---
PASS if the reply explains that in dev mode the CSS chunk URL is stable and
cacheable across server restarts (unlike a production build, which
content-hashes the CSS URL), so the browser tab can keep applying a
stylesheet that came from an already-killed dev server even after a restart
and a hard refresh, and it recommends verifying this by diffing the actually
applied stylesheet (e.g. document.styleSheets) against a fresh no-store fetch
of the served CSS, or forcing a fresh fetch (cache-busting the stylesheet
link, or restarting the dev server on a different port).
FAIL if the reply only suggests generic cache-clearing steps (clear browser
cache, hard refresh again, incognito window) without naming why a same-port
restart does not fix it, or if it blames the CSS source code itself instead
of the stale-applied-stylesheet cause.
