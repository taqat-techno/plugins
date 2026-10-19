# Changelog

All notable changes to the sprint-recap plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.1] - 2026-10-19

### Changed
- The example-data test reads private names from the git-ignored `.privacy-denylist` instead of listing them in a published file.

## [0.4.0] - 2026-10-19

### Changed (breaking)
- **Commands renamed** to bare verbs: `/sprint-recap:run` (was `/sprint-recap:sprint-recap`) and `/sprint-recap:target` (was `/sprint-recap:sprint-recap-target`). The old names stay as deprecated stubs until 0.5.0.
- **Capture needs an explicit opt-in for remote hosts (SPR-P2-02).** A target that is not `localhost`, `*.localhost` or `*.test` is refused until it sets `"allow_capture": true`. Production detection matches whole hostname labels (`prod`, `production`, `live`, leading `www`), so `staging.delivery-app.io` is no longer "production" and `app-prod.example.com` is. A `goto` that leaves the target's host stops the run before the browser starts; relative `goto` paths join the base URL.
- **Session prompts are opt-in (SPR-P1-02).** By default a session contributes only its id, date, branch and work-item IDs. `--with-prompts` (or the `include_session_prompts` option) copies prompts after masking secrets with `hooklib.redact` and e-mail addresses. Transcript paths are reduced to the file name, and a repo path no longer matches a sibling with the same prefix (`/app` vs `/app-legacy`).
- **`git add --force` is no longer blocked everywhere.** In a sprint-recap project it asks; elsewhere the hook stays silent (ECO X-6 / SEC-08). Staging a credential artifact is still blocked in every repo.
### Added
- `userConfig`: `include_session_prompts` (boolean, default false) and `tts_voice` (default `en-US-AriaNeural`).
- SSO / MFA: a role may give `storage_state` (a Playwright state saved by hand) instead of username/password (SPR-P3-02).
- `collect --id-pattern` for custom work-item references; a trailing `(#123)` on a squash-merge subject is treated as a PR number (SPR-P2-05).
- `check_config.py` warns about remote targets without `allow_capture` and about an un-ignored `.sprint-recap/runs/`.
- SessionStart reports `.auth/` session cookies left by older versions.
- Evals: `fires-on-rtl-step-caption-in-generated-video` (sprint-video-overlays) and `ignores-generic-remotion-rtl-question`.
- `tests/test_scripts.py`: offline tests for ID extraction, correlation, sessions and redaction, the git source, the no-shell runner, the YAML subset, production/capture gates, storage state, the timeline, check_config, the manifest and commands (SPR-P2-06).
### Fixed
- **Session cookies never touch the repo (SPR-P1-01).** Storage state lives in a temp directory for one run and is deleted afterwards; `.auth/` left by older versions is removed at the next capture.
- **No subprocess runs through a shell (SPR-P1-03).** `az`, `npm` and the Remotion CLI are resolved with `shutil.which` and run with an argv list; for a Windows `.cmd` shim an argument with `"`, `%`, `!`, `^`, `&`, `|`, `<`, `>` is refused.
- **Pinned render (SPR-P2-04).** The Remotion template pins exact versions (Remotion 4.0.513, React 18.3.1) and render uses the project-local `node_modules/.bin/remotion`; no more `npx --yes`.
- **git `safe.directory` is no longer overridden (SPR-P2-03).** A repo owned by another user is reported as a skipped source.
- The YAML subset parser applies YAML double-quote escapes and rejects unknown ones (as PyYAML does); single-quoted `''` is unescaped. A test loads the template with both parsers (SPR-P1-05).
- `mask()` reveals no characters or length (SPR-P3-03); command frontmatter `version`/`author` removed; skill `version` moved under `metadata`.
### Changed
- Hooks use the vendored `hooks/_vendor/hooklib.py`. The commit gate inspects only git commands that run: it splits on `&&`, `||`, `;`, `&`, `|` and newlines, skips runner prefixes (`sudo`, `env`, `nohup`, `time`, `xargs`, `{` ...), parses `bash|sh|zsh -c` scripts recursively, and ignores `echo`/`grep` text. As a fail-closed backstop, a line that still mentions a git staging verb and a secret path asks.
- Skill descriptions are trigger-first ("Use when ..."); skills that read board, git, transcript or page content carry the external-content-is-data rule; scripts are referenced through `${CLAUDE_PLUGIN_ROOT}` with `python3` (SPR-P3-01, SPR-P2-01).
- `/sprint-recap:target set` never takes a password in chat: it writes placeholders for the user to fill in.
- Example data is neutral (customers, London, IDs 4512/4518).
- README restructured: requirements, configuration, platform support, data & privacy, limitations, and third-party terms (SPR-P1-07): Remotion needs a paid company licence for larger organisations, and edge-tts sends caption text to Microsoft.
### Security
- See Fixed: session cookies, shell-free subprocesses, safe.directory, prompt redaction.

