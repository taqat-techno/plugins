"""Tests for scripts/db_manager.py — database backup, restore, and management."""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup_path(scripts_dir):
    """Ensure the scripts directory is on sys.path for every test."""


def test_pg_env():
    """_pg_env returns dict with PGPASSWORD and PGUSER."""
    from db_manager import _pg_env

    env = _pg_env("myuser", "mypass")
    assert env["PGPASSWORD"] == "mypass"
    assert env["PGUSER"] == "myuser"
    # Should also contain inherited env vars
    assert "PATH" in env


def test_pg_args():
    """_pg_args returns correct connection argument list."""
    from db_manager import _pg_args

    args = _pg_args("dbhost", 5433, "dbuser")
    assert args == ["-h", "dbhost", "-p", "5433", "-U", "dbuser"]


def test_backup_sql(tmp_path):
    """backup_sql calls pg_dump and writes to output directory."""
    from db_manager import backup_sql

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("db_manager.subprocess.run", return_value=mock_result) as mock_run:
        # We need the file to exist for stat() call — mock open via subprocess
        with patch("builtins.open", MagicMock()):
            # Because backup_sql opens a file and checks size, we patch at a higher level
            pass

    # Simpler approach: just verify the function structure by mocking subprocess
    with patch("db_manager.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Patch Path.stat to avoid FileNotFoundError
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_size=1024)
            result = backup_sql(
                database="testdb",
                host="localhost",
                port=5432,
                user="odoo",
                password="odoo",
                output_dir=str(tmp_path / "backups"),
            )
        # Verify pg_dump was called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "pg_dump"
        assert "-U" in call_args
        assert result is not None


def test_backup_dump(tmp_path):
    """backup_dump calls pg_dump with -Fc flag."""
    from db_manager import backup_dump

    with patch("db_manager._run", return_value=0) as mock_run, \
         patch("pathlib.Path.stat", return_value=MagicMock(st_size=2048)):
        result = backup_dump(
            database="testdb",
            output_dir=str(tmp_path / "backups"),
        )
        call_args = mock_run.call_args[0][0]
        assert "pg_dump" in call_args
        assert "-Fc" in call_args


def test_restore_sql(tmp_path):
    """restore_sql calls psql with -f flag."""
    from db_manager import restore_sql

    backup_file = tmp_path / "test.sql"
    backup_file.write_text("-- SQL dump")

    with patch("db_manager._run", return_value=0) as mock_run:
        result = restore_sql(
            backup_file=str(backup_file),
            database="newdb",
        )
        assert result is True
        # Check that psql was called (second _run call for the actual restore)
        calls = mock_run.call_args_list
        # First call is createdb, second is psql
        psql_call = calls[1][0][0]
        assert "psql" in psql_call
        assert "-f" in psql_call


def test_restore_dump(tmp_path):
    """restore_dump calls pg_restore."""
    from db_manager import restore_dump

    backup_file = tmp_path / "test.dump"
    backup_file.write_bytes(b"\x00binary")

    with patch("db_manager._run", return_value=0) as mock_run:
        result = restore_dump(
            backup_file=str(backup_file),
            database="newdb",
        )
        assert result is True
        calls = mock_run.call_args_list
        # Second call should be pg_restore
        pg_restore_call = calls[1][0][0]
        assert "pg_restore" in pg_restore_call


def test_create_database():
    """create_database calls createdb with correct args."""
    from db_manager import create_database

    with patch("db_manager._run", return_value=0) as mock_run:
        result = create_database(name="newdb", host="localhost", port=5432, user="odoo", password="odoo")
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "createdb" in call_args
        assert "newdb" in call_args


def test_list_databases():
    """list_databases calls psql and parses stdout."""
    from db_manager import list_databases

    with patch("db_manager._run_capture", return_value=("db1\ndb2\ndb3\n", "", 0)):
        result = list_databases()
        assert result == ["db1", "db2", "db3"]


def test_list_databases_empty():
    """list_databases returns empty list on error."""
    from db_manager import list_databases

    with patch("db_manager._run_capture", return_value=("", "error", 1)):
        result = list_databases()
        assert result == []


def test_reset_admin_password():
    """reset_admin_password calls psql with UPDATE SQL."""
    from db_manager import reset_admin_password

    with patch("db_manager._run", return_value=0) as mock_run:
        result = reset_admin_password(
            database="testdb",
            new_password="newpass123",
        )
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "psql" in call_args
        # Verify the SQL contains the password update
        sql_arg_idx = call_args.index("-c") + 1
        sql = call_args[sql_arg_idx]
        assert "UPDATE res_users" in sql
        assert "newpass123" in sql
