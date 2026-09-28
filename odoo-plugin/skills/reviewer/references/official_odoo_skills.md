# Working with Odoo's official skills (20.0+)

Odoo S.A. publishes `odoo-guidelines`, `odoo-web-guidelines`, `odoo-security` and
`odoo-review` in the Odoo repository (`skills/`, 20.0 and master). `/official-skills`
installs the set matching a project's Odoo version into `<project>/.claude/skills/`,
fetched from upstream. Each installed skill directory carries a `.odoo-official.json`
marker naming its branch and commit.

## Which rules win

| Project version | Official skills installed? | Rule floor | This plugin adds |
|---|---|---|---|
| 20.0+ | yes | **Odoo's**. Run `odoo-review`'s process and read the mapped `odoo-guidelines` / `odoo-web-guidelines` / `odoo-security` sections | Multi-tenancy isolation, live verification through the MCP (`odoo_inspect_model`, effective access), recorded field lessons, and anything the official set does not cover |
| 20.0+ | no | this plugin, including `v20_deltas.md` | Suggest `/official-skills` once |
| 14–19 | no | this plugin (`v19_deltas.md`, the version traps) | — |
| 14–19 | **yes** (marker branch `20.0`/`master`) | this plugin | Flag the mismatch: the 20.0 rules are wrong here. Recommend `/official-skills remove` |

A finding from both sources is reported once, citing the official section first.

## Detecting it

- Installed: `<project>/.claude/skills/odoo-review/.odoo-official.json` exists. Read its
  `branch` and `commit`.
- The project version: the `version` in the touched modules' `__manifest__.py`
  (`20.0.x.y.z`). Check this before applying any rule from either source; their own review
  skill requires the same (confirm the API exists at the reviewed revision).

## Why not copy them into this plugin

- **Version.** They are written for 20.0 and would produce false findings on 14–19.
- **Freshness.** They change weekly, and a vendored copy goes stale.
- **Licence.** They are LGPL-3, part of Odoo Community. Fetching them into a project
  redistributes nothing.

Rules from them that also hold on older versions are restated, version-gated and in this
plugin's own words, in `security_pitfalls.md`, `coding_guidelines.md` and
`change_impact.md`.
