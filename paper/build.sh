#!/usr/bin/env bash
cd "$(dirname "$0")" || { printf 'Could not enter the source directory.\n' >&2; exit 1; }
command -v pdflatex >/dev/null 2>&1 || { printf 'pdflatex is required.\n' >&2; exit 1; }
if command -v bibtex >/dev/null 2>&1; then
  BIBTEX=bibtex
elif command -v bibtex.original >/dev/null 2>&1; then
  BIBTEX=bibtex.original
else
  printf 'A BibTeX executable is required.\n' >&2
  exit 1
fi
run_step() {
  "$@"
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    printf 'Build step failed with return code %s: %s\n' "$rc" "$*" >&2
    return "$rc"
  fi
  return 0
}
run_step pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex || exit $?
run_step "$BIBTEX" main || exit $?
run_step pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex || exit $?
run_step pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex || exit $?
