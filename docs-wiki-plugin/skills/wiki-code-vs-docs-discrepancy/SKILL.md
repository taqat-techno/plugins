---
name: wiki-code-vs-docs-discrepancy
description: Report disagreements between a project Wiki and the actual code (or runtime config, deploy scripts, schema, CI workflow) with concrete file-line evidence. Owns the never-silently-choose rule, the discrepancy classification (doc-drift / code-drift / intentional gap / unknown), and the evidence-pinning convention. Activates whenever a wiki page claims one behavior and the code shows another; activates on wiki-says / doc-says / spec-says prompts.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - discrepancy classification (doc-drift / code-drift / intentional gap / unknown)
  - evidence-pinning convention (file-path plus line number plus last-modified)
  - never-silently-choose gate
  - two-author suspicion heuristic (when wiki and code each look right in isolation)
defers_to:
  - wiki-safe-updates (any chosen-direction wiki edit goes through that skill)
  - wiki-link-validation (when the discrepancy is about a missing wiki cross-reference)
  - project owner / engineering lead (the user makes the directional call; this skill does not)
user_invocable: false
---

# wiki-code-vs-docs-discrepancy

## Purpose

When the wiki says X and the code does Y, the worst response is silently picking one and updating the other. The wiki and the code each have authors who believed they were right. This skill enforces one rule: **report the discrepancy with evidence; never silently pick a side.** The user decides which is the source of truth for the contested behavior.

## When to use

Activate when:

- A wiki page claims a behavior, and the code, runtime config, schema, or CI workflow shows a different behavior.
- Two wiki pages contradict each other on the same topic.
- A user prompt asks "what does the wiki say about X" and the code path is also in scope.
- Trigger phrases appear: "the wiki says…", "the doc says…", "I thought we did X", "the spec says…".
- A wiki audit (`/wiki-audit`, `/wiki-drift`) surfaces a contradiction.

Skip when:

- The "discrepancy" is purely stylistic — the wiki uses one term and the code uses a synonym, with no behavioral difference.
- The wiki page is explicitly marked as historical / archived / target-state. Those are not authoritative for current behavior.

## Inputs

- The claim from each side, pinned with `file:line` citations and the file's last-modified date.
- A runtime probe demonstrating the actual current behavior (when the claim is behavioral, not stylistic).
- The project's source-of-truth assignment for the topic (see Decision framework below).

## Read-only investigation steps

1. **Pin each side verbatim.** Quote the relevant lines from the wiki page AND the code file, with `file:line` plus the file's last-modified date.
2. **Classify by authority.** Some sources are authoritative by policy (a SOP wiki page for process rules). Some are authoritative by execution (code that ships, config that loads). Decide which is which for the topic at hand.
3. **Probe runtime if the claim is behavioral.** Reading the code may not be enough — a feature flag, environment value, or runtime config may divert the actual path. Run a read-only probe.
4. **Check freshness.** Either side may be stale. A wiki page edited 18 months ago and a code path rewritten 2 weeks ago tells you which moved.
5. **Check intent markers.** "TODO", "FIXME", "DEPRECATED" comments, or wiki "as of date" headers signal that the author knew something was in flux.

## Decision framework

### The four classifications

| Class | Meaning | Typical fix direction |
|---|---|---|
| **doc-drift** | The code is correct (and intentional); the wiki was not updated when the code changed | Update the wiki |
| **code-drift** | The wiki is correct (and the team-policy intent); the code drifted away | Update the code |
| **intentional gap** | The wiki describes target state; the code is current state; the gap is known | Annotate the wiki page as "target state — not yet implemented" |
| **unknown** | Insufficient evidence to classify | Hand off to the user with both sides documented |

### Source-of-truth assignment (project-supplied; the skill does NOT bake in)

| Topic | Typical authority |
|---|---|
| Business process / SOP / approval flow | Wiki (authoritative by policy) |
| Runtime API behavior (request → response) | Code |
| Database schema / column meaning | Schema definition file (code-adjacent) |
| Deployment process / rollback steps | Wiki SOP — but code (CI workflow) is the executed truth |
| Role / permission matrix | Code (whatever the route handler enforces) — wiki should document the same |
| Feature flag default | Config file — wiki should document the current default |
| Onboarding / role guide | Wiki (lived experience) |
| Build / install instructions | Wiki — but verified against actual build output |

The project's wiki should declare its source-of-truth assignments somewhere (often in the Home page or a "Documentation Index"). If absent, ask the user once and record the answer in `.docs-wiki.local.json` for future runs.

