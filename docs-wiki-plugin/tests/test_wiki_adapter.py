"""Offline tests for scripts/wiki_adapter.py (WIKI-P2-06 detection + schema, WIKI-P1-04
report paths)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "wiki_adapter.py"


def load():
    spec = importlib.util.spec_from_file_location("wiki_adapter", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wa = load()


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.dir = Path(self._t.name)

    def mk(self, rel, text=""):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


class Detect(Tmp):
    def test_github_wiki_from_remote(self):
        wiki = self.dir / "shop.wiki"
        wiki.mkdir()
        r = wa.detect(wiki, remote="git@github.com:acme/shop.wiki.git")
        self.assertEqual((r["flavour"], r["confidence"]), ("github-wiki", "high"))

    def test_gitlab_wiki_from_remote(self):
        wiki = self.dir / "w"
        wiki.mkdir()
        r = wa.detect(wiki, remote="https://gitlab.example.com/acme/shop.wiki.git")
        self.assertEqual(r["flavour"], "gitlab-wiki")

    def test_azure_from_order_files(self):
        self.mk("wiki/.order", "Home\n")
        self.mk("wiki/Home.md", "# Home\n")
        r = wa.detect(self.dir / "wiki", remote="")
        self.assertEqual(r["flavour"], "azure-devops-wiki")

    def test_azure_from_remote(self):
        wiki = self.dir / "w"
        wiki.mkdir()
        r = wa.detect(wiki, remote="https://dev.azure.com/contoso/Web/_git/Web.wiki")
        self.assertEqual(r["flavour"], "azure-devops-wiki")

    def test_mkdocs_tree(self):
        self.mk("mkdocs.yml", "site_name: x\n")
        self.mk("docs/index.md", "# x\n")
        r = wa.detect(self.dir / "docs", remote="")
        self.assertEqual((r["flavour"], r["confidence"]), ("mkdocs-tree", "high"))

    def test_no_signal_means_ask(self):
        self.mk("notes/a.md", "# a\n")
        r = wa.detect(self.dir / "notes", remote="")
        self.assertIsNone(r["flavour"])
        self.assertEqual(r["confidence"], "none")

    def test_tie_means_ask(self):
        self.mk("w/_Sidebar.md", "- x\n")
        self.mk("w/.attachments/x.png", "")
        r = wa.detect(self.dir / "w", remote="")
        self.assertIsNone(r["flavour"], r)

    def test_missing_path(self):
        self.assertFalse(wa.detect(self.dir / "nope", remote="")["exists"])

    def test_credentials_in_remote_are_not_echoed(self):
        wiki = self.dir / "w"
        wiki.mkdir()
        r = wa.detect(wiki, remote="https://jane:s3cret@github.com/acme/shop.wiki.git")
        self.assertNotIn("s3cret", json.dumps(r))


class Validate(Tmp):
    def test_absent_file_is_ok(self):
        result, code = wa.validate(self.dir)
        self.assertEqual(code, 0)
        self.assertFalse(result["exists"])

    def test_new_location_wins_over_legacy(self):
        self.mk(".claude/docs-wiki.local.json", '{"wikiFlavour": "github-wiki"}')
        self.mk(".docs-wiki.local.json", '{"wikiFlavour": "gitlab-wiki"}')
        self.assertFalse(wa.locate(self.dir)["legacy"])

    def test_legacy_location_is_read_with_a_warning(self):
        self.mk(".docs-wiki.local.json", '{"wikiFlavour": "github-wiki"}')
        result, code = wa.validate(self.dir)
        self.assertEqual(code, 0)
        self.assertTrue(result["legacy"])
        self.assertTrue(any("legacy" in w for w in result["warnings"]))

    def test_typo_is_reported_with_a_suggestion(self):
        self.mk(".claude/docs-wiki.local.json", '{"retiredFolder": ["_old/"]}')
        result, code = wa.validate(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("retiredFolders", result["errors"][0])

    def test_bad_values(self):
        errors, _ = wa.validate_data({"wikiFlavour": "confluence", "retiredFolders": "x",
                                      "renderMode": "kroki", "exceptions": [1]})
        text = " ".join(errors)
        self.assertIn("wikiFlavour", text)
        self.assertIn("retiredFolders: expected list", text)
        self.assertIn("krokiEndpoint", text)
        self.assertIn("exceptions: every entry", text)

    def test_public_kroki_and_secrets_are_errors(self):
        errors, _ = wa.validate_data({"renderMode": "kroki",
                                      "krokiEndpoint": "https://kroki.io", "pat": "x"})
        self.assertTrue(any("public" in e for e in errors))
        self.assertTrue(any("secret" in e for e in errors))

    def test_known_strays_accepts_list_or_object(self):
        self.assertEqual(wa.validate_data({"knownStrays": ["docs/x/"]})[0], [])
        self.assertEqual(wa.validate_data({"knownStrays": {"docs/x/": "why"}})[0], [])

    def test_unparseable_file(self):
        self.mk(".claude/docs-wiki.local.json", "{not json")
        self.assertEqual(wa.validate(self.dir)[1], 1)


class ReportPath(Tmp):
    def test_default_is_outside_the_wiki_and_unique(self):
        wiki = self.dir / "repo.wiki"
        root = self.dir / "repo"
        wiki.mkdir()
        root.mkdir()
        a = wa.report_path("audit", wiki, root, now=0)
        self.assertTrue(a["path"].startswith(str(root / ".docs-wiki" / "reports")))
        Path(a["path"]).parent.mkdir(parents=True)
        Path(a["path"]).write_text("x", encoding="utf-8")
        b = wa.report_path("audit", wiki, root, now=0)
        self.assertNotEqual(a["path"], b["path"])
        self.assertTrue(Path(b["path"]).name.startswith("audit-"))

    def test_kinds_get_distinct_names(self):
        wiki, root = self.dir / "w", self.dir / "r"
        wiki.mkdir()
        root.mkdir()
        names = {Path(wa.report_path(k, wiki, root, now=0)["path"]).name for k in wa.REPORT_KINDS}
        self.assertEqual(len(names), 3)

    def test_in_repo_wiki_folder(self):
        root = self.dir
        wiki = root / "wiki"
        wiki.mkdir()
        r = wa.report_path("drift", wiki, root, now=0)
        self.assertFalse(Path(r["path"]).resolve().is_relative_to(wiki.resolve()))

    def test_root_is_the_wiki_falls_back_to_data_dir(self):
        wiki = self.dir / "repo.wiki"
        wiki.mkdir()
        data = self.dir / "data"
        r = wa.report_path("audit", wiki, wiki, data_dir=str(data), now=0)
        self.assertTrue(r["path"].startswith(str(data / "reports")))

    def test_unsubstituted_data_dir_is_ignored(self):
        wiki = self.dir / "repo.wiki"
        wiki.mkdir()
        r = wa.report_path("audit", wiki, wiki, data_dir="${CLAUDE_PLUGIN_DATA}", now=0)
        self.assertNotIn("${", r["path"])
        self.assertFalse(Path(r["path"]).resolve().is_relative_to(wiki.resolve()))

    def test_reports_dir_inside_wiki_is_skipped(self):
        wiki, root = self.dir / "w", self.dir / "r"
        wiki.mkdir()
        root.mkdir()
        self.mk("r/.claude/docs-wiki.local.json", json.dumps({"reportsDir": str(wiki / "_audit")}))
        r = wa.report_path("audit", wiki, root, now=0)
        self.assertTrue(r["path"].startswith(str(root / ".docs-wiki")))

    def test_gitignore_hint(self):
        wiki, root = self.dir / "w", self.dir / "r"
        wiki.mkdir()
        root.mkdir()
        self.assertIsNotNone(wa.report_path("audit", wiki, root, now=0)["gitignore_hint"])
        (root / ".gitignore").write_text(".docs-wiki/\n", encoding="utf-8")
        self.assertIsNone(wa.report_path("audit", wiki, root, now=0)["gitignore_hint"])


class Cli(Tmp):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                              text=True, timeout=60)

    def test_cli_round_trip(self):
        wiki = self.dir / "w"
        wiki.mkdir()
        out = self.run_cli("report-path", "sync-audit", "--wiki", str(wiki), "--root", str(self.dir / "r"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("sync-audit-", json.loads(out.stdout)["path"])
        self.assertEqual(self.run_cli("detect", str(wiki)).returncode, 0)
        self.assertEqual(self.run_cli("validate", "--root", str(self.dir)).returncode, 0)
        self.assertEqual(self.run_cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()
