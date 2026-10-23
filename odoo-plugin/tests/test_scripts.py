"""Offline coverage for every CLI script under scripts/.

Each script must at least start (`--help`) under `python -I`, which drops the script's
own directory from sys.path, so the documented invocation works however it is run.
The upgrade, i18n, security, test-tooling, frontend and official-skills scripts are
then exercised on small fixture modules in a temp directory. Nothing touches the
network, a database or a running Odoo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN_ROOT / "scripts"

CLI_SCRIPTS = [
    "frontend/bootstrap_mapper.py", "frontend/version_detector.py",
    "i18n/i18n_converter.py", "i18n/i18n_extractor.py", "i18n/i18n_reporter.py",
    "i18n/i18n_validator.py",
    "official_skills.py",
    "owl/owl_lint.py", "owl/owl_scaffold.py",
    "security/access_checker.py", "security/route_auditor.py", "security/security_auditor.py",
    "security/sql_scanner.py", "security/sudo_finder.py",
    "service/db_manager.py", "service/docker_manager.py", "service/env_initializer.py",
    "service/ide_configurator.py", "service/server_manager.py",
    "test/coverage_reporter.py", "test/mock_data_factory.py", "test/test_generator.py",
    "test/test_runner.py",
    "upgrade/cli.py",
]


def _env(**extra):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("ODOO_UPGRADE_BACKUP_DIR", None)
    env.update(extra)
    return env


def run(script, *args, cwd=None, **env):
    proc = subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, env=_env(**env), timeout=120,
                          cwd=str(cwd or PLUGIN_ROOT))
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def test_every_cli_script_is_listed():
    found = set()
    for py in SCRIPTS.rglob("*.py"):
        rel = py.relative_to(SCRIPTS).as_posix()
        if py.name.startswith("_") or "transforms/" in rel or rel in (
                "service/shared.py", "upgrade/utils.py", "upgrade/precheck.py",
                "upgrade/upgrade.py", "upgrade/validate.py"):
            continue  # library modules, exercised through their CLI
        found.add(rel)
    assert found == set(CLI_SCRIPTS), found ^ set(CLI_SCRIPTS)


@pytest.mark.parametrize("script", [s for s in CLI_SCRIPTS if not s.startswith("frontend/")])
def test_cli_help_runs_isolated(script):
    code, out, err = run(script, "--help")
    assert code == 0, err
    assert "usage" in out.lower(), out


def test_self_tests_pass():
    for script in ("official_skills.py",):
        code, out, err = run(script, "--self-test")
        assert code == 0 and "FAIL" not in out, (script, out, err)


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def module(tmp_path):
    """A small Odoo 17 module inside an addons directory."""
    mod = tmp_path / "addons" / "my_mod"
    (mod / "views").mkdir(parents=True)
    (mod / "models").mkdir()
    (mod / "controllers").mkdir()
    (mod / "security").mkdir()
    (mod / "__manifest__.py").write_text(
        "{'name': 'My Module', 'version': '17.0.1.0.0', 'depends': ['base'],\n"
        " 'data': ['security/ir.model.access.csv', 'views/v.xml']}\n", encoding="utf-8")
    (mod / "__init__.py").write_text("from . import models, controllers\n", encoding="utf-8")
    (mod / "models" / "__init__.py").write_text("from . import thing\n", encoding="utf-8")
    (mod / "models" / "thing.py").write_text(
        "from odoo import _, fields, models\n\n\n"
        "class Thing(models.Model):\n"
        "    _name = 'my.thing'\n"
        "    _description = 'Thing'\n\n"
        "    name = fields.Char(string='Name')\n"
        "    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State')\n\n"
        "    def action_done(self):\n"
        "        self.env.cr.execute(\"SELECT id FROM my_thing WHERE name = '%s'\" % self.name)\n"
        "        return self.sudo().write({'state': 'done'})\n\n"
        "    def _msg(self):\n"
        "        return _('Thing is done')\n", encoding="utf-8")
    (mod / "controllers" / "__init__.py").write_text("from . import main\n", encoding="utf-8")
    (mod / "controllers" / "main.py").write_text(
        "from odoo import http\n\n\n"
        "class Main(http.Controller):\n"
        "    @http.route('/my/things', auth='public', csrf=False)\n"
        "    def things(self, **kw):\n"
        "        return 'ok'\n", encoding="utf-8")
    (mod / "security" / "ir.model.access.csv").write_text(
        "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
        "access_my_thing,my.thing,model_my_thing,,1,1,1,1\n", encoding="utf-8")
    (mod / "views" / "v.xml").write_text(
        '<odoo><record id="v" model="ir.ui.view"><field name="model">my.thing</field>'
        '<field name="arch" type="xml"><tree string="Things"><field name="name"/></tree>'
        "</field></record></odoo>\n", encoding="utf-8")
    return mod


# ------------------------------------------------------------------ upgrade


def test_upgrade_precheck_reports_tree(module):
    code, out, err = run("upgrade/cli.py", "precheck", module, "--target", 19)
    assert code == 1, err  # one critical issue
    assert "<tree> tag must be <list>" in out


def test_upgrade_validate_passes(module):
    code, out, err = run("upgrade/cli.py", "validate", module)
    assert code == 0, out + err


def test_upgrade_backup_is_a_zip_outside_the_addons_path(module):
    code, out, err = run("upgrade/cli.py", "upgrade", module, "--target", 19)
    assert code == 0, out + err
    addons = module.parent
    # No second, installable copy of the module next to it.
    siblings = [p for p in addons.iterdir() if p.is_dir() and (p / "__manifest__.py").exists()]
    assert siblings == [module], siblings
    backups = list((addons / ".odoo-upgrade-backups").glob("my_mod_backup_*.zip"))
    assert len(backups) == 1
    assert (addons / ".odoo-upgrade-backups" / ".gitignore").read_text(encoding="utf-8").strip() == "*"
    with zipfile.ZipFile(backups[0]) as zf:
        names = zf.namelist()
        assert "my_mod/__manifest__.py" in names
        assert b"<tree" in zf.read("my_mod/views/v.xml")  # the original
    assert "<list" in (module / "views" / "v.xml").read_text(encoding="utf-8")
    assert "19.0" in (module / "__manifest__.py").read_text(encoding="utf-8")


def test_upgrade_backup_dir_override(module, tmp_path):
    target = tmp_path / "elsewhere"
    code, out, err = run("upgrade/cli.py", "upgrade", module, "--target", 19,
                         ODOO_UPGRADE_BACKUP_DIR=str(target))
    assert code == 0, out + err
    assert list(target.glob("my_mod_backup_*.zip"))
    assert not (module.parent / ".odoo-upgrade-backups").exists()


def test_manifest_only(module):
    code, out, err = run("upgrade/cli.py", "manifest", module, "--target", 18)
    assert code == 0, err
    assert "18.0" in (module / "__manifest__.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ security


@pytest.mark.parametrize("script,needle", [
    ("security/sql_scanner.py", "execute"),
    ("security/sudo_finder.py", "sudo"),
])
def test_security_scanners_find_issues(module, script, needle):
    code, out, err = run(script, module, "--json")
    assert "Traceback" not in err, err
    assert needle in out, out


def test_route_auditor_reports_json(module):
    code, out, err = run("security/route_auditor.py", module, "--json")
    assert "Traceback" not in err, err
    assert json.loads(out)["auditor"] == "route_auditor"


def test_security_auditor_runs(module):
    code, out, err = run("security/security_auditor.py", module, "--json")
    assert "Traceback" not in err, err
    json.loads(out[out.index("{"):])


def test_access_checker_runs(module):
    code, out, err = run("security/access_checker.py", module)
    assert "Traceback" not in err, err


# ------------------------------------------------------------------ i18n


def test_i18n_extract_report_validate_stats(module):
    code, out, err = run("i18n/i18n_extractor.py", "--module", module, "--lang", "ar")
    assert code == 0, out + err
    po = module / "i18n" / "ar.po"
    assert po.is_file()
    assert "Thing is done" in po.read_text(encoding="utf-8")
    code, out, err = run("i18n/i18n_reporter.py", "--module", module, "--lang", "ar", "--format", "json")
    assert "Traceback" not in err, err
    code, out, err = run("i18n/i18n_validator.py", "--po-file", po, "--lang", "ar")
    assert "Traceback" not in err, err
    code, out, err = run("i18n/i18n_converter.py", "--action", "stats", "--po", po)
    assert code == 0 and "Traceback" not in err, err


# ------------------------------------------------------------------ test tooling


def test_test_generator_dry_run(module):
    code, out, err = run("test/test_generator.py", "--model", "my.thing", "--module", module, "--dry-run")
    assert code == 0, err
    assert "class Test" in out


def test_mock_data_factory(module):
    code, out, err = run("test/mock_data_factory.py", "--model", "res.partner", "--count", 2)
    assert code == 0, err
    assert "res.partner" in out


def test_coverage_reporter(module):
    code, out, err = run("test/coverage_reporter.py", "--module", module, "--format", "json")
    assert "Traceback" not in err, err


# ------------------------------------------------------------------ frontend


def test_frontend_helpers():
    sys.path.insert(0, str(SCRIPTS / "frontend"))
    import bootstrap_mapper
    import version_detector

    assert bootstrap_mapper is not None and version_detector is not None
    code, out, err = run("frontend/bootstrap_mapper.py", "ml-3 text-left")
    assert code == 0, err
    assert "ms-3" in out and "text-start" in out


def test_version_detector_reads_manifest(module):
    code, out, err = run("frontend/version_detector.py", module)
    assert code == 0, err
    assert "17" in out


# ------------------------------------------------------------------ official skills (offline)


class FakeGitHub:
    """Stands in for official_skills._get: two upstream commits of one skill."""

    def __init__(self):
        self.head = "b" * 40
        self.files = {"a" * 40: b"old rules", "b" * 40: b"new rules"}

    def __call__(self, url):
        if "/commits?sha=" in url:
            return json.dumps([{"sha": self.head, "commit": {"committer": {"date": "2026-10-01"}}}]).encode()
        if "/commits/" in url:
            sha = url.rsplit("/", 1)[-1]
            return json.dumps({"sha": sha, "commit": {"committer": {"date": "2026-09-01"}}}).encode()
        if "/git/trees/" in url:
            return json.dumps({"tree": [{"path": "odoo-review/SKILL.md", "type": "blob"}]}).encode()
        if "/compare/" in url:
            return json.dumps({"files": [{"filename": "skills/odoo-review/SKILL.md",
                                          "status": "modified", "changes": 3}]}).encode()
        if url.startswith("https://raw.githubusercontent.com/"):
            sha = url.split("/odoo/odoo/", 1)[1].split("/", 1)[0]
            return self.files[sha]
        raise AssertionError(url)


@pytest.fixture
def official(monkeypatch, tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    import official_skills

    fake = FakeGitHub()
    monkeypatch.setattr(official_skills, "_get", fake)
    project = tmp_path / "proj"
    (project / "m").mkdir(parents=True)
    (project / "m" / "__manifest__.py").write_text("{'name': 'm', 'version': '20.0.1.0.0'}", encoding="utf-8")
    return official_skills, fake, project


def _skill(project):
    return project / ".claude" / "skills" / "odoo-review"


def test_official_pinned_install_then_reviewed_update(official, capsys):
    mod, fake, project = official
    assert mod.main(["install", "--project", str(project), "--commit", "a" * 40]) == 0
    assert (_skill(project) / "SKILL.md").read_bytes() == b"old rules"
    marker = json.loads((_skill(project) / ".odoo-official.json").read_text(encoding="utf-8"))
    assert marker["commit"] == "a" * 40 and marker["pinned"] is True
    capsys.readouterr()

    # An update shows the changes and replaces nothing without --yes.
    assert mod.main(["update", "--project", str(project)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["result"] == "update available, not applied"
    assert report["changed_files"][0]["file"] == "skills/odoo-review/SKILL.md"
    assert "compare" in report["compare_url"]
    assert (_skill(project) / "SKILL.md").read_bytes() == b"old rules"

    assert mod.main(["update", "--project", str(project), "--yes"]) == 0
    assert (_skill(project) / "SKILL.md").read_bytes() == b"new rules"


def test_official_rejects_a_non_sha_commit(official):
    mod, fake, project = official
    with pytest.raises(SystemExit, match="hex commit SHA"):
        mod.main(["install", "--project", str(project), "--commit", "main; rm -rf /"])


def test_official_never_overwrites_a_user_skill(official):
    mod, fake, project = official
    _skill(project).mkdir(parents=True)
    (_skill(project) / "SKILL.md").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        mod.main(["install", "--project", str(project)])
    assert (_skill(project) / "SKILL.md").read_text(encoding="utf-8") == "mine"


def test_official_refuses_on_odoo_17(official, tmp_path, capsys):
    mod, fake, _ = official
    project = tmp_path / "p17"
    (project / "m").mkdir(parents=True)
    (project / "m" / "__manifest__.py").write_text("{'name': 'm', 'version': '17.0.1.0.0'}", encoding="utf-8")
    assert mod.main(["--project", str(project)]) == 0
    assert json.loads(capsys.readouterr().out)["applicable"] is False
    assert not (project / ".claude").exists()
