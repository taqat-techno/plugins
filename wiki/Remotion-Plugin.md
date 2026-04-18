# Remotion Plugin

**Package:** `remotion` · **Version:** `2.1.0` · **Category:** development · **License:** MIT · **Source:** [`remotion-plugin/`](../../remotion-plugin/)

## Purpose

Create **professional videos with smooth voice narration** using [Remotion](https://remotion.dev) and Claude Code. The core differentiator: the **Continuous Audio Pattern** that prevents the voice-cutting-between-slides problem common to Remotion-based video generation.

## What it does

- **Initialize** a new Remotion project with all dependencies and the continuous-audio skeleton.
- **Voice narration** via [edge-tts](https://github.com/rany2/edge-tts) (free, 200+ voices, 75+ languages, no API key).
- **Continuous audio pipeline** — a single audio track at the root level plays through all visual transitions, so voice never cuts between slides.
- **TailwindCSS-based styling** for visual composition.
- **Natural-language prompts** describe the video; Claude composes the Remotion scenes.
- **Multiple output formats** — MP4, WebM, GIF.

## How it works (high level)

### The voice-cutting problem

Standard Remotion uses `<Audio>` components inside each `<Composition>`. When slides transition, the audio components re-mount and audio cuts. The plugin's scaffold avoids this by placing a single `<Audio>` at the root that survives every transition.

### The workflow

1. User runs `/remotion <project-name>` — plugin scaffolds a Remotion project with the continuous-audio pattern pre-wired.
2. User describes the video in plain English.
3. Claude generates the scene composition (typescript + Tailwind).
4. edge-tts generates the continuous voice track from the narration script.
5. Remotion renders the final MP4/WebM/GIF.

### Layout

- **Single command** (`/remotion`) handles status + project init. v2.0 consolidated 5 commands into this one.
- **Templates** under `templates/` — starter compositions with continuous-audio pre-wired.
- **Memories** under `memories/` — session learnings, voice preferences, render-setting defaults.
- **Scripts** under `scripts/` — helpers for edge-tts invocation and asset pipeline.
- **Hooks** — advisory, lightweight.

## Command

| Command | Purpose |
|---|---|
| `/remotion` | Check project status + prerequisites (or) |
| `/remotion <name>` | Initialize a new Remotion project with continuous-audio scaffold |

Post-initialization, the user describes the video in natural language and Claude iterates on the composition. No further slash commands are needed.

## Inputs and outputs

**Inputs:**
- Project name (for init).
- Natural-language video description.
- Optional: voice name (edge-tts voice ID), visual style preferences.

**Outputs:**
- A fully-scaffolded Remotion project (for init).
- Generated TypeScript compositions + Tailwind styles.
- WAV narration track via edge-tts.
- Rendered MP4 / WebM / GIF.

## Configuration

- **edge-tts** — installed automatically as part of project init. Uses Microsoft's free voices.
- **Remotion 4.0+** — installed as an npm dependency by the init script.
- **Render settings** live in the project's `remotion.config.ts`. Defaults target 1080p MP4.

## Dependencies

- **Node.js 18+** with npm/npx.
- **Python 3** for edge-tts.
- **FFmpeg** (installed by the Remotion setup — required for render).
- **System resources** — Remotion rendering is CPU-heavy. Long videos benefit from a workstation rather than a laptop.

## Usage examples

```
# 1. Set up a new Remotion project
/remotion my-video

# 2. Start Remotion Studio (for preview)
cd my-video && npm run dev

# 3. Describe the video in natural language
"Create a 60-second product demo with voice narration about our new feature"

# 4. Iterate — add a slide, adjust pacing, change voice
"Add a final slide with the CTA, use the Azure voice Michelle"

# 5. Render
"Render my video as a high-quality MP4"
```

## Known limitations

- **Render is CPU-bound.** No GPU acceleration by default. Minutes-to-hours for longer videos.
- **Voice options limited to edge-tts.** For premium voices (ElevenLabs, OpenAI TTS, etc.), users need to swap the narration script generation manually.
- **TailwindCSS-first.** Non-Tailwind projects can be adapted but require re-wiring the scaffold.
- **No live audio-to-visual sync editor.** The continuous-audio pattern pre-generates the audio; visual timing is driven by composition durations, not by interactive sync.
- **Remotion licensing.** Remotion has its own license (free for individuals + small teams, paid for larger orgs). See [remotion.dev/docs/license](https://remotion.dev/docs/license). The plugin is MIT but the Remotion runtime is not.

## Related plugins and integrations

- **ntfy** — push a notification to your phone when a long render finishes.
- **paper** — use the design system output as visual templates for the video.
- **pandoc** — convert a written article into a narration script, then feed it to Remotion.

## See also

- Source: [`remotion-plugin/README.md`](../../remotion-plugin/README.md)
- [`remotion-plugin/CHANGELOG.md`](../../remotion-plugin/CHANGELOG.md)
- [Remotion official documentation](https://remotion.dev/docs)
- [edge-tts on GitHub](https://github.com/rany2/edge-tts) — free voice generation used by the scaffold
