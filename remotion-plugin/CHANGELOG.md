# Changelog

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
