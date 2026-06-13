# Neutralization discipline

Reference for `wiki-authoring` and `wiki-source-of-truth`. How to remove tenant / client / customer names from a wiki page without breaking the page in the process. Read this whenever a page contains a real organisation, tenant, product, or customer name and the page is being published, generalized, or shared beyond the team that owns that name.

The wrong instinct is a blind global find/replace: `sed s/AcmeCorp/Tenant-A/g` across the page. That corrupts the page, because not every occurrence of a name plays the same role. A name in active prose is a leak to fix. The *same name* inside a quoted historical record, a provenance note, or an example that demonstrates a rule may be load-bearing — replacing it silently changes what the page asserts or destroys the evidence a rule depends on.

So neutralization is a **per-hit classification**, never a sweep.

---

## Classify each name hit (three classes)

For every occurrence of a real tenant / client / product / customer name, decide which class it falls in *before* touching it.

### Class 1 — Active-target prose → NEUTRALIZE

The name appears in present-tense, descriptive prose about how the system works, how to operate it, or who does what. The name is incidental — the sentence is true of any tenant. This is the leak.

- Examples: "Log in to the AcmeCorp dashboard and click Deploy." / "The AcmeCorp tenant uses the standard retry budget."
- Action: replace with a **deterministic placeholder** — the same name always maps to the same placeholder within the page (and ideally across the wiki). Use a stable scheme like `<TENANT>`, `Tenant-A`, `<CLIENT>`, `Example Co`, chosen once and applied consistently. Determinism matters: if "AcmeCorp" and "Acme Corp" both appear, map both to the same placeholder so the page still reads as one tenant.

### Class 2 — Legacy reference / provenance → PRESERVE BYTE-IDENTICAL

The name appears inside a quoted record, an incident log entry, a commit/PR quotation, an ADR's "context" recounting what actually happened, a migration note, or an example whose whole point is that *this specific historical thing* occurred. Here the name is **evidence**. The rule, lesson, or audit trail the line supports depends on it being exactly what it was.

- Examples: an ADR context paragraph — "In 2024 the AcmeCorp migration overran because the cutover ran on a Friday" (the rule "never cut over on a Friday" is anchored to this real event). / A quoted incident postmortem line. / A provenance footnote — "originally documented for AcmeCorp in [ticket]".
- Action: **do not touch it.** Preserve it byte-identical. Rewriting it to `<TENANT>` would make the provenance unverifiable and could turn a true historical statement into a false generic one. If the concern is exposure, the right move is to decide whether the *whole record* belongs in a shared wiki at all (escalate to the page owner) — not to silently scrub the name out of a record that is supposed to be faithful.

### Class 3 — Operator / platform context → PRESERVE

The name is not a tenant/client at all — it is the operating company, the platform vendor, the tool, the team, or the infrastructure that legitimately appears in operator-facing docs. Neutralizing it would make the doc wrong or unusable.

- Examples: the name of the company that runs the platform in its own internal runbook; a cloud provider, CI vendor, or library name; the owning team's name in a role guide.
- Action: **preserve.** This is not a leak; it is the context the reader needs. (Apply the usual no-secrets / no-PII rules — a vendor name is fine; a vendor API key is not.)

---

## Decision flow

```
name hit found
  ├─ Is it a tenant / client / customer name in present-tense descriptive prose? 
  │     → Class 1: NEUTRALIZE to a deterministic placeholder
  ├─ Is it inside a quoted record / provenance / incident log / ADR-context / a rule's anchoring example?
  │     → Class 2: PRESERVE byte-identical (escalate the whole record if exposure is a concern)
  └─ Is it the operator / platform / vendor / team context the reader needs?
        → Class 3: PRESERVE
never: a single global find/replace across the page
```

When a hit is genuinely ambiguous (the same paragraph mixes active prose and a provenance quote), split it: neutralize the prose sentence, preserve the quoted line. Do not let the ambiguous case collapse into "replace everything" or "replace nothing".

---

## Determinism rules for Class 1 placeholders

- Pick the placeholder scheme once per page (or per wiki, via the project's convention) and apply it consistently. `<TENANT>` everywhere, or `Tenant-A` / `Tenant-B` if the page genuinely describes more than one.
- Map every spelling variant of the same real name to the same placeholder (`AcmeCorp`, `Acme Corp`, `acme` → one placeholder).
- Map distinct real tenants to distinct placeholders — do not merge two clients into one, or the page's meaning changes.
- Preserve surrounding structure: a placeholder must be grammatically substitutable so the sentence still reads correctly.

---

## Interaction with the source-of-truth doctrine

This discipline pairs with `wiki-source-of-truth`:

- A **current-state** page describing live behavior is where Class 1 neutralization applies most — the tenant name is incidental to a present-tense fact.
- A **provenance / decision record** (ADR context, incident log) is exactly where Class 2 preservation applies — the named event is the evidence the decision rests on.
- If neutralizing would change a config-constant or a named decision's meaning, stop: that is no longer cosmetic neutralization, it is a content change, and it routes through the normal decision/owner-confirmation path, not a scrub.

---

## Output format

```
NEUTRALIZATION PLAN — <page>
| Hit (line) | Name | Class | Action |
|------------|------|-------|--------|
| L12 | AcmeCorp | 1 active prose | → <TENANT> |
| L40 | AcmeCorp | 2 ADR-context provenance | preserve byte-identical |
| L55 | <vendor> | 3 platform context | preserve |

Placeholder map (deterministic):
  AcmeCorp / Acme Corp → <TENANT>

Escalations:
  - L40 record contains a real client name; preserved for provenance. Confirm this record belongs in a shared wiki? [owner decision]
```

Apply the plan through the normal diff-preview (`wiki-safe-updates`) so the owner sees exactly which lines change and which are deliberately left intact.

---

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Global find/replace the name across the whole page | Corrupts provenance and rule-anchoring examples; changes what the page asserts | Classify each hit; act per class |
| Neutralize a name inside an ADR "context" paragraph | The rule the ADR records is anchored to that real event; the provenance becomes unverifiable | Class 2: preserve byte-identical |
| Map two different clients to the same placeholder | The page now describes one tenant where there were two; meaning changes | Distinct real names → distinct placeholders |
| Map one client's spelling variants to different placeholders | The page reads as multiple tenants where there is one | Same name (all variants) → one placeholder |
| Scrub a vendor / platform / team name as if it were a client | Makes an operator runbook wrong or unusable | Class 3: preserve operator/platform context |
| Silently delete a record because it contains a client name | Loses the audit trail / lesson the record exists to preserve | Preserve; escalate whether the record belongs in a shared wiki |
| Treat "remove all names" as cosmetic and skip diff preview | A meaning-changing edit slips through unreviewed | Always diff-preview; the owner sees what changed and what was preserved |
