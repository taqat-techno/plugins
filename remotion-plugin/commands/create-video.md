---
title: 'Create Video'
read_only: false
type: 'command'
description: 'Create a complete video with voice narration from a text prompt. Full pipeline: prompt to scenes to voice to video.'
---

# /create-video - Full Video Creation Pipeline

Create a complete video with voice narration from a natural language description.

## On Activation

Display welcome message:

```
Create Video Pipeline
=====================
Describe your video and I'll generate:
  1. Scene breakdown with narration scripts
  2. Voice narration (free via edge-tts)
  3. Continuous audio track (no cutting between slides!)
  4. React composition with animations
  5. Ready to preview in Remotion Studio
```

## Pipeline Steps

### Step 1: Gather Requirements

Ask the user to describe their video. If they provide a brief prompt, expand by asking:

1. **Topic/Content**: What is the video about?
2. **Number of scenes**: How many slides/scenes? (default: 3-5)
3. **Duration target**: How long? (default: 30-60 seconds)
4. **Style**: Professional, casual, educational, marketing? (default: professional)
5. **Voice**: Which voice? (default: en-US-AriaNeural, suggest listing with `--list-voices`)
6. **Dimensions**: 1920x1080 landscape or 1080x1920 portrait? (default: 1920x1080)
7. **Colors**: Brand colors or preferences? (default: dark slate theme)

### Step 2: Generate Scene Breakdown

Break the content into scenes. Each scene needs:
- **Scene ID** (e.g., "intro", "content1", "outro")
- **Scene type** ("title", "content", "image", "outro")
- **Visual content** (title, bullet points, background)
- **Narration script** (what the voice will say)

Example breakdown:
```
Scene 1 (intro, ~5s):    Title slide with topic name
Scene 2 (content, ~15s): Key points with bullet animations
Scene 3 (content, ~15s): More details with examples
Scene 4 (outro, ~5s):    Call to action / thank you
```

### Step 3: Generate Voice Narration

For each scene, generate an MP3 file:

```bash
# Generate per-scene audio
python scripts/generate_voice.py \
  --text "Welcome to our presentation about..." \
  --voice "en-US-AriaNeural" \
  --output public/audio/scene01_intro.mp3

python scripts/generate_voice.py \
  --text "The first key point is..." \
  --voice "en-US-AriaNeural" \
  --output public/audio/scene02_content.mp3

# ... repeat for each scene
```

Alternatively, create a scenes JSON file and batch generate:

```json
[
  {"id": "scene01_intro", "text": "Welcome to our presentation..."},
  {"id": "scene02_content", "text": "The first key point is..."},
  {"id": "scene03_content", "text": "Another important aspect..."},
  {"id": "scene04_outro", "text": "Thank you for watching..."}
]
```

```bash
python scripts/generate_voice.py \
  --scenes scenes.json \
  --output-dir public/audio/ \
  --voice "en-US-AriaNeural"
```

### Step 4: Concatenate Audio (CRITICAL)

Merge all scene audio into ONE continuous track:

```bash
python scripts/concat_audio.py \
  --files public/audio/scene01_intro.mp3 public/audio/scene02_content.mp3 public/audio/scene03_content.mp3 public/audio/scene04_outro.mp3 \
  --output public/audio/narration.mp3 \
  --gap 300 \
  --fps 30
```

**Save the JSON output** - it contains the segment timestamps needed for Sequence timing:

```json
{
  "total_frames_with_padding": 1387,
  "segments": [
    {"start_frame": 0, "end_frame": 150, "duration_frames": 150},
    {"start_frame": 159, "end_frame": 459, "duration_frames": 300},
    ...
  ]
}
```

### Step 5: Generate Composition

Create a React composition using the **continuous audio pattern**:

**CRITICAL RULES**:
1. Place ONE `<Audio>` component at the root `<AbsoluteFill>` level
2. Use `<Sequence>` ONLY for visual elements
3. Use `Math.ceil()` for ALL frame calculations
4. Use segment timestamps from concat_audio.py for Sequence timing
5. Add spring/interpolate animations for smooth transitions
6. Total `durationInFrames` = `total_frames_with_padding` from concat output

Create the composition file at `src/compositions/[VideoName].tsx`:

```typescript
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";

// Segment timestamps from concat_audio.py
const SEGMENTS = [
  { startFrame: 0, durationFrames: 150 },
  { startFrame: 159, durationFrames: 300 },
  // ... from concat_audio.py output
];

export const MyVideo: React.FC = () => (
  <AbsoluteFill>
    {/* Continuous audio - NEVER cuts */}
    <Audio src={staticFile("audio/narration.mp3")} />

    {/* Visual scenes */}
    <Sequence from={SEGMENTS[0].startFrame} durationInFrames={SEGMENTS[0].durationFrames}>
      <IntroScene />
    </Sequence>
    {/* ... more scenes */}
  </AbsoluteFill>
);
```

### Step 6: Register Composition

Update `src/Root.tsx` to register the new composition:

```typescript
<Composition
  id="MyVideo"
  component={MyVideo}
  durationInFrames={1387}  // from concat_audio.py total_frames_with_padding
  fps={30}
  width={1920}
  height={1080}
/>
```

### Step 7: Display Preview Instructions

```
Video created successfully!

Files generated:
  - public/audio/scene01_intro.mp3      (scene narration)
  - public/audio/scene02_content.mp3    (scene narration)
  - public/audio/narration.mp3          (continuous track)
  - src/compositions/MyVideo.tsx        (video composition)
  - src/Root.tsx                        (updated with new composition)

Preview:
  npm run dev
  Open http://localhost:3000 and select "MyVideo" from the sidebar

Render when ready:
  /render-video
  or: npx remotion render MyVideo out/my-video.mp4
```

## Animation Guidelines

When generating scene components, use these patterns:

### Text Fade-In
```typescript
const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
const translateY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: "clamp" });
```

### Bullet Points (Staggered)
```typescript
points.map((point, i) => {
  const delay = 15 + i * 12;
  const opacity = interpolate(frame, [delay, delay + 12], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
});
```

### Spring Entrance
```typescript
const scale = spring({ frame, fps, config: { damping: 200, stiffness: 100 } });
```

### Scene Exit Fade
```typescript
const exitOpacity = interpolate(
  frame,
  [durationInFrames - 10, durationInFrames],
  [1, 0],
  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
);
```

## Error Recovery

- If voice generation fails: check edge-tts is installed, try a different voice
- If concat fails: check all MP3 files exist, try `--method simple`
- If composition errors: check imports, verify Audio component is at root level
- If preview is blank: check `durationInFrames` > 0, verify staticFile paths
