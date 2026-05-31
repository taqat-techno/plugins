---
name: verify-identity-and-rbac
description: Live identity and authorization PROOF during browser QA — the part static code review cannot do. Activates when verifying who is actually logged in, whether a permission change took effect at runtime, or whether the UI gate matches the API gate for a given role. Owns trusting the identity endpoint over on-screen role labels, the status-code proof method that turns a pre-fix 403 into a post-fix 400 without crafting a destructive payload, and reporting the two RBAC failure shapes (UI hides but API allows; API denies but UI advertises). Defers per-route enumeration to route-access-matrix and the disposable-data gate to safe-destructive-testing.
version: 0.1.0
last_reviewed: 2026-05-31
owns:
  - identity-endpoint-over-label rule (trust auth/me-style call, not decorative shell role text)
  - status-code proof method (401/403 = blocked; 400/409 = authorized, reached business logic)
  - the 403-to-400 transition as proof a gate opened (without a destructive payload)
  - Shape-A reporting — UI hides but API allows (the dangerous one)
  - Shape-B reporting — API denies but UI advertises the action
  - the IDENTITY+RBAC PROOF output block (claimed / verified / probe / status / verdict)
defers_to:
  - route-access-matrix (the per-role × per-route enumeration walk)
  - safe-destructive-testing (the disposable-data / non-production gate)
  - runtime-reality-check (env + build identity must be confirmed first)
  - console-and-network-capture (capturing the actual response status)
  - react-kit data-fetching-states (the UI states these statuses should produce)
user_invocable: false
---

# verify-identity-and-rbac

## Purpose

A green-looking admin shell proves nothing. The role badge in the corner is decorative text; the session it claims to describe may be stale, impersonated, or simply wrong. This skill owns the live, runtime proof of two questions a static read of the code can never answer: *who is the server treating me as right now*, and *did the permission change actually take effect*. It proves authorization by reading status codes, not by trusting screens — and it does so without ever crafting a destructive payload.

## When to use

Activate when:

- Verifying which identity / role the live session actually has.
- Confirming an RBAC change took effect (a role gained or lost access; a permission predicate was edited).
- Checking whether a UI gate (hidden button, blocked page) is backed by a real API gate.
- Investigating a report that a user "can see / do something they shouldn't" or "can't do something they should."
- Re-verifying after a deploy that touched auth, roles, or permissions.

Defer the full (role × route) sweep to `route-access-matrix`. This skill owns the identity check and the single status-code proof; the matrix skill owns the enumeration.

## Inputs (adapter)

Every value below is a NAMED adapter input. None is hardcoded; the skill's behavior never depends on any specific value.

1. **Identity endpoint** — the authoritative auth/identity call that returns the live session principal and its role(s) (an auth/me-style request). The skill reads it; the project names it.
2. **Role list** — the set of roles defined in the project, with which the on-screen claim is compared.
3. **Restricted routes** — the routes / actions that are supposed to be gated, supplied by the user or read from the project's permission matrix.
4. **Disposable target** — the non-production record / tenant against which any probe runs (classified by `safe-destructive-testing`).

## Read-only investigation steps

1. **Confirm reality first.** `runtime-reality-check` must have passed — correct env, correct build. A permission "fix" verified against a stale deploy proves nothing.
2. **Read the identity endpoint.** Call the adapter's identity endpoint and record the verified role(s). This is the source of truth for "who am I."
3. **Read the on-screen claim.** Note the role label the shell renders. Compare to step 2. A mismatch is itself a finding (see the auth/me-over-label check).
4. **Locate the gate under test.** For the restricted route/action, find the UI affordance (present? hidden? disabled?) and the API call that backs it.
5. **Probe by status, not by mutation.** Issue the gated request against a disposable target and read the status code only. Do NOT supply a valid destructive payload — an empty or minimal body is enough; the status code tells the whole story (see the decision framework).
6. **Classify the failure shape** if UI and API disagree.

All steps are read-only with respect to real data. The only request that touches the server is a status probe against a disposable target, gated by `safe-destructive-testing`.

## Decision framework

