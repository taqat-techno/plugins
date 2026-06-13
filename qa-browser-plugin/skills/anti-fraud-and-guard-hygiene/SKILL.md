---
name: anti-fraud-and-guard-hygiene
description: Two runtime-QA checks static review keeps missing — (1) client-rendered artifacts (barcode / QR / SVG token / printed badge) are NOT authentication proof when they carry no server signature, binding, or expiry, and screenshots of two different identities scan identically; (2) server-guard hygiene — a host allow/deny decision must lowercase and canonicalize the host before matching, and a state-changing request with NEITHER an Origin NOR a Referer header must be treated as a CSRF reject, not waved through. Activates when QA sees an on-screen code or scannable graphic used as access/identity, when a host-based allow/deny guard is under test, or when checking CSRF / same-origin enforcement on a mutating endpoint.
version: 0.1.0
last_reviewed: 2026-06-13
owns:
  - client-artifact-is-not-auth rule (no signature/binding/expiry => decorative, forgeable)
  - the identical-screenshot test (two identities render the same scannable graphic => no binding)
  - host-canonicalization rule (lowercase + normalize before allow/deny match)
  - the no-Origin-AND-no-Referer = CSRF reject rule (absence is not innocence)
  - the GUARD-HYGIENE and ARTIFACT-TRUST output blocks
defers_to:
  - verify-identity-and-rbac (the authoritative identity endpoint + status-code proof)
  - route-access-matrix (the per-role x route dual/three-layer denial sweep)
  - safe-destructive-testing (any probe runs on a disposable target only)
  - console-and-network-capture (capturing request/response headers without leaking secrets)
  - runtime-reality-check (confirm env + build before trusting any probe)
user_invocable: false
---

# anti-fraud-and-guard-hygiene

## Purpose

Two classes of bug slip past code review because they only manifest at runtime, against a real
request:

1. **Client-rendered artifacts treated as authentication.** A barcode, QR code, inline SVG
   "token", or printed badge that the browser draws from plain data is decorative. If the server
   never signs it, never binds it to a session/identity, and never expires it, then a screenshot is
   a forgery: two different identities produce graphics that scan to the same value, and anyone can
   replay one.

2. **Sloppy server guards.** A host-based allow/deny check that matches the raw `Host` header lets
   `EXAMPLE.com`, `example.com.`, or a mixed-case variant slip past a list written in lowercase. A
   CSRF / same-origin guard that only rejects a *wrong* Origin waves through a request that carries
   **neither** an Origin **nor** a Referer — the exact shape a scripted cross-site POST can present.

This skill owns the runtime checks for both. It does not replace `verify-identity-and-rbac` (the
identity proof) or `route-access-matrix` (the role sweep) — it covers the fraud surface and the
guard-input hygiene those skills assume is already sound.

## When to use

Activate when:

- An on-screen scannable graphic (QR / barcode / SVG code) or a printed/exported badge is used as
  proof of identity, entitlement, ticket, or access — and you must decide whether it is real auth or
  decoration.
- A server guard makes an allow/deny decision keyed on the request **host** (host allowlist, tenant
  routing, environment gate).
- You are checking CSRF / same-origin enforcement on a state-changing endpoint (POST / PUT / PATCH /
  DELETE).
- A report says "the badge/QR lets people in" or "someone reused a screenshot."

Skip when the artifact is purely informational (a QR that opens a public URL with no access meaning)
or when no host-based or origin-based guard exists on the path under test.

## Inputs (adapter)

Every value is a NAMED adapter input; behavior never depends on a specific one.

1. **Artifact under test** — the scannable graphic or badge, and the claim attached to it
   ("scanning this admits the holder" / "this proves the order is paid").
2. **Decode method** — how the artifact's payload is read (a QR/barcode decoder, or reading the
   `<svg>`/`<img>` source in the DOM). Read-only.
3. **Two distinct identities** — two disposable accounts/records whose artifacts can be compared.
4. **Host allowlist / guard** — the set of hosts the server is supposed to accept, and the endpoint
   whose guard is under test.
5. **Mutating endpoint** — the state-changing route whose CSRF / same-origin behavior is probed
   (against a disposable target, gated by `safe-destructive-testing`).

## Read-only investigation steps

