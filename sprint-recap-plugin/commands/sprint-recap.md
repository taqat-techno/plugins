---
description: Turn a finished sprint into a narrated walkthrough video of the real app plus a matching HTML reproduction guide. Runs in resumable stages (collect, script, capture, render, publish) with a human approval gate before anything touches a browser.
argument-hint: "[collect | script | capture | render | publish | all] [--sprint \"Sprint 24\"]"
author: TAQAT Techno
version: 0.1.0
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /sprint-recap

Produce the sprint review artifacts: an MP4 walkthrough of the real application
with step text burned in, and an HTML guide that lets someone reproduce every
step by hand.

`$ARGUMENTS` selects the stage. With no argument, run `collect` then `script`
and stop at the approval gate.

## The contract

Everything downstream reads `02-script/steps.yaml`. Each step's `caption` is
written once and consumed three times — as the on-screen video text, as the
numbered instruction in the HTML guide, and as the narration line. Never write
the caption text into the video and the guide separately; that is how the two
artifacts drift apart.

## Stages

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/`. Run them with `python`.
Artifacts land in `.sprint-recap/runs/<sprint>/`.

### 1. collect (read-only)

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/collect_evidence.py" \
  --sprint "Sprint 24" --since 2026-09-01 --until 2026-09-14 \
  --iteration-path "Project\\Sprint 24" --repos "D:\\codes\\app,D:\\codes\\api"
```

Correlates Azure DevOps work items, git commits and Claude session transcripts
on work-item ID. Each source degrades on its own — report what was actually
collected rather than implying full coverage. Read `sources` in the output and
tell the user plainly if `az` was unavailable.

### 2. script (you draft, the user approves) — THE GATE

Read `01-collect/evidence.json` and write `02-script/steps.yaml`
(see `${CLAUDE_PLUGIN_ROOT}/templates/steps.example.yaml`).

Rules for a good step script:

- A **step is a unit of narration, not a single click**. "Search, export, confirm
  the toast" is one step with four actions and one caption.
- Every step needs a `start` URL. That is what makes its clip self-contained and
  the step independently re-runnable.
- Write captions for a stakeholder, not for a tester: "Export the filtered donors
  to CSV", not "click #export-btn".
- Only include work items with a real UI surface. A refactor or a pipeline fix
  has nothing to show — say so instead of inventing a flow for it.
- Never guess a selector. If the evidence does not reveal one, mark the step and
  ask, or leave the item out.

**Then STOP.** Show the user the drafted steps and wait for approval. Do not run
the capture stage in the same turn you drafted the script — it drives a real
application with real credentials.

Validate without a browser at any time:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/capture_steps.py" --steps <steps.yaml> --dry-run
```

### 3. capture (drives the real app)

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/capture_steps.py" --steps <steps.yaml>
```

Requires Playwright (`pip install playwright && python -m playwright install chromium`).
Records one clip per step, plus a screenshot, console errors and failed requests.

Safety, non-negotiable:
- Production-looking URLs are refused. Do not pass `--allow-production` on the
  user's behalf; ask first.
- Destructive-looking actions are skipped unless the step sets
  `allow_destructive: true`. Do not set that flag yourself — raise it with the user.
- A failed step does not abort the run. It is reported as failed, excluded from
  the video, and shown in the guide as "not verified". Never present a failed
  step as if it worked.

### 4. render

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_remotion.py" \
  --capture-log <capture-log.json> --install --render
```

Add `--narrate` for edge-tts voice-over. If clip durations could not be measured,
the script says so — pass that warning on rather than quietly shipping captions
whose timing is approximate.

### 5. publish

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/publish_guide.py" \
  --capture-log <capture-log.json> --video <path-or-url>
```

Writes the shareable guide. It contains no passwords by design: it names the role
each step needs and points at the config key holding that role's login.

Add `--with-credentials` **only when the user asks** for the plaintext page. It
is written to `.sprint-recap/credentials/` (gitignored) and must never be bundled
with the video or attached to a ticket. Say where it landed and remind the user
to delete it after the review.

## Reporting

Close with what was actually produced: steps captured vs. failed, the video path
and duration, the guide path, and anything left out. If a work item has no
demonstrable UI, list it as covered-by-commits-only rather than silently dropping it.
