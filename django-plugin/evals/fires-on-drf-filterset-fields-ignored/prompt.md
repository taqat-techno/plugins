---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My DRF ModelViewSet declares filterset_fields = ['status'] and search_fields = ['name'], and django-filter is installed and in INSTALLED_APPS. But GET /api/orders/?status=paid still returns every order, and ?search= does nothing either. No error anywhere. What am I missing?
