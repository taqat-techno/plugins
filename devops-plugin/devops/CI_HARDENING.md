# CI / pipeline hardening review (checklist, not an engine)

This is a **review checklist** for a human (or an assisting agent) to walk when changing
CI/CD pipeline definitions. It does not scan, diff, or score anything by itself — it is a
set of rules plus how to verify each one by hand.

The automated diff review and deep security analysis are owned by the dedicated
code-review and security-guidance plugins. Use those for line-by-line findings on a pull
request. Use **this** document as the mental model and the manual fallback: the things a
reviewer should consciously confirm before approving a pipeline change, regardless of which
CI system (hosted Git CI, self-hosted runners, container-based pipelines, or a managed
DevOps service) is in play.

The checklist is intentionally generic. Wherever a concrete snippet appears it is marked
**Example (illustrative — not required)** and uses placeholder names only. No item depends
on any specific repository, organization, tool, or secret.

## How to use this checklist

Walk the six items below in order against the *changed* pipeline files, not the whole
repo. For each item: read the rule, then run the "How to verify" step and record pass/flag.
A flag is not an automatic block — it is a thing to justify in the PR description or fix.

The six items:

1. SHA-pin third-party CI actions/steps
2. An approval-looking YAML block is not itself an approval gate
3. Don't trust the docs' workflow inventory — enumerate the real files
4. Don't weaken established gates
5. Distinguish a real secret leak from an ephemeral in-job credential
6. "Merged" is not "deployed" — reconcile the deployed SHA to the environment before
   calling a fix shipped, and diff env-driven secrets between source and target first

## 1. SHA-pin third-party actions and steps

**Rule.** Any third-party reusable action, step, or shared pipeline template must be pinned
to a **full commit SHA**, not to a mutable tag or branch. A tag like `v3` or a branch like
`main` can be repointed by whoever controls that repository, so pinning to it means you run
whatever they push next — a supply-chain risk, since CI runs with access to your
credentials and source.

