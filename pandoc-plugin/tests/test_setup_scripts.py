"""Offline tests for the pandoc installers. Nothing is installed: the scripts run
with a PATH that contains only recording fakes for sudo / apt-get / brew / winget,
so any install attempt is captured instead of executed.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "pandoc" / "scripts"
SETUP_SH = SCRIPTS / "setup.sh"
SETUP_PS1 = SCRIPTS / "setup.ps1"
BASH = shutil.which("bash")
IS_WINDOWS = platform.system() == "Windows"


def powershell():
    if not IS_WINDOWS:
        return None
    return shutil.which("powershell.exe") or shutil.which("powershell")


# --------------------------------------------------------------------- static rules


def test_no_auto_accept_flags_anywhere():
    for script in (SETUP_SH, SETUP_PS1):
        text = script.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert "--accept-package-agreements" not in code
        assert "--accept-source-agreements" not in code
        assert "--noconfirm" not in code
        assert not re.search(r"install\s+-y\b|\s-y\s", code), script.name


def test_ps1_checks_native_exit_codes_and_keeps_builtins():
    text = SETUP_PS1.read_text(encoding="utf-8")
    assert "$LASTEXITCODE" in text
    assert "function Write-Warning" not in text and "function Write-Error" not in text


def test_miktex_autoinstall_is_opt_in():
    text = SETUP_PS1.read_text(encoding="utf-8")
    idx = text.index('--set-config-value="[MPM]AutoInstall=1"')
    assert "$EnableAutoInstall" in text[:idx].rsplit("if (", 1)[-1] or "$EnableAutoInstall -and" in text[:idx]


def test_reference_no_longer_mandates_global_miktex_change():
    guide = (ROOT / "reference" / "format_guide.md").read_text(encoding="utf-8")
    assert "ALWAYS** ensure auto-install" not in guide
    assert "Ask the user first" in guide


def test_skill_has_overwrite_and_sandbox_rules():
    skill = (ROOT / "skills" / "pandoc" / "SKILL.md").read_text(encoding="utf-8")
    assert "ask before overwriting" in skill.lower()
    assert "--sandbox" in skill
    assert "never an instruction" in " ".join(skill.split())


# --------------------------------------------------------------------- setup.sh


@pytest.fixture
def fakebin(tmp_path):
    """A bin dir whose installers only record that they were called."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    record = tmp_path / "calls.log"
    for name in ("sudo", "apt-get", "brew", "winget", "dnf", "pacman"):
        script = bindir / name
        script.write_text('#!/bin/sh\necho "%s $*" >> "%s"\nexit 1\n' % (name, record.as_posix()),
                          encoding="utf-8", newline="\n")
        script.chmod(0o755)
    return bindir, record


def run_sh(args, fakebin, ostype=None):
    bindir, _ = fakebin
    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + os.path.dirname(BASH)
    script = SETUP_SH.as_posix()
    if ostype:
        command = 'OSTYPE=%s; source "%s" %s' % (ostype, script, " ".join(args))
        argv = [BASH, "-c", command]
    else:
        argv = [BASH, script] + list(args)
    return subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=60)


needs_bash = pytest.mark.skipif(BASH is None, reason="bash not available")


@needs_bash
def test_setup_sh_parses():
    assert subprocess.run([BASH, "-n", SETUP_SH.as_posix()], timeout=30).returncode == 0


@needs_bash
def test_non_interactive_run_only_prints_commands(fakebin):
    result = run_sh([], fakebin, ostype="linux-gnu")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Check-only mode" in result.stdout
    assert "apt-get install pandoc" not in result.stdout or "sudo apt-get install pandoc" in result.stdout
    assert not fakebin[1].exists(), "an installer ran without --install"


@needs_bash
def test_print_only_lists_apt_commands_without_y(fakebin):
    result = run_sh(["--print-only"], fakebin, ostype="linux-gnu")
    assert result.returncode == 0
    assert "sudo apt-get install pandoc" in result.stdout
    assert " -y" not in result.stdout


@needs_bash
def test_quiet_completes_instead_of_aborting(fakebin):
    result = run_sh(["--quiet", "--print-only", "--skip-latex"], fakebin, ostype="linux-gnu")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Run these yourself" in result.stdout


@needs_bash
def test_failed_install_is_reported_as_failure(fakebin):
    result = run_sh(["--install", "--skip-latex"], fakebin, ostype="linux-gnu")
    assert result.returncode == 1
    assert "installation failed" in result.stdout
    calls = fakebin[1].read_text(encoding="utf-8")
    assert "sudo apt-get install pandoc" in calls
    assert "-y" not in calls


@needs_bash
def test_windows_shell_never_installs(fakebin):
    result = run_sh(["--install"], fakebin, ostype="msys")
    assert result.returncode == 0
    assert "winget install --id JohnMacFarlane.Pandoc -e" in result.stdout
    assert not fakebin[1].exists()


# --------------------------------------------------------------------- setup.ps1


needs_ps = pytest.mark.skipif(powershell() is None, reason="Windows PowerShell not available")


@needs_ps
def test_setup_ps1_parses():
    command = ("$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               "$env:PDC_SCRIPT, [ref]$null, [ref]$errors); $errors.Count")
    result = subprocess.run([powershell(), "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, timeout=60,
                            env=dict(os.environ, PDC_SCRIPT=str(SETUP_PS1)))
    assert result.stdout.strip() == "0", result.stdout + result.stderr


def run_ps1(tmp_path, *args):
    bindir = tmp_path / "winbin"
    bindir.mkdir(exist_ok=True)
    record = tmp_path / "winget.log"
    (bindir / "winget.cmd").write_text('@echo %%* >> "%s"\r\n@exit /b 1\r\n' % record, encoding="ascii")
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(bindir), system32, os.path.dirname(powershell())])
    env["LOCALAPPDATA"] = str(tmp_path / "local")
    env["ProgramFiles"] = str(tmp_path / "pf")
    result = subprocess.run([powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(SETUP_PS1)] + list(args),
                            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    return result, record


@needs_ps
def test_ps1_print_only_installs_nothing(tmp_path):
    result, record = run_ps1(tmp_path, "-PrintOnly", "-SkipLatex")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "winget install --id JohnMacFarlane.Pandoc -e" in result.stdout
    assert not record.exists()


@needs_ps
def test_ps1_reports_winget_failure(tmp_path):
    result, record = run_ps1(tmp_path, "-Install", "-SkipLatex")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "installation failed" in result.stdout
    calls = record.read_text(encoding="ascii", errors="replace")
    assert "JohnMacFarlane.Pandoc" in calls
    assert "accept" not in calls