### Never silently choose

Even when the answer "feels obvious", surface the discrepancy:

```
DISCREPANCY DETECTED

  Topic: <name>
  Wiki claim:
    "<verbatim quote>"
    Source: wiki/Operations.md:42 — last modified 2025-11-14
  Code reality:
    "<verbatim quote OR runtime probe result>"
    Source: src/handlers/orders.ts:88 — last modified 2026-03-22
    Runtime probe: <command and output>

  Classification (proposed): <doc-drift | code-drift | intentional gap | unknown>
  Reasoning: <2-3 sentences>

  Direction (NOT applied): wait for user input
    Option A — update wiki to match code (recommended IF doc-drift)
    Option B — update code to match wiki (recommended IF code-drift)
    Option C — annotate wiki as target state (recommended IF intentional gap)
    Option D — investigate further (recommended IF unknown)
```

The skill stops here. The user picks. Once the user picks, follow `wiki-safe-updates` (for wiki changes) or the project's normal code-change process (for code changes).

### Two-author suspicion heuristic

When the wiki and code each look internally consistent but contradict each other, the two-author hypothesis often applies: a wiki author wrote what the team intended, and a code author implemented what they understood. Without a meeting, both ship and the world quietly diverges.

Signal: both sides are well-formed; neither has stale markers; the contradiction is on a single behavior. Treat as a discovery, not an error. Surface; do not pick.

### Wiki-vs-wiki contradictions

When two wiki pages disagree:

1. Apply the same evidence-pinning.
2. Check which page is more recently modified.
3. Check which page is referenced by the Home / Sidebar / index (the linked page is presumptively the active one; the orphan may be stale).
4. Report with the same vocabulary; the user decides which to merge into which.

Special case: a wiki page explicitly marked as historical / archived / superseded is NOT in contradiction with a current page — it documents history. Do not flag.

## Safety gates

- **Never** silently update either the wiki or the code to "resolve" a discrepancy.
- **Never** classify as "doc-drift" just because the code is newer; the code may have drifted from the policy intent (the wiki).
- **Never** quote a wiki page that contains PII / secrets / tokens in your report. If the page has such content, redact at quote time AND surface as a separate finding (wiki should not contain secrets).
- Prefer applying a wiki update via `wiki-safe-updates` (optional diff preview) — advisory, not enforced.
- **Never** discard the "intentional gap" classification — target-state documentation is legitimate.

## Validation checklist

Before reporting a discrepancy:

- [ ] Both sides pinned with `file:line` + last-modified.
- [ ] Wiki quote verbatim; not paraphrased.
- [ ] Code quote verbatim OR runtime probe captured with command + output.
- [ ] Classification proposed with reasoning.
- [ ] No PII / secrets quoted in the report.
- [ ] Both possible directions named; the skill does NOT pick.

## Output format

The block in "Never silently choose" above. Compact, evidence-first, action-deferred.

For batch reports (e.g., when `/wiki-drift` finds many): one block per discrepancy, sorted by topic, grouped by classification.

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| "The code is newer, so the wiki must be wrong" | Drift may be from code; the wiki could be the team-policy intent | Surface; user picks |
| Update the wiki to match the code without asking | Erases the historical intent; loses the policy record | Report; ask |
| Update the code to match the wiki without asking | Could revert an intentional fix | Report; ask |
| Quote a wiki page that has an embedded secret | Secret in the report | Redact; flag the page as a separate finding |
| Skip the runtime probe because "I read the code" | Feature flag may divert; config may override | Probe |
| Treat "TODO" as a present-state claim | TODO marks intent, not current behavior | Read as target state |
| Treat an archived wiki page as the source of truth | Historical artifact, not current | Check page status header |
| Classify "doc-drift" silently and edit the wiki | Erases the discrepancy without user review | Report; wait |

## Portability rationale

The four-classification model and the never-silently-choose rule apply to any project with both docs and code. The skill does not depend on:

- A specific wiki platform
- A specific code language
- A specific source-of-truth assignment (project-supplied via adapter)

## Cross-references

- `wiki-structure` — when the discrepancy is about wiki organization / link convention, not behavior.
- `wiki-link-validation` — when the discrepancy is a missing cross-reference.
- `wiki-safe-updates` — applied AFTER the user picks the direction.
- `wiki-drift-reporter` (agent) — automates batch drift detection using this skill's classification vocabulary.
- `runtime-reality-check` (if `qa-browser` is also loaded) — runtime probes for behavioral discrepancies.
