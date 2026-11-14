#!/usr/bin/env bash
# Lint + oracle/nop selfcheck for every package in generated_tasks/.
# Run from WSL2 with Docker running. No model key needed.
#
#   scripts/selfcheck_all.sh                 # all packages
#   scripts/selfcheck_all.sh generated_tasks/pallets__click-0001-foo   # specific ones
#
# Raw harbor run dirs go to ./sc (gitignored). The printed tables are saved under
# results/selfcheck/ as our validation evidence.
set -uo pipefail
cd "$(dirname "$0")/.."

if [ "$#" -ge 1 ]; then
  tasks=("$@")
else
  tasks=()
  for d in generated_tasks/*/; do
    [ -f "${d}task.toml" ] && tasks+=("${d%/}")
  done
fi
[ "${#tasks[@]}" -ge 1 ] || { echo "no task packages found in generated_tasks/" >&2; exit 2; }

mkdir -p results/selfcheck
rc=0

echo "## check_structure"
uv run python kit/harness/check_structure.py "${tasks[@]}" 2>&1 | tee results/selfcheck/check_structure.txt
[ "${PIPESTATUS[0]}" = 0 ] || { echo "lint failed: fix every ERROR before building containers" >&2; exit 1; }

echo "## selfcheck (oracle / nop)"
SELFCHECK_OUT="${SELFCHECK_OUT:-./sc}" uv run bash kit/harness/selfcheck.sh "${tasks[@]}" 2>&1 | tee results/selfcheck/selfcheck.txt
[ "${PIPESTATUS[0]}" = 0 ] || rc=1

exit "$rc"
