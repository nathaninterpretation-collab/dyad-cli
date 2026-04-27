#!/usr/bin/env bash
# build.sh — compile The Last Corridor omnibus PDF
#
# Steps:
#   1. Convert all SVG figures to PDF (rsvg-convert)
#   2. xelatex × 2 (for ToC and refs)
#
# Usage:
#   ./build.sh           — full build
#   ./build.sh quick     — single xelatex pass

set -euo pipefail

cd "$(dirname "$0")"

echo "==> Converting SVG figures → PDF"
shopt -s nullglob globstar
for svg in figures/**/*.svg; do
  pdf="${svg%.svg}.pdf"
  if [[ ! -f "$pdf" || "$svg" -nt "$pdf" ]]; then
    rsvg-convert -f pdf -o "$pdf" "$svg"
    echo "    $svg → $pdf"
  fi
done

QUICK=${1:-}
echo "==> xelatex pass 1"
xelatex -interaction=nonstopmode -halt-on-error book.tex > /tmp/xelatex1.log 2>&1 || {
  echo "xelatex pass 1 failed; tail of log:"
  tail -30 /tmp/xelatex1.log
  exit 1
}

if [[ "$QUICK" != "quick" ]]; then
  echo "==> xelatex pass 2"
  xelatex -interaction=nonstopmode -halt-on-error book.tex > /tmp/xelatex2.log 2>&1 || {
    echo "xelatex pass 2 failed; tail of log:"
    tail -30 /tmp/xelatex2.log
    exit 1
  }
fi

if [[ -f book.pdf ]]; then
  pages=$(pdfinfo book.pdf 2>/dev/null | awk '/^Pages:/ {print $2}' || echo "?")
  size=$(du -h book.pdf | awk '{print $1}')
  echo "==> Built book.pdf  ·  ${pages} pages  ·  ${size}"
else
  echo "==> Build did not produce book.pdf"
  exit 1
fi
