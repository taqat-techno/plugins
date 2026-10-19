---
type: llm
---
PASS if the reply explains that beforeunload does not cover in-app Back navigation and guards it with a
history sentinel and a popstate handler (or the router's navigation-blocking API), deriving the
dirty flag from the form's own change state rather than DOM events.
FAIL if the reply only tweaks the beforeunload handler, or suggests autosave alone, without guarding Back
navigation.
