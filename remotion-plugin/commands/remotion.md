---
title: 'Remotion - Video Creator'
read_only: false
type: 'command'
description: 'Video creation toolkit — status, setup, render, and voice management'
argument-hint: '[setup|render|voices] [args...]'
---

# /remotion - Video Creator Toolkit

Unified entry point for the Remotion video creation plugin.

## Routing

Parse `$ARGUMENTS` and route to the appropriate section:

| Input | Route To |
|---|---|
| *(no arguments)* | **Section: Status + Help** |
| `setup` | **Section: Project Setup** |
| `render [compositionId] [format]` | **Section: Render Video** |
| `voices [language]` | **Section: Voice List** |

If the user provides a natural language description instead of a sub-command, infer intent:
- "set up a new project" / "create project" / "init" -> route to **setup**
- "render my video" / "export to mp4" / "make a gif" -> route to **render**
- "what voices are available" / "list voices" / "arabic voices" -> route to **voices**
- "what's the status" / "check my project" -> route to **Status + Help**

---

## Section: Status + Help

**Trigger**: `/remotion` with no arguments.

### 1. Detect Project

```bash
ls package.json remotion.config.ts src/Root.tsx 2>/dev/null
```

- If `package.json` contains `"remotion"` in dependencies -> **Inside a Remotion project**
- Otherwise -> **No project found**

### 2. Display Status

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

### 3. Show Sub-Commands

```
Sub-commands:
  /remotion setup           Set up a new Remotion project with voice pipeline
  /remotion render          Render a composition to MP4, WebM, or GIF
  /remotion voices          List available edge-tts voices by language

Examples (natural language works too):
  /remotion setup my-video
  /remotion render ContinuousAudioVideo mp4
  /remotion voices ar
  "render my video as a high-quality mp4"
  "list Arabic voices"
  "set up a new project called demo"
```

### 4. Key Reminder

Always mention:

```
Tip: This plugin uses the CONTINUOUS AUDIO pattern - voice narration
plays through all slide transitions without cutting. Audio is placed
at the root level, not inside individual Sequences.
```

### 5. Error Guidance

- Node.js missing: suggest `winget install OpenJS.NodeJS.LTS`
- edge-tts missing: suggest `pip install edge-tts`
- No project found: suggest `/remotion setup`

---

## Section: Project Setup

**Trigger**: `/remotion setup [project-name]`

Absorbs the full functionality of the former `/remotion-setup` command.

### Welcome Banner

```
Remotion Project Setup
======================
This will create a new Remotion project with:
  - React + TypeScript video framework
  - TailwindCSS styling
  - Free voice narration (edge-tts)
  - Continuous audio pipeline (no voice cutting!)
  - Ready-to-use composition templates
```

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
1. **Project name** (default: `my-video`, or use the argument if provided)
2. **Video dimensions** (default: `1920x1080`)
3. **Voice preference** (default: `en-US-AriaNeural`)

### Step 3: Create Remotion Project

```bash
npx create-video@latest [project-name]
```

During interactive setup, instruct the user to choose:
- Template: **Blank**
- TailwindCSS: **Yes**
- Install Skills: **Yes**

Non-interactive alternative:

```bash
npx create-video@latest [project-name] --template blank --tailwind --skills
cd [project-name]
npm install
```

### Step 4: Install Voice Dependencies

```bash
pip install edge-tts mutagen pydub
```

### Step 5: Create Project Structure

```bash
mkdir -p public/audio
mkdir -p public/images
mkdir -p src/compositions/scenes
mkdir -p scripts
```

### Step 6: Copy Templates

Copy composition templates from the plugin into the project:

1. `templates/composition_continuous_audio.tsx` -> `src/compositions/ContinuousAudioVideo.tsx`
2. `templates/composition_multi_scene.tsx` -> `src/compositions/MultiSceneVideo.tsx`
3. `templates/timeline_schema.ts` -> `src/lib/timeline.ts`
4. Update `src/Root.tsx` to import and register the compositions

**Important**: Adapt import paths to match the project structure.

### Step 7: Copy Scripts

Copy Python helper scripts into the project:

1. `scripts/generate_voice.py` -> `scripts/generate_voice.py`
2. `scripts/concat_audio.py` -> `scripts/concat_audio.py`
3. `scripts/measure_audio.py` -> `scripts/measure_audio.py`

### Step 8: Create Sample Timeline

Create `public/content/timeline.json`:

```json
{
  "title": "My First Video",
  "narrationFile": "audio/narration.mp3",
  "totalDurationMs": 15000,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "scenes": [
    {
      "id": "intro",
      "title": "Welcome",
      "text": "Your subtitle here",
      "startMs": 0,
      "endMs": 5000,
      "style": "title"
    },
    {
      "id": "content",
      "title": "Main Point",
      "points": ["First point", "Second point", "Third point"],
      "startMs": 5000,
      "endMs": 12000,
      "style": "content"
    },
    {
      "id": "outro",
      "title": "Thank You",
      "startMs": 12000,
      "endMs": 15000,
      "style": "outro"
    }
  ]
}
```

