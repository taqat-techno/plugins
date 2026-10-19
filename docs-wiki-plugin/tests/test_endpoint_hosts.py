#!/usr/bin/env python3
"""Offline tests for the 0.11.1 host checks (re-audit RA-WIKI-01 / RA-WIKI-02).

  * the public-Kroki refusal compares the parsed hostname case-insensitively, ignores a
    trailing dot, port and userinfo, covers subdomains, fails closed on an unreadable
    host, and no longer refuses a self-hosted name that merely CONTAINS a public one;
  * the Azure upload refuses a non-https --org (the PAT would travel in clear text)
    and warns on a host that is not Azure DevOps Services. Both checks run before any
    side effect.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "wiki-plantuml" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


publish = load("publish_update")
upload = load("upload_attachment")


class KrokiPublicHost(unittest.TestCase):
    def test_public_hosts_refused_in_any_case_or_spelling(self):
        for ep in ("https://kroki.io", "https://KROKI.IO", "https://Kroki.Io./",
                   "https://kroki.io:443/", "https://user@kroki.io", "kroki.io",
                   "//KROKI.io/x", "https://demo.kroki.io", "https://WWW.PlantUML.com/plantuml",
                   "https://plantuml.com.", "HTTPS://PLANTUML.COM"):
            with self.subTest(ep=ep):
                self.assertTrue(publish.is_public_kroki(ep))

    def test_unreadable_host_fails_closed(self):
        for ep in ("https://", "http://[bad", ""):
            with self.subTest(ep=ep):
                self.assertTrue(publish.is_public_kroki(ep))

    def test_self_hosted_endpoints_allowed(self):
        for ep in ("https://kroki.internal.example.com", "http://my-plantuml.company.internal",
                   "http://localhost:8000", "https://kroki.io.example.net",
                   "https://notkroki.io", "http://10.0.0.5:8000"):
            with self.subTest(ep=ep):
                self.assertFalse(publish.is_public_kroki(ep))

    def _argv(self, d, endpoint):
        page, puml = Path(d) / "P.md", Path(d) / "s.puml"
        page.write_text("# P\n", encoding="utf-8")
        puml.write_text("@startuml\n@enduml\n", encoding="utf-8")
        return ["--page", str(page), "--flavour", "github", "--puml", str(puml),
                "--alt", "A", "--wiki-clone", d, "--render", "kroki",
                "--kroki-endpoint", endpoint]

    def test_validate_refuses_uppercase_public_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            args = publish.build_parser().parse_args(self._argv(d, "https://KROKI.IO"))
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err, \
                    self.assertRaises(SystemExit):
                publish.validate(args)
            self.assertIn("REFUSED", err.getvalue())

    def test_validate_accepts_self_hosted_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            args = publish.build_parser().parse_args(
                self._argv(d, "http://my-plantuml.company.internal"))
            publish.validate(args)  # no SystemExit


class AzureOrgHost(unittest.TestCase):
    def test_https_azure_hosts_pass_silently(self):
        for org in ("contoso", "https://dev.azure.com/contoso", "https://DEV.AZURE.COM/c",
                    "https://contoso.visualstudio.com"):
            with self.subTest(org=org):
                url, warning = upload.check_org(org)
                self.assertTrue(url.startswith("https://"))
                self.assertIsNone(warning)

    def test_non_https_is_refused(self):
        for org in ("http://dev.azure.com/contoso", "ftp://dev.azure.com/c", "https://"):
            with self.subTest(org=org):
                with self.assertRaises(ValueError):
                    upload.check_org(org)

    def test_non_azure_host_warns(self):
        _, warning = upload.check_org("https://tfs.corp.example.com/DefaultCollection")
        self.assertIn("tfs.corp.example.com", warning)
        _, warning = upload.check_org("https://dev.azure.com.evil.example/x")
        self.assertIsNotNone(warning)

    def test_main_refuses_http_before_reading_pat_or_network(self):
        with tempfile.TemporaryDirectory() as d:
            png = Path(d) / "a.png"
            png.write_bytes(b"\x89PNG")
            argv = ["--org", "http://dev.azure.com/contoso", "--project", "p",
                    "--wiki-id", "w", "--file", str(png), "--name", "a.png"]
            with mock.patch.dict(os.environ, {"AZDO_PAT": "pat-value"}), \
                    mock.patch.object(upload.urllib.request, "urlopen") as op, \
                    mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(upload.main(argv), 1)
            op.assert_not_called()
            self.assertIn("https", err.getvalue())
            self.assertNotIn("pat-value", err.getvalue())

    def test_publish_validate_refuses_http_org(self):
        with tempfile.TemporaryDirectory() as d:
            page, puml = Path(d) / "P.md", Path(d) / "s.puml"
            page.write_text("# P\n", encoding="utf-8")
            puml.write_text("@startuml\n@enduml\n", encoding="utf-8")
            args = publish.build_parser().parse_args(
                ["--page", str(page), "--flavour", "azure", "--puml", str(puml), "--alt", "A",
                 "--org", "http://tfs.local/c", "--project", "p", "--wiki-id", "w"])
            with mock.patch("sys.stderr", new_callable=io.StringIO), \
                    self.assertRaises(SystemExit):
                publish.validate(args)


if __name__ == "__main__":
    unittest.main()
