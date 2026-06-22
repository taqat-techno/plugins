---
name: release-verification
description: Proves a fix is actually deployed to the TARGET environment, not merely merged. Reconciles the deployed commit SHA to the environment (verify the fix commit is contained in the branch AND that the branch maps to that environment per the deploy config); diffs env-driven secrets between source and target before promoting (a migration or feature needing an env key the target lacks fails the deploy); forces the resolved connection host/name to be printed FIRST because a remote DB command can silently fall back to a local DB / sqlite when the public connection URL is empty; and catches lockfile / package-manager MAJOR mismatches that break CI installs. Provider-neutral across any Git host, CI system, and hosting provider. Activates when someone asks "is the fix live?", "did it deploy?", "verify the release", or before promoting between environments.
version: 0.2.0
last_reviewed: 2026-06-22
owns:
  - the "FIXED means proven in the target environment, not merged" discipline
  - the deployed-SHA -> environment reconciliation (branch containment AND branch-to-environment mapping)
  - the env-secret diff (by key NAME and presence only) before promotion
  - the resolved-connection-target print-first rule (guard against silent local fallback)
  - the lockfile / package-manager parity check
  - the report-only-gate detection (a gate with `|| true` / `continue-on-error` surfaces findings but does not block)
  - the RELEASE VERIFICATION REPORT output contract
defers_to:
  - migration-safety skill for the risky-migration / cutover skeleton and destructive/CASCADE review
  - references/deployed-sha-reconciliation.md for the SHA-to-environment procedure
  - references/env-secret-diff.md for the by-name secret-diff procedure
  - the deploy config of each project for branch-to-environment mapping and env-var source
user_invocable: false
---

# release-verification

## Purpose

"I merged the fix" and "the fix is running in the environment the user is complaining about" are different claims, and conflating them is the most common false "it's fixed." This skill encodes the discipline that **FIXED means PROVEN IN THE TARGET ENVIRONMENT** — backed by the actual deployed commit SHA, an env-key diff, a resolved connection target, and lockfile parity — never by a merge alone.

## When to use

Activate when any of these appear:

- "Is the fix live?", "did it deploy?", "is it on prod/staging yet?", "verify the release."
- Before promoting a build or branch from one environment to the next.
- A bug reported as fixed still reproduces in the target environment.
- A deploy "succeeded" but behaviour did not change.
- A migration or feature depends on an env key and you are about to promote.
- CI install fails after a dependency change (possible lockfile / package-manager mismatch).

Do NOT activate for the mechanics of running a risky migration or cutover — that is the **migration-safety** skill. This skill verifies; that skill executes safely.

## Inputs (adapter)

Every project-specific value is a named adapter input. Nothing below is hardcoded to a vendor.

1. **`git_host` / `ci_system`** — discovered from the remote and the CI workflow files present. Selects how to query build/deploy metadata.
2. **`hosting_provider`** — discovered from the deploy config. Selects how to read the running revision and the env-var source.
3. **`target_environment`** — the environment the claim is about (e.g. the one the user is hitting). Never assume "prod"; confirm which one.
4. **`branch_to_environment_map`** — read from the deploy config: which branch deploys to which environment. This is the source of truth, not folklore.
5. **`fix_commit`** — the commit (or PR) that allegedly fixes the issue.
6. **`env_source_of_truth`** — where the target's env keys live (the provider's env/secret store or the deploy config). Names/presence only — never values.

If an adapter value is unknown, the first step is to discover it read-only, never to assume it.

## Read-only investigation steps

