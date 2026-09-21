# sprint-recap

Turn a finished sprint into two artifacts your stakeholders can actually use:

- **a walkthrough video of the real application**, with the step text burned in
- **an HTML reproduction guide**, so anyone can redo those exact steps by hand

Both are generated from one step script, so the video and the written guide can
never describe a step differently.

---

## Why this exists

A sprint review usually produces either a screen-share nobody recorded or a wiki
page nobody follows. This plugin produces both from the same source, and does it
from evidence you already have: the board, the commit history, and the sessions
where the work was done.

## The pipeline

Five resumable stages. Artifacts land in `.sprint-recap/runs/<sprint>/`.

```
01-collect/evidence.json     Azure DevOps + git + Claude transcripts, correlated
02-script/steps.yaml         the contract  <-- YOU APPROVE THIS
03-capture/                  one clip + screenshot per step
04-render/                   generated Remotion project + MP4
05-publish/                  the shareable HTML guide
```

Each stage is re-runnable on its own: a failed capture does not mean re-querying
the board, and a caption fix does not mean re-recording the browser.

### The approval gate

Stage 2 stops. Claude drafts the step script from the collected evidence and
waits — because stage 3 drives a real application with real credentials, and
board titles rarely describe a click-path well enough to trust blindly.

## The contract

`steps.yaml` is the single source of truth:

```yaml
sprint: "Sprint 24"
target: staging
items:
  - work_item: 23923
    title: "Add donor export to the admin list"
    parent_pbi: 23900
    role: qa_admin
    steps:
      - id: s1
        caption: "Export the filtered donors to CSV"
        start: "/admin/donors"
        hold_ms: 1500
        actions:
          - { do: fill, selector: "input[name='search']", value: "Cairo" }
          - { do: click, selector: "role=button[name='Export']" }
          - { do: expect, selector: "text=Export started" }
```

Each `caption` is written **once** and used **three times**: as the on-screen
video text, as the numbered instruction in the HTML guide, and as the narration
line. That is the whole anti-drift mechanism.

A **step is a unit of narration, not a single click** — the example above is one
step with three actions, not three steps. And every step declares `start`, a URL,
which is what makes its clip self-contained.

## One clip per step

Playwright starts a video when a page is created and finalises it when the
context closes. Each step therefore gets its own context, and its clip's
boundaries are exactly the step's boundaries.

That means a caption is pinned to a **clip**, not to a timestamp on a long
recording. Caption drift stops being a timing problem you have to watch the whole
video to catch, and becomes structurally impossible.

## Credentials

Two files, deliberately separate:

| File | Contains | Shareable |
|---|---|---|
| `05-publish/sprint-<id>-guide.html` | steps, screenshots, role names, config key pointers | yes |
| `.sprint-recap/credentials/<id>-credentials.html` | real usernames and passwords | no |

The guide contains no secret. It names the role each step needs and points at the
config key holding that login. The plaintext page is written only when you pass
`--with-credentials`, into a gitignored directory, and is never bundled with the
video.

A single convenient file with working logins gets emailed, Slacked and
screen-shared — and `.gitignore` protects none of those. Separating them makes
handing over credentials a deliberate act.

A `PreToolUse` hook blocks git from staging either secret artifact, including via
`git add --force`.

## Commands

| Command | Purpose |
|---|---|
| `/sprint-recap [stage]` | run the pipeline (`collect`, `script`, `capture`, `render`, `publish`, `all`) |
| `/sprint-recap-target [check\|set\|show]` | manage environments, login flow and role credentials |

## Setup

```bash
# capture stage only
pip install playwright
python -m playwright install chromium

# render stage only (Node 18+)
# handled automatically by build_remotion.py --install

# optional
pip install pyyaml      # full YAML; a subset parser is built in
pip install edge-tts    # voice narration via --narrate
# ffmpeg on PATH gives frame-accurate clip durations
```

`collect`, `render` and `publish` run on a bare Python 3.9+. Only `capture` needs
a third-party package.

Then configure the target:

```
/sprint-recap-target set
```

Add to `.gitignore` before the first run:

```
.sprint-recap.local.json
.sprint-recap/credentials/
```

## Skills

| Skill | Owns |
|---|---|
| `sprint-step-script` | the contract, caption rules, step granularity |
| `sprint-evidence-correlation` | the work-item join key, per-source degradation |
| `sprint-capture-clips` | per-step recording, safety gates, failed-step honesty |
| `sprint-video-overlays` | scene model, caption composition, RTL |
| `sprint-repro-guide` | the credential split, instruction rendering, status badges |

## Honest limits

- **A step that fails capture stays failed.** It is excluded from the video and
  shown in the guide as "not verified", with the error. It is never presented as
  working.
- **Work items with no UI** (refactors, pipelines, dependency bumps) have nothing
  to demonstrate and are reported as covered-by-commits-only.
- **Without ffmpeg**, clip durations fall back to wall-clock timing and captions
  may be off by a few frames. The build warns when this happens.
- **Transcript evidence is local** to the machine that ran the sessions.
- **Correlation depends on work-item IDs** appearing in branches or commits. A
  team that does not reference them will see most commits land in
  `unattributed`, and the step script will need manual scoping.

## License

MIT
