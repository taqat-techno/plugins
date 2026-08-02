"""WP-7 — the merged UserPromptSubmit hook, and the N-01 regression.

N-01, in one paragraph
----------------------
``prompt_retrieval_reminder.domain_probe()`` built
``GET /api/search?query=…&top_k=1&compact=true`` with **no project**. From
ragtools v3.0.0 that is a hard ``HTTP 422 SCOPE_UNRESOLVED``, so the probe
always errored, ``main()`` took ``if err: silent_pass(err)``, and
``inject_reminder()`` was unreachable. The hook's own log:

    reminder-injected                  380   last  2026-07-28T08:23:16Z
    silent-pass:probe-error:http-422   105   first 2026-07-29T07:55:59Z

Four days of active use, 105 probes, zero injections — and invisible, because an
advisory hook fails open and "the probe errored" looks exactly like "nothing
matched".

``TestTheProbeIsScoped`` is the regression. It reads the shipped source of both
the merged hook and the retired one, so it fails against the baseline for the
right reason and cannot pass by accident.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT, is_baseline, read  # type: ignore[import-not-found]  # noqa: E402

HOOK = PLUGIN_ROOT / "hooks" / "context_inject.py"


def run_hook(prompt: str, cwd: str, timeout: int = 30) -> str:
    """Run the hook as Claude Code does. Returns stdout (empty = silent pass)."""
    payload = json.dumps({"hook_event_name": "UserPromptSubmit",
                          "user_prompt": prompt, "cwd": cwd})
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                          capture_output=True, text=True, timeout=timeout)
    assert proc.returncode == 0, f"advisory hook must always exit 0, got {proc.returncode}"
    return proc.stdout.strip()


def injected_text(stdout: str) -> str:
    if not stdout:
        return ""
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


class TestTheProbeIsScoped(unittest.TestCase):
    """The N-01 regression, asserted against shipped source."""

    def test_the_merged_hook_passes_a_project_to_the_probe(self):
        src = read("hooks/context_inject.py")
        self.assertTrue(src, "hooks/context_inject.py is missing")
        start = src.find("def domain_probe")
        self.assertGreater(start, 0, "domain_probe not found")
        body = src[start:start + 1800]
        self.assertIn('"project"', body,
                      "the relevance probe still omits project= — this is N-01")

    def test_domain_probe_requires_a_project_argument(self):
        src = read("hooks/context_inject.py")
        self.assertIn("def domain_probe(prompt: str, project: str)", src,
                      "the probe signature must make scope non-optional")

    def test_a_422_after_scoping_is_logged_distinctly(self):
        """The old code swallowed every 422 into generic probe noise. A 422
        that arrives *after* a project was passed is a real defect and must be
        distinguishable in the log."""
        src = read("hooks/context_inject.py")
        self.assertIn("http-422-after-scope", src)

    def test_the_retired_hook_demonstrably_lacked_scope(self):
        """Negative control against the actual pre-fix source."""
        baseline = PLUGIN_ROOT / "tests" / "baseline_v0.17.0" / "hooks" / "prompt_retrieval_reminder.py"
        if not baseline.is_file():
            self.skipTest("baseline snapshot missing")
        src = baseline.read_text(encoding="utf-8")
        start = src.find("def domain_probe")
        self.assertGreater(start, 0)
        body = src[start:start + 1200]
        self.assertIn("urlencode", body)
        self.assertNotIn(
            '"project"', body,
            "the v0.17.0 probe unexpectedly contains a project argument — the "
            "snapshot has been contaminated and this control is vacuous",
        )


class TestNoNetworkOnUnrelatedPrompts(unittest.TestCase):
    def test_an_unrelated_prompt_injects_nothing(self):
        out = run_hook("Please rewrite this email to sound more polite.",
                       str(PLUGIN_ROOT))
        self.assertEqual(out, "", "an unrelated prompt must not inject context")

    def test_a_current_context_question_injects_nothing(self):
        out = run_hook("What does this code above do?", str(PLUGIN_ROOT))
        self.assertEqual(out, "")

    def test_an_operational_question_injects_nothing(self):
        """D-027's classifier: machine-state questions answer from the
        filesystem, not the index."""
        for prompt in ("How do I restart the rag service?",
                       "What's running on port 21420?",
                       "Where is the config file on my disk?"):
            self.assertEqual(run_hook(prompt, str(PLUGIN_ROOT)), "",
                             f"operational prompt injected context: {prompt!r}")


class TestInjectedBlockNeverTeachesAnUnscopedCall(unittest.TestCase):
    """Whatever path the hook takes, it must not print the failing call."""

    def _all_blocks(self) -> list[str]:
        src = read("hooks/context_inject.py")
        start = src.find("def build_block")
        end = src.find("def inject(", start)
        return [src[start:end]]

    def test_every_suggested_call_carries_a_project(self):
        for body in self._all_blocks():
            for line in body.splitlines():
                if "search_knowledge_base(" in line and "unscoped-example-ok" not in line:
                    self.assertIn(
                        "project", line,
                        f"build_block emits an unscoped call: {line.strip()!r}",
                    )

    def test_the_no_scope_path_points_at_list_projects(self):
        """'No project resolved' must route to list_projects(), never to an
        unscoped search — which is what the old neutral notice implied."""
        body = self._all_blocks()[0]
        self.assertIn("list_projects()", body)
        self.assertIn("422", body)

    def test_the_ambiguous_path_offers_a_union_not_a_guess(self):
        body = self._all_blocks()[0]
        self.assertIn("projects=[", body)


class TestModeAndFreshnessSurface(unittest.TestCase):
    """The two facts that stop a confident-and-wrong answer."""

    def test_docs_mode_produces_an_explicit_warning(self):
        src = read("hooks/context_inject.py")
        self.assertIn("DOCS mode", src)
        self.assertIn("means nothing here", src,
                      "an empty code result in docs mode must be named as "
                      "uninformative, not as absence")

    def test_stale_state_produces_a_verification_instruction(self):
        src = read("hooks/context_inject.py")
        self.assertIn("STALE", src)
        self.assertIn("working tree", src)


class TestFailOpenIsStructural(unittest.TestCase):
    """D-031: an advisory hook must never be able to block a prompt."""

    def test_malformed_stdin_exits_zero(self):
        for payload in ("", "   ", "not json", "[]", '{"user_prompt": 42}'):
            proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0,
                             f"payload {payload!r} produced exit {proc.returncode}")

    def test_the_hook_is_registered_advisory(self):
        launcher = read("hooks/hook_launcher.py")
        self.assertIn('"context-inject": ("context_inject.py", "advisory")', launcher,
                      "the merged hook must be registered advisory, so every exit "
                      "is normalised to 0")

    def test_retired_target_names_remain_mapped(self):
        launcher = read("hooks/hook_launcher.py")
        for legacy in ("retrieval-reminder", "project-focus"):
            self.assertIn(f'"{legacy}"', launcher,
                          f"{legacy} must stay mapped for one release so a stale "
                          "hooks.json cannot break a session")


class TestHooksJsonShape(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(read("hooks/hooks.json") or "{}")

    def test_exactly_one_user_prompt_submit_hook(self):
        ups = self.data.get("hooks", {}).get("UserPromptSubmit", [])
        self.assertEqual(len(ups), 1,
                         "the two injectors were merged; two entries means one "
                         "of them is still firing")

    def test_the_inline_bootstrap_is_preserved(self):
        """D-031's mechanism: the `-c` form takes no script-file argument, so a
        missing script can never produce the blocking exit 2."""
        ups = self.data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("python3 -c", ups)
        self.assertIn("py -3 -c", ups, "the interpreter chain must be intact")
        self.assertIn(" context-inject ", ups)

    def test_pretooluse_guard_is_untouched(self):
        pre = self.data.get("hooks", {}).get("PreToolUse", [])
        self.assertEqual(len(pre), 1)
        self.assertIn(" lock-conflict ", pre[0]["hooks"][0]["command"])


class TestBaselineDiffers(unittest.TestCase):
    def test_the_baseline_has_two_injectors_and_no_merged_hook(self):
        if not is_baseline():
            self.skipTest("only meaningful against the baseline snapshot")
        self.assertEqual(read("hooks/context_inject.py"), "",
                         "the baseline should not contain the merged hook")


if __name__ == "__main__":
    unittest.main(verbosity=2)
