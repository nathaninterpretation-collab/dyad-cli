#!/usr/bin/env python3
"""
tts.py — generate narration audio per chapter from manifest JSON.

Per-chapter pipeline:
  1. Read manifest (chapter JSON)
  2. For each block, emit a TTS clip with the appropriate voice
     - narration  -> NARRATOR_VOICE (default: ash)
     - speaker    -> per-speaker voice mapping
     - break      -> 1.6s silence
     - epigraph   -> NARRATOR_VOICE, italic instruction
  3. Concat clips with silence pauses, write per-block durations to a
     timing manifest used by the alignment + render stages

Outputs:
  build/audio/<chapter>.mp3         full chapter audio
  build/audio/<chapter>.timing.json [(block_index, t_start, t_end)]
  build/audio/<chapter>/<block_n>.mp3   per-block fragments (for debug)

Uses OpenAI's `gpt-4o-mini-tts` for highest narration quality. Falls back
to `tts-1-hd` if the newer model is unavailable.

Voices (gpt-4o-mini-tts catalogue):
  ash, ballad, coral, sage, verse — most expressive
  alloy, echo, onyx — classic
  nova, shimmer, fable — bright

Style direction is passed via the `instructions` parameter on gpt-4o-mini-tts.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from openai import OpenAI

# ---------------------------------------------------------------------------
# Voice casting
# ---------------------------------------------------------------------------

NARRATOR_VOICE = "ash"           # principal narrator (the frame and prose)
NARRATOR_STYLE = (
    "Speak slowly. Weight the silences. Read like a man recounting "
    "something he has told many times, in flat measured cadence, without "
    "residue. No theatrical inflection. Pause between sentences for "
    "half a beat."
)

# Tribunal speakers and key voices
SPEAKER_VOICES = {
    "OLEN":   ("ash",     "Deliberate. Each sentence a placement. A man making "
                          "an argument that he has thought through for years. "
                          "Pause after key terms."),
    "MAREN":  ("sage",    "Measured, judicial, institutional warmth. The voice "
                          "of a presiding officer who genuinely believes the "
                          "framework she is enforcing is kind."),
    "DAVAN":  ("verse",   "Precise. Slightly clipped. A logician's voice."),
    "KAEL":   ("ballad",  "Analytical. Cool. Female-coded, mid-range."),
    "PREN":   ("coral",   "Younger, brisker, technical."),
    "LIEN":   ("alloy",   "Procedural. Operational. Slightly skeptical."),
    "SERA":   ("nova",    "Composed. Physicalist precision. Never rises. A "
                          "woman whose register does not change across decades."),
    "VOSS":   ("shimmer", "Artistic, layered, slightly dreamy."),
    "LIRENI": ("echo",    "Sharp, political, decisive."),
    "TOMEK":  ("onyx",    "Quiet, weary, distant. A man who has been alone "
                          "for 240 years."),
    "K-4471": ("fable",   "System Kepler citizen — uniform, integrated, even."),
    "A-9003": ("fable",   "System Arcturus citizen — uniform, broadcasting."),
}

EPIGRAPH_VOICE = "ballad"
EPIGRAPH_STYLE = "Read as if quoting an institutional document — flat, italic, dry."

BREAK_SECONDS = 1.6              # silence between section breaks
INTER_BLOCK_SILENCE = 0.40       # silence between any two blocks
SPEAKER_TAG_SILENCE = 0.55       # extra silence before a dialog block

# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------

def get_client() -> OpenAI | None:
    """Return an OpenAI client, or None if the API is unreachable."""
    if os.environ.get("TTS_BACKEND") == "espeak":
        return None
    key = (
        os.environ.get("OPENAI_API_KEY")
        or (Path("~/.openai_key").expanduser().read_text().strip()
            if Path("~/.openai_key").expanduser().exists() else "")
    )
    if not key:
        return None
    return OpenAI(api_key=key)


# Per-OpenAI-voice espeak-ng fallback mapping. The variants are the closest
# espeak-ng equivalents (gender + pitch). Quality is much lower; the user
# should run the pipeline against the OpenAI API for production.
ESPEAK_VOICES = {
    "ash":     ("en-us+m4", 155, 50),   # measured male
    "onyx":    ("en-us+m1", 145, 45),   # deep male
    "sage":    ("en-gb+f3", 160, 50),   # judicial female
    "verse":   ("en-us+m5", 175, 55),   # precise male
    "ballad":  ("en-gb+f2", 170, 55),   # analytical female
    "coral":   ("en-us+f4", 180, 60),   # brisk female
    "alloy":   ("en-us+m2", 165, 50),   # procedural male
    "nova":    ("en-us+f2", 165, 55),   # composed female
    "shimmer": ("en-us+f1", 170, 60),   # dreamy female
    "echo":    ("en-us+m3", 170, 55),   # sharp male
    "fable":   ("en-us+f5", 160, 50),   # even neutral
}


def synth_espeak(text: str, voice: str, out_path: Path) -> None:
    """Local-quality fallback synthesis via espeak-ng."""
    espeak_voice, rate, pitch = ESPEAK_VOICES.get(voice, ("en-us+m4", 160, 50))
    wav_path = out_path.with_suffix(".wav")
    subprocess.run(
        ["espeak-ng", "-v", espeak_voice, "-s", str(rate), "-p", str(pitch),
         "-w", str(wav_path), text],
        check=True,
    )
    # Convert WAV to mp3 for consistent downstream handling
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
         "-codec:a", "libmp3lame", "-qscale:a", "2", str(out_path)],
        check=True,
    )
    wav_path.unlink()


def synth_to_file(
    client: OpenAI | None, *, text: str, voice: str, style: str | None,
    out_path: Path, model: str = "gpt-4o-mini-tts",
) -> None:
    """Synthesise `text` with `voice` and write mp3 to `out_path`."""
    if client is None:
        synth_espeak(text, voice, out_path)
        return
    kwargs: dict = {"model": model, "voice": voice, "input": text, "response_format": "mp3"}
    if style and model == "gpt-4o-mini-tts":
        kwargs["instructions"] = style
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with client.audio.speech.with_streaming_response.create(**kwargs) as response:
            with open(out_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    except Exception as e:
        # Network or permission failure → fall back so the pipeline keeps moving.
        msg = str(e)[:160]
        print(f"  [tts] OpenAI unavailable ({msg!r}); using espeak-ng fallback",
              file=sys.stderr)
        synth_espeak(text, voice, out_path)


def ffprobe_duration(path: Path) -> float:
    """Return audio duration in seconds (uses ffprobe)."""
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def silence_clip(seconds: float, out_path: Path) -> None:
    """Generate `seconds` of silence as mp3 via ffmpeg."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
         "-t", f"{seconds:.3f}", "-q:a", "9", "-acodec", "libmp3lame",
         str(out_path)],
        check=True,
    )


