Follow these submission formats and guardrails from the hackathon participant kit.

SOURCE DOCUMENTS

The kit is located at:
/Volumes/Samsung T7/Innodata Hackathon/Track 1 - Coding

Read these for the exact contracts:
- docs/harbor_task_interface.md
- docs/validation_protocol.md
- SUBMISSION.md
- JUDGING.md
- benchmark/benchmark_guide.md
- examples/ — complete worked example

TASK PACKAGE FORMAT

Each task must have this structure:

generated_tasks/<instance_id>/
├── task.toml
├── instruction.md
├── environment/
│   └── Dockerfile
├── solution/
│   ├── solve.sh
│   └── patch.diff
└── tests/
    ├── test.sh
    ├── grade.py
    ├── run_script.sh
    ├── parser.py
    ├── test_patch.diff
    ├── fail_to_pass.json
    └── pass_to_pass.json

FILE REQUIREMENTS

instruction.md
- The feature specification shown to the solver.
- Define exact public interfaces, defaults, return values, behavior,
  edge cases, ordering, errors, and backward compatibility.
- Include examples and acceptance criteria.
- Everything hidden tests depend on must be stated.
- Do not reference hidden test IDs or the gold solution.

task.toml
- Follow the kit’s exact Harbor configuration.
- metadata.name and metadata.instance_id match the task folder name.
- source_repo identifies the upstream repository.
- base_commit is a real, full 40-character commit SHA.
- Record the correct license and programming_language.
- For Click: source_repo = "pallets/click";
  programming_language = "python".
- Set docker_image = "" so Harbor builds the Dockerfile.
- Valid network_mode values: "no-network", "allowlist", "public".
  "none" is invalid.
- Declare oracle baseline reward 1.0 and nop baseline reward 0.0.
- The kit targets Harbor 0.25.x.

environment/Dockerfile
- Must be included in every task.
- Build the repository at the declared base_commit.
- Install the required toolchain and dependencies.
- Leave the repository as a usable Git working tree.
- Pin dependencies for reproducibility.
- Do not depend on private or local-only images.

solution/solve.sh and solution/patch.diff
- Apply the correct reference implementation.
- Gold implementation and test patch must not edit the same files.

tests/test.sh
- Harbor’s verifier entry point.
- Create /logs/verifier and invoke grade.py.

tests/grade.py
- Apply the hidden test patch, execute tests, parse results,
  and write reward.json and grading_details.json.
- Use the supplied example and interface contract.

tests/run_script.sh and tests/parser.py
- Run the selected tests and parse their actual results.
- Parsed test IDs must exactly match the JSON test-ID lists.
- Avoid aborting the test runner because a named test path is absent.

tests/test_patch.diff
- Adds feature tests and necessary test support.
- Keep its file paths separate from those changed by the gold.

tests/fail_to_pass.json
- JSON array of feature test IDs.
- These tests fail at base and pass with the gold.

tests/pass_to_pass.json
- JSON array of relevant, pre-existing regression test IDs.
- These tests pass both at base and with the gold.

GRADING CONTRACT

- Gold: all feature and regression tests pass → reward 1.0.
- Base: feature tests fail; regression tests pass → reward 0.0.
- Any required regression test fails → reward 0.0.
- Otherwise, partial reward is feature tests passed / feature tests total.

QUALITY GUARDRAILS

- Generate five substantively different tasks from one supplied repo.
- Allowed repos: pallets/click, colinhacks/zod,
  open-source-parsers/jsoncpp.
- Variation must concern capabilities, behavior, rules, or interactions;
  renaming and rewording are insufficient.
- Features must extend actual repository functionality.
- Features must be novel against live upstream, including changes
  merged after the pinned commit.
- Features must not be drop-ins from a well-known library.
- Confirm the base repository builds and its existing suite passes.
- Select relevant existing regression tests programmatically.
- Tests must assert observable specified behavior, not a particular
  algorithm, internal helper, or implementation structure.
- Corrupting the gold must make feature tests fail.
- Scoring must be deterministic and execution-based.
- Keep hidden tests and the gold inaccessible to the solver.
- Do not hand-fix generated packages after generation; fix the
  pipeline and regenerate.
- Report failures, retries, manual interventions, reused components,
  and incomplete functionality honestly.
- Never fabricate validation, benchmark, novelty, or usage evidence.

SUBMISSION FORMAT

Submit one ZIP named TeamName_Track1.zip.

Suggested internal organization:

TeamName_Track1/
├── README.md
├── pipeline/
├── generated_tasks/
│   └── <five task-package folders>
├── validation_evidence/
├── pipeline_run.json
├── generation_logs/
├── variation_writeup.md
└── trajectory/                 # Optional benchmark evidence

The overall folder organization is suggested; the task-package
structure and benchmark trajectory layout are prescribed.

Include:
- Pipeline source, pinned dependencies, and exact run instructions.
- Raw generated task packages.
- Per-task self-check evidence.
- Resource telemetry backed by usage exports or raw run logs.
- A 1–2 page explanation of meaningful variation.
- Each member’s contribution.
- Disclosures of reused code, manual interventions, and limitations.

PIPELINE_RUN.JSON FORMAT

{
  "pipeline": "your-team/version",
  "tasks": [
    {
      "instance_id": "<task-folder-name>",
      "model": "<model-used>",
      "wall_seconds": 142,
      "model_calls": 6,
      "attempts": 2,
      "n_input_tokens": 180000,
      "n_output_tokens": 9000,
      "n_cache_tokens": 150000
    }
  ]
}

- One entry per submitted task.
- attempts means generate-and-check cycles needed for that task.
- Use actual tooling-reported figures backed by auditable evidence.
- Preserve generation trajectories/logs.

BENCHMARK EVIDENCE, IF INCLUDED

Required layout at the submission’s top level:

trajectory/<instance_id>/<model>/rollout_N/
├── result.json
└── verifier/
    ├── reward.json
    └── grading_details.json

- Keep all k rollouts.
- Instance IDs must match submitted task packages.
- Rollouts must match the exact submitted task checksums.
- Confirm the actual model and agent in result.json.
- The Markdown guide prescribes terminus-2,
  anthropic/claude-haiku-5-5, and k=3.
- A section of the Word assignment says k=5; flag this conflict
  for organizer clarification.
- resolve@k means successful graded rollouts / graded rollouts.
- Exclude and rerun infrastructure failures, API errors, rate limits,
  and truncated responses; report them separately.
- Agent timeouts count as genuine misses.
- Benchmark agents need network access to their installation
  sources and model API.

SECRETS AND BUDGET

- API keys belong in environment variables.
- Never include secrets in source, logs, command-line arguments,
  or the submission ZIP.
- Organizer allocations: $100 OpenRouter + $100 Anthropic per team.
- Personal paid accounts and extra API spending are not allowed.

REQUIRED CHECKS

Run against the generated packages:

python3 harness/check_structure.py generated_tasks/*

SELFCHECK_OUT=./sc harness/selfcheck.sh generated_tasks/*

Run against the exact final submission folder or ZIP:

python3 harness/validate_submission.py <submission-folder-or-zip>

Structure/submission checks are offline.
Oracle/nop checks require Harbor and Docker, but no model key.
Passing these checks does not establish novelty, difficulty,
fairness, or meaningful variation.