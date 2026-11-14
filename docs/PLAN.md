# Plan: timeline and ownership

> Skeleton. Fill in owners and times as a team. Build window is 4h30m (see `kit/README.md`).

## Ownership

| Area | Files | Owner | Backup |
|---|---|---|---|
| Environment + template | `templates/click_base/`, Dockerfile green | TBD | TBD |
| Grading files from organizers | `kit/MISSING.md` | TBD | TBD |
| Propose (ideas, variation) | `pipeline/propose.py`, `docs/VARIATION.md` | TBD | TBD |
| Generate (spec, gold, tests) | `pipeline/generate.py` | TBD | TBD |
| P2P selection | `pipeline/select_p2p.py` | TBD | TBD |
| Validation loop | `pipeline/validate.py`, `scripts/selfcheck_all.sh` | TBD | TBD |
| Telemetry | `pipeline/telemetry.py`, `results/pipeline_run.json` | TBD | TBD |
| Benchmark | `scripts/bench_all.sh`, `results/bench/` | TBD | TBD |
| Writeup + submission | `docs/RESULTS.md`, `docs/VARIATION.md`, ZIP | TBD | TBD |

## Timeline

| When | Milestone | Done |
|---|---|---|
| TBD | Everyone set up: `uv sync`, template image builds, click suite green | [ ] |
| TBD | Missing kit grading files obtained; template complete | [ ] |
| TBD | One hand-made package passes selfcheck (oracle 1.0 / nop 0.0) | [ ] |
| TBD | Pipeline produces one validated package end to end | [ ] |
| TBD | 5 validated packages in `generated_tasks/` | [ ] |
| TBD | Benchmark resolve@3 for all 5 | [ ] |
| TBD | Writeup, `validate_submission.py` clean, submitted | [ ] |

## Open questions

- See the "Open questions" section of the top-level `README.md`.
