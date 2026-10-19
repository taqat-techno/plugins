"""
Offline tests for the ADO write ask-gate (hooks/pre_write_confirm.py).

Synthetic PreToolUse payloads are routed exactly as Claude Code routes them:
a tool name reaches a script only if that hooks.json matcher matches it. No MCP
server is started.

Contract:
  * every gated write tool -> exit 0 + permissionDecision "ask" with a reason
    naming the action and its target
  * read tools and the 5 validator-owned tools never reach the ask gate
  * the validator-owned tools keep their existing routing and behavior
  * hooks.json matcher == the table in rules/write-gate.md (single source of truth)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
HOOKS_JSON = PLUGIN / "hooks" / "hooks.json"
CONFIRM = PLUGIN / "hooks" / "pre_write_confirm.py"
VALIDATE = PLUGIN / "hooks" / "pre_write_validate.py"
WRITE_GATE = PLUGIN / "rules" / "write-gate.md"
PREFIX = "mcp__plugin_devops_azure-devops__"
LEGACY = "mcp__azure-devops__"
VALIDATED = ["wit_create_work_item", "wit_update_work_item", "wit_add_work_item_comment",
             "wit_work_items_link", "repo_create_pull_request"]
READS = ["wit_get_work_item", "wit_my_work_items", "repo_get_pull_request_by_id",
         "pipelines_get_builds", "wiki_get_page_content", "repo_list_pull_request_threads",
         "testplan_list_test_cases", "work_get_team_capacity"]


def _matchers():
    groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    out = {}
    for g in groups:
        cmd = g["hooks"][0]["command"]
        out[re.search(r"hooks/([\w-]+\.py)", cmd).group(1)] = g["matcher"]
    return out


MATCHERS = _matchers()
ASK_MATCHER = MATCHERS["pre_write_confirm.py"]


def gated_tools_from_rule():
    text = WRITE_GATE.read_text(encoding="utf-8")
    section = text.split("## Hook-Enforced Confirmation", 1)[1].split("\n## ", 1)[0]
    rows = [ln for ln in section.splitlines() if ln.startswith("| ") and "`" in ln]
    return sorted({t for ln in rows for t in re.findall(r"`([a-z]+_[a-z_]+)`",
                                                        ln.split("|")[2])})


GATED = gated_tools_from_rule()


def expand(matcher):
    """Enumerate the tool names of a grouped ^mcp__...__(a|pre_(b|c))$ matcher."""
    body = matcher.split("azure-devops__(", 1)[1].rsplit(")$", 1)[0]
    items, depth, cur = [], 0, ""
    for ch in body:
        depth += (ch == "(") - (ch == ")")
        if ch == "|" and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    names = set()
    for item in items:
        m = re.fullmatch(r"([a-z_]+)\(([a-z_|]+)\)", item)
        names |= {m.group(1) + alt for alt in m.group(2).split("|")} if m else {item}
    return names


def routed(tool_name):
    """Scripts Claude Code would run for this tool (unanchored regex search)."""
    return {s for s, m in MATCHERS.items() if re.search(m, tool_name)}


def run(script, payload, tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, str(script)], input=raw.encode("utf-8"),
                       capture_output=True, env=env, timeout=15)
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")


def ask_reason(out):
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    return hso["permissionDecisionReason"]


class TestRouting:
    def test_rule_table_is_non_trivial(self):
        assert len(GATED) >= 20
        assert not set(GATED) & set(VALIDATED)

    @pytest.mark.parametrize("prefix", [PREFIX, LEGACY])
    def test_matcher_equals_rule_table(self, prefix):
        # Every tool listed in write-gate.md is routed, and nothing else known is.
        for tool in GATED:
            assert re.search(ASK_MATCHER, prefix + tool), tool
        for tool in VALIDATED + READS:
            assert not re.search(ASK_MATCHER, prefix + tool), tool
        assert expand(ASK_MATCHER) == set(GATED)

    def test_ask_matcher_is_anchored(self):
        assert ASK_MATCHER.startswith("^") and ASK_MATCHER.endswith("$")
        assert not re.search(ASK_MATCHER, PREFIX + "pipelines_run_pipeline_x")
        assert not re.search(ASK_MATCHER, "mcp__other__" + "pipelines_run_pipeline")

    @pytest.mark.parametrize("tool", READS)
    def test_read_tools_reach_no_write_hook(self, tool):
        assert routed(PREFIX + tool) == set()

    @pytest.mark.parametrize("tool", VALIDATED)
    def test_validated_tools_keep_validator_and_skip_ask(self, tool):
        assert routed(PREFIX + tool) == {"pre_write_validate.py"}
        assert routed(LEGACY + tool) == {"pre_write_validate.py"}

    def test_ask_hook_uses_same_launcher(self):
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
        cmds = [g["hooks"][0]["command"] for g in groups]
        assert len({re.sub(r"hooks/[\w-]+\.py", "hooks/X.py", c) for c in cmds}) == 1


class TestAskGate:
    @pytest.mark.parametrize("tool,tool_input,expect", [
        ("pipelines_run_pipeline", {"project": "Proj", "pipelineId": 42},
         ["pipelines run pipeline", "project=Proj", "pipelineId=42"]),
        ("repo_update_pull_request",
         {"repositoryId": "0a1b2c3d-0000-4000-8000-00000000abcd", "pullRequestId": 17,
          "status": "Completed"},
         ["repo update pull request", "pullRequestId=17", "status=Completed"]),
        ("wit_update_work_items_batch",
         {"updates": [{"id": 1, "op": "add", "path": "/fields/System.State",
                       "value": "Closed"}, {"id": 2, "op": "add",
                                            "path": "/fields/System.State", "value": "Done"}]},
         ["wit update work items batch", "2 updates"]),
    ])
    def test_write_tool_asks_with_target(self, tmp_path, tool, tool_input, expect):
        assert routed(PREFIX + tool) == {"pre_write_confirm.py"}
        code, out, err = run(CONFIRM, {"hook_event_name": "PreToolUse",
                                       "tool_name": PREFIX + tool,
                                       "tool_input": tool_input}, tmp_path)
        assert code == 0 and err == ""
        reason = ask_reason(out)
        for fragment in expect:
            assert fragment in reason, (fragment, reason)

    @pytest.mark.parametrize("tool", GATED)
    def test_every_gated_tool_asks(self, tmp_path, tool):
        code, out, _ = run(CONFIRM, {"tool_name": LEGACY + tool, "tool_input": {}}, tmp_path)
        assert code == 0
        assert tool.replace("_", " ") in ask_reason(out)

    def test_non_ascii_input_survives(self, tmp_path):
        code, out, _ = run(CONFIRM, {"tool_name": PREFIX + "wiki_create_or_update_page",
                                     "tool_input": {"path": "/عربي"}},
                           tmp_path)
        assert code == 0 and "عربي" in ask_reason(out)

    @pytest.mark.parametrize("payload", ["not json", "[]", json.dumps({"tool_name": 3})])
    def test_fail_open(self, tmp_path, payload):
        assert run(CONFIRM, payload, tmp_path)[:2] == (0, "")

    def test_read_tool_payload_is_allowed_silently(self, tmp_path):
        # Unreachable via the matcher; even if mis-routed, a non-ADO name is ignored.
        assert run(CONFIRM, {"tool_name": "Read", "tool_input": {}}, tmp_path)[:2] == (0, "")


class TestValidatorUnchanged:
    def test_read_tool_through_validator_is_silent(self, tmp_path):
        code, out, err = run(VALIDATE, {"tool_name": PREFIX + "wit_get_work_item",
                                        "tool_input": {"id": 1}}, tmp_path)
        assert (code, out.strip(), err.strip()) == (0, "", "")

    def test_validator_still_hard_blocks_unresolved_mention(self, tmp_path):
        code, out, err = run(VALIDATE, {"tool_name": PREFIX + "wit_add_work_item_comment",
                                        "tool_input": {"comment": "@bob hi"}}, tmp_path)
        assert code == 2 and "Unresolved @mentions" in err and "permissionDecision" not in out

    def test_validator_still_advises_without_decision(self, tmp_path):
        code, out, _ = run(VALIDATE, {"tool_name": PREFIX + "repo_create_pull_request",
                                      "tool_input": {"repositoryId": "my-repo"}}, tmp_path)
        hso = json.loads(out)["hookSpecificOutput"]
        assert code == 0 and "permissionDecision" not in hso
        assert "not a GUID" in hso["additionalContext"]
