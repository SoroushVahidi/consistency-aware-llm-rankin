#!/usr/bin/env bash
set -euo pipefail
document_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$document_root"
mkdir -p build
export TEXINPUTS="$document_root:${TEXINPUTS:-}"
export BIBINPUTS="$document_root:${BIBINPUTS:-}"
export BSTINPUTS="$document_root:${BSTINPUTS:-}"
for document_name in main supplement; do
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build "$document_name.tex" >"build/$document_name.console.log" 2>&1
  (cd build && bibtex "$document_name") >>"build/$document_name.console.log" 2>&1
  for build_pass in 2 3 4; do
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build "$document_name.tex" >>"build/$document_name.console.log" 2>&1
  done
  cp "build/$document_name.pdf" "$document_name.pdf"
done
cp supplement.pdf ESM_1.pdf
# Retained fallback: same scientific body, identity-bearing declarations/links suppressed.
for document_name in main supplement; do
  job_name="${document_name}_anonymous"
  for build_pass in 1 2 3; do
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build -jobname="$job_name" "\def\AnonymousVersion{1}\input{$document_name.tex}" >"build/$job_name.console.log" 2>&1
    if [ "$build_pass" = 1 ]; then
      (cd build && bibtex "$job_name") >>"build/$job_name.console.log" 2>&1
    fi
  done
  cp "build/$job_name.pdf" "$job_name.pdf"
done
