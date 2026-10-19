# Changelog

## [3.0.0] - 2026-10-19

Major: the `/remotion` command is split into verb commands, and concat output
changes (ffmpeg mode re-encodes; simple mode reports no gaps).

### Added
- `/remotion:init [name]` with an explicit procedure (RMT-P0-02): prerequisite
  check, refuse-or-ask on an existing directory, Remotion licence and Chrome
  download notice, `npx create-video@latest --yes --blank`, `npx remotion add
  @remotion/media zod`, copy of all four `templates/` into `src/`, and a
  `npx remotion compositions` check. Bare invocation proposes `my-video`.
- `/remotion:status`, `/remotion:render`, `/remotion:voice`.
- The skill now links every `memories/` note and the `templates/` directory as
  progressive-disclosure references.
- Render resource notes: Chrome Headless Shell download, CPU/RAM use,
  `--concurrency`, draft frame ranges (RMT-P3-09).
- `tests/test_scripts.py`: 25 offline pytest cases covering every script
  (concat timing in all three modes, ffmpeg argv, quote escaping, frame
  rounding, scene-id validation, measurement, dependency check, setup check).
  `tests/test_paths.py` also checks that init copies every template and the skill
  links every memory file.

### Changed
- `/remotion` is now a deprecated stub that routes to the new commands; it is
  removed in the next minor version.
- Skill description rewritten to 1,024 characters or fewer, starting "Use
  when"; `<example>` blocks removed; `last_reviewed` moved under `metadata`.
- `templates/Root.tsx` no longer imports a Tailwind `index.css` the Blank
  template does not have.
- README restructured to the marketplace template (requirements, scripts,
  platform support, data & privacy, limitations, licences) (RMT-P1-05).
- `generate_voice.py` rounds `duration_frames` up with `math.ceil`, matching
  `measure_audio.py` and the skill (it overcounted by one frame on exact
  multiples).

### Fixed
- **Concat timing in simple mode** (RMT-P1-04): byte-level concatenation cannot
  insert gaps but still added `--gap` to every timestamp, so scene N's visuals
  drifted `gap*(N-1)` ms from the audio. Timestamps are now cumulative durations
  and the JSON reports `gap_ms: 0`.
- **ffmpeg concat format mismatch** (RMT-P1-04): silence was generated at
  44.1 kHz and stream-copied next to 24 kHz edge-tts audio. Silence now matches
  the first input's sample rate and channel layout, the output is re-encoded with
  libmp3lame, every ffmpeg return code is checked, temporary files live in a
  per-run directory, and `'` in paths is escaped for the concat list.
- `--gap` below zero is rejected.
- The plugin no longer advertises ElevenLabs in skill metadata; the memory note
  marks it as an unwired, optional snippet (RMT-P2-08).

### Security
- Discloses that edge-tts sends narration text to Microsoft's online service and
  that Remotion needs a company licence for larger for-profit organisations, in
  the README, skill, `/remotion:voice` and `generate_voice.py` (help text plus a
  stderr notice on each run) (RMT-P1-03).
- Scene ids from `--scenes` JSON must match `[A-Za-z0-9_-]{1,64}`; `../` ids are
  rejected before any network call (RMT-P2-07).
- `setup_check.py` no longer suggests piping a remote script into `sudo bash`;
  it suggests the distro package or nvm (RMT-P2-07).

### Removed
- The empty `hooks/hooks.json` (ECO-P3-02).

## [2.2.3] - 2026-10-19

### Changed
- Added `"license": "MIT"` to plugin.json.

## [2.2.2] - 2026-10-19

