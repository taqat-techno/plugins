---
name: release-verification
description: Proves a fix is actually deployed to the TARGET environment, not merely merged. Reconciles the deployed commit SHA to the environment (verify the fix commit is contained in the branch AND that the branch maps to that environment per the deploy config); diffs env-driven secrets between source and target before promoting (a migration or feature needing an env key the target lacks fails the deploy); forces the resolved connection host/name to be printed FIRST because a remote DB command can silently fall back to a local DB / sqlite when the public connection URL is empty; and catches lockfile / package-manager MAJOR mismatches that break CI installs. Names the specific "is it actually deployed?" failure modes -- a DB-free /health/ 200 can be answered by the OLD deployment during a cold rebuild, so it gates liveness on a direct probe of a CODE MARKER (a removed API-schema field disappearing / an added field appearing) rather than a health ping; a multi-service deploy can silently SKIP or stall one service (WAITING / stopped), so it verifies EACH service's deployed SHA, not one; a CLI "deploy from source" (e.g. a railway up --ci --detach-style command) uploads the local WORKING TREE, not the git commit, so it diffs the tree against the intended commit first; and an SSO / deployment-protection-walled frontend (401) cannot be HTTP-verified, so it reads the platform API (state:READY + commit SHA). Also flags a CI env-var false-FAILURE that MASKS a real test failure underneath (the complement of the report-only false-PASS), reproduces walled behaviour against a reachable DB via a fully rolled-back script, and separates already-fixed client bug reports from genuinely new ones by comparing report time to deploy time. Provider-neutral across any Git host, CI system, and hosting provider. Activates when someone asks "is the fix live?", "did it deploy?", "verify the release", when a /health 200 or a green deploy conflicts with unchanged behaviour, when one service of a multi-service deploy may be stalled, or before promoting between environments.
version: 0.3.0
last_reviewed: 2026-07-23
owns:
  - the "FIXED means proven in the target environment, not merged" discipline
  - the deployed-SHA -> environment reconciliation (branch containment AND branch-to-environment mapping)
  - the env-secret diff (by key NAME and presence only) before promotion
  - the resolved-connection-target print-first rule (guard against silent local fallback)
  - the lockfile / package-manager parity check
  - the report-only-gate detection (a gate with `|| true` / `continue-on-error` surfaces findings but does not block)
  - the deploy-liveness probe (gate on a code marker over a /health ping; verify each service's SHA; diff the working tree vs the commit for deploy-from-source; read the platform API for an SSO/401-walled frontend)
  - the CI env-var false-FAILURE detection (a red env/setup error that masks a real test failure underneath -- the complement of the report-only false-PASS)
  - the unreachable-target evidence path (migration state read from the target's deploy log rather than a local status command; unauthenticated 401-vs-404 route-existence probing) for a target whose database admits no connection
  - the report-time-vs-deploy-time triage that separates already-fixed client reports from genuinely new bugs
  - the RELEASE VERIFICATION REPORT output contract
defers_to:
  - migration-safety skill for the risky-migration / cutover skeleton and destructive/CASCADE review
  - github-actions-release-safety skill for the AUTHORING-time application of the report-only-gate rule (the soft-fail sweep across workflow files and the prove-it-blocks procedure), and for workflow/tag authoring safety generally -- this skill states the rule and applies it at deploy time
  - references/deployed-sha-reconciliation.md for the SHA-to-environment procedure and the deploy-liveness failure modes
  - references/env-secret-diff.md for the by-name secret-diff procedure
  - the django-testing skill (django plugin) for the rolled-back deployed-behaviour reproduction recipe (in-process auth + an always-rollback transaction) used when a walled frontend blocks HTTP verification
  - the deploy config of each project for branch-to-environment mapping and env-var source
user-invocable: false
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
- A `/health/` (or liveness) endpoint returns 200 but the reported behaviour has not changed after a deploy.
- A multi-service / monorepo deploy where one service may have been skipped, left waiting, or stalled.
- A deploy CLI that uploads from source (a "deploy from source" / `up`-style command) rather than from a built commit.
- The frontend is behind an SSO / deployment-protection wall (401), so it cannot be probed over plain HTTP.
- A CI job went red on an environment/setup error and you are tempted to call it benign and merge.
- Deciding whether a freshly reported bug was already fixed by a prior deploy.

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
   - If the running SHA cannot be read directly, or the only signal is a health endpoint, **probe a code marker** instead of trusting a `/health` 200, and verify **each** service of a multi-service deploy — see "Deploy-liveness failure modes" below.
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
| Deploy liveness (code marker) | a direct probe shows the fix's code marker (a removed API field now absent / an added field now present) | only a `/health` 200, or the marker is unchanged -- the OLD build may still be serving |
| Per-service SHA | every service in the deploy runs a SHA that contains `fix_commit` | any service is SKIPPED / WAITING / stalled, or runs an older SHA |
| Deploy source (CLI) | the working tree equals the intended commit (clean tree, HEAD on that SHA) | a deploy-from-source upload from a dirty / parallel tree -- ships uncommitted changes |
| Walled frontend | the platform API reports `state:READY` + a commit SHA containing the fix | only a 401 / SSO wall over HTTP -- the app cannot be probed by request |

### Deploy-liveness failure modes (a green deploy is not a live deploy)

A build that reports "success" is not proof the new code is answering requests. Four modes let a deploy look done while the target still serves the old code — reconcile each explicitly (procedure in `references/deployed-sha-reconciliation.md`):

1. **A health endpoint lies during a cold rebuild.** A DB-free `/health/` (or `/livez`) route returns **200 from the OLD deployment** while the new build is still rebuilding — the old container keeps serving until cutover. A health ping therefore proves the service is *up*, never that *this fix* is live. **Gate liveness on a direct probe of a code marker**, not a health 200: pick a change observable without auth — an API/schema field the fix **removed** (assert it is now **absent**) or one it **added** (assert it is now **present**) — and probe that. The marker flips only when the new code is actually serving; a health 200 does not.
2. **A multi-service deploy silently skips or stalls one service.** When a release spans several services (API, worker, scheduler, frontend, a monorepo's sub-apps), one can be **SKIPPED**, left **WAITING**, or stopped mid-rollout while the others go green — so part of the release runs the fix and part runs the old SHA. **Verify EACH service's deployed SHA independently**; never generalise from one green service to "the deploy is live."
3. **A "deploy from source" CLI ships the working tree, not the commit.** A CLI that deploys from local source (e.g. a `railway up --ci --detach`-style command) uploads the **current working tree** — including uncommitted and parallel changes — not the git commit you think you are shipping. **Diff the working tree against the intended commit before deploying** (`git status` clean, `HEAD` on the right SHA). This bites hardest as a "fix" for a stuck deploy: re-running the source upload can ship uncommitted or a teammate's parallel edits, and a `redeploy`-type command may **refuse to act on a stuck deployment** — resolve the stuck state, do not paper over it with a fresh source upload from a dirty tree.
4. **An SSO / deployment-protection wall (401) blocks HTTP verification.** A frontend behind a deployment-protection or SSO wall answers **401 to every unauthenticated request**, so neither a page fetch nor a code-marker probe over plain HTTP can see the app. **Read the platform's deployment API instead** — confirm the deployment is `state:READY` (or the provider's terminal-success equivalent) AND that its recorded commit SHA contains the fix. The API is the source of truth when the app itself is unreachable.

### Reproducing walled behaviour against a reachable DB (rolled-back script)

When the frontend is walled (mode 4 above) you cannot drive the app over HTTP — but if the target environment's **database is reachable**, you can reproduce the deployed behaviour directly against it, without a browser and without mutating anything. Run a script that authenticates **in-process** (as the affected role) inside a **transaction that always rolls back**, so the verification reads real target data yet writes nothing. This reproduces what the deployed code does against the deployed data, which HTTP cannot reach. Print the resolved connection target FIRST (Safety gates) so the script cannot silently hit a local fallback. The concrete framework recipe — in-process auth plus an always-rollback transaction — lives in the **django-testing** skill (django plugin); this skill owns only the "verify in the target env, read-only, roll back" framing and stays engine-neutral about it.

The wall still blocks the *browser* evidence, so pair the rolled-back target-DB run with a run of the **byte-identical commit** on localhost: the target run proves the behaviour against real deployed data, the local run shows it happening in a UI. The pairing is only admissible while both sides are the same commit — check out the deployed SHA locally rather than driving your working tree, or the screenshots document code the target is not running.

### Report-time vs deploy-time triage (is this bug already fixed?)

Before investigating a client-reported bug as new, compare its **report timestamp** to the last **deploy timestamp** for the target environment. A report filed *before* the fix deployed may already be resolved — a bug whose report time predates the deploy that fixed it is not a new bug. Reproduce against the **current** deployed SHA before spending effort; only a reproduction on the current build makes a report "genuinely still open."

### Report-only gates (a green check that cannot block)

A green pipeline is not proof the code is safe even when the gate ran: a CI step is only **enforcing** if its exit code can fail the run. Append `|| true`, or set `continue-on-error: true` (or a custom `fail_action`/soft-fail flag) on the step, and the non-zero exit is swallowed — the gate becomes **report-only**: it still surfaces findings, but it will NOT block a PR or merge. So "the security/lint/test job is green" can mean either "passed" or "found problems and was told to pass anyway."

- **Map which checks actually block:** grep the workflow files for `\|\| true`, `continue-on-error`, and `fail_action` (or the CI's soft-fail equivalent). Every gate carrying one of these is report-only; treat its green as informational, not as a barrier.
- **Prove a gate blocks** (don't assume) — a gate you have never seen fail is an unproven gate. The prove-it-blocks procedure (feeding the gate must-fail input, and confirming its selector collected files and the check is in the required list) is owned by the **github-actions-release-safety** skill; use it there rather than re-deriving it here.

### False-FAILURE masking (a red gate can hide a worse red)

The report-only gate above is one failure direction — a real problem swallowed into green. The **mirror** is a red gate that hides a real failure: a CI job forced red by an **environment problem** (a missing or renamed env var, a broken/absent service container, a runner misconfiguration) fails during **setup, before the real tests run** — so a genuine test failure underneath is never reached and never surfaces. The visible red is the env error; the real red is masked behind it. Do not conclude "it was just the missing env var" and merge: **fix the env cause, RE-RUN, and read the underlying result.** The tests may still be red once they finally execute. (This complements the report-only false-PASS: there a real failure is reported-but-not-blocked; here a real failure is not even reached.)

Classifying a red gate as benign is *sometimes* correct, but it has to be earned from the failed run's log, never from the job name or a hunch: read `--log-failed` (or the CI's equivalent) and require a mechanism that **structurally cannot occur in the target**. The clean example is a one-time data migration that CI re-runs because CI builds a **fresh database from zero**, and that migration then fails for want of a key the CI environment does not carry — while the target applied that migration long ago (so it will not re-run) and does carry the key. Note the shape: that is a claim about the *target's* state, so confirm the target's state (the migration is already applied there, the key is present) instead of inferring it from the error text — and record the durable fix (give CI the placeholder key) rather than re-classifying the same red every release. Without that proof the red stands.

### The silent-local-fallback trap (print connection target FIRST)

A command meant to run against a remote database can **silently fall back to a local DB or an on-disk sqlite file when the public connection URL is empty or unset** — and then "succeed" against the wrong target, producing a confidently false verification. The defence is deterministic: **resolve and print the connection host / database name BEFORE running the command**, and refuse to proceed if it is local when a remote was intended. See `references/env-secret-diff.md` for resolving the connection string by name without printing its value.

## Safety gates

- **Never** call a fix "deployed" on the strength of a merge or a green CI run alone — require the deployed-SHA reconciliation.
- **Never** run an environment-touching command without printing the **resolved connection host/name first**; abort if it resolved to a local fallback when a remote was intended.
- **Never** print secret values — diff env keys by NAME and presence/shape only (e.g. `DATABASE_URL: present in source, ABSENT in target`).
- **Never** assume the target environment, the branch mapping, or the env source — discover each read-only.
- **Never** promote or mutate anything as part of verification; produce a go / no-go for the user to act on.
- **Never** treat "works on my machine" / local reproduction as evidence about the target environment.
- **Never** accept a `/health` / liveness **200 as proof the fix is live** — during a cold rebuild it can be answered by the OLD deployment; gate liveness on a direct probe of a code marker (a removed field now absent / an added field now present).
- **Never** verify only **one** service of a multi-service deploy — a SKIPPED / WAITING / stalled service leaves part of the release on the old SHA; check EACH service's deployed SHA.
- **Never** treat a **deploy-from-source** CLI upload as shipping the committed SHA — it uploads the local working tree; diff the tree against the intended commit first, and do not "fix" a stuck deploy with a fresh source upload from a dirty tree.
- **Never** call an **SSO / 401-walled** frontend "deployed" from an HTTP probe — read the platform API (`state:READY` + commit SHA); the wall answers 401 to every request.
- **Never** conclude a red CI job was "just the env var" and merge — an env-driven false-FAILURE can mask a real test failure; fix the env, re-run, and read the underlying result.
- **Never** take a target's migration state from a **local** migration-status command when the target's database has no public proxy — the local command reports whichever database the local environment resolved to; read the applied-migration line in the target's deploy / pre-deploy log instead.

## Validation checklist

- [ ] Claim and `target_environment` stated explicitly.
- [ ] Deployed SHA read from the target and reconciled (containment AND mapping both confirmed).
- [ ] Resolved connection host/name printed before any environment-touching command; local fallback ruled out.
- [ ] Env-secret diff done by key NAME + presence only; no values printed.
- [ ] Lockfile parity and package-manager MAJOR version checked.
- [ ] Liveness gated on a code-marker probe, not a `/health` / liveness 200 (old build ruled out for a cold rebuild).
- [ ] Every service of a multi-service deploy verified to run a SHA containing the fix (no SKIPPED / WAITING / stalled service).
- [ ] For a deploy-from-source CLI, the working tree diffed against the intended commit before deploying (clean tree, right HEAD).
- [ ] A walled (401 / SSO) frontend verified via the platform API (`state:READY` + SHA), not an HTTP probe.
- [ ] Any red CI job that failed on an env / setup error re-run after the fix, and its underlying test result read (false-FAILURE not assumed benign); any red classified as benign backed by the failed-run log plus a mechanism that cannot occur in the target.
- [ ] Where the target's database is unreachable, migration state read from the target's deploy / pre-deploy log (not a local status command), and route existence probed unauthenticated (401/403 = exists and gated, 404 = missing) with the untested behaviour named.
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
  Deploy liveness:    <code-marker probed=PROVEN | /health-200-only=UNPROVEN>  marker=<removed/added field probed>
  Per-service SHA:    <all services contain fix | service <name>=SKIPPED/WAITING/older-SHA>
  Deploy source:      <built commit | deploy-from-source: working-tree-vs-commit=<clean|DIRTY>>
  Walled frontend:    <n/a | platform API state:READY+SHA | HTTP-BLOCKED (401/SSO)>
  Connection target:  <resolved host / db name>  (intended=<remote|local>, fallback-risk=<yes|no>)
  Env-secret diff:    <KEY: present|ABSENT in target> ...   (names only, no values)
  Lockfile / PM:      <match | DRIFT>  PM major: <match | MISMATCH>
  Report vs deploy:   <n/a | report predates fix-deploy (may already be fixed) | report after deploy (still open)>
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
| `/health` 200, so it's live | A DB-free health ping is served by the OLD deployment during a cold rebuild | Probe a code marker (a removed field now absent / an added field now present), not a ping |
| Verify one service, call the whole deploy live | A multi-service deploy can SKIP or stall one service (WAITING / stopped) | Verify EACH service's deployed SHA independently |
| `up` / deploy-from-source, assume it shipped the commit | The CLI uploads the local working tree, not the git commit — dirty / parallel changes ship | Diff the working tree against the intended commit before deploying |
| HTTP-probe an SSO / 401-walled frontend | The wall returns 401 to every unauthenticated request — HTTP cannot see the app | Read the platform API (`state:READY` + commit SHA) |
| "CI was just the missing env var" -> merge | A red env/setup error can mask a real test failure that never ran | Fix the env, re-run, read the underlying result before merging |
| Confirm the target applied a migration with a local status command | It reports whichever DB the local env resolved to — never a target with no public proxy | Read the applied-migration line in the target's deploy / pre-deploy log |
| Read the elapsed time of a 503 -> 200 flip as "too fast to be a rebuild" | Timing discriminates nothing — cold start, cache and rollout strategy vary; it is no more evidence of the old build than of the new | Ask the application what it is running (code marker / component registry with timestamps) |
| Investigate every client report as new | A report filed before the fix deployed may already be resolved | Compare report time to deploy time; reproduce on the current SHA first |

## Portability rationale

The reconciliation logic, the verification matrix, the print-target-first rule, and the report contract describe *how to reason*, not *which vendor to call*. The Git host, CI system, and hosting provider are adapter inputs discovered at run time; vendor-specific query commands live in the reference docs. Adding support for a new platform means adding query variants to a reference doc, not changing this skill.

## Cross-references

- `references/deployed-sha-reconciliation.md` — read the running SHA, prove containment, confirm branch->environment mapping, the deploy-liveness failure modes (code-marker probe, per-service SHA, deploy-from-source working tree, walled-frontend platform API), and the unreachable-target evidence sources (deploy-log migration line, unauthenticated 401-vs-404 existence probe).
- `references/env-secret-diff.md` — diff env keys by name/presence, resolve the connection target without printing it, the local-fallback guard.
- `migration-safety` (skill) — the risky-migration / cutover skeleton, drift detection, destructive/CASCADE review, and environment-vs-environment schema-drift detection (the other half of RS-3).
- `github-actions-release-safety` (skill, this plugin) — the authoring side of the same two signals: the soft-fail sweep and the prove-it-blocks procedure applied while a workflow is written or reviewed, plus the `workflow_dispatch` default-branch rule, the `timeout-minutes` queue-vs-execution trap, the push -> wait for green -> tag ordering, and the secret-presence guard contract. This skill owns the report-only-gate rule's statement and its deploy-time application; do not restate either side in the other.
- `django-testing` (skill, django plugin) — the rolled-back deployed-behaviour reproduction recipe (in-process auth + always-rollback transaction) for when a walled frontend blocks HTTP verification.
- `release-verify` (command) — user entry point; routes the pre-promotion checklist to this skill and migration-safety.
