"""Tests for scripts/env_initializer.py — environment initialization."""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup_path(scripts_dir):
    """Ensure the scripts directory is on sys.path for every test."""


def test_detect_python_version_14():
    """detect_python_version for Odoo 14 returns (3,7)-(3,10)."""
    from env_initializer import detect_python_version

    min_v, max_v = detect_python_version(14)
    assert min_v == (3, 7)
    assert max_v == (3, 10)


def test_detect_python_version_17():
    """detect_python_version for Odoo 17 returns (3,10)-(3,13)."""
    from env_initializer import detect_python_version

    min_v, max_v = detect_python_version(17)
    assert min_v == (3, 10)
    assert max_v == (3, 13)


def test_detect_python_version_19():
    """detect_python_version for Odoo 19 returns (3,10)-(3,13)."""
    from env_initializer import detect_python_version

    min_v, max_v = detect_python_version(19)
    assert min_v == (3, 10)
    assert max_v == (3, 13)


def test_detect_python_version_unknown():
    """detect_python_version for unknown version returns default (3,10)-(3,13)."""
    from env_initializer import detect_python_version

    min_v, max_v = detect_python_version(99)
    assert min_v == (3, 10)
    assert max_v == (3, 13)


def test_check_python_compatibility():
    """check_python_compatibility returns True when current Python is in range."""
    from env_initializer import check_python_compatibility

    # Current Python should be compatible with at least one Odoo version.
    # We test against version 17 which supports 3.10-3.13.
    current = sys.version_info[:2]
    result = check_python_compatibility(17)
    expected = (3, 10) <= current <= (3, 13)
    assert result == expected


def test_get_venv_python_windows(tmp_path):
    """get_venv_python returns Windows path when Scripts/python.exe exists."""
    from env_initializer import get_venv_python

    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    (scripts / "python.exe").write_text("")
    result = get_venv_python(str(tmp_path))
    assert result.endswith("python.exe")


def test_get_venv_python_linux(tmp_path):
    """get_venv_python returns Linux path when bin/python exists."""
    from env_initializer import get_venv_python

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").write_text("")
    result = get_venv_python(str(tmp_path))
    assert result.endswith("python")


def test_create_conf_file_basic(tmp_path):
    """create_conf_file creates a file with correct project name and port."""
    from env_initializer import create_conf_file

    conf_path = create_conf_file(
        project="testproj",
        version=17,
        port=8069,
        output_dir=str(tmp_path / "conf"),
    )
    assert conf_path.exists()
    content = conf_path.read_text(encoding="utf-8")
    assert "testproj" in content
    assert "8069" in content


def test_create_conf_file_v17_gevent_port(tmp_path):
    """create_conf_file for v17+ uses gevent_port (not longpolling_port)."""
    from env_initializer import create_conf_file

    conf_path = create_conf_file(
        project="myproj",
        version=17,
        port=8069,
        output_dir=str(tmp_path / "conf"),
    )
    content = conf_path.read_text(encoding="utf-8")
    assert "gevent_port" in content
    assert "longpolling_port" not in content


def test_create_conf_file_v14_longpolling_port(tmp_path):
    """create_conf_file for v14 uses longpolling_port (not gevent_port)."""
    from env_initializer import create_conf_file

    conf_path = create_conf_file(
        project="oldproj",
        version=14,
        port=8069,
        output_dir=str(tmp_path / "conf"),
    )
    content = conf_path.read_text(encoding="utf-8")
    assert "longpolling_port" in content
    assert "gevent_port" not in content


def test_create_conf_file_has_dev_comment(tmp_path):
    """create_conf_file output contains 'Local development defaults' comment."""
    from env_initializer import create_conf_file

    conf_path = create_conf_file(
        project="proj",
        version=17,
        output_dir=str(tmp_path / "conf"),
    )
    content = conf_path.read_text(encoding="utf-8")
    assert "Local development defaults" in content


def test_check_postgresql_port_closed():
    """check_postgresql returns False when port is closed."""
    from env_initializer import check_postgresql

    with patch("env_initializer.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 1  # connection refused
        result = check_postgresql(host="localhost", port=5432)
        assert result is False


def test_find_python_executable_preferred():
    """find_python_executable returns preferred when shutil.which finds it."""
    from env_initializer import find_python_executable

    with patch("env_initializer.shutil.which", return_value="/usr/bin/python3.11"):
        result = find_python_executable("python3.11")
        assert result == "python3.11"


def test_find_python_executable_not_found():
    """find_python_executable raises RuntimeError when nothing is found."""
    from env_initializer import find_python_executable

    with patch("env_initializer.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="No Python executable found"):
            find_python_executable()
