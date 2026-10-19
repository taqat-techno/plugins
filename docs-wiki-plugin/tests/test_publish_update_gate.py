#!/usr/bin/env python3
"""Offline tests for the --approve gate in skills/wiki-plantuml/scripts/publish_update.py.

Contract (WIKI-P0-01):
  * without --approve: zero network calls (no upload_attachment.py), no image staged
    into the wiki clone, the page is NOT written; the diff comes from
    embed_swimlane.py --dry-run and the only render goes to a temp dir;
  * with --approve: render, upload (azure) / stage (github) and the page write happen.

Every external command goes through publish_update.run(), which is replaced by a
recorder. The render/upload helper calls are simulated; the embed_swimlane.py call is
executed for real so the page bytes can be compared. socket connect and urlopen are
patched to fail the test. Every helper must be run via sys.executable (no pwsh).

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "wiki-plantuml" / "scripts"
PAGE_TEXT = "# Orders\n\nIntro.\n\n## Next\n\nMore.\n"
PUML_TEXT = "@startuml\n|Customer|\nstart\n:Order;\nstop\n@enduml\n"
FAKED = {"render_puml.py", "upload_attachment.py"}


def load_module():
    spec = importlib.util.spec_from_file_location("publish_update", SCRIPTS / "publish_update.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Recorder:
    """Stand-in for publish_update.run: records commands, fakes render/upload, runs embed."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, cmd):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        assert cmd[0] == sys.executable, f"helper not run via sys.executable: {cmd[0]}"
        script = Path(cmd[1]).name
        if script == "render_puml.py":
            puml = Path(cmd[cmd.index("--puml") + 1])
            fmt = cmd[cmd.index("--format") + 1]
            out = Path(cmd[cmd.index("--out") + 1]) if "--out" in cmd else puml.parent
            (out / f"{puml.stem}.{fmt}").write_bytes(b"\x89PNG fake")
        if script in FAKED:
            return subprocess.CompletedProcess(cmd, 0)
        return subprocess.run(cmd, check=False, capture_output=True, text=True)

    def scripts(self) -> list[str]:
        return [Path(c[1]).name for c in self.calls]

    def helper_calls(self) -> list[list[str]]:
        return [c for c in self.calls if Path(c[1]).name in FAKED]

    def embed_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c[1].endswith("embed_swimlane.py")]


def _no_network(*_a, **_k):
    raise AssertionError("network connection attempted")


