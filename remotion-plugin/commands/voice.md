---
description: Generate, list or preview edge-tts narration voices for the current Remotion project
argument-hint: '[--list [language]] | [--generate]'
---

# /remotion:voice

Use the `remotion-video` skill's Voice Generation workflow with `$ARGUMENTS`.

- No arguments or `--list [language]`: run
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate_voice.py" --list-voices` (add
  `--language <code>` when given) and show a short table. Where there is no
  `python3`, use `python`, then `py -3`.
- `--generate`: run the full narration pipeline from the skill.

edge-tts sends every narration string to Microsoft's online text-to-speech
service. Say so before the first generation in a session and do not narrate
text the user marked confidential without their go-ahead. Listing voices also
calls that service (no user text is sent), so mention it the first time you list.
