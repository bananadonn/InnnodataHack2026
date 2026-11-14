# Coding Task Factory — Track 1

Turns `pallets/click` at a pinned commit into **5 distinct, hard, mechanically sound feature tasks** in the
Harbor interface, with validation evidence, `pipeline_run.json` telemetry, and optional resolve@3 benchmark
trajectories.

```
plan slots ─► spec ─► novelty ─► gold ─► tests ─► local gates L1–L7 ─► Harbor export ─► container self-check ─► benchmark
(variation)  (LLM)  (GitHub+LLM)  (LLM)  (LLM)   (pytest, mutation,     (kit format)    (lint, oracle=1/nop=0,     (terminus-2,
                                                 fairness, solvers)                    container mutation)        haiku, k=3)
```

## Setup (Linux or macOS)

Requires **Python 3.12**, **git**, **Docker** (running), and the Harbor CLI.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # pytest==8.3.5 (local inner loop) + harbor==0.25.*
harbor --help                            # must work
```

Clone the supplied repo and pin the team-wide base commit (click 8.5.1, same as the teammates' template):

```bash
git clone https://github.com/pallets/click work/click
git -C work/click checkout cf19179e8e2fd54c601378cec9e0d21bb12b6fb1   # tag 8.5.1
export BASE=$(git -C work/click rev-parse HEAD)
echo $BASE                               # record it in the writeup
```

Keys (environment only — never on the command line, never committed):

```bash
export ANTHROPIC_API_KEY=...             # generation + benchmark
export OPENROUTER_API_KEY=...            # optional: a second, independent solver family
export GITHUB_TOKEN=...                  # optional: higher GitHub search rate limit for the novelty gate
```

Model roles (defaults shown; `provider:model`, provider = `anthropic` | `openrouter`):

| env var | default | role |
|---|---|---|
| `CTF_GEN_MODEL` | `anthropic:claude-sonnet-5-5` | specs, gold, novelty/fairness judges, near-miss bugs |
| `CTF_TEST_MODEL` | `anthropic:claude-sonnet-5-5` | hidden tests (never sees the gold) |
| `CTF_SOLVER_MODELS` | `anthropic:claude-sonnet-5-5` + `CTF_CROSS_SOLVER` if `OPENROUTER_API_KEY` is set | comma list; blind solvers from instruction.md (fairness evidence) |
| `CTF_CROSS_SOLVER` | `openrouter:openai/gpt-5` | a solver from a different model family than the gold/test writers (check the id exists on OpenRouter) |
| `CTF_PROBE_MODEL` | `anthropic:claude-haiku-5-5` | one-shot difficulty probe (should FAIL) |
| `CTF_BENCH_MODEL` | `anthropic/claude-haiku-5-5` | required benchmark model (harbor `-m` syntax) |

## Run

```bash
# 0. smoke test: one slot, no containers (fast, cheap)
python main.py generate --repo-dir work/click --base-commit $BASE --n 5 --only-slot 0 --no-container --out scratch_tasks

# 1. full batch: 5 slots -> generated_tasks/ + container self-check + pipeline_run.json
python main.py generate --repo-dir work/click --base-commit $BASE --n 5 --out generated_tasks

