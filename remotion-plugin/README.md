# Remotion Video Creator - Claude Code Plugin v2.2.2

Create professional videos with smooth voice narration using [Remotion](https://remotion.dev) and Claude Code. Describe your video in plain English, get a rendered MP4 with free voice narration.

## Key Feature: No Audio Cutting

The #1 problem with video narration in Remotion is **voice cutting between slides**. This plugin solves it with the **Continuous Audio Pattern** — a single audio track at the root level that plays through all visual transitions.

## Quick Start

```bash
# 1. Set up a new Remotion project
/remotion my-video

# 2. Start Remotion Studio
cd my-video && npm run dev

# 3. Describe your video in natural language
"Create a 60-second product demo with voice narration about our new feature"

# 4. Render final video
"Render my video as a high-quality MP4"
```

## Command

| Command | Description |
|---------|-------------|
| `/remotion` | Check project status and prerequisites |
| `/remotion [name]` | Start a new Remotion project with the given name. There is no scripted init step yet: Claude scaffolds it following the skill's guidance |

All other workflows (rendering, voice generation, video creation) are handled through natural language — no slash commands needed.

### Natural Language Workflows

- **"Create a 5-scene explainer video about our API with voice-over"** — full pipeline from prompt to video
- **"Add professional voice narration to my existing composition"** — voice integration
- **"Render my video as MP4 in high quality"** — render with quality presets
- **"List available Arabic voices"** — browse edge-tts voices

## How It Works

### The Problem

Placing `<Audio>` inside `<Sequence>` components causes voice to **stop** at each slide boundary:

```typescript
// WRONG - voice cuts between slides
<Sequence from={0} durationInFrames={90}>
  <Audio src="slide1.mp3" />  // Stops at frame 90!
</Sequence>
```

### The Solution

One continuous audio track at the root level:

```typescript
// CORRECT - voice plays through all transitions
<AbsoluteFill>
  <Audio src="narration.mp3" />  // Never stops!
  <Sequence from={0} durationInFrames={90}><Slide1 /></Sequence>
  <Sequence from={90} durationInFrames={120}><Slide2 /></Sequence>
</AbsoluteFill>
```

### Voice Pipeline

```
1. Write narration script per scene
2. Generate MP3s with edge-tts (free, 300+ voices)
3. Concatenate into ONE continuous track
4. Use segment timestamps for visual Sequence timing
5. Render with continuous audio
```

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 18+ | `winget install OpenJS.NodeJS.LTS` |
| Python | 3.8+ | Pre-installed on most systems |
| edge-tts | latest | `pip install edge-tts` |
| mutagen | latest | `pip install mutagen` |

## Plugin Structure

```
remotion-plugin/
├── skills/remotion/SKILL.md   # remotion-video skill (triggers on video/voice/render requests)
├── commands/remotion.md       # /remotion command
├── hooks/hooks.json           # Empty: no hooks are registered
├── scripts/                   # Python tools for the voice pipeline, run in place
│   │                          #   as python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"
│   ├── setup_check.py         # Check all prerequisites
│   ├── generate_voice.py      # Generate MP3 from text (edge-tts)
│   ├── concat_audio.py        # Merge MP3s into continuous track
│   ├── measure_audio.py       # Validate audio duration vs frames
│   └── _common.py             # Shared utilities
├── templates/                 # TSX composition templates (reference only; not copied automatically)
├── memories/                  # Reference files for patterns and troubleshooting
├── tests/test_paths.py        # Offline check: referenced plugin paths exist
├── CHANGELOG.md
└── README.md
```

## Extending the Plugin

- **Templates**: Modify TSX files in `templates/` to change default compositions
- **Scripts**: All scripts accept CLI args (`--fps`, `--voice`, `--gap`, `--method`)
- **Memories**: Add `.md` files to `memories/` for project-specific patterns
- **Scene renderers**: Extend the `SCENE_RENDERERS` map in `composition_multi_scene.tsx`

## License

MIT — Free to use, modify, and distribute.

## Author

**TAQAT Techno** — info@taqatechno.com