1. **Confirm reality first.** `runtime-reality-check` must have passed — right env, right build.
2. **Decode the artifact** (item 1). Read its payload via the decode method. Record what it encodes:
   a raw id? a URL? an opaque string? a signed token (has a signature segment + issuer/expiry)?
3. **Run the identical-screenshot test.** Generate the same artifact for two distinct identities.
   Decode both. If they scan to values that differ ONLY by a non-secret public id (or are identical),
   and neither carries a signature/expiry, the artifact is not bound — FINDING.
4. **Probe replay** (on disposable data). Re-present a captured artifact value to the endpoint that
   "consumes" it. If it is accepted a second time, or after its nominal validity window, there is no
   binding/expiry — FINDING.
5. **Inspect the host guard** (item 2). Determine whether the allow/deny match lowercases and
   canonicalizes the host before comparing. Probe with case and trailing-dot variants.
6. **Probe the CSRF/origin guard.** Issue the mutating request three ways against a disposable
   target: correct Origin, wrong Origin, and **no Origin and no Referer at all**. Read the status of
   each. The no-headers case must be rejected.

All steps are read-only with respect to real data; the only server-touching probes run against a
disposable target gated by `safe-destructive-testing`, and use the empty/minimal-body, status-only
technique from `verify-identity-and-rbac`.

## Decision framework

### Is the artifact authentication? (item 1)

| Property the artifact has | Present? | Consequence |
|---|---|---|
| Server **signature** (HMAC / asymmetric signature the server verifies) | no | Anyone can fabricate a valid-looking payload |
| **Binding** to the session/identity that presents it | no | A screenshot from identity A works for identity B |
| **Expiry** / single-use / nonce | no | A captured screenshot replays forever |

Rule: an artifact is authentication ONLY if the server independently verifies a signature AND binds
it to the presenter AND enforces expiry/single-use. Missing ANY one => it is decorative; report it
as a fraud surface, not a feature. The hallmark proof is the **identical-screenshot test**: two
different identities whose artifacts scan to the same (or trivially-predictable) value, accepted by
the server, is positive evidence of no binding.

### Host-guard canonicalization (item 2)

```
incoming Host header  ──▶  lowercase  ──▶  strip trailing dot  ──▶  strip :port (if policy ignores port)
                                                    │
                                                    ▼
                                        compare to allowlist (also canonical)
```

Probe variants against a host-keyed guard (read-only GET is enough to read the decision):

| Variant sent as Host | Should the guard treat it as the allowlisted host? | A correct guard … |
|---|---|---|
| `example.com` (exact, lowercase) | yes | allows |
| `EXAMPLE.com` / `Example.Com` | yes (case is not identity) | allows — proves it lowercased |
| `example.com.` (trailing dot, still the same host) | yes | allows OR rejects consistently — must not differ from the bare form by accident |
| `evil.com` | no | denies |

A guard that allows `example.com` but denies `EXAMPLE.com` (or vice-versa) is matching raw bytes, not
hosts — FINDING. Canonicalize (lowercase + normalize) **before** the allow/deny match.

### CSRF / same-origin: absence is not innocence (item 2)

| Request presents | A correct mutating-endpoint guard … |
|---|---|
| Correct same-site Origin | allows |
| Wrong / cross-site Origin | rejects |
| **No Origin AND no Referer** | **rejects** (treat as CSRF — a stripped-header cross-site POST looks exactly like this) |

The trap: guards often `if (origin && origin !== allowed) reject;` — which lets the no-Origin case
fall through to allow. The correct rule for a state-changing request is: a trusted origin signal MUST
be present and MUST match; its **absence is a reject**, not a pass. (CSRF tokens / SameSite cookies
are the primary defense; this header check is the QA tripwire that catches a missing or bypassable
one.)

## Safety gates

- **Never** probe against production or non-disposable data — defer target classification to
  `safe-destructive-testing`.
- **Never** send a valid destructive payload to test the CSRF/host guard; an empty/minimal body plus
  the status code is enough (per `verify-identity-and-rbac`).
- **Never** print a real signed token, session cookie, or the decoded payload of a *genuinely* signed
  artifact into evidence — record its shape (signed? bound? expiring?), not its value.
- **Never** report a host guard as PASS on the strength of one exact-case request — always probe the
  case and trailing-dot variants.
- **Never** conclude a CSRF guard is sound without the no-Origin-AND-no-Referer probe; the wrong-Origin
  reject alone does not prove it.
