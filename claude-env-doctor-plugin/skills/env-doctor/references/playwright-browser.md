# Playwright / browser-MCP setup diagnosis

Diagnose the two failure modes that stop a Playwright-based browser MCP (or any Playwright-driven tool) from launching: the wrong browser channel, and a locked persistent profile. This doc is generic — it depends on no specific OS path, project, or vendor. Never print secrets, tokens, or environment values while diagnosing.

## Symptom 1: "Chromium distribution 'chrome' is not found"

This error means the tool was told to launch the **system Chrome channel** but no Google Chrome is installed on the machine. Playwright distinguishes between two launch modes:

- **Channel** — launch an externally-installed branded browser (`chrome`, `chrome-beta`, `msedge`, etc.). The browser must already be installed system-wide. There is **no** `channel: "chromium"` value — passing `"chromium"` as a channel is invalid and will fail the same way.
- **Bundled Chromium** — launch the Chromium build that Playwright downloaded into its own browser cache. This is selected by the **executable path**, not by a channel.

So the tool is defaulting to `channel: "chrome"` and the host has no Chrome.

### Fix A — install the branded system browser

If the workflow genuinely needs branded Chrome (e.g. for Widevine/DRM, specific codecs, or matching a user's real browser), install it system-wide, then re-run. Once the channel browser exists, the launch succeeds unchanged.

### Fix B — point the tool at the bundled Chromium executable

Usually the cleaner fix: stop requesting a channel and launch Playwright's own Chromium. Remove the `channel` option and instead supply the **executable path** to the bundled binary. Resolve the path generically rather than hardcoding it:

- Programmatically, the Playwright API exposes the resolved binary location for the chromium browser type (the `executablePath()` accessor). Prefer this over guessing.
- If the bundled browsers were never downloaded, run Playwright's browser-install step first so the cache is populated.
- Honor any documented environment override for the browser-download cache directory if the project relocates it — but read it, never echo its value into logs.

Decision rule: need a *specific branded* browser → Fix A (install it). Otherwise → Fix B (executable path to bundled Chromium). Never try to satisfy the error by inventing a `channel: "chromium"` — that channel does not exist.

Example (illustrative — not required): a launch config carrying `{ "channel": "chrome" }` on a CI runner with no Chrome installed. Switching to `{ "executablePath": "<resolved bundled chromium path>" }` (no `channel` key) resolves it.

## Symptom 2: persistent profile "already in use" / profile lock

A browser MCP that uses a **persistent profile** (a fixed user-data directory that survives restarts, so logins and cookies persist) keeps a *singleton lock* on that directory while a browser is attached to it. If a previous browser was killed uncleanly — or is still running detached — the lock survives and a new launch reports the profile is already in use and refuses to start.

The fix is: find and stop the **one** browser process that owns the profile, clear the stale lock artifacts, then let the MCP relaunch on demand.

### Step 1 — identify the top-level owning process

The owning browser spawns many child processes (renderer, GPU, utility, network-service, zygote). You want the **single top-level (parent) browser process**, not the children:

- Match on the user-data-directory / profile path argument the browser was launched with, so you target *this* profile rather than every browser on the machine.
- Exclude processes whose command line marks them as children — the launcher passes a `--type=` flag to renderers/helpers (e.g. `--type=renderer`, `--type=gpu-process`, `--type=utility`). The top-level process has **no** `--type=` flag.
- If several candidates remain, the parent is typically the one whose parent PID is not itself another browser process of the same profile.

### Step 2 — stop the owning process

Terminate that one top-level process. Its children exit with it. Prefer a graceful stop first; escalate to a forced kill only if it does not release.

#### Footgun: the self-kill loop

A naive "kill everything matching `chrome`/`chromium`" pattern loop is dangerous in an MCP/agent context: the pattern can match **the agent's own controlling shell, the diagnosing process, or its parent**, killing the very session running the diagnosis. Guard against it:

- **Exclude the current process** (`$$` / current PID) and **its parent** (`$PPID` / parent PID) from any kill list before acting.
- Match on the **profile-directory argument**, not on the bare browser name, so unrelated browsers and your own tooling are never in scope.
- Drop child/helper processes (the `--type=` filter from Step 1) — killing the parent reaps them anyway.
- Review the resolved PID list before sending any signal; never pipe an unfiltered match straight into a kill.

### Step 3 — clear the stale singleton lock

After the owning process is gone, remove the leftover singleton lock artifacts inside the profile directory. Chromium-family browsers keep their cross-process lock in a small set of `Singleton*` entries at the profile root (a lock plus its cookie/socket siblings). These are safe to delete **only once no browser is attached to the profile** — deleting them under a live browser corrupts the profile.

- Remove the `Singleton`-prefixed lock artifacts at the profile root.
- Do not touch cookies, local-storage, or login state — the point is to keep the persistent profile, just release its lock.
- Take a backup of the profile directory first if the profile is precious.

### Step 4 — relaunch

Do nothing else. A persistent-profile browser MCP **relaunches the browser on demand** the next time a browser action is requested. Once the lock is cleared, the next call starts a fresh browser cleanly against the same profile. Do not pre-start a browser manually — that risks re-creating the lock race.

## When qa-browser-plugin should reference this doc

`qa-browser-plugin` (and any plugin that drives a Playwright/browser MCP for QA) should **link to this diagnosis rather than re-implementing it**. The browser-setup health check is environment-level, not QA-specific — it belongs in env-doctor and should have exactly one owner.

Reference this doc from qa-browser-plugin when:

- A QA run fails to **launch the browser at all** with the channel error (Symptom 1) or the profile-lock error (Symptom 2). These are setup faults, not test failures — hand off to env-doctor's diagnosis instead of duplicating the channel/executable-path logic.
- A QA skill needs to **describe the bundled-Chromium-vs-system-Chrome distinction** or the persistent-profile model. Point at the sections above instead of restating them, so the explanation has a single source of truth.
- The persistent-profile **lock-clearing and self-kill guard** procedure is needed. The kill-loop footgun is easy to get wrong; centralizing it here prevents each plugin shipping its own unsafe variant.

`qa-browser-plugin` keeps ownership of QA concerns — selecting/asserting on pages, capturing failures, test structure. It should treat "can a browser even start in this environment" as a precondition that env-doctor diagnoses, and route here on the two errors above.