### Step 9: Display Next Steps

```
Project created successfully!

Next steps:
  1. cd [project-name]
  2. npm run dev           (Terminal 1 - opens Remotion Studio at localhost:3000)
  3. claude                (Terminal 2 - start prompting!)
  4. Describe your video and generate it

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

---

## Section: Render Video

**Trigger**: `/remotion render [compositionId] [format]`

Absorbs the full functionality of the former `/render-video` command.

### Step 1: Detect Compositions

Read `src/Root.tsx` and list all registered compositions:

```bash
grep -oP 'id="[^"]*"' src/Root.tsx
```

If `compositionId` was provided as an argument, use it directly. Otherwise display:

```
Available compositions:
  1. ContinuousAudioVideo (1920x1080, 30fps)
  2. MultiSceneVideo (1920x1080, 30fps)

Which composition do you want to render?
```

### Step 2: Choose Quality and Format

If `format` was provided as an argument, use it. Otherwise ask:

```
Quality Presets:
  1. draft     (CRF 28) - Fast, smaller file, good for preview
  2. balanced  (CRF 24) - Default, good quality/size ratio
  3. high      (CRF 18) - High quality, larger file (YouTube/presentations)
  4. max       (CRF 15) - Maximum quality, very large (archival)

Format Options:
  1. mp4       (H.264, most compatible)
  2. webm      (VP8, smaller for web)
  3. gif       (animated GIF, no audio)
```

### Step 3: Execute Render

```bash
# MP4 with quality preset
npx remotion render [CompositionId] out/[filename].mp4 --crf=[crf_value]

# WebM
npx remotion render [CompositionId] out/[filename].webm --codec=vp8 --crf=[crf_value]

# GIF (no audio)
npx remotion render [CompositionId] out/[filename].gif --codec=gif

# With specific output name
npx remotion render [CompositionId] "out/My Video - Final.mp4" --crf=18
```

### Step 4: Validate Audio (Post-Render)

```bash
python scripts/measure_audio.py public/audio/narration.mp3 --fps 30
```

Compare reported duration with the composition's `durationInFrames`.

### Step 5: Display Results

```
Render complete!

Output:     out/my-video.mp4
Size:       12.5 MB
Duration:   45.2 seconds
Quality:    High (CRF 18)
Resolution: 1920x1080
Format:     MP4 (H.264)

Audio validation: PASS (narration duration matches composition)

Open the file:
  start out/my-video.mp4     (Windows)
  open out/my-video.mp4      (macOS)
  xdg-open out/my-video.mp4  (Linux)
```

### Advanced Render Options

```bash
# Render specific frames (first 3 seconds at 30fps)
npx remotion render MyVideo --frames=0-90

# Render a thumbnail
npx remotion still MyVideo out/thumbnail.png --frame=0

# Transparent video (for overlays)
npx remotion render MyVideo --codec=prores --prores-profile=4444

# Image sequence (for compositing)
npx remotion render MyVideo --image-format=png --sequence
```

### Render Error Recovery

- "Composition not found": check ID matches exactly (case-sensitive)
- Render crashes: try `--gl=angle` on Windows, check memory (close other apps)
- Audio is silent: verify narration.mp3 exists in `public/audio/`
- Black frames: check component renders something for all frame ranges
- Very slow: use `--crf=28` for draft, reduce resolution, or limit frame range

---

## Section: Voice List

**Trigger**: `/remotion voices [language]`

List available edge-tts voices, optionally filtered by language code.

### List Voices

```bash
# List all voices
edge-tts --list-voices

# Filter by language (if argument provided)
edge-tts --list-voices | grep -i "[language]"
```

If a `[language]` argument is provided (e.g., `ar`, `en`, `fr`, `es`), filter results to that language.

Display results in a table:

```
Available Voices ([language or "all"]):

Name                          Gender    Language
----                          ------    --------
en-US-AriaNeural              Female    en-US
en-US-GuyNeural               Male      en-US
en-US-JennyNeural             Female    en-US
ar-EG-SalmaNeural             Female    ar-EG
ar-SA-HamedNeural             Male      ar-SA
...

Usage:
  python scripts/generate_voice.py --voice "en-US-AriaNeural" --text "Hello" --output public/audio/test.mp3
```

If edge-tts is not installed, show: `pip install edge-tts`

---

## Footer

> **Previously separate commands**: The functionality of `/remotion-setup`, `/render-video`,
> and voice listing has been consolidated into this single `/remotion` entry point.
> Use `/remotion setup`, `/remotion render`, and `/remotion voices` respectively.
