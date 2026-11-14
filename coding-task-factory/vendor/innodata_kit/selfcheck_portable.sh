#!/usr/bin/env bash
# selfcheck.sh — participant self-check of a task package's MECHANICAL soundness.
#
# This uses only the PUBLIC Harbor interface (the oracle/nop baselines) — not our evaluation grader. It tells
# you whether a task is sound enough to submit; final acceptance is decided by our evaluation after you submit.
#
#   oracle (gold applied)    -> expect reward 1.0, F2P n/n, P2P m/m   (gold solves it; regression intact)
#   nop    (base, no change) -> expect reward 0.0, F2P < n,  P2P m/m   (feature tests detect the missing impl)
#
# Requires: the `harbor` CLI (https://www.harborframework.com/) and Docker. No model API key needed
# (oracle/nop don't call a model).
#
# Usage:
#   harness/selfcheck.sh path/to/<instance_id> [more ...]
#   harness/selfcheck.sh path/to/generated_tasks/*
set -uo pipefail

command -v harbor >/dev/null 2>&1 || { echo "ERROR: 'harbor' CLI not on PATH — https://www.harborframework.com/" >&2; exit 2; }
[ "$#" -ge 1 ] || { echo "usage: $0 <task_dir> [<task_dir> ...]" >&2; exit 2; }

OUT_ROOT="${SELFCHECK_OUT:-$(mktemp -d)}"
echo "# selfcheck output: $OUT_ROOT"; echo

read_grade() {  # $1 run dir, $2 key
  local gd; gd="$(python3 -c "import glob,os,sys;f=sorted(glob.glob(sys.argv[1]+\"/**/grading_details.json\",recursive=True),key=os.path.getmtime);print(f[-1] if f else \"\")" "$1")"
  [ -z "$gd" ] && { echo ""; return; }
  python3 -c "import json;print(json.load(open('$gd')).get('$2',''))" 2>/dev/null
}

overall=0
for TASK in "$@"; do
  TASK="${TASK%/}"; iid="$(basename "$TASK")"
  [ -f "$TASK/task.toml" ] || { echo "SKIP  $iid (no task.toml)"; overall=1; continue; }
  o="$OUT_ROOT/$iid/oracle"; n="$OUT_ROOT/$iid/nop"; mkdir -p "$o" "$n"
  harbor run -p "$TASK" -a oracle -k 1 -o "$o" --no-delete -y >/dev/null 2>"$o/.err"
  harbor run -p "$TASK" -a nop    -k 1 -o "$n" --no-delete -y >/dev/null 2>"$n/.err"

  o_r=$(read_grade "$o" reward); o_fp=$(read_grade "$o" f2p_passed); o_ft=$(read_grade "$o" f2p_total)
  o_pp=$(read_grade "$o" p2p_passed); o_pt=$(read_grade "$o" p2p_total)
  n_r=$(read_grade "$n" reward); n_fp=$(read_grade "$n" f2p_passed); n_ft=$(read_grade "$n" f2p_total)
  n_pp=$(read_grade "$n" p2p_passed); n_pt=$(read_grade "$n" p2p_total)

  echo "== $iid =="
  if [ -z "$o_r" ] || [ -z "$n_r" ]; then
    echo "  FAIL  a baseline produced no grading (build/env crash). See $o/.err  $n/.err"; overall=1; echo; continue
  fi
  printf "  %-7s reward=%-5s F2P=%s/%s P2P=%s/%s\n" oracle "$o_r" "$o_fp" "$o_ft" "$o_pp" "$o_pt"
  printf "  %-7s reward=%-5s F2P=%s/%s P2P=%s/%s\n" nop    "$n_r" "$n_fp" "$n_ft" "$n_pp" "$n_pt"
  ok=1
  { [ "$o_r" = "1.0" ] && [ "$o_fp" = "$o_ft" ]; } || { echo "  ✗ gold not 1.0 / F2P not full"; ok=0; }
  { [ -n "$n_ft" ] && [ "$n_fp" = "$n_ft" ]; } && { echo "  ✗ F2P already pass at base (tests don't detect the feature)"; ok=0; }
  { [ "$o_pp" = "$o_pt" ] && [ "$n_pp" = "$n_pt" ]; } || { echo "  ✗ P2P not full on oracle and/or nop (regression)"; ok=0; }
  [ "$ok" = 1 ] && echo "  ✓ mechanically sound" || { echo "  ✗ not sound"; overall=1; }
  echo
done
[ "$overall" = 0 ] && echo "ALL SOUND" || echo "SOME NOT SOUND"
exit "$overall"
