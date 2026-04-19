---
name: markdown-authoring
description: Use this skill when Claude is creating or drafting Markdown files — READMEs, runbooks, SOPs, architecture pages, reference docs, troubleshooting guides, concept pages, design notes, or any .md content that will be indexed into a ragtools knowledge base. Activates on phrasing like "write a README for X", "document this component", "create a runbook for Y", "draft an SOP for Z", "add documentation", "write up the architecture", "make chunks well", "RAG-friendly markdown", "optimize for retrieval". Loads the 8 hard rules + 5 page templates + anti-pattern catalog from references/ and produces Markdown that satisfies the ragtools chunker invariants (single-topic sections ≤ 300 words, keyword-rich headings, no YAML frontmatter carrying knowledge, no content-before-first-heading, no pseudo-headings). Never auto-saves files — Claude proposes content; the user accepts/edits/rejects.
version: 0.7.0
---

# markdown-authoring

This skill makes Claude's Markdown output **chunker-friendly** for the ragtools RAG pipeline. The ragtools chunker (`src/ragtools/chunking/markdown.py`) walks heading structure, prepends heading names to every embedded chunk, and paragraph-splits sections over 400 tokens. Writing Markdown with this in mind turns every heading into a retrievable chunk and every chunk into a keyword-anchored semantic claim.

The skill does not save files. It shapes what Claude writes.

## When the skill activates

On any Markdown creation or drafting intent:

- "Write a README for X" / "Document component Y"
- "Create a runbook for incident Z"
- "Draft an SOP for the deploy process"
- "Add an architecture page"
- "Write up the decision record"
- "Make this markdown RAG-friendly"
- "Optimize for retrieval"
- "Create a concept page about N"

Does not activate on code, config, shell, or non-Markdown files.

## Phase 1 — Detect page type

Pick the template that matches the user's intent:

| User intent | Template |
|---|---|
| README, "document this", "what is X" | **Concept page** |
| runbook, troubleshooting, "what to do when X fails", incident response | **Runbook page** |
| SOP, "how to", step-by-step guide, deploy procedure | **SOP page** |
| reference, API, field list, config reference | **Reference page** |
| architecture, design, decision record, component overview | **Architecture page** |
| Something else | **Concept page** (default — most adaptable) |

Full scaffolds in `references/page-templates.md`.

## Phase 2 — Follow the 8 hard rules

Before emitting any Markdown, check every output against the 8 hard rules the ragtools chunker punishes violations of. Full rationale with file:line references to `src/ragtools/chunking/markdown.py` in `references/rag-md-guidelines.md` §3.

1. **Never put knowledge before the first heading.** Open with `# Title` (or `## Title` if the file is a subsection of a larger doc).
2. **Target 150–250 words per leaf section.** The whole section becomes one clean chunk within the 256-token embedding window.
3. **Hard cap: ~300 words per `###` section.** Beyond that triggers paragraph splitting — the tail loses topical coherence with its heading.
4. **Blank lines between paragraphs and around code blocks.** Required for the paragraph-splitter fallback to keep related ideas together.
5. **Keyword-rich, specific headings.** `## Configuring the chunk overlap` beats `## Configuration`. Headings are prepended to every chunk's embedding — they are the biggest single retrieval lever.
6. **Use heading hierarchy semantically.** `##` = topic, `###` = sub-topic, `####` = specific aspect. Don't skip levels.
7. **One idea per heading.** If a section covers two topics, split it: `### X` and `### Y`. Mixed-topic chunks are the #1 retrieval killer.
8. **Leaf headings unique within the file.** Two `### Usage` in one file → the MCP formatter shows both as `file.md > Usage` with no disambiguation.

## Phase 3 — Avoid the 9 anti-patterns

Full table with rationale in `references/anti-patterns.md`.

| Anti-pattern | Why the chunker punishes it |
|---|---|
| Long intro before any `#` heading | Chunks produced have empty headings; MCP formatter shows `file.md >` with no anchor |
| One giant `##` covering several topics | Paragraph splitter produces mixed-topic chunks sharing the same heading |
| Vague headings (`Overview`, `Notes`, `Details`, `Section 1`) | Heading is prepended to every chunk; vague heading = vague embedding |
| Nested `####`/`#####` wrapping tiny 30-word sections | Bloats heading prefix without improving chunk quality |
| Code-block walls (100+ lines, no surrounding prose) | Counts as one paragraph; sentence splitter mangles it when oversize |
| Giant single table (20+ rows) | Same as above — one paragraph; rows get stranded across chunk boundaries |
| YAML frontmatter holding semantic info (`tags:`, `keywords:`, `description:`) | Thrown away by `extract_frontmatter` — invisible to search |
| Identical leaf headings across files (`### Usage`, `### Example`) | MCP output can't disambiguate sources |
| Pseudo-headings (bold text used as section title) | Don't match the heading regex; don't create chunk boundaries |

## Phase 4 — Apply soft rules when producing content

- Code blocks ≤ 60 lines. Longer → break into labelled steps with `###` headings.
- Tables ≤ 15 rows. Longer → split by category.
- Introduce every code block with a prose sentence. Example: *"The following command stops the service:"* before the fence.
- Don't rely on frontmatter for retrieval. If tags/keywords need to be searchable, put them in a `## Tags` section in the body.
- Prefer prose sentences for the first paragraph of a section; put bullets after.

## Phase 5 — Pre-output checklist

Before showing the Markdown to the user, verify:

- [ ] File opens with a `#` heading (no intro-before-heading).
- [ ] Every `##` / `###` section is ≤ 300 words (estimate: 1 word ≈ 1.3 tokens, so 300 words ≈ 400 tokens).
- [ ] Leaf headings are unique within the file.
- [ ] No knowledge in YAML frontmatter. Tags/keywords, if needed, are in a `## Tags` section.
- [ ] Code blocks ≤ 60 lines (split with `###` if longer).
- [ ] Tables ≤ 15 rows (split if longer).
- [ ] Every code block has a prose intro sentence.
- [ ] Headings are specific and keyword-rich, not vague.
- [ ] Heading levels don't skip (`##` → `####` with no `###` in between).
- [ ] Blank lines around headings and code fences.
- [ ] No pseudo-headings (`**Text**` as a section title).

## Boundary — what this skill does NOT do

- **Does not save files.** Claude proposes the content; the user accepts, edits, or rejects as usual. `/md-rag-enhance` is the command that writes.
- **Does not rewrite existing Markdown.** That's `/md-rag-enhance`'s job. This skill only applies when *creating* new content.
- **Does not change the user's content model.** If the user is writing domain content the skill doesn't understand (academic prose, poetry, non-technical documentation), follow the user's preference — the 8 hard rules still apply, but the templates are tools, not mandates.
- **Does not touch non-Markdown files.** Code, config, shell scripts — not in scope.

## See also

- `references/rag-md-guidelines.md` — the full 359-line authoring standard (§1 repo findings, §2 chunking analysis, §3 hard rules, §4 page templates, §5 anti-patterns, §6 unified KB standard, §7 before/after examples, §8 pre-commit checklist).
- `references/page-templates.md` — the 5 copy-paste scaffolds.
- `references/anti-patterns.md` — detailed rationale per anti-pattern.
- `/md-rag-enhance` (sibling command) — scans existing Markdown and safely enhances it.
- `docs/decisions.md` D-023 — the binding decision for this skill + command pair.
- `ragtools_mcp_doc.md` at the workspace root — MCP v2.5.0 contract the retrieval layer uses.
