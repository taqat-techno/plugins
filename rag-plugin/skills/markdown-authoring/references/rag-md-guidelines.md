Markdown authoring standard for this RAG

  I've inspected the actual pipeline. Findings first, then concrete writing rules grounded in what the code actually does.

  ---
  1 — Repository findings

  Files that implement Markdown ingestion

  ┌───────────────────────────────┬─────────────────────────────────────────┬─────────────────────────────────────────────────────────────────┐
  │             Stage             │                  File                   │                          Key function                           │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Frontmatter + tokens          │ src/ragtools/chunking/metadata.py       │ extract_frontmatter, estimate_tokens                            │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Chunker (heart of the system) │ src/ragtools/chunking/markdown.py       │ chunk_markdown_file, _split_by_headings, _split_large_section   │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Chunk model                   │ src/ragtools/models.py                  │ Chunk (lines 8–18)                                              │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Embedder                      │ src/ragtools/embedding/encoder.py       │ Encoder.encode_batch — all-MiniLM-L6-v2, normalised, cosine     │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Vector DB insert              │ src/ragtools/indexing/indexer.py:80-107 │ chunks_to_points — writes Qdrant payload                        │
  ├───────────────────────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Retrieval formatter           │ src/ragtools/retrieval/formatter.py     │ format_context_compact (MCP), format_context (UI), _deduplicate │
  └───────────────────────────────┴─────────────────────────────────────────┴─────────────────────────────────────────────────────────────────┘

  How the pipeline actually works

  1. frontmatter.load strips YAML frontmatter → body. Frontmatter is NOT indexed or searched (metadata.py:9-21). It's invisible.
  2. _split_by_headings walks every #…###### in the body. Each section runs from its heading to the next heading of any depth. Content before the first
  heading becomes an empty-hierarchy section (markdown.py:110-113).
  3. Parent-heading inheritance is live: a ### Bar under ## Foo inherits ["## Foo", "### Bar"]. A sibling ## Baz resets the chain (markdown.py:115-131).
  4. If the section body ≤ chunk_size=400 tokens → one chunk. Otherwise it's split at \n\n paragraph boundaries with chunk_overlap=100 tokens overlap
  (markdown.py:148-196). Last-resort: sentence splitting (_split_by_sentences).
  5. For each chunk the embedder sees: "Heading1 > Heading2\n\n<raw_text>" — heading names with # stripped, joined by > (markdown.py:255-258). The
  headings are the primary semantic signal prepended before every embedding.
  6. Qdrant payload stores raw_text (no headings), the heading array, file_path, project_id, chunk_index, token_count, file_hash (indexer.py:93-107). No
   frontmatter, no file title, no neighboring-chunk context.
  7. MCP result formatter shows the user only the deepest heading as project/file.md > Heading and truncates raw_text to 600 chars at a sentence
  boundary (formatter.py:78-83, 106-114).
  8. Dedup across results collapses file.md and file_v2.md pairs if the first heading matches (formatter.py:117-132).

  Token-budget reality

  - MiniLM-L6-v2's max_seq_length is 256 tokens. Input beyond that is silently truncated inside the model.
  - Your 400-token chunk target + an 8-ish-token heading prefix ≈ ~300 words embedded. Anything past that is cut before it contributes to the vector. In
   practice this means the tail of a 400-token chunk is weaker than its head.
  - estimate_tokens uses words × 1.33 — an underestimate for code-heavy or table-heavy text.

  ---
  2 — Chunking analysis — what this code rewards

  Rewards

  - Short, heading-anchored sections (~150–250 words each) — the whole section becomes one clean chunk. Best possible case for retrieval.
  - Descriptive, keyword-rich headings — headings prepended to every chunk, so ## Configuring MCP tool access carries weight. ## Overview doesn't.
  - Topically homogeneous sections — one idea per ##. The chunk embedding represents one semantic claim, not three.
  - Explicit paragraph breaks (blank lines) — when sections overflow, good \n\n boundaries let the paragraph splitter keep related ideas together.
  - Stable leaf headings — formatter.py deduplication uses the first heading; predictable leaf names keep versioned files from erasing each other.

  Penalises

  - Content before the first heading — no heading prefix, weaker embedding, harder to attribute in results (formatter.py:80-82 prints empty leaf).
  - Vague headings (Overview, Details, Notes, Section 1) — dilutes the primary semantic signal prepended to every chunk.
  - Giant sections (>400 tokens, roughly >300 words) — force paragraph splitting; the tail of the section becomes a chunk with the same heading chain
  but an unrelated topic, producing "mixed-topic chunks" that pollute search.
  - Walls of text with no blank lines — fall through to sentence splitting (markdown.py:199-241); sentence chunks are the weakest kind.
  - Giant tables and 100-line code blocks — the splitter treats a table/code fence as a single paragraph; if it exceeds chunk_size the sentence fallback
   shreds it.
  - YAML frontmatter carrying knowledge — it's stripped and thrown away. tags: [x, y] is invisible to search.
  - Duplicate first headings across versioned files — formatter.py:117-132 will swallow the older one even if it has unique content.
  - Unicode pseudo-headings (─── Section ───) — not matched by _HEADING_RE, so they don't create a chunk boundary and don't feed the prefix.

  ---
  3 — Markdown writing criteria for this RAG

  Hard rules (the chunker will punish you if you break these)

  1. Never put knowledge before the first heading. Open with a # Title (or ## if the file itself is a subsection), then content. Intros without a
  heading become anchor-less chunks.
  2. Target 150–250 words per deepest section. This is the sweet spot: the section = one chunk, the whole chunk fits in the embedding window.
  3. Hard cap: ~300 words per ### section. Past that you trigger paragraph splitting; the second half loses topical coherence with its heading.
  4. Every section body separated by blank lines. One blank line between paragraphs, two around code blocks. No wall-of-text.
  5. Headings are keyword-rich and specific. ## Configuring the chunk overlap beats ## Configuration. The heading is prepended to every chunk's
  embedding — it's the biggest single lever you have.
  6. Use heading hierarchy semantically. ## = topic, ### = sub-topic, #### = a specific aspect. Don't skip levels.
  7. One idea per heading. If a section covers two topics, split it: ### X and ### Y. Mixed-topic chunks are the #1 retrieval killer.
  8. Leaf headings must be unique within the file. Two sections both titled ### Usage → the MCP formatter shows both as file.md > Usage with no
  disambiguation.

  Soft rules (strongly recommended)

  9. Code blocks stay under ~60 lines. Longer → break into labelled steps with ### headings: ### Step 1 — install, ### Step 2 — configure.
  10. Tables stay under ~15 rows. Beyond that, pre-chunk them: introduce with prose, split into multiple tables by category, or move to a dedicated
  reference/ file.
  11. Prefer prose sentences over terse bullets for the first paragraph of a section. The embedding benefits from natural language context;
  "What/Why/When" in prose first, then bullets.
  12. Introduce every code block in prose. The following command stops the service: before the fence. The prose goes in the chunk with the fence and
  carries the semantic signal the code alone can't.
  13. Don't rely on frontmatter for retrieval. Put tags/keywords in the body under a ## Tags or ## Keywords section if you need them indexed.
  14. Version files by first-heading disambiguation. proposal.md with # Proposal (v1, 2026-01) and proposal_v2.md with # Proposal (v2, 2026-04) —
  otherwise dedup eats one silently.

  ---
  4 — File patterns per page type

  Concept page

  # <Concept name>

  ## What it is
  <1 paragraph, 80–120 words. Ends with a definition-sentence.>

  ## Why it exists
  <1 paragraph, 80–120 words. Problem it solves.>

  ## Key rules
  <bulleted invariants, each bullet a complete sentence>

  ## Related concepts
  <links to sibling pages>
  Produces 3–4 tight, heading-anchored chunks.

  SOP page (walkthrough)

  # SOP: <action>

  ## Purpose
  <1 paragraph>

  ## Preconditions
  <bulleted checklist>

  ## Step 1 — <verb + noun>
  <prose explaining what to do>
  <code block if needed, under 60 lines>

  ## Step 2 — <verb + noun>
  ...

  ## Validation
  <how to confirm it worked>

  ## Failure modes
  <table or bulleted list of known failures + links to runbooks>
  Every step is its own chunk under a named leaf heading.

  Reference page

  # <Area> reference

  ## <Table 1 — ~10 rows>
  | Field | ... |

  ## <Table 2 — ~10 rows>
  | Field | ... |
  Each ## holds one short table → one chunk per table. Never dump a 50-row table under one heading.

  Runbook / troubleshooting page

  # Runbook: <symptom>

  ## Symptom
  <1 paragraph — user-visible evidence>

  ## Likely causes
  <bulleted list>

  ## Diagnosis
  ### Check <X>
  ...

  ### Check <Y>
  ...

  ## Recovery
  ### If <cause A>
  ...

  ### If <cause B>
  ...

  ## Prevention
  <paragraph>
  Each diagnostic / recovery branch = its own ### chunk.

  Architecture page

  # <Component> architecture

  ## What it is
  ## How it fits in the system
  ## Key decisions
  ### Decision — <name>
  ### Decision — <name>
  ## Failure modes
  ## Code paths
  Decisions become independent chunks, each retrievable by name.

  ---
  5 — Anti-patterns to avoid

  ┌───────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────┐
  │                       Anti-pattern                        │                                Why it hurts this RAG                                │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Long intro before any # heading                           │ Chunks produced have empty headings; formatter shows them as file.md > with no      │
  │                                                           │ anchor; embedding lacks the keyword prefix.                                         │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ One giant ## section covering several topics              │ Paragraph splitter produces mixed-topic chunks sharing the same heading —           │
  │                                                           │ false-confidence matches in retrieval.                                              │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Vague headings (Overview, Notes, Details)                 │ The heading is prepended to every chunk's embedding. Vague heading = vague          │
  │                                                           │ embedding.                                                                          │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Nested ####/##### wrapping tiny 30-word sections          │ You're bloating the heading prefix without improving chunk quality. Stop at ###     │
  │                                                           │ except for step-by-step SOPs.                                                       │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Code-block walls (100+ lines, no surrounding prose)       │ Counts as one paragraph; when oversize, sentence splitter mangles it; the resulting │
  │                                                           │  chunks have no natural-language anchor.                                            │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Giant single table (20+ rows)                             │ Same as above — one paragraph to the splitter. When oversize, rows get stranded     │
  │                                                           │ across chunk boundaries.                                                            │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ YAML frontmatter holding semantic info (tags:, keywords:, │ Thrown away by extract_frontmatter — invisible to search.                           │
  │  description:)                                            │                                                                                     │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Identical leaf headings across files (### Usage, ###      │ MCP output shows file.md > Usage with no differentiation; LLM can't distinguish     │
  │ Example, ### Notes everywhere)                            │ sources.                                                                            │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Duplicate file versions without first-heading change      │ formatter.py:117-132 dedup collapses them, dropping one silently.                   │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Pseudo-headings (bold text used as a section title        │ Don't match the heading regex; don't create chunk boundaries; embedding pollutes    │
  │ instead of ##)                                            │ adjacent sections.                                                                  │
  ├───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Mixing languages / scripts mid-section                    │ MiniLM is English-tuned; non-English text inside an English section dilutes the     │
  │                                                           │ embedding vector.                                                                   │
  └───────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────┘

  ---
  6 — Unified knowledge base standard

  To make many files feel like one KB:

  1. File naming = topic-url-safe-kebab-case. project-status.md, not Project Status.md or ProjectStatus.md. Consistent paths let dedup work correctly
  and make source citations legible.
  2. Project IDs follow the same convention as directory names. project_id is visible in every search result — make it readable.
  3. Every file opens with a # Title matching the filename's intent. First heading is the dedup key.
  4. Reserved section names across files. Pick a small vocabulary and reuse it:
    - ## Purpose, ## Scope, ## Preconditions, ## Steps, ## Validation, ## Failure modes, ## Related, ## Change log.
  When the same prompt ("what are the preconditions for X?") can hit the same named heading across files, retrieval is predictable.
  5. Terminology dictionary. Maintain one glossary.md per project. Link to it instead of redefining terms. Don't let service, daemon, process drift
  meaning across files.
  6. Cross-file links use relative paths ([See indexer](../architecture/indexing-pipeline.md)) so they survive renames. The link text goes into a chunk,
   so link text matters semantically — use descriptive anchor text, not "click here".
  7. One topic per file. If a file has five ## sections covering unrelated topics, split into five files. Retrieval per-chunk ignores file boundaries;
  file size doesn't matter for quality, but mixed files produce cross-polluted search because the same file_path shows up repeatedly in unrelated
  queries.
  8. Every page has a metadata block (plain Markdown table, not YAML frontmatter) with Owner / Last validated against version / Last reviewed / Status —
   already standard in docs/wiki-src/** (see Standards-and-Governance/Documentation-Standards.md). The table is indexed and retrievable; frontmatter is
  not.

  ---
  7 — Before / after examples

  Example A — bad (intro before heading, vague heading, wall of text)

  This document describes how to configure the service. The service is
  started with various flags that control its behaviour. It's important
  to understand these before deploying.

  ## Overview

  The service takes a host, a port, a log level, and optionally a
  startup delay, a notification flag, a desktop notifications flag,
  and a cooldown seconds setting. These all have defaults. The host
  is 127.0.0.1 and the port is 21420 for installed, 21421 for dev.
  Log level defaults to INFO. You can override all of these via env
  vars with RAG_ prefix or in ragtools.toml. Changes to service_port
  require a restart. Other fields hot-reload.

  Problems: Intro has no heading → anchor-less chunk. ## Overview is generic → weak embedding prefix. 90-word paragraph with eight config keys → one
  chunk covering 8 topics → mixed-topic match for every config query.

  Example A — good

  # Service configuration

  ## Network binding — host and port

  The service binds to `127.0.0.1` by default. Override with
  `RAG_SERVICE_HOST` or `[service].host` in `ragtools.toml`.
  Port defaults to 21420 (installed) or 21421 (dev) to avoid
  collision; override with `RAG_SERVICE_PORT`. Port changes
  require a service restart.

  ## Log level

  Set with `RAG_LOG_LEVEL` or `[service].log_level`. Valid values:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`. Hot-reloads on change.

  ## Desktop notifications

  Toggle with `RAG_DESKTOP_NOTIFICATIONS` or the admin-panel
  Settings page. Cooldown between toasts is
  `RAG_NOTIFICATION_COOLDOWN_SECONDS` (default 30 s).

  Why it works: Every concept is its own ## chunk. Heading carries keywords (host and port, Log level, Desktop notifications). Each chunk is 40–60
  words, well under the 256-token embedding window. A search for "how do I change the port" now lands on one tight chunk about host and port.

  Example B — oversized section

  ## Indexing pipeline

  <1200 words describing scan → chunk → embed → upsert → state tracking
  all in one section, no subheadings>

  Problem: One ## → paragraph splitter fires → produces ~4 chunks that all claim heading ## Indexing pipeline but cover scan, chunk, embed, upsert
  separately. Retrieval returns "all about indexing pipeline" with no way to tell which stage.

  Example B — good

  ## Indexing pipeline

  Brief intro — one paragraph explaining the four stages.

  ### Stage 1 — Scan
  <200 words>

  ### Stage 2 — Chunk
  <200 words>

  ### Stage 3 — Embed
  <200 words>

  ### Stage 4 — Upsert to Qdrant
  <200 words>

  Each stage becomes its own chunk with a specific leaf heading. "How does chunking work?" lands directly on Stage 2.

  ---
  8 — Implementation recommendation

  Do this: create docs/knowledge-base-markdown-guidelines.md in the repo and surface it from the existing
  docs/wiki-src/Standards-and-Governance/Documentation-Standards.md (the ownership-standards page, which today doesn't cover chunk-optimised writing).

  The guidelines file should contain the five things authors actually need at their desk:

  1. The 8 hard rules (section 3 above) as a numbered checklist.
  2. The 5 page templates (section 4) as copy-paste scaffolds.
  3. The anti-pattern table (section 5).
  4. Why it matters — one-paragraph grounding in the actual chunker behaviour so future authors understand the "why" when these rules look restrictive,
  with file:line references to chunking/markdown.py so the claims are verifiable.
  5. A pre-commit checklist authors can run through:
    - File opens with a # heading (no intro-before-heading)
    - Every ##/### section ≤ 300 words
    - Leaf headings are unique within the file
    - No knowledge in YAML frontmatter
    - Code blocks ≤ 60 lines (split with ### if longer)
    - Tables ≤ 15 rows (split if longer)
    - Every code block has a prose intro sentence
