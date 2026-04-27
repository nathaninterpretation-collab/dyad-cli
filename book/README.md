# The Last Corridor — Omnibus Edition

Typeset omnibus of *The Last Corridor*, Books One & Two, by Mintao Huang
(黄敏韬). Source novel: BilinCo · Philosophical Fiction · April 2026.
Framework: Tripolism · Three-World Ontology · L/P Boundary.

## Build

```
./build.sh        # full build (xelatex × 2 for ToC and refs)
./build.sh quick  # single xelatex pass
```

Output: `book.pdf` — 140 × 210 mm, ~140 pages, set in Latin Modern Roman
with Noto Serif CJK SC for hanzi.

## Toolchain

- `xelatex` (texlive-xetex)
- `rsvg-convert` (librsvg2-bin) — converts the SVG diagrams to PDF
- Noto Serif CJK SC (`fonts-noto-cjk`) — for inline hanzi motifs

## Layout

```
book/
├── book.tex                     master document
├── style/corridor.sty           typography package (geometry, fonts,
│                                tribunal/reflection/latticelog
│                                environments, drop-caps, running heads)
├── meta/                        front matter
│   ├── halftitle.tex
│   ├── titlepage.tex
│   ├── copyright.tex
│   ├── dedication.tex           bilingual EN / 中文
│   ├── epigraph.tex
│   ├── preface.tex              "A Reader's Primer" with framework diagrams
│   └── colophon.tex
├── parts/
│   ├── book_one.tex             part-page opener
│   ├── b1_chapters.tex          12 chapters of Book One
│   ├── book_two.tex             part-page opener
│   └── b2_chapters.tex          9 chapters of Book Two
├── figures/                     SVG conceptual diagrams + hanzi motifs
│   ├── three_worlds.svg
│   ├── lp_boundary.svg
│   ├── corridor.svg
│   ├── format_mismatch.svg
│   ├── cogito_loop.svg
│   ├── chinese_room.svg
│   ├── tribunal_geometry.svg
│   ├── two_hands.svg
│   ├── scattering_map.svg
│   └── motifs/                  廊 · 觉 · 镜 · 桥 — large hanzi seals
├── ai_art/
│   └── frontispiece_briefs.md   image-generation prompts (Midjourney /
│                                SDXL / DALL-E) for chapter frontispieces
└── scripts/
    └── convert.py               source-text → LaTeX converter (used to
                                 author chapter files from the original PDFs)
```

## Editorial register

- **Light copyedit + targeted polish.** The authorial voice — recursive,
  declarative, deliberate — is preserved. Smart quotes, em-dashes,
  small-caps emphasis on the source's ALL-CAPS-emphasis tokens, and the
  three structural environments (`tribunal`, `reflection`, `latticelog`)
  are applied uniformly. No scenes are re-ordered, no paragraphs cut.
- **Three-tier structural rendering.** The book has three voices:
  body prose; tribunal speech (sans, indented, dim left rule); reflective
  italic stanzas (italic, indented, accent left rule); Lattice-Olen logs
  (italic, indented, dim left rule). Each is a distinct typographic
  register that mirrors the L/P framework the book is about.

## Diagrams

Eight conceptual SVGs author the book's framework visually:

| Figure              | Purpose                                          |
|---------------------|--------------------------------------------------|
| `three_worlds`      | Matter / Structure / Felt experience            |
| `lp_boundary`       | Exclusion vs. happening — the wall              |
| `corridor`          | The felt channel inside an architecture          |
| `format_mismatch`   | How the gravitational wave opened a corridor     |
| `cogito_loop`       | The cogito read structurally vs. phenomenally    |
| `chinese_room`      | The room as the Lattice civilization             |
| `tribunal_geometry` | The chamber, five Counselors, Olen, Sera         |
| `two_hands`         | One drunk, one held — the book's heart           |
| `scattering_map`    | Fifteen corridors across three star systems      |

Hanzi motifs (廊 · 觉 · 镜 · 桥) appear inline in chapter heads and as
large seal-style figures in `figures/motifs/`.

## License

Story © 2026 Mintao Huang. The omnibus typesetting layer (this LaTeX
project) is provided alongside the source novel for reading and study.
