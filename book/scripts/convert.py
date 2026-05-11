#!/usr/bin/env python3
"""Convert The Last Corridor source text (pdftotext -layout output) to LaTeX.

Indent fingerprints in the source:
  Body paragraphs:   first line indent=4, continuation=0
  Tribunal blocks:   first line indent=7 (NAME:), continuation=3
  Reflection stanzas: every line indent=5 (italic in original)
  Lattice-Olen logs:  every line indent=3 (Book 2, italic in original)
  Scene breaks:      "·  ·  ·"  or  "◊ ◊ ◊"  (centered, indent ~47)
"""
import re
import pathlib

CHAPTER_HDR_RE = re.compile(r"^CHAPTER\s+([A-Z]+)\s*$")
PAGE_NUMBER_RE = re.compile(r"^\s+\d+\s*$|^\d+\s*$")
DOT_BREAK_RE = re.compile(r"^\s*[·]\s+[·]\s+[·]\s*$")
DIAMOND_BREAK_RE = re.compile(r"^\s*[◊]\s+[◊]\s+[◊]\s*$")
NAME_LINE_RE = re.compile(r"^([A-Z][A-Z]+):\s*(.*)$")

CHAPTER_TITLES_BOOK1 = {
    1: "The Museum of Doors",
    2: "The Gallery",
    3: "The Cogito and the Bat",
    4: "The Chinese Room and the Mill",
    5: "The Three Worlds",
    6: "The Occam Strike",
    7: "The Strings",
    8: "The Reprieve",
    9: "Three Weeks After",
    10: "The Thirty Years",
    11: "The Cancer and the Confession",
    12: "The Upload",
}
CHAPTER_TITLES_BOOK2 = {
    1: "The Reconstruction",
    2: "Is Something Suboptimal?",
    3: "The Conjecture",
    4: "The Initiative",
    5: "The Affected",
    6: "The Colosseum",
    7: "The Warrants",
    8: "The Scattering",
    9: "The Asymmetric Persistence",
}
ROMAN_TO_INT = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6,
    "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12,
}


def latex_escape(s: str) -> str:
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("$", r"\$")
    s = s.replace("#", r"\#")
    s = s.replace("_", r"\_")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    return s


def convert_quotes(text: str) -> str:
    """Turn ASCII " into \\enquote{}, single ' that bracket phrases into \\enquote*{}.

    We do single-quote conversion first within already-quoted spans, then convert
    the doubles. Both passes assume strict alternation."""
    # Pass 1: nested singles. A nested single span is 'X' where the opening '
    # follows whitespace or a quote-opener and X contains at least one space and
    # the closing ' is followed by punctuation/space/quote-closer.
    def repl_singles(m):
        return r"\enquote*{" + m.group(1) + "}"
    text = re.sub(
        r"(?<=[\s\"\(\{])'([^'\n]{2,250}?)'(?=[\s\.,;:?!\"\)\}])",
        repl_singles, text)

    # Pass 2: doubles. Strict alternation.
    out = []
    open_quote = False
    for ch in text:
        if ch == '"':
            if not open_quote:
                out.append(r"\enquote{")
                open_quote = True
            else:
                out.append("}")
                open_quote = False
        else:
            out.append(ch)
    if open_quote:
        out.append("}")
    return "".join(out)


def emphasize_caps_words(text: str) -> str:
    """The source uses bare ALL-CAPS short words for emphasis ('IS', 'ARE', 'AM',
    'BE', 'DO', 'DOES', 'WAS', 'I', 'NOT'). Render them as \\textsc{}.

    We only convert when surrounded by whitespace/punct (not part of an acronym)."""
    targets = ["IS", "ARE", "AM", "BE", "DO", "DOES", "WAS", "NOT"]
    for t in targets:
        text = re.sub(
            r"(?<![A-Za-z\\])" + t + r"(?=[ ,.;:?!\)\}\]\-])",
            r"\\textsc{" + t.lower() + r"}",
            text,
        )
    return text


