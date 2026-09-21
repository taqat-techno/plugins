#!/usr/bin/env python3
"""Stage 04 - build/render: turn captured clips into a Remotion timeline.

Each captured step becomes one <Sequence> whose length is that clip's measured
duration, so its caption is on screen for exactly as long as the clip and not a
frame longer. Clip length is measured, never assumed:

  1. ffprobe, when it is on PATH                      (frame-accurate)
  2. `npx remotion ffprobe`, using Remotion's bundled ffmpeg
  3. the wall-clock time the capture stage recorded   (approximate, warned)

Writes a self-contained Remotion project and optionally renders it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from _common import die, info, read_json, run_dir, slugify, warn, which, write_json

FPS = 30
TITLE_SECONDS = 3.0
ITEM_CARD_SECONDS = 2.0
OUTRO_SECONDS = 2.5
PAD_SECONDS = 0.35


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build (and optionally render) the video.")
    p.add_argument("--capture-log", required=True)
    p.add_argument("--out", help="Remotion project dir (default: run dir 04-render)")
    p.add_argument("--video-out", help="Rendered file path")
    p.add_argument("--fps", type=int, default=FPS)
    p.add_argument("--render", action="store_true", help="Run the render after building")
    p.add_argument("--narrate", action="store_true",
                   help="Generate edge-tts narration from each caption")
    p.add_argument("--voice", default="en-US-AriaNeural")
    p.add_argument("--install", action="store_true", help="Run npm install first")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# duration measurement
# --------------------------------------------------------------------------- #
def probe_duration(path: Path) -> tuple[float | None, str]:
    if which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60,
            )
            if out.returncode == 0:
                value = json.loads(out.stdout).get("format", {}).get("duration")
                if value:
                    return float(value), "ffprobe"
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            pass

    if which("npx"):
        try:
            out = subprocess.run(
                ["npx", "--yes", "remotion", "ffprobe", str(path)],
                capture_output=True, text=True, timeout=180,
                shell=(os.name == "nt"),
            )
            blob = (out.stdout or "") + (out.stderr or "")
            match = re.search(r"durationInSeconds[\"']?\s*[:=]\s*([0-9.]+)", blob)
            if not match:
                match = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", blob)
                if match:
                    h, m, s = match.groups()
                    return int(h) * 3600 + int(m) * 60 + float(s), "remotion-ffprobe"
            if match:
                return float(match.group(1)), "remotion-ffprobe"
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

    return None, "unmeasured"


def scene_frames(seconds: float, fps: int) -> int:
    return max(1, int(round(seconds * fps)))


# --------------------------------------------------------------------------- #
# timeline
# --------------------------------------------------------------------------- #
def build_timeline(log: dict, project: Path, fps: int, script: dict | None):
    public = project / "public" / "clips"
    public.mkdir(parents=True, exist_ok=True)

    scenes = []
    intro = (script or {}).get("intro") or {}
    sprint = log.get("sprint") or "Sprint"
    scenes.append({
        "type": "title",
        "durationInFrames": scene_frames(TITLE_SECONDS, fps),
        "title": intro.get("title") or (str(sprint) + " - what we shipped"),
        "subtitle": intro.get("subtitle") or log.get("base_url", ""),
    })

    usable = [r for r in log.get("steps", []) if r.get("status") == "ok" and r.get("clip")]
    if not usable:
        die(
            "No usable clips in the capture log. Every step either failed or was "
            "skipped -- fix the step script and re-run the capture stage."
        )

    by_item: dict = {}
    for row in usable:
        by_item.setdefault(row["work_item"], []).append(row)

    titles = {
        item.get("work_item"): item.get("title", "")
        for item in (script or {}).get("items", [])
    }
    parents = {
        item.get("work_item"): item.get("parent_pbi")
        for item in (script or {}).get("items", [])
    }

    approximate = 0
    for work_item, rows in by_item.items():
        scenes.append({
            "type": "item",
            "durationInFrames": scene_frames(ITEM_CARD_SECONDS, fps),
            "workItem": work_item,
            "title": titles.get(work_item, ""),
            "parent": parents.get(work_item),
            "role": rows[0].get("role"),
            "stepCount": len(rows),
        })
        for index, row in enumerate(rows, start=1):
            source = Path(row["clip"])
            target = public / source.name
            shutil.copyfile(source, target)

            seconds, how = probe_duration(source)
            if seconds is None:
                seconds = max(1.0, (row.get("wall_ms") or 3000) / 1000.0)
                approximate += 1
            scenes.append({
                "type": "step",
                "durationInFrames": scene_frames(seconds + PAD_SECONDS, fps),
                "clip": "clips/" + source.name,
                "caption": row.get("caption", ""),
                "workItem": work_item,
                "role": row.get("role"),
                "start": row.get("start"),
                "index": index,
                "total": len(rows),
                "measuredBy": how,
            })

    scenes.append({
        "type": "outro",
        "durationInFrames": scene_frames(OUTRO_SECONDS, fps),
        "title": "Reproduce every step",
        "subtitle": "See the HTML guide published with this video",
    })

    if approximate:
        warn(
            str(approximate) + " clip(s) could not be measured; their captions use "
            "wall-clock timing and may be off by a few frames. Install ffmpeg for "
            "frame-accurate sequencing."
        )
    return scenes


# --------------------------------------------------------------------------- #
# narration (optional)
# --------------------------------------------------------------------------- #
def narrate(scenes: list, project: Path, voice: str) -> None:
    if not which("edge-tts"):
        warn("--narrate requested but edge-tts is not on PATH; "
             "install it with `pip install edge-tts`. Continuing without audio.")
        return
    audio_dir = project / "public" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, scene in enumerate(scenes):
        text = scene.get("caption") or scene.get("title")
        if scene["type"] not in ("step", "title") or not text:
            continue
        out = audio_dir / (slugify(str(i) + "-" + str(text)[:40]) + ".mp3")
        try:
            result = subprocess.run(
                ["edge-tts", "--voice", voice, "--text", str(text),
                 "--write-media", str(out)],
                capture_output=True, text=True, timeout=120,
                shell=(os.name == "nt"),
            )
            if result.returncode == 0 and out.exists():
                scene["audio"] = "audio/" + out.name
        except (OSError, subprocess.SubprocessError):
            warn("narration failed for scene " + str(i))


# --------------------------------------------------------------------------- #
# project scaffolding
# --------------------------------------------------------------------------- #
def scaffold(project: Path, templates: Path) -> None:
    (project / "src").mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "remotion.config.ts", "tsconfig.json"):
        source = templates / name
        if source.exists():
            shutil.copyfile(source, project / name)
    for name in ("Root.tsx", "SprintRecap.tsx", "Caption.tsx", "index.ts"):
        source = templates / "src" / name
        if source.exists():
            shutil.copyfile(source, project / "src" / name)


def main() -> int:
    args = parse_args()
    log = read_json(Path(args.capture_log))

    capture_dir = Path(args.capture_log).parent
    script = None
    for candidate in (capture_dir.parent / "02-script" / "steps.yaml",
                      capture_dir.parent / "02-script" / "steps.json"):
        if candidate.exists():
            from _yaml import load as yaml_load
            script = yaml_load(candidate.read_text(encoding="utf-8"))
            break
    if script is None:
        warn("No step script found next to the capture log; item titles will be blank.")

    project = Path(args.out) if args.out else run_dir(
        log.get("sprint", "sprint")) / "04-render"
    project.mkdir(parents=True, exist_ok=True)

    templates = Path(__file__).resolve().parent.parent / "templates" / "remotion"
    scaffold(project, templates)

    scenes = build_timeline(log, project, args.fps, script)
    if args.narrate:
        narrate(scenes, project, args.voice)

    total_frames = sum(s["durationInFrames"] for s in scenes)
    data = {
        "fps": args.fps,
        "width": (log.get("viewport") or {}).get("width", 1280),
        "height": (log.get("viewport") or {}).get("height", 720),
        "sprint": log.get("sprint"),
        "durationInFrames": total_frames,
        "scenes": scenes,
    }
    write_json(project / "src" / "data.json", data)

    info("built timeline: " + str(len(scenes)) + " scenes, " + str(total_frames)
         + " frames (" + str(round(total_frames / args.fps, 1)) + "s)")

    if args.install or args.render:
        if not which("npm"):
            die("npm is not on PATH; Node 18+ is required to render.")
        if args.install:
            info("running npm install ...")
            subprocess.run(["npm", "install", "--silent"], cwd=project,
                           check=False, shell=(os.name == "nt"))

    if args.render:
        video_out = Path(args.video_out) if args.video_out else (
            project / ("sprint-" + slugify(str(log.get("sprint", "recap"))) + ".mp4")
        )
        video_out.parent.mkdir(parents=True, exist_ok=True)
        info("rendering -> " + str(video_out))
        result = subprocess.run(
            ["npx", "--yes", "remotion", "render", "SprintRecap", str(video_out)],
            cwd=project, check=False, shell=(os.name == "nt"),
        )
        if result.returncode != 0:
            die("Remotion render failed. Run `npx remotion studio` in "
                + str(project) + " to debug the composition.")
        print(video_out)
    else:
        info("project ready. Preview: cd " + str(project)
             + " && npm install && npx remotion studio")
        print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
