#!/usr/bin/env bash
# build_all.sh — end-to-end video pipeline runner.
#
# Runs every stage for every chapter, then optionally concats into the
# full-book MP4.
#
# Usage:
#   video/scripts/build_all.sh              # run full pipeline
#   video/scripts/build_all.sh frame        # just one chapter
#   video/scripts/build_all.sh --no-concat  # skip final concat
#
# Prerequisites:
#   - python3 with PIL, openai
#   - ffmpeg, espeak-ng
#   - OPENAI_API_KEY in environment for production-quality TTS
#     (falls back to espeak-ng if API is unreachable)

set -euo pipefail
cd "$(dirname "$0")/../.."

CHAPTERS=("frame" "p1" "p2" "p3" "p4" "coda")
PARTS_DIR=parts
BUILD=video/build
MANIFESTS=$BUILD/manifests
AUDIO=$BUILD/audio
FRAMES=$BUILD/frames
CLIPS=$BUILD/clips
SCRIPTS=video/scripts

mkdir -p "$MANIFESTS" "$AUDIO" "$FRAMES" "$CLIPS"

run_chapter() {
  local ch=$1
  echo "==> chapter: $ch"

  echo "  [extract]"
  python3 "$SCRIPTS/extract_text.py" "$PARTS_DIR/$ch.tex" > "$MANIFESTS/$ch.json"

  echo "  [tts]"
  python3 "$SCRIPTS/tts.py" "$MANIFESTS/$ch.json" --out "$AUDIO"

  echo "  [align]"
  python3 "$SCRIPTS/align.py" "$AUDIO/$ch.timing.json"

  echo "  [render]"
  python3 "$SCRIPTS/render.py" "$AUDIO/$ch.words.json" --out "$FRAMES"

  echo "  [compose]"
  python3 "$SCRIPTS/compose.py" chapter "$ch" \
    --frames "$FRAMES" --audio "$AUDIO" --out "$CLIPS"

  echo "  ✓ $ch → $CLIPS/$ch.mp4"
}

# Parse args
ONLY=""
NO_CONCAT=0
for arg in "$@"; do
  case "$arg" in
    --no-concat) NO_CONCAT=1 ;;
    -*)          echo "unknown flag: $arg" >&2; exit 2 ;;
    *)           ONLY="$arg" ;;
  esac
done

if [ -n "$ONLY" ]; then
  run_chapter "$ONLY"
else
  for ch in "${CHAPTERS[@]}"; do
    run_chapter "$ch"
  done
  if [ "$NO_CONCAT" -eq 0 ]; then
    echo "==> concatenating full book"
    python3 "$SCRIPTS/compose.py" concat \
      --clips "$CLIPS" \
      --out "$BUILD/the_last_corridor.mp4" \
      "${CHAPTERS[@]}"
    echo "✓ $BUILD/the_last_corridor.mp4"
  fi
fi
