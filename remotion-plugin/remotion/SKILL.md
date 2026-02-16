---
name: remotion
description: "Create professional videos with smooth voice narration using Remotion and Claude Code. Complete video creation pipeline from text prompts to rendered MP4 with free edge-tts voice generation and continuous audio that never cuts between slides."
version: "1.0.0"
author: "TaqaTechno"
license: "MIT"
category: "video-creation"
tags:
  - remotion
  - video
  - voice-narration
  - edge-tts
  - animation
  - react
  - typescript
  - presentation
  - motion-graphics
  - text-to-speech
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
metadata:
  mode: "cli-tool"
  supported-platforms: ["windows", "macos", "linux"]
  node-min-version: "18.0.0"
  remotion-version: "4.0.0+"
  voice-engines: ["edge-tts", "elevenlabs"]
  output-formats: ["mp4", "webm", "gif", "png-sequence"]
---

# Remotion Video Creator - Claude Code Skill

Create professional videos with smooth voice narration using Remotion (React-based video framework) and Claude Code. This skill provides the complete pipeline: describe a video in natural language, generate voice narration for free, and render production-quality video.

## When to Use This Skill

Activate when you need to:

- **Create videos from text prompts** - Describe scenes and get a full video
- **Add voice narration** - Free text-to-speech with 300+ voices via edge-tts
- **Build animated presentations** - Multi-scene videos with smooth transitions
- **Render video content** - MP4, WebM, GIF from React components
- **Fix audio cutting issues** - Continuous audio pipeline prevents voice gaps between slides

---

## Available Commands

| Command | Description |
|---------|-------------|
| `/remotion` | Main entry - status, help, quick start |
| `/remotion-setup` | Set up a new Remotion project with all dependencies |
| `/create-video` | Full pipeline: prompt to video with voice narration |
| `/render-video` | Render composition with quality presets |
| `/add-voice` | Add voice narration to an existing composition |

---

## Prerequisites

### Required

| Tool | Min Version | Install Command | Purpose |
|------|-------------|-----------------|---------|
| **Node.js** | 18.0.0 | `winget install OpenJS.NodeJS.LTS` | Remotion runtime |
| **Python** | 3.8.0 | Pre-installed on most systems | Voice generation scripts |
| **edge-tts** | latest | `pip install edge-tts` | Free Microsoft Neural TTS |
| **mutagen** | latest | `pip install mutagen` | Audio duration measurement |

### Optional

| Tool | Install Command | Purpose |
|------|-----------------|---------|
| **pydub** | `pip install pydub` | Audio concatenation (alternative to ffmpeg CLI) |
| **FFmpeg** | `winget install Gyan.FFmpeg` | Advanced audio/video processing |
| **ElevenLabs** | `npm install @elevenlabs/elevenlabs-js` | Premium realistic voices |

### Prerequisite Check Script

Run the included setup checker before starting:

```bash
python remotion/scripts/setup_check.py
```

This reports missing dependencies with exact install commands for your platform.

---

## Architecture Overview

### How Remotion Works

Remotion treats **video as a function of images over time**:

```
Frame Number -> React Component -> Image -> Video
```

1. You write React/TypeScript components
2. Each component receives a frame number via `useCurrentFrame()`
3. By changing what renders based on the frame, you create animation
4. Remotion captures each frame and encodes to MP4/WebM/GIF via FFmpeg

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Composition** | A registered video with dimensions, FPS, and duration |
| **Sequence** | A time-sliced container - shows children only during specified frames |
| **AbsoluteFill** | Full-frame positioning container (like `position: absolute; inset: 0`) |
| **Frame** | Zero-indexed. First frame = 0. At 30 FPS, frame 30 = 1 second |
| **FPS** | Frames per second. Standard: 30. Cinematic: 24. Smooth: 60 |

### Standard Project Structure

```
my-video/
├── public/                    # Static assets
│   ├── audio/                 # Voice narration MP3 files
│   │   └── narration.mp3     # Single continuous narration track
│   ├── images/               # Background images, logos
│   └── fonts/                # Custom font files
├── src/
│   ├── Root.tsx              # Composition registration (entry point)
│   ├── index.ts              # Module entry
│   ├── index.css             # TailwindCSS imports
│   ├── compositions/         # Video composition components
│   │   ├── MyVideo.tsx       # Main composition
│   │   └── scenes/           # Individual scene components
│   │       ├── IntroScene.tsx
│   │       ├── ContentScene.tsx
│   │       └── OutroScene.tsx
│   └── lib/
│       ├── types.ts          # Zod schemas and TypeScript types
│       ├── constants.ts      # FPS, durations, colors
│       └── utils.ts          # Frame timing helpers
├── scripts/                   # Voice generation and audio tools
├── remotion.config.ts        # Remotion + Webpack configuration
├── package.json
├── tsconfig.json
└── tailwind.config.js
```

