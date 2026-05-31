---
name: host-scoped-auth-headers
description: Host-scoped injection rule for browser-QA auth and bypass headers (preview-bypass secrets, tunnel keys, proxy / Access tokens) used to reach a protected preview or staging deployment. Owns the global-vs-host-scoped decision, the CORS-preflight leak symptom and its route-scoped fix, the bypass-secret sourcing rule, and the edge-401 primitive choice. Activates when adding any custom auth or bypass header to a browser context so QA can load a protected deployment, especially when page chrome renders but every data widget is empty and the console floods with preflight header-not-allowed errors.
version: 0.1.0
last_reviewed: 2026-05-31
owns:
  - host-scoped header injection rule (route-scope the header to the protected host only)
  - global-vs-host-scoped decision table
  - CORS-preflight leak symptom -> cause -> fix mapping
  - bypass-secret sourcing rule (adapter input from env / local, gitignored, never printed)
  - edge-401 primitive choice (scoped automation-bypass secret over account access or disabling protection)
defers_to:
  - console-and-network-capture (the CORS preflight signal in the network panel)
  - safe-destructive-testing (credentials-must-be-gitignored, production-URL refusal)
  - runtime-reality-check (env identity confirms which host you are actually on)
user_invocable: false
---

# host-scoped-auth-headers

## Purpose

Reaching a protected preview or staging deployment for QA usually needs one extra header — a platform preview-bypass secret, a tunnel key, or a proxy / Access token. The trap is injecting that header globally on the browser context. A global header rides along on EVERY request, including cross-origin API XHRs, whose CORS preflight rejects the unknown header. The page shell renders, but every data widget is empty. This skill makes the header host-scoped so cross-origin calls stay untouched.

## When to use

Activate when:

- Adding any custom auth or bypass header to a browser context to load a protected preview / staging URL.
- Page chrome renders but every data widget is empty.
- The console floods with preflight errors like "Request header field X is not allowed by Access-Control-Allow-Headers".
- An edge-protected preview returns 401 and you are deciding how to authenticate the automation.

Skip when the target is unprotected (no extra header needed) or when the only auth is same-origin cookie-based login (no custom header to scope).

## Inputs (adapter)

