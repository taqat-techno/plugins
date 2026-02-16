"""
Remotion Plugin - Audio Duration Measurement & Validation

Measures actual MP3 duration and validates against expected timing.
Use this to verify that frame calculations match real audio length.

Usage:
    python measure_audio.py audio.mp3
    python measure_audio.py audio.mp3 --expected-ms 45000
    python measure_audio.py audio.mp3 --expected-ms 45000 --fps 30
    python measure_audio.py --dir public/audio/ --fps 30
"""

import argparse
import glob
import json
import math
import os
import sys


def check_dependencies():
    """Verify required packages are installed."""
    try:
        from mutagen.mp3 import MP3  # noqa: F401
    except ImportError:
        print(f"ERROR: mutagen not installed")
        print(f"Install: {sys.executable} -m pip install mutagen")
        sys.exit(1)


def measure_file(filepath, fps=30, expected_ms=None):
    """Measure an MP3 file and return detailed timing information."""
    from mutagen.mp3 import MP3

    audio = MP3(filepath)
    duration_seconds = audio.info.length
    duration_ms = int(duration_seconds * 1000)
    duration_frames = math.ceil(duration_seconds * fps)
    duration_frames_padded = duration_frames + math.ceil(1.0 * fps)  # +1s padding

    result = {
        "file": filepath,
        "file_size_bytes": os.path.getsize(filepath),
        "duration_seconds": round(duration_seconds, 3),
        "duration_ms": duration_ms,
        "duration_frames": duration_frames,
        "duration_frames_with_padding": duration_frames_padded,
        "fps": fps,
        "sample_rate": audio.info.sample_rate,
        "channels": audio.info.channels,
        "bitrate": audio.info.bitrate,
    }

    # Validation against expected duration
    if expected_ms is not None:
        diff_ms = duration_ms - expected_ms
        result["expected_ms"] = expected_ms
        result["difference_ms"] = diff_ms
        result["difference_frames"] = math.ceil(abs(diff_ms) * fps / 1000)

        if abs(diff_ms) <= 50:
            result["status"] = "PASS"
            result["message"] = "Audio duration matches expected timing"
        elif abs(diff_ms) <= 100:
            result["status"] = "WARN"
            result["message"] = f"Minor difference: {diff_ms:+d}ms (acceptable)"
        else:
            result["status"] = "FAIL"
            result["message"] = f"Significant difference: {diff_ms:+d}ms - adjust durationInFrames!"

            if diff_ms > 0:
                result["recommendation"] = (
                    f"Audio is {diff_ms}ms LONGER than expected. "
                    f"Increase durationInFrames by {result['difference_frames']} frames."
                )
            else:
                result["recommendation"] = (
                    f"Audio is {abs(diff_ms)}ms SHORTER than expected. "
                    f"Decrease durationInFrames by {result['difference_frames']} frames, "
                    f"or keep padding for safety."
                )

    return result


def measure_directory(dir_path, fps=30):
    """Measure all MP3 files in a directory."""
    files = sorted(glob.glob(os.path.join(dir_path, "*.mp3")))

    if not files:
        print(f"ERROR: No MP3 files found in {dir_path}")
        sys.exit(1)

    results = []
    total_ms = 0

    for filepath in files:
        result = measure_file(filepath, fps)
        results.append(result)
        total_ms += result["duration_ms"]

    total_frames = math.ceil(total_ms * fps / 1000)
    padding_frames = math.ceil(1.0 * fps)

    summary = {
        "directory": dir_path,
        "file_count": len(results),
        "total_duration_ms": total_ms,
        "total_duration_seconds": round(total_ms / 1000, 3),
        "total_frames": total_frames,
        "total_frames_with_padding": total_frames + padding_frames,
        "fps": fps,
        "files": results,
        "scene_duration_constant": {},
    }

    # Generate SCENE_DURATION constant for TypeScript
    for r in results:
        name = os.path.splitext(os.path.basename(r["file"]))[0]
        # Clean up common prefixes
        name = name.replace("scene_", "").replace("scene", "")
        if name.startswith("0") or name.startswith("1"):
            # Has number prefix like "01_intro" -> "intro"
            parts = name.split("_", 1)
            if len(parts) > 1:
                name = parts[1]
        summary["scene_duration_constant"][name] = r["duration_frames_with_padding"]

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Measure MP3 audio duration and validate against expected timing"
    )
    parser.add_argument("file", nargs="?", help="MP3 file to measure")
    parser.add_argument("--dir", type=str, help="Directory of MP3 files to measure")
    parser.add_argument("--expected-ms", type=int, default=None,
                        help="Expected duration in milliseconds (for validation)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Video FPS for frame calculations (default: 30)")

    args = parser.parse_args()

    check_dependencies()

    if args.dir:
        result = measure_directory(args.dir, args.fps)
        print(json.dumps(result, indent=2))

        # Print summary table to stderr
        print(f"\n{'File':<40} {'Duration':<12} {'Frames':<10} {'Padded':<10}", file=sys.stderr)
        print("-" * 72, file=sys.stderr)
        for f in result["files"]:
            name = os.path.basename(f["file"])
            print(
                f"{name:<40} {f['duration_seconds']:<12.2f}s "
                f"{f['duration_frames']:<10} {f['duration_frames_with_padding']:<10}",
                file=sys.stderr,
            )
        print("-" * 72, file=sys.stderr)
        print(
            f"{'TOTAL':<40} {result['total_duration_seconds']:<12.2f}s "
            f"{result['total_frames']:<10} {result['total_frames_with_padding']:<10}",
            file=sys.stderr,
        )
        print(f"\nSuggested durationInFrames: {result['total_frames_with_padding']}", file=sys.stderr)

    elif args.file:
        if not os.path.exists(args.file):
            print(f"ERROR: File not found: {args.file}")
            sys.exit(1)

        result = measure_file(args.file, args.fps, args.expected_ms)
        print(json.dumps(result, indent=2))

        # Human-readable summary to stderr
        print(f"\nFile: {result['file']}", file=sys.stderr)
        print(f"Duration: {result['duration_seconds']}s ({result['duration_ms']}ms)", file=sys.stderr)
        print(f"Frames: {result['duration_frames']} (with padding: {result['duration_frames_with_padding']})", file=sys.stderr)

        if "status" in result:
            status_icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX"}[result["status"]]
            print(f"Validation: [{status_icon}] {result['message']}", file=sys.stderr)
            if "recommendation" in result:
                print(f"Action: {result['recommendation']}", file=sys.stderr)

    else:
        parser.error("Provide a file path or --dir")


if __name__ == "__main__":
    main()
