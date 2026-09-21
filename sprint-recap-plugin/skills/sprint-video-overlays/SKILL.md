---
name: sprint-video-overlays
description: Conventions for the Remotion layer that draws step text over captured footage. Owns the scene model (title, item card, step, outro), caption composition, RTL handling for Arabic captions, and the sequencing rule that a caption lasts exactly as long as its clip. Use when editing the generated Remotion project or changing how step text appears on screen.
version: 0.1.0
last_reviewed: 2026-09-21
owns:
  - scene model and timeline assembly
  - caption overlay composition and legibility
  - RTL caption handling
defers_to:
  - sprint-capture-clips (where clips and durations come from)
  - sprint-step-script (where caption text comes from)
---

# The overlay layer

`build_remotion.py` writes `src/data.json`; the composition renders it. The
project is regenerated on every build — **edit the step script, not the
generated project**, or your changes vanish on the next run.

## Scene model

| Scene | Purpose | Length |
|---|---|---|
| `title` | sprint name and environment | 3s |
| `item` | work item ID, title, parent PBI, role | 2s |
| `step` | the captured clip with its caption | measured clip length + 0.35s pad |
| `outro` | pointer to the HTML guide | 2.5s |

Sequences are laid out by accumulating `durationInFrames`, so the timeline is
contiguous by construction and the composition's total always equals the sum of
its scenes.

## Caption rules

- The caption text comes from the step script. Never hand-edit it in the
  composition — the guide would then disagree with the video.
- A caption is on screen for exactly its clip's duration. It does not outlive
  its footage.
- The badge row carries work item, step counter and role, so a viewer who joins
  mid-video knows what they are looking at.
- Keep captions legible over arbitrary UI: dark translucent panel, light text,
  generous padding. The underlying app may be any colour.

## RTL

Captions containing Arabic characters are rendered with `dir="rtl"` and the badge
row reversed. Do not assume left-to-right layout — these videos are produced for
projects with Arabic interfaces, and a mirrored caption over a mirrored app is
the correct result.

## Narration

`--narrate` generates edge-tts audio from the same caption text. Narration is
optional and degrades to silence when edge-tts is absent; the build says so
rather than failing.