def normalize_lines(raw: str):
    """Strip pdftotext page-number ghosts and form-feed characters that pdftotext
    inserts at page boundaries. Returns lines preserving leading whitespace so
    we can read indents."""
    cleaned = []
    for ln in raw.splitlines():
        # pdftotext sometimes prefixes the first line of a new page with \x0c.
        ln = ln.lstrip("\x0c")
        ln = ln.rstrip()
        if PAGE_NUMBER_RE.match(ln):
            continue
        cleaned.append(ln)
    return cleaned


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def find_chapters(lines, titles_map):
    starts = []
    for i, ln in enumerate(lines):
        m = CHAPTER_HDR_RE.match(ln.strip())
        if m and m.group(1) in ROMAN_TO_INT:
            n = ROMAN_TO_INT[m.group(1)]
            if n in titles_map:
                starts.append((i, n))
    chapters = []
    for idx, (start, n) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = lines[start + 1: end]
        title_idx = next((i for i, ln in enumerate(body) if ln.strip()), None)
        if title_idx is not None:
            body = body[title_idx + 1:]
        chapters.append((n, titles_map[n], body))
    return chapters


def parse_chapter_blocks(lines):
    """Walk chapter lines, classify each contiguous run into a typed block.

    Returns list of (kind, payload_lines) where kind is one of:
      'body', 'tribunal', 'reflection', 'latticelog', 'break'

    Handles page-break-fragmented paragraphs by detecting that a continuation
    paragraph (first-line indent=0 and previous block was body) should be
    merged into the previous block.
    """
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        ind = indent_of(ln)
        text = ln.strip()
        # scene break (centered "·  ·  ·" or "◊ ◊ ◊")
        if DOT_BREAK_RE.match(ln) or DIAMOND_BREAK_RE.match(ln):
            blocks.append(("break", []))
            i += 1
            continue
        # tribunal: NAME: at indent 7 (we accept >=6 for safety)
        if ind >= 6 and NAME_LINE_RE.match(text):
            collected = [ln[ind:]]
            i += 1
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    break
                nind = indent_of(nxt)
                # tribunal continuation lines indent=3
                if nind in (3, 4) and not NAME_LINE_RE.match(nxt.strip()):
                    collected.append(nxt[nind:])
                    i += 1
                else:
                    break
            blocks.append(("tribunal", collected))
            continue
        # reflection: italic stanzas. Indent is 5, 6, or 7 in the source PDF;
        # all lines share the same indent. (Indent 7 is tribunal only when the
        # first line matches NAME:, which we already filtered above.)
        if ind in (5, 6, 7):
            collected = [ln[ind:]]
            i += 1
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    break
                if indent_of(nxt) == ind:
                    collected.append(nxt[ind:])
                    i += 1
                else:
                    break
            blocks.append(("reflection", collected))
            continue
        # latticelog: every line indent=3 (Book 2 italic logs).
        # Disambiguate from body-with-indent=3: if the second line is also
        # indent=3 the paragraph is a latticelog; otherwise it's a body
        # paragraph that just happened to open at indent=3.
        if ind == 3:
            second_is_indent3 = (
                i + 1 < n and lines[i + 1].strip() and indent_of(lines[i + 1]) == 3
            )
            single_line = (
                i + 1 >= n or not lines[i + 1].strip()
            )
            if second_is_indent3 or single_line:
                collected = [ln[3:]]
                i += 1
                while i < n:
                    nxt = lines[i]
                    if not nxt.strip():
                        break
                    if indent_of(nxt) == 3:
                        collected.append(nxt[3:])
                        i += 1
                    else:
                        break
                blocks.append(("latticelog", collected))
                continue
            # Otherwise fall through to body
        # body: first-line indent in {0, 3, 4} ; continuation indent=0
        # If indent==0 and previous block is 'body', this is a page-break-
        # fragmented continuation: merge into the previous block.
        collected = [text]
        i += 1
        while i < n:
            nxt = lines[i]
            if not nxt.strip():
                break
            if indent_of(nxt) == 0:
                collected.append(nxt.strip())
                i += 1
            else:
                break
        # Merge with previous body block if THIS block opened at indent=0
        # AND the previous block was a body paragraph that ended without a
        # sentence-ending punctuation (page-break fragmentation case).
        if ind == 0 and blocks and blocks[-1][0] == "body":
            prev = blocks[-1][1]
            blocks[-1] = ("body", prev + collected)
        else:
            blocks.append(("body", collected))
    return blocks


