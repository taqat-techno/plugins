---
title: 'Remotion - Video Creator'
read_only: true
type: 'command'
description: 'Main entry point for the Remotion video creation plugin. Shows status, available commands, and quick start guide.'
---

# /remotion - Video Creator Hub

Welcome to the Remotion Video Creator plugin! Create professional videos with smooth voice narration using Claude Code.

## On Activation

When this command is invoked, perform these checks and display results:

### 1. Check Current Directory

Determine if the user is inside a Remotion project:

```bash
# Check for Remotion project markers
ls package.json remotion.config.ts src/Root.tsx 2>/dev/null
```

- If `package.json` contains `"remotion"` in dependencies -> **Inside a Remotion project**
- If not -> **Not in a Remotion project** (suggest `/remotion-setup`)

### 2. Display Status

Show a status summary:

```
Remotion Video Creator v1.0.0
==============================

Project Status: [Inside Remotion Project / No Project Found]
Directory:      [current directory]
Node.js:        [version or "not found"]
Python:         [version or "not found"]
edge-tts:       [installed / not installed]
Audio Files:    [count in public/audio/ or "none"]
Compositions:   [list from Root.tsx or "none"]
```

### 3. Show Available Commands

```
Available Commands:
  /remotion-setup   Set up a new Remotion project with voice pipeline
  /create-video     Create a video from a text prompt with voice narration
  /render-video     Render a composition with quality presets
  /add-voice        Add voice narration to an existing composition

Quick Start:
  1. /remotion-setup              Create a new project
  2. /create-video                Describe your video and generate it
  3. npm run dev                  Preview in Remotion Studio
  4. /render-video                Render final video
```

### 4. Key Reminder

Always mention the continuous audio pattern:

```
Tip: This plugin uses the CONTINUOUS AUDIO pattern - voice narration
plays through all slide transitions without cutting. Your audio is
placed at the root level, not inside individual Sequences.
```

## Error Handling

- If Node.js is not installed: suggest `winget install OpenJS.NodeJS.LTS`
- If edge-tts is not installed: suggest `pip install edge-tts`
- If not in a Remotion project: suggest running `/remotion-setup`
