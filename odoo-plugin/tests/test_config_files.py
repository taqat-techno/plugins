"""Static checks on shipped configuration: .mcp.json, compose templates, commands, agents."""
from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def test_mcp_json_optional_env_vars_have_a_default():
    text = (PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8")
    json.loads(text)
    # A bare ${VAR} passes the literal text through when VAR is unset.
    for var in re.findall(r"\$\{([^}]+)\}", text):
        assert var == "CLAUDE_PLUGIN_ROOT" or ":-" in var, var


def test_prod_compose_requires_a_postgres_password():
    text = (PLUGIN_ROOT / "templates/docker/docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD:-" not in text
    assert "${POSTGRES_PASSWORD:?" in text


def test_service_commands_use_the_plugin_root_path():
    for name, script in (("db", "db_manager.py"), ("stop", "server_manager.py")):
        text = (PLUGIN_ROOT / "commands" / ("%s.md" % name)).read_text(encoding="utf-8")
        assert '"${CLAUDE_PLUGIN_ROOT}/scripts/service/%s"' % script in text, name


def test_destructive_commands_tell_claude_to_ask_the_user():
    db = (PLUGIN_ROOT / "commands/db.md").read_text(encoding="utf-8")
    assert "the user confirms" in db.lower() and "--password-stdin" in db
    assert "paste the new password" in db
    stop = (PLUGIN_ROOT / "commands/stop.md").read_text(encoding="utf-8")
    assert "--all --yes" in stop and "kill -9" not in stop.replace("`kill -9`", "")


def test_every_agent_declares_tools():
    for agent in sorted((PLUGIN_ROOT / "agents").glob("*.md")):
        fm = re.match(r"^---\n(.*?)\n---\n", agent.read_text(encoding="utf-8"), re.S).group(1)
        assert re.search(r"^tools:", fm, re.M), agent.name


def test_theme_generator_lists_figma_tools_and_no_odoo_write_tools():
    text = (PLUGIN_ROOT / "agents/theme-generator.md").read_text(encoding="utf-8")
    fm = text.split("---", 2)[1]
    assert "get_design_context" in fm
    assert "odoo_write" not in fm and "odoo_unlink" not in fm and "odoo_call" not in fm