# 2. (re)run the organizer self-check alone
python main.py selfcheck generated_tasks/* --evidence evidence

# 3. hardness: k=3 rollouts of the benchmark model -> trajectory/<iid>/<model>/rollout_N/
python main.py bench generated_tasks/*

# 3b. validate packages from ANY producer (our generator or the team SDK); see VALIDATION.md
python main.py validate generated_tasks/* --repo-dir work/click [--llm] [--container]

# 4. whole-submission check (run last, on the exact folder you zip)
python vendor/innodata_kit/validate_submission.py .
```

**Difficulty knobs.** A valid task that the one-shot probe (small benchmark-family model) solves is *hardened*
instead of discarded: 1–2 requirements that interact with existing click behavior are appended (old requirements
stay verbatim), the gold is rewritten from base, the validated tests are extended, and every gate re-runs
(`--harden-rounds`, default 2). Each slot collects `--valid-per-slot` valid candidates (default 2); with harbor +
Docker available, each candidate gets ONE rollout of the real benchmark harness (terminus-2 + claude-haiku-5-5)
and the slot keeps the hardest (`--no-agent-select` to pick by the one-shot probe only). Fast profile for a live
demo: `--only-slot N --valid-per-slot 1 --harden-rounds 0 --no-agent-select`.

**Speed / robustness knobs.** Slots run in parallel (`--workers`, default 5; lower it if you hit rate limits).
Model responses are streamed: a request that is silent for `CTF_LLM_IDLE_TIMEOUT` s (default 90) or exceeds
`CTF_LLM_DEADLINE` s (default 600) is abandoned and retried (up to 5 attempts, exponential backoff, honours
`retry-after` on 429). Failed calls are still written to `llm_calls.jsonl` and counted in `pipeline_run.json`.

A **fresh batch** for the live demo: `--seed 1 --only-slot 2` (different slot assignment, one task, end to end).

LLM responses are cached in `.ctf_cache/` keyed by (model, prompt, temperature, variant): a re-run with the
same seed reproduces the same packages without new spend; delete the cache for fresh samples.

## Outputs

| Path | What |
|---|---|
| `generated_tasks/<instance_id>/` | Harbor packages (task.toml, instruction.md, solution/, tests/, environment/Dockerfile) |
| `pipeline_run.json` | per-task wall time, model calls, attempts, tokens (all attempts in a slot are charged to its task) |
| `runs/<id>/llm_calls.jsonl` | raw audit log: one line per model call with provider-reported usage |
| `runs/<id>/reports/<iid>.json` | every gate's result per candidate, accepted or rejected |
| `runs/<id>/evidence/` | `check_structure.txt`, `selfcheck.txt`, harbor oracle/nop/mutation run dirs |
| `runs/<id>/summary.json` | funnel (proposed → duplicate → not novel → gate-rejected → accepted) + per-task metrics |
| `trajectory/`, `bench_summary.json` | benchmark rollouts and resolve@3 distribution, infra failures listed separately |

## Gates

Local (fast, before any container): **L1** structure · **L2** fairness audit (every asserted fact must be in
instruction.md; spec auto-repaired once) · **L2b** requirement coverage (every numbered behavior has ≥1 test,
checked from `# R<n>` comments; missing ones auto-added once) · **L3** interface (tests only use declared new
symbols) · **L4** F2P/P2P on a curated regression set (test files that exercise the touched modules) **plus the
whole upstream suite under the gold** (not shipped; catches collateral breakage) · **L5** determinism · **L6**
mutation (AST mutants of the gold + LLM near-miss bugs must be killed; tests auto-strengthened ≤2 rounds) ·
**L7** a blind strong solver must pass (solvable from text) — with a cross-vendor solver configured we also report
whether a model family that wrote neither gold nor tests agrees with them — and the weak probe ideally fails (hard).

Gold self-check loop (`CTF_GOLD_REPAIRS`, default 2): after writing the gold, the pipeline checks that every SEARCH/REPLACE edit applied, the changed files parse, and the existing regression tests of the touched modules still pass; problems (with the pytest output tail and the gold's own diff) are sent back for a targeted repair. The hidden feature tests are never shown to the gold writer, so gold and tests stay independent.

How we know the gold is correct: "correct" means "satisfies instruction.md". Evidence = gold and tests written
independently from the spec agree (L4); a blind solver from another model family agrees too (L7); every spec
behavior is tested (L2b) and every tested fact is in the spec (L2); the whole upstream suite stays green (L4);
the organizer grader scores it 1.0 in the container.
Container (authoritative): organizer `check_structure.py`, `selfcheck.sh` (oracle 1.0 / nop 0.0), and one
corrupted gold run through the oracle (reward must drop below 1.0).

## Disclosure / reused components

- `vendor/innodata_kit/` — organizer-supplied files used unchanged: `grade.py`, `parser.py`, `test.sh` (copied
  verbatim into every package, as the kit specifies), `check_structure.py`, `selfcheck.sh`,
  `validate_submission.py`, and the example task. `selfcheck_portable.sh` is `selfcheck.sh` with one line changed
  (GNU-only `find -printf` replaced by Python) so it runs on macOS.
- The pipeline code was written with an AI coding assistant during preparation and the event.

## Limitations (keep this section honest at submission time)

- The local inner loop runs pytest with the host Python; the container uses Python 3.12. Use 3.12 locally.
- Novelty evidence relies on GitHub issue/PR search + an LLM judgment; it can miss features discussed elsewhere.
- Surviving AST mutants may be semantically equivalent; they are listed, not auto-classified.
- `CTF_NETWORK_MODE` defaults to `public` because the benchmark agent needs egress.