**The voice pipeline commands now run from the user's project** (RMT-P0-01).
`skills/remotion/SKILL.md` told Claude to run `python scripts/generate_voice.py`,
`concat_audio.py`, `measure_audio.py` and `setup_check.py` by relative path,
saying the scripts were "copied from plugin" - nothing ever copied them, so from a
video project's directory every command failed. Each invocation now uses
`python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (the scripts already locate
`_common.py` relative to themselves), the project tree no longer shows a copied
`scripts/` folder, and the skill states that output paths are relative to the
current directory.

README no longer claims things that do not ship: the "5 PostToolUse safety
hooks" line is gone (`hooks/hooks.json` is empty), templates are described as
reference-only rather than "copied during setup", `/remotion [name]` says there is
no scripted init step yet, the structure tree shows `skills/remotion/SKILL.md`
and `tests/`, the header version is current, and the placeholder
`support@example.com` contact is replaced with `info@taqatechno.com`.

- Added `tests/test_paths.py` (offline, stdlib `unittest`): every concrete
  `${CLAUDE_PLUGIN_ROOT}/...` reference resolves to a file, the skill references
  all four pipeline scripts, and no bare `python scripts/...` invocation remains.
  Run with `python -m unittest discover -s tests -v`.

## [2.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (1 must-fire case + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-narration-audio-cuts-between-scenes` targets `remotion`
- `ignores-ffmpeg-merge-mp4-files` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [2.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

**Restored an undiscovered skill.** `remotion/SKILL.md` sat outside `skills/` and was never loaded. Moved to `skills/remotion/` (git mv) and renamed to `remotion-video` to clear a collision with `commands/remotion.md`; `/remotion` remains the user entry point (`user-invocable: false`).

## v2.1.0 (2026-03-23)

### Architecture Revision

**Hooks:**
- Fixed broken hook #2 (Audio-inside-Sequence guard) — old matcher tried to match file content which PostToolUse never sees. Now matches `.tsx`/`.jsx` file writes.
- Improved render hook matcher to catch both `npx remotion render` and `npm run render`.
- Added new hook: Timeline JSON validation reminder on write.
- Updated all hook messages to remove hardcoded script paths.

**Scripts:**
- Created `scripts/_common.py` — shared dependency checker and audio duration utility, eliminating duplication across 3 scripts.
- Fixed `generate_voice.py`: added `--fps` parameter (was hardcoded to 30), added retry logic with exponential backoff for edge-tts network failures.
- Moved `scripts/` and `templates/` from `remotion/` to plugin root for clearer separation of concerns.

**Skill:**
- Trimmed SKILL.md from 980 lines to ~200 lines (79% reduction).
- Removed: generic Remotion API docs, composition patterns, voice tables, troubleshooting, TailwindCSS integration, changelog — all moved to memory files or removed.
- Kept: continuous audio pattern, frame formula, prerequisites, project structure.
- Added: render and voice workflow instructions (absorbed from removed command sub-routes).
- Removed unsupported frontmatter attributes (version, author, category, tags, allowed-tools).

**Commands:**
- Simplified `/remotion` to init/setup only (~120 lines, down from ~400).
- Removed `render` and `voices` sub-commands — now handled by skill via natural language.

**Memory files:**
- Created `memories/troubleshooting.md` — common issues, audio debugging checklist, performance tips.
- Created `memories/voice_reference.md` — voice tables, rate/pitch control, SSML, script writing tips.

**Documentation:**
- Updated README.md with new structure, extension guide, and natural language workflow examples.

## v1.0.0 (2026-02-16)

### Initial Release

**Core Features:**
- Continuous Audio Pattern - voice narration never cuts between slides
- Free voice generation via edge-tts (300+ Microsoft Neural voices, 70+ languages)
- Full video creation pipeline from text prompts
- Cross-platform support (Windows, macOS, Linux)

**Commands (5):**
- `/remotion` - Main entry point with status and help
- `/remotion-setup` - Project scaffolding with all dependencies
- `/create-video` - Full pipeline: prompt to video with voice narration
- `/render-video` - Render with quality presets (draft/balanced/high/max)
- `/add-voice` - Add narration to existing compositions

**Python Scripts (4):**
- `setup_check.py` - Prerequisites checker with platform-specific install commands
- `generate_voice.py` - edge-tts voice generation with batch mode support
- `concat_audio.py` - Audio concatenation with segment timestamps (pydub/ffmpeg/simple)
- `measure_audio.py` - Audio duration measurement and frame validation

**Composition Templates (4):**
- `composition_continuous_audio.tsx` - The correct pattern with single root audio
- `composition_multi_scene.tsx` - Data-driven multi-scene with timeline.json
- `Root.tsx` - Root registration with static and dynamic duration patterns
- `timeline_schema.ts` - Zod schemas for timeline data validation

**Memory Files (2):**
- `audio_patterns.md` - Continuous audio pattern documentation and anti-patterns
- `composition_patterns.md` - Reusable scene component recipes and color schemes

**Hooks (4):**
- Post-render audio validation reminder
- Continuous audio pattern guard (warns if Audio inside Sequence)
- Voice generation duration measurement reminder
- Audio concat timestamp usage reminder

### Issues Prevented

1. **Audio cutting between slides** - Solved by continuous audio pattern
2. **Frame rounding errors** - Enforced Math.ceil() in all calculations
3. **Duration mismatches** - Audio validation script catches discrepancies
4. **Missing dependencies** - Setup checker reports exact install commands
