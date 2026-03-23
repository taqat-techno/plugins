"""
Remotion Plugin - Shared Utilities

Common functions used across all Remotion plugin scripts.
Provides dependency checking and audio measurement utilities.
"""

import sys


# Package groups for dependency checking
_PACKAGE_GROUPS = {
    "voice": ["edge_tts", "mutagen"],
    "audio": ["mutagen"],
    "concat": ["mutagen"],
}

# Display names for error messages (pip install names)
_PIP_NAMES = {
    "edge_tts": "edge-tts",
    "mutagen": "mutagen",
}


def check_dependencies(group="audio"):
    """Verify required packages for the given script group.

    Args:
        group: One of "voice", "audio", "concat"

    Exits with code 1 if any required package is missing.
    """
    packages = _PACKAGE_GROUPS.get(group, [])
    missing = []
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(_PIP_NAMES.get(pkg, pkg))

    if missing:
        print(f"ERROR: Missing packages: {', '.join(missing)}")
        print(f"Install: {sys.executable} -m pip install {' '.join(missing)}")
        sys.exit(1)


def get_audio_duration_ms(filepath):
    """Get the exact duration of an MP3 file in milliseconds.

    Args:
        filepath: Path to the MP3 file

    Returns:
        Duration in milliseconds (integer)
    """
    from mutagen.mp3 import MP3

    audio = MP3(filepath)
    return int(audio.info.length * 1000)
