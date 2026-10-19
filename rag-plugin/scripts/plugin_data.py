#!/usr/bin/env python3
"""Where rag-plugin keeps its per-user state. The single owner of that answer.

Resolution order for the data directory:

1. ``RAG_PLUGIN_DATA_DIR``: explicit override (tests, unusual setups).
2. ``CLAUDE_PLUGIN_DATA``: the directory Claude Code gives every plugin. It survives
   plugin updates and is removed on uninstall. Hooks always receive it; commands pass
   it to the scripts they run.
3. ``~/.claude/rag-plugin``: the legacy location (plugin versions up to 0.19.x).

Reading falls back to the legacy location. ``path(rel)`` returns the file under the
data directory. When that file does not exist yet but the legacy copy does, it is
copied forward once (the legacy file is left in place), so state written by an older
plugin version keeps working after an update and is not lost on a downgrade.

Stdlib only. Never raises from the public helpers: a state problem must not break a
hook or a command.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

__all__ = ["data_dir", "legacy_dir", "path", "marker_present"]


def legacy_dir() -> Path:
    return Path.home() / ".claude" / "rag-plugin"


def data_dir() -> Path:
    for var in ("RAG_PLUGIN_DATA_DIR", "CLAUDE_PLUGIN_DATA"):
        value = os.environ.get(var, "").strip()
        # An unsubstituted "${CLAUDE_PLUGIN_DATA}" is not a directory name.
        if value and "${" not in value:
            return Path(value).expanduser()
    return legacy_dir()


def path(rel: str) -> Path:
    """The state file ``rel`` under the data directory, copied forward from the
    legacy location the first time it is needed."""
    target = data_dir() / rel
    try:
        legacy = legacy_dir() / rel
        if not target.exists() and legacy.is_file() and legacy.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(legacy), str(target))
    except Exception:
        pass
    return target


def marker_present(name: str) -> bool:
    """True when the marker file exists in the data directory or the legacy one.
    Markers are toggles a user may have set with an older version; honour both."""
    try:
        return (data_dir() / name).is_file() or (legacy_dir() / name).is_file()
    except Exception:
        return False


if __name__ == "__main__":
    print(data_dir())
