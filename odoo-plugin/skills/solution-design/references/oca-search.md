# Searching OCA per version branch — and judging what you find

OCA modules live in topic repositories (`OCA/stock-logistics-warehouse`, `OCA/sale-workflow`,
`OCA/manufacture`, `OCA/pos`, `OCA/account-financial-tools`, `OCA/server-tools`, `OCA/web`, …),
one **branch per Odoo version** (`17.0`, `18.0`, `19.0`). A module on `16.0` only is not
available for 17 until its migration PR is merged.

## Finding candidates

1. **Pick the owning repositories** for the domain (stock → `stock-logistics-*`, sales →
   `sale-workflow`, POS → `pos`, accounting → `account-*`, MRP → `manufacture`, HR → `hr*`).
2. **List the branch's modules** (no clone needed):
   ```bash
   gh api repos/OCA/stock-logistics-warehouse/contents?ref=19.0 --jq '.[] | select(.type=="dir") | .name'
   ```
3. **Search by keyword on the branch.** GitHub code search covers the default branch only, so
   search, then confirm on the version branch:
   ```bash
   gh search code --owner OCA "negative stock" --filename __manifest__.py --limit 30
   gh api "repos/OCA/<repo>/contents/<module>/__manifest__.py?ref=19.0" --jq .content | base64 -d
   ```
4. **Check open migration PRs** when the module exists only on an older branch:
   `gh pr list -R OCA/<repo> --search "[19.0][MIG] <module>" --state open`.
5. **apps.odoo.com** lists OCA modules too, but its version tabs lag; the branch is the truth.
6. A ragtools/knowledge-base hit on a client repository is not evidence that a module exists
   upstream; confirm on GitHub.

## Recording a candidate

| Field | Where |
|---|---|
| repo / module / branch | the path you read |
| `development_status` (Alpha, Beta, Production/Stable, Mature) | manifest |
| version, licence, maintainers | manifest |
| last commit on the module folder | `gh api "repos/OCA/<repo>/commits?path=<module>&sha=19.0&per_page=1" --jq '.[0].commit.committer.date'` |
| `depends` and `external_dependencies` | manifest — pull in their own OCA dependencies too |
| open issues for the version | `gh issue list -R OCA/<repo> --search <module>` |

## Judging maturity

- **Alpha** — not for production without your own review; usually a reason to skip the rung.
- **Beta** — usable after the behaviour check in [reuse-ladder.md](reuse-ladder.md).
- **Production/Stable, Mature** — still run the behaviour check; maturity is about API
  stability, not about fitting your requirement.
- No commit since the version branch was created, or only the migration commit: treat as
  unmaintained for that version.
- A module whose `depends` drags in a large stack you otherwise don't need costs more than
  a small custom extension; record that as the skip reason.

## Using an accepted OCA module

Vendor module by module, never a whole OCA repository as a submodule: copy only the modules you
depend on into an `oca/` folder with a README recording repo, branch, commit, version and
licence. Never edit vendored code — extend it from your own module. Put `oca/` once on
`addons_path` so a single copy loads. The Odoo.sh specifics of this are owned by the `odoo-sh`
skill.
