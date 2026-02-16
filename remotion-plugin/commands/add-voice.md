---
title: 'Add Voice Narration'
read_only: false
type: 'command'
description: 'Add voice narration to an existing Remotion composition using the continuous audio pattern.'
---

# /add-voice - Add Voice Narration

Add free voice narration to an existing Remotion composition using edge-tts.

## On Activation

Display welcome:
```
Add Voice Narration
===================
Add professional voice narration to your video using free edge-tts voices.
The audio uses the CONTINUOUS pattern - voice never cuts between slides.
```

## Pipeline Steps

### Step 1: Identify the Composition

Read the project's `src/Root.tsx` to find registered compositions. Ask the user which one to add voice to, or accept it as an argument.

### Step 2: Analyze Existing Scenes

Read the composition file to identify:
1. How many `<Sequence>` components exist
2. The current `from` and `durationInFrames` for each
3. Whether an `<Audio>` component already exists

If an `<Audio>` already exists inside a `<Sequence>` (the WRONG pattern), warn the user:
```
WARNING: Found <Audio> inside <Sequence> - this causes audio cutting!
I'll move it to the root level for smooth playback.
```

### Step 3: Collect Narration Text

Ask for narration text. Two modes:

**Mode A - Single text** (for short videos):
> "Provide the full narration text. I'll generate one audio file."

**Mode B - Per-scene text** (recommended for multi-scene):
> "Provide narration text for each scene:"
```
Scene 1 (intro):   "Welcome to..."
Scene 2 (content): "The first key point..."
Scene 3 (outro):   "Thank you for..."
```

### Step 4: Choose Voice

Show popular voices and ask the user to choose:

```
Popular voices:
  1. en-US-AriaNeural   (Female, American) - DEFAULT
  2. en-US-GuyNeural    (Male, American)
  3. en-GB-RyanNeural   (Male, British)
  4. en-GB-SoniaNeural  (Female, British)
  5. ar-SA-HamedNeural  (Male, Arabic)
  6. ar-EG-SalmaNeural  (Female, Arabic)

Or list all: python scripts/generate_voice.py --list-voices
```

### Step 5: Generate Voice

**For single text:**
```bash
python scripts/generate_voice.py \
  --text "[narration text]" \
  --voice "[chosen voice]" \
  --output public/audio/narration.mp3
```

**For per-scene text:**
```bash
# Generate each scene
python scripts/generate_voice.py --text "[scene 1 text]" --voice "[voice]" --output public/audio/scene01.mp3
python scripts/generate_voice.py --text "[scene 2 text]" --voice "[voice]" --output public/audio/scene02.mp3
python scripts/generate_voice.py --text "[scene 3 text]" --voice "[voice]" --output public/audio/scene03.mp3

# Concatenate into continuous track
python scripts/concat_audio.py \
  --files public/audio/scene01.mp3 public/audio/scene02.mp3 public/audio/scene03.mp3 \
  --output public/audio/narration.mp3 \
  --gap 300 \
  --fps 30
```

**Save the concat output JSON** - it has segment timestamps.

### Step 6: Measure Audio Duration

```bash
python scripts/measure_audio.py public/audio/narration.mp3 --fps 30
```

Note the `duration_frames_with_padding` value.

### Step 7: Modify Composition

**CRITICAL - Apply the Continuous Audio Pattern:**

1. **Add `<Audio>` at the ROOT level** (inside the outermost `<AbsoluteFill>`, NOT inside any `<Sequence>`):
   ```typescript
   import { Audio } from "@remotion/media";

   // At the top of the component's return, inside AbsoluteFill:
   <Audio src={staticFile("audio/narration.mp3")} />
   ```

2. **Remove any existing `<Audio>` inside `<Sequence>` components** (if found)

3. **Update Sequence timings** to match the concat_audio.py segment timestamps:
   ```typescript
   // Use segment timestamps from concat_audio.py
   <Sequence from={segments[0].startFrame} durationInFrames={segments[0].durationFrames}>
   ```

4. **Update `durationInFrames`** in Root.tsx to match `total_frames_with_padding` from concat output

### Step 8: Display Results

```
Voice narration added successfully!

Audio files:
  - public/audio/scene01.mp3    (scene 1 narration)
  - public/audio/scene02.mp3    (scene 2 narration)
  - public/audio/narration.mp3  (continuous track)

Composition updated:
  - [CompositionFile.tsx]: Added <Audio> at root level
  - [Root.tsx]: Updated durationInFrames to [new value]

Preview: npm run dev
Render:  /render-video
```

## Important Rules

1. **NEVER** place `<Audio>` inside a `<Sequence>` - it will cut between slides
2. **ALWAYS** use `Math.ceil()` for ms-to-frame calculations
3. **ALWAYS** add padding frames (1 second = 30 frames at 30fps)
4. **ALWAYS** validate audio duration matches composition duration
5. If adding voice to an existing video that already has music, place both `<Audio>` components at the root level - Remotion will mix them automatically

## Error Recovery

- If voice sounds robotic: try a different voice (en-GB-RyanNeural is more natural)
- If audio is too fast/slow: use `--rate "+10%"` or `--rate "-15%"` flag
- If gap between scenes is too long: reduce `--gap` to 100 or 150ms
- If audio still cuts: verify `<Audio>` is NOT inside any `<Sequence>`
