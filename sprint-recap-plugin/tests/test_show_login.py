#!/usr/bin/env python3
"""`show_login` behaviour, proven without a browser.

The two claims worth testing are the ones that were broken before the flag
existed:

  1. a show_login step must start SIGNED OUT, or the app redirects away from
     the login screen before a frame of it is recorded;
  2. the password must come from the config, never from the step script, so
     nothing that gets reviewed or shared carries a working credential.

Both are observable at the seam between this module and Playwright, so the
doubles below record what production code ASKED FOR rather than standing in
for a real browser.

    python tests/test_show_login.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import capture_steps  # noqa: E402


TARGET_CFG = {
    "base_url": "https://staging.example.test",
    "login": {
        "path": "/login",
        "username_selector": "input[name='email']",
        "password_selector": "input[name='password']",
        "submit_selector": "button[type='submit']",
        "success_selector": "[data-testid='shell-topbar']",
    },
}
CREDS = {"username": "qa.admin@example.test", "password": "s3cret-pw"}


class FakePage:
    def __init__(self):
        self.calls = []
        self.video = None

    def goto(self, url):
        self.calls.append(("goto", url))

    def fill(self, selector, value):
        self.calls.append(("fill", selector, value))

    def click(self, selector):
        self.calls.append(("click", selector))

    def wait_for_selector(self, selector, timeout=None):
        self.calls.append(("wait_for_selector", selector))

    def wait_for_load_state(self, state):
        self.calls.append(("wait_for_load_state", state))

    def wait_for_timeout(self, ms):
        self.calls.append(("wait_for_timeout", ms))

    def screenshot(self, path, full_page=False):
        Path(path).write_bytes(b"png")

    def set_default_timeout(self, ms):
        pass

    def on(self, event, handler):
        pass

    def close(self):
        pass


class FakeContext:
    def __init__(self, page, kwargs):
        self._page = page
        self.kwargs = kwargs

    def new_page(self):
        return self._page

    def set_default_timeout(self, ms):
        pass

    def close(self):
        pass


class FakeBrowser:
    """Records the kwargs every context was built with."""

    def __init__(self, page):
        self._page = page
        self.contexts = []

    def new_context(self, **kwargs):
        self.contexts.append(kwargs)
        return FakeContext(self._page, kwargs)


class Args:
    width = 1280
    height = 720
    timeout = 15000


class PerformLoginTests(unittest.TestCase):
    def test_navigate_false_does_not_goto(self):
        """A show_login step has already navigated to its own `start`."""
        page = FakePage()
        capture_steps.perform_login(page, TARGET_CFG, CREDS, 1000, navigate=False)
        self.assertEqual([c for c in page.calls if c[0] == "goto"], [])

    def test_navigate_true_goes_to_the_configured_login_path(self):
        page = FakePage()
        capture_steps.perform_login(page, TARGET_CFG, CREDS, 1000)
        self.assertIn(
            ("goto", "https://staging.example.test/login"), page.calls
        )

    def test_credentials_come_from_the_config(self):
        page = FakePage()
        capture_steps.perform_login(page, TARGET_CFG, CREDS, 1000, navigate=False)
        fills = {c[1]: c[2] for c in page.calls if c[0] == "fill"}
        self.assertEqual(fills["input[name='email']"], "qa.admin@example.test")
        self.assertEqual(fills["input[name='password']"], "s3cret-pw")


class CaptureStepContextTests(unittest.TestCase):
    """The regression that made the flag necessary."""

    def _capture(self, step, tmp: Path, creds=CREDS):
        page = FakePage()
        browser = FakeBrowser(page)
        row = capture_steps.capture_step(
            browser,
            {"work_item": 33605, "role": "tenant_admin"},
            step,
            TARGET_CFG,
            "C:/state/tenant-admin.json",
            tmp,
            Args(),
            [CREDS["password"]],
            creds,
        )
        return row, page, browser

    def test_show_login_step_gets_no_storage_state(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            row, page, browser = self._capture(
                {"id": "login", "caption": "Sign in", "start": "/login",
                 "show_login": True},
                Path(d),
            )
        self.assertIsNone(
            browser.contexts[0]["storage_state"],
            "a show_login step must start signed out, or /login redirects away",
        )
        self.assertEqual(row["status"], "ok")
        self.assertTrue(row["show_login"])
        # it typed the password, from the config
        self.assertIn(
            ("fill", "input[name='password']", "s3cret-pw"), page.calls
        )

    def test_ordinary_step_still_reuses_storage_state(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            row, page, browser = self._capture(
                {"id": "s1", "caption": "Open the catalogue", "start": "/catalogue"},
                Path(d),
            )
        self.assertEqual(
            browser.contexts[0]["storage_state"], "C:/state/tenant-admin.json"
        )
        self.assertFalse(row["show_login"])
        # no login flow was driven for an ordinary step
        self.assertEqual([c for c in page.calls if c[0] == "fill"], [])

    def test_show_login_without_credentials_fails_that_step_only(self):
        """A missing credential must not kill the whole run."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            row, _, _ = self._capture(
                {"id": "login", "caption": "Sign in", "start": "/login",
                 "show_login": True},
                Path(d),
                creds=None,
            )
        self.assertEqual(row["status"], "failed")
        self.assertIn("show_login", row["error"])


class GuideRenderingTests(unittest.TestCase):
    def test_guide_names_the_role_and_config_key_but_no_password(self):
        sys.path.insert(
            0, str(Path(__file__).resolve().parent.parent / "scripts")
        )
        import publish_guide  # noqa: PLC0415

        script = {
            "sprint": "Sprint 3",
            "target": "dev",
            "items": [{
                "work_item": 33605,
                "title": "Sign in",
                "role": "tenant_admin",
                "steps": [{
                    "id": "login",
                    "caption": "Sign in to Electronic Services",
                    "start": "/login",
                    "show_login": True,
                }],
            }],
        }
        log = {
            "base_url": "https://staging.example.test",
            "steps": [{
                "key": "33605-login", "status": "ok", "clip": None,
                "screenshot": None, "error": None,
            }],
        }
        class GuideArgs(Args):
            no_embed = True
            video = None

        html = publish_guide.build_guide(
            script, log, GuideArgs(), Path("."),
            {"targets": {"dev": {"roles": {"tenant_admin": CREDS}}}},
        )
        self.assertIn("Sign in as", html)
        self.assertIn("tenant_admin", html)
        self.assertIn(".sprint-recap.local.json", html)
        self.assertNotIn(CREDS["password"], html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
