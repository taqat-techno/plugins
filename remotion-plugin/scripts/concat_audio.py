"""
Remotion Plugin - Audio Concatenation

Merges multiple MP3 files into a single continuous audio track.
This is the KEY script that solves audio cutting between slides.

Instead of per-slide audio (which cuts at Sequence boundaries),
this creates ONE continuous narration file used at the root level.

Usage:
    python concat_audio.py --files scene01.mp3 scene02.mp3 scene03.mp3 --output narration.mp3
    python concat_audio.py --files scene01.mp3 scene02.mp3 --output narration.mp3 --gap 300
    python concat_audio.py --dir public/audio/scenes/ --output public/audio/narration.mp3
    python concat_audio.py --files scene01.mp3 scene02.mp3 --output narration.mp3 --fps 30

Output:
    - Concatenated MP3 file
    - JSON with segment timestamps for Sequence timing (printed to stdout)
"""

import argparse
import glob
import json
import math
import os
import sys

# Allow importing _common from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import check_dependencies, get_audio_duration_ms


def concat_with_pydub(files, output_path, gap_ms=0):
    """Concatenate MP3 files using pydub (preferred method)."""
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=gap_ms) if gap_ms > 0 else None
    segments = []
    current_ms = 0

    for i, filepath in enumerate(files):
        audio = AudioSegment.from_mp3(filepath)
        duration_ms = len(audio)

        # Add gap before this segment (except for the first)
        if i > 0 and silence:
            combined += silence
            current_ms += gap_ms

        segment_info = {
            "file": os.path.basename(filepath),
            "index": i,
            "start_ms": current_ms,
            "end_ms": current_ms + duration_ms,
            "duration_ms": duration_ms,
        }
        segments.append(segment_info)

        combined += audio
        current_ms += duration_ms

    # Export
    combined.export(output_path, format="mp3", bitrate="192k")
    return segments, current_ms


def _ffconcat_line(path):
    """One line of an ffmpeg concat-demuxer list. A ' in the path is written as '\\''."""
    path = os.path.abspath(path).replace(chr(92), "/")
    return "file '" + path.replace("'", "'" + chr(92) + "''") + "'\n"


def _audio_format(filepath):
    """(sample_rate, channels) of an MP3, with edge-tts defaults if unreadable."""
    try:
        from mutagen.mp3 import MP3
        info = MP3(filepath).info
        return int(info.sample_rate) or 24000, int(info.channels) or 1
    except Exception:
        return 24000, 1