1. **State the claim and the target.** Record exactly what is "fixed" and which `target_environment` the claim is about.
2. **Discover the adapter.** Resolve `git_host`/`ci_system`, `hosting_provider`, `branch_to_environment_map`, and `env_source_of_truth` by inspection.
3. **Reconcile the deployed SHA to the environment** (see `references/deployed-sha-reconciliation.md`):
   - Read the commit SHA the `target_environment` is actually running.
   - Verify the `fix_commit` is **contained** in the branch that runs there (`git branch --contains`, `git merge-base --is-ancestor`, or the host's equivalent).
   - Verify that branch **maps** to `target_environment` per `branch_to_environment_map`. Both must hold. Containment without mapping = merged but not deployed there.
4. **Print the resolved connection target FIRST** for any environment-touching command (see Safety gates) — host/name only, before running anything.
5. **Diff env-driven secrets source -> target** by key NAME and presence only (see `references/env-secret-diff.md`). Any key the target lacks that the release needs is a deploy-blocking finding.
6. **Check lockfile / package-manager parity** — committed lockfile matches the manifest, and the package-manager MAJOR version matches what CI uses.
7. **Assemble the RELEASE VERIFICATION REPORT** and give a go / no-go with evidence. Do not promote.

## Decision framework

### The core reconciliation (why merged != deployed)

```
fix_commit --> [contained in branch B?] --no--> NOT deployed (still in flight / on another branch)
                       |yes
                       v
            [does branch B map to target_environment?] --no--> deployed ELSEWHERE, not the target
                       |yes
                       v
       [is target_environment running a SHA that includes fix_commit?] --no--> built but not promoted/rolled out
                       |yes
                       v
                    PROVEN in target  (and only now)
```

Two independent facts must both be true: containment (the code is on the branch) AND mapping (that branch is what the target runs). A green CI run proves neither by itself.

### Verification matrix

| Check | PROVEN when | UNPROVEN / blocking signal |
|---|---|---|
| Deployed SHA | target runs a SHA that contains `fix_commit` | target runs an older SHA, or the running SHA is unknown |
| Branch containment | `fix_commit` is an ancestor of the deploy branch tip | commit only on a feature/PR branch, or behind the tip |
| Branch -> environment | deploy config maps that branch to `target_environment` | mapping points the branch at a different environment |
| Env-secret parity | every required key exists in the target (by name) | a required key is absent in the target -> deploy will fail |
| Connection target | resolved host/name is the intended remote | empty/blank URL -> silent fallback to local DB / sqlite |
| Lockfile parity | lockfile matches manifest; PM major matches CI | lockfile drift or PM major mismatch -> CI install breaks |

### Report-only gates (a green check that cannot block)

A green pipeline is not proof the code is safe even when the gate ran: a CI step is only **enforcing** if its exit code can fail the run. Append `|| true`, or set `continue-on-error: true` (or a custom `fail_action`/soft-fail flag) on the step, and the non-zero exit is swallowed — the gate becomes **report-only**: it still surfaces findings, but it will NOT block a PR or merge. So "the security/lint/test job is green" can mean either "passed" or "found problems and was told to pass anyway."

- **Map which checks actually block:** grep the workflow files for `\|\| true`, `continue-on-error`, and `fail_action` (or the CI's soft-fail equivalent). Every gate carrying one of these is report-only; treat its green as informational, not as a barrier.
- **Prove a gate blocks** (don't assume): feed the enforcing check input that must make it exit non-zero — e.g. a deliberate syntax error for a linter/compiler — and confirm the run fails. A gate you have never seen fail is an unproven gate.

### The silent-local-fallback trap (print connection target FIRST)

A command meant to run against a remote database can **silently fall back to a local DB or an on-disk sqlite file when the public connection URL is empty or unset** — and then "succeed" against the wrong target, producing a confidently false verification. The defence is deterministic: **resolve and print the connection host / database name BEFORE running the command**, and refuse to proceed if it is local when a remote was intended. See `references/env-secret-diff.md` for resolving the connection string by name without printing its value.

## Safety gates

- **Never** call a fix "deployed" on the strength of a merge or a green CI run alone — require the deployed-SHA reconciliation.
- **Never** run an environment-touching command without printing the **resolved connection host/name first**; abort if it resolved to a local fallback when a remote was intended.
- **Never** print secret values — diff env keys by NAME and presence/shape only (e.g. `DATABASE_URL: present in source, ABSENT in target`).
- **Never** assume the target environment, the branch mapping, or the env source — discover each read-only.
- **Never** promote or mutate anything as part of verification; produce a go / no-go for the user to act on.
- **Never** treat "works on my machine" / local reproduction as evidence about the target environment.

## Validation checklist

- [ ] Claim and `target_environment` stated explicitly.
- [ ] Deployed SHA read from the target and reconciled (containment AND mapping both confirmed).
- [ ] Resolved connection host/name printed before any environment-touching command; local fallback ruled out.
- [ ] Env-secret diff done by key NAME + presence only; no values printed.
- [ ] Lockfile parity and package-manager MAJOR version checked.
- [ ] Every reported PROVEN item has concrete evidence attached.
- [ ] "Not tested or blocked" lists anything that could not be verified read-only, and why.
- [ ] No promotion or mutation performed.

## Output format

The skill emits exactly one block:

```
RELEASE VERIFICATION REPORT
  Claim:              <what is allegedly fixed>
  Target environment: <name>  (branch map: <branch> -> <environment>, from deploy config)
  Deployed SHA:       <sha running in target>   fix_commit=<sha>
  Reconciliation:     containment=<yes|no>  branch->env mapping=<yes|no>
  Connection target:  <resolved host / db name>  (intended=<remote|local>, fallback-risk=<yes|no>)
  Env-secret diff:    <KEY: present|ABSENT in target> ...   (names only, no values)
  Lockfile / PM:      <match | DRIFT>  PM major: <match | MISMATCH>
  Verdict:            <PROVEN IN TARGET | NOT PROVEN — promote blocked: reason>
  Safe next action:   <single explicit step for the USER>
  Not tested or blocked:
                      - <what could not be verified read-only, and why>
  (no secret values included)
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| "PR merged, so it's fixed" | Merge != deployed to the target the user is hitting | Reconcile deployed SHA: containment AND branch->env mapping |
| Trust a green CI run as proof of deploy | CI proves the build, not what the environment is running | Read the SHA the target actually runs |
| Trust a green gate that has `\|\| true` / `continue-on-error` | The flag swallows the exit code -> the gate is report-only, never blocks | Grep workflows for those flags; prove the gate fails on bad input |
| Run the remote DB command without checking the target | Empty URL silently falls back to local DB / sqlite -> false pass | Print resolved host/name FIRST; abort on local fallback |
| Promote, then discover a missing env key | The migration/feature fails mid-deploy | Diff env keys by name source->target BEFORE promoting |
| Paste env values to "compare them" | Leaks secrets into the transcript | Compare by key name and presence only |
| Ignore lockfile after a dependency bump | PM major / lockfile drift breaks CI install on the runner | Confirm lockfile-manifest match and PM major parity |
| Assume `main` deploys everywhere | Branch->environment mapping is per deploy config | Read the mapping; verify the specific target |

## Portability rationale

The reconciliation logic, the verification matrix, the print-target-first rule, and the report contract describe *how to reason*, not *which vendor to call*. The Git host, CI system, and hosting provider are adapter inputs discovered at run time; vendor-specific query commands live in the reference docs. Adding support for a new platform means adding query variants to a reference doc, not changing this skill.

## Cross-references

- `references/deployed-sha-reconciliation.md` — read the running SHA, prove containment, confirm branch->environment mapping (provider-neutral query variants).
- `references/env-secret-diff.md` — diff env keys by name/presence, resolve the connection target without printing it, the local-fallback guard.
- `migration-safety` (skill) — the risky-migration / cutover skeleton, drift detection, and destructive/CASCADE review.
- `release-verify` (command) — user entry point; routes the pre-promotion checklist to this skill and migration-safety.
