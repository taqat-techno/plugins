---
name: sprint-repro-guide
description: "Use when publishing sprint-recap's HTML reproduction guide or deciding how to hand logins to a reviewer: a shared walkthrough page that would contain passwords, a credentials file that might be committed or attached, or a step that was not verified but could look like it was. Explains the two-file credential policy, status badges and the gitignore rules."
metadata:
  version: 0.1.0
  last_reviewed: 2026-10-19
  owns:
    - the shareable-guide / local-credentials split
    - rendering Playwright actions as human instructions
    - status badges for steps that were not verified
  defers_to:
    - sprint-step-script (source of the instruction text)
    - sprint-capture-clips (source of screenshots and statuses)
---

# Two files, on purpose

| File | Contains | Shareable |
|---|---|---|
| `05-publish/sprint-<id>-guide.html` | steps, screenshots, role NAMES, config key pointers | yes |
| `.sprint-recap/credentials/<id>-credentials.html` | real usernames and passwords | no |

The guide never contains a secret. For each step it names the role required and
the config key holding that role's login, so a reader knows exactly what they
need and where to get it without the guide itself becoming a password file.

The credentials page is written **only** with `--with-credentials`, into a
gitignored directory, and is never bundled with the video or attached to a
ticket. It carries a banner saying so.

Why not one convenient self-contained file: a single HTML with working logins
gets emailed, Slacked and screen-shared, and `.gitignore` protects none of those.
Separating them makes handing over credentials a deliberate act rather than a
side effect of sharing a document.

## Rendering actions as instructions

Each Playwright action becomes a sentence a human can follow — `click` becomes
"Click `role=button[name='Export']`", `fill` becomes "Type **London** into
`input[name='search']`". The selector is printed literally so a reader can find
the control even if the UI has since shifted.

## Honest badges

Every step carries the status the capture actually produced:

- **verified** — captured successfully; the screenshot is real evidence
- **not verified - capture failed** — with the error text shown
- **not captured - destructive action** — skipped by the safety gate

A guide that presents an unverified step as verified is worse than no guide: it
sends a reviewer off to reproduce something that may not work. Keep the failure
text in place.

## Before publishing

Confirm `.sprint-recap.local.json` and the whole `.sprint-recap/` folder (credential
pages, run evidence, and any `.sprint-recap/**/.auth/` session cookies left by
versions before 0.4) are gitignored
(`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_config.py"`). The plugin's PreToolUse hook
blocks git from staging these paths, but a check costs nothing and the hook is
the last line of defence, not the first.