1. **Protected host pattern** — the exact host (or host glob) of the protected deployment the bypass header is FOR. This is the scope boundary. Never `*` / all-hosts.
2. **Bypass-secret source** — where the secret value is read from at runtime: an environment variable or a gitignored local file. Never a literal in the skill, command, or committed config. Never printed to logs or evidence.
3. **Header name** — the exact header the platform expects (named by the platform's docs; the skill does not assume one).
4. **Cross-origin API host(s)** — the host(s) the front end calls for data. These MUST NOT receive the bypass header. Used to verify the scope is correct.

## Read-only investigation steps

1. **Confirm which host you are on.** Verify env identity (defer to `runtime-reality-check`) so the scope pattern matches the real protected host, not a guess.
2. **Reproduce the empty-widget symptom.** Load the protected URL. Does chrome render while data widgets stay empty?
3. **Read the network panel.** Filter for failed XHR / fetch. Are the failing requests cross-origin (a different host than the page)? Are they failing at the OPTIONS preflight stage? (defer to `console-and-network-capture` for the capture window.)
4. **Read the console.** Look for "header field ... is not allowed by Access-Control-Allow-Headers" or "preflight ... did not succeed". One such line on a cross-origin request is the global-leak signature.
5. **Check the current injection scope.** Is the header configured per-route (host-matched) or globally on the whole context? Global is the smell.

## Decision framework

### Global vs host-scoped injection

| Approach | Applies header to | Cross-origin API calls | Verdict |
|---|---|---|---|
| Global request-header injection | EVERY request the context makes | Preflight rejects unknown header -> data calls fail | WRONG — causes empty-widget symptom |
| Host-scoped route interception | Only requests whose host matches the protected host pattern | Untouched — preflight stays clean | CORRECT |

Route-scope the header to the protected host only, using the browser-MCP / Playwright per-route interception keyed by a host pattern:

```
# Illustrative — not required. Conceptual shape, not literal API:
intercept route WHERE request.host MATCHES <protected-host-pattern>:
    add header <header-name> = <secret-from-adapter-source>
    continue
# All other hosts (the cross-origin API) get NO added header.
```

```
Page host  ──GET document──►  protected-host        (header added ✓)
Front end  ──XHR /api──────►  cross-origin api host  (NO header → preflight clean ✓)
```

### CORS-preflight leak: symptom -> cause -> fix

| Symptom | Cause | Fix |
|---|---|---|
| Chrome renders, every data widget empty | Global header leaks onto cross-origin API XHRs | Host-scope the header to the protected host only |
| Console floods "header field X not allowed by Access-Control-Allow-Headers" | The unknown bypass header trips the cross-origin server's CORS preflight | Remove header from cross-origin requests via route scoping |
| OPTIONS preflight requests failing in network panel | Custom header forces a preflight that the API host does not permit | Scope so the API host's requests carry no custom header |

### Edge-protected preview returning 401

| Option | Use it? | Why |
|---|---|---|
| Platform's purpose-built automation-bypass primitive (a scoped bypass secret) | YES | Designed for automation; scoped; revocable; touches only the protected edge |
| Logging in with a real account | NO | Broader access than QA needs; couples QA to credential lifecycle |
| Disabling protection on the environment | NEVER | Exposes a shared environment to everyone for the duration |

Use the platform's scoped automation-bypass secret. Read it from the adapter source (env / gitignored local). Inject it host-scoped per the rule above.

### Where the secret lives

| Location | Allowed? |
|---|---|
| Environment variable read at runtime | YES |
| Gitignored local file read at runtime | YES |
| Hardcoded in skill / command / agent text | NEVER |
| Committed config or checked-in fixture | NEVER |
| Printed to console, logs, or evidence report | NEVER |

## Safety gates

- **Never** inject an auth or bypass header globally on the browser context — always host-scope it to the protected host pattern.
- **Never** hardcode the bypass secret anywhere in the repo; read it from the adapter source.
- **Never** print, log, or paste the secret value into evidence, reports, or chat.
- **Never** apply the bypass header to cross-origin API hosts — that is the bug.
- **Never** disable edge protection on a shared environment to "make it load."
- **Never** commit the secret source file; it must be gitignored (defer to `safe-destructive-testing`).
- **Never** widen the host pattern to `*` or all-hosts to "fix" a no-match — fix the pattern instead.

## Validation checklist

Before relying on a bypass-header setup for a QA pass:

- [ ] Header is injected only on requests matching the protected host pattern.
- [ ] Cross-origin API XHRs carry NO added bypass header (verified in network panel).
- [ ] No "header not allowed by Access-Control-Allow-Headers" lines remain in the console.
- [ ] At least one real data widget loads with non-empty content.
- [ ] Secret is read from the adapter source (env / gitignored local), not a literal.
- [ ] Secret value appears nowhere in logs, evidence, or committed files.
- [ ] For an edge 401, the platform's scoped bypass primitive was used (not account login, not disabling protection).
- [ ] Env identity confirmed so the host pattern matches the real protected host.

## Output format

Emit a HEADER-SCOPING PLAN block (secret value redacted — show the SOURCE, never the value):

```
HEADER-SCOPING PLAN
  Protected host pattern: <host-or-glob>
  Header name:            <header-name>
  Secret source:          <env-var-name | gitignored-local-file>   (value: REDACTED)
  Injection scope:        host-scoped (route interception matching protected host only)
  Cross-origin API hosts: <host(s)>  → NO bypass header
  Edge-401 strategy:      scoped automation-bypass primitive (not account login, not disable protection)
  Verification:           network panel shows clean preflight on API hosts; data widgets non-empty
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Global `setExtraHTTPHeaders` / context-wide header | Header rides on cross-origin XHRs; preflight rejects it; data widgets empty | Host-scoped route interception matching the protected host only |
| Widening scope to `*` when no host matched | Reintroduces the global leak | Fix the host pattern to match the real protected host |
| Hardcoding the bypass secret in a command file | Leaks the secret into version control | Read from env or gitignored local file |
| Pasting the secret into the evidence report | Discloses a live credential in a shared artifact | Record the SOURCE name; value stays REDACTED |
| Logging in with a personal account to bypass 401 | Grants QA more access than needed; couples to credential lifecycle | Use the platform's scoped automation-bypass primitive |
| Disabling protection on staging so it loads | Exposes a shared environment to everyone | Keep protection on; bypass with a scoped secret, host-scoped |
| Blaming the API "CORS config" for empty widgets | The API is fine; the global header forced the preflight | Stop sending the custom header to cross-origin hosts |

## Portability rationale

The rule is platform-agnostic. It does not depend on any specific:

- Hosting / edge platform or its bypass-secret name (named via the adapter, not assumed).
- Browser automation library — any per-route interception keyed by host works (browser MCP, Playwright, or equivalent).
- Secret store — env var or gitignored local file; the skill specifies the contract, not the vault.

Every project-specific value (protected host, header name, secret source, API hosts) is an adapter input. Behavior never depends on a particular company, deployment, or URL.

## Cross-references

- `console-and-network-capture` — provides the CORS-preflight failure signal (failed OPTIONS, header-not-allowed lines) this skill reacts to, plus the redaction rules that keep the secret out of evidence.
- `safe-destructive-testing` — owns the credentials-must-be-gitignored rule and production-URL refusal that this skill's secret sourcing defers to.
- `runtime-reality-check` — confirms which host / environment you are actually on, so the host pattern matches reality.
- `browser-qa-discipline` — status vocabulary for reporting a blocked-by-auth check.
