#!/usr/bin/env python3
"""
render.py — kinetic-typography frame renderer.

Reads a word-aligned manifest and renders an image sequence (PNG) where
words appear in sync with the narration. Page-locked layout: the camera
does not move; the text fills the page one word at a time and clears at
section breaks.

Aesthetic:
  - Background:  near-black (#0A0907) with subtle vignette
  - Text:        cream (#F5EBD8), serif
  - Speakers:    speaker name in dim accent, monospace small-caps
  - Title card:  title in italic, centered
  - Break:       three dim diamonds centered, fade in, hold, fade out

Output:
    build/frames/<chapter>/000001.png ...
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


WIDTH = 1920
HEIGHT = 1080
FPS = 30

BG_COLOR = (10, 9, 7)
TEXT_COLOR = (245, 235, 216)
DIM_COLOR = (138, 132, 122)
ACCENT = (179, 95, 78)
SPEAKER_COLOR = (179, 130, 110)

MARGIN_X = 260
MARGIN_TOP = 200
LINE_HEIGHT = 64
BODY_SIZE = 38
TITLE_SIZE = 72
CHAPTER_LABEL_SIZE = 22
SPEAKER_SIZE = 24
ORNAMENT_SIZE = 48

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
FONT_ITALIC_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
FONT_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def first_existing(paths: list[str]) -> str:
    for p in paths:
        if Path(p).exists():
            return p
    raise FileNotFoundError(f"none of {paths}")


def load_fonts():
    reg = first_existing(FONT_CANDIDATES)
    ital = first_existing(FONT_ITALIC_CANDIDATES)
    mono = first_existing(FONT_MONO_CANDIDATES)
    return {
        "body":      ImageFont.truetype(reg, BODY_SIZE),
        "body_ital": ImageFont.truetype(ital, BODY_SIZE),
        "title":     ImageFont.truetype(ital, TITLE_SIZE),
        "label":     ImageFont.truetype(mono, CHAPTER_LABEL_SIZE),
        "speaker":   ImageFont.truetype(mono, SPEAKER_SIZE),
        "ornament":  ImageFont.truetype(reg, ORNAMENT_SIZE),
    }


@dataclass
class LaidWord:
    text: str
    x: int
    y: int
    w: int
    h: int
    t0: float
    t1: float
    block: int
    kind: str
    who: str | None
    is_speaker_tag: bool = False
    italic: bool = False


@dataclass
class PageBreak:
    t_start: float
    t_end: float
    kind: str = "break"


def layout_words(words: list[dict], fonts) -> list[list[LaidWord] | PageBreak]:
    pages: list[list[LaidWord] | PageBreak] = []
    cur: list[LaidWord] = []
    cur_y = MARGIN_TOP
    cur_x = MARGIN_X
    max_x = WIDTH - MARGIN_X
    current_block = None
    current_kind = None
    current_who = None

    space_w = fonts["body"].getbbox(" ")[2]

    def finish_page():
        nonlocal cur, cur_y, cur_x, current_block, current_kind, current_who
        if cur:
            pages.append(cur)
        cur = []
        cur_y = MARGIN_TOP
        cur_x = MARGIN_X
        current_block = None
        current_kind = None
        current_who = None

    i = 0
    while i < len(words):
        w = words[i]
        block = w.get("block")
        kind = w.get("kind") or "narration"
        who = w.get("who")

        if kind == "break":
            finish_page()
            pages.append(PageBreak(t_start=w["t0"], t_end=w["t1"]))
            i += 1
            continue

        if kind == "title":
            title_words = []
            while i < len(words) and words[i].get("kind") == "title":
                title_words.append(words[i])
                i += 1
            text = " ".join(t["w"] for t in title_words)
            tw = fonts["title"].getbbox(text)
            tx = (WIDTH - (tw[2] - tw[0])) // 2
            ty = (HEIGHT - TITLE_SIZE) // 2
            cur.append(LaidWord(
                text=text,
                x=tx, y=ty, w=tw[2]-tw[0], h=TITLE_SIZE,
                t0=title_words[0]["t0"],
                t1=title_words[-1]["t1"],
                block=block or 0, kind="title", who=None, italic=True,
            ))
            finish_page()
            continue

        if kind == "speaker" and (current_who != who or current_kind != "speaker"):
            if current_block is not None and current_kind == "speaker" and current_who != who:
                finish_page()
            elif current_kind not in (None, "speaker"):
                finish_page()
            tag_text = (who or "").upper()
            tw = fonts["speaker"].getbbox(tag_text)
            cur.append(LaidWord(
                text=tag_text,
                x=MARGIN_X, y=cur_y - 48,
                w=tw[2]-tw[0], h=SPEAKER_SIZE,
                t0=max(0.0, w["t0"] - 0.4),
                t1=w["t0"],
                block=block or 0, kind="speaker_tag", who=who,
                is_speaker_tag=True,
            ))
            current_who = who
            current_kind = "speaker"

        if current_block is not None and block != current_block and kind != "speaker":
            if cur_x > MARGIN_X:
                cur_y += LINE_HEIGHT
                cur_x = MARGIN_X
            current_block = block
            current_kind = kind

        if current_block is None:
            current_block = block
            current_kind = kind

        font = fonts["body_ital"] if kind == "speaker" else fonts["body"]
        bbox = font.getbbox(w["w"])
        ww = bbox[2] - bbox[0]
        wh = BODY_SIZE

        if cur_x + ww > max_x:
            cur_x = MARGIN_X
            cur_y += LINE_HEIGHT

        if cur_y + wh > HEIGHT - MARGIN_TOP - 60:
            finish_page()

        cur.append(LaidWord(
            text=w["w"],
            x=cur_x, y=cur_y,
            w=ww, h=wh,
            t0=w["t0"], t1=w["t1"],
            block=block or 0, kind=kind, who=who,
            italic=(kind == "speaker"),
        ))
        cur_x += ww + space_w
        current_block = block
        current_kind = kind
        i += 1

    if cur:
        finish_page()

    return pages


def render_vignette(size: tuple[int, int]) -> Image.Image:
    w, h = size
    g = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(g)
    cx, cy = w / 2, h / 2
    max_r = math.hypot(cx, cy)
    for r in range(0, int(max_r), 4):
        alpha = int(255 * (1.0 - 0.35 * (r / max_r) ** 1.8))
        d.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            outline=alpha, width=4,
        )
    g = g.filter(ImageFilter.GaussianBlur(40))
    return g


def compose_frame(
    t: float,
    page: list[LaidWord],
    fonts,
    *,
    chapter_label: str = "",
    vignette: Image.Image | None = None,
    is_break: bool = False,
    break_t: float = 0.0,
    break_dur: float = 1.6,
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    if vignette is not None:
        dark = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        img = Image.composite(img, dark, vignette)

    d = ImageDraw.Draw(img)

    if chapter_label:
        d.text((MARGIN_X, 80), chapter_label, fill=DIM_COLOR, font=fonts["label"])

    if is_break:
        frac = min(max((t - break_t) / break_dur, 0.0), 1.0)
        if frac < 0.25:
            alpha = frac / 0.25
        elif frac > 0.75:
            alpha = (1.0 - frac) / 0.25
        else:
            alpha = 1.0
        color = tuple(int(c * alpha) for c in ACCENT)
        ornament = "◆     ◆     ◆"
        ob = fonts["ornament"].getbbox(ornament)
        ow = ob[2] - ob[0]
        d.text(((WIDTH - ow) // 2, (HEIGHT - ORNAMENT_SIZE) // 2 - 8),
               ornament, fill=color, font=fonts["ornament"])
        return img

    for lw in page:
        if t < lw.t0:
            continue
        fade_dur = 0.22
        if t < lw.t0 + fade_dur:
            alpha = (t - lw.t0) / fade_dur
            alpha = max(0.0, min(1.0, alpha))
        else:
            alpha = 1.0

        if lw.kind == "title":
            base = TEXT_COLOR
            font = fonts["title"]
        elif lw.is_speaker_tag:
            base = SPEAKER_COLOR
            font = fonts["speaker"]
        elif lw.italic:
            base = TEXT_COLOR
            font = fonts["body_ital"]
        else:
            base = TEXT_COLOR
            font = fonts["body"]

        color = tuple(int(c * alpha + BG_COLOR[i] * (1 - alpha)) for i, c in enumerate(base))
        d.text((lw.x, lw.y), lw.text, fill=color, font=font)

    return img


def render_chapter(
    words_path: Path,
    *,
    out_dir: Path,
    fps: int = FPS,
    verbose: bool = True,
) -> dict:
    data = json.loads(words_path.read_text(encoding="utf-8"))
    duration = data["duration"]
    chapter = data["chapter"]
    title = data["title"]
    words = data["words"]

    fonts = load_fonts()
    pages = layout_words(words, fonts)
    vignette = render_vignette((WIDTH, HEIGHT))

    page_spans: list[tuple[float, float, list[LaidWord] | PageBreak]] = []
    for page in pages:
        if isinstance(page, PageBreak):
            page_spans.append((page.t_start, page.t_end, page))
        else:
            t_start = min(w.t0 for w in page)
            t_end = max(w.t1 for w in page) + 1.6
            page_spans.append((t_start, t_end, page))

    if page_spans:
        last_start, _, last_payload = page_spans[-1]
        page_spans[-1] = (last_start, duration, last_payload)

    starts = [s[0] for s in page_spans]

    frames_dir = out_dir / chapter
    frames_dir.mkdir(parents=True, exist_ok=True)

    total_frames = math.ceil(duration * fps)
    if verbose:
        print(f"  [render] {chapter}: {len(pages)} pages, "
              f"{total_frames} frames @ {fps}fps", file=sys.stderr)

    chapter_label = f"{title}".upper()

    for f in range(total_frames):
        t = f / fps
        out_path = frames_dir / f"{f:06d}.png"
        if out_path.exists():
            continue
        idx = bisect.bisect_right(starts, t) - 1
        if idx < 0:
            idx = 0
        while idx < len(page_spans) - 1 and t >= page_spans[idx][1]:
            idx += 1
        s, e, payload = page_spans[idx]

        if isinstance(payload, PageBreak):
            img = compose_frame(
                t, [], fonts, chapter_label=chapter_label, vignette=vignette,
                is_break=True, break_t=payload.t_start,
                break_dur=max(0.4, payload.t_end - payload.t_start),
            )
        else:
            img = compose_frame(
                t, payload, fonts, chapter_label=chapter_label, vignette=vignette,
            )
        img.save(out_path, "PNG")

        if verbose and f % (fps * 5) == 0:
            print(f"    frame {f:06d}/{total_frames} @ t={t:6.2f}s",
                  file=sys.stderr)

    if verbose:
        print(f"  [render] {chapter}: complete → {frames_dir}", file=sys.stderr)
    return {"chapter": chapter, "frames": total_frames, "fps": fps}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("words", help="*.words.json from align.py")
    ap.add_argument("--out", default="video/build/frames")
    ap.add_argument("--fps", type=int, default=FPS)
    args = ap.parse_args(argv[1:])

    info = render_chapter(Path(args.words), out_dir=Path(args.out), fps=args.fps)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
