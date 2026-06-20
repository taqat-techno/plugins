# Safe doc deletion

Reference for `wiki-safe-updates`. The pre-deletion gate that must pass before removing a docs tree, a wiki page, or a documented section. Read this whenever the request is "delete the old docs", "we migrated this, drop the source", "remove the legacy decisions", or "this section is obsolete, cut it".

Deleting documentation is special because the loss is asymmetric. The author sees a clean diff; the reader sees broken links and a decision that no longer has a home. Git history technically preserves the content, but nobody re-reads a deleted file. So the bar before deletion is high: **prove the content is captured elsewhere, and prove nothing still points at it that you have not handled.**

There are two mandatory checks. Both must pass. Neither is optional, and "the user told me to delete it" does not waive them — the user is trusting the plugin to catch the migration gap they did not see.

---

## Check 1 — Capture-check (is every named decision genuinely captured?)

The doomed content usually contains *decisions* — "we settled on X over Y", "the retry budget is N", "auth uses approach Z". Before deletion, each NAMED final decision must be genuinely captured in the source-of-truth wiki.

### What "captured" means

A decision is captured only when it is **named** in the source-of-truth wiki — there is a heading, a row, a callout, or a sentence that states *this specific decision* as a present-tense fact a reader can find.

A decision is **NOT** captured when:

- It is *scattered* across several pages but never stated as a single named decision. A reader can reconstruct it only by reading three pages and inferring — that is a **migration gap**, not a capture. Treat it as NOT captured and keep the deletion blocked.
- It is *paraphrased* into prose that softens or generalizes it ("we use sensible retry defaults") so the actual value or choice is lost.
- It lives only in a TARGET / aspirational doc (per `wiki-source-of-truth`) — intent is not a record of the decision.
- It lives only in the git history of the file you are about to delete (circular: deleting it is what makes it unfindable).

### How to run the capture-check

1. Enumerate the NAMED decisions in the doomed content. A decision is "named" if it states a choice, a constant, a policy, or a final answer — not merely background.
2. For each, search the source-of-truth wiki for the same decision stated as a present-tense fact. Use the page that *should* own it (the architecture page for an architecture decision, the SOP for a procedure rule, an ADR for a "why").
3. Classify each decision:
   - **CAPTURED** — found, named, present-tense, in the right source-of-truth page.
   - **SCATTERED (gap)** — reconstructable but never named anywhere. Blocks deletion until named.
   - **MISSING** — not present at all. Blocks deletion until added.
4. If any decision is SCATTERED or MISSING, deletion is blocked. The fix is to *name* the decision in the wiki first (through the normal diff-preview write), then re-run the check.

Defer the "is this genuinely the source of truth / is this a TARGET doc" judgement to `wiki-source-of-truth`. This check only asks "is the named decision present in the layer that owns it."

---

## Check 2 — Cross-reference sweep (what still points at this content?)

A deletion that leaves dangling references ships broken links and broken pipelines. Before deleting, grep **every** surface that could reference the doomed content, then categorize each hit. Missing a surface is the common failure — code comments and CI workflows are the ones people forget.

### Where to grep (the target list)

Search for references to the doomed paths, page names, anchor slugs, and any stable identifiers the content defined:

| Surface | Why it matters | What to grep for |
|---|---|---|
| Other wiki pages | Inbound `[label](Page)` and `[label](Page#anchor)` links break | page basename, old slug, section anchors |
| Code comments | `// see docs/...`, docstrings, module headers pointing at the doc | file path, page name, URL fragment |
| CI / pipeline workflows | A workflow step that reads, lints, or publishes the doc fails the build | doc path, generated-artifact name |
| Root README / instruction files | `README`, `CONTRIBUTING`, agent/instruction files (e.g. a repo's CLAUDE.md), onboarding pointers | path, page name, "see the docs at ..." |
| Build / coverage artifacts | Doc coverage manifests, link-check allowlists, site-generator nav configs, sitemap entries | path, slug, nav entry |

Grep across the code repo AND the wiki repo. Anchors (`#section`) count as references — a deleted section breaks `Page#section` links even if the page survives.

### Categorize every hit

Each reference gets exactly one category. Do not delete until all three categories are resolved.

| Category | When | Action (same change set as the deletion) |
|---|---|---|
| **rewrite** | The reference should now point at the captured location in the wiki | Update the link / comment / config to the new target |
| **accept-stale** | The reference is in frozen history, a retired folder, a changelog entry, or otherwise intentionally a point-in-time record | Leave it; note it as knowingly stale so a later audit does not re-flag it |
| **delete-with-target** | The reference exists *only* to point at the doomed content and has no value once it is gone | Remove the reference together with the content |

`rewrite` and `delete-with-target` references MUST be handled in the same change set as the deletion — never "fix later". `accept-stale` is the only category that survives untouched, and it must be a deliberate decision, not a default.

---

## Decision flow

```
deletion requested
  ├─ Capture-check: every named decision CAPTURED in the source-of-truth wiki?
  │     ├─ any SCATTERED or MISSING → BLOCK; name the decision in the wiki first
  │     └─ all CAPTURED → continue
  └─ Cross-reference sweep: all surfaces grepped, every hit categorized?
        ├─ any uncategorized hit → BLOCK; finish the sweep
        ├─ any rewrite / delete-with-target unhandled → BLOCK; handle in this change set
        └─ all resolved → deletion may proceed
```

This checklist is an **optional, advisory** sanity check before deleting wiki content — it does not block you. Removal is typically a `git rm` + commit; `revert` keeps the file recoverable from history if you change your mind.

---

## Output format

```
SAFE-DOC-DELETION REPORT — <target path / page / section>

CAPTURE-CHECK
| Decision (named) | Status | Source-of-truth location |
|------------------|--------|--------------------------|
| <decision>       | CAPTURED | <wiki page#anchor> |
| <decision>       | SCATTERED (gap) | reconstructable only across <pages>; not named |
| <decision>       | MISSING | not found |

CROSS-REFERENCE SWEEP
| Reference | Surface | Category | Action |
|-----------|---------|----------|--------|
| <file:line> | code comment | rewrite | point at <wiki page> |
| <workflow:line> | CI workflow | delete-with-target | remove step |
| CHANGELOG:line | changelog | accept-stale | leave (point-in-time record) |

VERDICT
  Capture-check:    PASS | BLOCKED (<n> scattered/missing)
  Reference sweep:  PASS | BLOCKED (<n> uncategorized / unhandled)
  Deletion:         CLEARED to proceed via diff-preview + push-approval
                    | BLOCKED — <next step>
```

---

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Delete right after "migrating" because the content "is in the wiki now" | The decision may be paraphrased or scattered, never named | Capture-check each named decision; SCATTERED counts as a gap |
| Grep only other wiki pages for references | Code comments, CI, READMEs, and build artifacts also point at docs | Sweep every surface in the target list |
| Categorize a live inbound link as accept-stale to avoid editing it | Ships a broken link to readers | accept-stale is only for frozen / historical references |
| Fix dangling references in a follow-up commit | The broken reference ships in the deletion commit and hits readers/CI immediately | Handle rewrite + delete-with-target in the same change set |
| `git push --force` to "clean up" the deleted file from history | Erases history and breaks anyone's parallel work; the content is meant to stay recoverable | `git rm` + commit + normal push (revert if wrong) |
| Trust "the user said delete it" as a waiver | The user usually cannot see the migration gap; that is what this gate is for | Run both checks regardless; surface what is blocking |
