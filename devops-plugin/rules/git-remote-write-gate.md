# Remote git write gate (permission-first + identity-correctness)

A provider-neutral safety contract that gates every **remote** git write. It does not own commit message style, PR templates, or review ergonomics — the official code-review, commit-commands, and github/GitLab/Azure plugins own those. This rule is only the gate that runs *before* a remote write is allowed to proceed.

## Scope

This rule applies to any operation that mutates a remote: `push`, force-push, branch/tag delete on remote, opening or updating a pull/merge request, merging, and tagging or publishing a release. It is provider-neutral and covers GitHub, GitLab, Azure Repos, and any other remote-backed host. Domain skills reference this file rather than re-implementing the checks.

Local-only actions — staging, local commits, local branch creation, diffing, status — are out of scope. The gate engages at the moment work would leave the local machine.

## Gate 1: permission-first

Never push, open a PR/MR, merge, or release without **explicit user approval** for that specific action. A prior "go ahead" on an earlier, different remote write does not carry over.

Before requesting approval, surface exactly what will leave the machine so the user can judge it:

- the target remote and ref (which remote, which branch/tag).
- the proposed commit message(s) for anything not yet pushed.
- the changed-file list (paths only — never file contents that may carry secrets).
- the action verb: push vs. open-PR vs. merge vs. release.

Then **stop and wait** for an explicit affirmative. Treat silence, ambiguity, or an unrelated instruction as "not approved." Re-ask if the plan changed after approval was given (different branch, added files, amended message).

Do not bundle multiple remote writes behind one approval unless the user explicitly approved the whole sequence.

## Gate 2: identity-correctness

Before any remote write, confirm the active CLI identity is allowed to write to the target repository.

1. **Detect the target owner** from the remote URL (the org/user/namespace segment of the configured remote).
2. **Detect the active identity** from the provider CLI's current auth/account state.
3. **Compare.** If owner and active identity are consistent, proceed to Gate 1's approval step.
4. **On mismatch: REPORT and ASK.** State the detected target owner and the active identity, and ask the user how to proceed. Do **not** auto-switch identities by default.

### When auto-switch is allowed

Auto-switching is permitted **only** when the project has explicitly configured an `owner -> identity` mapping (for example in a project rule or settings file the user maintains). When such a mapping exists and it resolves the detected owner unambiguously:

- switch to the mapped identity,
- perform the approved remote write,
- then **switch back to the default identity** afterward, leaving the environment as it was found.

Absent an explicit mapping, mismatch always falls through to REPORT-and-ASK. Never guess an identity, never invent a mapping, and never persist a credential change the user did not ask for.

### Adapter inputs (provider-neutral)

The gate consumes abstract values, not provider-specific commands, so it works across hosts:

- `target_owner` — owner/org/namespace parsed from the remote URL.
- `active_identity` — the currently authenticated account reported by the host CLI.
- `owner_identity_map` — optional, project-configured `{owner: identity}` mapping; absent by default.
- `default_identity` — the identity to restore to after a mapped switch.

Example (illustrative — not required):

```
remote URL        -> owner segment            -> target_owner = "<owner-a>"
host CLI auth     -> active account           -> active_identity = "<identity-1>"
project mapping   -> { "<owner-a>": "<identity-2>" }   # only if user configured it
=> mismatch + mapping present => switch to <identity-2>, write, restore <identity-1>
=> mismatch + no mapping      => REPORT "<owner-a> vs <identity-1>" and ASK
```

The bracketed placeholders above are stand-ins. Plugin behavior must never depend on any literal owner, identity, repo, or org name.

## Safety gates checklist

Run top to bottom before any remote write. Any failed gate halts the operation.

- [ ] **Scope check** — confirmed the action is a remote write (this rule applies).
- [ ] **Disclosure** — surfaced target remote/ref, commit message(s), and changed-file paths.
- [ ] **Explicit approval** — got a clear affirmative for *this* specific action; re-asked if the plan changed.
- [ ] **Owner detected** — parsed `target_owner` from the remote URL.
- [ ] **Identity detected** — read `active_identity` from the host CLI.
- [ ] **Match or resolve** — identities consistent, or mismatch handled (auto-switch only with an explicit `owner_identity_map`, otherwise REPORT-and-ASK).
- [ ] **No secrets emitted** — never printed tokens, credentials, env values, or file contents.
- [ ] **Restore** — if an identity was switched via mapping, restored `default_identity` after the write.

## Non-goals

- This rule does not format commit messages, build PR/MR descriptions, or run reviews — defer to the owning command/skill/plugin for those.
- This rule does not authenticate, store, or rotate credentials — it only reads the host CLI's reported state and, when explicitly mapped, asks the host CLI to switch and restore.
- This rule never prints secrets, tokens, or environment values under any circumstance.
