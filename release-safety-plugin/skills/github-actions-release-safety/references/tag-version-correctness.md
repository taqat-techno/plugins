# Tag and version correctness

A tag is the ref people trust, so it has to be right the first time: re-tagging the same
version later gives two different builds one name. Check these four things before the tag
is pushed, and again on the tag after it exists.

| Check | What "right" means | How to prove it |
|---|---|---|
| Tag matches the manifest | The version in the tag equals the version the package declares (`package.json`, `pyproject.toml`, `Cargo.toml`, `.claude-plugin/plugin.json`, `VERSION`) | `check_release.py` check `tag-matches-manifest` |
| CHANGELOG entry exists | The changelog has a heading for exactly this version | `check_release.py` check `changelog-entry` |
| Semver is monotonic | The version is greater than every earlier tag in the same series (`v*`, or `<package>-v*` in a monorepo); not a re-tag, not a downgrade | `check_release.py` check `semver-monotonic` |
| Tag is on the green commit | The commit the tag points at is the one whose CI run finished green | `git rev-list -n 1 <tag>` equals the SHA of the green run |

## The script

`scripts/check_release.py` in this plugin runs the first three checks. It is read-only: it
reads the manifest and changelog and runs `git tag --list` (plus
`git describe --tags --exact-match` when no tag is given). It never fetches, writes or
pushes. Python 3.8 or later, stdlib only.

```bash
python <plugin>/scripts/check_release.py --tag v1.4.0          # before creating the tag
python <plugin>/scripts/check_release.py                       # the tag on HEAD
python <plugin>/scripts/check_release.py --tag acme-v0.3.0 --root packages/acme
python <plugin>/scripts/check_release.py --version 1.4.0 --json
```

Exit 0 means every check passed or was skipped (a missing manifest or changelog is a skip,
reported as such). Exit 1 means a check failed. Exit 2 means the inputs could not be worked
out (no tag, no version, or a tag with no X.Y.Z in it).

It only sees local tags. Run `git fetch --tags` yourself first if the remote may have tags
your clone lacks; the script will not do it for you.

## Tag on the green commit

```bash
git rev-list -n 1 v1.4.0          # commit the tag points at
git rev-parse origin/main         # commit you pushed and watched go green
```

They must be equal, or the tag must point at a commit whose own run is green. A tag created
on a local commit that was never pushed, or on a commit after the green one, publishes code
nobody tested.

## Rollback readiness (before you promote)

Write down, before promoting, how you would put the previous build back:

- the previous release's tag and the commit or image digest it deployed;
- the exact redeploy action for this platform (redeploy a previous deployment, roll back a
  release, re-run the deploy job on the old tag), and who is allowed to run it;
- whether the release includes a migration that the previous build cannot run against.
  If it does, rollback is not a redeploy: it needs the contract step of the migration
  skeleton to be still pending (see the `migration-safety` skill).

If you cannot name the previous build and the action that restores it, the release has no
rollback, and that is an UNPROVEN item in the go / no-go.
