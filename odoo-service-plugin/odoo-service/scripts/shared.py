#!/usr/bin/env python3
"""
shared.py — Shared utilities for Odoo service scripts.

Contains environment detection and platform helpers used across
server_manager.py, env_initializer.py, and other scripts.
"""

import platform
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"


def detect_environment(project_root: str = ".") -> str:
    """
    Detect the current Odoo environment type.
    Priority: docker > venv > bare

    Returns: 'docker', 'venv', or 'bare'
    """
    root = Path(project_root).resolve()

    # Docker detection (highest priority)
    if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
        return "docker"
    if (root / "Dockerfile").exists():
        return "docker"

    # Venv detection
    for venv_dir in [".venv", "venv", "env"]:
        venv_path = root / venv_dir
        if venv_path.is_dir():
            if (venv_path / "Scripts" / "python.exe").exists():
                return "venv"
            if (venv_path / "bin" / "python").exists():
                return "venv"

    return "bare"


def find_python_in_venv(project_root: str = ".") -> Optional[str]:
    """Find the Python executable inside a virtual environment."""
    root = Path(project_root).resolve()

    for venv_dir in [".venv", "venv", "env"]:
        venv_path = root / venv_dir
        win_python = venv_path / "Scripts" / "python.exe"
        linux_python = venv_path / "bin" / "python"

        if win_python.exists():
            return str(win_python)
        if linux_python.exists():
            return str(linux_python)

    return None
