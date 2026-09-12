---
type: llm
---
PASS if the reply identifies that the bypass header was injected globally instead of
being scoped to only the protected host, causing the CORS preflight on cross-origin API
calls to reject the extra header, and recommends host-scoped route interception instead
of a global header.
FAIL if the reply gives generic CORS-fix advice, such as adding
Access-Control-Allow-Origin on the server, disabling CORS, or using a proxy, without
naming the global-vs-host-scoped header injection cause.
