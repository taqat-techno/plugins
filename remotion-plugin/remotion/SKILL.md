---
name: remotion
description: |
  Create professional videos with smooth voice narration using Remotion and Claude Code. Complete video creation pipeline: describe scenes in natural language, generate free edge-tts narration (300+ voices), build React compositions with continuous audio that never cuts between slides, and render production-quality MP4/WebM/GIF output.

  <example>
  Context: User wants to create a video with narration
  user: "Create a product demo video with voice narration explaining our features"
  assistant: "I will use the remotion skill to scaffold a Remotion composition, generate edge-tts voice narration for each scene, and produce a continuous audio pipeline without voice cutting."
  <commentary>Core trigger - video creation from text prompts with AI narration.</commentary>
  </example>

  <example>
  Context: User wants to render the final video
  user: "Render my Remotion video in 1080p as an MP4 file"
  assistant: "I will use the remotion skill to detect compositions, select quality preset, and run the Remotion render command."
  <commentary>Rendering trigger - final video export.</commentary>
  </example>

  <example>
  Context: User wants to add voice to an existing composition
  user: "Add professional voice narration to my existing Remotion video"
  assistant: "I will use the remotion skill to generate edge-tts audio tracks, concatenate them into a continuous track, and integrate at the root level."
  <commentary>Audio integration trigger - adding voice to existing video.</commentary>
  </example>
metadata:
  mode: "cli-tool"
  supported-platforms: ["windows", "macos", "linux"]
  node-min-version: "18.0.0"
  remotion-version: "4.0.0+"
  voice-engines: ["edge-tts", "elevenlabs"]
  output-formats: ["mp4", "webm", "gif", "png-sequence"]
  model: sonnet
---
<!-- Last updated: 2026-03-26 -->

# Remotion Video Creator

Create professional videos with voice narration using Remotion and Claude Code.

## When to Use This Skill

- **Create videos from text prompts** - Describe scenes and get a full video
- **Add voice narration** - Free text-to-speech with 300+ voices via edge-tts
- **Build animated presentations** - Multi-scene videos with smooth transitions
- **Render video content** - MP4, WebM, GIF from React components
- **Fix audio cutting issues** - Continuous audio pipeline prevents voice gaps

## Command

| Command | Description |
|---------|-------------|
| `/remotion` | Initialize a new Remotion project with all dependencies |

All other workflows (rendering, voice generation, video creation) are handled via natural language.

---

## Prerequisites

| Tool | Min Version | Install |
|------|-------------|---------|
| Node.js | 18.0.0 | `winget install OpenJS.NodeJS.LTS` |
| Python | 3.8.0 | Pre-installed on most systems |
| edge-tts | latest | `pip install edge-tts` |
| mutagen | latest | `pip install mutagen` |

Run `python scripts/setup_check.py` from the plugin directory to verify.

---

## Project Structure

```
my-video/
├── public/
│   ├── audio/              # Voice narration MP3 files
│   │   └── narration.mp3   # Single continuous narration track
│   ├── images/             # Background images, logos
│   └── content/
│       └── timeline.json   # Scene timing data
├── src/
│   ├── Root.tsx            # Composition registration
│   ├── compositions/       # Video compositions
│   │   └── scenes/         # Individual scene components
│   └── lib/
│       ├── types.ts        # Zod schemas
│       └── constants.ts    # FPS, durations, colors
├── scripts/                # Voice generation tools (copied from plugin)
├── remotion.config.ts
└── package.json
```

---

## The Continuous Audio Pattern (CRITICAL)

### The Problem

When each slide has its own `<Audio>` inside a `<Sequence>`, audio **stops** when the Sequence ends. This creates jarring cuts in voice narration.

### WRONG - Audio Cuts

```typescript
// BAD - Audio cuts at every slide transition!
<Sequence from={0} durationInFrames={90}>
  <Audio src={staticFile("audio/slide1.mp3")} />  {/* STOPS at frame 90 */}
</Sequence>
```

### CORRECT - Continuous Audio

```typescript
// GOOD - Audio plays continuously through all transitions
<AbsoluteFill>
  <Audio src={staticFile("audio/narration.mp3")} />  {/* ROOT level - never cuts */}

  <Sequence from={0} durationInFrames={scene1Frames}>
    <IntroScene />
  </Sequence>
  <Sequence from={scene1Frames} durationInFrames={scene2Frames}>
    <ContentScene />
  </Sequence>
</AbsoluteFill>
```

### The Pipeline

1. Write narration text for each scene
2. Generate per-scene MP3 files with edge-tts (`python scripts/generate_voice.py`)
3. Concatenate all MP3s into ONE continuous track (`python scripts/concat_audio.py`)
4. Use segment timestamps from concat output for visual `<Sequence>` timing
5. Place single `<Audio>` at root — never inside `<Sequence>`
6. Validate with `python scripts/measure_audio.py`

### Frame Calculation Formula

```typescript
// ALWAYS use Math.ceil - never truncate audio timing
const FPS = 30;
const PADDING_FRAMES = Math.ceil(1.0 * FPS); // 1 second padding

const durationFrames = Math.ceil(audioDurationMs * FPS / 1000) + PADDING_FRAMES;
const startFrame = Math.ceil(timestampMs * FPS / 1000);
```

---

## Voice Generation Workflow

When the user asks to add voice narration or create a video with voice:

```bash
# Generate per-scene audio
python scripts/generate_voice.py --text "Scene text..." --voice "en-US-AriaNeural" --output public/audio/scene01.mp3 --fps 30

# Concatenate into continuous track
python scripts/concat_audio.py --files public/audio/scene01.mp3 public/audio/scene02.mp3 --output public/audio/narration.mp3 --gap 200 --fps 30

# Measure and validate
python scripts/measure_audio.py public/audio/narration.mp3 --fps 30
```

The concat script outputs JSON with segment boundaries — use these for `<Sequence>` timing.

Default voice: `en-US-AriaNeural`. Run `edge-tts --list-voices` to see all 300+ options.

---

## Rendering Workflow

When the user asks to render a video:

1. Detect compositions from `src/Root.tsx`
2. Ask user for quality preset and format if not specified

```bash
# Quality presets
npx remotion render [CompositionId] --crf=15    # Max quality
npx remotion render [CompositionId] --crf=18    # High quality
npx remotion render [CompositionId] --crf=24    # Balanced (default)
npx remotion render [CompositionId] --crf=28    # Draft (fast)

# Format options
npx remotion render [CompositionId] out/video.mp4               # MP4 (default)
npx remotion render [CompositionId] out/video.webm --codec=vp8  # WebM
npx remotion render [CompositionId] out/video.gif --codec=gif    # GIF

# Thumbnail
npx remotion still [CompositionId] out/thumb.png --frame=0
```

---

## Key Rules

1. **ONE `<Audio>` at root level** — never inside `<Sequence>`. This is the #1 rule.
2. **Always use `Math.ceil()`** for ms-to-frame conversions — never truncate.
3. **Always add 1 second padding** to total composition duration after audio ends.
4. **Validate audio duration** with measure_audio.py before final render.
5. **Use `staticFile()`** for all assets in `public/` — never hardcode paths.

---

## Quick Start

```bash
# 1. Set up project
/remotion my-video

# 2. Start Remotion Studio
cd my-video && npm run dev

# 3. Describe your video in natural language
"Create a 5-scene presentation about [TOPIC] with voice narration"
```
