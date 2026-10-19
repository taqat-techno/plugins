---
description: Check Remotion prerequisites and whether the current directory is a Remotion project
---

# /remotion:status

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_check.py"` and show its
   output. It installs nothing.
2. Check whether the current directory is a Remotion project: `package.json`
   lists `remotion`, and `src/Root.tsx` exists. If it is, list the composition
   ids registered in `src/Root.tsx` and whether `public/audio/narration.mp3`
   exists (measure it with
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/measure_audio.py" public/audio/narration.mp3`
   when it does).
3. Summarise in a few lines: what is ready, what is missing, and the next step
   (`/remotion:init <name>` when there is no project, otherwise describe the
   video to create or `/remotion:render`).
