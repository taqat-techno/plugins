# RBAC three-layer denial checklist

A role gate is only proven when denial holds at **all three** layers for the same (role × action),
asserted **together**. Checking one layer and inferring the others is how the two failure shapes ship.
This checklist extends the dual-gate (UI + API) in `route-access-matrix` by separating the API edge
from the service/backend layer behind it.

## The three layers

| Layer | What it is | How to observe (read-only / disposable) |
|---|---|---|
| **1. Route / API edge** | The HTTP endpoint the front end calls; the request-handler / middleware authorization at the route boundary | Probe the endpoint directly (empty/minimal body); read the status |
| **2. Service / backend** | The domain/service function, query scope, or DB-row policy that runs *after* the edge — tenant scoping, ownership check, row-level filter | Probe a sibling/related endpoint that reaches the same service; check the returned data scope; probe an id owned by another tenant/user |
| **3. UI** | The rendered affordance — menu link, button, page guard, disabled state | Navigate as the role; observe shown / hidden / disabled / 403-page |

The edge (layer 1) and the service (layer 2) are distinct: an endpoint can authorize the *verb* at the
edge yet fail to scope the *data* in the service (returns another tenant's rows), or vice-versa. Assert
both, not just "the API said 403."

## The assertion: all three deny together

For each (role × restricted action), record one status per layer and require agreement:

```
ROLE = <role>   ACTION = <verb route, e.g. GET /api/records/:id>

  Layer 1 (route/API edge): <401|403 = deny>  |  <200/400/409 = reached handler>
  Layer 2 (service/backend): data scope =      <denied/empty/own-only>  |  <leaked another principal's data>
                             cross-owner probe: GET .../:id-owned-by-other -> <403/404 deny | 200 leak>
  Layer 3 (UI):              <hidden / disabled / 403-page = deny>  |  <shown / content rendered>

  PASS  = all three deny (for a role that must be denied)
  PASS  = all three allow + scope correct (for a role that must be allowed)
  FAIL  = any layer disagrees
```

Use the status semantics from the main skill: 401/403 = blocked; 400/409/422 = the request *passed*
authorization and hit business logic (so for a must-be-denied role that is a FAIL at that layer); 404 is
ambiguous — investigate.

## Mapping disagreements to Shape-A / Shape-B (extended to three layers)

| Pattern | Shape | Severity | Meaning |
|---|---|---|---|
| UI hides; edge allows | **Shape A** | HIGH | Hidden button, open endpoint — classic bypass |
| UI hides; edge denies; **service leaks data on a sibling route** | **Shape A (service-layer)** | HIGH | The gated route is fine but another route reaches the same data with no scope check |
| UI advertises; edge/service deny | **Shape B** | LOW–MED | Dead affordance; UX/trust bug |
| Edge allows the verb; service returns another principal's rows | **Shape A (broken object/tenant scope)** | HIGH | Authz passed but data was not scoped to the caller — IDOR-class |

The most-missed cell is the **service-layer Shape A**: the obvious endpoint is correctly gated, but a
list/search/export/sibling endpoint reaches the same records without re-applying the ownership/tenant
filter. Always probe at least one *related* route that touches the same data, not only the one named in
the ticket.

## Probe sequence (read-only; disposable target only)

1. `runtime-reality-check` passed; identity endpoint confirms the live role (per the main skill).
2. **Layer 1** — probe the gated endpoint directly (empty body). Record status.
3. **Layer 2** — probe a sibling endpoint that reads the same data (list, search, export, by-id with an
   id owned by *another* disposable principal). Record whether the response is scoped (own-only / empty /
   403) or leaks. This is the IDOR / broken-object-level-authorization check.
4. **Layer 3** — navigate as the role; record the UI affordance state.
5. Compare the three; classify any disagreement with the table above.

All probes use empty/minimal bodies and disposable targets (gated by `safe-destructive-testing`); never
send a valid destructive payload to prove a gate.

## Validation checklist

- [ ] Identity endpoint confirmed the live role before probing.
- [ ] Layer 1 (edge) status recorded for the gated action.
- [ ] Layer 2 (service) probed via at least one sibling/related route AND a cross-owner id.
- [ ] Layer 3 (UI) affordance state recorded.
- [ ] All three compared; agreement required for PASS.
- [ ] Any service-layer leak flagged as Shape A (HIGH), even when the edge and UI deny.
- [ ] No valid destructive payload sent; no probe on non-disposable data.
- [ ] No tokens / cookies / PII printed in the captured evidence.

## Output row

```
RBAC THREE-LAYER — <role> × <action>
  Layer 1 route/API edge:  <status> (<deny|reached-handler>)
  Layer 2 service/backend: scope=<own-only|empty|denied|LEAKED>  cross-owner probe=<403/404|200 leak>
  Layer 3 UI:              <hidden|disabled|403-page|shown>
  Agreement:               all-deny | all-allow+scoped | DISAGREE
  Failure shape:           none | Shape A (edge) | Shape A (service-layer) | Shape B
  Verdict:                 PASS | FAIL (<which layer + shape>)
```

## Cross-references

- `verify-identity-and-rbac` — owns the identity proof and the single status-code proof this checklist
  applies at each layer.
- `route-access-matrix` — owns the per-(role × route) sweep and the implicit-method probe; this
  checklist adds the explicit service-layer separation and the cross-owner (IDOR) probe.
- `safe-destructive-testing` — disposable-target gate for every probe here.
- `uat-readiness-report` — any service-layer Shape A is a HIGH row.
