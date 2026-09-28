---
title: 'Odoo Official Skills'
read_only: false
type: 'command'
description: "Install, update or remove Odoo's official agent skills (20.0+) in this project, matched to its Odoo version"
argument-hint: '[install|update|status|remove] [--branch 20.0|master] [--force]'
---

# /official-skills

Odoo S.A. publishes agent skills in the Odoo repository itself (`skills/` on 20.0 and
master):

| Skill | Covers |
|---|---|
| `odoo-guidelines` | House rules for everything outside `static/` |
| `odoo-web-guidelines` | JavaScript, Owl and SCSS |
| `odoo-security` | A pattern sweep audit |
| `odoo-review` | A two-pass review |

This command installs the set that matches **this project's Odoo version** into
`<project>/.claude/skills/`, fetched from upstream. Nothing is vendored: the skills stay
Odoo's (LGPL-3), current and version-exact.

## Bare-invocation behavior (no args)

Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/official_skills.py" --project "<project root>"`.
The script:

1. detects the Odoo version from the project's module manifests (majority vote), falling
   back to `odoo/release.py`;
2. on **20.0+**, installs the matching set, or updates it when upstream has moved;
3. on **14–19**, installs nothing and explains why. Those branches ship no official skills,
   and the 20.0 rules are wrong there: `ir.access` replaces `ir.model.access` and
   `ir.rule`, `t-esc`/`t-raw` are gone, and constraints are declared only with
   `models.Constraint`.

Report the result, including the branch, the upstream commit and the installed skills. Tell
the user to **restart the session** so the skills are discovered.

## Subcommands

| Command | What it does |
|---|---|
| `install` | Fetch the set for the detected version, or for `--branch` |
| `update` | Re-fetch when upstream has a newer commit |
| `status` | Show the installed set and commit, and whether upstream moved |
| `remove` | Delete only the directories this command installed (each carries a `.odoo-official.json` marker) |

## Rules

- **Never pass `--branch` to force 20.0 rules onto a 14–19 project.** Use it only when the
  project really targets that branch, for example a migration branch.
- **Never overwrite a same-named skill the user wrote.** The script refuses without
  `--force`. Ask before passing it.
- Do not edit the installed files; they are upstream's. Run `update` to refresh them.
- `.claude/skills/` may or may not belong in the project's version control. Mention it and
  let the user decide.
- Once installed, odoo-plugin's `reviewer` and `security` skills use them as the rule floor
  on 20.0+ projects (see the reviewer's `references/official_odoo_skills.md`).
- `GITHUB_TOKEN` or `GH_TOKEN`, if set, lifts the anonymous GitHub API rate limit.