---

## Core APIs Reference

### Hooks

```typescript
import { useCurrentFrame, useVideoConfig } from "remotion";

// Get the current frame number (0-indexed)
const frame = useCurrentFrame();

// Get video metadata
const { width, height, fps, durationInFrames, id } = useVideoConfig();
```

### Animation Functions

```typescript
import { interpolate, spring } from "remotion";

// Linear interpolation: map frame range to value range
const opacity = interpolate(frame, [0, 30], [0, 1], {
  extrapolateRight: "clamp",  // Don't go beyond 1
});

// Spring physics animation
const scale = spring({
  frame,
  fps,
  config: {
    damping: 200,    // Higher = less bounce
    stiffness: 100,  // Higher = faster
    mass: 1,         // Higher = slower
  },
});
```

### Components

```typescript
import { AbsoluteFill, Sequence, Img, staticFile } from "remotion";
import { Audio } from "@remotion/media";

// Full-frame container
<AbsoluteFill style={{ backgroundColor: "#1a1a2e" }}>
  {/* content */}
</AbsoluteFill>

// Time-sliced container (show from frame 0 for 90 frames)
<Sequence from={0} durationInFrames={90}>
  <MyScene />
</Sequence>

// Audio playback
<Audio src={staticFile("audio/narration.mp3")} />

// Image from public folder
<Img src={staticFile("images/background.png")} />
```

### Composition Registration

```typescript
// src/Root.tsx
import { Composition } from "remotion";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MyVideo"
        component={MyVideoComponent}
        durationInFrames={900}  // 30 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
```

### Dynamic Duration with calculateMetadata

```typescript
// For videos where duration depends on audio length
<Composition
  id="MyVideo"
  component={MyVideoComponent}
  fps={30}
  width={1920}
  height={1080}
  calculateMetadata={async () => {
    // Load timeline to determine actual duration
    const res = await fetch(staticFile("content/timeline.json"));
    const timeline = await res.json();
    const lastElement = timeline.audio[timeline.audio.length - 1];
    const durationMs = lastElement.endMs;
    const durationInFrames = Math.ceil((durationMs / 1000) * 30) + 30; // +1s padding

    return {
      durationInFrames,
      props: { timeline },
    };
  }}
/>
```

---

## The Continuous Audio Pattern (CRITICAL)

### The Problem: Audio Cutting Between Slides

When each slide has its own `<Audio>` inside a `<Sequence>`, audio **stops** when the Sequence ends. This creates jarring cuts in voice narration between slides.

### WRONG - Per-Slide Audio (CAUSES CUTTING)

```typescript
// BAD - Audio cuts at every slide transition!
const BrokenVideo = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={90}>
      <Audio src={staticFile("audio/slide1.mp3")} />  {/* STOPS at frame 90 */}
      <Slide1 />
    </Sequence>
    <Sequence from={90} durationInFrames={120}>
      <Audio src={staticFile("audio/slide2.mp3")} />  {/* Starts cold at frame 90 */}
      <Slide2 />
    </Sequence>
  </AbsoluteFill>
);
```

**Why it breaks**:
1. Audio inside `<Sequence>` is unmounted when the Sequence ends
2. Browser audio context needs time to initialize new audio
3. Frame rounding errors create micro-gaps between sequences
4. No overlap = silence during transition

### CORRECT - Single Continuous Audio

```typescript
// GOOD - Audio plays continuously, slides are purely visual
const SmoothVideo = () => (
  <AbsoluteFill>
    {/* ONE audio track at the root - spans the ENTIRE video */}
    <Audio src={staticFile("audio/narration.mp3")} />

    {/* Visual slides - transitions don't affect audio */}
    <Sequence from={0} durationInFrames={scene1Frames}>
      <IntroScene />
    </Sequence>
    <Sequence from={scene1Frames} durationInFrames={scene2Frames}>
      <ContentScene />
    </Sequence>
    <Sequence from={scene1Frames + scene2Frames} durationInFrames={scene3Frames}>
      <OutroScene />
    </Sequence>
  </AbsoluteFill>
);
```

