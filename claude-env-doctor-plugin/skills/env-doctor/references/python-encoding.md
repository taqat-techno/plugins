# Python output encoding on Windows

A Python script that runs fine elsewhere can crash on Windows the moment it prints a non-ASCII character. This page explains the symptom, the cause, the fix, and a safe wrapper pattern for Python scripts shipped by a plugin.

## Symptom

A working script raises a `UnicodeEncodeError` while writing to stdout or stderr. The traceback points at a `print()` call (or a logging handler) and names the `cp1252` codec, for example:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f600'
in position 0: character maps to <undefined>
```

The script itself is correct. The failure happens only on Windows, only when the output contains an emoji, a box-drawing glyph, an accented letter, or any other character outside the legacy console codec. The same script prints cleanly on Linux/macOS or when the output is redirected to a file.

## Cause

On Windows, Python chooses the console's encoding for `sys.stdout` and `sys.stderr` based on the active code page. That default is frequently a legacy single-byte codec (commonly `cp1252`) that simply cannot represent most non-ASCII characters. When the program tries to encode such a character for output, the codec fails and raises `UnicodeEncodeError`.

This is a writing/encoding problem on the output stream. It is distinct from the reading-side concern where a UTF-8 file begins with a byte-order mark (BOM) and must be decoded with `utf-8-sig` so the leading marker is stripped. The BOM issue is about how bytes are read into the program; the issue here is about how text is written out of it. Diagnose them separately.

## Fix

Make the output streams use UTF-8 instead of removing the characters. Set the encoding in the environment before the process starts:

```
# Windows (PowerShell)
$env:PYTHONIOENCODING = "utf-8"

# Windows (cmd)
set PYTHONIOENCODING=utf-8

# POSIX shells
export PYTHONIOENCODING=utf-8
```

`PYTHONIOENCODING=utf-8` tells the interpreter to encode stdout and stderr as UTF-8 regardless of the console code page, so the same characters that fail under `cp1252` are emitted correctly. Prefer this over stripping or replacing characters: stripping hides real data, changes output, and tends to mask the same problem in the next script.

Do not solve this by deleting emoji or transliterating text out of the source. The data is valid; the output codec is the thing that needs to change.

## Safe wrapper for plugin-shipped scripts

A plugin cannot assume anything about the host console's code page, and it should not depend on every caller remembering to export `PYTHONIOENCODING`. Make each shipped Python script reconfigure its own output streams to UTF-8 at process start, before any other output. This is idempotent and harmless on platforms that are already UTF-8.

Example (illustrative — not required):

```python
import sys

# Force UTF-8 output so non-ASCII (emoji, accents, box-drawing)
# never triggers a cp1252 UnicodeEncodeError on a Windows console.
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="backslashreplace")

# ... rest of the script ...
print("status: ok")
```

Notes on the snippet:

- `reconfigure()` exists on the standard text streams in modern Python; the `getattr` guard keeps the code safe if a stream has been replaced with an object that lacks it.
- `errors="backslashreplace"` keeps the program running on the rare stream that still cannot encode a character, emitting a visible escape instead of crashing. Use the default strict errors if a crash is preferable to lossy output.
- Setting `PYTHONIOENCODING=utf-8` in the environment and reconfiguring inside the script are complementary; doing both gives robust behavior whether the script is launched directly or wrapped by another process.

Never echo secrets, tokens, or raw environment values as part of diagnosing or demonstrating an encoding problem.