**Exception.** First-party / official actions published by the same platform vendor that
runs your CI (the platform's own checkout, cache, or artifact steps) may use a **major
version tag** (for example a `vN` tag). These are maintained by the platform itself and the
major-version tag is the documented stability contract. Anything from a third party — an
individual, a community org, a vendor that is not the CI platform — gets a SHA.

**How to verify.**

- List every external step/action reference in the changed files. For each, ask: who
  publishes it?
- If it is third-party and pinned to a tag or branch, flag it. Resolve the intended tag to
  its current commit SHA and pin to that SHA, ideally with a trailing comment recording
  which human-readable version that SHA corresponds to.
- Confirm the SHA is a full-length commit hash, not a short prefix and not a tag that merely
  looks hash-like.
- Re-pinning later (to pick up a fix) is a deliberate, reviewable change — that is the
  point.

**Example (illustrative — not required).**

```yaml
# Flag: third-party action pinned to a mutable tag
- uses: some-org/some-action@v2

# Preferred: same action pinned to a full commit SHA, version noted in a comment
- uses: some-org/some-action@3a1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b  # v2.4.1

# Acceptable: first-party/official platform action on a major-version tag
- uses: actions/checkout@v4
```

## 2. An approval-looking YAML block is not the gate

**Rule.** A block in the pipeline file that *looks* like an approval or protection
mechanism — an `environment:` reference, a stanza naming reviewers, a step that says it
"requires approval" — is usually only a **pointer**. The enforcement (who must approve, how
many, whether a wait/timer applies, which branches are protected) lives in the CI system's
**repo/project settings**, not in the YAML. Editing or even deleting the YAML pointer does
not necessarily change the real rule, and a present-looking pointer does not prove a rule
exists.

**How to verify.**

- When a change adds, edits, or removes an approval-looking block, do not conclude the gate
  changed. Open the corresponding setting (environment protection rules, branch/tag
  protection, required reviewers, deployment approvals) and confirm what is actually
  configured.
- If the YAML references an environment or protected target, confirm that target exists in
  settings and carries the protection you expect.
- If the gate matters for security or releases, treat "the setting exists and is enabled" as
  the evidence — screenshot, link, or note it in the PR. The YAML alone is not evidence.
- Conversely, removing an `environment:` line may silently drop a real protection. Flag it
  and check.

## 3. Don't trust the docs' workflow inventory

**Rule.** README/wiki/architecture notes describing "the pipelines we have" drift from
reality. Always **enumerate the actual workflow/pipeline files** on disk and read their
triggers directly. This matters most for chained pipelines: when one pipeline is triggered
by the completion of another, the link is frequently keyed by the upstream pipeline's
**display name**. Renaming a pipeline (changing its `name:`) can silently break a downstream
`workflow_run`-style trigger that still references the old name — nothing errors, the
downstream simply never fires.

**How to verify.**

- List the actual pipeline definition files (the CI config directory / the platform's
  pipeline list), not the inventory in the docs.
- For each, read its trigger block: on which events, branches, tags, paths, schedules, or
  upstream-completion does it run?
- For any pipeline triggered by another pipeline's completion, find the exact key it matches
  on (commonly the upstream display name). Grep for that string and confirm an upstream
  pipeline still produces it.
- If a change renames a pipeline, search for the old name across all pipeline files and any
  external trigger config; update every reference or confirm none exist.
- Note any pipeline file present on disk but absent from the docs (and vice versa) — that
  gap is itself a finding.

## 4. Don't weaken established gates

**Rule.** A pipeline change should not quietly downgrade a check that was previously
blocking. Two common silent weakenings:

- **`continue-on-error` added to a blocking gate.** This turns a step that used to fail the
  pipeline into one that reports a problem but lets the run pass. On an established
  test/lint/security/build gate this is a regression. It is *legitimate* only on a
  clearly-new, clearly-advisory step (for example a freshly added scanner you are still
  tuning) — and even then it should be labeled as advisory.
- **Renamed required-check job names.** Branch protection / merge requirements reference
  required checks **by job name**. Renaming the job (or the matrix leg that produces the
  check) can orphan the requirement: the old required name never reports again, so the
  protection passes vacuously while appearing intact.

**How to verify.**

- Diff each gate step. If `continue-on-error` (or the equivalent "ignore failure" flag) was
  added to a step that previously could fail the run, flag it. Confirm whether the step is a
  brand-new advisory scanner or an existing blocking gate.
- Confine any allowed `continue-on-error` to clearly-new advisory checks, and make the
  advisory intent explicit (a comment or a non-blocking label).
- For any renamed job / check, cross-check the required-checks list in branch protection. If
  the old name is still required, either keep the name or update the protection to the new
  name in the same change.
- Watch for subtler weakenings too: a gate moved behind an `if:` condition so it rarely runs,
  a threshold loosened, a path filter that now excludes the files it used to guard.

## 5. Real secret leak vs. ephemeral in-job credential

**Rule.** Not every credential string in pipeline output or config is a leak. Distinguish:

- **A real secret leak** — a long-lived secret (API token, signing key, cloud access key,
  database password) that is printed to logs, written to an artifact, committed to the repo,
  exposed to untrusted pull-request runs, or otherwise made reachable beyond the job that
  needs it. This is a genuine finding: rotate and remediate.
- **An ephemeral in-job credential guarding nothing reachable** — a short-lived token the CI
  platform mints for the duration of a single job (an OIDC/federated token, a per-run
  registry login, a temporary deploy credential) that expires when the job ends and cannot
  be replayed. Seeing such a value referenced is expected pipeline plumbing, not a leak, as
  long as it is not also persisted somewhere durable.

The test is **reachability and lifetime**: can something outside this job use the value
later? If no, it is plumbing. If yes, it is a finding.

**How to verify.**

- For each credential-looking reference, ask: is it long-lived or minted per-run? Does it
  outlive the job? Is it written to a log, an artifact, an env file, a cache, or the repo?
- Confirm secrets are injected from the platform's secret store (masked, not echoed) rather
  than hardcoded.
- Check whether secrets are exposed to triggers from untrusted sources (e.g. pull requests
  from forks). An ephemeral token scoped to a trusted job is fine; a long-lived secret
  reachable from an untrusted trigger is a finding.
- **Never print, paste, or echo the secret value itself** while verifying — reference it by
  name and reason about its lifetime and reachability only.

## 6. "Merged" is not "deployed" — reconcile the SHA to the environment first

**Rule.** A change reaching a branch is **not** the same as that change running in an
environment. "It's merged to the release branch" answers *what code exists*, not *what code
is live*. Before telling anyone a fix is shipped — or before promoting one environment to
the next — establish two facts independently, with evidence, never by inference:

- **Deployed-SHA reconciliation.** Find the commit SHA the target environment is *actually
  running* (from the deploy record, the release artifact, a `/version` or build-info
  endpoint, or the platform's last-successful-deploy metadata), then prove the fix's commit
  is an ancestor of it. Branch containment alone is insufficient: a commit can sit on the
  release branch for days while the environment still runs an older SHA, or a hotfix can be
  live on the environment without ever touching the branch you are looking at.
- **Branch-to-environment mapping.** "Which environment does this branch deploy to?" is
  answered by the **deploy configuration** (the pipeline's environment/branch map, the
  deploy target rules, the GitOps target ref), not by the branch name or by convention. A
  branch called `release` does not necessarily feed the environment you assume; confirm the
  mapping in config before reasoning about where its commits run.

A fix is "shipped" only when both hold: the fix commit is an ancestor of the SHA the target
environment is running, **and** the deploy config confirms that branch maps to that
environment. Until then it is "merged," which is a different, weaker claim.

**How to verify.**

- Get the environment's live SHA from a source of truth that reflects *runtime*, not source
  control: the deploy/release record, the artifact's embedded build metadata, or a
  version/health endpoint the running service exposes. Treat the branch tip as a candidate,
  not as the answer.
- Prove ancestry with the merge-base ancestor check rather than eyeballing the branch:

  **Example (illustrative — not required).**

  ```bash
  # Is <fix-sha> contained in what the environment is running (<deployed-sha>)?
  # Exit 0 => <fix-sha> is an ancestor of <deployed-sha> => the fix is in that build.
  # Exit 1 => it is NOT deployed yet, even if it is merged to the branch.
  git merge-base --is-ancestor <fix-sha> <deployed-sha> && echo "DEPLOYED" || echo "NOT DEPLOYED"
  ```

- Map the branch to its environment from the deploy config, not from its name. Open the
  pipeline's environment/branch rules (or the GitOps target) and confirm which environment
  the branch you merged into actually feeds. Note any branch whose name implies one
  environment but whose config points at another — that mismatch is a finding.
- Only after both checks pass should the status move from "merged" to "deployed" / "shipped."
  Record the deployed SHA and the environment in the report so the claim is auditable.

### 6a. Diff env-driven secrets between source and target BEFORE promoting

**Rule.** Before promoting a build/release from one environment to the next (e.g. staging →
production), **diff the set of environment-driven configuration keys** the two environments
provide — by **key name and presence**, never by value. Environments drift: a key added for
a feature in the lower environment is frequently missing in the higher one. The most
dangerous case is a **secret or config key a data migration depends on** (an encryption key
the migration uses to re-encrypt rows, a connection string the migration reads, a feature
flag the migration branches on). If that key is absent or different in the target, the
migration can fail mid-run or — worse — silently write wrong/unrecoverable data.

**How to verify.**

- Enumerate the configuration **key names** each environment supplies (from the platform's
  env/variable-group/secret-store listing). Compare the two **sets**: which keys exist in
  source but not target, and vice versa. Compare presence and shape only.
- Pay special attention to keys any pending **data migration** reads. List the env keys the
  migration code references and confirm each one exists in the *target* environment before
  the migration runs there. A missing migration-critical key is a hard pre-promotion flag.
- Confirm value *shape* compatibility without reading the values: same kind of key (e.g. a
  URL vs. a token), same expected format, same scope. You are checking for "present and of
  the right kind in both," not comparing the secrets themselves.
- **Never print, paste, echo, log, or diff the secret values.** Reconcile by key name,
  presence, and shape only. A value-level diff would leak secrets into the transcript or
  report — reason about the key inventory, not the contents.
- If the key sets differ in a way that touches a migration or a runtime dependency, treat
  promotion as blocked until the target environment is reconciled. A clean app deploy with a
  missing migration key is still a broken release.

## Scope and ownership

- This is a manual **review** aid. It does not execute, lint, or auto-fix.
- Automated, diff-aware review of a pull request belongs to the **code-review** plugin.
- Deep security analysis (vulnerability classes, taint, exposure modeling) belongs to the
  **security-guidance** plugin.
- Use this checklist to decide *what to look for* and as the fallback when those automated
  tools are unavailable or when a human sign-off is required.
