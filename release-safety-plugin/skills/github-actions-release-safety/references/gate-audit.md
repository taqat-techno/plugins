# gate-audit — soft-fail catalog, prove-it-blocks, shape assertions, tag withdrawal

Support material for the `github-actions-release-safety` skill. The skill owns the rules; this file
holds the lookups and command sequences.

## 1. Soft-fail token catalog (what swallows an exit code)

Grep every workflow / pipeline file for these before trusting a green run. Each one makes the step
**report-only**: it still runs and annotates, but its non-zero exit cannot fail the run.

| Layer | Token | Notes |
|---|---|---|
| Shell | `\|\| true`, `\|\| :`, `\|\| exit 0` | Discards the command's status; the step exits 0 |
| Shell | missing `set -e` in a multi-line `run:` | Only the LAST command's status is the step's status |
| Shell | a failing command inside a pipeline without `set -o pipefail` | Exit status comes from the last pipe stage |
| GitHub Actions | `continue-on-error: true` (step or job) | Step/job shows a warning; the run stays green |
| GitHub Actions | `if: always()` on a *downstream* step | Not itself a soft-fail, but often masks intent — check what it re-enables |
| Action inputs | `fail_action: false`, `soft_fail: true`, `fail-on-error: false`, `continue_on_error` | Per-action names vary; read the action's inputs |
| Linters | `--exit-zero` (ruff/flake8-style), `--no-error-on-unmatched-pattern`, severity set to `warning` | The tool itself returns 0 |
| Test runners | `--passWithNoTests`, an empty/over-narrow selector | Green because nothing ran (see §2) |
| Azure Pipelines | `continueOnError: true`, `failOnStderr: false` | Same semantics as `continue-on-error` |
| GitLab CI | `allow_failure: true` | Job shows an orange warning, pipeline passes |

Suggested sweep:

```bash
grep -rnE '\|\| *(true|:)|continue-on-error|continueOnError|allow_failure|fail[_-]action|soft_fail|--exit-zero' \
  .github/workflows/ ci/ azure-pipelines*.yml .gitlab-ci.yml 2>/dev/null
```

Classify each hit as **intentional advisory** (fine — but its green is informational) or
**accidental report-only** (a gate someone believes blocks).

## 2. Prove-it-blocks recipe

A gate you have never seen fail is unproven. Exercise it once, on a throwaway branch:

1. Pick the *enforcing* check (one with no token from §1).
2. Give it input it MUST reject:
   - linter / compiler -> commit a deliberate syntax error in a file the gate globs
   - schema / config validator -> a known-bad fixture
   - test gate -> a temporary `assert False` in a test the selector actually collects
3. Push and confirm the run goes **red** and the PR check is **blocking** (not just annotated).
4. Revert. Record in the PR or the workflow file that the gate is proven.

Two things this catches that reading YAML does not: a selector that collects **zero** files (green
because nothing ran) and a gate wired to a job that is not in the required-checks list at all.

## 3. Secret-presence guard: shape assertions

Never compare a secret against its own interpolation token, and never rely on emptiness. Map through
`env:` first, then assert on decoded shape.

```yaml
# Azure Pipelines — secrets are NOT auto-exposed; map explicitly
- script: |
    set -euo pipefail
    if [ "${#DEPLOY_KEY_B64}" -lt 100 ]; then
      echo "DEPLOY_KEY: shape check failed (too short)"; exit 1
    fi
    if ! printf '%s' "$DEPLOY_KEY_B64" | base64 -d | head -n1 | grep -q 'BEGIN OPENSSH PRIVATE KEY'; then
      echo "DEPLOY_KEY: shape check failed (not an OpenSSH private key)"; exit 1
    fi
    echo "DEPLOY_KEY: shape OK"
  env:
    DEPLOY_KEY_B64: $(DEPLOY_KEY_B64)
```

Assertions that survive both failure directions: **length threshold**, **known prefix** (`sk-`,
`ghp_`, `-----BEGIN`), **decodes cleanly as base64/JSON**, **decoded first line matches**. All of them
report a verdict without revealing the value.

Never used as a presence test:

- `[ "$S" = '$(S)' ]` — the macro is expanded in the script body, so both sides become the value.
- `[ -z "$S" ]` — an undefined variable is left as the **literal** `$(S)` string, never empty.
- `echo "$S" | head -c 4` — a partial print is still a leak into logs and annotations.

Before changing a variable because a guard says it is missing, confirm against the platform's own
view (variable-list command or REST definition). The guard is the more likely culprit; the observed
cost of skipping this is two red builds and a "fix" that breaks a working path.

## 4. Tag withdrawal sequence

Order matters — deleting the tag does not stop an in-flight publish.

```bash
gh run list --workflow release.yml --limit 5     # find the run the tag triggered
gh run cancel <run-id>                           # 1. stop it FIRST
gh release view <tag>                            # 2. confirm nothing was published
                                                 #    (if a partial release exists, delete it explicitly)
git tag -d <tag>                                 # 3. delete local
git push origin :refs/tags/<tag>                 # 4. delete remote
# fix, push branch, wait for green, THEN re-tag
```

Deleting a published release and re-tagging the same version is user-visible. Surface the state and
the commands; let the user decide.

## 5. Queue-vs-execution triage

A job that shows no progress is either slow or unstartable, and the two need opposite responses.

| Signal | Reading |
|---|---|
| `runner_name` empty, no log lines | Never started — queued. `timeout-minutes` is not running |
| Sibling matrix legs allocated in seconds, one leg not | That leg's label is retired / nonexistent |
| `gh run view --log` refuses ("still in progress") | Normal: the downloadable log archive is only assembled when the RUN completes, so one stuck job hides every sibling's diagnosis from the CLI — the UI's per-job live view is the only way in until then |
| `runner_name` set, log lines advancing slowly | Genuinely executing; `timeout-minutes` applies |

Fix for the unstartable case is the label, not the timeout: check the platform's current runner-image
list and replace the retired label. Then remove any non-blocking job from a gate's `needs`, because
`needs` waits on queue time and will stall the gate without ever failing it.
