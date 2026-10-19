---
name: sprint-step-script
description: "Use when drafting or reviewing a sprint-recap steps.yaml, or when a sprint demo video and its written guide disagree. Explains the step-script schema: one caption written once and used for the video, the guide and the narration; a step as a unit of narration; and the start URL every step needs."
metadata:
  version: 0.2.0
  last_reviewed: 2026-10-19
  owns:
    - steps.yaml schema and validation rules
    - caption authoring (one caption, three consumers)
    - step granularity (narration unit, not single click)
    - the start-URL requirement that makes a step self-contained
    - show_login as the only way a step may involve credentials
  defers_to:
    - sprint-capture-clips (how a step is executed and recorded)
    - sprint-repro-guide (how a step renders as written instructions)
---

# The step script is the contract

`steps.yaml` is the single source of truth for three artifacts: the browser
walkthrough, the on-screen video text, and the HTML reproduction guide.

## Rule 1 — one caption, three consumers

Each step's `caption` is written once and read by the capture log, the Remotion
caption overlay, and the guide's numbered instruction. Never write step text
separately into the video and the guide. Two copies of the same sentence drift
the moment one is edited, and nobody notices until a stakeholder follows a guide
that contradicts the video they just watched.

## Rule 2 — a step is a unit of narration, not a click

One caption covers one thing a viewer should understand. "Search for London,
export to CSV, confirm the toast" is ONE step with four actions, not three steps.

Over-splitting produces a video that flashes a new caption every 1.5 seconds and
a guide with forty meaningless entries.

## Rule 3 — every step declares `start`

`start` is a URL. It is what makes the step's clip self-contained: the capture
stage opens a fresh page there, so the clip's boundaries are the step's
boundaries and its caption cannot drift onto the wrong footage.

A step that can only be reached by replaying earlier steps is a step that will
break the first time an earlier one changes. If a flow genuinely cannot start
from a URL, fold it into the previous step instead.

## Schema

```yaml
sprint: "Sprint 24"
iteration_path: "Project\Sprint 24"   # optional, for the Azure DevOps query
target: staging                        # key into .sprint-recap.local.json
intro:
  title: "Sprint 24 - what we shipped"
  subtitle: "Project name"
items:
  - work_item: 4512
    title: "Add customer export to the admin list"
    parent_pbi: 4500
    role: qa_admin                     # key into the target's roles map
    steps:
      - id: s1
        caption: "Export the filtered customers to CSV"
        start: "/admin/customers"
        hold_ms: 1500                  # dwell at the end so the eye can land
        actions:
          - { do: fill, selector: "input[name='search']", value: "London" }
          - { do: click, selector: "role=button[name='Export']" }
          - { do: expect, selector: "text=Export started" }
```

Actions: `goto`, `click`, `fill`, `select`, `press`, `hover`, `scroll`,
`expect`, `wait`. Selectors are Playwright syntax, so the guide can print the
literal thing to click.

## What does NOT belong in the script

- Work items with no UI surface. A refactor, a pipeline fix or a dependency bump
  has nothing to demonstrate. List it as covered-by-commits-only.
- Guessed selectors. If the evidence does not show one, ask rather than invent —
  a wrong selector costs a whole capture run to discover.
- Destructive actions. `allow_destructive: true` exists, but setting it is the
  user's decision, never yours.

## Validate before capturing

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/capture_steps.py" --steps steps.yaml --dry-run
```

Checks every step for a caption, a start URL, a unique id and known actions, and
reports which steps would be skipped as destructive — without launching a browser.
