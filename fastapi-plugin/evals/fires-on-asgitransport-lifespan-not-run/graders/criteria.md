---
type: llm
---
PASS if the reply explains that ASGITransport does not run the ASGI lifespan, so startup never executes in the tests, and fixes it by wrapping the app in asgi_lifespan.LifespanManager (passing manager.app to the transport) or by using TestClient as a context manager.
FAIL if the reply blames the test database, pytest-asyncio configuration or app.state misuse without naming that the transport skips lifespan startup.
