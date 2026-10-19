"""Offline tests for embed_swimlane.py (idempotency, line endings, blank line, link
hygiene) and the 0.11.0 publish_update.py additions (relative .puml link, kroki only on
--approve, attachment body encoding)."""
from __future__ import annotations

import base64
import importlib.util
import io
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "wiki-plantuml" / "scripts"
EMBED = SCRIPTS / "embed_swimlane.py"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def embed(page, *extra):
    return subprocess.run([sys.executable, str(EMBED), "--page", str(page), "--flavour",
                           "github", "--artifact", "s.png", "--alt", "Order flow", *extra],
                          capture_output=True, text=True, timeout=60)


class Embed(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.page = Path(self._t.name) / "Orders.md"

    def test_second_run_is_byte_identical(self):
        self.page.write_bytes(b"# Orders\n\nIntro.\n")
        self.assertEqual(embed(self.page).returncode, 0)
        first = self.page.read_bytes()
        out = embed(self.page)
        self.assertIn("no change", out.stdout)
        self.assertEqual(self.page.read_bytes(), first)

    def test_blank_line_before_following_heading_is_kept(self):
        self.page.write_bytes(b"# Orders\n\n### Swimlane\n\nold\n\n#### Sub detail\n\ntext\n")
        self.assertEqual(embed(self.page).returncode, 0)
        text = self.page.read_text(encoding="utf-8")
        self.assertIn("[[/images/s.png|Order flow]]\n\n#### Sub detail", text)
        self.assertIn("no change", embed(self.page).stdout, "replacement must be idempotent")

    def test_crlf_page_stays_crlf(self):
        self.page.write_bytes(b"# Orders\r\n\r\n## Next\r\n\r\nMore.\r\n")
        self.assertEqual(embed(self.page).returncode, 0)
        raw = self.page.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))

    def test_absolute_local_puml_link_is_refused(self):
        self.page.write_bytes(b"# Orders\n")
        for link in ("C:/Users/jane/s.puml", "C:\\Users\\jane\\s.puml", "/home/jane/s.puml",
                     "~/s.puml", "\\\\server\\share\\s.puml"):
            with self.subTest(link=link):
                out = embed(self.page, "--puml-link", link)
                self.assertEqual(out.returncode, 2, out.stdout)
        self.assertEqual(self.page.read_bytes(), b"# Orders\n")

    def test_relative_and_url_links_are_accepted(self):
        self.page.write_bytes(b"# Orders\n")
        self.assertEqual(embed(self.page, "--puml-link", "images/s.puml", "--dry-run").returncode, 0)
        self.assertEqual(embed(self.page, "--puml-link", "https://example.com/s.puml",
                               "--dry-run").returncode, 0)

    def test_native_flavour_needs_source(self):
        self.page.write_bytes(b"# Orders\n")
        out = subprocess.run([sys.executable, str(EMBED), "--page", str(self.page), "--flavour",
                              "gitlab", "--artifact", "s.svg", "--alt", "A"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 2)


def _no_network(*_a, **_k):
    raise AssertionError("network connection attempted")


class PublishExtras(unittest.TestCase):
    def setUp(self):
        self.mod = load("publish_update")
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.dir = Path(self._t.name)
        self.clone = self.dir / "repo.wiki"
        (self.clone / "diagrams").mkdir(parents=True)
        self.page = self.clone / "Orders.md"
        self.page.write_text("# Orders\n", encoding="utf-8")
        self.puml = self.clone / "diagrams" / "swimlane-orders.puml"
        self.puml.write_text("@startuml\n|A|\nstart\n:x;\nstop\n@enduml\n", encoding="utf-8")
        self.calls = []

    def fake_run(self, cmd):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        if Path(cmd[1]).name == "render_puml.py":
            out = Path(cmd[cmd.index("--out") + 1]) if "--out" in cmd else self.puml.parent
            (out / f"{self.puml.stem}.png").write_bytes(b"png")
        return subprocess.CompletedProcess(cmd, 0)

    def argv(self, flavour="github", *extra):
        a = ["--page", str(self.page), "--flavour", flavour, "--puml", str(self.puml),
             "--alt", "Orders"]
        if flavour == "github":
            a += ["--wiki-clone", str(self.clone)]
        if flavour == "azure":
            a += ["--org", "contoso", "--project", "web", "--wiki-id", "web.wiki"]
        return a + list(extra)

    def embed_call(self):
        return next(c for c in self.calls if c[1].endswith("embed_swimlane.py"))

    def test_puml_link_is_relative_to_the_wiki(self):
        with mock.patch.object(self.mod, "run", self.fake_run):
            self.assertEqual(self.mod.main(self.argv()), 0)
        call = self.embed_call()
        self.assertEqual(call[call.index("--puml-link") + 1], "diagrams/swimlane-orders.puml")

    def test_puml_outside_the_wiki_gets_no_link(self):
        outside = self.dir / "elsewhere" / "swimlane-orders.puml"
        outside.parent.mkdir()
        outside.write_text(self.puml.read_text(encoding="utf-8"), encoding="utf-8")
        argv = self.argv()
        argv[argv.index("--puml") + 1] = str(outside)
        with mock.patch.object(self.mod, "run", self.fake_run):
            self.assertEqual(self.mod.main(argv), 0)
        self.assertNotIn("--puml-link", self.embed_call())

    def test_kroki_preview_makes_no_network_call(self):
        with mock.patch.object(self.mod, "run", self.fake_run), \
                mock.patch.object(socket.socket, "connect", _no_network), \
                mock.patch("urllib.request.urlopen", _no_network):
            self.assertEqual(self.mod.main(self.argv("github", "--render", "kroki",
                                                     "--kroki-endpoint",
                                                     "https://kroki.internal.example.com")), 0)
        self.assertNotIn("render_puml.py", [Path(c[1]).name for c in self.calls])

    def test_kroki_approve_posts_to_the_self_hosted_endpoint(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        seen = {}

        def fake_urlopen(req, timeout=0):
            seen["url"], seen["method"], seen["data"] = req.full_url, req.get_method(), req.data
            return Resp(b"\x89PNG-from-kroki")

        with mock.patch.object(self.mod, "run", self.fake_run), \
                mock.patch.object(self.mod.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(self.mod.main(self.argv(
                "github", "--render", "kroki", "--kroki-endpoint",
                "https://kroki.internal.example.com/", "--approve")), 0)
        self.assertEqual(seen["url"], "https://kroki.internal.example.com/plantuml/png")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual((self.clone / "images" / "swimlane-orders.png").read_bytes(),
                         b"\x89PNG-from-kroki")

    def test_public_kroki_is_refused_before_anything_runs(self):
        with mock.patch.object(self.mod, "run", self.fake_run), self.assertRaises(SystemExit):
            self.mod.main(self.argv("github", "--render", "kroki", "--kroki-endpoint",
                                    "https://kroki.io", "--approve"))
        self.assertEqual(self.calls, [])

    def test_body_encoding_is_passed_to_the_upload(self):
        with mock.patch.object(self.mod, "run", self.fake_run):
            self.assertEqual(self.mod.main(self.argv("azure", "--body-encoding", "raw",
                                                     "--approve")), 0)
        upload = next(c for c in self.calls if c[1].endswith("upload_attachment.py"))
        self.assertEqual(upload[upload.index("--body-encoding") + 1], "raw")


class UploadEncoding(unittest.TestCase):
    def test_raw_and_base64_bodies(self):
        up = load("upload_attachment")
        raw = up.build_request("contoso", "web", "w", "a.png", b"\x89PNG", "tok",
                               body_encoding="raw")
        b64 = up.build_request("contoso", "web", "w", "a.png", b"\x89PNG", "tok")
        self.assertEqual(raw.data, b"\x89PNG")
        self.assertEqual(b64.data, base64.b64encode(b"\x89PNG"))

    def test_cli_flag(self):
        up = load("upload_attachment")
        args = up.build_parser().parse_args(["--org", "o", "--project", "p", "--wiki-id", "w",
                                             "--file", "f", "--name", "n",
                                             "--body-encoding", "raw"])
        self.assertEqual(args.body_encoding, "raw")
        self.assertEqual(up.build_parser().parse_args(
            ["--org", "o", "--project", "p", "--wiki-id", "w", "--file", "f", "--name", "n"]
        ).body_encoding, "base64")


if __name__ == "__main__":
    unittest.main()
