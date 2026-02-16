"""
Remotion Plugin - Voice Generation via edge-tts (FREE)

Generates MP3 narration from text using Microsoft Neural TTS voices.
No API key required. 300+ voices across 70+ languages.

Usage:
    python generate_voice.py --text "Hello world" --output output.mp3
    python generate_voice.py --text "Hello world" --voice "en-GB-RyanNeural" --output output.mp3
    python generate_voice.py --file script.txt --output output.mp3
    python generate_voice.py --list-voices
    python generate_voice.py --list-voices --language "en"
"""

import argparse
import asyncio
import json
import os
import sys


def check_dependencies():
    """Verify required packages are installed."""
    missing = []
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        missing.append("edge-tts")
    try:
        from mutagen.mp3 import MP3  # noqa: F401
    except ImportError:
        missing.append("mutagen")

    if missing:
        print(f"ERROR: Missing packages: {', '.join(missing)}")
        print(f"Install: {sys.executable} -m pip install {' '.join(missing)}")
        sys.exit(1)


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


async def generate_voice(text, voice, output_path, rate=None, pitch=None):
    """Generate MP3 from text using edge-tts."""
    import edge_tts
    from mutagen.mp3 import MP3

    # Build rate/pitch string
    kwargs = {}
    if rate:
        kwargs["rate"] = rate
    if pitch:
        kwargs["pitch"] = pitch

    # Generate audio
    communicate = edge_tts.Communicate(text, voice, **kwargs)
    await communicate.save(output_path)

    # Measure actual duration
    audio = MP3(output_path)
    duration_seconds = audio.info.length
    duration_ms = int(duration_seconds * 1000)
    file_size = os.path.getsize(output_path)

    # Output result as JSON for easy parsing
    result = {
        "file": output_path,
        "voice": voice,
        "duration_seconds": round(duration_seconds, 3),
        "duration_ms": duration_ms,
        "duration_frames_30fps": int(duration_seconds * 30) + 1,
        "file_size_bytes": file_size,
        "text_length": len(text),
    }

    print(json.dumps(result, indent=2))
    return result


async def generate_multi_scene(scenes_json_path, output_dir, voice, rate=None, pitch=None):
    """Generate voice for multiple scenes from a JSON file.

    JSON format:
    [
        {"id": "scene01", "text": "Scene 1 narration..."},
        {"id": "scene02", "text": "Scene 2 narration..."}
    ]
    """
    with open(scenes_json_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for scene in scenes:
        scene_id = scene["id"]
        text = scene["text"]
        output_path = os.path.join(output_dir, f"{scene_id}.mp3")

        print(f"Generating {scene_id}...", file=sys.stderr)
        result = await generate_voice(text, voice, output_path, rate, pitch)
        result["scene_id"] = scene_id
        results.append(result)

    # Print all results
    summary = {
        "total_scenes": len(results),
        "total_duration_ms": sum(r["duration_ms"] for r in results),
        "total_duration_seconds": round(sum(r["duration_seconds"] for r in results), 3),
        "output_dir": output_dir,
        "voice": voice,
        "scenes": results,
    }

    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Generate voice narration using edge-tts (FREE Microsoft Neural TTS)"
    )

    parser.add_argument("--text", type=str, help="Text to convert to speech")
    parser.add_argument("--file", type=str, help="Text file to read content from")
    parser.add_argument("--scenes", type=str, help="JSON file with scene definitions for batch generation")
    parser.add_argument("--output", type=str, help="Output MP3 file path")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory for batch generation")
    parser.add_argument("--voice", type=str, default="en-US-AriaNeural",
                        help="Voice name (default: en-US-AriaNeural)")
    parser.add_argument("--rate", type=str, default=None,
                        help="Speech rate adjustment (e.g., '+10%%', '-20%%')")
    parser.add_argument("--pitch", type=str, default=None,
                        help="Pitch adjustment (e.g., '+10Hz', '-5Hz')")
    parser.add_argument("--list-voices", action="store_true",
                        help="List all available voices")
    parser.add_argument("--language", type=str, default=None,
                        help="Filter voices by language (e.g., 'en', 'ar', 'fr')")

    args = parser.parse_args()

    check_dependencies()

    # List voices mode
    if args.list_voices:
        asyncio.run(list_voices(args.language))
        return

    # Batch scene generation mode
    if args.scenes:
        if not os.path.exists(args.scenes):
            print(f"ERROR: Scenes file not found: {args.scenes}")
            sys.exit(1)
        asyncio.run(generate_multi_scene(
            args.scenes, args.output_dir, args.voice, args.rate, args.pitch
        ))
        return

    # Single text generation mode
    if not args.text and not args.file:
        parser.error("Provide --text, --file, or --scenes")

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text

    if not args.output:
        parser.error("--output is required for single text generation")

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    asyncio.run(generate_voice(text, args.voice, args.output, args.rate, args.pitch))


if __name__ == "__main__":
    main()
