# Run the agent pipeline

Run commands from the repository root. The current order is:

**Explore → Mine user demand → Propose candidates → Audit/select → Refine specs → Author tests/find regressions → Haiku implementation → OpenRouter reference implementation.**

Run each stage separately and check its output before continuing. Model calls use the
team's API allocations. This workflow currently produces drafts and candidate patches;
automated behavioral validation and final Harbor packaging are still unfinished.

## 0. Prepare your terminal and dependencies

On this Mac, the repository is on an external SSD. Keep the Python environment on the
internal drive to avoid macOS `._` metadata causing package installation failures.
Run these exports again when opening a new terminal:

```bash
cd "/Volumes/Samsung T7/InnoData_hack"
export PATH="$HOME/.local/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$HOME/.local/share/venvs/innodata-hack"
export UV_LINK_MODE=copy
uv sync
```

If `uv` is not installed, install it first, then rerun the commands above:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create `.env` only if it does not already exist:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

Fill in `.env` locally with the team-provided `ANTHROPIC_API_KEY` and
`OPENROUTER_API_KEY`. `OPENROUTER_REFERENCE_MODEL` optionally overrides the reference
model. The application loads `.env` automatically; do not paste keys into commands,
logs, source files or submissions.

The commands below use `uv run --no-active` to use the configured project environment
and suppress warnings about another active `.venv`. A similar warning from `uv sync`
means it is ignoring that other environment, not that installation failed.

## 1. Explore the repository

```bash
uv run --no-active python -m pipeline.cli explore https://github.com/pallets/click --ref 8.5.1
```

Clones Click at the requested ref, maps the repository, explores key modules, and
researches upstream online. Uses the Claude Agent SDK with `EXPLORE_MODEL` from
`pipeline/config.py` (currently `claude-sonnet-5-5`). Internet access is required.

Outputs: `runs/<run_id>/report.md`, `report.json`, `map.json`, `upstream.json`,
`run.json`, `claims/`, `events.jsonl`, and the pinned `repo/` clone.

Wait for successful completion and a report before proceeding. Copy the printed run ID.

## 2. Select the run to use for every following stage

Set `PIPELINE_RUN_ID` to the exact run ID printed by exploration. This is an existing
example; replace the value when working with a new run:

```bash
export PIPELINE_RUN_ID="20261114-133919-pallets-click"
```

Use the same value throughout the workflow. Do not type angle-bracket placeholders
such as `<run_id>` into the shell: the shell interprets `<` as input redirection.

To list available run IDs and their recorded status:

```bash
uv run --no-active python - <<'PY'
import json
from pathlib import Path
for path in sorted(Path("runs").glob("*/run.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    print(path.parent.name, data.get("status"), "report:", (path.parent / "report.json").is_file())
PY
```

Optional follow-up question for the exploration agent:

```bash
uv run --no-active python -m pipeline.cli ask "$PIPELINE_RUN_ID" "Where are option defaults resolved?"
```

Resumes that run's exploration session and appends the answer to `qa.md`.

## 3. Design, audit and refine the features

### 3a. Mine user demand — Sonnet

```bash
uv run --no-active python -m pipeline.cli demand "$PIPELINE_RUN_ID"
```

Finds real user requests online and writes `demand.json` and `demand.md`.
Uses `DEMAND_MODEL`. This is a paid research stage. The proposal stage also mines
requests automatically if `demand.json` is absent.

### 3b. Propose candidates — Opus

```bash
uv run --no-active python -m pipeline.cli propose "$PIPELINE_RUN_ID" --n 15
```

Uses the repository report and user demand to propose a pool of candidates. Uses
`PROPOSE_MODEL` (currently `claude-opus-5-5`) and writes `candidates.json`.
This stage no longer writes the final `features.json` consumed by tests and coding.
Subsequent proposal rounds preserve earlier round artifacts and use audit feedback.

### 3c. Audit and select candidates — Sonnet and Opus

```bash
uv run --no-active python -m pipeline.cli validate "$PIPELINE_RUN_ID"
```

Audits novelty and user value with Sonnet, difficulty with Opus, and selects features
using application rules. Writes `audit.json`, `selection.json`, and `candidates.md`.
This command validates feature ideas; it does not execute regression tests or verify
candidate implementations. Inspect selection and rejection reasons before continuing.

### 3d. Refine selected specifications and quiz them — Opus, Sonnet and Haiku

```bash
uv run --no-active python -m pipeline.cli spec "$PIPELINE_RUN_ID"
```

Writes full specifications and case tables with Opus, then uses independent blind
readers for fairness and difficulty signals. May replace failed or too-easy features
with reserves. Expected case values and model quiz answers are not execution evidence.

Outputs: `specs/<slug>/instruction.md`, `cases.json`, `spec.json`, `quiz.json`, plus
`features.md` and `features.json` in the run directory. These are the inputs for the
test agent and both coding agents. Inspect retained, dropped and blocked features.
Rerunning specification authoring replaces the feature handoff; keep tests and coding
attempts aligned with the exact specification snapshot they consumed.

To read the finalized features on macOS:

```bash
open "runs/$PIPELINE_RUN_ID/features.md"
```

## 4. Generate feature-test drafts and find existing regression tests — Opus

```bash
uv run --no-active python -m pipeline.cli tests "$PIPELINE_RUN_ID"
```

Loads `test_agent_rules.md` and the generated feature plan. Uses `TEST_MODEL` (currently `claude-opus-5-5`).
It performs two tasks:

