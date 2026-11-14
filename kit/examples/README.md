# Example task — what one task package looks like

This folder holds **one complete, worked example** so you can see exactly what your pipeline must
produce. It is a deliberately tiny, **synthetic** task on a made-up library (`toycorp/stringkit`) —
**not** one of the supplied repos. It is here to show the *shape* of a task, not to be copied or
submitted.

> **Do not submit this task.** It is a toy on a repo you won't use. Build your own tasks on the
> supplied repos (`repos/README.md`). This example intentionally does **not** show you how to make a
> task *hard* or how we grade your submission — only what a well-formed package contains.

## The task in one line

> Add a `truncate(text, limit, suffix="…")` helper to the `stringkit` library.

## Read it as input → output → grading

| You're looking at | File(s) | What it is |
|---|---|---|
| **The solver's INPUT** | `instruction.md` | The spec — the *only* description the solver gets. No tests, no gold. |
| | `environment/Dockerfile` | The repo at its base state + toolchain. (Here the toy repo is embedded; a real task clones a pinned `base_commit`.) |
| **The gold OUTPUT** | `solution/patch.diff` | The reference implementation — a correct answer, as a unified diff. |
| | `solution/solve.sh` | Applies the gold (`git apply patch.diff`). Used by the **oracle** baseline. |
| **How it's GRADED** | `tests/test_patch.diff` | Adds the feature tests (`tests/test_truncate.py`). |
| | `tests/fail_to_pass.json` | Tests that **fail at base** and **pass with the gold** — the feature. |
| | `tests/pass_to_pass.json` | Existing tests (`test_slugify`) that must **stay green** — the regression guard. |
| | `tests/test.sh` | Verifier entry Harbor runs → creates `/logs/verifier`, calls `grade.py`. |
| | `tests/grade.py`, `parser.py`, `run_script.sh` | Run the suite, parse results, write `reward.json`. |
| **Metadata** | `task.toml` | `instance_id`, `base_commit`, `network_mode`, env + verifier config. |

## What makes it a valid task (the two baselines)

The whole package is designed so Harbor's two baselines land exactly here:

- **oracle** (gold applied) → every `fail_to_pass` passes **and** every `pass_to_pass` passes → **reward 1.0**.
- **nop** (untouched base) → the feature is absent so `fail_to_pass` fails, while `pass_to_pass` stays green → **reward 0.0**.

Those two facts are the **fairness**, **discrimination**, and **regression** evidence the brief asks
for. Your self-check (`harness/selfcheck.sh`) runs these two baselines for every package you generate.

## Try it

```bash
# format lint (offline)
harness/check_structure.py examples/toy__stringkit-0001-truncate

# oracle=1.0 / nop=0.0 soundness (needs Docker + Harbor; no model key)
SELFCHECK_OUT=./sc harness/selfcheck.sh examples/toy__stringkit-0001-truncate
```

See `docs/harbor_task_interface.md` for the full field-by-field contract.
