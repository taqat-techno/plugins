---
title: 'Remotion Setup'
read_only: false
type: 'command'
description: 'Set up a new Remotion video project with voice narration pipeline, TailwindCSS, and all dependencies.'
---

# /remotion-setup - Project Setup

Set up a complete Remotion video project with voice narration pipeline.

## On Activation

Display a welcome message:

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

## Setup Steps

### Step 1: Check Prerequisites

Run the setup checker script. Look for it relative to the skill location or use inline checks:

```bash
# Check Node.js
node --version  # Need >= 18.0.0

# Check Python
python --version  # Need >= 3.8

# Check/install Python packages
pip install edge-tts mutagen pydub
```

If Node.js is not installed or < 18, STOP and provide install instructions:
- Windows: `winget install OpenJS.NodeJS.LTS`
- macOS: `brew install node@20`
- Linux: `sudo apt install nodejs`

### Step 2: Ask for Project Details

Ask the user for:
1. **Project name** (default: `my-video`)
2. **Video dimensions** (default: `1920x1080`)
3. **Voice preference** (default: `en-US-AriaNeural`)

### Step 3: Create Remotion Project

```bash
npx create-video@latest [project-name]
```

During the interactive setup, instruct the user to choose:
- Template: **Blank**
- TailwindCSS: **Yes**
- Install Skills: **Yes**

If the user wants non-interactive setup:

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

Create the following directories and files in the new project:

```bash
mkdir -p public/audio
mkdir -p public/images
mkdir -p src/compositions/scenes
mkdir -p scripts
```

### Step 6: Copy Templates

Copy the composition templates from the plugin into the project:

1. Copy `templates/composition_continuous_audio.tsx` -> `src/compositions/ContinuousAudioVideo.tsx`
2. Copy `templates/composition_multi_scene.tsx` -> `src/compositions/MultiSceneVideo.tsx`
3. Copy `templates/timeline_schema.ts` -> `src/lib/timeline.ts`
4. Update `src/Root.tsx` to import and register the compositions

**Important**: When copying templates, adapt the import paths to match the project structure.

### Step 7: Copy Scripts

Copy the Python helper scripts into the project:

1. Copy `scripts/generate_voice.py` -> `scripts/generate_voice.py`
2. Copy `scripts/concat_audio.py` -> `scripts/concat_audio.py`
3. Copy `scripts/measure_audio.py` -> `scripts/measure_audio.py`

### Step 8: Create Sample Timeline

Create a sample `public/content/timeline.json`:

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
  4. /create-video         (describe your video and generate it)

Voice narration:
  python scripts/generate_voice.py --text "Hello world" --output public/audio/test.mp3
  python scripts/generate_voice.py --list-voices --language en

Your project uses the CONTINUOUS AUDIO pattern:
  - Voice narration never cuts between slides
  - Audio is placed at the root level, not inside Sequences
  - Run concat_audio.py to merge per-scene audio into one track
```

## Error Recovery

- If `npx create-video` fails: check Node.js version, try `npm cache clean --force`
- If `pip install` fails: try `python -m pip install --user edge-tts mutagen pydub`
- If port 3000 in use: `npx kill-port 3000` or use a different port `npm run dev -- --port 3001`
