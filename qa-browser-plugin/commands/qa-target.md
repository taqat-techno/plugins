---
description: Set or inspect the QA target — base URL, credential map per role, do-not-click selector skiplist, production markers. Required before /qa-smoke, /qa-roles, /qa-route, /qa-report. Credentials are written to .qa-browser.local.json (gitignored); plugin refuses to operate if the file is tracked by git.
argument-hint: "[set | show | clear | check]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

# /qa-target

You are managing the QA target configuration. Credentials live in `.qa-browser.local.json` at the project root. The file is gitignored and must never be committed.

## Modes

- `set` — interactive prompt to set / update target URL + credentials + skiplist.
- `show` — display current configuration (credentials masked).
- `clear` — remove the local config file (asks for confirmation).
- `check` — verify the file's state: exists, gitignored, not tracked, no production-looking credentials.

Default mode if no argument: `check` (read-only, safe).

## Step 0 — MCP server pre-check

Verify that at least one browser MCP server is loaded:

- `chrome-devtools-mcp` (tools matching `mcp__.*chrome-devtools.*__browser_*` or `mcp__.*chrome-devtools.*__navigate_page`)
- `playwright-mcp` (tools matching `mcp__.*playwright.*__browser_*`)

If neither is loaded, surface a clear message:

> qa-browser requires a browser MCP server. Install one of:
>   - chrome-devtools-mcp: https://github.com/anthropics/chrome-devtools-mcp
>   - playwright-mcp: https://github.com/microsoft/playwright-mcp
> Then restart Claude Code and rerun /qa-target.

Continue only if at least one is loaded.

## Mode: check (default)

Inspect `.qa-browser.local.json` and report:

```
QA-BROWSER TARGET — check

File: <path>/.qa-browser.local.json
  Exists: <yes | no>
  Tracked by git: <no — good | YES — RECONFIGURE NOW>
  In .gitignore: <yes — good | no — ADD IT>
  File permissions: <readable by user only | broader — review>

Target URL: <url | not configured>
  Matches production markers: <no | YES — refusal active>
  Reachable (HEAD): <reachable | unreachable — check VPN / DNS / service>

Configured roles: <count>
  <role-1>: <username masked> <totp configured: yes/no>
  <role-2>: ...

Do-not-click skiplist: <count entries>
Production markers: <list>
Console allowlist: <count entries>

Recommended next: <run /qa-target set | /qa-target clear | proceed to /qa-smoke>
```

If the file is tracked by git: STOP. Do NOT proceed. Print a clear remediation:

```
DANGER: .qa-browser.local.json is tracked by git.

Run:
  git rm --cached .qa-browser.local.json
  echo ".qa-browser.local.json" >> .gitignore
  git add .gitignore
  git commit -m "[CHORE] gitignore qa-browser credentials"

Then re-run /qa-target check.
```

## Mode: set

Interactive. Ask one section at a time.

### Section 1 — Target URL

```
Target base URL? (staging / UAT / sandbox; never production by default)
  Example: https://staging.example.com
```

Reject if the URL matches any production marker without explicit override.

After accepting: send a HEAD request to confirm reachability. Capture the response status. Warn (but allow) if non-2xx.

### Section 2 — Roles + credentials

```
Configured roles (comma-separated): admin, manager, support, viewer
```

For each role:

```
[<role>] username:
[<role>] password:                 (never echoed; redacted in logs)
[<role>] totp secret (optional):
```

Store in the file as:

```json
{
  "targetUrl": "https://staging.example.com",
  "roles": {
    "admin":   { "username": "qa-admin@example.com",   "password": "...", "totp": null },
    "manager": { "username": "qa-manager@example.com", "password": "...", "totp": null }
  }
}
```

### Section 3 — Production markers

```
Production markers (substrings that trigger refusal; case-insensitive):
  Default: ["prod", "production"]
  Add custom? (e.g., a vanity production domain like "app.example.com"): _
```

### Section 4 — Do-not-click skiplist

```
Do-not-click selector list (CSS selectors that block clicks):
  Examples:
    - "button:has-text('Refund')"
    - "[data-customer-id]:not([data-customer-id^='qa-'])"
    - ".admin-billing-panel button"
  Enter one per line; empty line to finish.
```

### Section 5 — Console allowlist

```
Console error allowlist (known-benign errors that should not fail a row):
  Format: { messagePrefix: "...", reason: "..." }
  Empty by default.
```

After all sections: write the file. Print a summary (credentials masked). Suggest the next step (`/qa-smoke <role>`).

## Mode: show

Display the current config with credentials masked:

```
QA-BROWSER TARGET — show

Target URL: <url>
Roles:
  admin    username=q***@e***.com  totp=<configured | not configured>
  manager  username=q***@e***.com  totp=<configured | not configured>
  ...
Production markers: <list>
Do-not-click: <count entries; first 3 listed>
Console allowlist: <count entries>
Last modified: <ISO timestamp>
```

Never print full credentials.

## Mode: clear

Ask for explicit confirmation:

```
This will delete <path>/.qa-browser.local.json
Type "clear qa-browser config" to confirm:
```

Only delete if the user types the exact confirmation string.

## Safety

- Refuse to set a URL matching production markers (unless `--allow-production` is passed AND the user types the override confirmation).
- Refuse to read/write the file if it is tracked by git.
- Never echo passwords, OTPs, or tokens in any output.
- Never log credentials to the conversation; the file is the only persistence.
- File permissions on POSIX: `chmod 600` after write. On Windows: skip (NTFS ACLs not modified).
