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

**When the platform reports nothing to the Git host at all.** Some hosting platforms publish **no commit status and no check-runs** — the branch shows a bare pushed commit and there is no external deploy signal to read, green or red. There is then nothing to reconcile *against*, and the application's own account of itself is not merely the best source, it is the only one. Ask it for its **installed-component registry** — the module/plugin/version table an application framework exposes, a build-info record, an admin/metadata API — and read, per changed component, **the version AND the installed/updated timestamp**. A version string alone is stale evidence: a component whose declared version did not change between the two builds looks identical in both. The timestamp is what moves. Cross-check against a component the change did **not** touch, as a control: every touched component stamped shortly after the push while the untouched one still carries its old timestamp is a conclusive reading; all components sharing one fresh timestamp usually means the platform rebuilt everything and the reading proves nothing about *your* change.

**Elapsed time is not evidence in either direction.** A `503 -> 200` flip that seems "far too fast to be a rebuild" does not show the old build is still serving, exactly as a slow one does not show the new build is. Cold-start behaviour, layer caching, and rollout strategy vary too widely for duration to discriminate between builds. A timing-based reading is a guess dressed as a finding — state the marker or the component registry, or state that liveness is UNPROVEN.

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

## When the target's database is unreachable — log evidence and existence probes

Some environments expose **no public database proxy**: nothing can connect from a workstation to run a migration-status command, mint a token, or open an application shell against the target. The trap is that a local status command still *runs* — against whichever database the local environment resolved to (a dev copy, a different environment's proxy, an on-disk file) — and prints that database's migration state in the same format, so it reads as an answer about the target. It is the silent-local-fallback trap wearing a migration hat.

Two substitutes, both read-only and both genuinely about the target:

- **Read the applied-migration line in the target's deploy / pre-deploy log.** A release that migrates as a pre-deploy step logs each migration it applied (an `Applying <migration> ... OK`-style line). That line is first-hand evidence the migration ran **on the target**, which no local status output can be. The step's failure semantics carry the rest of the meaning: where the pre-deploy migrate is fail-safe — a failure aborts the release and the previous version keeps serving — the *absence* of the line means the migration did not run at all, not that it half-ran and left a partial schema. Confirm that ordering for the platform in use before leaning on it.
- **Probe route existence unauthenticated.** With no token available, an unauthenticated request still separates **401/403 (the route exists and is auth-gated)** from **404 (the route is not there)**. That proves the new code's URL surface shipped, without any credential. It proves nothing about the behaviour behind the gate, the response shape, or role permissions — for those, rely on the *same commit* verified in an environment you can authenticate against, and name the gap explicitly in the report's "Not tested or blocked" line.

Neither replaces `deployed_sha` (Step 1) where a SHA source exists; they are what remains when the target admits no connection.

## Platform note (labeled examples only)

> Example (illustrative — not required): one project exposes the running commit at a `/version` route; another records it as a container image tag; another reads it from the hosting provider's "active deployment" metadata. The reconciliation behaviour — read running SHA, prove containment, prove the running build includes the fix, confirm branch->environment mapping — is identical across all three. Only the *source* of `deployed_sha` and the *location* of the branch mapping differ.
