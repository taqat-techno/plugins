---
type: llm
---
PASS if the reply explains that once a lifespan is passed to FastAPI, the @app.on_event startup/shutdown handlers are no longer called, and the fix is to move the database setup (and its teardown after yield) into the lifespan context manager, since on_event is deprecated.
FAIL if the reply blames the database driver, the import order or app.state usage without naming that lifespan replaces and disables on_event handlers.
