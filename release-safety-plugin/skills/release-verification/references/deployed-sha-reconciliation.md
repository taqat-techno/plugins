# Deployed-SHA reconciliation — provider-neutral procedure

Prove that a specific fix commit is **running in a specific environment**, not merely merged. Two independent facts must both hold: the fix commit is *contained* in the branch that runs there, and that branch *maps* to the target environment per the deploy config. A green CI run proves neither.

Never print secrets while doing this. The only values you need are commit SHAs, branch names, and the branch->environment mapping.

## Step 1 — Read the SHA the target is actually running

The running revision is exposed differently per provider; discover the one this project uses. Common sources, in rough order of reliability:

- A build/release-info endpoint or static asset the app serves (e.g. a version/commit field).
- The hosting provider's "current deployment" / "active release" metadata for that environment.
- A revision/commit label recorded on the running artifact (image tag, release record, deploy log).
- The CI/CD run that last promoted to that environment (its source commit).

Record it as `deployed_sha`. If you cannot read it, the verdict is **NOT PROVEN — running SHA unknown**; do not infer it from the latest merge.

## Step 2 — Prove the fix commit is contained in the deploy branch

Let `B` be the branch the target environment runs (from Step 4's mapping) and `fix_commit` the alleged fix.

Provider-neutral Git checks (use whichever the local clone supports):

```
git merge-base --is-ancestor <fix_commit> origin/<B>   # exit 0 = contained
git branch -r --contains <fix_commit>                  # lists branches that contain it
git log --oneline origin/<B> | grep <fix_commit_short> # contained if present
```

If `fix_commit` is **not** an ancestor of `origin/<B>`, it is on a feature/PR branch or behind the tip -> **NOT PROVEN** (still in flight). Containment in `main` is not containment in the deploy branch unless the deploy branch IS `main`.

## Step 3 — Confirm the deployed SHA includes the fix commit

Even if `B` contains `fix_commit`, the environment may run an older `deployed_sha`:

```
git merge-base --is-ancestor <fix_commit> <deployed_sha>   # exit 0 = the running build includes the fix
```

Non-zero -> the fix is on the branch but **not yet promoted/rolled out** -> NOT PROVEN.

## Step 4 — Confirm the branch maps to the target environment

Read the **deploy config** (the project's actual CI/CD or hosting config) for the branch->environment mapping. Do not rely on memory or convention. Typical homes for this mapping:

- The CI/CD pipeline/workflow definition (branch filters / environment stages).
- The hosting provider's environment settings (which branch each environment tracks).
- An infra-as-code or deploy descriptor that pins branch -> environment.

If the branch that contains the fix maps to a **different** environment than the target, the fix is deployed **elsewhere** -> NOT PROVEN for the target.

## The verdict table

| containment in B | deployed_sha includes fix | B maps to target | Verdict |
|---|---|---|---|
| no | — | — | NOT PROVEN — fix not on the deploy branch |
| yes | no | — | NOT PROVEN — built but not promoted/rolled out |
| yes | yes | no | NOT PROVEN — deployed to a different environment |
| yes | yes | yes | PROVEN IN TARGET |

Only the last row justifies "it's fixed."

## Platform note (labeled examples only)

> Example (illustrative — not required): one project exposes the running commit at a `/version` route; another records it as a container image tag; another reads it from the hosting provider's "active deployment" metadata. The reconciliation behaviour — read running SHA, prove containment, prove the running build includes the fix, confirm branch->environment mapping — is identical across all three. Only the *source* of `deployed_sha` and the *location* of the branch mapping differ.
