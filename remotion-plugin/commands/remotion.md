---
title: 'Remotion - Video Creation'
read_only: false
type: 'command'
description: 'Video creation toolkit - status, setup, render, and voice management'
argument-hint: '[project-name] | render [opts] | voice [opts]'
---

# /remotion - Video Creation Toolkit

Parse `$ARGUMENTS`:

| Input | Action |
|-------|--------|
| *(no args)* | Status check - detect project, show capabilities |
| `[project-name]` | Set up new Remotion project with given name |
| `render [opts]` | Render video (--format mp4/webm/gif, --resolution 1080p) |
| `voice [opts]` | Manage voice narration (--list, --preview, --generate) |

Use the remotion skill for:
- Project scaffolding (React + Remotion + edge-tts)
- Continuous audio pipeline (no voice cutting between slides)
- Scene breakdown from natural language descriptions
- Voice generation with 300+ edge-tts voices
- Audio synchronization and timing
- Render configuration (codec, resolution, quality)

Key patterns:
- Always use continuous audio pipeline (single Audio component, offset-based timing)
- Never split voice per slide (causes cutting artifacts)
- Use edge-tts for free, high-quality narration
