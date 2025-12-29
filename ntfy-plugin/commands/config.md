---
title: 'ntfy Configuration'
read_only: false
type: 'command'
description: 'Update ntfy notification settings'
---

# /ntfy-config

Update ntfy notification settings.

## Instructions

### View Current Configuration

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import get_config, save_config

config = get_config()

print("Current Configuration")
print("=" * 50)
print(f"Server:           {config.get('server', 'https://ntfy.sh')}")
print(f"Topic:            {config.get('topic', '(not set)')}")
print(f"Default Priority: {config.get('default_priority', 'high')}")
print("")
print("Auto-Notify:")
auto = config.get('auto_notify', {})
print(f"  Task Complete:    {'ON' if auto.get('on_task_complete', True) else 'OFF'}")
print(f"  Action Required:  {'ON' if auto.get('on_action_required', True) else 'OFF'}")
print(f"  Blocked/Error:    {'ON' if auto.get('on_blocked', True) else 'OFF'}")
print(f"  Long Tasks:       {'ON' if auto.get('on_long_task', True) else 'OFF'}")
print("")
print("Rate Limiting:")
rate = config.get('rate_limit', {})
print(f"  Max per minute:   {rate.get('max_per_minute', 10)}")
print(f"  Cooldown:         {rate.get('cooldown_seconds', 5)}s")
```

## Configuration Options

### Change Topic
```python
from notify import setup_topic
setup_topic("new-topic-name")
```

### Change Server (Self-hosted)
```python
from notify import setup_topic
setup_topic("my-topic", server="https://ntfy.example.com")
```

### Toggle Auto-Notify Settings
```python
config = get_config()
config['auto_notify']['on_task_complete'] = False  # or True
config['auto_notify']['on_action_required'] = True
config['auto_notify']['on_blocked'] = True
config['auto_notify']['on_long_task'] = False
save_config(config)
print("Configuration updated!")
```

### Update Rate Limiting
```python
config = get_config()
config['rate_limit']['max_per_minute'] = 15
config['rate_limit']['cooldown_seconds'] = 3
save_config(config)
print("Rate limits updated!")
```

### Update Default Priority
```python
config = get_config()
# Options: min, low, default, high, urgent
config['default_priority'] = 'default'
save_config(config)
print("Default priority updated!")
```

### Set Up Authentication (Private Servers)
```python
config = get_config()
config['authentication'] = {
    'enabled': True,
    'token': 'tk_your_access_token_here'
}
save_config(config)
```

## Subcommands

- `/ntfy-config show` - Show current configuration
- `/ntfy-config topic <name>` - Change topic
- `/ntfy-config server <url>` - Change server
- `/ntfy-config priority <level>` - Change default priority
- `/ntfy-config auto-notify [on|off]` - Toggle all auto-notify
- `/ntfy-config reset` - Reset to defaults

## Full Config Reference

```json
{
  "server": "https://ntfy.sh",
  "topic": "your-topic",
  "default_priority": "high",
  "auto_notify": {
    "on_task_complete": true,
    "on_action_required": true,
    "on_blocked": true,
    "on_long_task": true
  },
  "rate_limit": {
    "max_per_minute": 10,
    "cooldown_seconds": 5
  },
  "tags": {
    "success": ["white_check_mark"],
    "warning": ["warning"],
    "error": ["x"],
    "action": ["bell"],
    "blocked": ["stop_sign"]
  }
}
```

---

*Part of ntfy-notifications Plugin v2.0*
