# Changelog

All notable changes to the sprint-recap plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-22

### Added

- **`show_login: true` on a step** - records the sign-in itself as the opening
  scene. The step is built without the cached storage state, so the login
  screen actually renders, and the flow is driven from the target's `login`
  block plus the role's entry in `.sprint-recap.local.json`.

  This closes the only gap that would have forced a credential into
  `steps.yaml`: actions take literal strings, so spelling a sign-in out as
  `fill` actions meant a working password in a file that gets reviewed and
  shared. Credentials now stay in the config for this case too, and the
  existing redaction already scrubs them from console and network logs.

  The reproduction guide renders the step as "Sign in as <role>" pointing at
  the config key - never the password, because that page is the shareable one.

### Fixed

- **The credential commit gate blocked discussion, not just staging.** It
  matched the secret filenames against the whole Bash command, so a commit
  whose MESSAGE named the file was refused - including the commit that
  documents why the file must never be committed. It now matches only the
  part of a command that can name a path to stage: a heredoc body and an
  inline `-m` message are excluded. Every real staging path still blocks, and
  the tests pin both directions.

- A step could not start signed out. Every context was built with the role's
  storage state, so a step targeting `/login` was redirected away by the app
  before a frame was recorded - the clip showed a dashboard under a caption
  that said "sign in", silently.

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

### Verification

- **Eval suite (HR-20)** - 4 must-fire cases plus 1 must-not-fire, under
  `evals/`. The fire cases target `sprint-evidence-correlation` (a branch named
  `release/2026-planning` must not become work item 2026),
  `sprint-step-script` (the video and the written guide disagreeing),
  `sprint-capture-clips` (one continuous take with timestamp-positioned
  captions, plus the production and destructive-action gates) and
  `sprint-repro-guide` (logins written into a page that gets committed and
  shared). `sprint-video-overlays` is deliberately uncovered: it documents
  conventions for editing the generated render project rather than a question a
  user arrives with, so no natural prompt should route to it. The must-not-fire
  case is an ordinary product-explainer video request - video-adjacent, with no
  sprint, no evidence and nothing to reproduce.

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
