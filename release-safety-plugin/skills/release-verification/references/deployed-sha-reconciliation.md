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

## Deploy-liveness failure modes (why a green deploy can still be the old build)

Steps 1-4 assume you can read a trustworthy `deployed_sha`. These four modes are where that assumption breaks — a deploy reports success while the target still serves old code. Handle each before trusting a verdict.

### A. The health-endpoint trap — probe a code marker, not a ping

A DB-free `/health/` (or `/livez` / `/ping`) route returns **200 from the OLD deployment** during a cold rebuild: the previous container keeps answering until the new build cuts over. So a health 200 proves the service is *up*, not that *this commit* is running — do not use it as `deployed_sha` evidence.

Instead, probe a **code marker** that flips only when the new code serves:

- Pick a change observable without auth — a field the fix **removed** from an API/schema response (assert it is now **absent**) or one it **added** (assert it is now **present**). A serialised schema, an OpenAPI/GraphQL document, an enum value, a response header, or a rendered version string all work.
- Request it against the target and assert the new state. Absent-when-removed / present-when-added means the new code is live; unchanged means the old build is still serving regardless of a green deploy or a health 200.

Record the marker result as the liveness signal and reconcile it with `deployed_sha` from Step 1. If they disagree (SHA says new, marker says old), trust the **marker** — the SHA source may be reporting the *intended* release, not the *serving* one.

### B. Per-service reconciliation — verify EACH service, not one

A release that spans multiple services (API, worker, scheduler, frontend, a monorepo's sub-apps) can leave one **SKIPPED**, **WAITING**, or stopped mid-rollout while the rest go green. One green service is not the deploy.

- Enumerate every service the release touches (from the deploy config / pipeline / platform project).
- Read `deployed_sha` **per service** and run Steps 2-3 for each. A service still on the old SHA, or in a non-terminal state (WAITING / queued / a `deploymentStopped`-type status), is a blocking finding even if its siblings are live.
- Only when **every** service both contains and is running the fix is the multi-service deploy proven.

### C. Deploy-from-source CLIs upload the working tree, not the commit

A CLI that deploys from local source (e.g. a `railway up --ci --detach`-style command) uploads the **current working tree** — uncommitted edits, parallel changes, and all — not the git commit you believe you are shipping.

- **Diff the tree first**: confirm `git status` is clean and `HEAD` is the intended commit before invoking the upload. A dirty tree ships whatever is on disk.
- This is most dangerous as a **stuck-deploy remedy**: re-running the source upload to "unstick" a deploy can ship uncommitted or a teammate's parallel changes into the environment. Prefer resolving the stuck state directly; note that a `redeploy`-type command may **refuse to act on a stuck deployment** — clear the stuck deploy rather than papering over it with a fresh dirty-tree upload.
- After a source deploy, still reconcile via a code marker (mode A) — the upload's own "success" does not tell you which tree it captured.

### D. A walled frontend (401/SSO) — verify via the platform API

A frontend behind a deployment-protection or SSO wall answers **401 to every unauthenticated request**, so neither a page fetch nor a code-marker probe over plain HTTP can see the app.

- Read the **platform's deployment API/metadata** for that environment: confirm the deployment is `state:READY` (or the provider's terminal-success equivalent) AND that its recorded commit SHA contains `fix_commit` (Steps 2-3 against that SHA).
- The platform API is the source of truth when the app is unreachable by request. If neither the app nor an authenticated API path is reachable, the verdict is **NOT PROVEN — walled, no API confirmation**; do not infer liveness from the wall's 401.

## Platform note (labeled examples only)

> Example (illustrative — not required): one project exposes the running commit at a `/version` route; another records it as a container image tag; another reads it from the hosting provider's "active deployment" metadata. The reconciliation behaviour — read running SHA, prove containment, prove the running build includes the fix, confirm branch->environment mapping — is identical across all three. Only the *source* of `deployed_sha` and the *location* of the branch mapping differ.
