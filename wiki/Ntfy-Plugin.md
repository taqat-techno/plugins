# Ntfy Plugin

**Package:** `ntfy-notifications` · **Version:** `3.0.0` · **Category:** productivity · **License:** MIT · **Source:** [`ntfy-plugin/`](../../ntfy-plugin/)

## Purpose

Push notifications to your phone via [ntfy.sh](https://ntfy.sh) whenever Claude Code completes tasks, needs your input, or encounters errors. **Two-way Q&A** — Claude can ask questions and wait for your phone response. 100% free, no account required, no credit card, no vendor lock-in (can self-host if desired).

## What it does

- **Push notifications** to the user's ntfy app (iOS / Android / Desktop).
- **Two-way Q&A flow** — Claude sends a question with "wait for response"; the user responds from their phone; Claude resumes with the answer.
- **Auto-retry with exponential backoff** for flaky network conditions.
- **Deduplication + rate limiting** — same notification within a window is suppressed.
- **Local notification history** — JSONL log of what was sent, when, to which topic.
- **Self-hosted ntfy server support** — point at any ntfy instance, not just ntfy.sh.

## How it works

- **ntfy.sh** is an open-source push service. A unique *topic* (any string you choose, e.g., `claude-yourname-abc123`) is the address. Anyone who subscribes to that topic on the ntfy app receives messages posted there.
- **No accounts.** The topic *is* the identity. Keep it private (random component) for casual privacy.
- **Two commands** (`/ntfy` + `/ntfy-mode`) consolidated from 8 narrow commands in v3.0.
- **Hooks** can emit notifications automatically on Stop/Notification events.
- **Config** lives at `~/.claude/ntfy-plugin/config.json` with the topic, server, auth (if using a protected server), and retry settings.

## Commands (2)

| Command | Purpose |
|---|---|
| `/ntfy <subcommand>` | Core dispatcher — `setup`, `test`, `status`, `history`, `config`, or send a message (`/ntfy <message>`) |
| `/ntfy-mode` | Toggle the notification mode (quiet / normal / verbose) |

### `/ntfy` subcommands

- `/ntfy setup` — interactive setup wizard (pick a topic, configure server, verify delivery).
- `/ntfy test` — send a test notification; confirm the user received it on the phone.
- `/ntfy status` — show current configuration + last-sent status.
- `/ntfy history` — view the local JSONL notification log.
- `/ntfy config` — update settings (topic, server URL, auth, priority, retry behavior).
- `/ntfy <message>` — send an ad-hoc notification.

### `/ntfy-mode`

- **quiet** — only fire on Stop events (task completed).
- **normal** — Stop + user-input-needed events.
- **verbose** — Stop + user-input + errors + warnings.

## Inputs and outputs

**Inputs:**
- ntfy topic (user picks at setup).
- ntfy server URL (defaults to `https://ntfy.sh`).
- Optional authentication (for self-hosted servers with access tokens).
- Message text, priority (1–5), tags (emoji).

**Outputs:**
- Push notification to the subscribed phone / desktop.
- Entry in the local JSONL history log.

## Configuration

- **First-time setup** via `/ntfy setup` — interactive wizard.
- **Config location:** `~/.claude/ntfy-plugin/config.json`.
- **History location:** `~/.claude/ntfy-plugin/history.jsonl` (append-only, user can `cat` or `tail`).
- **Self-hosted:** point `server` at any ntfy instance (e.g., `https://ntfy.your-company.com`). Add `auth` token if required.
- **No config file in-repo** — all config is user-level.

## Dependencies

- **ntfy app** installed on your phone (iOS App Store, Google Play, F-Droid) or desktop ([ntfy.sh/app](https://ntfy.sh/app)).
- **`curl`** on PATH for sending HTTP POST to the ntfy endpoint.
- **No API key, no account, no credit card** — the default public ntfy.sh instance is free.

## Usage examples

```
# First-time setup (5 minutes)
1. Install ntfy app on your phone (iOS / Android).
2. Subscribe to a unique topic: "claude-yourname-abc123"
3. In Claude Code:
   /ntfy setup
   (enter the topic, test delivery)
4. /ntfy test
5. Claude now notifies you automatically on long tasks.

# Ad-hoc notification
/ntfy "Build finished, check the artifact"

# Toggle verbosity
/ntfy-mode verbose

# See what was sent today
/ntfy history
```

### Two-way Q&A example

```
Claude: Running a long migration. I'll notify you when I need confirmation.
[Claude works for 10 minutes]
[Phone buzzes: "About to drop the staging database. Confirm?"]
[User replies from phone: "yes"]
Claude: Resuming with confirmation received. Dropping...
```

## Known limitations

- **Network required** for the push itself (though ntfy can retry).
- **Public ntfy.sh topics are discoverable.** If someone guesses your topic, they see your messages. Use a random suffix for casual privacy; self-host for stronger isolation.
- **Rate limits on ntfy.sh** — public instance has soft limits (roughly: don't spam). Self-host to lift limits.
- **No end-to-end encryption by default.** ntfy.sh supports message auth/encryption but it's opt-in.
- **Desktop notifications** require the ntfy desktop app or PWA.

## Related plugins and integrations

- **odoo** — notify when `/odoo-upgrade` long migrations complete.
- **remotion** — notify when video rendering finishes.
- **devops** — notify on new work item assignment via `/task-monitor` + `/loop 15m`.
- **Any plugin** — the `/ntfy <message>` command is a one-liner anywhere.

## See also

- Source: [`ntfy-plugin/README.md`](../../ntfy-plugin/README.md) — full setup walkthrough
- [ntfy.sh documentation](https://docs.ntfy.sh/) — topic conventions, self-hosting, auth
- [ntfy iOS/Android apps](https://ntfy.sh/app)
