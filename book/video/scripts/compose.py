#!/usr/bin/env python3
"""
compose.py — assemble frames + audio into an MP4.

Inputs:
  build/frames/<chapter>/000001.png ...
  build/audio/<chapter>.mp3

Output:
  build/clips/<chapter>.mp4

H.264 yuv420p (web-safe), 30 fps default, AAC audio at 192k.

The compose step is pure ffmpeg orchestration — no PIL, no decoding here.
For full-book assembly, concat the per-chapter MP4s in compose.py --concat mode.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


def ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    print("    $ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)


def compose_chapter(
    chapter: str, *, frames_dir: Path, audio_path: Path,
    out_path: Path, fps: int = 30,
) -> dict:
    frames_pattern = str(frames_dir / "%06d.png")
    ffmpeg([
        "-framerate", str(fps),
        "-i", frames_pattern,
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "20",
        "-preset", "slow",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ])
    return {"chapter": chapter, "out": str(out_path)}


def concat_clips(clip_paths: list[Path], out_path: Path) -> dict:
    """Concat per-chapter MP4s with stream copy (re-encode if codecs differ)."""
    list_path = out_path.with_suffix(".concat.txt")
    list_path.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in clip_paths),
        encoding="utf-8",
    )
    ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ])
    list_path.unlink()
    return {"out": str(out_path), "clips": [str(p) for p in clip_paths]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("chapter")
    p1.add_argument("chapter")
    p1.add_argument("--frames", default="video/build/frames")
    p1.add_argument("--audio", default="video/build/audio")
    p1.add_argument("--out", default="video/build/clips")
    p1.add_argument("--fps", type=int, default=30)

    p2 = sub.add_parser("concat")
    p2.add_argument("--clips", default="video/build/clips")
    p2.add_argument("--out", default="video/build/the_last_corridor.mp4")
    p2.add_argument("chapters", nargs="+", help="chapter names in order")

    args = ap.parse_args(argv[1:])

    if args.cmd == "chapter":
        frames_dir = Path(args.frames) / args.chapter
        audio_path = Path(args.audio) / f"{args.chapter}.mp3"
        out_path = Path(args.out) / f"{args.chapter}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        info = compose_chapter(
            args.chapter, frames_dir=frames_dir, audio_path=audio_path,
            out_path=out_path, fps=args.fps,
        )
        print(json.dumps(info))
    else:
        clips = [Path(args.clips) / f"{c}.mp4" for c in args.chapters]
        for p in clips:
            if not p.exists():
                print(f"missing clip: {p}", file=sys.stderr)
                return 1
        info = concat_clips(clips, Path(args.out))
        print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
