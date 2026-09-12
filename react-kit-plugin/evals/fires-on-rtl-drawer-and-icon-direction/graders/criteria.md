---
type: llm
---
PASS if the reply says to use logical CSS properties/positioning (for example
inset-inline-end / inset-inline-start, margin-inline-start/end, or Tailwind
logical utilities like ms-/me-/start-/end-) instead of hardcoded left/right so
the drawer edge flips automatically with direction, AND it corrects the icon
mirroring the wrong way around: a directional icon such as the back-button
arrow SHOULD mirror in RTL while a non-directional icon such as the search
icon should NOT mirror.
FAIL if the reply only gives generic RTL/i18n advice (e.g. "use a CSS
framework with RTL support" or "test in both directions") without naming
logical CSS properties, or if it treats the icon mirroring the wrong way
around (e.g. says the search icon should mirror or the back arrow should
not), or if it suggests flex-direction: row-reverse to fix the layout.
