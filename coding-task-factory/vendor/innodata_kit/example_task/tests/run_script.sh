#!/usr/bin/env bash
# Run the graded tests. -rA feeds parser.py; only present files are passed so the
# feature-absent (nop) state still runs the P2P file. NOT `set -e` (pytest exits
# non-zero when the feature is absent).
set -uo pipefail
cd /app
PY=/app/.venv/bin/python
[ -x "$PY" ] || PY="$(command -v python)"
ALL=(
  "tests/test_slugify.py"
  "tests/test_truncate.py"
)
PRESENT=()
for f in "${ALL[@]}"; do [ -e "$f" ] && PRESENT+=("$f"); done
[ "${#PRESENT[@]}" -eq 0 ] && { echo "no graded test files present"; exit 0; }
"$PY" -m pytest "${PRESENT[@]}" -rA --tb=short -p no:cacheprovider --color=no --continue-on-collection-errors
