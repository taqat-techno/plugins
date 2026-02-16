# Audio Patterns for Remotion Videos

## The Continuous Audio Pattern (ALWAYS USE)

The single most important pattern for videos with voice narration:

**Place ONE `<Audio>` component at the root `<AbsoluteFill>` level.**

```typescript
<AbsoluteFill>
  <Audio src={staticFile("audio/narration.mp3")} />  {/* ROOT level */}
  <Sequence from={0} durationInFrames={150}>
    <IntroScene />  {/* Visual only */}
  </Sequence>
  <Sequence from={150} durationInFrames={300}>
    <ContentScene />  {/* Visual only */}
  </Sequence>
</AbsoluteFill>
```

Audio plays continuously through all visual transitions.

## Anti-Patterns (NEVER DO)

### 1. Audio Inside Sequence

```typescript
// WRONG - Audio STOPS when Sequence ends
<Sequence from={0} durationInFrames={150}>
  <Audio src={staticFile("audio/slide1.mp3")} />  // CUTS at frame 150!
  <Slide1 />
</Sequence>
```

### 2. Frame Truncation

```typescript
// WRONG - truncates, losing milliseconds
const frames = Math.floor(durationMs * FPS / 1000);

// CORRECT - always round up
const frames = Math.ceil(durationMs * FPS / 1000);
```

### 3. No Duration Validation

```typescript
// WRONG - assumes duration without checking
durationInFrames={900}

// CORRECT - calculate from actual audio duration
// Run: python measure_audio.py narration.mp3 --fps 30
// Use: duration_frames_with_padding from output
```

## Voice Generation Pipeline

```
1. Write script per scene
2. generate_voice.py per scene -> scene01.mp3, scene02.mp3, ...
3. concat_audio.py -> narration.mp3 + segment timestamps JSON
4. Use ONE <Audio> at root with narration.mp3
5. Use segment timestamps for visual Sequence timing
6. measure_audio.py to validate
```

## Frame Calculation Rules

```
startFrame = Math.ceil(startMs * FPS / 1000)
durationFrames = Math.ceil((endMs - startMs) * FPS / 1000)
totalFrames = Math.ceil(totalMs * FPS / 1000) + Math.ceil(paddingSeconds * FPS)
```

- Always use Math.ceil() - never Math.floor() or parseInt()
- Always add 1 second padding (30 frames at 30fps)
- Always validate with measure_audio.py after generation

## Mixing Multiple Audio Tracks

If you need background music AND narration:

```typescript
<AbsoluteFill>
  {/* Both at root level - Remotion mixes automatically */}
  <Audio src={staticFile("audio/narration.mp3")} />
  <Audio src={staticFile("audio/music.mp3")} volume={0.15} />

  {/* Visual scenes */}
  <Sequence ...>
    <Scene />
  </Sequence>
</AbsoluteFill>
```

Use `volume` prop to balance music vs narration (0.1-0.2 for background music).
