# Anti-fraud artifacts and server-guard hygiene — deep reference

This reference expands the two runtime-QA surfaces owned by the
`anti-fraud-and-guard-hygiene` skill: client-rendered artifacts that are mistaken for
authentication, and server guards whose input hygiene (host canonicalization, Origin/Referer
presence) is wrong. It is platform-neutral; every concrete name is illustrative and never required.

Throughout: never print a real token, cookie, or the decoded payload of a genuinely signed artifact.
Report **shape** (signed? bound? expiring?), not value.

---

## Part 1 — A client-rendered artifact is NOT authentication

### What "the artifact" means

A QR code, 1-D/2-D barcode, an inline `<svg>` that renders a code, an `<img>` of a generated code, a
printable/exported badge or ticket. The browser draws it from data the page already has. Drawing is
not signing.

### The three properties that separate auth from decoration

An artifact is authentication **only** if the server, on the consuming side, independently enforces
all three:

1. **Signature** — the payload carries a cryptographic signature (HMAC with a server-held key, or an
   asymmetric signature) that the **server verifies on every presentation**. Without it, the payload
   is attacker-authorable: anyone who learns the format can mint a "valid" one.
2. **Binding** — the payload is tied to the identity/session/record that is allowed to present it
   (e.g., embeds and the server checks the holder's principal, a device binding, or a
   resource+holder pair). Without it, a copy taken from identity A is accepted for identity B.
3. **Expiry / single-use** — the payload stops being valid after a short window, or after first use
   (nonce / rotating value). Without it, a screenshot replays indefinitely.

Miss any one and the artifact is **decorative** — treat it as a fraud surface, not a feature.

### The identical-screenshot test (the load-bearing proof)

The cheapest definitive proof that **binding** is missing:

```
1. Provision two distinct disposable identities: A and B.
2. Render the artifact for A. Decode its payload (decoder, or read the <svg>/<img> source in the DOM).
3. Render the artifact for B. Decode its payload.
4. Compare:
   - Identical payloads  -> NO binding (both encode the same thing) -> DECORATIVE.
   - Differ only by a public, guessable id (e.g., a sequential record number) AND no signature/expiry
       -> effectively NO binding (B's value is predictable / A's is replayable) -> DECORATIVE.
   - Differ by an opaque value that the server rejects when A presents B's value -> binding present;
       continue to the signature + expiry checks.
5. Cross-present (disposable only): have A present B's decoded value to the consuming endpoint.
       Accepted -> confirmed NO binding (FINDING).
```

Two different people whose "access codes" scan to the same value, both admitted, is the canonical
fraud. A screenshot is then a master key.

### The replay probe (expiry / single-use)

On a disposable target:

```
1. Capture an artifact value once; present it to the consuming endpoint -> note status.
2. Present the SAME value a second time -> accepted again? Then no single-use / nonce.
3. Wait past the nominal validity window (if one is claimed); present again -> still accepted?
       Then no expiry enforcement.
```

Accepted-twice or accepted-after-expiry is positive evidence the artifact has no temporal binding.

### The signature check

Decode the payload and classify:

- **Raw id** (`12345`, `order-987`): no signature. Authorable by anyone.
- **Public URL** (`https://host/track/abc`): informational; "access meaning" only if the URL itself
  is gated server-side (then the gate, not the QR, is the auth — test the gate, not the graphic).
- **Opaque string** with no verifiable structure: could be a random token (possibly bound server-side)
  OR an unverified blob. Distinguish via the cross-present + replay probes above — if A can use B's
  blob, it is not verified/bound.
- **Signed token** (a structured token with a signature segment + issuer/expiry claims that the
  server verifies): candidate for real auth — confirm the server actually *verifies* it (tamper one
  byte of the signature on a disposable probe; a correct server returns 401/403, not 200).

### Reporting

Record shape only. Example ARTIFACT-TRUST rows:

```
ARTIFACT-TRUST — venue-entry QR ("scanning admits the holder")
  Encodes:              raw-id (sequential ticket number)
  Server signature:     NONE
  Bound to identity:    NO
  Expiry / single-use:  NO
  Identical-screenshot: two identities scan to different but sequential ids
  Replay (disposable):  accepted-twice
  Verdict:              DECORATIVE (fraud surface — a screenshot or an incremented id admits anyone)
```

```
ARTIFACT-TRUST — payout badge ("proves the order is paid")
  Encodes:              signed-token (signature segment + exp claim present)
  Server signature:     verified (tampered signature -> 403 on probe)
  Bound to identity:    yes (A rejected when presenting B's token)
  Expiry / single-use:  yes (rejected after exp window)
  Identical-screenshot: two identities scan to different opaque values
  Replay (disposable):  rejected on second use
  Verdict:              AUTHENTICATION
```

### Common misframings to push back on

- "It has the company logo / official styling." Visual chrome is trivially copied; it is not a
  signature.
- "It is hard to read by eye / it's a complex barcode." Complexity of encoding is not security; the
  decoder reads it instantly.
- "Only our app generates it." If the format is deterministic from public data, anyone can generate
  it; secrecy of the generator is not a signature.
- "We log who scanned it." Detection after the fact is not prevention of forgery.

---

