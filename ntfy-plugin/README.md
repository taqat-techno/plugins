# ntfy Notifications Plugin for Claude Code

> **Push notifications to your phone whenever Claude Code completes tasks, needs your input, or encounters errors. Two-way Q&A lets Claude ask questions and wait for your phone response.**

**v3.0.0** | **100% FREE** - Uses [ntfy.sh](https://ntfy.sh), an open-source push notification service that requires no account.

---

## Why Use This?

Claude Code often works autonomously on complex tasks. Without notifications:

| Problem | Impact |
|---------|--------|
| Checking back repeatedly | Wastes your time |
| Missing when Claude needs input | Tasks stall |
| Not knowing when work is done | Lost productivity |
| Missing errors and blockers | Delayed resolution |

---

## Quick Start (5 Minutes)

```
1. Install ntfy app on your phone (iOS App Store / Google Play)
2. Subscribe to a unique topic (e.g., claude-yourname-abc123)
3. Run:  /ntfy setup
4. Test:  /ntfy test
5. Done! Claude will notify you automatically.
```

### Detailed Setup

**Step 1: Install the ntfy App**

| Platform | Instructions |
|----------|-------------|
| **iOS** | App Store > Search "ntfy" > Install (by Philipp Heckel) |
| **Android** | Google Play / F-Droid > Search "ntfy" > Install |
| **Desktop** | Visit [ntfy.sh/app](https://ntfy.sh/app) or install the PWA |

**Step 2: Create Your Topic**

1. Open the ntfy app
2. Tap the **+** button
3. Create a **unique, hard-to-guess** topic name (e.g., `claude-john-x7k9m2`)
4. Tap **Subscribe**

> **IMPORTANT:** Topic names act like passwords. Anyone who knows your topic can send you notifications. Make it unique!

**Step 3: Configure & Test**

```
/ntfy setup          # Interactive setup wizard
/ntfy test           # Send a test notification
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/ntfy <sub-command>` | Unified command: `send`, `setup`, `test`, `status`, `history`, `config` |
| `/ntfy-mode` | Toggle session auto-notify on/off (with optional custom topic) |

### Two-Way Q&A (Skill-Driven)

Two-way phone Q&A is handled automatically by the ntfy skill. Just ask Claude naturally:

- *"Ask me on my phone whether to deploy to production"*
- *"Send a notification asking which database to use"*

---

## Plugin Structure

```
ntfy-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── .gitignore                   # Excludes user config, history, state
├── ntfy/                        # Skill folder
│   ├── SKILL.md                 # Main skill (injected into Claude context)
│   ├── config.json              # User config (gitignored, created from default)
│   ├── config.default.json      # Default config template (committed)
│   └── scripts/                 # Python utilities
│       ├── notify.py            # Core: send_notification, config management
│       ├── notification_checker.py  # Retry, deduplication, convenience functions
│       ├── interactive.py       # Two-way Q&A (ask_user, ask_choice, etc.)
│       ├── claude_actions.py    # Session-aware high-level API for Claude
│       ├── session.py           # Session state for ntfy-mode (auto-expires)
│       ├── task_helpers.py      # TaskContext, @notify_on_complete decorator
│       └── notification_logger.py   # History storage and analytics
├── commands/
│   ├── ntfy.md                  # /ntfy — unified command with sub-commands
│   └── ntfy-mode.md             # /ntfy-mode — session auto-notify toggle
└── README.md                    # This documentation
```

### Architecture Layers

| Layer | Module | Purpose |
|-------|--------|---------|
| **1. Transport** | `notify.py` | Raw HTTP send to ntfy, config management, rate limiting |
| **2. Reliability** | `notification_checker.py` | Retry with backoff, deduplication, convenience functions |
| **3. Interaction** | `interactive.py` | Two-way Q&A: send question, poll for response |
| **4. Session** | `claude_actions.py` | Session-aware API: checks mode, resolves topic, delegates |
| **5. Helpers** | `task_helpers.py` | Context managers, decorators, lifecycle hooks |
| **6. Storage** | `notification_logger.py` | JSON history, statistics, export |
| **7. State** | `session.py` | Session mode on/off, expiry, counters |

---

## Configuration

### Config Files

- `ntfy/config.default.json` — Template shipped with the plugin (committed to git)
- `ntfy/config.json` — Your config (gitignored, created by `/ntfy setup`)

### Full Config Reference

```json
{
  "server": "https://ntfy.sh",
  "topic": "your-unique-topic",
  "default_priority": "default",
  "platform": "universal",
  "auto_notify": {
    "on_task_complete": true,
    "on_action_required": true,
    "on_error": true,
    "on_long_task": true,
    "long_task_threshold_seconds": 60
  },
  "priorities": {
    "task_complete": "high",
    "action_required": "urgent",
    "blocked": "high",
    "error": "high",
    "info": "default",
    "success": "default"
  },
  "tags": {
    "task_complete": ["white_check_mark", "computer"],
    "action_required": ["warning", "bell"],
    "blocked": ["x", "stop_sign"],
    "error": ["rotating_light", "skull"],
    "info": ["information_source"],
    "success": ["tada", "rocket"]
  },
  "rate_limit": {
    "enabled": true,
    "max_per_minute": 10,
    "cooldown_seconds": 5
  },
  "logging": {
    "enabled": true,
    "max_history": 1000
  },
  "authentication": {
    "enabled": false,
    "token": "",
    "username": "",
    "password": ""
  }
}
```

### Self-Hosted Server

```json
{
  "server": "https://ntfy.yourdomain.com",
  "topic": "your-topic",
  "authentication": {
    "enabled": true,
    "token": "tk_your_access_token"
  }
}
```

---

## API Reference

### Core Functions (notify.py)

```python
send_notification(title, message, priority, tags, click, actions, topic, ...)
send_json_notification(payload)
setup_topic(topic_name, server=None)
get_config_status()
check_connection()
test_notification()
load_config()
save_config(config)
get_topic()
```

### Fail-Safe Functions (notification_checker.py)

```python
ensure_notification(title, message, priority, tags, max_retries, allow_duplicate, silent)
task_complete(task_name, details, duration, silent)
action_required(action_name, details, options, silent)
blocked(blocker_name, details, suggestion, silent)
error(error_type, details, silent)
info(title, message, silent)
success(title, message, silent)
queue_notification(title, message)
flush_queue()
```

### Interactive Functions (interactive.py)

```python
ask_user(title, message, options, timeout, priority, tags, platform, topic)
ask_yes_no(title, message, timeout, platform, topic)
ask_choice(title, message, choices, timeout, platform, topic)
ask_confirm(action, details, timeout, platform, topic)
ask_approval(item, description, timeout, platform, topic)
set_platform(platform)  # "ios", "android", "universal"
```

### Claude Actions (claude_actions.py) — Primary API

```python
need_action(title, message, options, timeout, force)
task_done(task_name, summary, next_steps, auto_proceed, timeout, force)
ask_proceed(action, details, timeout)
ask_choice(question, choices, context, timeout)
get_user_input(prompt, context, timeout)
blocked(issue, details, options, timeout)
error_occurred(error, details, can_retry, timeout)
should_notify()
```

### Task Helpers (task_helpers.py)

```python
TaskContext(name, notify_on_start, notify_on_complete, notify_on_error)
@notify_on_complete(task_name)
quick_notify(message, title)
notify_when_done(message)
on_task_start(task_name, task_id, details, notify)
on_task_end(task_name, task_id, success, details, notify)
on_error(error_type, error_message, traceback, recoverable)
on_long_task(task_name, elapsed_seconds, estimated_remaining, progress_percent)
```

### History Functions (notification_logger.py)

```python
get_history(since_date, until_date, priority, success_only, limit, search)
get_today()
get_recent(count)
get_failed()
get_statistics(days)
export_to_markdown(output_path)
export_to_csv(output_path)
clear_history(confirm)
prune_old_entries(days)
```

---

## Priority Levels

| Level | Name | Use Case | Behavior |
|-------|------|----------|----------|
| 5 | `urgent` | User must act NOW | Loud, persistent |
| 4 | `high` | Important notifications | Long vibration |
| 3 | `default` | General updates | Normal sound |
| 2 | `low` | FYI notifications | Quiet |
| 1 | `min` | Silent, background | No sound |

## Emoji Tags

| Shortcode | Use For |
|-----------|---------|
| `white_check_mark` | Success, Complete |
| `warning` | Attention needed |
| `x` | Errors, Failed |
| `rotating_light` | Critical alerts |
| `bell` | Action required |
| `hourglass` | Long-running tasks |
| `tada` | Celebrations |
| `rocket` | Deployments |
| `stop_sign` | Blocked |

---

## Interactive Two-Way Communication

### How It Works

**Android:** Notification with action buttons — tap to respond directly.

**iOS:** Numbered options in notification body — open browser at `https://ntfy.sh/YOUR-TOPIC` and type your choice.

### Platform Configuration

```python
from interactive import set_platform
set_platform("ios")       # iOS users
set_platform("android")   # Android users
set_platform("universal") # Both (default)
```

| Mode | Description | Best For |
|------|-------------|----------|
| `universal` | Buttons + numbered options | Mixed devices |
| `ios` | Numbered options only | iOS users |
| `android` | Action buttons only | Android users |

---

## Notification Templates

```python
TEMPLATES = {
    "task_complete": {"title": "Task Complete", "priority": "default", "tags": ["white_check_mark"]},
    "needs_input": {"title": "Input Required", "priority": "high", "tags": ["pause_button"]},
    "error": {"title": "Error", "priority": "urgent", "tags": ["x", "warning"]},
    "server_ready": {"title": "Server Ready", "priority": "low", "tags": ["rocket"]},
    "tests_passed": {"title": "Tests Passed", "priority": "default", "tags": ["white_check_mark"]},
    "tests_failed": {"title": "Tests Failed", "priority": "urgent", "tags": ["x"]},
    "deploy_complete": {"title": "Deployed", "priority": "default", "tags": ["rocket"]},
}
```

---

## Windows Toast Fallback

If ntfy.sh is unreachable, fall back to Windows Toast notifications:

```python
import subprocess, sys

def send_with_fallback(title, message):
    # Try ntfy first, then Windows Toast, then terminal bell
    from notify import send_notification
    result = send_notification(title=title, message=message)
    if result.get("success"):
        return result

    if sys.platform == "win32":
        ps_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep 1; $n.Dispose()'''
        subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "method": "windows_toast"}

    print(f"\a[NOTIFICATION] {title}: {message}", flush=True)
    return {"success": True, "method": "terminal"}
```

---

## GitHub Actions Integration

```yaml
- name: Notify via ntfy
  if: always()
  run: |
    STATUS="${{ job.status }}"
    ICON=$([ "$STATUS" = "success" ] && echo "check" || echo "x")
    PRIORITY=$([ "$STATUS" = "success" ] && echo "default" || echo "high")
    curl -s \
      -H "Title: $ICON CI $STATUS" \
      -H "Priority: $PRIORITY" \
      -H "Tags: $ICON" \
      -H "Click: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
      -d "Branch: ${{ github.ref_name }} | Job: ${{ github.job }}" \
      https://ntfy.sh/${{ secrets.NTFY_TOPIC }}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Not receiving notifications | Check app permissions, verify subscription, test manually at `https://ntfy.sh/YOUR-TOPIC` |
| "No topic configured" | Run `/ntfy setup` |
| Notifications delayed | Set priority to "urgent"; check iOS battery settings for ntfy app |
| Connection errors | Verify internet; check `failed_notifications.log` |
| Too many notifications | Lower `rate_limit.max_per_minute` or disable specific `auto_notify` events |

---

## Security Notes

1. **Topic Privacy**: Topic names act like passwords. Keep them secret and hard to guess.
2. **No Auth Required**: Public ntfy.sh topics need no accounts. Anyone with the topic name can read/write.
3. **For Sensitive Use**: [Self-host ntfy](https://docs.ntfy.sh/install/) with authentication.
4. **Local Logging**: All notifications are logged locally. No data sent anywhere except ntfy.sh.

---

## License

MIT License - Free to use, modify, and distribute.

## Credits

- [ntfy.sh](https://ntfy.sh) - Open-source notification service by Philipp Heckel
- [Claude Code](https://claude.ai/code) - AI-powered coding assistant by Anthropic
- [TaqaTechno](https://www.taqatechno.com) - Plugin development
