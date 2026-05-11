#!/usr/bin/env python3
"""
align.py — produce word-level timing manifests from block-level TTS timings.

Strategy: linear distribution per block. The TTS step already produced
precise t_start/t_end for each block (narration, speaker, epigraph, title).
For kinetic typography we split each block's text into words and assign
timestamps proportional to word length (so longer words consume more time).

Output:
    build/audio/<chapter>.words.json
        {
          "chapter": "frame",
          "duration": 123.12,
          "words": [
            {"w": "He", "t0": 2.61, "t1": 2.74, "block": 0, "kind": "narration"},
            ...
          ]
        }

This is "linear forced alignment" — accuracy is ±100 ms which is fine for
the kinetic-typography reveal. For frame-perfect alignment, swap in
faster-whisper word-level timestamps; the manifest schema is the same.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


WORD_RE = re.compile(r"\S+")


def split_words(text: str) -> list[str]:
    """Tokenise to display words (keeps punctuation attached)."""
    return WORD_RE.findall(text)


def weight(word: str) -> float:
    """Crude pronunciation-time weight ∝ syllable count.

    Heuristic: char count minus vowel pairs, clamped to ≥ 1.
    Punctuation-only tokens get tiny weight.
    """
    if not any(c.isalnum() for c in word):
        return 0.2
    # rough syllable estimate
    w = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not w:
        return 0.5
    syll = max(1, len(re.findall(r"[aeiouy]+", w)))
    # heavier weight for words ending in . ! ?  (sentence-final pause)
    pause_bonus = 1.5 if word[-1:] in ".!?" else 1.0
    return syll * pause_bonus


def align_block(block: dict, words_acc: list[dict]) -> None:
    """Distribute words across [t_start, t_end] proportional to weight."""
    text = block.get("text", "")
    t0 = block["t_start"]
    t1 = block["t_end"]
    span = max(0.0001, t1 - t0)

    words = split_words(text)
    if not words:
        return

    weights = [weight(w) for w in words]
    total = sum(weights) or 1.0
    cursor = t0
    for w, wt in zip(words, weights):
        dt = span * (wt / total)
        words_acc.append({
            "w": w,
            "t0": round(cursor, 4),
            "t1": round(cursor + dt, 4),
            "block": block.get("index"),
            "kind": block.get("kind"),
            "who": block.get("who"),
        })
        cursor += dt


def align_chapter(timing_path: Path, *, out_path: Path) -> dict:
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    words: list[dict] = []
    for i, blk in enumerate(timing["blocks"]):
        blk = dict(blk)
        blk["index"] = i
        align_block(blk, words)

    result = {
        "chapter": timing["chapter"],
        "title": timing["title"],
        "duration": timing["duration"],
        "model": timing.get("model"),
        "blocks": timing["blocks"],
        "words": words,
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("timing", help="*.timing.json from tts.py")
    ap.add_argument("--out", help="output .words.json", default=None)
    args = ap.parse_args(argv[1:])

    tp = Path(args.timing)
    if args.out:
        op = Path(args.out)
    else:
        op = tp.with_name(tp.name.replace(".timing.json", ".words.json"))

    result = align_chapter(tp, out_path=op)
    print(f"  [align] {result['chapter']}: {len(result['words'])} words "
          f"across {result['duration']:.1f}s → {op}", file=sys.stderr)
    print(str(op))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
