---
type: llm
---
PASS if the reply says an empty retrieval result is never evidence of absence, and specifically says the project's indexing mode must be checked first -- most projects index in "docs" mode (documentation/Markdown only, no source code indexed), so an empty result for a code lookup there is the expected outcome, not proof the symbol is missing -- and recommends checking the mode (or otherwise confirming via Grep/reading the source) before telling anyone the function does not exist.
FAIL if the reply just says "try a different search query" or "maybe reindex" or agrees the function might not exist without naming the docs/code/general indexing-mode distinction and the empty-is-not-absence rule.
