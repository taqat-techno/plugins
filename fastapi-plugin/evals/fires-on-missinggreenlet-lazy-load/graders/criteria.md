---
type: llm
---
PASS if the reply explains that accessing an unloaded relationship triggers an implicit lazy load, which is synchronous I/O that AsyncSession cannot perform, and fixes it by eager loading in the query (selectinload or joinedload for Order.customer), optionally noting expire_on_commit=False so attributes are not expired after commit.
FAIL if the reply suggests wrapping the call in asyncio.run, switching back to a sync session as the fix, or installing greenlet, without identifying the implicit lazy load and eager loading.
