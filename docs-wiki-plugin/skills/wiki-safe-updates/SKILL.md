---
name: wiki-safe-updates
description: Optional best-practice tips for editing and publishing a GitHub wiki — preview a diff before a big overwrite, prefer git revert over reset --hard for rollback, one purpose per commit, retired-folder awareness, and an optional reference check before deleting a page. Purely advisory and non-blocking — the plugin does NOT gate git push, force-push, or Write/Edit. Help, not gates.
version: 1.0.0
last_reviewed: 2026-06-20
owns:
  - diff-preview suggestion (optional)
  - revert-based rollback tip
  - one-purpose-per-commit tip
  - retired-folder awareness
  - optional reference check before deleting a page
defers_to:
  - wiki-structure (structural conventions a write may follow)
  - wiki-link-validation (optional pre-push broken-link sweep)
  - wiki-code-vs-docs-discrepancy (optional code-vs-wiki drift report)
  - project release SOP (any project-specific wiki-publishing convention)
user_invocable: false
---

# wiki-safe-updates

## Purpose

Helpful, **optional** tips for working on a GitHub wiki. None of this blocks you — the
plugin imposes **no gates** on writing, pushing, force-pushing, or deleting. Use what's
useful; skip what isn't. A GitHub wiki publishes the moment its repo is pushed
(`git push` is the deploy), so these tips just help avoid the common foot-guns.

## Tips

**Preview before a big overwrite (optional).** For a large edit to an existing page it
can help to glance at the diff first so a wrong edit is easy to catch — but writing the
file directly is completely fine when you already know what you want.

**Rollback with revert (keeps history).** If a change goes wrong:

```
git -C <wiki-repo-path> revert <commit-sha>
git -C <wiki-repo-path> push
```

`git reset --hard` and force-push also work if you prefer them — your call. `revert` is
just friendlier because it preserves the published history.

**One purpose per commit (optional, tidier rollback).** Keeping content edits, renames,
and sidebar/navigation changes in separate commits makes a single `revert` clean. Mixed
commits are fine too.

**Retired-folder awareness.** Folders intentionally archived (`_archived/`,
`_deprecated/`, `historical/`, `_old/`, `attic/`) hold non-current content. The audit
skills skip them so they aren't flagged as "drift":

```json
{ "retiredFolders": ["_archived/", "_deprecated/", "_legacy/"] }
```

**Before deleting a page (optional sanity check).** Deleting a page breaks any inbound
links to it. If you'd like, grep for references first — `references/safe-doc-deletion.md`
has a checklist — but it's a suggestion, not a requirement.

## Pushing

Pushing the wiki is **unrestricted** — there is no approval gate and no force-push block.
Push whenever you're ready:

```
git -C <wiki-repo-path> push origin master
```

## Cross-references

- `wiki-structure` — structural conventions a write may follow.
- `wiki-link-validation` — optional pre-push broken-link sweep.
- `wiki-code-vs-docs-discrepancy` — optional code-vs-wiki drift report.
- `wiki-vs-stray-docs` — suggests (does not force) keeping team docs in the wiki.
- `references/safe-doc-deletion.md` — optional pre-deletion checklist.
- `wiki-link-auditor` (agent) — automates the optional pre-push link validation.
