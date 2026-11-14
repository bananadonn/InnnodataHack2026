# Track 1 — AI Task Factory · package

Everything needed to run the Track 1 challenge: build a pipeline that turns a supplied repository into
realistic, hard, reliably-testable feature tasks in the [Harbor](https://www.harborframework.com/) interface —
then run the benchmark model against them.

## The loop

```
supplied repo  ──►  your pipeline  ──►  task packages  ──►  SELF-CHECK (sound?)  ──►  BENCHMARK (hard?)
 (click/zod/jsoncpp)   (you build)   (Harbor format, 5       oracle=1.0 / nop=0.0      resolve@k, k=3
                                      per chosen repo)
```
After you submit, we evaluate your pipeline and its output against the brief's requirements.

A finished task is **sound** (gold solves it, feature tests detect its absence, regression stays green) and
**hard** (the benchmark model fails it). Your deliverable is the *pipeline* that produces such tasks reliably,
plus evidence.

## What's in here

| Path | Audience | What it is |
|---|---|---|
| `BRIEF.md` | participants | The challenge: goal, what "good" means, supplied repos, deliverable, **tools & budget, and rules**. |
| `SUBMISSION.md` | participants | What to hand back + **how to submit (ZIP naming / form) and the demo format**. |
| `JUDGING.md` | participants | The **published judging criteria** (7 weighted dimensions, 100 pts) + scale and tie-break. |
| `Track1_AI_Task_Factory_Participant_Guide.docx` | participants | The polished one-file participant guide (§1–§6 + judging table). Same content as `BRIEF.md` + `SUBMISSION.md` + `JUDGING.md`. |
| `docs/harbor_task_interface.md` | participants | The package format contract (what a task package looks like). |
| `docs/harbor_quickstart.md` | participants | Harbor CLI mechanics (`run`, oracle/nop self-check, benchmark) — commands only. |
| `examples/` | participants | **One complete, worked example task** (a synthetic toy) so you can see the format — input/spec, gold, tests, Dockerfile. Illustrative only; not a supplied repo, not to submit. |
| `docs/validation_protocol.md` | participants | How to self-check a package (format lint + oracle/nop soundness). |
| `repos/README.md` | participants | The supplied repositories + environment recipes. |
| `harness/` | participants | `check_structure.py` (lint) + `selfcheck.sh` (Harbor oracle/nop soundness). Self-check only — not the grader. |
| `benchmark/benchmark_guide.md` | participants | The finish line: benchmarking a model (resolve@k). |
| `evaluation/` | **evaluators only** | Our grader + scoring criteria. **Remove before handing the kit to teams — it reveals how we grade.** |

## Quick start (participants)

1. Read `BRIEF.md`, then `docs/harbor_task_interface.md`. Look at `examples/` — one complete worked task
   package showing the format end to end (spec → gold → tests → Dockerfile).
2. Install the Harbor CLI (https://www.harborframework.com/) and Docker.
3. Pick a supplied repo (`repos/README.md`) and a real `base_commit`; confirm it builds and its suite is green.
4. Build your pipeline to emit packages in the interface — **5 distinct tasks from your chosen repo**. How you
   design it is up to you.
5. Self-check each package (needs Harbor + Docker; no model key):
   ```bash
   harness/check_structure.py              generated_tasks/*   # fast offline lint
   SELFCHECK_OUT=./sc harness/selfcheck.sh generated_tasks/*   # oracle=1.0, nop=0.0 (mechanical soundness)
   ```
   Also emit `pipeline_run.json` (per-task resource usage — see `SUBMISSION.md`) so we can
   measure efficiency. Final acceptance is decided by our evaluation after you submit.
6. Benchmark your sound tasks against the benchmark model (`benchmark/benchmark_guide.md`) — low resolve@k = hard.
7. Package it up per `SUBMISSION.md`.

## Requirements
- **Harbor CLI** + **Docker** for validation and benchmarking.
- A **model API key** only for the benchmark step (validation needs none). Keys go in the environment —
  never on the command line, never committed.
- **Teams of 5, 4h30m build, in-person.** You get one OpenRouter + one Anthropic key per team ($100 each).
  See `BRIEF.md` → *Tools and access* / *Rules*, and `SUBMISSION.md` → *How to submit* / *Demo*.

## For evaluators
The grader and scoring criteria live in `evaluation/` — **remove that folder before handing the kit to
teams** (it reveals how we grade). Evaluators: start at `evaluation/OVERVIEW.md` and
`evaluation/evaluator_runbook.md`.
