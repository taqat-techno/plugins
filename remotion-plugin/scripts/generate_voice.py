"""
Remotion Plugin - Voice Generation via edge-tts

Generates MP3 narration from text using Microsoft Neural TTS voices.
No API key required. 300+ voices across 70+ languages.

DATA EGRESS: edge-tts is an unofficial client of Microsoft Edge's online
read-aloud service. Every narration string is sent to Microsoft's servers over
the network. It is not an SLA-backed or explicitly commercially licensed API.
Do not narrate confidential text you may not share with Microsoft.

Usage:
    python generate_voice.py --text "Hello world" --output output.mp3
    python generate_voice.py --text "Hello world" --voice "en-GB-RyanNeural" --output output.mp3
    python generate_voice.py --file script.txt --output output.mp3
    python generate_voice.py --list-voices
    python generate_voice.py --list-voices --language "en"
    python generate_voice.py --scenes scenes.json --output-dir public/audio/ --fps 30
"""

import argparse
import asyncio
import json
import math
import os
import re
import sys

# Allow importing _common from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import check_dependencies

# A scene id becomes a file name inside --output-dir, so it may not carry a path.
SCENE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

EGRESS_NOTICE = ("NOTE: edge-tts sends the narration text to Microsoft's online "
                 "text-to-speech service.")


def frames_for(duration_seconds, fps):
    """Frames needed to cover the audio: always rounded UP, never truncated."""
    return math.ceil(duration_seconds * fps)


def validate_scenes(scenes):
    """Return the scene list or raise ValueError naming the first bad entry."""
    if not isinstance(scenes, list):
        raise ValueError("scenes JSON must be a list of {\"id\", \"text\"} objects")
    seen = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or "id" not in scene or "text" not in scene:
            raise ValueError("scene {0} needs \"id\" and \"text\"".format(index))
        scene_id = scene["id"]
        if not isinstance(scene_id, str) or not SCENE_ID_RE.match(scene_id):
            raise ValueError(
                "scene {0} id {1!r} must be 1-64 characters of A-Z a-z 0-9 _ -".format(index, scene_id))
        if scene_id in seen:
            raise ValueError("duplicate scene id {0!r}".format(scene_id))
        seen.add(scene_id)
    return scenes


async def list_voices(language_filter=None):
    """List available edge-tts voices."""
    import edge_tts

    voices = await edge_tts.list_voices()

    if language_filter:
        voices = [v for v in voices if v["Locale"].lower().startswith(language_filter.lower())]

    print(f"\n{'Voice Name':<35} {'Gender':<10} {'Locale':<10}")
    print("-" * 60)
    for v in sorted(voices, key=lambda x: x["Locale"]):
        print(f"{v['ShortName']:<35} {v['Gender']:<10} {v['Locale']:<10}")

    print(f"\nTotal: {len(voices)} voices")


async def generate_voice(text, voice, output_path, fps=30, rate=None, pitch=None, retries=3):
    """Generate MP3 from text using edge-tts with retry logic.

    Args:
        text: Text to convert to speech
        voice: edge-tts voice name
        output_path: Output MP3 file path
        fps: Video FPS for frame calculations
        rate: Speech rate adjustment (e.g., "+10%", "-20%")
        pitch: Pitch adjustment (e.g., "+10Hz", "-5Hz")
        retries: Number of retry attempts on network failure
    """
    import edge_tts
    from mutagen.mp3 import MP3

    kwargs = {}
    if rate:
        kwargs["rate"] = rate
    if pitch:
        kwargs["pitch"] = pitch

    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice, **kwargs)
            await communicate.save(output_path)
            break
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(
                    f"WARNING: edge-tts attempt {attempt + 1}/{retries} failed: {e}. "
                    f"Retrying in {wait}s...",
                    file=sys.stderr,
                )
                await asyncio.sleep(wait)
            else:
                print(
                    f"ERROR: edge-tts failed after {retries} attempts: {e}",
                    file=sys.stderr,
                )
                print(
                    "Check your internet connection. edge-tts requires access to Microsoft servers.",
                    file=sys.stderr,
                )
                sys.exit(1)

    audio = MP3(output_path)
    duration_seconds = audio.info.length
    duration_ms = int(duration_seconds * 1000)
    file_size = os.path.getsize(output_path)

    result = {
        "file": output_path,
        "voice": voice,
        "duration_seconds": round(duration_seconds, 3),
        "duration_ms": duration_ms,
        "duration_frames": frames_for(duration_seconds, fps),
        "fps": fps,
        "file_size_bytes": file_size,
        "text_length": len(text),
    }

    print(json.dumps(result, indent=2))
    return result


