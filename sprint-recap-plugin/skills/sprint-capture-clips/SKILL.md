---
name: sprint-capture-clips
description: Why sprint-recap records one browser clip per step instead of one continuous take, and the safety discipline the capture stage runs under. Owns the per-step-context recording model, storage-state reuse for login, the production gate, the destructive-action gate, and honest handling of failed steps. Use when running or debugging the capture stage.
version: 0.2.0
last_reviewed: 2026-09-22
owns:
  - per-step context recording and why captions cannot drift
  - storage-state reuse so login is captured once, not per step
  - the show_login step that records the sign-in without putting a password in steps.yaml
  - production and destructive-action gates
  - failed-step reporting discipline
defers_to:
  - sprint-step-script (what the steps are)
  - sprint-video-overlays (how captions are drawn)
---

# One clip per step

Playwright starts a video when a **page** is created and finalises it when the
context closes. Giving each step its own context therefore produces a clip whose
boundaries are exactly that step's boundaries.

This is the design's load-bearing decision. With one long recording, captions
have to be placed by timestamp, and any retry, network stall or slow render
desynchronises text from footage — silently. You would only catch it by watching
the entire video. With one clip per step, a caption is bound to a clip rather
than to a moment in time, so **drift is structurally impossible** rather than
merely unlikely.

The cost is that each step must start on its own, which is why the schema
requires `start`. Authentication is carried across steps by storage state
captured once per role, so the login flow is not re-recorded into every clip.

## Recording the sign-in on purpose

Storage-state reuse means the login screen is never on camera — which is right
for every step except an opening one that is *about* signing in. A step with
`show_login: true` is built **without** the cached session, so the login screen
actually renders; the flow is then driven from the `login` block and the role's
entry in `.sprint-recap.local.json`.

Two consequences follow, and both are the point:

- **The credentials stay in the config.** Actions take literal strings, so
  spelling the sign-in out as `fill` actions would put a working password in
  `steps.yaml` — a file that gets reviewed, diffed and pasted into chat.
  `show_login` exists so that never has to happen.
- **It must start signed out.** Give the step the cached session and the app
  redirects away from `/login` before a frame is recorded, so the clip shows a
  dashboard under a caption that says "sign in". That failure is silent, which
  is why the flag controls the context rather than just the actions.

Use it once, as the first item. A second `show_login` step re-records a sign-in
the viewer has already watched. If the sprint has nothing to show about
authentication, leave it out and open on the first real screen — a title card
naming the role carries the same information in less time.

## Duration is measured, never assumed

Clip length comes from `ffprobe`, else Remotion's bundled ffprobe, else the
wall-clock time the capture recorded. The last is approximate and the build
stage says so. Pass that warning on — do not present approximate timing as
frame-accurate.

## Gates

**Production.** A base URL matching a production marker is refused.
`--allow-production` exists for genuinely disposable environments; it is the
user's call, never yours.

**Destructive actions.** Selectors or values matching delete / remove / drop /
wipe / purge / revoke (and the Arabic equivalents) are skipped and reported. A
step opts in with `allow_destructive: true`. Do not add that flag on the user's
behalf — a sprint video is not worth destroying a record someone needs.

**Secrets.** Console output and failed request URLs are redacted against every
configured password before being written to the capture log.

## Failed steps stay failed

A step that times out does not abort the run: it is recorded as `failed` with its
error and console output, excluded from the video, and rendered in the guide as
"not verified - capture failed".

Never quietly drop a failed step, and never describe it as working. A step that
fails during capture is usually a real bug the sprint review should hear about —
it is a finding, not noise.
