# The Last Corridor — Kinetic Typography Video

Renders the novel as an MP4: word-by-word reveal in sync with TTS narration,
cream-on-black v0.2 aesthetic, distinct voices for tribunal speakers, ornaments
at narrative breaks.

## Pipeline

```
parts/<ch>.tex                                   # LaTeX source
   │
   │ video/scripts/extract_text.py
   ▼
build/manifests/<ch>.json                        # structured blocks (narration, speaker, break)
   │
   │ video/scripts/tts.py
   ▼
build/audio/<ch>.mp3                             # synthesised narration
build/audio/<ch>.timing.json                     # per-block t_start/t_end
   │
   │ video/scripts/align.py
   ▼
build/audio/<ch>.words.json                      # per-word timestamps
   │
   │ video/scripts/render.py
   ▼
build/frames/<ch>/000001.png ...                 # 1920×1080 @ 30fps
   │
   │ video/scripts/compose.py chapter <ch>
   ▼
build/clips/<ch>.mp4
   │
   │ video/scripts/compose.py concat
   ▼
build/the_last_corridor.mp4
```

## Quickstart

```bash
# Prereqs
apt-get install -y ffmpeg espeak-ng
pip install pillow openai

# Run everything
export OPENAI_API_KEY=sk-...
video/scripts/build_all.sh
```

The first run is the long one — OpenAI TTS for ~9000 words takes ~10–15 min
and costs roughly $4–8 on `gpt-4o-mini-tts`. Frame rendering is CPU-bound,
about 15 fps on a modern laptop; the full ~75-minute book takes ~2 hours to
render. ffmpeg encoding is fast (real-time).

Subsequent runs are incremental — audio clips, frames, and chapter MP4s are
cached. To force a re-render of one chapter:

```bash
rm -rf video/build/{audio,frames,clips}/p2*
video/scripts/build_all.sh p2
```

## TTS backends

`tts.py` tries OpenAI's `gpt-4o-mini-tts` first (best quality, style direction
via the `instructions` parameter). If the host is unreachable or the key is
missing, it falls back transparently to local `espeak-ng`. The voice mapping
(see `tts.py: SPEAKER_VOICES`) is preserved across both backends — each
OpenAI voice has a chosen espeak counterpart that approximates gender and
register.

For absolute best quality, swap to ElevenLabs by editing `synth_to_file` to
use the ElevenLabs SDK (~$8–15 for full book at premium voices).

## Voice casting

| Role     | Voice (OpenAI) | Notes                                          |
|----------|----------------|------------------------------------------------|
| Narrator | ash            | Deliberate, weighted, half-beat pauses         |
| Olen     | ash            | Same voice — he is also the recounting narrator|
| Maren    | sage           | Judicial, institutional warmth                 |
| Davan    | verse          | Precise, slightly clipped                      |
| Kael     | ballad         | Analytical, cool                               |
| Pren     | coral          | Brisker, technical                             |
| Lien     | alloy          | Procedural, slightly skeptical                 |
| Sera     | nova           | Composed, physicalist, never rises             |
| Voss     | shimmer        | Layered, dreamy                                |
| Lireni   | echo           | Sharp, political                               |
| Tomek    | onyx           | Quiet, weary, distant                          |
| Kepler citizen | fable    | Uniform, integrated, even                      |

Style instructions are passed to `gpt-4o-mini-tts` per block. Edit
`SPEAKER_VOICES` to retune.

## Visual spec

- Resolution: 1920×1080 (16:9). Change `WIDTH`/`HEIGHT` in `render.py`.
- Background: `#0A0907`, subtle radial vignette
- Text: `#F5EBD8` cream, Liberation Serif (or DejaVu fallback)
- Chapter label: dim, top-left, monospace
- Speaker tags: dim accent, monospace, sit above dialog
- Break ornament: `◆     ◆     ◆` in dried-blood accent, fade in/hold/fade out
- Word reveal: 220 ms fade-in per word, no movement
- Page clear: at speaker change, narrative break, and page overflow

## Tuning

- Fade duration: `fade_dur = 0.22` in `render.py: compose_frame`
- Inter-block silence: `INTER_BLOCK_SILENCE = 0.40` in `tts.py`
- Break silence: `BREAK_SECONDS = 1.6`
- Title-card hold: `+1.4` in `tts.py: build_chapter` after title synth
- FPS: pass `--fps 24` for film-pace; default is 30

## Costs (OpenAI, approximate)

| Chapter | Words | Tokens | $ at gpt-4o-mini-tts |
|---------|-------|--------|----------------------|
| Frame   | 227   | ~300   | $0.05                |
| Part I  | ~3500 | ~4500  | $0.80                |
| Part II | ~2400 | ~3100  | $0.55                |
| Part III| ~1900 | ~2400  | $0.45                |
| Part IV | ~2900 | ~3700  | $0.65                |
| Coda    | ~1200 | ~1500  | $0.30                |
| **Total**| ~12100| ~15500 | **~$2.80**          |

`gpt-4o-mini-tts` is `$0.60 / 1M tokens` (input + output combined). Whisper-1
forced alignment would add $0.006 / minute audio ≈ $0.45 for the full book.
Currently the pipeline uses linear distribution per block, so no whisper cost.

## Output

A finished build produces:

```
build/
├── manifests/      JSON per chapter (block structure)
├── audio/          MP3 + timing per chapter, per-block fragments under <ch>/
├── frames/         PNG sequences per chapter (~2 GB for full book)
├── clips/          MP4 per chapter (~20 MB each)
└── the_last_corridor.mp4   the assembled book (~150 MB)
```

The frames directory is large but disposable — delete after a successful
build. Audio MP3s are tiny and worth keeping (they cost real money to
regenerate).