**Why it works**:
1. Audio is at the root level - never unmounted during the video
2. `<Sequence>` only controls visual elements
3. Voice plays smoothly through all slide transitions
4. No gaps, no cutting, no re-initialization

### The Complete Pipeline

```
1. Write narration text for each scene
2. Generate per-scene MP3 files with edge-tts
3. Concatenate all MP3s into ONE continuous narration.mp3
4. Measure total duration with mutagen
5. Calculate scene boundaries from per-segment durations
6. Build composition with single <Audio> at root
7. Use scene boundaries for visual <Sequence> timing
```

### Frame Calculation Formula

```typescript
// ALWAYS use Math.ceil - never truncate audio timing
const FPS = 30;
const PADDING_FRAMES = Math.ceil(1.0 * FPS); // 1 second padding

// Convert audio duration to frames
const durationFrames = Math.ceil(audioDurationMs * FPS / 1000) + PADDING_FRAMES;

// Convert timestamp to start frame
const startFrame = Math.ceil(timestampMs * FPS / 1000);
```

### Duration Validation

Always validate that calculated frames match actual audio duration:

```bash
python remotion/scripts/measure_audio.py public/audio/narration.mp3 --expected-ms 45000
```

If the actual duration differs by more than 100ms from expected, adjust frame calculations.

---

## Voice Generation

### Free: edge-tts (Microsoft Neural Voices)

300+ voices across 70+ languages. Completely free, no API key needed.

```bash
# Generate narration for a single scene
python remotion/scripts/generate_voice.py \
  --text "Welcome to our presentation. Today we'll cover..." \
  --voice "en-US-AriaNeural" \
  --output public/audio/scene01.mp3

# List available voices
edge-tts --list-voices

# Generate with specific voice characteristics
edge-tts --text "Hello world" --voice "en-GB-RyanNeural" --write-media output.mp3
```

**Popular English Voices**:

| Voice | Gender | Accent | Best For |
|-------|--------|--------|----------|
| `en-US-AriaNeural` | Female | American | General narration |
| `en-US-GuyNeural` | Male | American | Professional tone |
| `en-GB-RyanNeural` | Male | British | Formal presentations |
| `en-GB-SoniaNeural` | Female | British | Elegant narration |
| `en-AU-NatashaNeural` | Female | Australian | Casual tone |
| `en-IN-NeerjaNeural` | Female | Indian | Tech presentations |

**Arabic Voices**:

| Voice | Gender | Dialect |
|-------|--------|---------|
| `ar-SA-HamedNeural` | Male | Saudi |
| `ar-SA-ZariyahNeural` | Female | Saudi |
| `ar-EG-SalmaNeural` | Female | Egyptian |
| `ar-EG-ShakirNeural` | Male | Egyptian |

### Multi-Scene Voice Pipeline

```bash
# Step 1: Generate per-scene audio files
python remotion/scripts/generate_voice.py --text "Scene 1 text..." --output public/audio/scene01.mp3
python remotion/scripts/generate_voice.py --text "Scene 2 text..." --output public/audio/scene02.mp3
python remotion/scripts/generate_voice.py --text "Scene 3 text..." --output public/audio/scene03.mp3

# Step 2: Concatenate into single continuous track
python remotion/scripts/concat_audio.py \
  --files public/audio/scene01.mp3 public/audio/scene02.mp3 public/audio/scene03.mp3 \
  --output public/audio/narration.mp3 \
  --gap 300

# Output: narration.mp3 + JSON with segment timestamps for Sequence timing
```

The concat script outputs JSON with segment boundaries:

```json
{
  "total_duration_ms": 45230,
  "total_frames": 1387,
  "segments": [
    {"file": "scene01.mp3", "start_ms": 0, "end_ms": 15400, "start_frame": 0, "end_frame": 462},
    {"file": "scene02.mp3", "start_ms": 15700, "end_ms": 30100, "start_frame": 471, "end_frame": 903},
    {"file": "scene03.mp3", "start_ms": 30400, "end_ms": 45230, "start_frame": 912, "end_frame": 1357}
  ],
  "gap_ms": 300,
  "fps": 30
}
```

Use these segment boundaries to time your visual `<Sequence>` components.

### Premium: ElevenLabs (Optional)

