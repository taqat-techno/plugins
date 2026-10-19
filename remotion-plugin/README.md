# remotion

## What it does

Helps Claude build narrated [Remotion](https://remotion.dev) videos whose voice
never cuts between scenes. It sets up a project with continuous-audio templates,
generates per-scene narration with edge-tts, joins it into one track with
frame-exact scene timestamps, and renders the result.

For developers making explainer, demo or promo videos in Remotion (React).

The core idea: an `<Audio>` inside a `<Sequence>` stops when that Sequence ends,
so per-scene audio cuts at every transition. The plugin puts one narration track
at the root of the composition and times the scenes from measured MP3 durations.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install remotion@taqat-techno-plugins
```

## Requirements

| Requirement | Needed for | Check |
|---|---|---|
| Node.js 18+ and npm | Remotion itself, `/remotion:init`, rendering | `node --version` |
| Python 3.8+ | the pipeline scripts | `python --version` |
| `edge-tts` (pip) | narration | `python -m pip show edge-tts` |
| `mutagen` (pip) | measuring MP3 durations | `python -m pip show mutagen` |
| `pydub` (pip) or `ffmpeg` | optional: silence gaps between segments | `ffmpeg -version` |
| Network access | `npx create-video`, edge-tts, the first render's Chrome Headless Shell download | |

`/remotion:status` runs `scripts/setup_check.py`, which checks all of these and
prints install commands. It installs nothing.

## Commands

| Command | Description |
|---|---|
| `/remotion:init [name]` | Create a project from Remotion's Blank template (`npx create-video --yes --blank`), install `@remotion/media` and `zod` with `npx remotion add`, copy the templates, and check that `npx remotion compositions` lists them. No name: proposes `my-video` and asks. |
| `/remotion:status` | Prerequisites, plus composition ids and narration status when run inside a Remotion project |
| `/remotion:render [id]` | Render a composition; no id lists them and asks |
| `/remotion:voice [--list [lang]] \| [--generate]` | List edge-tts voices, or run the narration pipeline |
| `/remotion` | Deprecated alias that routes to the four commands above; removed in the next minor version |

## Skills

| Skill | Loads when |
|---|---|
| `remotion-video` | Narration cuts between scenes, Audio inside Sequence, narration generation, MP3 concatenation, ms-to-frame timing, new Remotion project, rendering. Model-invoked only (`user-invocable: false`). |

The skill links the reference notes in `memories/` (audio patterns, scene
recipes, voices, troubleshooting) and the TSX files in `templates/`.

## Agents

None.

## Hooks

None. The plugin ships no hooks.

## Scripts

All run in place as `python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` from the
video project's root; outputs are relative to the current directory.

| Script | Does |
|---|---|
| `setup_check.py` | Checks Node, npm, Python, edge-tts, mutagen, pydub, ffmpeg; prints install commands |
| `generate_voice.py` | Text or `--scenes` JSON to MP3 via edge-tts; prints duration and frames (rounded up) as JSON. Scene ids must be `[A-Za-z0-9_-]`. |
| `concat_audio.py` | Joins MP3s into one track (pydub, then ffmpeg, then byte-level `simple`); prints per-segment start/end ms and frames as JSON. ffmpeg output is re-encoded at the inputs' sample rate; `simple` cannot add gaps and reports `gap_ms: 0`. |
| `measure_audio.py` | Measures an MP3 or a directory; validates against `--expected-ms` |
| `_common.py` | Shared dependency check and duration helper |

## Configuration

None. Scripts take CLI flags (`--fps`, `--voice`, `--rate`, `--pitch`, `--gap`,
`--method`). No userConfig, no environment variables.

## Platform support

| Platform | Status |
|---|---|
| Windows | Supported. `setup_check.py` suggests `winget` installs. |
| macOS | Supported (Homebrew suggestions). |
| Linux | Supported (distro package or nvm suggestions). |
| WSL | Works as Linux; rendering needs the Linux Chrome Headless Shell dependencies. |

## Data & privacy

- **edge-tts sends every narration string to Microsoft.** edge-tts is an
  unofficial client of Microsoft Edge's online read-aloud service. It is free to
  call but is not an official, SLA-backed or explicitly commercially licensed API.
  Do not narrate confidential or unreleased material you may not share with
  Microsoft. The skill says this before the first narration call.
- `npx create-video`, `npx remotion add` and the first render download packages
  and Chrome Headless Shell from the internet.
- Nothing is stored by the plugin. Audio, JSON and video files are written only
  to the paths you pass, inside your project.
- No API keys are read or stored. ElevenLabs appears only as an optional,
  unwired snippet in `memories/voice_reference.md`.

## Limitations

- Templates track the Remotion 4 API (`@remotion/media`, `zod`); a future
  Remotion release may need template updates.
- Rendering is CPU- and RAM-heavy (about half the cores by default; limit with
  `--concurrency`) and writes temporary frame data to disk.
- edge-tts needs network access and can be rate-limited or changed by Microsoft
  without notice.
- Byte-level `simple` concatenation cannot insert gaps; install pydub or ffmpeg
  for them.

## License

MIT (see `LICENSE`).

Third-party terms you must check yourself:

- **Remotion** is source-available, not open source. It is free for
  individuals, non-profits, for-profit organisations with up to 3 employees and
  for evaluation; other companies need a paid company licence:
  https://www.remotion.dev/license
- **edge-tts** is a third-party Python package (check its licence on PyPI)
  that talks to a Microsoft online service whose terms are Microsoft's; see
  Data & privacy above.

Author: TAQAT Techno, info@taqatechno.com
