#!/usr/bin/env python3
"""notification plugin - contract tests.

Stdlib only, no pytest, no network, no desktop required. Run from anywhere:

    python notification-plugin/tests/test_notification.py

The tests that matter most are the isolation ones: whatever else changes, the
hook must stay silent on stdout and must always exit 0, because four of the six
events it subscribes to are blocking events.
"""

import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HOOKS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
NOTIFY = os.path.join(HOOKS, "notify.py")
sys.path.insert(0, HOOKS)

import backends   # noqa: E402
import identity   # noqa: E402
import notify     # noqa: E402
import policy     # noqa: E402
import render     # noqa: E402
import state      # noqa: E402


def run_hook(category, payload, data_dir, extra_env=None):
    """Invoke notify.py exactly as Claude Code would, and capture everything."""
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_DATA"] = data_dir
    # Force the unsupported path so tests never fire real desktop notifications.
    env["SSH_CONNECTION"] = "test 0 test 0"
    if extra_env:
        env.update(extra_env)
    if isinstance(payload, dict):
        payload = json.dumps(payload, ensure_ascii=False)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return subprocess.run([sys.executable, NOTIFY, category], input=payload,
                          capture_output=True, env=env, timeout=30)


class DataDirTestCase(unittest.TestCase):
    """Points CLAUDE_PLUGIN_DATA at a throwaway directory for each test."""

    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="ccn-test-")
        self._saved = os.environ.get("CLAUDE_PLUGIN_DATA")
        os.environ["CLAUDE_PLUGIN_DATA"] = self.data

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CLAUDE_PLUGIN_DATA", None)
        else:
            os.environ["CLAUDE_PLUGIN_DATA"] = self._saved
        shutil.rmtree(self.data, ignore_errors=True)


