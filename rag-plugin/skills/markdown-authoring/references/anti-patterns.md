# Anti-patterns — what hurts the ragtools RAG pipeline

Nine anti-patterns, with the specific mechanism by which each one hurts retrieval. Grounded in the actual behavior of `src/ragtools/chunking/markdown.py` and `src/ragtools/retrieval/formatter.py`.

Source: `references/rag-md-guidelines.md` §5.

## 1. Long intro before any `#` heading

**What it looks like:**
```markdown
This document describes how to configure the service. The service
takes various flags that control its behaviour. It's important to
understand these before deploying.

## Overview
...
```

**Why it hurts:** the chunker produces an empty-hierarchy section for content before the first heading (`markdown.py:110-113`). The MCP formatter prints it as `file.md >` with no anchor (`formatter.py:80-82`). The embedding has no heading prefix — the biggest single retrieval signal is missing.

**Fix:** move the intro under the first `#` heading. If the file has a title concept, use it: `# Service configuration` + intro underneath.

## 2. One giant `##` section covering several topics

**What it looks like:**
```markdown
## Configuration

The service takes a host, port, log level, startup delay, notification
flag, desktop notifications flag, cooldown seconds... <continues for
800 words about 8 different config keys>
```

**Why it hurts:** the section exceeds the 400-token chunk target. The paragraph splitter (`markdown.py:148-196`) kicks in and produces ~4 chunks that all claim heading `## Configuration` but cover host, port, log level, and notifications separately. Retrieval returns "all about configuration" with no way to tell which topic.

**Fix:** split into `## Network binding — host and port`, `## Log level`, `## Desktop notifications`, etc. Each topic becomes one ≤250-word chunk.

## 3. Vague headings (`Overview`, `Notes`, `Details`, `Section 1`)

**What it looks like:**
```markdown
## Overview

<content about the chunking pipeline>

## Details

<more content about chunking>

## Notes

<caveats about chunking>
```

**Why it hurts:** the heading is prepended to every chunk's embedding (`markdown.py:255-258`). `## Overview` carries no keyword weight. A query like "how does chunking work?" has to match the content alone — the heading isn't helping.

**Fix:** `## The chunking pipeline`, `## Chunking edge cases`, `## Chunking limitations`. Each heading carries the keyword `chunking` so it contributes to the embedding.

## 4. Nested `####`/`#####` wrapping tiny 30-word sections

**What it looks like:**
```markdown
## Configuration

### Service

#### Host

The host is 127.0.0.1 by default.

#### Port

The port is 21420.
```

**Why it hurts:** the heading prefix fed to the embedding is `Configuration > Service > Host` — you're bloating the prefix with structural noise without improving the chunk's semantic content (a 5-word fact). Stop at `###` except for multi-step SOPs where each step is a real workflow unit.

**Fix:** flatten. `## Network binding` with `host` and `port` as paragraphs inside a single chunk.

## 5. Code-block walls (100+ lines with no surrounding prose)

**What it looks like:**
```markdown
## Installing

```bash
<100 lines of install commands with no prose between them>
```
```

**Why it hurts:** the splitter treats the fenced code block as a single paragraph. When it exceeds the 400-token chunk size, the sentence-splitter fallback fires and mangles the code — resulting chunks have no natural-language anchor and the code structure is lost.

**Fix:** break into labelled steps with `###` headings: `### Step 1 — install system packages`, `### Step 2 — create virtualenv`, each with its own short code block (≤ 60 lines) and a prose intro.

## 6. Giant single table (20+ rows)

**What it looks like:**
```markdown
## Config reference

| Key | Type | Description | Default |
|---|---|---|---|
| <40 rows of config keys>
```

**Why it hurts:** same as code-block walls — one paragraph to the splitter. When oversize, rows get stranded across chunk boundaries with no row-header disambiguation. A query for "what is config key X" might return a chunk that starts mid-row.

**Fix:** pre-chunk by category. `## Network config` (≤10 rows), `## Logging config` (≤10 rows), `## Indexing config` (≤10 rows). Each table fits in one chunk under a specific heading.

## 7. YAML frontmatter holding semantic info

**What it looks like:**
```yaml
---
title: Service configuration
tags: [service, config, networking, tls]
keywords: host, port, binding, listener
description: How to configure the RAG service's network settings
---

# Service configuration

<content>
```

**Why it hurts:** `extract_frontmatter` in `metadata.py:9-21` strips YAML frontmatter and throws it away. Tags, keywords, and descriptions are **invisible to search**. You've put the most semantic-dense content in a location the embedder will never see.

**Fix:** move knowledge into the body. Either embed it in the opening paragraph ("Service configuration covers host, port, TLS, and listener binding") or add a `## Tags` section near the end with the keyword list as prose or bullets.

## 8. Identical leaf headings across files

**What it looks like:**

File `service.md`:
```markdown
### Usage
```

File `watcher.md`:
```markdown
### Usage
```

File `indexer.md`:
```markdown
### Usage
```

**Why it hurts:** the MCP retrieval formatter shows each result as `<file>.md > <heading>` (`formatter.py:78-83`). When the LLM receives three chunks all labeled `service.md > Usage` / `watcher.md > Usage` / `indexer.md > Usage`, they're harder to distinguish. The dedup pass (`formatter.py:117-132`) may even collapse some.

**Fix:** scope the leaf heading. `### Service usage`, `### Watcher usage`, `### Indexer usage`. Or nest under a parent: `## Service` > `### Usage` — then the full hierarchy is `service.md > Service > Usage` which differentiates.

## 9. Pseudo-headings (bold text as section titles)

**What it looks like:**
```markdown
## Configuration

**Host**

The host binds to 127.0.0.1...

**Port**

Port defaults to 21420...
```

**Why it hurts:** `**Host**` and `**Port**` don't match `_HEADING_RE` in the chunker. They don't create section boundaries. The whole block becomes one chunk under `## Configuration`, and the pseudo-headings just pollute the embedded text without providing navigation.

**Fix:** use real headings. `### Host` and `### Port` as sub-sections. This is the single safe-fix category that `/md-rag-enhance` applies automatically — but if you're writing new content, write real headings from the start.

## Mixing languages mid-section (bonus)

MiniLM-L6-v2 is English-tuned. Non-English text inside an English section dilutes the embedding. If content needs to be bilingual, put languages in separate sections or separate files. Query behavior across mixed-language embeddings is unpredictable.

## See also

- `rag-md-guidelines.md` §5 — the canonical anti-pattern table
- `page-templates.md` — the positive patterns (what to do instead)
- `SKILL.md` Phase 5 — the pre-output checklist to run through before showing any Markdown to the user
