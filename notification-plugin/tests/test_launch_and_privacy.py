#!/usr/bin/env python3
"""notification plugin - interpreter fallback (D-016), privacy mode (NTF-P1-02),
secret masking, doctor reporting and Windows identity removal.

Stdlib only, no desktop required:

    python -m pytest -q -p no:cacheprovider
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

HOOKS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
NOTIFY = os.path.join(HOOKS, "notify.py")
sys.path.insert(0, HOOKS)

import backends   # noqa: E402
import notify     # noqa: E402
import policy     # noqa: E402
import render     # noqa: E402
import state      # noqa: E402


def run_hook(category, payload, data_dir, extra_env=None):
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_DATA"] = data_dir
    env["SSH_CONNECTION"] = "test 0 test 0"      # never fire a real notification
    env.pop("CLAUDE_PLUGIN_OPTION_TITLE_ONLY", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, NOTIFY, category],
                          input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, timeout=30)


class DataDir(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="ccn-test-")
        self._saved = {k: os.environ.get(k) for k in ("CLAUDE_PLUGIN_DATA", policy.USER_OPTION_TITLE_ONLY)}
        os.environ["CLAUDE_PLUGIN_DATA"] = self.data
        os.environ.pop(policy.USER_OPTION_TITLE_ONLY, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.data, ignore_errors=True)


class InterpreterFallbackManifest(unittest.TestCase):
    """D-016: every event is launched under python3, python and py -3, in exec form."""

    def setUp(self):
        with open(os.path.join(HOOKS, "hooks.json"), "r", encoding="utf-8") as handle:
            self.manifest = json.load(handle)

    def test_every_event_tries_all_three_interpreter_names(self):
        for event, groups in self.manifest["hooks"].items():
            for group in groups:
                launchers = [(h["command"], tuple(h["args"][:-2])) for h in group["hooks"]]
                self.assertEqual(launchers, [("python3", ()), ("python", ()), ("py", ("-3",))], event)

    def test_all_launchers_of_an_event_run_the_same_verb(self):
        for event, groups in self.manifest["hooks"].items():
            for group in groups:
                verbs = {tuple(h["args"][-2:]) for h in group["hooks"]}
                self.assertEqual(len(verbs), 1, event)
                script = next(iter(verbs))[0]
                self.assertEqual(script, "${CLAUDE_PLUGIN_ROOT}/hooks/notify.py")

    def test_no_launcher_goes_through_a_shell(self):
        for groups in self.manifest["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertNotIn(" ", hook["command"])
                    self.assertNotIn("shell", hook)
                    self.assertTrue(hook["async"])

    def test_doctor_knows_the_same_names(self):
        self.assertEqual(notify.HOOK_INTERPRETERS, ("python3", "python", "py"))


class OneEventOneRun(DataDir):
    """Sibling launches of one event deliver once; distinct events still deliver."""

    def test_first_claim_wins_and_siblings_back_off(self):
        self.assertTrue(state.claim("turn", b'{"a": 1}'))
        self.assertFalse(state.claim("turn", b'{"a": 1}'))
        self.assertFalse(state.claim("turn", b'{"a": 1}'))

    def test_different_payload_or_verb_is_a_different_event(self):
        self.assertTrue(state.claim("turn", b'{"a": 1}'))
        self.assertTrue(state.claim("turn", b'{"a": 2}'))
        self.assertTrue(state.claim("failure", b'{"a": 1}'))

    def test_stale_claim_is_taken_over(self):
        self.assertTrue(state.claim("turn", b"x"))
        for name in os.listdir(state.state_dir()):
            if name.startswith("claim-"):
                old = time.time() - state.CLAIM_WINDOW - 5
                os.utime(os.path.join(state.state_dir(), name), (old, old))
        self.assertTrue(state.claim("turn", b"x"))

    def test_unusable_state_fails_toward_notifying(self):
        blocker = os.path.join(self.data, "not-a-dir")
        open(blocker, "w").close()
        os.environ["CLAUDE_PLUGIN_DATA"] = blocker
        self.assertTrue(state.claim("turn", b"x"))
        self.assertTrue(state.claim("turn", b"x"))

    def test_sibling_hook_processes_record_one_run(self):
        payload = {"session_id": "s-sibling", "cwd": os.getcwd(), "last_assistant_message": "done"}
        for _ in range(3):
            result = run_hook("turn", payload, self.data)
            self.assertEqual((result.returncode, result.stdout), (0, b""))
        claims = [n for n in os.listdir(state.state_dir()) if n.startswith("claim-")]
        self.assertEqual(len(claims), 1)
        last = state.last_run()
        self.assertEqual(last["verb"], "turn")
        self.assertTrue(last["python"])

    def test_claims_are_swept(self):
        os.makedirs(state.state_dir(), exist_ok=True)
        orphan = os.path.join(state.state_dir(), "claim-orphan")
        open(orphan, "w").close()
        old = time.time() - state.CLAIM_WINDOW - 60
        os.utime(orphan, (old, old))
        state.claim("turn", b"fresh")
        self.assertFalse(os.path.exists(orphan))


class PrivacyMode(DataDir):
    """NTF-P1-02: title-only mode keeps every payload string off the screen."""

    SECRET_QUESTION = "Deploy with key sk-ant-api03-abcdefghijklmnopqrstuvwx to acme-prod?"

    PAYLOADS = {
        "question": {"tool_input": {"questions": [{"question": SECRET_QUESTION}, {"question": "b"}]}},
        "permission": {"message": "Claude needs your permission to use Bash: rm customer.csv"},
        "task": {"task_subject": "Email Jane Doe about invoice 4471"},
        "turn": {"last_assistant_message": "The password for acme is hunter2-very-secret"},
        "failure": {"error": "rate_limit", "last_assistant_message": "API Error: internal detail"},
    }

    def test_title_only_bodies_carry_no_payload_text(self):
        for category, payload in self.PAYLOADS.items():
            with self.subTest(category=category):
                _klass, title, body, _attrib = render.build(category, payload, project="acme", tag="abc",
                                                            title_only=True)
                self.assertEqual(body, render.GENERIC_BODIES[category])
                self.assertIn("acme", title)
                for value in json.dumps(payload).split('"'):
                    if len(value) > 12:
                        self.assertNotIn(value, body)

    def test_full_mode_masks_secret_shaped_text(self):
        _k, _t, body, _a = render.build("question", self.PAYLOADS["question"])
        self.assertNotIn("sk-ant-api03", body)
        self.assertIn("[REDACTED]", body)
        self.assertIn("(+1 more)", body)

    def test_full_mode_is_still_the_default(self):
        self.assertFalse(policy.title_only(dict(policy.DEFAULTS)))
        _k, _t, body, _a = render.build("task", self.PAYLOADS["task"])
        self.assertIn("Jane Doe", body)

    def test_user_config_option_turns_it_on(self):
        for value in ("true", "1", "TRUE", " yes "):
            os.environ[policy.USER_OPTION_TITLE_ONLY] = value
            self.assertTrue(policy.title_only(dict(policy.DEFAULTS)), value)

    def test_config_file_turns_it_on_and_user_config_false_cannot_undo_it(self):
        with open(policy.config_path(), "w", encoding="utf-8") as handle:
            json.dump({"title_only": True}, handle)
        config = policy.load()
        self.assertTrue(policy.title_only(config))
        os.environ[policy.USER_OPTION_TITLE_ONLY] = "false"
        self.assertTrue(policy.title_only(config))

    def test_hook_path_honours_the_option(self):
        sent = []
        original = backends.send
        backends.send = lambda **kwargs: sent.append(kwargs) or True
        try:
            os.environ[policy.USER_OPTION_TITLE_ONLY] = "true"
            notify.deliver("turn", dict(self.PAYLOADS["turn"], session_id="s-priv", cwd=os.getcwd()),
                           dict(policy.DEFAULTS))
        finally:
            backends.send = original
        self.assertEqual(sent[0]["body"], render.GENERIC_BODIES["turn"])

    def test_every_category_has_a_generic_body(self):
        self.assertEqual(set(render.GENERIC_BODIES), set(render.CATEGORIES))

    def test_manifest_declares_the_option(self):
        manifest = os.path.join(os.path.dirname(HOOKS), ".claude-plugin", "plugin.json")
        with open(manifest, "r", encoding="utf-8") as handle:
            option = json.load(handle)["userConfig"]["title_only"]
        self.assertEqual(option["type"], "boolean")
        self.assertIs(option["default"], False)
        self.assertLessEqual(set(option), {"type", "title", "description", "required", "default",
                                           "sensitive", "min", "max"})


class Doctor(DataDir):

    def doctor(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            notify.run_doctor(send_tests=False, as_json="--json" in args)
        return out.getvalue()

    def test_report_names_hook_interpreters_and_last_run(self):
        text = self.doctor()
        self.assertIn("Hook interpreters", text)
        for name in ("python3", "python", "py -3"):
            self.assertIn(name, text)
        self.assertIn("last run", text)
        self.assertIn("content", text)

    def test_report_shows_the_interpreter_that_handled_the_last_event(self):
        state.record_run("turn")
        self.assertIn(sys.executable, self.doctor())

    def test_json_report_carries_interpreters_and_privacy(self):
        data = json.loads(self.doctor("--json"))
        self.assertEqual([row["name"] for row in data["hook_interpreters"]], ["python3", "python", "py"])
        self.assertIn("title_only", data)
        self.assertIn("last_hook_run", data)

    def test_warns_when_no_interpreter_is_usable(self):
        original = notify.hook_interpreters
        notify.hook_interpreters = lambda: [(n, None, "") for n in notify.HOOK_INTERPRETERS]
        try:
            self.assertIn("no usable interpreter", self.doctor())
        finally:
            notify.hook_interpreters = original

    def test_probe_accepts_a_real_interpreter(self):
        self.assertEqual(notify.probe_interpreter(sys.executable, "python"), "")

    def test_probe_explains_a_non_python_executable(self):
        problem = notify.probe_interpreter(os.path.join(self.data, "missing.exe"), "python")
        self.assertTrue(problem.startswith("does not start"), problem)

    def test_unusable_names_are_reported(self):
        rows = notify.hook_interpreters(probe=lambda path, name: "starts no Python")
        self.assertTrue(all(problem for _name, path, problem in rows if path))


class WindowsIdentityRemoval(unittest.TestCase):

    class FakeWinreg:
        HKEY_CURRENT_USER = "HKCU"

        def __init__(self, missing=False):
            self.calls, self.missing = [], missing

        def DeleteKey(self, root, key):
            self.calls.append((root, key))
            if self.missing:
                raise FileNotFoundError(key)

    def test_removes_only_the_plugins_hkcu_key(self):
        fake = self.FakeWinreg()
        message = notify.uninstall_windows_identity(fake)
        self.assertEqual(fake.calls, [("HKCU", r"Software\Classes\AppUserModelId\TaqaTechno.ClaudeCode.Notifications")])
        self.assertTrue(message.startswith("removed"))

    def test_missing_key_is_not_an_error(self):
        self.assertTrue(notify.uninstall_windows_identity(self.FakeWinreg(missing=True)).startswith("nothing to do"))

    def test_key_matches_the_toast_script(self):
        with open(os.path.join(HOOKS, "win_toast.ps1"), "r", encoding="utf-8") as handle:
            script = handle.read()
        self.assertIn("$AppId         = 'TaqaTechno.ClaudeCode.Notifications'", script)
        self.assertIn(r"HKCU:\Software\Classes\AppUserModelId\$AppId", script)


class DoctorFlags(DataDir):

    def run_notify(self, *args):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data, SSH_CONNECTION="test 0 test 0")
        return subprocess.run([sys.executable, NOTIFY] + list(args), capture_output=True,
                              text=True, env=env, timeout=60)

    def test_write_config_works_after_doctor(self):
        result = self.run_notify("--doctor", "--write-config")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.data, "config.json")), result.stdout)

    def test_doctor_json_is_valid(self):
        result = self.run_notify("--doctor", "--json", "--no-test")
        self.assertIn("hook_interpreters", json.loads(result.stdout))


class VendoredRuntime(unittest.TestCase):

    def test_hooklib_is_vendored(self):
        self.assertTrue(os.path.isfile(os.path.join(HOOKS, "_vendor", "hooklib.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
