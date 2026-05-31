# Wiki Page Templates

Generic, portable starter templates for Wiki pages. Copy a template, fill in the placeholders, and publish. Nothing here is tied to a specific project, team, company, or workspace, so the same files work in any repository or Wiki.

## How to use these templates

1. Copy the template that matches the page you want to write.
2. Replace every `<ANGLE_BRACKET>` placeholder with your own content.
3. Delete sections that do not apply and add ones that do.
4. Remove any block marked `Example (illustrative — not required)` before publishing.

Placeholders always look like `<PLACEHOLDER_NAME>`. If you see a value wrapped in angle brackets, it is meant to be replaced. Plain text and headings outside angle brackets are reusable as written.

## Conventions

- Placeholders use `<ANGLE_BRACKETS>` and are written in `UPPER_SNAKE_CASE`.
- One topic per page. Split large subjects into linked pages instead of one long page.
- Use descriptive, keyword-rich headings so the page is easy to scan and search.
- Keep paths, URLs, names, and credentials out of templates. Supply your own at fill-in time, and never commit secrets or tokens.
- Examples are clearly labeled `Example (illustrative — not required)` and are safe to delete.

## Available templates

| Template | Purpose |
|----------|---------|
| `sop.md` | Standard Operating Procedure: a repeatable, step-by-step process with owners and prerequisites. |
| `runbook.md` | Operational runbook: detection, diagnosis, and recovery steps for a known operational scenario or incident. |
| `role-guide.md` | Role guide: what a given role owns, the access it needs, and the routine duties it performs. |
| `user-manual.md` | End-user manual: task-oriented instructions that explain how to use a feature or product. |
| `workflow.md` | Workflow page: an end-to-end process with stages and decision points, including a Mermaid diagram block. |
| `release-handover.md` | Release handover: what shipped, how it was validated, known issues, and rollback notes for the next owner. |
| `onboarding.md` | Onboarding guide: the first-day-to-first-week checklist for someone joining a team or project. |

## Mermaid diagrams

`workflow.md` includes a Mermaid diagram block so the process can be rendered visually. To customize it, edit the fenced ` ```mermaid ` block in place. Keep node labels generic and replace them with your own stages and decisions.

## Related skills

These templates pair with two skills in this plugin:

- **wiki-authoring** — guidance for writing clear, well-structured Wiki pages and choosing the right template.
- **wiki-mermaid** — guidance for authoring and validating Mermaid diagrams embedded in Wiki pages.

Use the templates as the starting structure, then lean on the skills for authoring decisions and diagram syntax.
