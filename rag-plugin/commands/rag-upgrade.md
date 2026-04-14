---
description: Detect installed ragtools version, check for newer GitHub releases, and walk the in-place upgrade flow. Read-only — never auto-downloads installer artifacts.
argument-hint: "[--verbose]"
allowed-tools: Bash(curl:*), Bash(rag version:*), Bash(rag service:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-upgrade

Detect the installed ragtools version, check the GitHub releases API for newer versions, and walk the in-place upgrade flow from `references/recovery-and-reset.md` and `references/upgrade-paths.md`. **Never auto-downloads** installer artifacts — produces URLs and instructions; the user clicks. (D-005, scope rule.)

## Behavior

1. **Detect installed version** via `rag version`. Parse the output for the semver string.
2. **Fetch the latest release** from `https://api.github.com/repos/taqat-techno/rag/releases/latest` (read-only no-auth).
3. **Compare versions.** If installed ≥ latest, print "up to date" and stop.
4. **If newer is available,** present:
   - The version diff (current → latest)
   - Release date
   - Top changelog highlights (parsed from the release `body` field)
   - The platform-correct installer download URL
   - The in-place upgrade walkthrough from `references/recovery-and-reset.md`
5. **Walk the in-place upgrade** one step at a time. Wait for user confirmation between steps.
6. **Verify the upgrade** by re-running version detection and the post-install checklist.

Compact-by-default per D-008: ≤ 20 lines in default mode, `--verbose` adds the full release body and the raw API response.

## Required steps (perform in order)

### Step 0 — Mode detection

Run the standard mode-detection recipe (Step 0 from `/rag-status`). Print the mode banner. Record `install_mode` and `service_mode`.

If `install_mode == not-installed`, refuse with: `ragtools is not installed. run /rag-setup first.` and stop.

### Step 1 — Detect installed version

```bash
rag version 2>&1
```

Expected output: `ragtools v<X.Y.Z>` or `<X.Y.Z>`. Parse the semver substring with a regex like `(\d+\.\d+\.\d+)`. If the parse fails, print: `could not parse rag version output: <output>. recommend reinstall — see references/install.md.` and stop.

Record `installed_version`.

**Pre-v2.4.1 special case:** if `installed_version < 2.4.1`, this is the data-loss-tier v2.4.1 bug version (F-001). Add a strong warning to the Step 4 output:
```
⚠ pre-v2.4.1 detected. config writes can land in the wrong path and cause projects to disappear after restart (F-001). upgrade is strongly recommended.
```

### Step 2 — Fetch latest release from GitHub

```bash
curl --max-time 5 -s -L \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/taqat-techno/rag/releases/latest
```

Parse the JSON response. Extract:
- `tag_name` (e.g. `v2.4.2` — strip the leading `v`)
- `name` (release title)
- `published_at` (ISO 8601 timestamp)
- `body` (markdown changelog)
- `assets[].name` and `assets[].browser_download_url` (installer files)

If the API call fails (network error, 404, rate limit), print: `could not reach GitHub releases API. check connectivity or visit https://github.com/taqat-techno/rag/releases manually.` and stop.

If the response is parseable but doesn't have a `tag_name`, print: `unexpected response from GitHub releases API. visit https://github.com/taqat-techno/rag/releases manually.` and stop.

Record `latest_version`.

### Step 3 — Compare versions

Compare `installed_version` and `latest_version` as semver tuples (major, minor, patch).

| Case | Action |
|---|---|
| `installed > latest` | Print: `you are on a newer version than the latest stable (<installed> > <latest>). probably a dev build — no upgrade needed.` Stop. |
| `installed == latest` | Print: `up to date: ragtools v<installed>. nothing to do.` Stop. |
| `installed < latest` | Continue to Step 4. |

### Step 4 — Present the upgrade summary

Compact format (≤ 12 lines):
```
ragtools v<installed> → v<latest>
released: <published_at> (<N> days ago)

highlights:
  • <line 1 from changelog>
  • <line 2 from changelog>
  • <line 3 from changelog>

[pre-v2.4.1 warning if applicable]

installer for your platform: <download URL from assets[]>
```

**Highlights extraction:** scan the `body` field for the first 3 bullet points or the first 3 non-empty lines after `## Changes` / `## What's Changed` / `### Highlights`. Cap each line at ~80 characters. If the body is empty or unparseable, write `(no changelog provided — see GitHub release page)`.

**Installer URL selection:** match the `assets[].name` against the user's platform from the mode banner:

| Install mode | Match pattern |
|---|---|
| `packaged-windows` | `RAGTools-Setup-*.exe` |
| `packaged-macos` | `RAGTools-*-macos-arm64.tar.gz` |
| `dev-mode` | (skip — recommend `git pull && pip install -e .`) |

If no asset matches, print: `no installer artifact found for your platform in the latest release. visit https://github.com/taqat-techno/rag/releases manually.`

### Step 5 — Ask the user how to proceed

```
how would you like to upgrade?
  1. walk the in-place upgrade (recommended)
  2. just give me the URL — I'll handle it myself
  3. cancel — I'll upgrade later
```

If the user picks option 1, continue to Step 6. Option 2: print the URL and stop. Option 3: stop.

### Step 6 — Walk the in-place upgrade

The in-place upgrade flow per `references/recovery-and-reset.md#upgrade-without-losing-data` and `references/upgrade-paths.md`:

#### Windows (packaged)

1. **Print:** `the installer handles in-place upgrade automatically. it stops the service, replaces files, reinstalls the startup task, and restarts the service. data and config are preserved.`
2. **Show the URL:** `download from <installer URL>` — the user clicks. **Never auto-download** (D-005).
3. **Wait for confirmation:** `tell me when the new version finishes installing.`
4. **Re-run Step 1** to verify the new version is detected.
5. **Re-run mode detection** to confirm the service is up.
6. **Recommend `/rag-status`** to confirm projects survived the upgrade.

#### macOS (packaged)

1. **Print the platform caveats** (G-005, G-002):
   - No code signing — Gatekeeper will block on first launch
   - No `.dmg`, manual `tar -xzf`
   - No LaunchAgent — service must be started manually
2. **Show the upgrade sequence:**
   ```bash
   # Stop the existing service
   ./rag service stop
   
   # Download the new tarball (manually from <URL>)
   tar -xzf RAGTools-<latest>-macos-arm64.tar.gz
   xattr -cr rag/
   
   # Move/replace the old install
   # (preserves ~/Library/Application Support/RAGTools/data and config.toml)
   
   cd rag
   ./rag service start
   ```
3. **Wait for confirmation,** then re-verify.

#### Dev mode

1. **Print:** `dev mode upgrade is git pull + pip install -e ".[dev]". config and data in ./ are preserved.`
2. **Show the sequence:**
   ```bash
   rag service stop
   git pull
   pip install -e ".[dev]"
   rag service start
   ```
3. **Wait for confirmation,** then re-verify.

### Step 7 — Verify

1. **Re-run `rag version`** — confirm new version.
2. **Re-probe `/health`** — confirm service is up.
3. **Print:** `upgrade complete. ragtools v<new>. service mode: UP. next: /rag-status to verify projects.`
4. **If anything is wrong** post-upgrade, route to `/rag-doctor`.

## Output examples

**Up to date (≤ 10 lines):**
```
ragtools detected: packaged-windows
service mode: UP (proxy)
[paths...]

up to date: ragtools v2.4.2. nothing to do.
```

**Upgrade available (≤ 20 lines):**
```
ragtools detected: packaged-windows
service mode: UP (proxy)
[paths...]

ragtools v2.4.0 → v2.4.2
released: 2026-04-10 (4 days ago)

highlights:
  • macOS Phase 1 platform support
  • Encoder forced to device="cpu" (MPS OOM fix)
  • MCP server 2-second proxy retry

⚠ pre-v2.4.1 detected. config writes can land in the wrong path and cause projects to disappear after restart (F-001). upgrade is strongly recommended.

installer: https://github.com/taqat-techno/rag/releases/download/v2.4.2/RAGTools-Setup-2.4.2.exe

how would you like to upgrade? (1=in-place / 2=URL only / 3=cancel)
```

## Failure handling

| Situation | Behavior |
|---|---|
| `ragtools` not installed | Refuse with "run /rag-setup first" |
| `rag version` output unparseable | Recommend reinstall, link to install.md |
| GitHub API unreachable | Print error, link to releases page manually |
| GitHub API rate-limited (403) | Print error noting the rate limit, suggest retrying later |
| No installer asset for the user's platform | Print error, link to releases page manually |
| User picks option 3 (cancel) | Stop without further action |
| Post-upgrade `rag version` returns an unexpected version | Route to `/rag-doctor` |

## Boundary reminders

- **Do NOT auto-download** installer artifacts (D-005). Produce URLs; the user clicks.
- **Do NOT call any MCP tool** (D-001).
- **Do NOT edit `config.toml`** (D-002). Upgrade is a binary operation, not a config operation.
- **Do NOT touch the data directory.** In-place upgrade preserves it; `/rag-reset` is the only command that deletes it.
- **Do NOT skip the pre-v2.4.1 warning.** F-001 is data-loss-tier; the warning must be loud.
- Compact-by-default per D-008.

## See also

- `/rag-status` — verify post-upgrade state
- `/rag-doctor` — diagnose post-upgrade issues
- `/rag-reset` — destructive escalation when upgrade isn't enough
- `references/versioning.md` — semver scheme and breaking-change history
- `references/recovery-and-reset.md#upgrade-without-losing-data` — in-place upgrade flow source
- `references/upgrade-paths.md` — in-place vs portable vs source upgrade
- `references/known-failures.md#f-001` — the v2.4.1 data-loss bug
