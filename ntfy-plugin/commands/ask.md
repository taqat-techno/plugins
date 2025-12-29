# /ntfy-ask

Send an interactive question to your phone and wait for response.

## Usage

```
/ntfy-ask <question> [options...]
```

## Examples

```
/ntfy-ask "Deploy to production?" Yes No
/ntfy-ask "Select database" PostgreSQL MySQL SQLite
/ntfy-ask "Continue with migration?" Confirm Cancel
```

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from interactive import ask_user

# Parse arguments
args = "${ARGS}".strip()

if not args:
    print("Usage: /ntfy-ask <question> [options...]")
    print("")
    print("Examples:")
    print('  /ntfy-ask "Deploy?" Yes No')
    print('  /ntfy-ask "Select DB" PostgreSQL MySQL SQLite')
else:
    # Parse question and options from args
    # Simple parsing: first quoted string is question, rest are options
    import shlex
    try:
        parts = shlex.split(args)
        if len(parts) < 2:
            print("Error: Need at least a question and one option")
            print('Example: /ntfy-ask "Your question?" Option1 Option2')
        else:
            question = parts[0]
            options = parts[1:]

            print(f"Question: {question}")
            print(f"Options: {', '.join(options)}")
            print("")

            response = ask_user(
                title="Claude Code Question",
                message=question,
                options=options,
                timeout=120
            )

            if response:
                print(f"\n[RESULT] User selected: {response}")
            else:
                print("\n[RESULT] No response (timeout)")
    except Exception as e:
        print(f"Error: {e}")
```

## How It Works

1. Sends notification with clickable buttons to your phone
2. Waits up to 2 minutes for your response
3. Returns the option you selected

## Response Handling

The selected option is returned and can be used in subsequent commands:

```python
from interactive import ask_user

response = ask_user("Continue?", "Proceed with task?", ["Yes", "No"])

if response == "Yes":
    # Continue with task
    pass
elif response == "No":
    # Cancel task
    pass
else:
    # Timeout - no response
    pass
```

---

*Part of ntfy-notifications Plugin v2.1*
