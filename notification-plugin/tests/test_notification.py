#!/usr/bin/env python3
"""notification plugin - contract tests.

Stdlib only, no pytest, no network, no desktop required. Run from anywhere:

    python notification-plugin/tests/test_notification.py

The tests that matter most are the isolation ones: whatever else changes, the
hook must stay silent on stdout and must always exit 0, because three of the
five events it subscribes to are blocking events.
"""

import json
import os
import subprocess
import sys
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks")
HOOKS = os.path.abspath(HOOKS)
NOTIFY = os.path.join(HOOKS, "notify.py")
sys.path.insert(0, HOOKS)

import identity   # noqa: E402
import policy     # noqa: E402
import render     # noqa: E402


def run_hook(category, payload, extra_env=None):
    """Invoke notify.py exactly as Claude Code would, and capture everything."""
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_DATA"] = os.path.join(os.path.dirname(NOTIFY), "..", "tests", "_data")
    # Force the unsupported path so tests never fire real desktop notifications.
    env["SSH_CONNECTION"] = "test 0 test 0"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, NOTIFY, category],
        input=json.dumps(payload) if isinstance(payload, dict) else payload,
        capture_output=True, text=True, env=env, timeout=30,
    )


class HookIsolation(unittest.TestCase):
    """D-001 / D-002: the notifier must never disturb the session."""

    def test_exits_zero_and_silent_for_every_category(self):
        payloads = {
            "question": {"tool_input": {"questions": [{"question": "Which one?"}]}},
            "permission": {"message": "Claude needs your permission"},
            "task": {"task_subject": "Add regression test"},
            "turn": {"last_assistant_message": "Done."},
            "failure": {"error": "rate_limit", "error_details": "429"},
        }
        for category, payload in payloads.items():
            with self.subTest(category=category):
                result = run_hook(category, dict(payload, cwd=os.getcwd(), session_id="abc123def"))
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "", "hook wrote to stdout")

    def test_survives_garbage_stdin(self):
        for raw in ("", "not json", "[1,2,3]", "null", '{"unclosed":'):
            with self.subTest(raw=raw):
                result = run_hook("turn", raw)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_survives_unknown_category(self):
        result = run_hook("not-a-category", {"cwd": os.getcwd()})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_no_arguments_is_a_noop(self):
        result = subprocess.run([sys.executable, NOTIFY], input="{}",
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


class TextSafety(unittest.TestCase):
    """Notification text is untrusted data, never executable content."""

    def test_shell_metacharacters_survive_as_literal_text(self):
        hostile = 'Use "A" or \'B\'; cost $5 `now` & <fast> $(rm -rf ~) %USERPROFILE%'
        cleaned = render.clean(hostile, 220)
        for fragment in ("$(rm -rf ~)", "`now`", "&", "<fast>", '"A"'):
            self.assertIn(fragment, cleaned)

    def test_strips_ansi_and_control_characters(self):
        cleaned = render.clean("\x1b[31mred\x1b[0m\x00\x07 text", 220)
        self.assertEqual(cleaned, "red text")

    def test_collapses_newlines_and_tabs(self):
        self.assertEqual(render.clean("line one\n\nline\ttwo", 220), "line one line two")

    def test_clips_long_text(self):
        cleaned = render.clean("x" * 5000, 220)
        self.assertLessEqual(len(cleaned), 220)

    def test_strips_leading_dashes_so_text_is_never_an_option(self):
        self.assertFalse(render.clean("--help me", 220).startswith("-"))

    def test_handles_non_ascii(self):
        for value in ("emoji 🚀 here", "عربية RTL", "日本語"):
            self.assertIn(value.split()[0], render.clean(value, 220))

    def test_never_raises_on_odd_types(self):
        for value in (None, 12, [1, 2], {"a": 1}, object()):
            render.clean(value, 50)


class Rendering(unittest.TestCase):

    def test_question_uses_question_text(self):
        built = render.build("question", {"tool_input": {"questions": [
            {"header": "Migrations", "question": "Which migration strategy?"}]}}, "proj")
        self.assertIsNotNone(built)
        klass, title, body, attrib = built
        self.assertEqual(klass, render.ATTENTION)
        self.assertIn("Answer", title)
        self.assertEqual(body, "Which migration strategy?")
        self.assertEqual(attrib, "proj")

    def test_question_falls_back_to_header(self):
        built = render.build("question", {"tool_input": {"questions": [{"header": "Pick one"}]}}, "p")
        self.assertEqual(built[2], "Pick one")

    def test_task_uses_task_subject(self):
        built = render.build("task", {"task_subject": "Add regression test"}, "Cluster2")
        self.assertEqual(built[0], render.INFORMATIONAL)
        self.assertEqual(built[2], "Add regression test")

    def test_failure_combines_error_and_detail(self):
        built = render.build("failure", {"error": "rate_limit",
                                         "last_assistant_message": "API Error: Rate limit reached"}, "p")
        self.assertEqual(built[0], render.ATTENTION)
        self.assertIn("rate_limit", built[2])
        self.assertIn("Rate limit reached", built[2])

    def test_failure_without_detail_still_renders(self):
        self.assertEqual(render.build("failure", {"error": "overloaded"}, "p")[2], "overloaded")

    def test_unknown_category_returns_none(self):
        self.assertIsNone(render.build("nope", {"task_subject": "x"}, "p"))

    def test_empty_body_returns_none(self):
        self.assertIsNone(render.build("task", {"task_subject": "   "}, "p"))

    def test_every_category_is_classified(self):
        for category, (klass, title) in render.CATEGORIES.items():
            self.assertIn(klass, (render.ATTENTION, render.INFORMATIONAL))
            self.assertTrue(title.strip())


class Identity(unittest.TestCase):

    def test_project_name_finds_the_repository_root(self):
        here = os.path.dirname(os.path.abspath(__file__))
        name = identity.project_name(here)
        self.assertTrue(name)
        self.assertNotIn(os.sep, name)

    def test_project_name_falls_back_to_directory_name(self):
        root = os.path.abspath(os.sep)
        self.assertIsInstance(identity.project_name(root), str)

    def test_session_tag_is_short_and_stable(self):
        tag = identity.session_tag("550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(len(tag), identity.SESSION_TAG_LENGTH)
        self.assertEqual(tag, identity.session_tag("550e8400-e29b-41d4-a716-446655440000"))

    def test_attribution_combines_both_halves(self):
        attrib = identity.attribution({"cwd": os.getcwd(), "session_id": "abcdef123456"})
        self.assertIn("·", attrib)

    def test_attribution_never_empty(self):
        self.assertTrue(identity.attribution({}))

    def test_replace_key_is_session_scoped(self):
        one = identity.replace_key({"session_id": "aaaaaaaa"}, "task")
        two = identity.replace_key({"session_id": "bbbbbbbb"}, "task")
        self.assertNotEqual(one, two)


class Suppression(unittest.TestCase):

    def setUp(self):
        self.config = dict(policy.DEFAULTS)

    def test_allows_a_normal_event(self):
        self.assertIsNone(policy.suppression_reason("task", {"task_subject": "x"}, self.config))

    def test_suppresses_subagent_events(self):
        reason = policy.suppression_reason("task", {"agent_id": "agent-1"}, self.config)
        self.assertIn("subagent", reason)

    def test_suppresses_teammate_tasks_by_default(self):
        reason = policy.suppression_reason("task", {"teammate_name": "implementer"}, self.config)
        self.assertIn("teammate", reason)

    def test_suppresses_turn_with_background_work(self):
        self.assertIsNotNone(policy.suppression_reason(
            "turn", {"background_tasks": [{"id": "1"}]}, self.config))
        self.assertIsNotNone(policy.suppression_reason(
            "turn", {"session_crons": [{"id": "1"}]}, self.config))
        self.assertIsNotNone(policy.suppression_reason(
            "turn", {"stop_hook_active": True}, self.config))

    def test_turn_with_empty_arrays_is_allowed(self):
        self.assertIsNone(policy.suppression_reason(
            "turn", {"background_tasks": [], "session_crons": []}, self.config))

    def test_disabled_category_is_suppressed(self):
        config = dict(policy.DEFAULTS)
        config["categories"] = dict(policy.DEFAULTS["categories"], task=False)
        self.assertIsNotNone(policy.suppression_reason("task", {}, config))

    def test_master_switch_is_suppressed(self):
        config = dict(policy.DEFAULTS, enabled=False)
        self.assertIsNotNone(policy.suppression_reason("question", {}, config))


class Configuration(unittest.TestCase):

    def test_defaults_when_no_file_exists(self):
        os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_missing")
        self.assertEqual(policy.load()["enabled"], True)

    def test_unknown_keys_are_ignored(self):
        merged = policy._merge(policy.DEFAULTS, {"nonsense": 1, "enabled": False})
        self.assertNotIn("nonsense", merged)
        self.assertFalse(merged["enabled"])

    def test_partial_category_override_keeps_the_rest(self):
        merged = policy._merge(policy.DEFAULTS, {"categories": {"turn": False}})
        self.assertFalse(merged["categories"]["turn"])
        self.assertTrue(merged["categories"]["question"])

    def test_config_never_lands_under_the_plugin_root(self):
        os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join("some", "data", "dir")
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", policy.config_path())


class HooksManifest(unittest.TestCase):
    """The manifest is the safety contract; assert it structurally."""

    def setUp(self):
        path = os.path.join(HOOKS, "hooks.json")
        with open(path, "r", encoding="utf-8") as handle:
            self.manifest = json.load(handle)

    def test_every_hook_is_async(self):
        for event, groups in self.manifest["hooks"].items():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertTrue(hook.get("async"),
                                    "{0} hook is not async - it could block Claude".format(event))

    def test_every_hook_uses_exec_form(self):
        for event, groups in self.manifest["hooks"].items():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertIn("args", hook, "{0} hook is shell form".format(event))

    def test_every_hook_has_a_timeout(self):
        for groups in self.manifest["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertIsInstance(hook.get("timeout"), int)

    def test_expected_events_only(self):
        self.assertEqual(
            sorted(self.manifest["hooks"]),
            ["Notification", "PreToolUse", "Stop", "StopFailure", "TaskCompleted"])

    def test_no_sessionstart_hook(self):
        self.assertNotIn("SessionStart", self.manifest["hooks"])

    def test_categories_match_render(self):
        verbs = set()
        for groups in self.manifest["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    verbs.add(hook["args"][-1])
        self.assertEqual(verbs, set(render.CATEGORIES))

    def test_matcher_omitted_on_events_without_matcher_support(self):
        for event in ("Stop", "StopFailure", "TaskCompleted"):
            for group in self.manifest["hooks"][event]:
                self.assertNotIn("matcher", group,
                                 "{0} has no matcher support; omit it".format(event))


if __name__ == "__main__":
    unittest.main(verbosity=2)
