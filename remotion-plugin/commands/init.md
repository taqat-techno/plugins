---
description: Create a new Remotion video project wired for continuous narration audio
argument-hint: '[project-name]'
---

# /remotion:init - new narrated-video project

Create a Remotion project in `./<project-name>` and copy in the plugin's
continuous-audio templates. With no argument, propose `my-video` and ask the user
to confirm or give another name before creating anything.

Follow these steps in order. Stop and report if any step fails.

1. **Check prerequisites.** Run
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/setup_check.py"`. Node.js 18+ and npm
   are required for this command; the Python packages are only needed later for
   narration. If Node or npm is missing, show the install line the script printed
   and stop. Do not install system packages yourself.
2. **Check the target.** If `./<project-name>` already exists, do not touch it:
   ask the user for another name or for explicit permission to use the existing
   directory.
3. **Tell the user, once, before creating the project:**
   - Remotion is source-available, not open source. It is free for individuals,
     non-profits, for-profit organisations with up to 3 employees, and for
     evaluation; other companies need a Remotion company licence
     (https://www.remotion.dev/license).
   - The first render downloads Chrome Headless Shell (roughly 100 MB or more).
4. **Create the project** (non-interactive, Blank template, as Remotion's docs
   recommend for Claude Code):
   ```bash
   npx create-video@latest --yes --blank <project-name>
   ```
   If the CLI rejects the flags (older `create-video`), ask the user to run
   `npx create-video@latest` themselves in a terminal, choose the Blank template,
   and then re-run this command with the same name to continue from step 5.
5. **Install the packages the templates import**, at the versions that match the
   project's Remotion version:
   ```bash
   cd <project-name> && npx remotion add @remotion/media zod
   ```
6. **Copy the templates** from `${CLAUDE_PLUGIN_ROOT}/templates/` (create the
   directories first; replace the Blank template's `src/Root.tsx`):

   | Template | Destination in the project |
   |---|---|
   | `${CLAUDE_PLUGIN_ROOT}/templates/Root.tsx` | `src/Root.tsx` |
   | `${CLAUDE_PLUGIN_ROOT}/templates/composition_continuous_audio.tsx` | `src/compositions/ContinuousAudioVideo.tsx` |
   | `${CLAUDE_PLUGIN_ROOT}/templates/composition_multi_scene.tsx` | `src/compositions/MultiSceneVideo.tsx` |
   | `${CLAUDE_PLUGIN_ROOT}/templates/timeline_schema.ts` | `src/lib/types.ts` |

   Also create `public/audio/` and `public/content/`. Keep any other file the
   Blank template created (`src/index.ts` registers `RemotionRoot` from `./Root`).
7. **Verify.** Run `npx remotion compositions` in the project. It must list
   `ContinuousAudioVideo`, `MultiSceneVideo` and `PortraitVideo`. Fix type or
   import errors before reporting success.
8. **Report** the project path, the three compositions, and the next steps:
   `npm run dev` to open Remotion Studio, then describe the video in plain
   language. The compositions play `public/audio/narration.mp3`, which the
   narration workflow in the `remotion-video` skill creates; until it exists,
   rendering `ContinuousAudioVideo` fails with a missing-file error.