- **Never** call a screenshot/QR/badge "secure" because it "looks official" — looks are not a
  signature.

## Validation checklist

- [ ] `runtime-reality-check` passed before any probe.
- [ ] Artifact payload decoded; recorded as raw-id / URL / opaque / signed-token.
- [ ] Identical-screenshot test run across two distinct identities; result recorded.
- [ ] Replay probe run on a disposable target (accepted twice / after expiry => FINDING).
- [ ] Host guard probed with exact, mixed-case, and trailing-dot variants.
- [ ] CSRF guard probed with correct-Origin, wrong-Origin, AND no-Origin-no-Referer.
- [ ] No real token / cookie / signed payload value printed in evidence.
- [ ] Any probe ran only on a target classified disposable by `safe-destructive-testing`.

## Output format

Emit an ARTIFACT-TRUST block per artifact, and a GUARD-HYGIENE block per guard.

```
ARTIFACT-TRUST — <artifact + the access claim>
  Encodes:              raw-id | public-url | opaque-string | signed-token
  Server signature:     verified | NONE
  Bound to identity:    yes | NO
  Expiry / single-use:  yes | NO
  Identical-screenshot: two identities scan to <same | different> value
  Replay (disposable):  accepted-once | ACCEPTED-TWICE | accepted-after-expiry
  Verdict:              AUTHENTICATION | DECORATIVE (fraud surface — not auth)
```

```
GUARD-HYGIENE — <endpoint + guard type>
  Host match canonicalizes: yes (lowercase+normalize before compare) | NO
    exact-case   <host>      -> allow | deny
    mixed-case   <HOST>      -> allow | deny   (must match exact-case)
    trailing-dot <host.>     -> allow | deny   (must be consistent)
    foreign host <evil>      -> deny (expected)
  CSRF / same-origin (mutating):
    correct Origin           -> allow
    wrong Origin             -> reject
    no Origin AND no Referer -> REJECT expected | ALLOWED (FINDING)
  Verdict:                   SOUND | FINDING (<which check failed>)
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| "The QR/badge proves who they are" | A client-drawn graphic with no server signature is forgeable; a screenshot replays | Require server signature + identity binding + expiry; else it is decorative |
| Comparing only one identity's artifact | Cannot reveal a missing binding | Run the identical-screenshot test across two identities |
| Trusting an artifact because it "looks official" / has a logo | Visual chrome is not a cryptographic signature | Decode it; check for a verified signature segment |
| Host allowlist matching the raw `Host` header | `EXAMPLE.com` / `host.` slip past a lowercase list | Lowercase + canonicalize before the allow/deny compare |
| `if (origin && origin !== allowed) reject` | The no-Origin request falls through to ALLOW | Require a trusted origin signal; treat its absence as a reject |
| Declaring CSRF "fine" after only a wrong-Origin reject | Misses the stripped-header (no Origin, no Referer) bypass | Probe the no-Origin-AND-no-Referer case explicitly |
| Printing the decoded payload of a real signed token | Leaks a live credential into evidence | Record shape (signed/bound/expiring), never the value |

## Portability rationale

Both checks are stack- and framework-agnostic:

- The artifact check needs only a decoder (or DOM read) and two disposable identities — it works for
  any QR/barcode/SVG/badge scheme. "Signed + bound + expiring" is the universal definition of auth.
- The guard checks are HTTP-level: host canonicalization and the Origin/Referer presence rule hold
  for any server. The allowlist and endpoints are adapter inputs, never hardcoded.

## Cross-references

- `verify-identity-and-rbac` — owns the authoritative identity endpoint and the empty-body
  status-code proof these probes reuse; an artifact that fails here is the *opposite* of the trusted
  identity-endpoint signal.
- `route-access-matrix` — the per-role x route denial sweep; a host/CSRF guard hole is the
  server-layer counterpart to a missing role gate.
- `safe-destructive-testing` — every server-touching probe runs on a disposable target only.
- `console-and-network-capture` — captures the request/response headers (Host, Origin, Referer,
  status) without leaking secrets; supplies the redaction rules.
- `runtime-reality-check` — confirm env + build before trusting any probe result.
- `uat-readiness-report` — an artifact-is-not-auth finding or a no-Origin-allowed finding is a HIGH
  severity row.
