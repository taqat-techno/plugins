# release-safety

## What it does

Proves a release is safe before you trust it: that a fix is really deployed to the target
environment (not just merged), that env secrets match before promotion, that a tag is the
right tag, and that risky migrations and cutovers follow a reversible skeleton. It is
provider-neutral: the Git host, CI system, hosting platform, database and ORM are
discovered from the project, never assumed.

It is for anyone who ships through CI to a hosted environment and wants "it's fixed" to mean
"proven in the environment". **Nothing here deploys, migrates, tags or blocks on its own.**
The skills and the command read and advise; the hooks remind, and only ask you to confirm
when you turn on `ask` mode.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install release-safety@taqat-techno-plugins
```

On Claude Code 2.1.275 or later, one step also works:
`/plugin install release-safety --marketplace taqat-techno/plugins`.

## Requirements

| Requirement | Why | Check |
|---|---|---|
| Python 3.8 or later as `python3`, `python` or `py -3` | the hooks and `scripts/check_release.py` | `python3 --version` |
| A POSIX shell for hook commands (Git Bash on Windows) | the hook launcher is POSIX sh | `sh --version` |
| git | tag checks read `git tag --list` | `git --version` |
| Your CI/host CLI (for example `gh`), optional | the skills use it read-only when it is there | `gh --version` |

## Commands

| Command | What it does |
|---|---|
| `/release-safety:release-verify [sha \| branch \| environment \| what you are releasing]` | Walks the pre-promotion checklist and reports each item PROVEN / UNPROVEN / NOT-APPLICABLE with evidence. With no argument it runs the full checklist. |

## Skills

| Skill | Use when |
|---|---|
| `release-verification` | asking whether a fix is live in an environment, before promoting, when a deploy "succeeded" but nothing changed, or a red CI job is blamed on an env var |
| `migration-safety` | running a risky migration, cutover or backfill, reviewing destructive or CASCADE changes, or checking migration and schema drift |
| `github-actions-release-safety` | writing or reviewing CI workflows, citing a green check, creating or pushing a tag or release, pinning actions, or debugging dispatch, queueing and secret-presence guards |

References, loaded on demand:

| File | Covers |
|---|---|
| `skills/release-verification/references/deployed-sha-reconciliation.md` | reading the running SHA, containment and branch mapping, deploy-liveness failure modes |
| `skills/release-verification/references/env-secret-diff.md` | env-key diff by name, resolving the connection target, the local-fallback guard |
| `skills/migration-safety/references/cutover-skeleton.md` | the expand/contract runbook |
| `skills/migration-safety/references/destructive-checks.md` | soft-delete bypasses and the cascade-FK inventory |
| `skills/github-actions-release-safety/references/gate-audit.md` | soft-fail sweep, prove-it-blocks, shape assertions, tag withdrawal, queue triage |
| `skills/github-actions-release-safety/references/action-pinning-and-protection.md` | SHA-pinning actions, where approval is really enforced, the renamed-required-check trap |
| `skills/github-actions-release-safety/references/tag-version-correctness.md` | tag versus manifest, CHANGELOG and earlier tags; tag on the green commit; rollback readiness |

### Script: `scripts/check_release.py`

Read-only tag / version check. It reports `tag-matches-manifest` (package.json,
pyproject.toml, Cargo.toml, .claude-plugin/plugin.json or VERSION), `changelog-entry` and
`semver-monotonic` (against earlier tags in the same series, so `acme-v*` tags in a monorepo
are their own series). It runs only `git tag --list` and `git describe --tags --exact-match`.

```bash
python scripts/check_release.py --tag v1.4.0       # before you create the tag
python scripts/check_release.py                    # the tag on HEAD
python scripts/check_release.py --version 1.4.0 --json
```

Exit 0 pass, 1 a check failed, 2 inputs could not be determined. It sees only local tags.

There are no agents.

## Hooks

| Hook | Event / matcher | What it does | Can block? |
|---|---|---|---|
| `hooks/session_start_release_advisory.py` | `SessionStart` | In a project with CI or deploy configuration (`.github/workflows`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `fly.toml`, `vercel.json`, `railway.json`, `Procfile`, release-tool configs, ...) it gives Claude one reminder to run `/release-safety:release-verify` and the check script. Once per project; silent elsewhere. | No |
| `hooks/release_push_guard.py` | `PreToolUse` on `Bash\|PowerShell` | Spots a branch and tag pushed together, `git push --tags`/`--follow-tags`, pushing a release tag, `gh release create`, and remote tag or release deletion | Only in `ask` mode, by asking you; never denies |

In the default `advise` mode the push reminder is PreToolUse `additionalContext`, which
Claude Code delivers with the tool result: the push has already happened when Claude reads
it. Only `ask` mode stops the command first. The guard matches the command that runs, not
text in quotes or commit messages. It cannot see tags pushed by scripts, aliases or a CI
job. Check its table offline with `python hooks/release_push_guard.py --self-test`.

## Configuration

| Setting | Where | Values | Default |
|---|---|---|---|
| `guard_mode` | plugin option (`/config`; reaches the hook as `CLAUDE_PLUGIN_OPTION_GUARD_MODE`) | `advise`, `ask`, `off` | `advise` |
| `session_hint` | plugin option (`CLAUDE_PLUGIN_OPTION_SESSION_HINT`) | `true`, `false` | `true` |
| `RELEASE_SAFETY_MODE` | environment variable set before starting Claude Code; overrides `guard_mode` | `advise`, `ask`, `off` | unset |
| `RELEASE_SAFETY_HINT` | environment variable; `off` silences the SessionStart reminder | `off` | unset |

To see the SessionStart reminder again in a project, delete
`${CLAUDE_PLUGIN_DATA}/session-hint/` (the folder Claude Code keeps for this plugin under
`~/.claude/plugins/data/`).

## Platform support

| Platform | Status |
|---|---|
| Linux, macOS | Supported. |
| Windows with Git Bash | Supported; both the Bash and PowerShell tools are watched. |
| Windows without Git Bash | Hook commands run in PowerShell, where the POSIX launcher does not parse; the hooks fail open (do nothing). Skills, command and script work. |
| WSL | Same as Linux. |

## Data & privacy

- The SessionStart hook checks whether release files exist in the project and writes one
  marker file per project under `${CLAUDE_PLUGIN_DATA}/session-hint/`. The marker name is a
  hash of the project path; it holds no content. Claude Code deletes the folder on uninstall.
- The push guard reads only the command in the hook payload, writes nothing and echoes no
  command text.
- `check_release.py` reads the manifest and changelog and runs read-only git commands.
- Nothing is sent anywhere by the plugin. When the skills call your CI or host CLI, that
  traffic goes to your provider under your credentials. Secret values are never printed:
  env keys are compared by name and presence only.

## Limitations

- Advise-mode reminders arrive after the command runs.
- The skills cannot see your provider's settings unless a CLI or API is available; anything
  they cannot read is reported UNPROVEN, not assumed.
- `check_release.py` knows five manifest formats; use `--manifest` for anything else
  (a JSON file with a `version` field or a one-line version file).
- Related plugins are optional. If `agent-safety-guards` is installed, its `agent-safety`
  skill handles a secret that leaked into the session; if `django` is installed, its
  `django-testing` skill has the rolled-back reproduction recipe.

## License

MIT. See `LICENSE`.
