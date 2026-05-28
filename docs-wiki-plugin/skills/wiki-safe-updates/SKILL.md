---
name: wiki-safe-updates
description: Safe workflow for editing and publishing wiki pages — diff preview before write, push-approval gate (no push without explicit user "push approved"), no force-push ever, retired-folder awareness (folders intentionally archived are not "drift"), rollback strategy via revert (never reset --hard). Activates before any wiki write or wiki git push.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - diff-preview-before-write contract
  - push-approval gate (explicit user phrase required)
  - no-force-push rule
  - retired-folder awareness
  - revert-based rollback strategy
  - one-purpose-per-commit rule for wiki changes
defers_to:
  - wiki-structure (the structural rules a change must respect)
  - wiki-link-validation (run before push to catch breakage)
  - wiki-code-vs-docs-discrepancy (when a wiki update would resolve a code/wiki gap; the user must decide direction first)
  - project release SOP (any project-specific wiki-publishing convention)
user_invocable: false
---

# wiki-safe-updates

## Purpose

A wiki publishes to readers the moment its repo is pushed. There is no review queue, no PR by default, no staging — `git push` is the deploy. This skill owns the safeguards that prevent the most-painful classes of accidents: silent overwrites, premature pushes, force-pushes that erase history, and "drift" reports on folders that were intentionally archived.

The skill is the gate. Every command that writes the wiki (`/wiki-init`, `/wiki-new`, `/wiki-update`, `/wiki-audit --fix`) goes through it.

## When to use

Activate before:

- Any `Write` or `Edit` to a file inside the wiki repo path.
- Any `git push` from the wiki repo.
- Any wiki-side cleanup ("remove orphan pages", "rename for collision").
- Any rollback action.

Skip when:

- The work is purely a read / audit (`/wiki-audit` without `--fix`).
- The work is on the main repo, not the wiki repo (the main repo has its own review process).

## Inputs

- Wiki repo path (from adapter cache).
- The specific files being written / edited.
- The user's expectation (initialise / add page / edit existing / push / rollback).
- The retired-folder list (folders intentionally archived; see `wiki-vs-stray-docs`).

## The diff-preview-before-write rule

For ANY edit to an existing wiki file:

1. Read the current file content.
2. Compute the diff between current and proposed.
3. Show the diff to the user inline.
4. Wait for explicit confirmation before applying.

```
PROPOSED CHANGE — wiki/Deploy-SOP.md

  --- current
  +++ proposed
  @@ -42,7 +42,9 @@
   1. Run `./deploy.sh` from the build server.
  -2. Verify the deploy via `/health`.
  +2. Verify the deploy via the `/api/health` endpoint.
  +3. Confirm the env label on the landing page matches the URL.
   4. Update the deploy log.

  Apply this change? [yes / no / edit]
```

Three response paths:

- `yes` → apply the edit; report the new file path.
- `no` → discard the proposed edit; report no change.
- `edit` → user wants to refine; surface the proposal and let them adjust before applying.

For NEW files (no existing content to diff):

```
PROPOSED NEW PAGE — wiki/Restart-API-Runbook.md
  Size: 142 lines
  Template: runbook
  First 20 lines:
    # Restart the API
    ...
  Apply? [yes / no / edit]
```

The diff-preview is non-negotiable. The plugin does not allow "just write the file" mode.

## The push-approval gate

The wiki repo's `git push` is a publish. Apply this rule:

```
NEVER push the wiki without an explicit user statement to push.
```

Implementation:

- The plugin's `PreToolUse` hook on `Bash(git push)` against any path containing `.wiki` (or matching the adapter's wiki-path pattern) BLOCKS the push.
- The block prints the explicit confirmation phrase required: `push approved` (configurable, lowercase, exact match).
- The user must type the phrase in the conversation before the next `git push` invocation runs.
- The approval is for one push. The next push re-prompts.

The plugin commands never call `git push` themselves. Push is always an explicit human action.

## No force-push, ever

The wiki repo's history is the record of what was published when. Force-push erases that record and breaks any external link to a specific revision.

```
REFUSE: git push --force / git push -f / git push --force-with-lease
```

The plugin's PreToolUse hook also blocks force-push variants. If the user truly needs to rewrite history (rare and dangerous), they must:

1. Disable the hook for the session (explicit step).
2. Document the reason in the wiki repo's commit message or notes.
3. Re-enable the hook.

The plugin never automates around this.

## Retired-folder awareness

Some folders in a wiki are intentionally archived: `_archived/`, `_deprecated/`, `historical/`, `_old/`, `attic/`. Their contents are NOT current; readers should not follow links from them; auditors should not flag them as "drift".

The retired-folder list is per-project, supplied via adapter:

```json
{
  "retiredFolders": ["_archived/", "_deprecated/", "_legacy/"]
}
```

Effect:

- `wiki-link-validation` skips orphan reporting for pages inside retired folders.
- `wiki-code-vs-docs-discrepancy` does not flag a retired page as in contradiction with current code.
- `wiki-vs-stray-docs` does not warn about retired folder existence.
- Diff-preview still applies to retired-folder writes — historical content is still editable.