## Part 2 — Server-guard hygiene

These are server-side bugs surfaced from the browser/QA side by probing inputs the developer's local
testing rarely varies.

### 2a. Canonicalize the host before allow/deny matching

A host-keyed guard (host allowlist, tenant resolver, environment gate) must normalize the host before
comparison, because the same host can arrive in many byte-forms:

```
raw Host header
   -> lowercase                 (DNS hostnames are case-insensitive; "EXAMPLE.com" == "example.com")
   -> strip a single trailing dot ("example.com." is the fully-qualified form of "example.com")
   -> strip :port if the policy is port-agnostic (decide once, apply consistently)
   -> (optional) IDNA/punycode-normalize internationalized hosts to one canonical form
   => compare to an allowlist that is itself stored canonical (lowercase, no trailing dot)
```

Why it bites: a list written `["example.com", "admin.example.com"]` and matched with raw `==` will
**deny** a perfectly legitimate `EXAMPLE.com` or `example.com.` — or, worse, a guard that special-cases
one form can be tricked into treating an attacker-controlled variant as trusted. Either direction is a
FINDING: the guard is matching bytes, not hosts.

Probe (read-only GET is enough to read the allow/deny decision; no mutation needed):

```
GET <endpoint>  Host: example.com      -> expect allow
GET <endpoint>  Host: EXAMPLE.com      -> expect allow (same host)   ; deny => not lowercasing
GET <endpoint>  Host: Example.Com      -> expect allow (same host)
GET <endpoint>  Host: example.com.      -> expect consistent w/ bare ; silent difference => FINDING
GET <endpoint>  Host: evil.com         -> expect deny
```

Note: some platforms validate Host at the edge/proxy before the app sees it. If so, record that the
canonicalization happens at the edge (still verify the variants), and do not double-report.

### 2b. Absence of Origin AND Referer is a CSRF reject, not a pass

For a **state-changing** request (POST/PUT/PATCH/DELETE), the same-origin/Origin check is a tripwire
that backs up CSRF tokens / SameSite cookies. The classic bug:

```
// WRONG — the no-Origin request falls through to allowed:
if (origin && origin !== ALLOWED_ORIGIN) { reject(); }
// ...else proceed   <-- a request with no Origin header at all reaches here and is ALLOWED
```

A scripted cross-site request, or one through certain intermediaries, can present **no Origin and no
Referer**. If the guard only rejects a *wrong* Origin, the stripped-header request sails through. The
correct rule for a mutating endpoint:

```
A trusted origin signal MUST be present AND MUST match.
Neither Origin nor Referer present  ->  REJECT  (do not assume same-origin).
```

Probe (disposable target only; empty/minimal body; read the status, do not rely on the mutation):

```
POST <mutating endpoint>  Origin: <same-site>        body: empty  -> expect allow-to-business-logic (400/409/200)
POST <mutating endpoint>  Origin: https://evil.test  body: empty  -> expect reject (403)
POST <mutating endpoint>  (no Origin, no Referer)     body: empty  -> expect reject (403)   ; 200/400 => FINDING
```

Interpreting status with the `verify-identity-and-rbac` semantics: a 400/409 here still means the
request *passed the origin guard* and reached business logic — for the no-headers case that is a
FINDING (the guard let it through). Only 401/403 means the guard rejected it.

Caveats to record, not to excuse the bug:
- The primary CSRF defenses are an anti-CSRF token and/or `SameSite=Lax/Strict` cookies. The
  Origin/Referer check is defense-in-depth and the easiest thing to probe from QA. If tokens are
  present and verified, note it — but a no-Origin *allow* is still worth flagging because it means one
  layer is missing.
- GET/HEAD/OPTIONS are safe methods; this rule is for state-changing verbs only. Do not flag a
  read-only endpoint for accepting a no-Origin GET.

### Reporting

```
GUARD-HYGIENE — POST /api/<resource> (host allowlist + CSRF origin check)
  Host match canonicalizes: NO
    exact-case   example.com   -> allow
    mixed-case   EXAMPLE.com   -> deny       (FINDING — raw byte match, not lowercased)
    trailing-dot example.com.  -> deny
    foreign host evil.com      -> deny
  CSRF / same-origin (mutating):
    correct Origin             -> allow
    wrong Origin               -> reject
    no Origin AND no Referer   -> ALLOWED    (FINDING — absence treated as innocence)
  Verdict:                     FINDING (host not canonicalized; no-Origin request accepted)
```

---

## Severity guidance (for the UAT report)

| Finding | Severity | Why |
|---|---|---|
| Decorative artifact used as access/identity (no signature/binding/expiry) | HIGH | Forgeable / replayable; a screenshot is a master key |
| Mutating endpoint accepts no-Origin-and-no-Referer | HIGH | CSRF bypass surface; cross-site requests can mutate state |
| Host guard not canonicalized (case/trailing-dot mismatch) | MEDIUM–HIGH | Legitimate denial (UX) or trust-the-wrong-host (security) depending on direction; treat as HIGH if a wrong host is trusted |
| Signed artifact verified but not single-use | MEDIUM | Replay window exists; bounded by expiry |

Feed HIGH rows into `uat-readiness-report`; a HIGH blocks a YES sign-off.
