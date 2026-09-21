# Changelog

All notable changes to the sprint-recap plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-21

Initial release.

### Added

- **Five-stage resumable pipeline** (`collect`, `script`, `capture`, `render`,
  `publish`) with artifacts under `.sprint-recap/runs/<sprint>/`. Each stage
  re-runs independently, so a caption fix does not mean re-recording the browser.
- **`/sprint-recap`** — runs the pipeline, stopping at the approval gate after
  drafting the step script.
- **`/sprint-recap-target`** — manages environments, the login flow selectors and
  role credentials in `.sprint-recap.local.json`; never prints a password unmasked.
- **Evidence correlation** across Azure DevOps iteration items, git commits and
  Claude session transcripts, joined on work-item ID. Explicit `#23923` and
  branch-style `feature/23923-x` references are recognised; bare year-like
  numbers are rejected so `release/2026-planning` cannot invent work item 2026.
  Each source degrades independently and reports its own status.
- **`steps.yaml` contract** — one `caption` per step, consumed by the video
  overlay, the HTML guide and the narration, so the artifacts cannot drift apart.
- **Per-step clip capture** via Playwright: each step records in its own browser
  context, so a caption is pinned to a clip instead of to a timestamp. Login is
  captured once per role via storage state rather than re-recorded per step.
- **Remotion render** with burned-in step text, work-item badges, step counters,
  RTL handling for Arabic captions, and optional edge-tts narration. Clip
  durations are measured via ffprobe, Remotion's bundled ffprobe, or wall-clock
  as a last resort with an explicit warning.
- **HTML reproduction guide** with embedded screenshots, Playwright actions
  rendered as human instructions, and honest per-step status badges
  (verified / not verified - capture failed / not captured - destructive action).
- **Two-file credential policy** — the shareable guide contains no secrets and
  points at config keys; the plaintext credentials page is written only with
  `--with-credentials`, into a gitignored directory, and is never bundled with
  the video.

### Safety

- Production-looking base URLs are refused unless `--allow-production` is passed.
- Destructive-looking selectors are skipped unless a step sets
  `allow_destructive: true`.
- Passwords are redacted from console output and failed request URLs before they
  reach the capture log.
- `PreToolUse` hook blocks git from staging `.sprint-recap.local.json`,
  `.sprint-recap/credentials/**` or any `*-credentials.html`, including via
  `git add --force`; broad `git add -A` gets a warning.
- `SessionStart` hook reports a tracked or un-ignored config, and leftover
  plaintext credential pages.

### Notes

- `collect`, `render` and `publish` run on a bare Python 3.9+; a built-in YAML
  subset parser removes the PyYAML requirement. Only `capture` needs Playwright.
