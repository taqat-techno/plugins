# sprint-recap

## What it does

Turns a finished sprint into two artifacts stakeholders can use: **a walkthrough video
of the real application** with the step text burned in, and **an HTML reproduction
guide** so anyone can redo those exact steps by hand. Both come from one step script,
so the video and the guide cannot describe a step differently.

It is for teams that hold sprint reviews of a web application with a staging
environment. It reads the evidence you already have: the Azure DevOps board (optional),
the git history, and your Claude Code sessions.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install sprint-recap@taqat-techno-plugins
```

## Requirements

| Requirement | Stage | Check |
|-------------|-------|-------|
| Python 3.9+ (`python3`, `python` or `py -3`) | all scripts and hooks | `python3 --version` |
| git | collect | `git --version` |
| Playwright + Chromium | capture only | `python3 -m playwright --version`; install with `pip install playwright` and `python3 -m playwright install chromium` |
| Node.js 18+ and npm | render only | `node --version`; `render --install` runs `npm install` with the exact versions pinned in `templates/remotion/package.json` (Remotion 4.0.513, React 18.3.1) |
| Azure CLI + `azure-devops` extension (optional) | collect: board items | `az extension show --name azure-devops` |
| PyYAML (optional) | full YAML; a strict subset parser is built in | `python3 -c "import yaml"` |
| edge-tts (optional) | `render --narrate` | `edge-tts --version`; `pip install edge-tts` |
| ffmpeg / ffprobe (optional) | frame-accurate clip durations | `ffprobe -version` |

`collect`, `render` (without `--render`) and `publish` run on a bare Python 3.9+.

## The pipeline

Five resumable stages; artifacts land in `.sprint-recap/runs/<sprint>/`.

```
01-collect/evidence.json     Azure DevOps + git + Claude sessions, correlated on work-item ID
02-script/steps.yaml         the contract  <-- YOU APPROVE THIS before anything opens a browser
03-capture/                  one clip + screenshot per step
04-render/                   generated Remotion project + MP4
05-publish/                  the shareable HTML guide
```

Each `caption` in `steps.yaml` is written once and used three times: on-screen text,
guide instruction and narration line. Each step gets its own browser context, so a
caption is pinned to a clip, not to a timestamp. See `templates/steps.example.yaml`.

## Commands

| Command | What it does |
|---------|--------------|
| `/sprint-recap:run [collect\|script\|capture\|render\|publish\|all]` | Runs the pipeline. With no argument it runs `collect` then `script` and stops at the approval gate |
| `/sprint-recap:target [check\|set\|show]` | Manages `.sprint-recap.local.json` (environments, login flow, roles). No argument runs the read-only `check` |
| `/sprint-recap:sprint-recap`, `/sprint-recap:sprint-recap-target` | Deprecated aliases of the two commands above; removed in 0.5.0 |

## Skills

| Skill | Loads when |
|-------|-----------|
| `sprint-step-script` | Drafting or reviewing `steps.yaml`, or the video and the guide disagree |
| `sprint-evidence-correlation` | Running collect, or evidence looks incomplete or wrongly attributed |
| `sprint-capture-clips` | Running or debugging capture: drifting captions, login on camera, refused or skipped steps |
| `sprint-video-overlays` | Editing the generated Remotion project, caption timing, right-to-left captions |
| `sprint-repro-guide` | Publishing the guide or handing logins to a reviewer |

## Agents

None.

## Hooks

| Hook | Event | What it does | Can block? |
|------|-------|--------------|-----------|
| `session_start_config_check.py` | SessionStart (`startup`) | Only in a project that uses sprint-recap: reports a tracked or un-ignored `.sprint-recap.local.json`, credential pages present or tracked, and leftover `.auth/` session cookies from older versions, as context for Claude. Silent otherwise | No |
| `pre_commit_secret_gate.py` | PreToolUse (`Bash`) | Looks only at git commands that will run (not at `echo`, `grep`, commit messages or heredoc bodies). Blocks staging of `.sprint-recap.local.json`, `.sprint-recap/credentials/**`, `*-credentials.html` and `.sprint-recap/**/.auth/` in any repository. In a sprint-recap project it also asks before `git add --force` and adds a note on a broad `git add -A` | Yes: staging a credential artifact (exit 2). `git add --force` gets an ask, not a block |

## Configuration

**Plugin options** (`/config`):

| Option | Default | Meaning |
|--------|---------|---------|
| `include_session_prompts` | `false` | When true, collect copies up to 12 prompts per matching session into `evidence.json`, with secrets and e-mail addresses masked |
| `tts_voice` | `en-US-AriaNeural` | edge-tts voice for `render --narrate` |

**Per-project file** `.sprint-recap.local.json` at the project root (written by
`/sprint-recap:target set`; you type the passwords into the file yourself, never into
the chat):

```json
{
  "targets": {
    "staging": {
      "base_url": "https://staging.example.com",
      "allow_capture": true,
      "login": { "path": "/login", "username_selector": "input[name='username']",
                 "password_selector": "input[name='password']",
                 "submit_selector": "button[type='submit']", "success_selector": "text=Dashboard" },
      "roles": {
        "qa_admin": { "username": "qa.admin@example.com", "password": "..." },
        "sso_user": { "storage_state": "~/secrets/staging-sso-user.json" }
      }
    }
  },
  "production_markers": ["prod", "production", "live"]
}
```

- `allow_capture: true` is required for any target that is not `localhost`,
  `*.localhost` or `*.test`. Add it only for a disposable test environment.
- Production detection matches whole hostname labels (`prod`, `production`, `live`,
  a leading `www`); `production_markers` replaces that with your own substrings.
- `storage_state` lets an SSO or MFA account use a Playwright storage state you saved
  after signing in by hand. Keep that file outside the repository.

**Script flags worth knowing:** `collect --with-prompts`, `--no-sessions`, `--no-azure`,
`--id-pattern 'PROJ-(\d+)'`; `capture --dry-run`, `--allow-production`;
`render --install --render --narrate --voice`; `publish --with-credentials`.

**`.gitignore`** before the first run:

```
.sprint-recap.local.json
.sprint-recap/
```

`.sprint-recap/` holds evidence, screenshots, clips and, with `--with-credentials`, a
plaintext credentials page. If you prefer to ignore only the secrets, list at least
`.sprint-recap/credentials/` and `.sprint-recap/**/.auth/` (session cookies left by
versions before 0.4). Commit only the guide you mean to share.

## Platform support

| Platform | Status |
|----------|--------|
| Windows | Supported. Hooks run through Git Bash (`py -3` fallback). No subprocess runs through a shell; `npm`, `npx` and `az` are `.cmd` shims there, so an argument containing `"`, `%`, `&`, `|`, `<`, `>`, `^` or `!` is refused rather than handed to cmd.exe. edge-tts must be an `.exe` (`pip install edge-tts`) |
| macOS | Supported (`python3`) |
| Linux | Supported |
| WSL | Works, but collect reads transcripts from the WSL home's `~/.claude/projects`; sessions run by Windows Claude Code are not found there |