## One-purpose-per-commit rule

Wiki commits should be one-purpose:

- One commit for content edits on one topic.
- A separate commit for a rename.
- A separate commit for a sidebar update.
- A separate commit for a navigation reorganization.

Why: when a wiki page goes wrong (e.g., a broken link slipped through), the maintainer reverts THAT commit. Mixed-purpose commits force "revert + manually re-add" recovery.

Commit message format (project may override):

```
[<area>] <one-line subject>

<optional body explaining the change>

Reviewed-by: <person> (optional)
```

`<area>`:

- `[SOP]` SOP page change
- `[RUNBOOK]` runbook change
- `[ARCH]` architecture / system doc
- `[NAV]` sidebar / Home navigation
- `[ARCHIVE]` move to retired folder
- `[FIX]` link fix, typo, collision rename
- `[STRUCT]` structural change

## Revert-based rollback

When a wiki change goes wrong:

```
git -C <wiki-repo-path> revert <commit-sha>
# review the revert commit's diff
# git push (with the push-approval gate)
```

Never `git reset --hard`, never `git push --force`. Revert keeps history intact and signals "we tried; we rolled back" rather than "we pretend this never happened."

For multi-commit rollback: `git revert <oldest-bad>..<newest-bad>` produces one revert commit per bad commit (or use `-n` to stage all and commit once with a clear message).

## Safety gates

- **Never** write a wiki file without diff preview.
- **Never** push the wiki without the explicit user confirmation phrase.
- **Never** force-push (`--force`, `-f`, `--force-with-lease`).
- **Never** use `git reset --hard` on the wiki repo.
- **Never** combine multiple unrelated changes in one wiki commit.
- **Never** flag retired-folder content as drift.
- **Never** auto-resolve a `wiki-link-validation` finding without user review.
- **Never** modify `_Sidebar.md` or `Home.md` without diff preview + maintainer confirmation.

## Validation checklist

Before each wiki write:

- [ ] Diff preview shown.
- [ ] User explicitly confirmed `yes`.
- [ ] Target file inside the wiki repo path (no escape).
- [ ] No secrets / PII in the proposed content (scan before write).

Before each wiki push:

- [ ] User typed the confirmation phrase in this session.
- [ ] `git status` is clean except for the intended commits.
- [ ] `git log <branch> --not <remote>/<branch>` shows the commits about to publish.
- [ ] Link validation ran AND surfaced no HIGH findings.
- [ ] No force-push flag in the command.

## Output format

For a write proposal:

```
PROPOSED WRITE — <file>
  Mode: <new | edit>
  Diff: <inline diff for edits | first N lines for new files>
  Scan: no secrets detected | <finding>
  Apply? [yes / no / edit]
```

For a push proposal:

```
PROPOSED PUSH — <wiki-repo-path>
  Branch: master
  Commits about to publish: <count>
    <sha-short> <subject>
    <sha-short> <subject>
  Link validation: PASS (0 HIGH findings)
  Confirmation phrase required: push approved
  (waiting for user input...)
```

For a refused operation:

```
REFUSED — <action>
  Reason: <missing diff preview | no push approval | force-push attempted | secret detected | retired-folder spurious flag>
  How to proceed: <step the user can take>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Write the wiki file in one shot, no diff | User has no chance to catch a wrong edit | Diff preview |
| Push the wiki because the user said "okay" earlier | Approval drift; "okay" was for the edit, not the publish | Explicit phrase per push |
| Force-push to fix a bad commit | Erases the bad commit AND anyone else's parallel work | Revert + push |
| Bundle navigation + content edits in one commit | Rollback either reverts both or neither | One purpose per commit |
| Flag `_archived/Old-SOP.md` as drift | The archive is intentional | Retired-folder awareness |
| Apply a `wiki-link-validation` suggestion automatically | The suggestion may be wrong | User confirms |
| Silently overwrite an existing wiki page on `/wiki-new` | Content loss with no diff trail | Refuse; surface the collision |
| Skip diff preview "because it's a small typo" | Small typos sometimes turn out to be in a code block where they break the example | Always preview |

## Portability rationale

The diff preview, approval gate, and force-push refusal apply to any wiki backed by git. The skill does not depend on:

- A specific git hosting platform
- A specific markdown renderer
- A specific commit-message format (project overrides)

For non-git wikis (Confluence, etc.), the diff-preview and approval-gate concepts still apply but the implementation differs; this skill targets git-backed wikis explicitly.

## Cross-references

- `wiki-structure` — rules a write must respect.
- `wiki-link-validation` — runs before push.
- `wiki-code-vs-docs-discrepancy` — runs before a wiki edit that intends to resolve a code-wiki gap.
- `wiki-vs-stray-docs` — refuses certain new-file writes outside the wiki.
- `wiki-link-auditor` (agent) — automates the pre-push link validation.
- `wiki-cleanup-validator` (agent) — pre-delete reference check before removing a wiki page.
- Plugin `hooks/hooks.json` — implements the push-approval gate at tool level.
