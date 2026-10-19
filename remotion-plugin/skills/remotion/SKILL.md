---
name: remotion-video
description: >-
  Use when the user is building or fixing a narrated video in Remotion (React):
  voice-over that cuts, stops or restarts between scenes or slides, an Audio
  element inside a Sequence, scene timing that drifts from the narration,
  generating narration with edge-tts, concatenating per-scene MP3s into one
  track, converting audio milliseconds to frames, creating a new Remotion
  project, or rendering a composition to MP4, WebM or GIF. Not for general
  ffmpeg video editing, non-Remotion video tools, or audio work unrelated to a
  Remotion composition.
user-invocable: false
metadata:
  mode: "cli-tool"
  supported-platforms: ["windows", "macos", "linux"]
  node-min-version: "18.0.0"
  remotion-version: "4.0.0+"
  voice-engines: ["edge-tts"]
  output-formats: ["mp4", "webm", "gif", "png-sequence"]
  last_reviewed: "2026-10-19"
---

# Remotion Video Creator

Narrated Remotion videos whose voice never cuts between scenes: one continuous
narration track at the root of the composition, with scene timing taken from
measured MP3 durations.

## Commands

| Command | Does |
|---|---|
| `/remotion:init [name]` | New project from the Blank template plus this plugin's templates |
| `/remotion:status` | Prerequisites and current-project check |
| `/remotion:render [id]` | Render a composition (Rendering workflow below) |
| `/remotion:voice [--list]` | List voices or run the narration pipeline |

Natural-language requests use the same workflows.

## Before you start: licence and data egress

Say each of these once per session, before the step it applies to:

- **Remotion licence** (before creating a project or a first render): Remotion
  is source-available. It is free for individuals, non-profits, for-profit
  organisations with up to 3 employees and for evaluation; other companies need
  a company licence: https://www.remotion.dev/license
- **edge-tts** (before the first narration call): edge-tts is an unofficial
  client of Microsoft Edge's online read-aloud service. Every narration string is
  sent to Microsoft; it is not an SLA-backed or explicitly commercially licensed
  API. Ask before narrating text the user called confidential or unreleased.

## Prerequisites

| Tool | Min version | Check |
|---|---|---|
| Node.js + npm | 18.0.0 | `node --version` |
| Python | 3.8 | `python --version` |
| edge-tts | latest | `python -m pip show edge-tts` |
| mutagen | latest | `python -m pip show mutagen` |
| pydub or ffmpeg | optional | needed for gaps between segments |

`python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_check.py"` checks all of them and
prints install commands. It installs nothing; show the user the commands rather
than running package installs yourself.

## The Continuous Audio Pattern (critical)

An `<Audio>` inside a `<Sequence>` stops when that Sequence ends, so per-scene
audio cuts at every transition. Put ONE `<Audio>` at the root and drive the
visual `<Sequence>`s from the narration's segment timestamps:

```tsx
<AbsoluteFill>
  <Audio src={staticFile("audio/narration.mp3")} />  {/* root level: never cuts */}
  <Sequence from={0} durationInFrames={scene1Frames}><IntroScene /></Sequence>
  <Sequence from={scene1Frames} durationInFrames={scene2Frames}><ContentScene /></Sequence>
</AbsoluteFill>
```

Frames: `Math.ceil(ms * FPS / 1000)` for every conversion, plus 1 second of
padding (`Math.ceil(1.0 * FPS)`) after the audio ends.

## Narration workflow

The scripts run in place from the plugin. Run them from the video project's
root; output paths are relative to the current directory.

```bash
# 1. One MP3 per scene (or --scenes scenes.json --output-dir public/audio/scenes)
python "${CLAUDE_PLUGIN_ROOT}/scripts/generate_voice.py" --text "Scene text..." --voice en-US-AriaNeural --output public/audio/scenes/01_intro.mp3 --fps 30

# 2. Concatenate into ONE track; stdout is JSON with per-segment start/end ms and frames
python "${CLAUDE_PLUGIN_ROOT}/scripts/concat_audio.py" --dir public/audio/scenes --output public/audio/narration.mp3 --gap 200 --fps 30

# 3. Validate the final track
python "${CLAUDE_PLUGIN_ROOT}/scripts/measure_audio.py" public/audio/narration.mp3 --fps 30
```

- Use the concat JSON `segments[].start_frame` / `duration_frames` for the
  `<Sequence>`s and `total_frames_with_padding` for `durationInFrames`.
- Concat picks pydub, then ffmpeg, then a byte-level `simple` mode. `simple`
  cannot insert gaps; its JSON then reports `gap_ms: 0` and back-to-back
  timestamps, which are correct for the audio it wrote.
- Scene ids in `--scenes` JSON are file names: letters, digits, `_` and `-` only.
- If an output file already exists and was not produced in this session, ask
  before overwriting it.
- Default voice `en-US-AriaNeural`; `generate_voice.py --list-voices --language ar`
  filters the list.

## Rendering workflow

1. Read the composition ids from `src/Root.tsx`.
2. Ask for format and quality if the user did not say; ask before overwriting an
   existing output file.

```bash
npx remotion render <CompositionId> out/video.mp4 --crf=18             # high (15 max, 24 balanced, 28 draft)
npx remotion render <CompositionId> out/video.webm --codec=vp8         # WebM
npx remotion render <CompositionId> out/video.gif --codec=gif          # GIF
npx remotion still <CompositionId> out/thumb.png --frame=0             # thumbnail
```

Resource use: the first render downloads Chrome Headless Shell. Rendering is
CPU- and RAM-heavy and uses roughly half the CPU cores by default; pass
`--concurrency=<n>` to limit it on a shared machine, and expect temporary frame
data on disk proportional to length and resolution. Use `--crf=28` or a frame
range (`--frames=0-90`) for quick drafts.

## Key rules

1. ONE `<Audio>` at root level, never inside `<Sequence>`.
2. `Math.ceil()` for every ms-to-frame conversion.
3. 1 second of padding after the audio ends.
4. Validate with `measure_audio.py` before the final render.
5. `staticFile()` for every asset in `public/`.

## Reference files (read when needed)

- `${CLAUDE_PLUGIN_ROOT}/memories/audio_patterns.md` - the continuous-audio pattern, anti-patterns, mixing music under narration
- `${CLAUDE_PLUGIN_ROOT}/memories/composition_patterns.md` - title, bullet, Ken Burns, transition, counter and progress-bar scene recipes; colour and resolution presets
- `${CLAUDE_PLUGIN_ROOT}/memories/voice_reference.md` - voice tables, rate and pitch, SSML, script-writing tips
- `${CLAUDE_PLUGIN_ROOT}/memories/troubleshooting.md` - common errors, audio-debugging checklist, render recovery
- `${CLAUDE_PLUGIN_ROOT}/templates/` - the files `/remotion:init` copies: `Root.tsx`, `composition_continuous_audio.tsx`, `composition_multi_scene.tsx`, `timeline_schema.ts`. Copy one into an existing project when the user wants that pattern there.