class PublishGate(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.page = self.dir / "Orders.md"
        self.page.write_bytes(PAGE_TEXT.encode("utf-8"))
        self.puml = self.dir / "swimlane-orders-fulfilment.puml"
        self.puml.write_text(PUML_TEXT, encoding="utf-8")
        self.clone = self.dir / "repo.wiki"
        self.rec = Recorder()
        self.copy_spy = mock.MagicMock(side_effect=self.mod.shutil.copy2)
        patches = [
            mock.patch.object(self.mod, "run", self.rec),
            mock.patch.object(self.mod.shutil, "copy2", self.copy_spy),
            mock.patch.object(socket.socket, "connect", _no_network),
            mock.patch.object(socket, "create_connection", _no_network),
            mock.patch("urllib.request.urlopen", _no_network),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def base(self, flavour: str) -> list[str]:
        argv = ["--page", str(self.page), "--flavour", flavour, "--puml", str(self.puml),
                "--alt", "Order fulfilment swimlane"]
        if flavour == "azure":
            argv += ["--org", "contoso", "--project", "web", "--wiki-id", "web.wiki"]
        if flavour == "github":
            argv += ["--wiki-clone", str(self.clone)]
        return argv

    def page_bytes(self) -> bytes:
        return self.page.read_bytes()

    def outside_files(self) -> set[str]:
        return {str(p.relative_to(self.dir)) for p in self.dir.rglob("*")}

    # ---- preview (no --approve) ----------------------------------------------------
    def test_azure_preview_makes_no_upload_and_no_page_write(self):
        before = self.outside_files()
        self.assertEqual(self.mod.main(self.base("azure")), 0)
        self.assertNotIn("upload_attachment.py", self.rec.scripts())
        self.assertEqual(self.page_bytes(), PAGE_TEXT.encode("utf-8"))
        self.assertEqual(self.outside_files(), before, "preview wrote outside temp")
        render = self.rec.helper_calls()
        self.assertEqual([Path(c[1]).name for c in render], ["render_puml.py"])
        self.assertIn("--out", render[0])
        self.assertFalse(Path(render[0][render[0].index("--out") + 1]).exists(),
                         "preview render dir should be a deleted temp dir")
        embeds = self.rec.embed_calls()
        self.assertEqual(len(embeds), 1)
        self.assertIn("--dry-run", embeds[0])

    def test_github_preview_stages_nothing(self):
        self.assertEqual(self.mod.main(self.base("github")), 0)
        self.copy_spy.assert_not_called()
        self.assertFalse(self.clone.exists(), "preview created the wiki clone images dir")
        self.assertEqual(self.page_bytes(), PAGE_TEXT.encode("utf-8"))

    def test_gitlab_preview_runs_no_render_or_upload_and_no_write(self):
        self.assertEqual(self.mod.main(self.base("gitlab")), 0)
        self.assertEqual(self.rec.helper_calls(), [])
        self.assertEqual(self.page_bytes(), PAGE_TEXT.encode("utf-8"))

    def test_invalid_args_fail_before_any_command(self):
        argv = self.base("azure")
        argv = argv[: argv.index("--org")]  # drop --org/--project/--wiki-id
        with self.assertRaises(SystemExit):
            self.mod.main(argv + ["--approve"])
        self.assertEqual(self.rec.calls, [])

    def test_plantuml_jar_flag_is_forwarded_to_the_renderer(self):
        self.assertEqual(self.mod.main(self.base("azure") + ["--plantuml-jar", "/x/p.jar"]), 0)
        render = self.rec.helper_calls()[0]
        self.assertEqual(render[render.index("--plantuml-jar") + 1], "/x/p.jar")

    # ---- approved ------------------------------------------------------------------
    def test_azure_approve_uploads_then_writes_page(self):
        self.assertEqual(self.mod.main(self.base("azure") + ["--approve"]), 0)
        scripts = self.rec.scripts()
        self.assertEqual(scripts, ["render_puml.py", "upload_attachment.py", "embed_swimlane.py"])
        upload = self.rec.calls[1]
        self.assertEqual(Path(upload[upload.index("--file") + 1]),
                         self.puml.with_suffix(".png"))
        self.assertEqual(upload[upload.index("--name") + 1], "swimlane-orders-fulfilment.png")
        self.assertNotIn("--dry-run", self.rec.embed_calls()[0])
        self.assertIn("![Order fulfilment swimlane](/.attachments/swimlane-orders-fulfilment.png)",
                      self.page.read_text(encoding="utf-8"))

    def test_github_approve_stages_image_and_writes_page(self):
        self.assertEqual(self.mod.main(self.base("github") + ["--approve"]), 0)
        self.copy_spy.assert_called_once()
        self.assertTrue((self.clone / "images" / "swimlane-orders-fulfilment.png").is_file())
        self.assertIn("[[/images/swimlane-orders-fulfilment.png|Order fulfilment swimlane]]",
                      self.page.read_text(encoding="utf-8"))


class EmbedDryRun(unittest.TestCase):
    def test_dry_run_prints_diff_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            page = Path(d) / "P.md"
            page.write_bytes(PAGE_TEXT.encode("utf-8"))
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "embed_swimlane.py"), "--page", str(page),
                 "--flavour", "github", "--artifact", "x.png", "--alt", "X", "--dry-run"],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("+### Swimlane", proc.stdout)
            self.assertIn("NOT written", proc.stdout)
            self.assertEqual(page.read_bytes(), PAGE_TEXT.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