For ultra-realistic voices with character-level timestamps:

```bash
npm install @elevenlabs/elevenlabs-js
```

```typescript
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

const client = new ElevenLabsClient({ apiKey: process.env.ELEVENLABS_API_KEY });

const result = await client.textToSpeech.convertWithTimestamps("voice-id", {
  text: "Your narration text here",
  model_id: "eleven_multilingual_v2",
});
// Returns audio + character-level timestamps for subtitle sync
```

---

## Composition Patterns

### Pattern 1: Simple Single Scene

Best for short animations (5-15 seconds):

```typescript
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

export const SimpleAnimation: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(frame, [0, 30], [50, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0f172a",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <h1
        style={{
          color: "white",
          fontSize: 80,
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        Hello World
      </h1>
    </AbsoluteFill>
  );
};
```

### Pattern 2: Multi-Scene with Continuous Audio

Best for presentations and explainer videos:

```typescript
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";

// Scene durations derived from audio segment timestamps
const SCENES = {
  intro: { startFrame: 0, duration: 462 },
  content: { startFrame: 471, duration: 432 },
  outro: { startFrame: 912, duration: 445 },
};

export const Presentation: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Single continuous audio - NEVER cuts */}
      <Audio src={staticFile("audio/narration.mp3")} />

      {/* Visual scenes */}
      <Sequence from={SCENES.intro.startFrame} durationInFrames={SCENES.intro.duration}>
        <IntroScene />
      </Sequence>

      <Sequence from={SCENES.content.startFrame} durationInFrames={SCENES.content.duration}>
        <ContentScene />
      </Sequence>

      <Sequence from={SCENES.outro.startFrame} durationInFrames={SCENES.outro.duration}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
```

### Pattern 3: Timeline-Driven (Dynamic)

Best for AI-generated videos with variable content:

```typescript
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { z } from "zod";

const TimelineSchema = z.object({
  totalDurationMs: z.number(),
  narrationFile: z.string(),
  scenes: z.array(z.object({
    title: z.string(),
    startMs: z.number(),
    endMs: z.number(),
    background: z.string().optional(),
    text: z.string().optional(),
  })),
});

type Timeline = z.infer<typeof TimelineSchema>;

export const DynamicVideo: React.FC<{ timeline: Timeline }> = ({ timeline }) => {
  const FPS = 30;

  return (
    <AbsoluteFill>
      {/* Single continuous audio */}
      <Audio src={staticFile(timeline.narrationFile)} />

      {/* Dynamic scenes from timeline */}
      {timeline.scenes.map((scene, i) => {
        const startFrame = Math.ceil(scene.startMs * FPS / 1000);
        const duration = Math.ceil((scene.endMs - scene.startMs) * FPS / 1000);

        return (
          <Sequence key={i} from={startFrame} durationInFrames={duration}>
            <SceneRenderer scene={scene} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
```

### Pattern 4: Spring Transitions Between Scenes

```typescript
import { useCurrentFrame, spring, useVideoConfig, interpolate } from "remotion";

const SceneWithTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Enter animation (spring in)
  const enterProgress = spring({
    frame,
    fps,
    config: { damping: 200, stiffness: 100 },
  });

  // Exit animation (fade out in last 15 frames)
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        opacity: exitOpacity,
        transform: `scale(${enterProgress})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
```

---

## Rendering

### CLI Commands

```bash
# Render with default settings (MP4, CRF 24)
npx remotion render MyVideo

# Render to specific path
npx remotion render MyVideo out/my-video.mp4

# Quality presets
npx remotion render MyVideo --crf=15    # Max quality (large file)
npx remotion render MyVideo --crf=18    # High quality
npx remotion render MyVideo --crf=24    # Balanced (default)
npx remotion render MyVideo --crf=28    # Draft (fast, smaller)

# Format options
npx remotion render MyVideo --codec=h264          # MP4 (default)
npx remotion render MyVideo --codec=vp8           # WebM
npx remotion render MyVideo --codec=gif           # GIF
npx remotion render MyVideo --codec=prores        # ProRes (Apple)

# Render specific frame range
npx remotion render MyVideo --frames=0-90

# Render a single still frame
npx remotion still MyVideo out/thumbnail.png --frame=0

# Transparent video (for overlays)
npx remotion render MyVideo --codec=prores --prores-profile=4444

