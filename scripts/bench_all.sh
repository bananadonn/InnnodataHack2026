#!/usr/bin/env bash
# Benchmark every package in generated_tasks/ with the required model: resolve@3.
# Run from WSL2 with Docker running. Needs the Anthropic key in .env (or the environment).
#
#   scripts/bench_all.sh                     # all packages
#   scripts/bench_all.sh generated_tasks/pallets__click-0001-foo   # specific ones
#
# Raw harbor run dirs go to ./bench/<instance_id> (gitignored); the console log of each
# run is saved to results/bench/<instance_id>.log.
# Only benchmark packages that already pass scripts/selfcheck_all.sh.
set -uo pipefail
cd "$(dirname "$0")/.."

AGENT="terminus-2"
MODEL="anthropic/claude-haiku-5-5"
K=3

if [ -f .env ]; then set -a; . ./.env; set +a; fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "the Anthropic key is not set (see .env.example)" >&2; exit 2; }

if [ "$#" -ge 1 ]; then
  tasks=("$@")
else
  tasks=()
  for d in generated_tasks/*/; do
    [ -f "${d}task.toml" ] && tasks+=("${d%/}")
  done
fi
[ "${#tasks[@]}" -ge 1 ] || { echo "no task packages found in generated_tasks/" >&2; exit 2; }

mkdir -p results/bench bench
rc=0
for task in "${tasks[@]}"; do
  task="${task%/}"; iid="$(basename "$task")"
  echo "== $iid =="
  uv run harbor run -p "$task" -a "$AGENT" -m "$MODEL" -k "$K" -o "bench/$iid" --no-delete -y \
    2>&1 | tee "results/bench/$iid.log"
  [ "${PIPESTATUS[0]}" = 0 ] || rc=1
done

# TODO: copy rollouts into the submission layout trajectory/<instance_id>/<model>/rollout_N/
#       and compute resolve@3 per task (see kit/benchmark/benchmark_guide.md).
exit "$rc"
