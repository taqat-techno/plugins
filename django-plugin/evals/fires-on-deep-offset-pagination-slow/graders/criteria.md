---
type: llm
---
PASS if the reply explains that OFFSET pagination makes the database scan and discard every skipped row (cost grows with depth) and that COUNT(*) over the whole table is itself expensive, and recommends keyset / cursor pagination on an indexed ordering column (for example DRF CursorPagination or filtering created_at < last_seen) and avoiding or approximating the total count.
FAIL if the reply only suggests adding caching, a bigger server, or select_related, without identifying the offset-scan cost and proposing keyset/cursor pagination.