# Image sequence (PNG per frame)
npx remotion render MyVideo --image-format=png --sequence
```

### Quality Presets Reference

| Preset | CRF | Use Case | File Size |
|--------|-----|----------|-----------|
| **Max** | 15 | Final delivery, archive | Very large |
| **High** | 18 | YouTube, presentations | Large |
| **Balanced** | 24 | General use | Medium |
| **Draft** | 28 | Quick preview, iteration | Small |

### Resolution Presets

| Preset | Width | Height | Aspect |
|--------|-------|--------|--------|
| 1080p Landscape | 1920 | 1080 | 16:9 |
| 1080p Portrait | 1080 | 1920 | 9:16 |
| 720p Landscape | 1280 | 720 | 16:9 |
| Square | 1080 | 1080 | 1:1 |
| 4K Landscape | 3840 | 2160 | 16:9 |

---

## Project Setup Workflow

### Quick Start (3 Commands)

```bash
# Terminal 1: Create and start project
npx create-video@latest    # Choose: Blank template, Yes TailwindCSS, Yes Skills
cd my-video && npm install
npm run dev                 # Opens Remotion Studio at localhost:3000

# Terminal 2: Launch Claude Code
cd my-video
claude                      # Start prompting!
```

### Full Setup with Voice Pipeline

```bash
# 1. Create Remotion project
npx create-video@latest
cd my-video && npm install

# 2. Install voice generation dependencies
pip install edge-tts mutagen pydub

# 3. Create audio directory
mkdir -p public/audio

# 4. Verify setup
python remotion/scripts/setup_check.py

# 5. Start development
npm run dev
```

---

## Common Video Types and Prompts

### Explainer/Presentation Video

> "Create a 5-scene presentation video about [TOPIC]. Include:
> - Intro scene with title and subtitle
> - 3 content scenes with key points appearing one by one
> - Outro with call-to-action
> Use dark blue background (#0f172a) with white text, 1920x1080, 30fps.
> Add voice narration using edge-tts."

### Product Demo

> "Create a product showcase video for [PRODUCT]. Show:
> - Product name with zoom-in animation
> - 3 feature highlights with icons
> - Pricing slide with spring animation
> - Contact information outro
> Portrait mode 1080x1920 for social media."

### Tutorial/Walkthrough

> "Create a step-by-step tutorial video showing [PROCESS]. Each step should:
> - Show step number with fade-in
> - Display instruction text
> - Hold for narration duration
> - Transition smoothly to next step
> With voice narration explaining each step."

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|---------|
| **Audio cuts between slides** | Per-slide `<Audio>` in `<Sequence>` | Use single `<Audio>` at root level (continuous audio pattern) |
| **Audio ends early** | Frame calculation truncates instead of ceiling | Use `Math.ceil()` for all ms-to-frame conversions |
| **Silent gap between scenes** | Rounding error in start frame calculation | Add 200-300ms gap in concat_audio.py instead of zero gap |
| **Black/blank render** | Missing background or opacity = 0 | Check `backgroundColor` and initial `interpolate` values |
| **Module not found** | Missing dependencies | Run `rm -rf node_modules && npm install` |
| **Port already in use** | Previous dev server running | Kill process on port 3000: `npx kill-port 3000` |
| **Fonts missing in render** | Custom fonts not loaded | Use `@remotion/google-fonts` or `staticFile()` for local fonts |
| **Slow render** | Too many frames or heavy components | Reduce FPS, optimize components, use `useMemo` for calculations |
| **TailwindCSS not working** | Missing config or CSS import | Verify `remotion.config.ts` has enableTailwind, import `index.css` in Root |
| **Skills not loading** | Not in project directory | Run `claude` from inside the Remotion project folder |

### Audio Debugging Checklist

1. Is there ONE `<Audio>` component at the root level? (Not inside any `<Sequence>`)
2. Does `narration.mp3` exist in `public/audio/`?
3. Does the total `durationInFrames` of the composition >= audio duration in frames?
4. Are scene boundaries using `Math.ceil()` for frame calculations?
5. Run `python measure_audio.py public/audio/narration.mp3` to verify actual duration
6. Check Remotion Studio audio waveform - is there a continuous line?

### Performance Tips

1. **Use `useMemo`** for expensive calculations that don't change every frame
2. **Prefer `interpolate()`** over manual math - it handles edge cases
3. **Use `spring()`** for natural motion instead of linear easing
4. **Keep components small** - one component per scene
5. **Use TailwindCSS** for styling instead of heavy inline styles
6. **Optimize images** - compress before placing in `public/`
7. **Use `premountFor`** on heavy sequences to pre-load them

---

## Voice Script Writing Tips

### For Natural Narration

1. **Write conversationally** - avoid jargon, use simple sentences
2. **One idea per sentence** - easier for TTS to pace correctly
3. **Add natural pauses** - use periods and commas, not ellipses
4. **Keep scenes 10-30 seconds** - long monologues lose attention
5. **End scenes with complete thoughts** - don't split sentences across slides

### Timing Guide

| Content Type | Approximate Duration |
|-------------|---------------------|
| Title slide (just a name) | 2-3 seconds |
| Single sentence | 3-5 seconds |
| Paragraph (3-4 sentences) | 10-15 seconds |
| Detailed explanation | 20-30 seconds |
| Full presentation (10 slides) | 3-7 minutes |

### Example Script Structure

```
Scene 1 (Intro - 5s):
"Welcome to [TOPIC]. Today we'll explore the key concepts you need to know."

