# Judging criteria

Your submission is scored on **seven weighted dimensions totalling 100 points**, after a light pass/fail
**floor**. This is the full rubric we grade with — nothing about the weighting is withheld.

## Floor (before scoring)

A submission is scored as long as there is something to judge:
- the pipeline **runs** and emits **at least one package** in the Harbor interface (its `task.toml` parses), and
- the pipeline-level check produces a summary.

Only a submission that doesn't run, emits no parseable package, or produces no summary scores zero overall.
**Partial pipelines are scored** — a pipeline whose packages don't all pass is still judged on every
dimension it demonstrates; the shortfall shows up *inside* the dimensions (mainly reliability and difficulty),
not as a disqualification.

## The seven dimensions (100 pts)

| # | Dimension | Pts | What we assess |
|---|---|---:|---|
| 1 | **Reliability of generation** | **20** | First-pass **yield**: the fraction of your raw, unedited packages that pass every validation gate. The core factory signal. |
| 2 | **Fairness** | **15** | Specs are complete and implementable **from the text alone** — no hidden constants, unstated ordering, or tests asserting what the spec never says. |
| 3 | **Task difficulty** | **20** | Tasks are genuinely hard for the benchmark model — low **resolve@k** — while the gold still scores 1.0 (provably solvable). |
| 4 | **Meaningful variation** | **20** | Packages differ **substantively** (capability, behavior, integration), not by wording or names. |
| 5 | **Regression protection** | **10** | A curated set of existing tests exercises the touched modules and stays green under the gold (not a decorative whole-suite dump). |
| 6 | **Reproducibility & interface fidelity** | **5** | A re-run reproduces comparable results; packages follow the Harbor interface exactly (valid `task.toml`, self-contained Dockerfile, correct baselines, no leaks/junk). |
| 7 | **Efficiency** | **10** | How cheaply the pipeline produces a *valid* task — $ / attempts / tokens per valid task. |

Each dimension is scored as a fraction of its points: **0** (none) · **0.25** (weak) · **0.5** (adequate) ·
**0.75** (strong) · **1.0** (excellent).

## The validation gates (pass/fail, per package)

Yield (dimension 1) counts a package only if it clears **every** gate, unedited:

| Gate | Checks |
|---|---|
| Structure | required files present; `task.toml` parses |
| Name integrity | identity rides on behavior, not renamed identifiers |
| Novelty | the feature isn't already upstream (incl. merged just after your base commit) |
| Grounding | the task extends real modules of the repo, not an all-new orphan |
| Gold (oracle) | the reference implementation builds and scores reward **1.0** |
| Feature-absent (nop) | at the base repo the feature tests **fail** (the feature is genuinely missing) |
| Base health | the untouched repo builds and its existing suite is green |
| Mutation | corrupting the gold makes the feature tests fail — i.e. the tests actually bite |

## How dimensions are measured

- **Reliability (1), difficulty (3), efficiency (7)** are measured **mechanically** — yield from validating
  your raw output, difficulty from the resolve@k benchmark, cost from the per-valid-task figures.
- **Regression (5)** and **reproducibility / interface fidelity (6)** are checked by inspecting the curated
  test sets and re-running the pipeline.
- **Fairness (2)** and **variation (4)** are semantic, so we assess them with the help of an **LLM judge**
  that reads the generated batch and your writeup — whether specs are implementable from their text alone,
  and whether packages are substantively distinct (beyond a lexical near-duplicate check). The LLM judge is
  **advisory**: it informs a human score and can flag for review, but never decides a dimension on its own.

## Tie-break

Equal totals → we prioritize task validity & solvability, then evidence of difficulty, then the ability to
generate fresh valid tasks.