def render_block(kind, payload, *, first_body=False, drop_letter=False):
    text = " ".join(payload).strip()
    text = re.sub(r"\s+", " ", text)
    # Re-flatten "sacred- body" → "sacred-body" (pdftotext hyphen artifact)
    text = re.sub(r"(\w)- (\w)", r"\1-\2", text)
    text = latex_escape(text)
    text = convert_quotes(text)
    text = emphasize_caps_words(text)
    if kind == "break":
        return "\\quietbreak\n"
    if kind == "tribunal":
        m = re.match(r"^([A-Z][A-Z]+):\s*(.*)$", text)
        if not m:
            return "% (malformed tribunal block)\n" + text + "\n"
        name = m.group(1)
        body = m.group(2)
        return f"\\begin{{tribunal}}{{{name}}}\n{body}\n\\end{{tribunal}}\n"
    if kind == "reflection":
        return f"\\begin{{reflection}}\n{text}\n\\end{{reflection}}\n"
    if kind == "latticelog":
        return f"\\begin{{latticelog}}\n{text}\n\\end{{latticelog}}\n"
    # body
    if drop_letter and text:
        # First letter big, second letter completes the word in lettrine "throw"
        first = text[0]
        rest = text[1:]
        if first.isalpha():
            # Find the rest of the first word (up to next space)
            m = re.match(r"^([A-Za-z']+)", rest)
            if m:
                throw = m.group(1)[:1]  # one-letter throw is enough
                tail = rest[len(throw):]
                return f"\\lettrine{{{first}}}{{{throw}}}{tail}\n"
        return text + "\n"
    return text + "\n"


def render_chapter(n, title, blocks, *, motif=None):
    out = []
    out.append("")
    out.append("% " + "=" * 60)
    if motif:
        out.append(
            f"\\chapter[{title}]{{{title}\\hspace{{0.6em}}{{\\Large\\color{{accent}}{motif}}}}}")
    else:
        out.append(f"\\chapter{{{title}}}")
    out.append("% " + "=" * 60)
    out.append("")
    first_body_done = False
    for kind, payload in blocks:
        is_first_body = (kind == "body" and not first_body_done)
        out.append(render_block(kind, payload, first_body=is_first_body, drop_letter=is_first_body))
        if kind == "body":
            first_body_done = True
    return "\n".join(out)


# Hanzi motifs paired to chapter atmosphere
MOTIFS_B1 = {
    1: "门",   # gates / doors
    2: "廊",   # gallery / corridor
    3: "觉",   # feel / awaken
    4: "镜",   # mirror
    5: "界",   # boundary
    6: "刃",   # blade (Occam)
    7: "线",   # threads / strings
    8: "宥",   # reprieve / forgive
    9: "茶",   # tea / coffee ritual
    10: "粥",  # congee
    11: "病",  # illness
    12: "別",  # parting
}
MOTIFS_B2 = {
    1: "构",   # construct / reconstruct
    2: "异",   # different / off
    3: "题",   # paper / problem
    4: "令",   # decree / initiative
    5: "众",   # the many / the affected
    6: "辩",   # debate / colosseum
    7: "诏",   # warrant / summons
    8: "散",   # scatter
    9: "守",   # hold / persist
}


def main():
    book1_src = pathlib.Path("/tmp/book1.txt").read_text()
    book2_src = pathlib.Path("/tmp/book2.txt").read_text()

    def strip_endmatter(src):
        m = re.search(r"\bEND\s+OF\s+BOOK", src)
        if m:
            src = src[: m.start()]
        else:
            m = re.search(r"^\s*END\s*$", src, re.MULTILINE)
            if m:
                src = src[: m.start()]
        return src

    book1_src = strip_endmatter(book1_src)
    book2_src = strip_endmatter(book2_src)

    book1_lines = normalize_lines(book1_src)
    book2_lines = normalize_lines(book2_src)

    chapters_b1 = find_chapters(book1_lines, CHAPTER_TITLES_BOOK1)
    chapters_b2 = find_chapters(book2_lines, CHAPTER_TITLES_BOOK2)

    out_b1 = []
    for n, title, body in chapters_b1:
        blocks = parse_chapter_blocks(body)
        rendered = render_chapter(n, title, blocks, motif=MOTIFS_B1.get(n))
        out_b1.append(rendered)

    out_b2 = []
    for n, title, body in chapters_b2:
        blocks = parse_chapter_blocks(body)
        rendered = render_chapter(n, title, blocks, motif=MOTIFS_B2.get(n))
        out_b2.append(rendered)

    pathlib.Path("/tmp/b1_chapters_auto.tex").write_text("\n".join(out_b1))
    pathlib.Path("/tmp/b2_chapters_auto.tex").write_text("\n".join(out_b2))

    print(f"Book 1 chapters: {len(chapters_b1)}")
    print(f"Book 2 chapters: {len(chapters_b2)}")


if __name__ == "__main__":
    main()
