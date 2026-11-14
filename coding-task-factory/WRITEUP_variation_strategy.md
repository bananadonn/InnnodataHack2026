# Variation strategy (draft — fill the bracketed parts with real run data)

## The idea in one sentence
The factory decides *what kind* of task to build before any model writes a word: each of the five tasks is
assigned a different **slot** = capability area × behavioral shape × integration depth, so the batch cannot
collapse into rewordings, and the model's job is only to fill the slot with a concrete, novel feature.

## The three axes

| Axis | Values (click) | Why it changes the task substantively |
|---|---|---|
| **Capability area** — which part of the system the feature extends | parsing semantics · parameter types · help formatting · shell completion · CliRunner testing utilities · Context/default resolution · terminal UI helpers · command composition | Different modules, different data structures, different existing tests to protect (each slot gets its own curated P2P set) |
| **Behavioral shape** — what kind of logic the solver must write | validation rule set with precedence · transformation with exact formatting · stateful/ordering behavior · interaction between ≥2 existing features · opt-in configuration with precedence | Different failure modes: precedence bugs vs. formatting bugs vs. accumulation bugs vs. integration bugs |
| **Integration depth** | library API · CLI behavior via CliRunner · both | Changes how much of the call path the solver must understand |

Five slots use five distinct capability areas and five distinct shapes (`factory/plan.py`; `--seed` re-samples).
Capability areas are bound to real module paths and dropped if the module does not exist (grounding).

## How the pipeline decides what to generate
1. Plan slots (deterministic, seeded).
2. For each slot the spec model proposes 3 candidates, given the focus modules in full and outlines of the rest.
3. Candidates are filtered by a lexical near-duplicate check against already-accepted tasks, then by a
   **novelty** gate (GitHub search of issues/PRs incl. merged after the base commit + LLM judgment over source).
4. Survivors go through gold → tests → gates L1–L7. A valid task that a small model solves one-shot is kept only
   as a fallback; the slot is retried with feedback asking for more interacting rules (hardness without vagueness).

## Why this yields hard *and* fair tasks
- Hardness comes from **precise, interacting rules** that require reading existing code — never from omission.
- Fairness is enforced mechanically: an LLM audit lists every test-asserted fact missing from the spec and the
  spec is repaired; a blind solver that sees only `instruction.md` must pass the hidden tests.
- Tests are attacked before shipping: AST mutants + targeted near-miss bugs; surviving bugs drive test repair.

## Results [fill in]
| instance_id | capability | shape | F2P | P2P | kill rate (before→after) | probe | resolve@3 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Funnel: [proposed → duplicate → not novel → rejected by gate → accepted]. Cost per valid task: [from pipeline_run.json].

## Team contributions [fill in]