### Status-code semantics (the proof method)

The probe never needs to succeed. The status code alone distinguishes "the gate is still closed" from "the gate opened and I reached business logic."

| Status | Meaning for authorization | Verdict |
|---|---|---|
| 401 Unauthorized | Not authenticated (no / invalid session) | Still BLOCKED — at the auth layer |
| 403 Forbidden | Authenticated but role not permitted | Still BLOCKED — at the authz layer |
| 400 / 409 / 422 | Authorized; request reached business logic and was rejected on data (missing field, conflict, validation) | AUTHORIZED — the gate is OPEN |
| 404 | Ambiguous — route absent, OR resource hidden, OR a deliberate "deny-by-hide" | INCONCLUSIVE — investigate before concluding |
| 200 / 201 | Authorized AND succeeded | AUTHORIZED — gate open (and, if a mutation, it happened — only acceptable on disposable data) |

The key inference, used to prove an RBAC change without a destructive payload:

```
Before fix:  POST <gated route>  (empty body)  ->  403 Forbidden        gate CLOSED
After  fix:  POST <gated route>  (empty body)  ->  400 "field required"  gate OPEN
                                                    ^^^
             reached validation = passed the authz check = the change took effect.
             No valid/destructive payload was ever sent.
```

A 403 turning into a 400 is positive proof the authorization layer now lets the role through — the business logic rejected the *empty* body, which it could only do *after* admitting the request. This is the entire point: you prove authorization moved without ever risking a real write.

### auth/me-over-label check

```
on-screen role label   ──compare──▶   identity endpoint role
        (decorative)                        (authoritative)

  match     ──▶  identity confirmed; proceed to gate check
  mismatch  ──▶  FINDING: shell renders a role the live session does not hold
                 (stale token, cached profile, impersonation leak, or wrong-account)
```

Rule: the identity endpoint wins, always. Admin shells render role text from cached profile data, feature flags, or build-time config — none of which is the live session role. Never report "logged in as X" on the strength of a badge.

### Shape-A / Shape-B detection

When the UI gate and the API gate disagree, name the shape:

| Shape | UI says | API says | Severity | Meaning |
|---|---|---|---|---|
| **Shape A** | hidden / blocked | allows (200 / 400 / 409) | HIGH — security hole | Hiding the button is not a control. Anyone who knows the route bypasses the UI and the server obeys. |
| **Shape B** | shows / advertises | denies (401 / 403) | LOW-MED — UX / trust bug | Dead affordance. The user clicks and is rejected; erodes trust, generates support load. |

Shape A is the dangerous one and must be flagged as a security finding, not a UX nit. Shape B is a UX/correctness bug. Agreement (both deny, or both allow for a permitted role) is the only passing outcome.

## Safety gates

- **Never** run a probe against production or any non-disposable target — defer the environment/target classification to `safe-destructive-testing`.
- **Never** send a valid destructive payload to prove a gate opened; an empty / minimal body plus the status code is sufficient.
- **Never** assume a non-200 means "blocked" — a 400 / 409 / 422 means *authorized* and rejected by a business rule, which is the opposite conclusion.
- **Never** treat 404 as proof of denial; it is ambiguous (absent route vs deny-by-hide) and must be investigated.
- **Never** report the logged-in role from the on-screen label; report only what the identity endpoint returns.
- **Never** print tokens, session cookies, auth headers, or other secret values when capturing the probe.
- **Never** duplicate the per-(role × route) enumeration here — that is owned by `route-access-matrix`.

## Validation checklist

- [ ] `runtime-reality-check` passed (correct env + build) before any probe.
- [ ] Identity endpoint was called; verified role recorded.
- [ ] On-screen role label compared to the verified role; mismatch surfaced if any.
- [ ] Probe ran against a disposable target classified by `safe-destructive-testing`.
- [ ] Probe used an empty / minimal body — no valid destructive payload.
- [ ] Status code read and mapped via the semantics table (401/403 vs 400/409 vs 404).
- [ ] If a change was under test, the before→after status transition is recorded as the proof.
- [ ] UI gate vs API gate compared; failure classified as Shape A or Shape B when they disagree.
- [ ] No secrets, tokens, or session values printed in the evidence.

