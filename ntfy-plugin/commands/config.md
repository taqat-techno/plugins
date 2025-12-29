# /ntfy-config

Update ntfy configuration settings.

## What This Does

Allows modification of ntfy settings without editing config.json directly:
1. Change topic
2. Change server
3. Toggle auto-notify settings
4. Configure priorities and tags
5. Set up authentication

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}")
sys.path.insert(0, str(plugin_dir))

from notify import load_config, save_config, get_config_status

config = load_config()
status = get_config_status()

print("Current Configuration")
print("=" * 50)
print(f"Server: {config.get('server', 'https://ntfy.sh')}")
print(f"Topic: {config.get('topic', '(not set)')}")
print(f"Default Priority: {config.get('default_priority', 'default')}")
print("")
print("Auto-Notify:")
auto = config.get('auto_notify', {})
print(f"  Task Complete: {auto.get('on_task_complete', True)}")
print(f"  Action Required: {auto.get('on_action_required', True)}")
print(f"  On Error: {auto.get('on_error', True)}")
print(f"  Long Task: {auto.get('on_long_task', True)}")
print(f"  Long Task Threshold: {auto.get('long_task_threshold_seconds', 60)}s")
print("")
print("Rate Limiting:")
rate = config.get('rate_limit', {})
print(f"  Enabled: {rate.get('enabled', True)}")
print(f"  Max per minute: {rate.get('max_per_minute', 10)}")
print(f"  Cooldown: {rate.get('cooldown_seconds', 5)}s")
```

## Configuration Options

### Change Topic
```python
config['topic'] = 'new-topic-name'
save_config(config)
```

### Change Server (Self-hosted)
```python
config['server'] = 'https://ntfy.example.com'
save_config(config)
```

### Toggle Auto-Notify
```python
# Disable task complete notifications
config['auto_notify']['on_task_complete'] = False
save_config(config)

# Enable all
config['auto_notify'] = {
    'on_task_complete': True,
    'on_action_required': True,
    'on_error': True,
    'on_long_task': True,
    'long_task_threshold_seconds': 60
}
save_config(config)
```

### Change Default Priority
```python
config['default_priority'] = 'high'  # min, low, default, high, urgent
save_config(config)
```

### Configure Rate Limiting
```python
config['rate_limit'] = {
    'enabled': True,
    'max_per_minute': 20,  # Increase limit
    'cooldown_seconds': 3   # Shorter cooldown
}
save_config(config)
```

### Set Up Authentication (for private servers)
```python
# Using access token
config['authentication'] = {
    'enabled': True,
    'token': 'tk_your_access_token_here'
}
save_config(config)

# Using username/password
config['authentication'] = {
    'enabled': True,
    'username': 'your_username',
    'password': 'your_password'
}
save_config(config)
```

### Custom Priority Per Event Type
```python
config['priorities'] = {
    'task_complete': 'high',
    'action_required': 'urgent',
    'blocked': 'high',
    'error': 'urgent',  # Make errors more prominent
    'info': 'low',
    'success': 'default'
}
save_config(config)
```

### Custom Tags Per Event Type
```python
config['tags'] = {
    'task_complete': ['white_check_mark', 'computer', 'rocket'],
    'action_required': ['warning', 'bell', 'eyes'],
    'blocked': ['x', 'stop_sign'],
    'error': ['rotating_light', 'skull', 'fire'],
    'info': ['information_source'],
    'success': ['tada', 'trophy']
}
save_config(config)
```

## Interactive Commands

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
  "default_priority": "default",
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
