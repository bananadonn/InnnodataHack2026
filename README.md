# Innodata Hackathon · Track 1 "AI Task Factory"

A pipeline that generates [Harbor](https://www.harborframework.com/)-format coding task
packages on top of `pallets/click`, validates them (oracle reward 1.0, nop reward 0.0), and
benchmarks `anthropic/claude-haiku-5-5` on them via the `terminus-2` agent at k=3.

**Deliverable:** the pipeline, 5 validated task packages, evidence, and a writeup.

For ordered commands to run every agent, start with [run_pipeline.md](run_pipeline.md).
The organizer brief, rubric and submission rules are in [`kit/`](kit/README.md). Read
`kit/BRIEF.md` and `kit/docs/harbor_task_interface.md` first.

## Status

| Piece | State |
|---|---|
| Repo scaffold, kit restored | done |
| click base template (`templates/click_base/`) | Dockerfile written, **not yet built or tested**; grading files are TODO placeholders |
| Kit grading files (`grade.py`, `test.sh`, ...) | **missing**, see [`kit/MISSING.md`](kit/MISSING.md) |
| Repo exploration (`pipeline/explore.py`) | implemented (Claude Agent SDK) |
| Feature design: propose, validate, spec (`pipeline/propose.py`, `audit.py`, `spec.py`) | implemented |
| Golden solution, hidden tests, packaging (`pipeline/generate.py`, `select_p2p.py`, `validate.py`) | stubs only |
| Coding agents | Haiku candidate + independent OpenRouter reference; authoring scaffold, execution validation pending |
| Generated tasks, selfcheck, benchmark | none yet |

Plan and ownership: [`docs/PLAN.md`](docs/PLAN.md).

## Setup

Windows users: do everything inside **WSL2** (the harness scripts are bash). Clone the repo
inside the WSL filesystem, not under `/mnt/c`.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the WSL2
   backend and make sure it is running.
2. Install [uv](https://docs.astral.sh/uv/).
3. Install dependencies (Python 3.12, harbor 0.25.x):
   ```bash
   uv sync
   ```
4. Create your local env file and fill in the keys (ask the team lead):
   ```bash
   cp .env.example .env
   ```
5. Pull the base image:
   ```bash
   docker pull python:3.12-slim
   ```
6. Build the click template image and confirm click's test suite is green:
   ```bash
   docker build -t click-base templates/click_base/environment
   docker run --rm click-base python -m pytest -q
   ```

## How to run

```bash
# 0. Explore the input repo: clone, read, research, write a report to runs/<run_id>/
uv run python -m pipeline.cli explore https://github.com/pallets/click --ref 8.5.1
uv run python -m pipeline.cli ask <run_id> "Where are option defaults resolved?"

# 0b. Design the features: user demand → 15 candidates → novelty/value/difficulty audit → select 5 → specs + blind quiz
uv run python -m pipeline.cli demand <run_id>
uv run python -m pipeline.cli propose <run_id>
uv run python -m pipeline.cli validate <run_id>
uv run python -m pipeline.cli spec <run_id>
# Draft feature tests from the final specs and locate existing regression tests
uv run python -m pipeline.cli tests <run_id>
# details: pipeline_plan.md → "How to Run"

# Prepare separate Haiku/reference coding workspaces, without paid calls
uv run python -m pipeline.cli code <run_id> --agent both

# Author one feature through both providers (uses the team's API budgets)
uv run python -m pipeline.cli code <run_id> --agent both --feature <slug> --execute

# 1. Generate packages into generated_tasks/   (stub for now)
uv run python -m pipeline.cli generate --n 5

# 2. Validate: structure lint + oracle/nop selfcheck. No model key needed.
scripts/selfcheck_all.sh

# 3. Benchmark the packages that pass: haiku via terminus-2, k=3. Uses the Anthropic key.
scripts/bench_all.sh

# 4. Before submitting: whole-submission check (see "Open questions" for a caveat)
uv run python kit/harness/validate_submission.py <submission_dir>
```

Both scripts accept specific package paths as arguments to run a subset.

The `tests` command reads `test_agent_rules.md` on every invocation and uses `TEST_MODEL`
in `pipeline/config.py`. It consumes the selected run's `features.json` and `features.md`
(or also `feature.md` when present). It inspects the repository's existing tests and prints
whether they were found and their folder paths. It then drafts one new pytest file per
feature, with acceptance-criterion mappings. Existing tests and source files are untouched.

Outputs are in `runs/<run_id>/feature_tests/attempt_N/`: `regression_tests.json`, `report.md`,
`summary.json`, input/rules snapshots, and one folder per feature containing `draft.json`,
`files/<repo-relative-test-path>`, and `test_patch.diff`. Ambiguous specifications are reported
as blocked drafts. Each invocation keeps previous attempts. Test files are drafts: syntax
and path checks are performed, but tests are not executed, collected IDs are not invented,
and Harbor/oracle/nop/mutation validation remains pending until a gold implementation exists.

The two coding agents live in separate modules: `pipeline/haiku_agent.py` uses the Claude
Agent SDK with the `haiku` alias, and `pipeline/reference_agent.py` uses OpenRouter with
`OPENROUTER_REFERENCE_MODEL` (default `anthropic/claude-opus-4.6`). Shared preparation and
source-only patch checks live in `pipeline/coding_common.py`; orchestration lives in
`pipeline/coding.py`. See [coding-agent details](docs/CODING_AGENTS.md) for the scaffold's
boundaries and output layout. No output is accepted as validated gold until execution gates pass.

## Layout

```
kit/               organizer kit, restored. Read-only reference, do not edit.
templates/click_base/   base package every generated task starts from
pipeline/          the task factory (explore → propose → generate → select_p2p → validate, + telemetry)
runs/<run_id>/     one exploration run: report.json, report.md, run.json, events.jsonl (clone is gitignored)
generated_tasks/   pipeline output (Harbor packages). Committed. Never hand-edited.
results/selfcheck/ oracle/nop evidence        results/bench/  haiku resolve@3 logs
results/pipeline_run.json   per-task telemetry (schema: kit/SUBMISSION.md §3b)
docs/              PLAN.md, VARIATION.md (writeup), RESULTS.md
scripts/           selfcheck_all.sh, bench_all.sh
```

Raw harbor run directories land in `./sc` and `./bench` at the repo root and are gitignored.

## Conventions

- **Base:** click 8.5.1 = `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`. Python 3.12. harbor 0.25.x.
  All constants live in `pipeline/config.py`.
- **Task IDs:** `pallets__click-0001-<kebab-slug>`. The folder name, `name` and `instance_id`
  in `task.toml` must all be identical.
- **Models:** Sonnet explores, mines demand and audits novelty/value; Opus proposes,
  audits difficulty, refines specs and authors test drafts through the Anthropic key.
  Haiku also authors implementation candidates through the Claude Agent SDK. The independent
  reference coding agent uses the OpenRouter key and its configurable model. Blind quizzes
  use independent Sonnet/Haiku readers. Benchmark only with `anthropic/claude-haiku-5-5`
  via `terminus-2`; authoring and model quizzes are separate from benchmark evidence.
  Model choices and limits live in `pipeline/config.py`.
- **Benchmark k:** the Markdown guide says k=3, part of the Word guide says k=5. Unresolved;
  ask the organizers. Scripts use k=3 for now.
- **The exploration agent is read-only** and confined to its run workspace. Repo and web
  content are untrusted input.
- **Gold patch and test patch must touch disjoint files.** The grader resets test-patch paths
  before applying the test patch, so any overlap reverts part of the gold.
- **Feature tests assert concrete values. Specs must state everything the tests check.**
- **Don't hand-fix generated packages.** Fix the pipeline and regenerate; the raw output is scored.
- **Never commit keys.** `.env` is gitignored; keys are passed by environment only.
- **Windows users work inside WSL2.**
- `kit/` is a reference copy. Don't edit it.

## Open questions

- **Missing grading files.** The toy example's `grade.py`, `test.sh`, `run_script.sh`,
  `parser.py` and friends are not in our copy of the kit. Ask the organizers
  ([`kit/MISSING.md`](kit/MISSING.md)).
- **`no-network` vs benchmarking.** The template sets `network_mode = "no-network"`, which is
  right for oracle/nop. `kit/benchmark/benchmark_guide.md` says a benchmark agent needs egress
  (`allowlist` or `public`) and will be starved under `no-network`. Decide before benchmarking.
- **Trajectory layout.** The submission wants rollouts at top-level
  `trajectory/<instance_id>/<model>/rollout_N/`. `scripts/bench_all.sh` currently keeps raw runs
  in `./bench` and logs in `results/bench/`; the copy step is a TODO.
- **`validate_submission.py` on the repo root** counts every folder with a `task.toml` as a
  package, including `templates/click_base/` and the incomplete toy example in `kit/`, and will
  report errors for them. Run it on a staged submission folder instead.