## Output format

Emit one IDENTITY+RBAC PROOF block per identity/gate verified:

```
IDENTITY+RBAC PROOF — <route or action under test>
  Claimed role (UI label):   <role text rendered by the shell>
  Verified role (identity):  <role returned by the identity endpoint>
  Identity match:            MATCH | MISMATCH (<note>)
  Target:                    <disposable target id> (non-production)
  Probe:                     <METHOD> <route>   body: <empty | minimal>
  Status:                    <code> (<status meaning from table>)
  Before → after (if change under test):  403 → 400  (gate OPENED)
  UI gate:                   shown | hidden | disabled
  API gate:                  allows | denies
  Failure shape:             none | Shape A (UI hides, API allows) | Shape B (API denies, UI advertises)
  Verdict:                   AUTHORIZED | BLOCKED | INCONCLUSIVE
```

Example (illustrative — not required):

```
IDENTITY+RBAC PROOF — POST /api/v1/records (create)
  Claimed role (UI label):   Manager
  Verified role (identity):  Viewer
  Identity match:            MISMATCH (shell badge stale; session is Viewer)
  Target:                    sandbox tenant #qa-7 (non-production)
  Probe:                     POST /api/v1/records   body: empty
  Status:                    403 (Forbidden — authz layer)
  Before → after:            n/a (no change under test)
  UI gate:                   shown
  API gate:                  denies
  Failure shape:             Shape B (API denies, UI advertises the action)
  Verdict:                   BLOCKED
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Reporting the logged-in role from the on-screen badge | The badge is decorative; it may be cached, stale, or impersonated | Read the adapter's identity endpoint; report that role |
| Treating a 400 / 409 / 422 as "still blocked" | Those codes mean the request *passed* authorization and hit business logic — the gate is OPEN | Map 400/409/422 to AUTHORIZED; only 401/403 mean blocked |
| Sending a valid destructive payload to prove the gate opened | Risks a real mutation just to read an access result | Send an empty body; the status code proves authorization |
| Concluding "fixed" from a green UI after a permission change | UI hiding is not enforcement; the API may still allow | Probe the API and read the before→after status transition |
| Calling 404 a denial | 404 is ambiguous (absent route vs deny-by-hide) | Mark INCONCLUSIVE and investigate the route's existence |
| Filing Shape A (UI hides, API allows) as a UX nit | It is a real authorization bypass — a security hole | Flag Shape A as a HIGH security finding |
| Enumerating every (role × route) pair in this skill | That walk is owned by `route-access-matrix`; duplicating it drifts | Cross-reference `route-access-matrix`; keep this to identity + one proof |
| Probing on production "just to check" | A status probe against real data can mutate or leak | Use a disposable target gated by `safe-destructive-testing` |

## Portability rationale

The method is framework- and stack-agnostic. It does not depend on:

- Any specific auth scheme (session cookie, JWT, opaque token) — only that an identity endpoint exists, named by the adapter.
- Any specific framework or admin UI library — the status-code semantics are HTTP-level.
- Any specific role model — the role list is an adapter input; the proof works for two roles or twenty.

Every project-specific value (identity endpoint, role list, restricted routes, disposable target) is a named adapter input. The 401/403-vs-400/409 status semantics are the same everywhere HTTP is spoken.

## Cross-references

- `route-access-matrix` — owns the per-(role × route) enumeration sweep; this skill owns the identity check and the single status-code proof it relies on.
- `safe-destructive-testing` — owns the disposable-data / non-production gate every probe here must pass through.
- `runtime-reality-check` — must pass first; confirms the probe runs against the intended env and build.
- `console-and-network-capture` — captures the actual response status the proof reads.
- `react-kit-plugin` `data-fetching-states` (`admin-states`) — defines the UI states (403 page, denied affordance, error display) these statuses should produce on the client.
- `role-smoke-tests` — the positive path (what a role CAN reach); this skill is the proof layer behind both positive and negative checks.
