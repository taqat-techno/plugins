---
description: 'Push notifications to your phone - send, setup, test, status, history, config'
argument-hint: '<message> | setup | test | status | history [--export|--search=X] | config <key> <value>'
---

# /ntfy - Push Notifications

Parse `$ARGUMENTS`:

| Input | Action |
|-------|--------|
| `setup` | Interactive setup wizard (topic, server, auth) |
| `test` | Send test notification to verify delivery |
| `status` | Show current config and connectivity |
| `history` | View notification history (--export, --search=X) |
| `config <key> <value>` | Update configuration setting |
| *(anything else)* | Quick send - treat entire argument as message |
| *(no args)* | Show help with usage examples |

Use the ntfy skill for:
- Setup workflow (topic creation, server config, authentication)
- Notification formatting (priority levels, tags, actions)
- Interactive notifications (phone-based Q&A via interactive.py)
- History management and export
- Rate limiting and deduplication
- Self-hosted server configuration
- Troubleshooting delivery issues

Scripts at `${CLAUDE_PLUGIN_ROOT}/ntfy/scripts/`:
- `send.py` - Send notifications
- `interactive.py` - Two-way phone Q&A
- `history.py` - View/export/search history
