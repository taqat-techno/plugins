---
name: safe-destructive-testing
description: Disposable-data-only rule for any QA action that mutates state. Owns the "what counts as disposable" test, the production-URL refusal, the selector skiplist (do-not-click), the credentials-must-be-gitignored rule, and the irreversible-action escalation. Activates BEFORE any QA action that could change data; activates BEFORE every QA pass to gate the environment.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - disposable-data classification (what counts as disposable)
  - production-URL refusal (gated by plugin hook + this skill's rules)
  - selector skiplist (do-not-click list — destructive buttons on real records)
  - credentials-must-be-gitignored rule
  - irreversible-action escalation to user
defers_to:
  - browser-qa-discipline (any blocked-by-safety check is BLOCKED with named precondition)
  - runtime-reality-check (env identity confirms which env you're actually on)
  - modal-and-action-walkthroughs (Pattern 2 commit gated by this skill)
  - import-export-ui-checks (Pattern 2 commit gated by this skill)
user_invocable: false
---

# safe-destructive-testing

## Purpose

The most expensive QA mistake is the one that destroys data. This skill makes destructive QA boring — by default, the plugin refuses to mutate anything; you have to deliberately, with named justification, opt in on a per-action basis against a disposable target.

This skill is the gate. Every other skill that wants to mutate (Pattern 2 in `modal-and-action-walkthroughs`, Pattern 2 in `import-export-ui-checks`, any direct API mutation) goes through this gate.

## When to use

Activate **before** any QA action that could change data. This includes:

- Clicking a destructive button (Delete, Suspend, Archive, Refund, Force-logout, …).
- Submitting a form that creates / updates / deletes a record.
- Committing an import.
- Triggering a state-machine transition (Approve, Publish, Cancel-Order).
- Calling a mutating API directly during a probe.

Also activate at the **start** of every QA pass, to gate the environment itself.

## Inputs

- Target URL (from the credentials file or `/qa-target`).
- The action the QA pass is about to take.
- The record the action targets.
- The project's "disposable data" policy:
  - Is there a separate sandbox tenant / project / org?
  - Is there a naming convention for test records (`qa-user-1`, `[TEST]-Order-…`)?
  - Is staging shared with real customer data, or is it fully synthetic?

## What counts as disposable

A record is **disposable** for QA purposes only if at least one of:

1. **Synthetic environment** — the entire environment (sandbox, dev, ephemeral preview, dedicated QA tenant) was provisioned with synthetic data; no real customers / orders / payments exist there.
2. **Marked test record** — the specific record carries a stable, machine-readable test-marker:
   - Naming convention: e.g., `qa-user-*`, `[TEST]-*`, `*--qa`.
   - Tag / label: e.g., `tags: ['qa-test']`.
   - Tenant scope: lives under a dedicated QA tenant within an otherwise-real environment.
3. **User explicit per-action approval** — the user said in this session, with the action and target named, "yes, this record is disposable; proceed."

A record is **NOT disposable** if:

- It is in a production environment (regardless of marker).
- It is in a staging environment shared with real customer / payment / billing data and lacks a marker.
- It was created by another QA pass less than ~30 days ago AND that pass is still running (race).
- It has dependents (FK references) you cannot enumerate — destroying it could cascade.

## The production-URL refusal

`qa-browser` ships a PreToolUse hook (`hooks/hooks.json`) that intercepts browser navigation calls. If the URL contains a production marker — by default `prod` or `production` as substrings — the hook refuses the navigation unless the user has explicitly enabled production mode for this session.

Defaults:

- Substring patterns: `prod`, `production` (case-insensitive). Configurable in `.qa-browser.local.json` under `productionMarkers`.
- Behavior: refuse the navigation; print a clear message; wait for the user to either confirm (override the gate for this session) or change the URL.

The override is **per-session, not persistent**. Even if the user confirms once, restarting the QA pass requires re-confirmation. This is intentional friction.

If the project's production URL does NOT contain `prod` (e.g., a vanity domain like `app.example.com`), add the production marker to the local config:

```json
{
  "productionMarkers": ["prod", "production", "app.example.com", "checkout.example.com"]
}
```

Anything the gate matches refuses. False positives are better than a leaked production action.

## The selector skiplist

For each environment, the user can configure a **do-not-click** selector list:

```json
{
  "doNotClick": [
    "[data-qa-skip='true']",
    "button:has-text('Refund')",
    "[data-customer-id]:not([data-customer-id^='qa-'])",
    ".admin-billing-panel button"
  ]
}
```

Before any click action, the QA flow checks the target selector against the skiplist. A match → the click is blocked; the row is marked BLOCKED with a named precondition ("selector matches do-not-click rule").

The skiplist is **additive** — destructive selectors that the project knows should never be clicked outside synthetic environments. Examples worth adding by default:

- Anything in a payment / billing / refund panel.
- Anything that triggers an outbound email / SMS / notification to a real address.
- Anything that triggers an outbound API call to a third-party service (payment processor, CRM).

## Credentials file rules

The credentials file `.qa-browser.local.json` MUST:

1. Be listed in `.gitignore` at the project root (and in any parent .gitignore that covers the path).
2. Never be committed to git, ever.
3. Live in the project root, not in a shared directory.
4. Be readable only by the developer's user (filesystem permissions, where the OS supports it).

The plugin refuses to operate if:

- The file exists but is tracked by git (verified via `git ls-files`).
- The file references credentials that look like production credentials (heuristic: presence of `prod` / `production` in usernames or context).

## Irreversible-action escalation

Some actions cannot be undone even on a disposable target:

- **Send real money** (refund, transfer) — even on a sandbox processor, the audit trail persists.
- **Send real email / SMS / push** to a real address.
- **Trigger a third-party webhook** to a non-test endpoint.
- **Run a one-way state transition** that the data model does not support reversing.

For these:

```
1. Skill refuses to proceed silently.
2. Skill names the action and the irreversibility.
3. Skill asks the user explicitly: proceed, or skip?
4. User answer is recorded in the report (PASS with explicit approval | SKIPPED).
```

## Safety gates (the rule set)

- **Refuse** any navigation to a URL matching the production-marker list, unless the user explicitly opts in for this session.
- **Refuse** any click whose target matches the do-not-click skiplist.
- **Refuse** to mutate a record that is not classified as disposable.
- **Refuse** to operate if the credentials file is tracked by git.
- **Refuse** to operate if the credentials file references production credentials.
- **Escalate** every irreversible action to the user; never assume.
- **Never** propagate a session cookie from a production probe into a non-production probe (rare, but cookies set on a parent domain leak).
- **Never** treat "the form looks like a test form" as evidence the data is disposable. Markers are explicit.

## Validation checklist

Before any mutating QA action:

- [ ] Reality-check passed; env identity matches the URL.
- [ ] Target URL is NOT in the production-marker list, OR explicit per-session override granted by the user.
- [ ] Target record is disposable per the classification above.
- [ ] No selector match against the do-not-click skiplist.
- [ ] Credentials file is gitignored AND not tracked AND does not reference production.
- [ ] Action is reversible OR the user has approved the irreversible escalation.

## Output format

When safe-destructive-testing blocks an action:

```
[BLOCKED] action="<verb> on <target>" route=<url>
  Reason: <production-marker | selector-skiplist | not-disposable | tracked-credentials | irreversible>
  Detail: <what specifically matched>
  Unblock: <what the operator needs to do> (e.g., "explicit per-session override; rerun with --allow-production")
```

When the gate allows but escalates an irreversible action:

```
[ASK] action="<verb> on <target>" route=<url>
  Irreversibility: <why this cannot be undone>
  Disposable evidence: <how the target was classified disposable>
  Proceed? [yes / skip]
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| "We only have one env; have to test on prod" | Prod traffic affected; users affected | Provision a non-prod env; the plugin refuses prod by default |
| Override the production gate "just for this one click" | The "one click" propagates; the override stays in muscle memory | Override is per-session; granted explicitly each time |
| Test record naming `temp-1`, `delete-me-2` | Not a stable marker; future code may treat them as real | Adopt a project-wide convention (`qa-*`, `[TEST]-*`); document it |
| Skip the selector skiplist because "I know what I'm clicking" | One slip clicks Refund on a real customer | Skiplist enforced; matches BLOCK |
| Credentials file checked into git "by accident" | Production credentials leaked | Plugin refuses to operate; you fix git first |
| Send real SMS during a smoke test | Real customer's phone rings at 3am | Skip the action OR use a project-provided mock provider |
| Mutate a record because "the data looks fake" | Looks-fake ≠ is-fake | Marker-based classification only |

## Portability rationale

The safety rules apply to any web app. The skill does not depend on:

- A specific cloud provider
- A specific environment naming convention (the markers are configurable)
- A specific test framework
- A specific MCP server (the gate is in the plugin hook; the rules are skill-level)

## Cross-references

- `browser-qa-discipline` — blocked actions become BLOCKED rows with named preconditions.
- `runtime-reality-check` — env identity verification feeds the production-marker check.
- `modal-and-action-walkthroughs` — Pattern 2 gated by this skill.
- `import-export-ui-checks` — Pattern 2 commit gated by this skill.
- `route-access-matrix` — implicit-method probes use this skill's "non-mutating payload" guidance.
- `qa-browser` hooks — production-URL refusal and credentials-gitignored check are enforced via plugin hooks.
