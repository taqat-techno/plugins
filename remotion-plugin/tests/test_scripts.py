"""Offline tests for the voice-pipeline scripts. No network, no edge-tts, no ffmpeg
binary: durations are stubbed or measured from hand-built MP3 frames, and ffmpeg is
replaced by a recording fake.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib
import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

concat_audio = importlib.import_module("concat_audio")
generate_voice = importlib.import_module("generate_voice")
measure_audio = importlib.import_module("measure_audio")
setup_check = importlib.import_module("setup_check")
_common = importlib.import_module("_common")

# MPEG-1 Layer III, 128 kbps, 44.1 kHz, mono, no padding: 417 bytes per frame,
# 1152 samples (26.12 ms) per frame. Mutagen measures CBR files from their size.
FRAME = bytes([0xFF, 0xFB, 0x90, 0xC4]) + bytes(413)


def write_mp3(path: Path, frames: int) -> Path:
    path.write_bytes(FRAME * frames)
    return path


def fake_durations(monkeypatch, durations):
    """Make get_audio_duration_ms return a fixed duration per file name."""
    monkeypatch.setattr(concat_audio, "get_audio_duration_ms",
                        lambda path: durations[Path(path).name])


# --------------------------------------------------------------------------- concat


def test_simple_mode_timestamps_are_cumulative_durations(tmp_path, monkeypatch):
    files = []
    for name in ("a.mp3", "b.mp3", "c.mp3"):
        (tmp_path / name).write_bytes(b"x")
        files.append(str(tmp_path / name))
    fake_durations(monkeypatch, {"a.mp3": 1000, "b.mp3": 2500, "c.mp3": 700})

    segments, total = concat_audio.concat_simple(files, str(tmp_path / "out.mp3"), gap_ms=200)

    assert [(s["start_ms"], s["end_ms"]) for s in segments] == [(0, 1000), (1000, 3500), (3500, 4200)]
    assert total == 4200
    assert (tmp_path / "out.mp3").read_bytes() == b"xxx"


def test_simple_mode_reports_zero_gap(tmp_path, monkeypatch, capsys):
    for name in ("a.mp3", "b.mp3"):
        write_mp3(tmp_path / name, 10)
    monkeypatch.setattr(sys, "argv", ["concat_audio.py", "--files", str(tmp_path / "a.mp3"),
                                      str(tmp_path / "b.mp3"), "--output", str(tmp_path / "o.mp3"),
                                      "--method", "simple", "--gap", "200"])
    monkeypatch.setattr(concat_audio, "check_dependencies", lambda group: None)
    fake_durations(monkeypatch, {"a.mp3": 1000, "b.mp3": 1000, "o.mp3": 2000})
    concat_audio.main()
    result = json.loads(capsys.readouterr().out)
    assert result["gap_ms"] == 0
    assert result["segments"][1]["start_ms"] == 1000
    assert result["segments"][1]["start_frame"] == 30


def test_ffmpeg_mode_reencodes_and_matches_sample_rate(tmp_path, monkeypatch):
    files = [str(write_mp3(tmp_path / n, 5)) for n in ("a.mp3", "b.mp3")]
    fake_durations(monkeypatch, {"a.mp3": 1000, "b.mp3": 1500})
    monkeypatch.setattr(concat_audio, "_audio_format", lambda path: (24000, 1))
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if "concat" in argv:
            listing = Path(argv[argv.index("-i") + 1]).read_text(encoding="utf-8")
            calls.append(listing)
        return SimpleNamespace(returncode=0, stderr="")

    segments, total = concat_audio.concat_with_ffmpeg(files, str(tmp_path / "o.mp3"), 200, runner=runner)

    silence, concat, listing = calls
    assert "anullsrc=r=24000:cl=mono" in silence
    assert "-c" not in concat and "copy" not in concat
    assert concat[concat.index("-c:a") + 1] == "libmp3lame"
    assert concat[concat.index("-ar") + 1] == "24000"
    assert listing.count("file '") == 3          # a, silence, b
    assert [s["start_ms"] for s in segments] == [0, 1200]
    assert total == 2700


def test_ffmpeg_silence_failure_aborts(tmp_path, monkeypatch):
    files = [str(write_mp3(tmp_path / n, 5)) for n in ("a.mp3", "b.mp3")]
    fake_durations(monkeypatch, {"a.mp3": 1000, "b.mp3": 1000})
    monkeypatch.setattr(concat_audio, "_audio_format", lambda path: (24000, 1))
    runner = lambda argv, **kw: SimpleNamespace(returncode=1, stderr="boom")  # noqa: E731
    with pytest.raises(SystemExit):
        concat_audio.concat_with_ffmpeg(files, str(tmp_path / "o.mp3"), 200, runner=runner)


def test_ffconcat_line_escapes_single_quotes(tmp_path):
    line = concat_audio._ffconcat_line(str(tmp_path / "it's.mp3"))
    assert line.endswith("it'\\''s.mp3'\n")
    assert line.startswith("file '")


def test_negative_gap_is_rejected(tmp_path, monkeypatch):
    write_mp3(tmp_path / "a.mp3", 2)
    monkeypatch.setattr(sys, "argv", ["concat_audio.py", "--files", str(tmp_path / "a.mp3"),
                                      "--output", str(tmp_path / "o.mp3"), "--gap", "-5"])
    monkeypatch.setattr(concat_audio, "check_dependencies", lambda group: None)
    with pytest.raises(SystemExit):
        concat_audio.main()


# --------------------------------------------------------------------------- generate_voice


def test_frames_round_up_never_overcount():
    assert generate_voice.frames_for(1.0, 30) == 30        # exact multiple: no extra frame
    assert generate_voice.frames_for(1.01, 30) == 31
    assert generate_voice.frames_for(0.0, 30) == 0


@pytest.mark.parametrize("bad", ["../escape", "a/b", "a\\b", "", "x" * 65, 7, "dot.mp3"])
def test_scene_ids_that_could_be_paths_are_rejected(bad):
    with pytest.raises(ValueError):
        generate_voice.validate_scenes([{"id": bad, "text": "hi"}])


def test_valid_scenes_pass_and_duplicates_fail():
    ok = [{"id": "scene_01", "text": "a"}, {"id": "scene-02", "text": "b"}]
    assert generate_voice.validate_scenes(ok) == ok
    with pytest.raises(ValueError):
        generate_voice.validate_scenes([{"id": "s", "text": "a"}, {"id": "s", "text": "b"}])
    with pytest.raises(ValueError):
        generate_voice.validate_scenes({"id": "s"})


def test_scene_file_with_traversal_exits_before_any_network_call(tmp_path):
    scenes = tmp_path / "scenes.json"
    scenes.write_text(json.dumps([{"id": "../../evil", "text": "x"}]), encoding="utf-8")
    import asyncio
    with pytest.raises(SystemExit):
        asyncio.run(generate_voice.generate_multi_scene(str(scenes), str(tmp_path / "out"), "v"))
    assert not (tmp_path / "out").exists()


def test_generate_voice_discloses_egress_in_help():
    out = subprocess.run([sys.executable, str(SCRIPTS / "generate_voice.py"), "--help"],
                         capture_output=True, text=True, timeout=60).stdout
    assert "Microsoft" in out


# --------------------------------------------------------------------------- measure / common


def test_measure_file_uses_ceil_and_padding(tmp_path):
    pytest.importorskip("mutagen")
    path = write_mp3(tmp_path / "n.mp3", 40)               # ~1.045 s
    result = measure_audio.measure_file(str(path), fps=30, expected_ms=1045)
    assert result["duration_frames"] == math.ceil(result["duration_seconds"] * 30)
    assert result["duration_frames_with_padding"] == result["duration_frames"] + 30
    assert result["sample_rate"] == 44100
    assert result["status"] == "PASS"


def test_measure_file_flags_large_difference(tmp_path):
    pytest.importorskip("mutagen")
    path = write_mp3(tmp_path / "n.mp3", 40)
    assert measure_audio.measure_file(str(path), fps=30, expected_ms=5000)["status"] == "FAIL"


def test_measure_directory_builds_scene_constants(tmp_path):
    pytest.importorskip("mutagen")
    write_mp3(tmp_path / "01_intro.mp3", 20)
    write_mp3(tmp_path / "02_outro.mp3", 20)
    summary = measure_audio.measure_directory(str(tmp_path), fps=30)
    assert summary["file_count"] == 2
    assert set(summary["scene_duration_constant"]) == {"intro", "outro"}


def test_common_duration_in_ms(tmp_path):
    pytest.importorskip("mutagen")
    path = write_mp3(tmp_path / "n.mp3", 100)                # 100 * 26.12 ms
    assert abs(_common.get_audio_duration_ms(str(path)) - 2612) <= 30


def test_check_dependencies_exits_with_install_hint(monkeypatch, capsys):
    monkeypatch.setitem(_common._PACKAGE_GROUPS, "audio", ["surely_not_installed_pkg_xyz"])
    with pytest.raises(SystemExit):
        _common.check_dependencies("audio")
    assert "pip install" in capsys.readouterr().out


# --------------------------------------------------------------------------- setup_check


def test_setup_check_never_suggests_piping_a_script_into_root():
    source = (SCRIPTS / "setup_check.py").read_text(encoding="utf-8")
    assert "| sudo" not in source and "|sudo" not in source


def test_parse_version():
    assert setup_check.parse_version("v20.11.1") == (20, 11, 1)
    assert setup_check.parse_version("garbage") == (0, 0, 0)


def test_setup_check_reports_missing_node(monkeypatch, capsys):
    monkeypatch.setattr(setup_check, "check_command", lambda cmd, flag="--version": (False, None))
    monkeypatch.setattr(setup_check, "check_python_package", lambda name: (True, "1.0"))
    assert setup_check.main() == 1
    out = capsys.readouterr().out
    assert "Not installed" in out and "Install:" in out


def _windows_like_path(monkeypatch, calls):
    """Simulate Windows: `npm`/`npx` exist only as `.cmd` shims that shutil.which finds
    via PATHEXT, and CreateProcess cannot start the bare name."""
    shims = {"node": r"C:\Program Files\nodejs\node.exe",
             "npm": r"C:\Program Files\nodejs\npm.cmd",
             "npx": r"C:\Program Files\nodejs\npx.cmd"}
    monkeypatch.setattr(setup_check.shutil, "which", lambda cmd: shims.get(cmd))
    versions = {"node.exe": "v20.11.1", "npm.cmd": "10.2.4", "npx.cmd": "10.2.4"}

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        assert not kwargs.get("shell"), "must not go through shell=True"
        name = argv[0].replace("\\", "/").rsplit("/", 1)[-1]
        if name not in versions:  # a bare `npm` is what CreateProcess cannot find
            raise FileNotFoundError(argv[0])
        return SimpleNamespace(stdout=versions[name] + "\n", stderr="", returncode=0)

    monkeypatch.setattr(setup_check.subprocess, "run", fake_run)


def test_check_command_runs_the_resolved_cmd_shim_on_windows(monkeypatch):
    calls = []
    _windows_like_path(monkeypatch, calls)
    assert setup_check.check_command("npm") == (True, "10.2.4")
    assert setup_check.check_command("npx") == (True, "10.2.4")
    assert calls[0][0] == [r"C:\Program Files\nodejs\npm.cmd", "--version"]
    assert all(not kw.get("shell") for _, kw in calls)


def test_check_command_reports_missing_without_running_anything(monkeypatch):
    calls = []
    _windows_like_path(monkeypatch, calls)
    assert setup_check.check_command("ffmpeg", "-version") == (False, None)
    assert calls == []


def test_setup_check_passes_npm_on_windows(monkeypatch, capsys):
    calls = []
    _windows_like_path(monkeypatch, calls)
    monkeypatch.setattr(setup_check, "check_python_package", lambda name: (True, "1.0"))
    assert setup_check.main() == 0
    out = capsys.readouterr().out
    npm_block = out.split("[2/6] npm", 1)[1].split("[3/6]", 1)[0]
    assert "PASS  10.2.4" in npm_block
    assert "Interpreter for the plugin scripts" in out


def test_check_command_unmocked_finds_the_running_python():
    found, version = setup_check.check_command(sys.executable)
    assert found and "Python" in version