class HookIsolation(DataDirTestCase):
    """D-001 / D-002: the notifier must never disturb the session."""

    def test_exits_zero_and_silent_for_every_verb(self):
        payloads = {
            "question": {"tool_input": {"questions": [{"question": "Which one?"}]}},
            "answered": {"tool_name": "AskUserQuestion"},
            "prompted": {"prompt": "next"},
            "permission": {"message": "Claude needs your permission"},
            "task": {"task_subject": "Add regression test"},
            "turn": {"last_assistant_message": "Done."},
            "failure": {"error": "rate_limit", "error_details": "429"},
        }
        for category, payload in payloads.items():
            with self.subTest(category=category):
                result = run_hook(category, dict(payload, cwd=os.getcwd(), session_id="abc123def"), self.data)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"", "hook wrote to stdout")

    def test_survives_garbage_stdin(self):
        for raw in ("", "not json", "[1,2,3]", "null", '{"unclosed":', b"\xff\xfe{\x9d"):
            with self.subTest(raw=raw):
                result = run_hook("turn", raw, self.data)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_survives_unknown_category(self):
        result = run_hook("not-a-category", {"cwd": os.getcwd()}, self.data)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_no_arguments_is_a_noop(self):
        result = subprocess.run([sys.executable, NOTIFY], input=b"{}", capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")


class StdinDecoding(unittest.TestCase):
    """Claude Code writes UTF-8; Windows Python reads piped stdin as cp1252."""

    def _windows_stdin(self, raw):
        # Exactly what Python 3 on a Western-locale Windows gives a hook process.
        return io.TextIOWrapper(io.BytesIO(raw), encoding="cp1252", errors="surrogateescape")

    def test_non_ascii_question_survives_an_ansi_code_page(self):
        question = "اختر ❓ ─┐ layout — 日本語?"
        raw = json.dumps({"tool_input": {"questions": [{"question": question}]}},
                         ensure_ascii=False).encode("utf-8")
        parsed = notify.read_payload(self._windows_stdin(raw))
        self.assertEqual(parsed["tool_input"]["questions"][0]["question"], question)

    def test_utf8_bom_is_tolerated(self):
        parsed = notify.read_payload(self._windows_stdin(b'\xef\xbb\xbf{"message": "hi"}'))
        self.assertEqual(parsed, {"message": "hi"})

    def test_invalid_utf8_degrades_instead_of_raising(self):
        parsed = notify.read_payload(self._windows_stdin(b'{"message": "bad \xff byte"}'))
        self.assertIn("bad", parsed["message"])

    def test_text_only_stream_still_works(self):
        self.assertEqual(notify.read_payload(io.StringIO('{"a": 1}')), {"a": 1})


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

    def test_clips_at_a_word_boundary(self):
        cleaned = render.clean("alpha beta gamma delta epsilon zeta eta theta", 30)
        self.assertLessEqual(len(cleaned), 30)
        self.assertTrue(cleaned.endswith("…"))
        self.assertIn(cleaned[:-1].split(" ")[-1], "alpha beta gamma delta epsilon zeta eta theta".split(" "))

    def test_strips_leading_dashes_so_text_is_never_an_option(self):
        self.assertFalse(render.clean("--help me", 220).startswith("-"))

    def test_handles_non_ascii(self):
        for value in ("emoji 🚀 here", "عربية RTL", "日本語"):
            self.assertIn(value.split()[0], render.clean(value, 220))

    def test_never_raises_on_odd_types(self):
        for value in (None, 12, [1, 2], {"a": 1}, object()):
            render.clean(value, 50)
            render.plain_text(value)


class MarkdownToPlainText(unittest.TestCase):

    def test_strips_common_markdown(self):
        message = ("## Summary\n\n**Fixed** the `render.py` bug - see [the docs](https://x.test/a).\n\n"
                   "```python\nprint('code')\n```\n- item one\n1. item two\n> quoted")
        text = render.plain_text(message)
        self.assertEqual(text, "Summary. Fixed the render.py bug - see the docs. item one. item two. quoted")

    def test_keeps_identifiers_with_underscores(self):
        self.assertEqual(render.plain_text("renamed my_var_name and __init__"),
                         "renamed my_var_name and __init__")

    def test_drops_table_rules_and_pipes(self):
        text = render.plain_text("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertNotIn("|", text)
        self.assertNotIn("---", text)

    def test_code_only_message_falls_back(self):
        built = render.build("turn", {"last_assistant_message": "```\nonly code\n```"}, "p", "t")
        self.assertEqual(built[2], "Claude finished and is waiting for you")


class Rendering(unittest.TestCase):

    def test_question_layout(self):
        built = render.build("question", {"tool_input": {"questions": [
            {"header": "Migrations", "question": "Which migration strategy?"}]}}, "proj", "abc123")
        self.assertIsNotNone(built)
        klass, title, body, attrib = built
        self.assertEqual(klass, render.ATTENTION)
        self.assertEqual(title, "❓ proj needs your answer")
        self.assertEqual(body, "Which migration strategy?")
        self.assertEqual(attrib, "session abc123")

    def test_title_without_project_names_claude(self):
        self.assertEqual(render.build("question", {}, "", "")[1], "❓ Claude needs your answer")

    def test_attribution_empty_without_session(self):
        self.assertEqual(render.build("task", {"task_subject": "x"}, "p", "")[3], "")

    def test_question_falls_back_to_header(self):
        built = render.build("question", {"tool_input": {"questions": [{"header": "Pick one"}]}}, "p")
        self.assertEqual(built[2], "Pick one")

    def test_multiple_questions_are_counted_and_survive_clipping(self):
        questions = [{"question": "word " * 80}, {"question": "b"}, {"question": "c"}]
        body = render.build("question", {"tool_input": {"questions": questions}}, "p")[2]
        self.assertTrue(body.endswith("(+2 more)"))
        self.assertLessEqual(len(body), render.BODY_LIMIT)

    def test_generic_permission_message_is_replaced(self):
        body = render.build("permission", {"message": "Claude needs your permission"}, "p")[2]
        self.assertNotEqual(body.lower(), "claude needs your permission")
        self.assertIn("terminal", body)

    def test_specific_permission_message_is_kept(self):
        body = render.build("permission", {"message": "Claude needs your permission to use Bash"}, "p")[2]
        self.assertEqual(body, "Claude needs your permission to use Bash")

    def test_task_uses_task_subject(self):
        built = render.build("task", {"task_subject": "Add regression test"}, "Cluster2")
        self.assertEqual(built[0], render.INFORMATIONAL)
        self.assertEqual(built[1], "☑️ Cluster2 finished a task")
        self.assertEqual(built[2], "Add regression test")

    def test_turn_body_is_plain_text(self):
        built = render.build("turn", {"last_assistant_message": "**Done.** All `42` tests pass."}, "p")
        self.assertEqual(built[1], "✅ p is done")
        self.assertEqual(built[2], "Done. All 42 tests pass.")

    def test_failure_is_humanised_without_repeating_itself(self):
        built = render.build("failure", {"error": "rate_limit",
                                         "last_assistant_message": "API Error: Rate limit reached"}, "p")
        self.assertEqual(built[0], render.ATTENTION)
        self.assertEqual(built[1], "❌ p hit an error")
        self.assertEqual(built[2], "Rate limit reached")

    def test_failure_combines_label_and_new_detail(self):
        built = render.build("failure", {"error": "server_error", "error_details": "HTTP 529 from upstream"}, "p")
        self.assertEqual(built[2], "API server error — HTTP 529 from upstream")

    def test_failure_without_detail_still_renders(self):
        self.assertEqual(render.build("failure", {"error": "overloaded"}, "p")[2], "The API is overloaded")
        self.assertEqual(render.build("failure", {"error": "brand_new_code"}, "p")[2], "Brand new code")
        self.assertEqual(render.build("failure", {}, "p")[2], "Unknown error")

    def test_long_project_name_is_clipped(self):
        title = render.build("turn", {}, "p" * 200)[1]
        self.assertLessEqual(len(title), render.TITLE_LIMIT)

    def test_unknown_category_returns_none(self):
        self.assertIsNone(render.build("nope", {"task_subject": "x"}, "p"))

    def test_empty_body_returns_none(self):
        self.assertIsNone(render.build("task", {"task_subject": "   "}, "p"))

    def test_every_category_is_classified(self):
        for category, (klass, icon, template) in render.CATEGORIES.items():
            self.assertIn(klass, (render.ATTENTION, render.INFORMATIONAL))
            self.assertTrue(icon.strip())
            self.assertIn("{who}", template)


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

    def test_group_key_is_session_scoped(self):
        one = identity.group_key({"session_id": "aaaaaaaa"}, "task")
        two = identity.group_key({"session_id": "bbbbbbbb"}, "task")
        self.assertNotEqual(one, two)


class QuestionDeduplication(DataDirTestCase):
    """D-013: one AskUserQuestion produces exactly one notification."""

    SESSION = "2ecaaa4e-84f3-4dd3-8ca7-bacb5c96cbb9"

    def permission_reason(self, session=None):
        # The exact payload Claude Code sent for a question, captured live.
        payload = {"session_id": session or self.SESSION, "hook_event_name": "Notification",
                   "message": "Claude needs your permission", "notification_type": "permission_prompt"}
        return policy.suppression_reason("permission", payload, dict(policy.DEFAULTS))

    def ask(self, **extra):
        payload = dict({"session_id": self.SESSION, "cwd": os.getcwd(),
                        "tool_input": {"questions": [{"question": "Which?"}]}}, **extra)
        self.assertEqual(run_hook("question", payload, self.data).returncode, 0)

    def test_real_permission_prompt_notifies(self):
        self.assertIsNone(self.permission_reason())

    def test_question_suppresses_its_follow_up_permission_prompt(self):
        self.ask()
        self.assertIsNotNone(self.permission_reason())

    def test_other_sessions_are_unaffected(self):
        self.ask()
        self.assertIsNone(self.permission_reason("some-other-session"))

    def test_answering_clears_the_question(self):
        self.ask()
        run_hook("answered", {"session_id": self.SESSION, "tool_name": "AskUserQuestion"}, self.data)
        self.assertIsNone(self.permission_reason())

    def test_turn_end_and_failure_clear_the_question(self):
        for verb in ("turn", "failure"):
            with self.subTest(verb=verb):
                self.ask()
                run_hook(verb, {"session_id": self.SESSION, "cwd": os.getcwd()}, self.data)
                self.assertIsNone(self.permission_reason())

    def test_new_prompt_clears_the_question(self):
        # Covers a question dismissed with Esc, where PostToolUse never fires.
        self.ask()
        run_hook(state.PROMPTED, {"session_id": self.SESSION, "prompt": "never mind"}, self.data)
        self.assertIsNone(self.permission_reason())

    def test_marker_expires(self):
        self.assertTrue(state.mark_question(self.SESSION))
        old = time.time() - state.QUESTION_WINDOW - 5
        os.utime(state._marker(self.SESSION), (old, old))
        self.assertIsNone(self.permission_reason())

    def test_suppressed_question_does_not_silence_the_prompt(self):
        # No question toast was sent, so the permission prompt is the only alert left.
        with open(os.path.join(self.data, policy.CONFIG_FILENAME), "w", encoding="utf-8") as handle:
            json.dump({"categories": {"question": False}}, handle)
        self.ask()
        self.assertIsNone(self.permission_reason())
        self.ask(agent_id="agent-1")
        self.assertIsNone(self.permission_reason())

    def test_marker_lives_under_plugin_data(self):
        state.mark_question(self.SESSION)
        self.assertTrue(os.path.abspath(state._marker(self.SESSION)).startswith(os.path.abspath(self.data)))
        self.assertFalse(os.path.abspath(state._marker(self.SESSION)).startswith(os.path.dirname(HOOKS)))

    def test_orphaned_markers_are_swept(self):
        os.makedirs(state.state_dir(), exist_ok=True)
        orphan = os.path.join(state.state_dir(), "question-orphan")
        open(orphan, "w").close()
        old = time.time() - state.STALE_AFTER - 60
        os.utime(orphan, (old, old))
        state.mark_question(self.SESSION)
        self.assertFalse(os.path.exists(orphan))

    def test_unusable_state_fails_toward_notifying(self):
        blocker = os.path.join(self.data, "not-a-dir")
        open(blocker, "w").close()
        os.environ["CLAUDE_PLUGIN_DATA"] = blocker
        self.assertFalse(state.mark_question(self.SESSION))
        self.assertFalse(state.question_pending(self.SESSION))
        self.assertFalse(state.clear_question(self.SESSION))
        for hostile in (None, "", "../../etc", 42):
            self.assertFalse(state.question_pending(hostile))


class NeverReplace(DataDirTestCase):
    """A new notification never replaces or removes an older one; only user actions withdraw."""

    def setUp(self):
        super().setUp()
        self.sent, self.removed = [], []
        self._send, self._remove = backends.send, backends.remove
        backends.send = lambda **kwargs: self.sent.append(kwargs) or True
        backends.remove = lambda keys: self.removed.append(list(keys)) or True

    def tearDown(self):
        backends.send, backends.remove = self._send, self._remove
        super().tearDown()

    def test_notifications_never_withdraw_anything(self):
        base = {"session_id": "s-never-replace", "cwd": os.getcwd()}
        # permission first: once the question is notified it would be suppressed (D-013).
        payloads = [
            ("permission", {"message": "Claude needs your permission to use Bash"}),
            ("question", {"tool_input": {"questions": [{"question": "Q?"}]}}),
            ("task", {"task_subject": "x"}),
            ("turn", {"last_assistant_message": "done"}),
            ("failure", {"error": "rate_limit"}),
        ]
        for category, extra in payloads:
            notify.deliver(category, dict(base, **extra), dict(policy.DEFAULTS))
        self.assertEqual(len(self.sent), len(payloads))
        self.assertTrue(all(not call.get("remove_keys") for call in self.sent))
        self.assertEqual(self.removed, [])

    def test_only_user_actions_withdraw(self):
        base = {"session_id": "s-never-replace"}
        notify.deliver(state.ANSWERED, dict(base, tool_name="AskUserQuestion"), dict(policy.DEFAULTS))
        notify.deliver(state.PROMPTED, dict(base, prompt="next"), dict(policy.DEFAULTS))
        self.assertEqual(self.removed[0], [identity.group_key(base, "question")])
        self.assertEqual(set(self.removed[1]),
                         {identity.group_key(base, name) for name in ("question", "permission", "turn", "failure")})
        self.assertEqual(self.sent, [])


class Suppression(DataDirTestCase):

    def setUp(self):
        super().setUp()
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


class Configuration(DataDirTestCase):

    def test_defaults_when_no_file_exists(self):
        config = policy.load()
        self.assertEqual(config["enabled"], True)
        self.assertEqual({name for name, on in config["persistent"].items() if on},
                         {"question", "permission", "turn", "failure"})

    def test_waiting_categories_persist_and_tasks_do_not(self):
        config = policy.load()
        for category in ("question", "permission", "turn", "failure"):
            self.assertTrue(policy.wants_persistent(category, config), category)
        self.assertFalse(policy.wants_persistent("task", config))
        self.assertFalse(policy.wants_persistent("task", {"persistent": "garbage"}))

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


class WindowsBackend(unittest.TestCase):

    def test_text_travels_only_in_the_environment(self):
        captured = {}

        def fake_run(argv, env=None, creationflags=0):
            captured["argv"], captured["env"] = argv, env
            return True

        original = backends._run
        backends._run = fake_run
        try:
            backends._send_windows("powershell.exe", '$(evil) "x"', "`body`", "session a",
                                   True, False, False, "claude-a-question", ["claude-a-permission"])
        finally:
            backends._run = original
        self.assertFalse(any("evil" in part or "body" in part for part in captured["argv"]))
        self.assertEqual(captured["env"]["CCN_TITLE"], '$(evil) "x"')
        self.assertEqual(captured["env"]["CCN_ATTENTION"], "1")
        self.assertEqual(captured["env"]["CCN_PERSISTENT"], "0")
        self.assertEqual(captured["env"]["CCN_REMOVE"], "claude-a-permission")
        self.assertEqual(captured["env"]["CCN_GROUP"], "claude-a-question")

    def test_every_toast_gets_its_own_tag_so_none_is_replaced(self):
        tags = []
        original = backends._run
        backends._run = lambda argv, env=None, creationflags=0: tags.append(env["CCN_TAG"]) or True
        try:
            for _ in range(3):
                backends._send_windows("powershell.exe", "t", "b", "", False, False, True, "claude-a-turn", ())
        finally:
            backends._run = original
        self.assertEqual(len(set(tags)), 3)
        self.assertNotIn("claude-a-turn", tags)

    def test_linux_sends_no_replace_in_place_hints(self):
        captured = {}
        original = backends._run
        backends._run = lambda argv, env=None, creationflags=0: captured.setdefault("argv", argv) is not None
        try:
            backends._send_linux("notify-send", "t", "b", "", False, False, True, "claude-a-turn", ())
        finally:
            backends._run = original
        self.assertFalse(any("synchronous" in part or "stack-tag" in part for part in captured["argv"]))

    def test_persistence_brings_a_visible_close_button(self):
        with open(os.path.join(HOOKS, "win_toast.ps1"), "r", encoding="utf-8") as handle:
            script = handle.read()
        # The icon lives in the header only.
        self.assertNotIn("appLogoOverride", script)
        self.assertIn("IconUri", script)
        # Windows silently ignores scenario="reminder" without a VISIBLE button;
        # an action placed only in the context menu does not count (verified live).
        self.assertIn('scenario="reminder"', script)
        self.assertIn('<action content="Close" arguments="dismiss" activationType="background"/>', script)
        self.assertNotIn('activationType="background" placement=', script)
        # Stale toasts are withdrawn by group, never replaced by tag.
        self.assertIn("RemoveGroup", script)

    def test_icon_is_a_png(self):
        with open(os.path.join(HOOKS, "icon.png"), "rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")

    @unittest.skipUnless(platform.system() == "Windows", "Windows PowerShell parser")
    def test_toast_script_parses(self):
        shell = backends._powershell()
        if not shell:
            self.skipTest("powershell.exe not found")
        command = ("$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
                   "$env:CCN_SCRIPT, [ref]$null, [ref]$errors); $errors.Count")
        env = dict(os.environ, CCN_SCRIPT=os.path.join(HOOKS, "win_toast.ps1"))
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(result.stdout.strip(), "0", result.stdout + result.stderr)


class HooksManifest(unittest.TestCase):
    """The manifest is the safety contract; assert it structurally."""

    def setUp(self):
        path = os.path.join(HOOKS, "hooks.json")
        with open(path, "r", encoding="utf-8") as handle:
            self.manifest = json.load(handle)

    def hooks(self):
        for event, groups in self.manifest["hooks"].items():
            for group in groups:
                for hook in group["hooks"]:
                    yield event, group, hook

    def test_every_hook_is_async(self):
        for event, _group, hook in self.hooks():
            self.assertTrue(hook.get("async"), "{0} hook is not async - it could block Claude".format(event))

    def test_every_hook_uses_exec_form(self):
        for event, _group, hook in self.hooks():
            self.assertIn("args", hook, "{0} hook is shell form".format(event))

    def test_every_hook_has_a_timeout(self):
        for _event, _group, hook in self.hooks():
            self.assertIsInstance(hook.get("timeout"), int)

    def test_expected_events_only(self):
        self.assertEqual(
            sorted(self.manifest["hooks"]),
            ["Notification", "PostToolUse", "PreToolUse", "Stop", "StopFailure", "TaskCompleted",
             "UserPromptSubmit"])

    def test_no_sessionstart_hook(self):
        self.assertNotIn("SessionStart", self.manifest["hooks"])

    def test_verbs_match_render_and_state(self):
        verbs = {hook["args"][-1] for _event, _group, hook in self.hooks()}
        self.assertEqual(verbs, set(render.CATEGORIES) | set(state.CONTROL_VERBS))

    def test_question_is_bracketed_on_the_same_tool(self):
        verbs = {(event, group.get("matcher"), hook["args"][-1]) for event, group, hook in self.hooks()}
        self.assertIn(("PreToolUse", "AskUserQuestion", "question"), verbs)
        self.assertIn(("PostToolUse", "AskUserQuestion", state.ANSWERED), verbs)

    def test_matcher_omitted_on_events_without_matcher_support(self):
        for event in ("Stop", "StopFailure", "TaskCompleted", "UserPromptSubmit"):
            for group in self.manifest["hooks"][event]:
                self.assertNotIn("matcher", group, "{0} has no matcher support; omit it".format(event))


if __name__ == "__main__":
    unittest.main(verbosity=2)
