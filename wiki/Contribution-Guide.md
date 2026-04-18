# Contribution Guide

How to contribute to **taqat-techno-plugins**. This page supplements (and overrides where they conflict) the older [`CONTRIBUTING.md`](../../CONTRIBUTING.md) at the repo root, which was written before the plugin taxonomy stabilized on commands / agents / skills / hooks / MCP / rules.

## What contributions are welcome

- **Bug fixes** in existing plugins.
- **New capabilities** for existing plugins (prefer skill workflows over new commands — see [[Plugin Development Guide|Plugin-Development-Guide]]).
- **New plugins** that fill a gap in the existing catalog.
- **Documentation** — this wiki, plugin READMEs, ARCHITECTURE notes, binding decisions.
- **Audits** — audit-style reports are the house format for major reviews (see `HOOK_STABILIZATION_REPORT.md` etc.).

## What contributions need extra discussion first

- **New commands** in existing plugins. Consolidation is preferred. Open an issue first; propose why a new command is better than a flag on an existing command.
- **Breaking changes** to a plugin's manifest, command surface, or binding decisions. These need a new D-NNN entry in the plugin's `docs/decisions.md`.
- **Changes to `claude-plugins-official-main/`.** This is vendored read-only. Copy patterns into `plugins/` instead.
- **Workspace-level infrastructure** (`validate_plugin.py`, `marketplace.json` schema). Open an issue to discuss impact across all plugins.

## Workflow

### 1. Open an issue (unless it's a trivial fix)

For anything more than a typo or obvious bug fix, open an issue describing:

- The problem or enhancement.
- Which plugin(s) are affected.
- The proposed approach, including whether it's a command, skill, agent, hook, rule, or reference-only change.

### 2. Fork, branch, build

```bash
gh repo fork taqat-techno/plugins --clone
cd plugins
git checkout -b <feature-branch>
```

### 3. Follow the house conventions

Full details in [[Plugin Development Guide|Plugin-Development-Guide]] and [[Architecture]]. Summary:

- **Consolidation over sprawl.** Prefer a new flag on an existing command over a new command.
- **Skills over commands.** Skills auto-activate on user intent; new workflows belong in the skill first.
- **Single-owner layering.** Each concern lives in one file. Don't duplicate logic across commands / skills / agents.
- **State-aware commands.** Commands start with a state-detection preamble; they refuse gracefully on bad states.
- **Binding decisions** in `<plugin>/docs/decisions.md` for load-bearing choices, with "Reverse only if:" exit criteria.
- **Hooks enforce, don't reason.** Command-type only, JSON output, fail silent on error.
- **Typed confirmation gates** for every destructive step.
- **Cross-platform parity.** Windows + macOS + Linux branches explicit where behavior differs.
- **Local-first.** No network egress unless explicit and opt-in.

### 4. Validate

```bash
python plugins/validate_plugin.py <plugin-dir>
```

Fix all errors. Document known-false-positive warnings in the plugin's CHANGELOG; never silence them.

### 5. Update documentation

For any plugin change:

