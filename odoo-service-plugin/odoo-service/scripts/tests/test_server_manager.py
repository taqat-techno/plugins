"""Tests for scripts/server_manager.py — Odoo server lifecycle management."""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup_path(scripts_dir):
    """Ensure the scripts directory is on sys.path for every test."""


def test_build_odoo_command_basic():
    """build_odoo_command with config + db returns correct list."""
    from server_manager import build_odoo_command

    cmd = build_odoo_command(
        config_path="conf/test.conf",
        database="mydb",
        python_executable="/usr/bin/python3",
    )
    assert cmd[0] == "/usr/bin/python3"
    assert "-m" in cmd
    assert "odoo" in cmd
    assert "-c" in cmd
    assert "conf/test.conf" in cmd
    assert "-d" in cmd
    assert "mydb" in cmd


def test_build_odoo_command_dev():
    """build_odoo_command with dev=True includes --dev=all."""
    from server_manager import build_odoo_command

    cmd = build_odoo_command(config_path="conf/test.conf", dev=True)
    assert "--dev=all" in cmd


def test_build_odoo_command_update():
    """build_odoo_command with update_modules includes -u flag."""
    from server_manager import build_odoo_command

    cmd = build_odoo_command(
        config_path="conf/test.conf",
        database="mydb",
        update_modules="sale",
    )
    assert "-u" in cmd
    assert "sale" in cmd
    assert "--stop-after-init" in cmd


def test_build_odoo_command_install():
    """build_odoo_command with install_modules includes -i flag."""
    from server_manager import build_odoo_command

    cmd = build_odoo_command(
        config_path="conf/test.conf",
        database="mydb",
        install_modules="purchase",
    )
    assert "-i" in cmd
    assert "purchase" in cmd
    assert "--stop-after-init" in cmd


def test_build_parser_subcommands():
    """build_parser has all expected subcommands."""
    from server_manager import build_parser

    parser = build_parser()
    # Parse each known subcommand to verify they exist
    for subcmd in ["start", "stop", "status", "restart", "install", "update", "refresh", "logs", "processes"]:
        if subcmd == "start":
            args = parser.parse_args([subcmd, "--config", "test.conf"])
        elif subcmd in ("install", "update"):
            args = parser.parse_args([subcmd, "--config", "test.conf", "--db", "testdb", "--module", "base"])
        elif subcmd == "refresh":
            args = parser.parse_args([subcmd, "--config", "test.conf", "--db", "testdb"])
        elif subcmd == "restart":
            args = parser.parse_args([subcmd, "--config", "test.conf"])
        else:
            args = parser.parse_args([subcmd])
        assert args.command == subcmd


def test_is_port_in_use_true():
    """is_port_in_use returns True when socket connects successfully."""
    from server_manager import is_port_in_use

    with patch("server_manager.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 0
        assert is_port_in_use(8069) is True


def test_is_port_in_use_false():
    """is_port_in_use returns False when socket connection is refused."""
    from server_manager import is_port_in_use

    with patch("server_manager.socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 1
        assert is_port_in_use(8069) is False


def test_kill_port_calls_helpers():
    """kill_port calls get_pid_on_port and kill_process."""
    from server_manager import kill_port

    with patch("server_manager.get_pid_on_port", return_value=1234) as mock_get_pid, \
         patch("server_manager.kill_process", return_value=True) as mock_kill:
        result = kill_port(8069)
        mock_get_pid.assert_called_once_with(8069)
        mock_kill.assert_called_once_with(1234)
        assert result is True


def test_kill_port_no_process():
    """kill_port returns True when no process is found on port."""
    from server_manager import kill_port

    with patch("server_manager.get_pid_on_port", return_value=None):
        result = kill_port(9999)
        assert result is True


def test_install_module_calls_subprocess():
    """install_module calls subprocess.run with --stop-after-init."""
    from server_manager import install_module

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("server_manager.subprocess.run", return_value=mock_result) as mock_run:
        rc = install_module(
            config="conf/test.conf",
            database="testdb",
            module="sale",
            python_executable="/usr/bin/python3",
        )
        assert rc == 0
        call_args = mock_run.call_args[0][0]
        assert "--stop-after-init" in call_args
        assert "-i" in call_args
        assert "sale" in call_args


def test_update_module_calls_subprocess():
    """update_module calls subprocess.run with -u flag."""
    from server_manager import update_module

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("server_manager.subprocess.run", return_value=mock_result) as mock_run:
        rc = update_module(
            config="conf/test.conf",
            database="testdb",
            module="purchase",
            python_executable="/usr/bin/python3",
        )
        assert rc == 0
        call_args = mock_run.call_args[0][0]
        assert "-u" in call_args
        assert "purchase" in call_args
        assert "--stop-after-init" in call_args
