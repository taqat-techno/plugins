# ntfy Notifications Plugin for Claude Code

> **Push notifications to your phone whenever Claude Code completes tasks, needs your input, or encounters errors. Two-way Q&A lets Claude ask questions and wait for your phone response.**

**v3.0.0** | **100% FREE** - Uses [ntfy.sh](https://ntfy.sh), an open-source push notification service that requires no account.

> **Migration Note**: In v3.0, 8 commands consolidated into 2. Two-way Q&A is skill-driven.

---

## Why Use This?

Claude Code often works autonomously on complex tasks. Without notifications:

| Problem | Impact |
|---------|--------|
| Checking back repeatedly | Wastes your time |
| Missing when Claude needs input | Tasks stall |
| Not knowing when work is done | Lost productivity |
| Missing errors and blockers | Delayed resolution |

**With this plugin:**
- Get **instant push notifications** on your phone
- Know **immediately** when tasks complete
- Never miss **action-required** prompts
- Get alerted to **errors and blockers**
- Track all notifications in **local history**

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

A "topic" is like a private channel for your notifications.

1. Open the ntfy app
2. Tap the **+** button
3. Create a **unique, hard-to-guess** topic name (e.g., `claude-john-x7k9m2`)

> **IMPORTANT:** Topic names act like passwords. Anyone who knows your topic can send you notifications. Make it unique!

4. Tap **Subscribe**

**Step 3: Configure & Test**

```
/ntfy setup          # Interactive setup wizard
/ntfy test           # Send a test notification
```

You should receive a push notification on your phone within seconds!

---

## Features

### Automatic Notifications

Claude Code automatically sends notifications for:

| Event | Priority | Sound |
|-------|----------|-------|
| Task completion | High | Long vibration |
| Action required | Urgent | Loud, persistent |
| Blocked/Error | High | Long vibration |
| Long-running task (60s+) | Low | Quiet |

### Priority Levels

| Level | Name | Use Case |
|-------|------|----------|
| 5 | `urgent` | User must act NOW |
| 4 | `high` | Important notifications |
| 3 | `default` | General updates |
| 2 | `low` | FYI notifications |
| 1 | `min` | Silent, background |

### Emoji Tags

Notifications include visual emoji indicators:

- ✅ `white_check_mark` - Success/Complete
- ⚠️ `warning` - Attention needed
- ❌ `x` - Errors/Failed
- 🚨 `rotating_light` - Critical
- 🔔 `bell` - Action required
- 🎉 `tada` - Celebrations
- 🚀 `rocket` - Deployments

### Reliability Features

- **Automatic retry** with exponential backoff (3 attempts)
- **Deduplication** prevents spam from repeated notifications
- **Rate limiting** prevents accidental flooding
- **Local fallback** logs notifications if network fails
- **History tracking** for all notifications

---

## Commands

| Command | Description |
|---------|-------------|
| `/ntfy <sub-command>` | Unified command — sub-commands: `send`, `setup`, `test`, `status`, `history`, `config` |
| `/ntfy-mode` | Toggle session auto-notify on/off (with optional custom topic) |

### /ntfy Sub-Commands

| Sub-Command | Usage | Description |
|-------------|-------|-------------|
| `send` | `/ntfy send <message>` | Quick send a notification |
| `setup` | `/ntfy setup` | Interactive setup wizard |
| `test` | `/ntfy test` | Send test notification |
| `status` | `/ntfy status` | Check configuration and connection |
| `history` | `/ntfy history` | View notification history |
| `config` | `/ntfy config` | Update settings |

### Two-Way Q&A (Skill-Driven)

Two-way phone Q&A is handled automatically by the ntfy skill — no command needed. Just ask Claude naturally:

- *"Ask me on my phone whether to deploy to production"*
- *"Send a notification asking which database to use"*

Claude will send an interactive notification and wait for your response.

---

## How Claude Uses This

### Automatic Usage

Once configured, Claude Code will automatically send notifications. No action needed!

### Manual Usage in Code

```python
import sys
sys.path.insert(0, r'C:\path\to\ntfy-notifications')
from notification_checker import ensure_notification, task_complete, action_required, blocked

# Task completion
task_complete(
    "Data Migration",
    "Migrated 500 records successfully",
    duration="2m 30s"
)

# Need user input
action_required(
    "Database Selection",
    "Which database should I use?",
    options=["PostgreSQL", "MySQL", "SQLite"]
)

# Blocked by error
blocked(
    "Missing Dependency",
    "Cannot import pandas module",
    suggestion="Run: pip install pandas"
)
```

### Context Manager

```python
from hooks import TaskContext

with TaskContext("Processing Files", notify_on_complete=True) as task:
    # Do work here
    task.update_progress(50, "Halfway done")
    # More work...
# Automatically notifies when complete
```

### Decorator

```python
from hooks import notify_on_complete

@notify_on_complete("Data Processing")
def process_data():
    # Work here
    pass
# Automatically notifies when function returns
```

---

## Configuration

### config.json

```json
{
  "server": "https://ntfy.sh",
  "topic": "your-topic-name",
  "default_priority": "default",
  "auto_notify": {
    "on_task_complete": true,
    "on_action_required": true,
    "on_error": true,
    "on_long_task": true,
    "long_task_threshold_seconds": 60
  },
  "rate_limit": {
    "enabled": true,
    "max_per_minute": 10,
    "cooldown_seconds": 5
  }
}
```

### Self-Hosted Server

If you run your own ntfy server:

```python
setup_topic("my-topic", server="https://ntfy.yourdomain.com")
```

### Authentication

For private/authenticated servers:

```json
{
  "authentication": {
    "enabled": true,
    "token": "tk_your_access_token"
  }
}
```

---

## Plugin Structure

```
ntfy-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── ntfy/                        # Skill folder
│   ├── SKILL.md                 # Main skill with YAML frontmatter (two-way Q&A)
│   ├── config.json              # User configuration
│   └── scripts/                 # Python utilities
│       ├── notify.py            # Core notification functions
│       ├── interactive.py       # Two-way Q&A (ask_user, ask_choice, etc.)
│       ├── notification_checker.py  # Retry logic and fail-safe
│       ├── notification_logger.py   # History and analytics
│       ├── claude_actions.py    # High-level action helpers
│       ├── session.py           # Session state for ntfy-mode
│       └── hooks.py             # Automatic triggers and decorators
├── commands/                    # Slash commands (2 commands)
│   ├── ntfy.md                  # /ntfy — unified command with sub-commands
│   └── ntfy-mode.md             # /ntfy-mode — session auto-notify toggle
└── README.md                    # This documentation
```

---

## API Reference

### Core Functions (notify.py)

```python
# Setup
setup_topic(topic_name, server=None)
get_config_status()
check_connection()
test_notification()

# Send notifications
send_notification(title, message, priority, tags, ...)
notify_task_complete(task_name, details, duration)
notify_action_required(action_name, details, options)
notify_blocked(blocker_name, details, suggestion)
notify_error(error_type, details, traceback)
notify_info(title, message)
notify_success(title, message)
```

### Fail-Safe Functions (notification_checker.py)

```python
# Primary function (RECOMMENDED)
ensure_notification(title, message, priority, tags, max_retries)

# Convenience with retry
task_complete(task_name, details, duration)
action_required(action_name, details, options)
blocked(blocker_name, details, suggestion)
error(error_type, details)

# Batch operations
queue_notification(title, message)
flush_queue()
```

### History Functions (notification_logger.py)

```python
# Query
get_history(since_date, until_date, priority, limit)
get_today()
get_recent(count)
get_failed()
search_notifications(query)

# Statistics
get_statistics(days)
print_summary()

# Export
export_to_markdown(output_path)
export_to_csv(output_path)

# Management
clear_history(confirm=True)
prune_old_entries(days)
```

### Hook Functions (hooks.py)

```python
# Lifecycle hooks
on_task_start(task_name, task_id, details)
on_task_end(task_name, task_id, success, details)
on_tool_complete(tool_name, success, output)
on_error(error_type, error_message, traceback)
on_user_input_needed(prompt, options, context)
on_long_task(task_name, elapsed_seconds, progress)

# Quick helpers
quick_notify(message, title)
notify_when_done(message)
notify_need_input(prompt, options)

# Context manager
TaskContext(name, notify_on_start, notify_on_complete, notify_on_error)

# Decorator
@notify_on_complete(task_name)
```

---

## Troubleshooting

### Not Receiving Notifications

1. **Check app permissions**: Ensure ntfy app has notification permissions on your phone
2. **Verify subscription**: Open ntfy app and confirm you're subscribed to the topic
3. **Test manually**: Visit `https://ntfy.sh/YOUR-TOPIC` in browser and send a test
4. **Check config**: Run `/ntfy-status` to verify configuration
5. **Check connection**: Ensure internet is working

### "No topic configured" Error

Run `/ntfy-setup` to configure your topic.

### Notifications Delayed

- iOS may batch notifications for battery saving
- Set priority to "urgent" for immediate delivery
- Check phone's notification settings for ntfy app

### Connection Errors

1. Verify internet connection
2. Check if ntfy.sh is accessible
3. Review `failed_notifications.log` for details

### Too Many Notifications

Adjust rate limiting in config:
```json
{
  "rate_limit": {
    "max_per_minute": 5,
    "cooldown_seconds": 10
  }
}
```

Or disable auto-notify for certain events:
```json
{
  "auto_notify": {
    "on_task_complete": false
  }
}
```

---

## Security Notes

1. **Topic Privacy**: Your topic name acts like a password. Keep it secret and make it hard to guess.

2. **No Authentication Required**: ntfy.sh public topics don't require accounts. Anyone who knows your topic can:
   - Subscribe (receive your notifications)
   - Publish (send you notifications)

3. **For Sensitive Use**: Consider [self-hosting ntfy](https://docs.ntfy.sh/install/) with authentication.

4. **Local Logging**: All notifications are logged locally in `notification_history.json`. No data is sent anywhere except ntfy.sh.

---

## Comparison: ntfy vs Alternatives

| Feature | ntfy.sh | Pushover | Pushbullet |
|---------|---------|----------|------------|
| **Cost** | FREE | $5 one-time | Freemium |
| **Account Required** | No | Yes | Yes |
| **Self-Hostable** | Yes | No | No |
| **Open Source** | Yes | No | No |
| **iOS/Android** | Yes | Yes | Yes |
| **Action Buttons** | Yes | Yes | Limited |
| **API Simplicity** | Very Simple | Simple | Complex |

---

## Contributing

Contributions welcome! Areas for improvement:

- Additional notification services (Pushover, Telegram, etc.)
- Enhanced retry strategies
- More hook integrations
- UI for configuration
- Documentation improvements

---

## License

MIT License - Free to use, modify, and distribute.

---

## Credits

- [ntfy.sh](https://ntfy.sh) - The amazing open-source notification service by Philipp Heckel
- [Claude Code](https://claude.ai/code) - AI-powered coding assistant by Anthropic
- [TaqaTechno](https://www.taqatechno.com) - Plugin development

---

## Version History

### 3.0.0 (Current)
- Consolidated 8 commands into 2 (`/ntfy` with sub-commands, `/ntfy-mode`)
- Two-way phone Q&A is now skill-driven (natural language triggers)
- Interactive notifications: `ask_user()`, `ask_choice()`, `ask_confirm()`, `ask_approval()`
- Cross-platform support (Android action buttons + iOS text replies)
- Session-based notification mode with `/ntfy-mode`
- Claude actions API (`claude_actions.py`) for high-level workflows

### 2.0.0
- Complete rewrite with modular architecture
- Automatic retry with exponential backoff
- Deduplication to prevent spam
- Rate limiting
- Context managers and decorators
- Comprehensive slash commands
- Local notification history with analytics
- Export to Markdown/CSV
- Self-hosted server support
- Authentication support

### 1.0.0 (Initial)
- Basic notification system
- Simple retry logic
- Plugin commands
