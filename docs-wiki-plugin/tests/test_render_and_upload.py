#!/usr/bin/env python3
"""Offline tests for the Python render + Azure upload helpers (WIKI-P1-05).

No Java, no PlantUML and no network are needed: renderer discovery takes an injected
environ + `which`, subprocess.run is mocked, and urllib.request.urlopen is mocked.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import base64
import importlib.util
import io
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "wiki-plantuml" / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render = load("render_puml")
upload = load("upload_attachment")


def which_of(mapping: dict[str, str]):
    return lambda name: mapping.get(name)


class RendererDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        self.flag_jar = d / "plantuml-1.2026.1-flag.jar"
        self.env_jar = d / "plantuml-1.2026.1-env.jar"
        for j in (self.flag_jar, self.env_jar):
            j.write_bytes(b"PK")
        self.which = which_of({"java": "/usr/bin/java", "plantuml": "/usr/bin/plantuml"})

    def test_flag_jar_wins_over_env_and_path(self):
        cmd = render.resolve_renderer(str(self.flag_jar), environ={"PLANTUML_JAR": str(self.env_jar)},
                                      which=self.which)
        self.assertEqual(cmd, ["/usr/bin/java", "-jar", str(self.flag_jar)])

    def test_env_jar_wins_over_path_cli(self):
        cmd = render.resolve_renderer(None, environ={"PLANTUML_JAR": str(self.env_jar)},
                                      which=self.which)
        self.assertEqual(cmd, ["/usr/bin/java", "-jar", str(self.env_jar)])

    def test_legacy_env_alias_is_accepted(self):
        cmd = render.resolve_renderer(None, environ={"DOCS_WIKI_PLANTUML_JAR": str(self.env_jar)},
                                      which=self.which)
        self.assertEqual(cmd[-1], str(self.env_jar))

    def test_plantuml_on_path_is_the_last_resort(self):
        cmd = render.resolve_renderer(None, environ={}, which=self.which)
        self.assertEqual(cmd, ["/usr/bin/plantuml"])

    def test_nothing_found_raises_actionable_error(self):
        with self.assertRaises(render.RendererNotFound) as ctx:
            render.resolve_renderer(None, environ={}, which=which_of({}))
        msg = str(ctx.exception)
        for needle in ("Java 8+", "PLANTUML_JAR", "--plantuml-jar", "brew install plantuml",
                       "apt install", "choco install", "Kroki"):
            self.assertIn(needle, msg)

    def test_jar_without_java_raises(self):
        with self.assertRaises(render.RendererNotFound) as ctx:
            render.resolve_renderer(str(self.flag_jar), environ={},
                                    which=which_of({"plantuml": "/usr/bin/plantuml"}))
        self.assertIn("Java not found", str(ctx.exception))

    def test_missing_jar_file_raises(self):
        with self.assertRaises(render.RendererNotFound) as ctx:
            render.resolve_renderer(str(Path(self.tmp.name) / "nope.jar"), environ={},
                                    which=self.which)
        self.assertIn("plantuml.jar not found", str(ctx.exception))

    def test_8059_trap_is_refused(self):
        trap = Path(self.tmp.name) / "plantuml-8059.jar"
        trap.write_bytes(b"PK")
        with self.assertRaises(render.RendererNotFound):
            render.resolve_renderer(str(trap), environ={}, which=self.which)

    def test_java_home_is_used_before_path(self):
        home = Path(self.tmp.name) / "jdk"
        (home / "bin").mkdir(parents=True)
        java = home / "bin" / ("java.exe" if os.name == "nt" else "java")
        java.write_bytes(b"")
        cmd = render.resolve_renderer(str(self.flag_jar), environ={"JAVA_HOME": str(home)},
                                      which=self.which)
        self.assertEqual(cmd[0], str(java))


class RenderMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def puml(self, text: str) -> Path:
        p = self.dir / "swimlane-x-y.puml"
        p.write_text(text, encoding="utf-8")
        return p

    def test_missing_dependency_exits_2_without_running_anything(self):
        p = self.puml("@startuml\nstart\n:A;\nstop\n@enduml\n")
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(render.shutil, "which", return_value=None), \
                mock.patch.object(render.subprocess, "run") as run:
            self.assertEqual(render.main(["--puml", str(p)]), 2)
        run.assert_not_called()

    def test_lint_rejects_prefix_colour_and_unbalanced_if(self):
        self.assertTrue(render.lint("#PaleGreen:Step;\n"))
        self.assertTrue(render.lint("if (x?) then (yes)\n:A;\n"))
        self.assertEqual(render.lint("if (x?) then (y)\n:A; <<#d6f5d6>>\nendif\n"), [])

    def test_render_invokes_plantuml_with_limit_size_and_out_dir(self):
        p = self.puml("@startuml\nstart\n:A;\nstop\n@enduml\n")
        out = self.dir / "out"

        def fake_run(cmd, env, check):
            (out / "swimlane-x-y.png").write_bytes(b"png")
            return mock.Mock(returncode=0)

        with mock.patch.object(render, "resolve_renderer", return_value=["plantuml"]), \
                mock.patch.object(render.subprocess, "run", side_effect=fake_run) as run:
            self.assertEqual(render.main(["--puml", str(p), "--format", "png",
                                          "--out", str(out)]), 0)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd, ["plantuml", "-tpng", "-o", str(out.resolve()), str(p.resolve())])
        self.assertEqual(run.call_args.kwargs["env"]["PLANTUML_LIMIT_SIZE"], "8192")


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))


class Upload(unittest.TestCase):
    PAT = "secret-pat-value"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.png = Path(self.tmp.name) / "swimlane-orders-fulfilment.png"
        self.png.write_bytes(b"\x89PNG-bytes")

    def argv(self):
        return ["--org", "https://dev.azure.com/contoso", "--project", "My Web",
                "--wiki-id", "Web.wiki", "--file", str(self.png),
                "--name", "swimlane orders.png"]

    def test_builds_the_correct_put_request(self):
        req = upload.build_request("https://dev.azure.com/contoso/", "My Web", "Web.wiki",
                                   "swimlane orders.png", b"\x89PNG", self.PAT)
        self.assertEqual(req.get_method(), "PUT")
        self.assertEqual(req.full_url,
                         "https://dev.azure.com/contoso/My%20Web/_apis/wiki/wikis/Web.wiki/"
                         "attachments?name=swimlane%20orders.png&api-version=7.1")
        self.assertEqual(req.data, base64.b64encode(b"\x89PNG"))
        self.assertEqual(req.get_header("Content-type"), "application/octet-stream")
        expected = base64.b64encode(f":{self.PAT}".encode()).decode()
        self.assertEqual(req.get_header("Authorization"), f"Basic {expected}")

    def test_bare_org_name_expands_to_dev_azure_com(self):
        req = upload.build_request("contoso", "web", "web.wiki", "a.png", b"", self.PAT)
        self.assertTrue(req.full_url.startswith("https://dev.azure.com/contoso/web/_apis/"))

    def test_main_puts_once_and_never_echoes_the_pat(self):
        with mock.patch.dict(os.environ, {"AZDO_PAT": self.PAT}), \
                mock.patch.object(upload.urllib.request, "urlopen",
                                  return_value=FakeResp(b"{}")) as op, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out, \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(upload.main(self.argv()), 0)
        self.assertEqual(op.call_count, 1)
        req = op.call_args.args[0]
        self.assertEqual(req.data, base64.b64encode(b"\x89PNG-bytes"))
        self.assertIn("/.attachments/swimlane orders.png", out.getvalue())
        self.assertNotIn(self.PAT, out.getvalue() + err.getvalue())

    def test_missing_pat_fails_before_any_request(self):
        env = {k: v for k, v in os.environ.items() if k != "AZDO_PAT"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(upload.urllib.request, "urlopen") as op:
            self.assertEqual(upload.main(self.argv()), 1)
        op.assert_not_called()

    def test_http_500_then_successful_reput_is_success(self):
        with mock.patch.dict(os.environ, {"AZDO_PAT": self.PAT}), \
                mock.patch.object(upload.urllib.request, "urlopen",
                                  side_effect=[http_error(500), FakeResp(b"{}")]) as op:
            self.assertEqual(upload.main(self.argv()), 0)
        self.assertEqual(op.call_count, 2)

    def test_http_500_twice_is_a_real_failure(self):
        with mock.patch.dict(os.environ, {"AZDO_PAT": self.PAT}), \
                mock.patch.object(upload.urllib.request, "urlopen",
                                  side_effect=[http_error(500), http_error(500)]):
            self.assertEqual(upload.main(self.argv()), 1)

    def test_other_http_error_fails_without_retry(self):
        with mock.patch.dict(os.environ, {"AZDO_PAT": self.PAT}), \
                mock.patch.object(upload.urllib.request, "urlopen",
                                  side_effect=[http_error(401)]) as op:
            self.assertEqual(upload.main(self.argv()), 1)
        self.assertEqual(op.call_count, 1)

    def test_wiki_not_found_is_reported_as_unprovisioned(self):
        with mock.patch.dict(os.environ, {"AZDO_PAT": self.PAT}), \
                mock.patch.object(upload.urllib.request, "urlopen",
                                  side_effect=[http_error(404, b"TF401174: Wiki not found")]), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(upload.main(self.argv()), 1)
        self.assertIn("not provisioned", err.getvalue())


if __name__ == "__main__":
    unittest.main()