Scene 2 (Content - 15s):
"The first important point is [POINT]. This matters because [REASON].
Let's look at how this works in practice."

Scene 3 (Content - 15s):
"Next, we have [POINT]. This builds on what we just covered.
The key difference here is [DETAIL]."

Scene 4 (Outro - 5s):
"That covers the essentials of [TOPIC]. Thanks for watching."
```

---

## Edge-TTS Voice Customization

### Rate and Pitch Control

```bash
# Slower speech (good for tutorials)
edge-tts --text "Speak slowly" --voice "en-US-AriaNeural" --rate="-20%" --write-media slow.mp3

# Faster speech (good for recaps)
edge-tts --text "Speak fast" --voice "en-US-AriaNeural" --rate="+15%" --write-media fast.mp3

# Higher pitch
edge-tts --text "Higher voice" --voice "en-US-GuyNeural" --pitch="+10Hz" --write-media high.mp3

# Lower pitch
edge-tts --text "Lower voice" --voice "en-US-GuyNeural" --pitch="-10Hz" --write-media low.mp3
```

### SSML Support (Advanced)

edge-tts supports SSML for fine-grained control:

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-AriaNeural">
    Welcome to our presentation.
    <break time="500ms"/>
    Today we will cover three important topics.
    <emphasis level="strong">First</emphasis>, the architecture overview.
  </voice>
</speak>
```

---

## Integration with TailwindCSS

Remotion supports TailwindCSS for styling video components:

```typescript
// Use Tailwind classes directly in components
const TitleSlide: React.FC<{ title: string }> = ({ title }) => (
  <AbsoluteFill className="bg-slate-900 flex items-center justify-center">
    <h1 className="text-7xl font-bold text-white tracking-tight">
      {title}
    </h1>
  </AbsoluteFill>
);
```

**Note**: Not all Tailwind utilities work in video rendering. Stick to:
- Layout: `flex`, `grid`, `items-center`, `justify-center`
- Spacing: `p-*`, `m-*`, `gap-*`
- Typography: `text-*`, `font-*`, `tracking-*`, `leading-*`
- Colors: `bg-*`, `text-*`, `border-*`
- Borders: `rounded-*`, `border-*`
- Effects: `shadow-*`, `opacity-*`

**Avoid**: `transition-*`, `animate-*`, `hover:*` (use Remotion's interpolate/spring instead)

---

## Remotion Configuration

### remotion.config.ts

```typescript
import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind-v4";

Config.overrideWebpackConfig((currentConfiguration) => {
  return enableTailwind(currentConfiguration);
});
```

### package.json Scripts

```json
{
  "scripts": {
    "dev": "remotion studio",
    "build": "remotion bundle",
    "render": "remotion render",
    "upgrade": "remotion upgrade"
  }
}
```

---

## Changelog

### v1.0.0 (2026-02-16)
- Initial release
- Continuous audio pattern (fixes voice cutting between slides)
- Free voice narration via edge-tts (300+ voices)
- 5 slash commands: /remotion, /remotion-setup, /create-video, /render-video, /add-voice
- 4 Python helper scripts (setup check, voice generation, audio concat, duration measurement)
- 4 composition templates (continuous audio, multi-scene, Root, timeline schema)
- Complete API reference and troubleshooting guide
- Cross-platform support (Windows, macOS, Linux)