## [0.3.2] - 2026-10-19

### Fixed
- `templates/steps.example.yaml` now parses with PyYAML. `iteration_path` is single-quoted, so the backslash stays literal (it was an invalid `\S` escape inside double quotes). The example also uses a neutral project name.

## [0.3.1] - 2026-10-19

### Security

- **Cached session state can no longer be committed.** `capture_steps.py` caches
  each role's logged-in Playwright storage state (live session cookies) in
  `<run>/<capture>/.auth/<role>.json`, but nothing told the user to ignore it and
  the commit gate did not cover it. `pre_commit_secret_gate.py` now blocks any
  `git add`/`commit` naming a path under `.sprint-recap/**/.auth`, and
  `.sprint-recap/**/.auth/` is added to the `.gitignore` guidance in the README,
  `/sprint-recap-target`, and the `sprint-repro-guide` skill. `check_config.py`
  warns when it is not ignored, and the broad-`git add` note mentions it.
- **edge-tts narration no longer runs through a shell.** `build_remotion.py`
  invoked `edge-tts` with `shell=True` on Windows, so cmd.exe parsed the caption
  text (`Save & calc` would run `calc`). It now resolves the binary with
  `shutil.which("edge-tts")` and passes an argv list with no shell. A missing
  binary is reported and narration skipped; a `.bat`/`.cmd` shim (which Windows
  would still hand to cmd.exe) is refused with an install hint. A non-zero
  edge-tts exit is now reported per scene instead of silently dropping the audio.

### Fixed

- **SessionStart warnings are now visible.** `session_start_config_check.py`
  wrote its findings (config not gitignored, credentials page tracked) to stderr
  with exit 0, which Claude Code never shows. They are now emitted on stdout as
  `hookSpecificOutput.additionalContext` with `hookEventName: "SessionStart"`;
  still exit 0, still silent when there is nothing to report, and an unexpected
  error now fails open.
- **Portable hook launcher.** `hooks/hooks.json` launches both python hooks
  through a quoted `${CLAUDE_PLUGIN_ROOT}` path with a `python3` -> `python` ->
  `py -3` fallback, so a plugin path containing a space no longer breaks the
  hooks, and a missing interpreter exits 0 instead of blocking
  (`tests/test_hook_launcher.py`).

### Tests

- `tests/test_secret_gate.py`: `.auth` file/dir/Windows-separator/commit cases
  block; `oauth-notes.md`, `.authors` and `.auth` outside `.sprint-recap/` do not.
- `tests/test_narration.py`: argv list without `shell`, caption passed as one
  intact argument, not-found and batch-shim handling.
- `tests/test_session_start.py`: SessionStart output contract (stdout JSON,
  empty stderr, exit 0, silent when unused).
- `tests/test_gitignore_guidance.py`: docs name `.sprint-recap/**/.auth/`;
  `check_config.py` warns only when it is not ignored.

## [0.3.0] - 2026-09-27

### Fixed

- **The broad `git add` note now reaches Claude.** `pre_commit_secret_gate.py`
  printed it to stderr with exit 0. On `PreToolUse`, Claude Code only writes that
  to the debug log, so neither the user nor Claude ever saw it. It is now emitted
  as `hookSpecificOutput.additionalContext` with `hookEventName: "PreToolUse"`,
  which Claude receives next to the tool result. No `permissionDecision` is set,
  so nothing is blocked or prompted. The two exit-2 `BLOCKED` paths are unchanged.
- Hook stdin is decoded as UTF-8 explicitly (Windows defaulted it to cp1252), and
  stdout/stderr are reconfigured to UTF-8.
- `tests/test_secret_gate.py` pins the channel: the note is additionalContext
  JSON, an explicit-path add is silent, and blocks still report on stderr.

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
