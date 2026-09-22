---
name: sprint-evidence-correlation
description: How sprint-recap correlates Azure DevOps work items, git commits and Claude session transcripts into one evidence set. Owns the work-item-ID join key, the year-vs-ID false-positive rule, per-source degradation, and what to do with unattributed commits. Use when running the collect stage or when sprint evidence looks incomplete or wrongly attributed.
version: 0.3.0
last_reviewed: 2026-09-22
owns:
  - the work-item ID join key and its false-positive rules
  - reading references from the commit body, explicit-only
  - per-source degradation reporting
  - unattributed-commit handling
defers_to:
  - sprint-step-script (turning evidence into a demo script)
---

# Correlating three sources

Three sources answer three different questions:

| Source | Answers | Weakness |
|---|---|---|
| Azure DevOps iteration | what the board says shipped | titles rarely describe a click-path |
| git commits in the window | what actually shipped | says nothing about the UI |
| Claude session transcripts | how it was built | noisy, local to one machine |

## The join key

Work-item ID, scraped from commit subjects, commit **bodies**, branch refs and
prompts:

- `#23923`, `AB#23923` — explicit, always trusted, wherever it appears.
- `feature/23923-donor-export`, `bugfix_23940` — branch-style, trusted at a
  token boundary.
- A bare four-digit number that looks like a year (`19xx`, `20xx`) is rejected.
  Without that rule `release/2026-planning` invents work item 2026 and silently
  attaches half the sprint's commits to it.
- A token that is **nothing but digits** is rejected outright. In prose a bare
  number is a status code, a port, a count or a version: "serve a favicon
  instead of a 404 on every page" must not file that commit under work item
  404. A real branch-style reference always carries its delimiter.

**Read the body, not just the subject.** Plenty of teams keep the subject
prose-only and put every reference in a trailer — `Closes #33724 #33727
#33730`. Matching on subject and refs alone correlates almost nothing for
them, and the damage is silent: the run reports a small number of matched
items and a large `unattributed` pile, which reads like a team that does not
reference work items rather than like a parser that cannot see them. On one
real sprint that was 0 subject references against 49 body-only commits hiding
111 work items.

Body matching is explicit-only. The branch-style rule is right for a ref,
where the delimiter carries the meaning; applied to free prose it manufactures
the false positives above. The per-repo note reports how many commits matched
on a body reference alone, so a sudden change in that number is visible rather
than buried.

Transcripts carry `gitBranch` and `cwd` per message, so a session is usually
attributable even when the prompts never mention an ID.

## Degradation is per-source, never fatal

A missing `az` CLI, an unreadable repo or an absent transcript directory
downgrades that one source and is recorded in `sources`. The run continues.

**Report what was actually collected.** If Azure DevOps was unavailable, the
evidence is git plus transcripts and the sprint's scope is whatever branched in
that window — say so rather than implying board-level completeness.

When no board data exists at all, items are synthesised from IDs found in
commits. That is a fallback, not a substitute: those items have no title, state
or parent PBI.

## Unattributed commits

A commit with no work-item reference lands in `unattributed`. Do not force it
onto the nearest item. It usually means one of:

- a hotfix that skipped the board — worth surfacing to the user
- chore/infra work with no demo value — correctly excluded
- a team that does not reference IDs in commits — in which case correlation is
  weak for the whole sprint and the step script needs manual scoping

Surface the count. A sprint where most commits are unattributed is a sprint whose
video will miss things, and the user should learn that before the capture runs.
