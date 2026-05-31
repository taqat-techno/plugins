---
name: react-lint-triage
description: Treats analyzer and linter findings (react-doctor, eslint, deslop, knip, and similar) as hypotheses to verify, not commands to obey. Owns the four-bucket classification (safe-mechanical, needs-judgment, false-positive, forbidden-zone), the false-positive catalog, and the rules against score-chasing and ruleset drift. Activates when triaging lint, static-analysis, or quality-tool output, before applying any auto-fix, before deleting a file a dead-code tool flagged, or when a tool reports a quality score to improve.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - four-bucket finding classification (safe-mechanical / needs-judgment / false-positive / forbidden-zone)
  - the false-positive catalog (runtime-throwing destructure, intentional derived state, array-index keys, trusted dangerouslySetInnerHTML, label over-fire, alias-blind dead-file detectors)
  - the "findings are hypotheses, not commands" discipline
  - the no-score-chasing rule (eliminate one rule fully before shaving counts)
  - the tool-version pinning rule (rulesets drift across runs)
  - the changed-file-set impact measurement rule
defers_to:
  - react-doctor (the separate scanning tool/skill that produces findings; this skill triages what it emits)
  - data-fetching-states (verdicts about loading/error/empty findings)
  - react19-migration (verdicts about deprecated-API findings)
  - admin-* skills (verdicts about admin-UI-specific findings)
  - the project's own observability/CI configuration (the source of truth for which zones are forbidden)
user_invocable: false
---

# react-lint-triage

## Purpose

A linter or analyzer says "fix this." It is wrong often enough that obeying every finding ships bugs, deletes live code, and lowers a vanity score while raising real risk. This skill reframes every finding as a hypothesis that must survive a read-only investigation before any edit, and sorts each one into exactly one of four buckets so the safe ones get applied and the dangerous ones get stopped.

## When to use

Activate when:

- Triaging the output of any analyzer or linter (react-doctor, eslint, deslop, knip, ts-prune, or similar).
- About to run an auto-fix (`eslint --fix`, a codemod, a "quick fix all").
- About to delete a file because a dead-code / unused-export tool flagged it.
- A tool reports an aggregate quality score and the goal is "raise the score."
- Reviewing a PR whose entire content is "address lint findings."

## Inputs (adapter)

Every project-specific value is a named adapter input. Nothing below is hardcoded into the skill's behavior.

1. **ANALYZERS** — which tool(s) produced the findings (e.g. eslint, react-doctor, knip, deslop). Determines how findings are parsed and grouped.
2. **TOOL_VERSIONS** — the exact version + ruleset hash of each analyzer for this triage run. Recorded so a later run is comparable.
3. **FORBIDDEN_ZONES** — the list of paths/domains where a cosmetic finding must never trigger an edit. The project defines these. Common shapes: authentication, payments/billing, exam/assessment logic, wallet/ledger, database migrations, CI/deploy config. The skill ships the *category*; the project supplies the *paths*.
4. **ALIAS_ROUTE_MAP** — how the project resolves path aliases (tsconfig `paths`, bundler aliases) and how its framework builds the route graph. Required before trusting any dead-file signal.
5. **CHANGED_FILE_SET** — the set of files this triage is allowed to touch. Impact is measured here only.

## Read-only investigation steps

No edits in this phase. Build the picture first.

1. **Capture the run.** Record ANALYZERS + TOOL_VERSIONS. If a previous triage exists, confirm the versions match; if they drifted, note it — counts are not comparable across ruleset changes.
2. **Group findings by rule, not by file.** One rule firing 40 times is one hypothesis to test once, not 40 decisions.
3. **For each rule, read one real instance** in source before judging. Open the flagged line and its surrounding component.
4. **Check the location against FORBIDDEN_ZONES** before reading anything else — if it lands there and the finding is cosmetic, the verdict is decided regardless of the rule.
5. **For dead-file/unused signals, resolve through ALIAS_ROUTE_MAP** — confirm the file is not reached via an alias import or a framework route before believing it is dead.
6. **Note runtime semantics** the linter cannot see: bound `this`, intentional derived state, index-based list mutation, trusted content sources.

## Decision framework

### The four buckets

Classify each finding (or each rule, when uniform) into exactly one bucket.

| Bucket | Meaning | Action |
|---|---|---|
| safe-mechanical | Pure syntax/format, no behavior change, no judgment (import order, unused import, `===`, missing `key` where a stable id exists) | Apply |
| needs-judgment | Could be right, but changing it alters behavior or design (effect deps, memoization, refactors, state shape) | Defer with a documented reason; escalate to a human or the owning skill |
| false-positive | The tool is wrong here (see catalog below) | Skip + record why, so the next run does not re-litigate it |
| forbidden-zone | Lands in a FORBIDDEN_ZONES path and the finding is cosmetic | Never touch for this finding; route to the zone's owner |

```
finding ──> in FORBIDDEN_ZONES & cosmetic? ──yes──> forbidden-zone (stop)
              │no
              ▼
            matches false-positive catalog? ──yes──> false-positive (skip + record)
              │no
              ▼
            behavior/design change? ──yes──> needs-judgment (defer + reason)
              │no
              ▼
            safe-mechanical (apply)
```