def concat_with_ffmpeg(files, output_path, gap_ms=0, runner=None):
    """Concatenate MP3 files using the ffmpeg CLI (fallback method).

    The output is RE-ENCODED (libmp3lame), never stream-copied: edge-tts writes
    24 kHz mono MP3 and a stream copy of inputs whose sample rate or channel
    layout differ (including the generated silence) yields a malformed stream
    whose duration no longer matches the segment timestamps. Silence is generated
    at the first input's sample rate and channel layout, and every ffmpeg return
    code is checked.
    """
    import subprocess
    import tempfile

    run = runner or subprocess.run
    segments = []
    current_ms = 0

    # Measure each file first
    for i, filepath in enumerate(files):
        duration_ms = get_audio_duration_ms(filepath)

        if i > 0 and gap_ms > 0:
            current_ms += gap_ms

        segments.append({
            "file": os.path.basename(filepath),
            "index": i,
            "start_ms": current_ms,
            "end_ms": current_ms + duration_ms,
            "duration_ms": duration_ms,
        })
        current_ms += duration_ms

    rate, channels = _audio_format(files[0])
    layout = "mono" if channels == 1 else "stereo"

    with tempfile.TemporaryDirectory(prefix="remotion-concat-") as work:
        silence_path = None
        if gap_ms > 0 and len(files) > 1:
            silence_path = os.path.join(work, "silence.mp3")
            made = run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", "anullsrc=r={0}:cl={1}".format(rate, layout),
                 "-t", str(gap_ms / 1000), "-c:a", "libmp3lame", "-q:a", "9",
                 silence_path],
                capture_output=True, text=True,
            )
            if made.returncode != 0:
                print("ERROR: ffmpeg could not generate silence: {0}".format(made.stderr),
                      file=sys.stderr)
                sys.exit(1)

        concat_list_path = os.path.join(work, "list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for i, filepath in enumerate(files):
                f.write(_ffconcat_line(filepath))
                if silence_path and i < len(files) - 1:
                    f.write(_ffconcat_line(silence_path))

        result = run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
             "-ar", str(rate), "-ac", str(channels),
             "-c:a", "libmp3lame", "-b:a", "192k", output_path],
            capture_output=True, text=True,
        )

    if result.returncode != 0:
        print(f"ERROR: ffmpeg failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    return segments, current_ms


def concat_simple(files, output_path, gap_ms=0):
    """Byte-level concatenation (last resort). It cannot insert gaps.

    The timestamps therefore never include a gap: reporting gap_ms that is not in
    the audio would shift scene N's visuals by gap_ms*(N-1) from the narration.
    The caller reports gap_ms as 0 for this method.
    """
    segments = []
    current_ms = 0

    with open(output_path, "wb") as out_f:
        for i, filepath in enumerate(files):
            duration_ms = get_audio_duration_ms(filepath)
            segments.append({
                "file": os.path.basename(filepath),
                "index": i,
                "start_ms": current_ms,
                "end_ms": current_ms + duration_ms,
                "duration_ms": duration_ms,
            })
            current_ms += duration_ms

            with open(filepath, "rb") as in_f:
                out_f.write(in_f.read())

    if gap_ms > 0:
        print("WARNING: simple mode cannot insert gaps; segments are back to back "
              "(gap_ms reported as 0). Install pydub or ffmpeg for gaps.", file=sys.stderr)

    return segments, current_ms


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate MP3 files into a single continuous audio track"
    )
    parser.add_argument("--files", nargs="+", help="MP3 files to concatenate (in order)")
    parser.add_argument("--dir", type=str, help="Directory of MP3 files (sorted alphabetically)")
    parser.add_argument("--output", type=str, required=True, help="Output MP3 file path")
    parser.add_argument("--gap", type=int, default=200,
                        help="Gap duration in ms between segments (default: 200)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Video FPS for frame calculations (default: 30)")
    parser.add_argument("--method", choices=["pydub", "ffmpeg", "simple", "auto"],
                        default="auto", help="Concatenation method (default: auto)")

    args = parser.parse_args()

    check_dependencies("concat")

    # Gather files
    if args.files:
        files = args.files
    elif args.dir:
        files = sorted(glob.glob(os.path.join(args.dir, "*.mp3")))
    else:
        parser.error("Provide --files or --dir")

    if args.gap < 0:
        parser.error("--gap must be >= 0")

    # Validate files exist
    for f in files:
        if not os.path.exists(f):
            print(f"ERROR: File not found: {f}")
            sys.exit(1)

    if not files:
        print("ERROR: No MP3 files found")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Select concatenation method
    method = args.method
    if method == "auto":
        try:
            from pydub import AudioSegment  # noqa: F401
            method = "pydub"
        except ImportError:
            import shutil
            if shutil.which("ffmpeg"):
                method = "ffmpeg"
            else:
                method = "simple"

    print(f"Method: {method} | Files: {len(files)} | Gap: {args.gap}ms | FPS: {args.fps}", file=sys.stderr)

    # Concatenate
    applied_gap = args.gap
    if method == "pydub":
        segments, total_ms = concat_with_pydub(files, args.output, args.gap)
    elif method == "ffmpeg":
        segments, total_ms = concat_with_ffmpeg(files, args.output, args.gap)
    else:
        segments, total_ms = concat_simple(files, args.output, args.gap)
        applied_gap = 0

    # Verify output
    actual_ms = get_audio_duration_ms(args.output)
    total_frames = math.ceil(actual_ms * args.fps / 1000)
    padding_frames = math.ceil(1.0 * args.fps)  # 1 second padding

    # Add frame calculations to segments
    for seg in segments:
        seg["start_frame"] = math.ceil(seg["start_ms"] * args.fps / 1000)
        seg["end_frame"] = math.ceil(seg["end_ms"] * args.fps / 1000)
        seg["duration_frames"] = seg["end_frame"] - seg["start_frame"]

    # Build result JSON
    result = {
        "output_file": args.output,
        "method": method,
        "total_duration_ms": actual_ms,
        "total_duration_seconds": round(actual_ms / 1000, 3),
        "total_frames": total_frames,
        "total_frames_with_padding": total_frames + padding_frames,
        "fps": args.fps,
        "gap_ms": applied_gap,
        "segment_count": len(segments),
        "segments": segments,
    }

    print(json.dumps(result, indent=2))

    # Summary to stderr
    print(f"\nOutput: {args.output}", file=sys.stderr)
    print(f"Duration: {actual_ms / 1000:.2f}s ({total_frames} frames at {args.fps}fps)", file=sys.stderr)
    print(f"Composition durationInFrames: {total_frames + padding_frames} (with 1s padding)", file=sys.stderr)


if __name__ == "__main__":
    main()