async def generate_multi_scene(scenes_json_path, output_dir, voice, fps=30, rate=None, pitch=None):
    """Generate voice for multiple scenes from a JSON file.

    JSON format:
    [
        {"id": "scene01", "text": "Scene 1 narration..."},
        {"id": "scene02", "text": "Scene 2 narration..."}
    ]
    """
    with open(scenes_json_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)
    try:
        validate_scenes(scenes)
    except ValueError as exc:
        print("ERROR: {0}".format(exc), file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for scene in scenes:
        scene_id = scene["id"]
        text = scene["text"]
        output_path = os.path.join(output_dir, f"{scene_id}.mp3")

        print(f"Generating {scene_id}...", file=sys.stderr)
        result = await generate_voice(text, voice, output_path, fps=fps, rate=rate, pitch=pitch)
        result["scene_id"] = scene_id
        results.append(result)

    summary = {
        "total_scenes": len(results),
        "total_duration_ms": sum(r["duration_ms"] for r in results),
        "total_duration_seconds": round(sum(r["duration_seconds"] for r in results), 3),
        "output_dir": output_dir,
        "voice": voice,
        "fps": fps,
        "scenes": results,
    }

    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Generate voice narration using edge-tts (sends the text to Microsoft's online TTS service)"
    )

    parser.add_argument("--text", type=str, help="Text to convert to speech")
    parser.add_argument("--file", type=str, help="Text file to read content from")
    parser.add_argument("--scenes", type=str, help="JSON file with scene definitions for batch generation")
    parser.add_argument("--output", type=str, help="Output MP3 file path")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory for batch generation")
    parser.add_argument("--voice", type=str, default="en-US-AriaNeural",
                        help="Voice name (default: en-US-AriaNeural)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Video FPS for frame calculations (default: 30)")
    parser.add_argument("--rate", type=str, default=None,
                        help="Speech rate adjustment (e.g., '+10%%', '-20%%')")
    parser.add_argument("--pitch", type=str, default=None,
                        help="Pitch adjustment (e.g., '+10Hz', '-5Hz')")
    parser.add_argument("--list-voices", action="store_true",
                        help="List all available voices")
    parser.add_argument("--language", type=str, default=None,
                        help="Filter voices by language (e.g., 'en', 'ar', 'fr')")

    args = parser.parse_args()

    check_dependencies("voice")

    if args.list_voices:
        asyncio.run(list_voices(args.language))
        return

    print(EGRESS_NOTICE, file=sys.stderr)

    if args.scenes:
        if not os.path.exists(args.scenes):
            print(f"ERROR: Scenes file not found: {args.scenes}")
            sys.exit(1)
        asyncio.run(generate_multi_scene(
            args.scenes, args.output_dir, args.voice, fps=args.fps, rate=args.rate, pitch=args.pitch
        ))
        return

    if not args.text and not args.file:
        parser.error("Provide --text, --file, or --scenes")

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text

    if not args.output:
        parser.error("--output is required for single text generation")

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    asyncio.run(generate_voice(text, args.voice, args.output, fps=args.fps, rate=args.rate, pitch=args.pitch))


if __name__ == "__main__":
    main()