### Scoring discipline

- **Never chase an aggregate score.** A lower number is not a goal; correct code is.
- For **rule-count scorers**, prefer **fully eliminating one rule** (so it can be enabled as an error and stay at zero) over shaving a few counts off many rules. Zero-of-one beats a-bit-less-of-ten.
- **Pin TOOL_VERSIONS across runs.** Rulesets drift; a count change between runs may be the ruleset moving, not the code.
- **Measure impact on CHANGED_FILE_SET only.** A global score moving is noise; what this triage changed is signal.

### False-positive catalog

These are recurring cases where the tool is usually wrong. Examples are illustrative — not required; the principle is what carries.

| Finding the tool raises | Why it is often a false positive | Correct verdict |
|---|---|---|
| "Destructure the method off a hook return" — Example (illustrative — not required): `const { get } = useSearchParams()` then `get('x')` | The native method is `this`-bound; detached it throws at runtime (`URLSearchParams.prototype.get` needs its receiver). Only stable, already-bound methods are safe to destructure. | false-positive — keep `params.get('x')`; do not destructure bound native methods |
| `no-derived-state` / "don't sync props into state" | Frequently intentional: form-reset-on-open, debounce mirror, cascading reset of dependent fields, a controlled snapshot taken at mount. | needs-judgment — inspect the intent; "fixing" it can break the reset/snapshot behavior |
| Array-index used as `key` | Fine when a stable unique id already exists on the item, when the value itself is unique, or when the list only ever mutates by index (append/replace-at-index). | needs-judgment — do not invent a synthetic key when a stable id is present; only fix true reorder-with-identity bugs |
| `dangerouslySetInnerHTML` flagged as XSS | When the HTML is trusted server-rendered or staff-authored content, this is AUDIT-ONLY. | false-positive for the cosmetic auto-fix — do NOT add a sanitizer dependency mid-cleanup; record an audit note instead |
| `control-has-associated-label` / `jsx-a11y` label rule | Over-fires when a visible `<label for>` already associates the control (adding `aria-label` clobbers the visible label) and on empty table header cells used for spacing. | false-positive — verify a visible label is absent before adding one; do not double-label |
| Dead-file / unused-export (knip, ts-prune) flags a file for deletion | Detectors that ignore path aliases and the framework route graph are ~95% false positive — alias imports and route-graph entrypoints look "unreferenced." | false-positive until proven — verify with an alias+route-aware tool (ALIAS_ROUTE_MAP) before deleting anything |

### Admin-panel triage

Admin UIs (list/detail tables, toolbars, drawers, status pipelines, bulk actions) produce a recurring family of findings. Triage them with the same four buckets and the same never-chase-the-score rule — these are just the shapes that show up most in data-grid code. Defer any domain verdict to the owning `admin-*` skill.

| Finding shape in admin code | How to triage | Bucket |
|---|---|---|
| Array-index `key` on table rows (`key={i}`) | Fix **only** when a stable unique id already exists on the row record (`key={row.id}`). If no stable id exists, **never invent a synthetic key** to silence the rule — index keys are correct for append/replace-at-index lists. | safe-mechanical when a stable id is present; otherwise false-positive (record why) |
| Complex conditional logic inline in render (nested ternaries choosing a status label/color/icon) | Extract a **small** helper or a flat status map (e.g. `STATUS_STYLE[status]`). Do **not** over-abstract into a config layer, a hook, or a component just to flatten one ternary. | needs-judgment — apply only the minimal extraction; the rule is advisory |
| Duplicated action/transition logic across a row action, a bulk action, and a detail-drawer action (the same approve/delete/advance written three times) | This is a **real maintainability finding**, not style. Consolidate into one action handler that takes one-or-many ids, so row/bulk/drawer all call the same path and stay consistent. | needs-judgment — genuine consolidation; verify all three call sites share semantics before merging |
| Component over-splitting flagged (a table + toolbar + pagination shattered into many tiny single-use files) | A cohesive data-grid living in one well-organized file is fine. Sometimes the splitter finding is simply **wrong** — do not merge or split files just to move a count. Only consolidate when the fragments are truly single-use and obscure the grid. | needs-judgment, and often false-positive — never restructure files to satisfy the metric |

Admin-specific false positives to skip outright:

- **Permission-gated action handlers flagged as "unreachable" / dead.** A handler only invoked when `canEdit`/`canManage` is true looks dead to a static tool that cannot see the runtime gate. Verify the gate, then skip — do not delete the handler. (Treat the route/handler the same way the dead-file rule treats alias-reached files: false-positive until proven.)
- **Backend-enforced scoping marked as "missing UI filter."** When the API already scopes records (viewer sees own, manager sees team, admin sees all), a finding that the list "does not filter client-side" is a false positive — client-side filtering is not the security boundary and must not be added to satisfy it.
- **Conditionally rendered cell/field flagged as a missing `key` or empty element.** Cells hidden by a field-access gate (redacted/role-gated columns) over-fire the same a11y/empty-element rules already in the catalog. Verify the gate before touching.

