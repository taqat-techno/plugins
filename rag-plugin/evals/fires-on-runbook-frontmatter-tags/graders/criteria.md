---
type: llm
---
PASS if the reply says that YAML frontmatter (tags/keywords/description fields) is thrown away by the chunker's frontmatter extraction and is invisible to search, so any tags or keywords meant to be searchable must go in a heading section in the body instead (for example a "## Tags" section) -- and also says headings should be specific and keyword-rich rather than vague ("Overview", "Notes") because heading text is prepended to every chunk's embedding.
FAIL if the reply gives only generic Markdown advice (use clear headings, keep it organized, use frontmatter for metadata) without stating that frontmatter content is discarded by the chunker/indexer, or without explaining that heading text is prepended into the embedded chunk.