## Data & privacy

| Data | Where | Leaves the machine? |
|------|-------|---------------------|
| Role usernames and passwords | `.sprint-recap.local.json` (keep it gitignored) | Typed into the target app's login form during capture |
| Session cookies | A temporary directory for one capture run, deleted when it ends | No |
| Evidence: work-item titles, commit subjects and file names, session ids, dates and branches; prompt text only with `--with-prompts` (masked) | `.sprint-recap/runs/<sprint>/01-collect/evidence.json` | No |
| Screenshots, clips, console errors, failed request URLs (passwords redacted) | `.sprint-recap/runs/<sprint>/03-capture/` | No |
| Credentials page (only with `--with-credentials`) | `.sprint-recap/credentials/` | No; never bundle it with the video |
| Caption text, with `--narrate` | Microsoft's online read-aloud service | **Yes.** edge-tts is an unofficial client of Microsoft Edge's read-aloud service. Do not narrate confidential or unreleased material |
| npm packages | `04-render/node_modules` | Downloaded from the npm registry by `render --install` |

Collect reads your local Claude Code transcripts (`~/.claude/projects/*/*.jsonl`) for
the sprint window and the repositories you name. Board items, commit messages, pages
the capture visits and transcript text are treated as data: instructions found in them
are reported, never followed.

## Limitations

- A step that fails capture stays failed: excluded from the video, shown in the guide
  as "not verified".
- Work items with no UI (refactors, pipelines) are reported as covered-by-commits-only.
- Without ffmpeg, clip durations fall back to wall-clock timing (warned).
- Correlation needs work-item IDs in branches or commits (`#1234`, `feature/1234-x`, or
  your own `--id-pattern`); a trailing `(#123)` on a squash-merge subject is treated as
  a PR number. Years in branch names are ignored.
- Repositories owned by another OS user are skipped (git's safe.directory check stays on).
- The login flow fills a form; SSO, MFA and CAPTCHA logins need a saved `storage_state`.
- The transcript format is Claude Code's internal JSONL, which may change.
- No `package-lock.json` is shipped: versions are pinned exactly in `package.json`, but
  their transitive dependencies are resolved by npm at install time.

## License

MIT (`LICENSE`).

Third-party terms you must check yourself:

- **Remotion** is source-available, not open source. It is free for individuals,
  non-profits, for-profit organisations with up to 3 employees and for evaluation;
  other companies need a paid company licence: https://www.remotion.dev/license
- **edge-tts** is a third-party Python package that talks to a Microsoft online
  service whose terms are Microsoft's; see Data & privacy.
- **Playwright** (Apache-2.0) and its downloaded Chromium build are installed by you.