Never restructure an admin component, merge/split its files, or add a client-side filter purely to lower a count — the changed-file diff carries risk for a vanity number. Same rule as everywhere else: eliminate one rule to zero, or skip.

## Safety gates

- **Never** delete a file on a dead-file signal alone — require alias + route-graph confirmation first.
- **Never** run an auto-fix that touches a FORBIDDEN_ZONES path for a cosmetic finding.
- **Never** refactor purely to lower a score.
- **Never** add a new dependency (e.g. a sanitizer) to satisfy a lint finding mid-cleanup — that is a design decision, not a triage fix.
- **Never** destructure a `this`-bound native method off a hook/object return to satisfy a finding.
- **Never** treat counts from two runs with different TOOL_VERSIONS as comparable.
- **Never** mass-apply `--fix` across the repo; scope to CHANGED_FILE_SET and review the diff.
- **Never** re-litigate a recorded false-positive on the next run — the record exists so it stays skipped.

## Validation checklist

Before committing a triage's edits:

- [ ] Every applied finding is bucket = safe-mechanical (no behavior change in the diff).
- [ ] Every needs-judgment finding is deferred with a written reason, not silently applied.
- [ ] Every skipped finding has a recorded false-positive reason.
- [ ] No edit touches a FORBIDDEN_ZONES path for a cosmetic finding.
- [ ] No file was deleted without alias + route-graph confirmation.
- [ ] No new dependency was added to satisfy a finding.
- [ ] TOOL_VERSIONS recorded; counts compared only against a same-version run.
- [ ] Impact measured on CHANGED_FILE_SET only.
- [ ] If a rule was fully eliminated, it is (or can be) promoted to error to stay at zero.

## Output format

The skill emits one per-finding decision table plus a short run header.

```
TRIAGE RUN
  analyzers:      <ANALYZERS>
  tool_versions:  <TOOL_VERSIONS>
  changed_files:  <CHANGED_FILE_SET>

| Finding (rule @ location)        | Bucket          | Verdict | Action / Reason                                  |
|----------------------------------|-----------------|---------|--------------------------------------------------|
| no-key @ List.tsx:42             | safe-mechanical | apply   | stable item.id exists; add key={item.id}         |
| derived-state @ Modal.tsx:18     | needs-judgment  | defer   | form-reset-on-open is intentional; owner reviews |
| destructure-get @ Search.tsx:9   | false-positive  | skip    | params.get is this-bound; detaching throws       |
| no-key @ AuthGate.tsx:30         | forbidden-zone  | skip    | auth path; cosmetic finding — route to owner     |

SUMMARY: <n applied> / <n deferred> / <n skipped> / <n forbidden>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Run `eslint --fix` across the repo and commit | Mixes behavior changes with formatting; deletes/rewrites live code blindly | Bucket first; apply only safe-mechanical, scoped to CHANGED_FILE_SET |
| Delete files knip/ts-prune flagged as unused | Alias imports and route entrypoints look unreferenced; ~95% false positive | Confirm via ALIAS_ROUTE_MAP before any deletion |
| Refactor components to drop the score from 120 to 90 | Score is a proxy; the diff added risk for a vanity number | Eliminate one rule to zero, or skip — never refactor for the number |
| Destructure `const { get } = useSearchParams()` to satisfy a hint | `get` is `this`-bound; detached call throws at runtime | Keep `params.get(...)`; never destructure bound native methods |
| Add a sanitizer dep to clear a `dangerouslySetInnerHTML` warning | Introduces a dependency + design change inside a cleanup pass | Audit-only for trusted content; record a note, do not add deps |
| Add `aria-label` wherever the a11y rule fires | Clobbers an existing visible `<label for>`; over-fires on empty header cells | Verify no visible label first; skip empty-cell false positives |
| "Fix" no-derived-state everywhere it fires | Breaks intentional form-reset / debounce-mirror / snapshot patterns | Inspect intent; defer as needs-judgment |
| Compare finding counts across runs with different tool versions | Ruleset drift moves counts independently of the code | Pin TOOL_VERSIONS; compare same-version runs only |

## Portability rationale

This skill is framework- and tool-agnostic. It hardcodes no project, path, domain term, or URL. The analyzers, forbidden zones, alias/route resolution, versions, and changed-file scope are all named adapter inputs. The false-positive catalog encodes JavaScript/React runtime semantics and tooling blind spots that hold across any codebase, with concrete cases labeled illustrative so the principle — not the example — is what ports.

## Cross-references

- `react-doctor` (separate tool/skill) — produces the findings this skill triages; this skill does not scan, it judges.
- `data-fetching-states` — owns verdicts on loading/error/empty-state findings.
- `react19-migration` — owns verdicts on deprecated/removed-API findings.
- `admin-states`, `admin-crud`, `admin-forms` and other `admin-*` skills — own verdicts on admin-UI-specific findings; defer there.
- The project's observability/CI config — the source of truth for FORBIDDEN_ZONES and ALIAS_ROUTE_MAP.