1. Creates new pytest test drafts for each feature, mapped to its acceptance criteria.
2. Reports whether it found existing regression tests, with their folder and file paths.

Outputs are saved in a new `runs/$PIPELINE_RUN_ID/feature_tests/attempt_N/`:

```text
report.md                         summary, regression locations, draft status/blockers
regression_tests.json             found/not-found and existing test paths
summary.json                      per-feature status
rules.md                          rules snapshot
features_input.json               feature-plan snapshot
<feature-slug>/draft.json          source, criterion mappings and notes
<feature-slug>/test_patch.diff     generated test patch
<feature-slug>/files/tests/...     actual new Python test files
```

Specifications with unresolved ambiguities are reported as blocked. This command does
not execute tests or establish that regression tests pass. It does not yet collect final
Harbor test IDs or perform oracle/nop/mutation validation.

## 5. Implement features — Claude Haiku

Run Haiku for all proposed features:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" --agent haiku --execute
```

Uses `HAIKU_IMPLEMENTATION_MODEL = "haiku"` through the Claude Agent SDK. Each feature
gets an independent copy of the pinned repository. The agent reads
`implementation_agent_rules.md`, inspects source and existing tests, and returns source
changes. The application checks and applies the candidate patch in its own copy.

To run just one feature, set its exact slug from `features.json`:

```bash
export PIPELINE_FEATURE_SLUG="option-requires-conflicts"
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" \
  --agent haiku --feature "$PIPELINE_FEATURE_SLUG" --execute
```

Use either the all-features command or the single-feature alternative as needed;
running both authors that feature again in a new attempt.

Outputs: `runs/$PIPELINE_RUN_ID/coding/<feature-slug>/haiku/attempt_N/`.

## 6. Create reference implementations — OpenRouter

Run the reference agent for all proposed features:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" --agent reference --execute
```

Uses `OPENROUTER_API_KEY` from `.env` and `OPENROUTER_REFERENCE_MODEL` (default
`anthropic/claude-opus-4.6`). It independently implements the same proposals from the
same pinned commit, aiming for a complete reference implementation. It does not receive
Haiku's candidate or generated hidden tests. Model strength alone does not prove quality.

Single-feature alternative, using the slug selected in step 5:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" \
  --agent reference --feature "$PIPELINE_FEATURE_SLUG" --execute
```

Outputs: `runs/$PIPELINE_RUN_ID/coding/<feature-slug>/reference/attempt_N/`.

## Alternative: run both coding agents with one command

After refining the specifications and authoring tests, this replaces the separate commands in
steps 5 and 6:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" --agent both --execute
```

For one feature only:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" \
  --agent both --feature "$PIPELINE_FEATURE_SLUG" --execute
```

The orchestrator runs the roles serially for each feature. It preserves separate
workspaces and previous attempts. Do not also run steps 5 and 6 unless you intend to
create and pay for additional attempts.

## Prepare coding workspaces without calling models

Omit `--execute` to prepare jobs and inspect their requests before live authoring:

```bash
uv run --no-active python -m pipeline.cli code "$PIPELINE_RUN_ID" --agent both
```

This creates pinned clones and `request.json` files but makes no paid model calls.
It reports `prepared`; a later `--execute` invocation creates a new attempt rather
than resuming the prepared attempt.

## Reading coding-agent results

Each coding attempt contains:

- `result.json`: role, model, pinned commit, status and compatibility checks.
- `request.json` and `rules.md`: exact proposal, prompts and implementation rules used.
- `draft.json`: the returned source changes or blockers, when available.
- `patch.diff`: the candidate source patch after successful checks.
- `repo/`: that attempt's independent repository copy; gitignored.
- `usage.json`: reported provider usage when available.
- Haiku: `events.jsonl`. OpenRouter: `request_N.json`, `response_N.json`, or sanitized
  `error_N.json` if an HTTP request fails.

| Status | Meaning |
| --- | --- |
| `prepared` | Workspace and instructions exist; model has not run. |
| `awaiting_validation` | Candidate patch was authored and applied; behavioral checks remain pending. |
| `blocked` | Compatibility or specification conflict needs resolution. |
| `invalid` | Draft or workspace checks rejected the candidate. |
| `error` | The provider/session failed; inspect recorded details. |

`accepted: false` and checks marked `not_run` are expected in the current scaffold.
Patch application and Python syntax checks do not prove backward compatibility.

## Validation and packaging are the next stage, not completed by these commands

Before accepting either implementation, a future execution stage must establish a
passing base, execute new feature tests and existing regression tests against the same
candidate, run the existing suite, and preserve actual results. Any required regression
failure must block acceptance; fix the implementation, never weaken the tests.

`pipeline.cli generate --n 5` remains a stub. The commands above do not yet produce
validated Harbor packages or official benchmark trajectories. Do not describe these
authoring runs as oracle/nop/mutation or benchmark evidence.

## Offline checks for the pipeline code

```bash
uv run --no-active python -m unittest discover -s tests -p 'test_*.py' -v
```

Uses temporary Git repositories and mocked providers to check pipeline behavior.
It does not spend model credits or validate generated feature implementations.

## Guidance for agents reading this repository

Read `guidelines.md`, `test_agent_rules.md`, and `implementation_agent_rules.md` for
the governing requirements. Keep feature plans, tests, candidate attempts and evidence
associated with the correct run and pinned commit. Commands in this document are
instructions, not proof that a stage has been executed successfully.