def concat_clips(paths: list[Path], out_path: Path) -> None:
    """Concatenate mp3 clips losslessly with ffmpeg concat demuxer."""
    list_path = out_path.with_suffix(".concat.txt")
    list_path.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in paths), encoding="utf-8"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(list_path),
         "-c", "copy", str(out_path)],
        check=True,
    )
    list_path.unlink()


# ---------------------------------------------------------------------------
# Block → voice resolution
# ---------------------------------------------------------------------------

def voice_for_block(block: dict) -> tuple[str, str | None]:
    if block["type"] == "narration":
        return NARRATOR_VOICE, NARRATOR_STYLE
    if block["type"] == "epigraph":
        return EPIGRAPH_VOICE, EPIGRAPH_STYLE
    if block["type"] == "speaker":
        who = block.get("who", "").upper()
        if who in SPEAKER_VOICES:
            return SPEAKER_VOICES[who]
        return ("alloy", None)
    return NARRATOR_VOICE, NARRATOR_STYLE


# ---------------------------------------------------------------------------
# Chapter builder
# ---------------------------------------------------------------------------

def build_chapter(
    manifest_path: Path, *, out_dir: Path, model: str = "gpt-4o-mini-tts",
    verbose: bool = True,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chap_name = manifest_path.stem
    audio_dir = out_dir / chap_name
    audio_dir.mkdir(parents=True, exist_ok=True)

    client = get_client()

    # Title card: synth chapter title with title-card pause
    title_text = manifest["title"]
    title_path = audio_dir / "00_title.mp3"
    if not title_path.exists():
        if verbose:
            print(f"  [tts] title — {title_text!r}", file=sys.stderr)
        synth_to_file(
            client,
            text=title_text + ".",
            voice=NARRATOR_VOICE,
            style="Read slowly, as a title card — single phrase, then a long pause.",
            out_path=title_path,
            model=model,
        )

    title_silence = audio_dir / "00_title_pause.mp3"
    silence_clip(1.4, title_silence)

    clip_paths: list[Path] = [title_path, title_silence]
    timings: list[dict] = [
        {"index": -1, "type": "title", "text": title_text},
    ]

    prev_was_speaker = False
    for i, block in enumerate(manifest["blocks"]):
        btype = block["type"]
        if btype == "break":
            sil = audio_dir / f"{i:03d}_break.mp3"
            silence_clip(BREAK_SECONDS, sil)
            clip_paths.append(sil)
            timings.append({"index": i, "type": "break"})
            prev_was_speaker = False
            continue

        voice, style = voice_for_block(block)
        text = block["text"]

        # Insert a small extra silence before/after dialog
        if btype == "speaker" and not prev_was_speaker:
            sil = audio_dir / f"{i:03d}_pre.mp3"
            silence_clip(SPEAKER_TAG_SILENCE, sil)
            clip_paths.append(sil)

        clip_path = audio_dir / f"{i:03d}.mp3"
        if not clip_path.exists():
            if verbose:
                snip = text[:60] + ("…" if len(text) > 60 else "")
                print(f"  [tts] {i:03d} {voice:8s} {btype:9s} — {snip!r}", file=sys.stderr)
            try:
                synth_to_file(
                    client, text=text, voice=voice, style=style,
                    out_path=clip_path, model=model,
                )
            except Exception as e:
                # On model failure fall back to tts-1-hd
                print(f"  [tts] fallback to tts-1-hd for block {i}: {e}", file=sys.stderr)
                synth_to_file(
                    client, text=text, voice=voice, style=None,
                    out_path=clip_path, model="tts-1-hd",
                )
        clip_paths.append(clip_path)

        # Inter-block silence
        sil = audio_dir / f"{i:03d}_post.mp3"
        silence_clip(INTER_BLOCK_SILENCE, sil)
        clip_paths.append(sil)

        timings.append({"index": i, "type": btype, "text": text,
                        "voice": voice})
        prev_was_speaker = (btype == "speaker")

    # Concatenate
    chapter_mp3 = out_dir / f"{chap_name}.mp3"
    concat_clips(clip_paths, chapter_mp3)

    # Annotate timings with absolute offsets by probing each clip
    cursor = 0.0
    enriched: list[dict] = []
    for p, t in zip(clip_paths, [{"index": -2, "type": "title_card"}] + timings + [{}]):
        pass  # placeholder; we'll measure below

    # Re-measure: walk clip_paths in order, accumulate, tag entries
    cursor = 0.0
    ti = 0
    timing_out: list[dict] = []
    # entries in `timings` correspond to "content" clips; silence clips are between
    for p in clip_paths:
        d = ffprobe_duration(p)
        name = p.name
        if "_pre" in name or "_post" in name or "_break" in name or "_pause" in name:
            cursor += d
            continue
        if name == "00_title.mp3":
            timing_out.append({
                "kind": "title",
                "text": title_text,
                "t_start": cursor,
                "t_end": cursor + d,
            })
        else:
            t = timings[ti + 1] if ti + 1 < len(timings) else {}
            timing_out.append({
                "kind": t.get("type", "narration"),
                "who": t.get("who"),
                "voice": t.get("voice", NARRATOR_VOICE),
                "text": t.get("text", ""),
                "t_start": cursor,
                "t_end": cursor + d,
            })
            ti += 1
        cursor += d

    timing_path = out_dir / f"{chap_name}.timing.json"
    timing_path.write_text(
        json.dumps({
            "chapter": chap_name,
            "title": title_text,
            "duration": cursor,
            "model": model,
            "blocks": timing_out,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if verbose:
        print(f"  [tts] {chap_name}: {cursor:.1f}s total, "
              f"{len(timing_out)} blocks → {chapter_mp3}", file=sys.stderr)

    return {"audio": str(chapter_mp3), "timing": str(timing_path), "duration": cursor}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="path to chapter manifest JSON")
    ap.add_argument("--out", default="video/build/audio", help="output directory")
    ap.add_argument("--model", default="gpt-4o-mini-tts",
                    help="OpenAI TTS model (gpt-4o-mini-tts | tts-1-hd | tts-1)")
    args = ap.parse_args(argv[1:])

    out_dir = Path(args.out)
    result = build_chapter(Path(args.manifest), out_dir=out_dir, model=args.model)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
