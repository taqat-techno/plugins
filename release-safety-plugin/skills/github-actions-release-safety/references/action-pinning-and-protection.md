# Action pinning and where the gate really lives

Three rules about the parts of a pipeline the workflow file does not control. They apply
to GitHub Actions directly and to any CI system that pulls shared steps by reference
(GitLab `include:`, Azure Pipelines templates from another repository, CircleCI orbs).

## 1. Pin third-party actions to a full commit SHA

A tag such as `uses: some-org/setup-tool@v3` is a pointer the action's owner can move. If
the owner's account is compromised, or a maintainer re-tags, every workflow that uses the
tag runs new code on its next run, with no diff in your repository. That code runs with
the job's token and secrets.

- Pin to the full 40-character commit SHA and keep the human-readable version in a comment:
  ```yaml
  - uses: some-org/setup-tool@1f2e3d4c5b6a79881726354a5b6c7d8e9f0a1b2c # v3.4.1
  ```
- A short SHA is not a pin: it can collide and some runners refuse it.
- Actions owned by your own organisation, and the CI vendor's first-party actions, are a
  lower risk. Pin them anyway when the job holds deploy or publish credentials.
- Pinning freezes bug fixes too. Let a dependency bot (Dependabot, Renovate) propose SHA
  bumps as reviewed pull requests; that keeps the pin current without trusting a moving ref.
- Container images used as steps have the same problem: pin by digest
  (`image@sha256:...`), not by tag.
- Give the job the least token permission it needs (`permissions:` at workflow or job
  level). A pinned action with a write-all token is still a large blast radius.

How to check a workflow quickly (read-only):

```bash
grep -rnE 'uses:\s*[^ #]+@' .github/workflows | grep -vE '@[0-9a-f]{40}(\s|$)' | grep -v 'uses: \./'
```

Every line printed is a reference that is not pinned to a full SHA (local `./` actions are
excluded).

## 2. An approval-looking YAML block is not the gate

A workflow file can name an `environment: production`, list reviewers in a comment, or
contain a "manual approval" step. None of that is enforcement. What stops a deploy is a
setting outside the file:

- **Environment protection rules** (required reviewers, wait timers, allowed branches) on
  the environment the job names.
- **Branch protection or rulesets** on the branch the workflow deploys from: required
  status checks, required reviews, restrictions on who can push.
- Equivalent settings in other systems: Azure Pipelines environment approvals and checks,
  GitLab protected environments.

So when you review a release pipeline, read the protection settings (through the host's
UI or a read-only API call), not just the YAML. A job that names an environment with no
protection rules deploys without asking anyone. Anyone who can edit the workflow file can
also delete a YAML "approval" step.

## 3. Renaming a job can make a required check pass vacuously

Branch protection lists required checks by name. Rename the job (or the workflow, or a
matrix entry that feeds the check name) and the protection still waits for the OLD name.
Depending on the host, that either blocks every pull request forever, or, when the required
check list is edited to match without anyone noticing that the old gate vanished, lets a
pull request merge with the real test job never required.

- Before renaming a job that a protected branch requires, add the new name to the required
  checks, let both run, then remove the old name.
- After any rename, open a fresh pull request and confirm the protected branch shows the
  new check as required and pending, not missing.
- A required check that is skipped (for example by a path filter) can count as passing on
  some hosts. Keep the required job unconditional, or make the skipped case report a real
  status.

If the `devops` plugin is installed, its CI hardening checklist covers the same ground for
Azure DevOps; this file is self-contained and does not require it.
