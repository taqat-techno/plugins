# Remotion Video Creator - Claude Code Plugin

Create professional videos with smooth voice narration using [Remotion](https://remotion.dev) and Claude Code. Describe your video in plain English, get a rendered MP4 with free voice narration.

## Key Feature: No Audio Cutting

The #1 problem with video narration in Remotion is **voice cutting between slides**. This plugin solves it with the **Continuous Audio Pattern** - a single audio track at the root level that plays through all visual transitions.

## Quick Start

```bash
# 1. Set up a new project
/remotion-setup

# 2. Create a video with voice narration
/create-video

# 3. Preview in browser
npm run dev

# 4. Render final video
/render-video
```

## Commands

| Command | Description |
|---------|-------------|
| `/remotion` | Status, help, and quick start guide |
| `/remotion-setup` | Create a new Remotion project with all dependencies |
| `/create-video` | Full pipeline: text prompt to video with voice narration |
| `/render-video` | Render composition to MP4/WebM/GIF with quality presets |
| `/add-voice` | Add voice narration to an existing composition |

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 18+ | `winget install OpenJS.NodeJS.LTS` |
| Python | 3.8+ | Pre-installed on most systems |
| edge-tts | latest | `pip install edge-tts` |
| mutagen | latest | `pip install mutagen` |

## How It Works

### The Problem

Placing `<Audio>` inside `<Sequence>` components causes voice to **stop** at each slide boundary:

```typescript
// WRONG - voice cuts between slides
<Sequence from={0} durationInFrames={90}>
  <Audio src="slide1.mp3" />  // Stops at frame 90!
</Sequence>
<Sequence from={90} durationInFrames={120}>
  <Audio src="slide2.mp3" />  // Starts cold
</Sequence>
```

### The Solution

One continuous audio track at the root level:

```typescript
// CORRECT - voice plays through all transitions
<AbsoluteFill>
  <Audio src="narration.mp3" />  // Never stops!

  <Sequence from={0} durationInFrames={90}>
    <Slide1 />  // Visual only
  </Sequence>
  <Sequence from={90} durationInFrames={120}>
    <Slide2 />  // Visual only
  </Sequence>
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

## Voice Options

### Free (edge-tts)
300+ Microsoft Neural voices across 70+ languages. No API key needed.

Popular voices:
- `en-US-AriaNeural` (Female, American)
- `en-US-GuyNeural` (Male, American)
- `en-GB-RyanNeural` (Male, British)
- `ar-SA-HamedNeural` (Male, Arabic)

### Premium (ElevenLabs)
Ultra-realistic voices with character-level timestamps. Requires API key.

## Installation

### Via Marketplace (Recommended)

If you already have the TaqaTechno plugins marketplace installed, the Remotion plugin is automatically available.

### Manual Installation

```bash
# Windows
cd %USERPROFILE%\.claude\plugins\marketplaces\taqat-techno-plugins
git pull  # Get latest updates

# Linux/macOS
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

## Helper Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_check.py` | Check all prerequisites |
| `scripts/generate_voice.py` | Generate MP3 from text (edge-tts) |
| `scripts/concat_audio.py` | Merge MP3s into continuous track |
| `scripts/measure_audio.py` | Validate audio duration vs frames |

## License

MIT - Free to use, modify, and distribute.

## Author

**TAQAT Techno** - info@taqatechno.com
