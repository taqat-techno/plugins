---
title: 'Render Video'
read_only: false
type: 'command'
description: 'Render a Remotion composition to MP4, WebM, or GIF with quality presets.'
---

# /render-video - Video Rendering

Render a Remotion composition to a video file with quality presets.

## On Activation

### Step 1: Detect Compositions

Read `src/Root.tsx` and list all registered compositions:

```bash
# Find composition IDs
grep -oP 'id="[^"]*"' src/Root.tsx
```

Display available compositions:
```
Available compositions:
  1. ContinuousAudioVideo (1920x1080, 30fps)
  2. MultiSceneVideo (1920x1080, 30fps)
  3. PortraitVideo (1080x1920, 30fps)

Which composition do you want to render?
```

### Step 2: Choose Quality Preset

Ask the user or accept a preset argument:

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

### Step 3: Render

Execute the render command:

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

After rendering, validate that audio timing matches:

```bash
python scripts/measure_audio.py public/audio/narration.mp3 --fps 30
```

Compare the reported duration with the composition's `durationInFrames`.

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

## Advanced Options

### Render Specific Frames
```bash
# Only render frames 0-90 (first 3 seconds at 30fps)
npx remotion render MyVideo --frames=0-90
```

### Render a Thumbnail
```bash
npx remotion still MyVideo out/thumbnail.png --frame=0
```

### Transparent Video (for overlays)
```bash
npx remotion render MyVideo --codec=prores --prores-profile=4444
```

### Image Sequence (for compositing)
```bash
npx remotion render MyVideo --image-format=png --sequence
```

## Error Recovery

- If "Composition not found": check the ID matches exactly (case-sensitive)
- If render crashes: try `--gl=angle` on Windows, check memory (close other apps)
- If audio is silent: verify narration.mp3 exists in public/audio/
- If black frames: check component renders something for all frame ranges
- If render is very slow: use `--crf=28` for draft, reduce resolution, or limit frame range
