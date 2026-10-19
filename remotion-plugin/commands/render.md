---
description: Render a composition of the current Remotion project to MP4, WebM or GIF
argument-hint: '[CompositionId] [--format mp4|webm|gif] [--quality draft|balanced|high|max]'
---

# /remotion:render

Use the `remotion-video` skill's Rendering workflow with `$ARGUMENTS`. With no
arguments, list the compositions in `src/Root.tsx` and ask which one to render
and at which quality (default: balanced MP4 to `out/<CompositionId>.mp4`).

If the output file already exists, ask before overwriting it.
