#!/usr/bin/env python3
"""
extract_text.py — LaTeX chapter file → narration script.

Strips LaTeX commands, dialog blocks, ornaments, and emits a structured
JSON manifest of sentences with metadata that downstream stages use:

    {
      "title": "The Apparition",
      "kind": "chapter",                # "frame" | "part" | "chapter" | "coda"
      "blocks": [
        {"type": "narration", "text": "The case file arrived ..."},
        {"type": "speaker",   "who":  "MAREN", "text": "Mr. Olen, ..."},
        {"type": "break"},
        ...
      ]
    }

Design notes:
  - "tribunal" environments → speaker blocks (speakers in CAPS)
  - \enquote{...} → curly quotes around inner text
  - \emph{...} / \textit{...} → preserved as inner text (italics handled in
    the render layer)
  - \lettrine{X}{rest} → "X rest" combined for narration
  - \quietbreak → break marker (used by renderer for a pause)
  - Numbers/times kept as-is for the TTS to pronounce
  - Sentences are split on .!? but kept short — long monologues stay whole

Usage:
  ./extract_text.py parts/p1.tex > build/manifests/p1.json
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path


def strip_latex(s: str) -> str:
    """Remove LaTeX markup; replace with narration-friendly text."""
    # Drop meta commands with multiple braced args
    s = re.sub(r"\\addcontentsline\{[^{}]*\}\{[^{}]*\}\{[^{}]*\}", "", s)
    s = re.sub(r"\\markboth\{[^{}]*\}\{[^{}]*\}", "", s)
    s = re.sub(r"\\(?:thispagestyle|pagestyle)\{[^{}]*\}", "", s)
    # \enquote{...} -> curly-quote-wrapped
    s = re.sub(r"\\enquote\*?\{([^{}]*)\}", lambda m: "“" + m.group(1) + "”", s)
    # \emph, \textit, \textsc, \texttt, \textbf -> inner text
    s = re.sub(r"\\(?:emph|textit|textsc|texttt|textbf|itshape)\{([^{}]*)\}", r"\1", s)
    # \lettrine{X}{rest} -> X+rest joined (drop-cap merged)
    s = re.sub(r"\\lettrine\{([^{}]*)\}\{([^{}]*)\}", r"\1\2", s)
    # \color{...}{X} -> X
    s = re.sub(r"\\(?:color|textcolor)\{[^{}]*\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:color|textcolor)\{[^{}]*\}", "", s)
    # \footnote{...} -> drop
    s = re.sub(r"\\footnote\{[^{}]*\}", "", s)
    # Quoted dashes
    s = s.replace("---", "—").replace("--", "–")
    # \hspace, \vspace, \par, \medskip, \bigskip, \smallskip etc.
    s = re.sub(r"\\(?:hspace|vspace|enspace|kern)\*?\{[^{}]*\}", " ", s)
    s = re.sub(
        r"\\(?:par|medskip|bigskip|smallskip|noindent|clearpage|newpage|vfill|hfill|bigskip|quietbreak)\b",
        "",
        s,
    )
    # Remaining single-arg commands
    s = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", s)
    # Bare backslash commands
    s = re.sub(r"\\[a-zA-Z]+\*?\b", "", s)
    # Curly braces left over
    s = s.replace("{", "").replace("}", "")
    # Double-tildes, percent comments
    s = re.sub(r"~", " ", s)
    s = re.sub(r"(?<!\\)%.*", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sentence_split(text: str) -> list[str]:
    """Split paragraph into narration units. Keep dialog whole."""
    # Sentence boundary: . or ! or ? followed by space + capital, em-dash, or quote
    pieces = re.split(r"(?<=[.!?…])\s+(?=[A-Z“—])", text)
    return [p.strip() for p in pieces if p.strip()]


def parse_chapter(tex: str, source_path: str) -> dict:
    """Parse a chapter .tex into a structured manifest."""
    blocks: list[dict] = []
    title = None
    kind = "chapter"

    # Find chapter or chapter* title
    m = re.search(r"\\chapter\*?(?:\[[^\]]*\])?\{([^{}]+)\}", tex)
    if m:
        title = strip_latex(m.group(1))
        # Strip hspace+hanzi suffix some chapters carry
        title = re.sub(r"\s*[一-鿿].*$", "", title).strip()
    if re.search(r"\\chapter\*", tex):
        kind = "frame_or_coda"

    # Detect parts
    pm = re.search(r"\\part\{([^{}]+)\}", tex)
    if pm and not m:
        title = strip_latex(pm.group(1))
        kind = "part"

    # Walk content sequentially
    cursor = 0
    end = len(tex)
    # Skip ahead past the chapter/part declaration
    decl = re.search(r"\\(?:chapter\*?|part)(?:\[[^\]]*\])?\{[^{}]+\}", tex)
    if decl:
        cursor = decl.end()

    # Patterns inside content
    tribunal_re = re.compile(
        r"\\begin\{tribunal\}\{([^{}]+)\}(.*?)\\end\{tribunal\}", re.DOTALL
    )
    quietbreak_re = re.compile(r"\\quietbreak\b")
    blockquote_re = re.compile(r"\\begin\{quote\}(.*?)\\end\{quote\}", re.DOTALL)

    body = tex[cursor:end]
    # Strip commented lines
    body = re.sub(r"(?m)^\s*%.*$", "", body)
    # Strip the trailing \clearpage if present
    body = body.replace("\\clearpage", "")

    # Tokenize: split body into segments separated by environment blocks
    # Find all blocks (tribunal + quote + quietbreak) with positions, sort, walk
    tokens: list[tuple[int, int, str, dict]] = []
    for m2 in tribunal_re.finditer(body):
        tokens.append(
            (
                m2.start(),
                m2.end(),
                "tribunal",
                {"who": m2.group(1).strip(), "text": m2.group(2)},
            )
        )
    for m2 in blockquote_re.finditer(body):
        tokens.append(
            (m2.start(), m2.end(), "blockquote", {"text": m2.group(1)})
        )
    for m2 in quietbreak_re.finditer(body):
        tokens.append((m2.start(), m2.end(), "break", {}))
    tokens.sort(key=lambda t: t[0])

    last = 0
    for start, stop, ttype, data in tokens:
        # Narration before this token
        prose = body[last:start]
        prose_clean = strip_latex(prose)
        for sent in sentence_split(prose_clean):
            if sent:
                blocks.append({"type": "narration", "text": sent})
        if ttype == "tribunal":
            inner = strip_latex(data["text"])
            for sent in sentence_split(inner):
                if sent:
                    blocks.append(
                        {"type": "speaker", "who": data["who"], "text": sent}
                    )
        elif ttype == "blockquote":
            inner = strip_latex(data["text"])
            for sent in sentence_split(inner):
                if sent:
                    blocks.append({"type": "epigraph", "text": sent})
        elif ttype == "break":
            blocks.append({"type": "break"})
        last = stop

    # Tail narration
    tail = strip_latex(body[last:])
    for sent in sentence_split(tail):
        if sent:
            blocks.append({"type": "narration", "text": sent})

    return {
        "source": source_path,
        "title": title or "Untitled",
        "kind": kind,
        "blocks": blocks,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: extract_text.py <tex-file>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    tex = path.read_text(encoding="utf-8")
    manifest = parse_chapter(tex, str(path))
    json.dump(manifest, sys.stdout, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