- [ ] Update the plugin's `README.md` if the command surface or setup changed.
- [ ] Update the plugin's `CHANGELOG.md` (mandatory for mature plugins; strongly recommended otherwise).
- [ ] Update `docs/decisions.md` with a new D-NNN if the change is load-bearing.
- [ ] Update `plugins/README.md` (marketplace catalog) if plugins were added / removed / renamed.
- [ ] Update `plugins/wiki/<Plugin>-Plugin.md` to reflect the new behavior.
- [ ] Update `plugins/wiki/_Sidebar.md` if a new wiki page was added.
- [ ] Bump `plugin.json` version per [semver](https://semver.org/).

Documentation drift has been a recurring regression — enforce the checklist in PR review.

### 6. Commit discipline

Commit messages follow the conventional-commits-ish style visible in the git log:

```
<type>(<scope>): <short summary in imperative mood>

<body — what changed, why, non-violation notes for binding-decision changes>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

Types seen in the repo:

- `feat(<plugin>):` — new capability
- `fix(<plugin>):` — bug fix
- `refactor(<plugin>):` — restructuring without behavior change
- `docs:` — documentation only
- `fix(hooks):` — hook ecosystem fixes (common)
- `chore:` — maintenance, validator, tooling

Co-author Claude on AI-assisted commits to match the established footer pattern.

### 7. Push — permission-first, account switching

**Never push without explicit user approval.** The CLAUDE.md rules are binding:

```
Permission First: never push or commit any update before asking permission
```

When pushing:

```bash
# 1. Check remote
git remote -v
# → origin  https://github.com/taqat-techno/plugins.git (push)

# 2. Switch to the right account for taqat-techno/*
gh auth switch --user a-lakosha

# 3. Push
git push origin <branch>

# 4. Switch back to the default account
gh auth switch --user ahmed-lakosha
```

For `ahmed-lakosha/*` repos, skip the switch (that account is already the default).

### 8. Open the PR

```bash
gh pr create --title "<title>" --body "..."
```

PR template:

```markdown
## Summary
- 1–3 bullets on what changed

## Test plan
- [ ] `python plugins/validate_plugin.py <plugin-dir>` passes
- [ ] Updated plugin README + CHANGELOG
- [ ] Updated marketplace README if plugin count changed
- [ ] Updated wiki page
- [ ] Cross-platform tested (Windows + macOS or Linux)
- [ ] Binding decision (D-NNN) added if load-bearing

## Related
- Closes #NNN
- Supersedes D-NNN (if applicable)
```

## Publishing the wiki

The wiki source lives in `plugins/wiki/`. GitHub Wikis are a separate Git repo at `<repo>.wiki.git`. To publish:

### One-time setup

1. On GitHub, enable the Wiki feature for the repo (Settings → Features → check **Wiki**).
2. Visit `https://github.com/taqat-techno/plugins/wiki` and click **Create the first page** — any minimal content. This creates the `.wiki.git` repo.

### Sync source → wiki

```bash
# Clone the wiki repo (once)
git clone https://github.com/taqat-techno/plugins.wiki.git ~/wiki-taqat-techno

# Copy source files
cp plugins/wiki/*.md ~/wiki-taqat-techno/

# Commit and push to the wiki
cd ~/wiki-taqat-techno
gh auth switch --user a-lakosha
git add -A
git commit -m "docs(wiki): sync from plugins/wiki/"
git push origin master
gh auth switch --user ahmed-lakosha
```

### Why source-in-repo?

- PRs can review wiki changes alongside code changes.
- Plugin changes + wiki updates land in the same commit.
- Git log captures wiki history in the main repo.
- No separate `.wiki.git` cloning during development.

The wiki at `<repo>.wiki.git` is the **published surface**; `plugins/wiki/` is the **edited source**. A future docs-sync workflow could automate this, but manual sync is fine for now.

## Reporting bugs

Open an issue with:

- Claude Code version.
- Plugin name and version (`cat plugins/<name>-plugin/.claude-plugin/plugin.json`).
- OS and shell.
- Exact error or unexpected behavior.
- Minimal steps to reproduce.
- For plugins with diagnostic commands (`/rag-doctor --full`, `/odoo-service`, `/pandoc status`), include their output.

## Suggesting features

Open an issue describing:

- The use case — what problem does this solve?
- Which plugin would own it (or is it a new plugin)?
- Whether it's a command, skill workflow, agent, hook, rule, or reference change.
- Any known constraints (cross-platform, network-egress, dependencies).

## Code of conduct

- Respectful, constructive, evidence-driven.
- Cite filenames and line numbers.
- Prefer "the file says X" over "I think X".
- Corrections over apologies — when evidence contradicts an earlier claim, add a retraction D-NNN and move on.

## See also

- [[Plugin Development Guide|Plugin-Development-Guide]] — how to author the components
- [[Architecture]] — shared patterns you'll be following
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) at the repo root (older, skill-first-era guide — still useful but less current than this wiki page)
- [[Change History|Change-History]] — see what's been done
