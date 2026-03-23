---
title: 'Remotion - Project Setup'
read_only: false
type: 'command'
description: 'Initialize a Remotion video project with voice pipeline and all dependencies'
argument-hint: '[project-name]'
---

# /remotion - Project Initialization

Set up a new Remotion video project with the continuous audio pipeline.

## Routing

Parse `$ARGUMENTS`:

| Input | Route To |
|---|---|
| *(no arguments)* | **Section: Status Check** |
| `[project-name]` | **Section: Project Setup** with the given name |

---

## Section: Status Check

**Trigger**: `/remotion` with no arguments.

### 1. Detect Project

```bash
ls package.json remotion.config.ts src/Root.tsx 2>/dev/null
```

- If `package.json` contains `"remotion"` in dependencies -> **Inside a Remotion project**
- Otherwise -> **No project found**

### 2. Display Status

```
Remotion Video Creator v2.1.0
==============================

Project Status: [Inside Remotion Project / No Project Found]
Directory:      [current directory]
Node.js:        [version or "not found"]
Python:         [version or "not found"]
edge-tts:       [installed / not installed]
Audio Files:    [count in public/audio/ or "none"]
Compositions:   [list from Root.tsx or "none"]

Next steps:
  /remotion my-video        Set up a new project
  "create a video about X"  Start creating (inside a project)
  "render my video"         Render to MP4/WebM/GIF

Tip: This plugin uses the CONTINUOUS AUDIO pattern — voice narration
plays through all slide transitions without cutting.
```

### 3. Error Guidance

- Node.js missing: suggest `winget install OpenJS.NodeJS.LTS`
- edge-tts missing: suggest `pip install edge-tts`
- No project found: suggest `/remotion my-video`

---

## Section: Project Setup

**Trigger**: `/remotion [project-name]`

### Step 1: Check Prerequisites

```bash
node --version   # Need >= 18.0.0
python --version # Need >= 3.8
pip install edge-tts mutagen pydub
```

If Node.js is missing or < 18, STOP and provide install instructions:
- Windows: `winget install OpenJS.NodeJS.LTS`
- macOS: `brew install node@20`
- Linux: `sudo apt install nodejs`

### Step 2: Ask for Project Details

Ask the user for:
1. **Video dimensions** (default: `1920x1080`)
2. **Voice preference** (default: `en-US-AriaNeural`)

### Step 3: Create Remotion Project

```bash
npx create-video@latest [project-name]
cd [project-name]
npm install
```

During interactive setup, choose: Blank template, Yes TailwindCSS, Yes Skills.

### Step 4: Install Voice Dependencies

```bash
pip install edge-tts mutagen pydub
```

### Step 5: Create Project Structure

```bash
mkdir -p public/audio
mkdir -p public/images
mkdir -p public/content
mkdir -p src/compositions/scenes
mkdir -p scripts
```

### Step 6: Copy Templates

Copy composition templates from the plugin's `templates/` directory into the project:

1. `templates/composition_continuous_audio.tsx` -> `src/compositions/ContinuousAudioVideo.tsx`
2. `templates/composition_multi_scene.tsx` -> `src/compositions/MultiSceneVideo.tsx`
3. `templates/timeline_schema.ts` -> `src/lib/timeline.ts`
4. Update `src/Root.tsx` to import and register the compositions

Adapt import paths to match the project structure.

### Step 7: Copy Scripts

Copy Python helper scripts from the plugin's `scripts/` directory:

1. `scripts/generate_voice.py` -> `scripts/generate_voice.py`
2. `scripts/concat_audio.py` -> `scripts/concat_audio.py`
3. `scripts/measure_audio.py` -> `scripts/measure_audio.py`
4. `scripts/_common.py` -> `scripts/_common.py`

### Step 8: Display Next Steps

```
Project created successfully!

Next steps:
  1. cd [project-name]
  2. npm run dev           (opens Remotion Studio at localhost:3000)
  3. Describe your video and start creating!

Voice narration:
  python scripts/generate_voice.py --text "Hello world" --output public/audio/test.mp3
  python scripts/generate_voice.py --list-voices --language en

Your project uses the CONTINUOUS AUDIO pattern:
  - Voice narration never cuts between slides
  - Audio is placed at the root level, not inside Sequences
  - Run concat_audio.py to merge per-scene audio into one track
```

### Setup Error Recovery

- `npx create-video` fails: check Node.js version, try `npm cache clean --force`
- `pip install` fails: try `python -m pip install --user edge-tts mutagen pydub`
- Port 3000 in use: `npx kill-port 3000` or `npm run dev -- --port 3001`
