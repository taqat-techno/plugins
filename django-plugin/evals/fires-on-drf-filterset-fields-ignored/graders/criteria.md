---
type: llm
---
PASS if the reply identifies that declaring filterset_fields / search_fields does nothing unless filter backends are enabled, and that DEFAULT_FILTER_BACKENDS is empty by default, so the fix is to set filter_backends on the view (DjangoFilterBackend, SearchFilter) or DEFAULT_FILTER_BACKENDS in REST_FRAMEWORK settings.
FAIL if the reply blames the query parameter spelling, the queryset, URL routing or caching without naming the missing filter backend configuration, or tells the user to filter manually in get_queryset as the main fix.
