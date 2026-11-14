# Project memory

Read [run_pipeline.md](run_pipeline.md) for ordered setup and commands for every agent,
output locations, and the current validation/packaging limitations.

## Hackathon requirements

- Read `guidelines.md` before planning, implementing, generating, validating, benchmarking, or packaging hackathon work. It preserves the participant-kit submission formats and guardrails supplied by the user.
- The participant kit is at `/Volumes/Samsung T7/Innodata Hackathon/Track 1 - Coding`. Consult its exact interface and validation contracts when implementing task packages; the relevant source documents are listed in `guidelines.md`.
- The pipeline uses the **Claude Agent SDK** and needs internet access for GitHub cloning, repository exploration, and upstream novelty research. See `pipeline_plan.md` for the initial exploration plan; the full hackathon scope also requires generating five substantively different task packages from one allowed repository.
- Preserve auditable generation logs and actual usage evidence. Fix generation failures in the pipeline and regenerate packages rather than hand-fixing generated outputs.
- Use only the organizer-provided allocations and keep secrets out of source, logs, command-line arguments, and submission artifacts.
- The benchmark rollout count is unresolved: the Markdown guide says k=3 and part of the Word assignment says k=5. Obtain organizer clarification before claiming a definitive requirement.

This file is persistent repository-level memory for future agent sessions.

## Test agent scope

- The test agent must read `test_agent_rules.md` at runtime. Its current two tasks are (1) create new executable tests for every generated feature, mapping tests to that feature's acceptance criteria, and (2) find the existing regression-test folder(s) in the pinned repository and report whether it found them and their paths.
- Current scope is authoring feature-test drafts and locating existing tests. Regression execution, final collected IDs, gold validation, mutation checks, and Harbor packaging are deferred and must never be reported as completed without execution evidence.
- `pipeline.cli tests <run_id>` consumes the proposal stage's `features.json` and `features.md` (also reads `feature.md` if present). Test artifacts and discovery reports live under `runs/<run_id>/feature_tests/attempt_N/`; keep previous attempts and the repository's existing tests unchanged.

## Implementation agent: compatibility is mandatory

- Read `implementation_agent_rules.md` when building or running the implementation stage. The user's primary requirement is that new features must not break or change existing behavior.
- New feature tests and existing regression tests must both pass. Any required regression failure blocks acceptance, even when all new tests pass. Repair the implementation, never weaken or alter existing regression tests.
- Establish a passing base, validate relevant existing regressions and the existing suite after implementation, and preserve actual execution evidence. Finding the regression folder is not evidence that regression tests passed.
- Block a feature whose specification requires incompatible behavior and report the conflict. The current generation stub does not yet enforce these gates.

## Two coding agents

- `pipeline/haiku_agent.py:implement_feature` uses Claude Haiku through the Claude Agent SDK. `pipeline/reference_agent.py:create_reference` uses a configurable advanced model through OpenRouter (default `anthropic/claude-opus-4.6`).
- `pipeline/coding.py` orchestrates the roles; `pipeline/coding_common.py` owns pinned workspaces, draft schemas, source-only checks and candidate artifacts. Keep agent logic out of `cli.py`.
- `pipeline.cli code <run_id>` prepares independent jobs without paid calls. `--execute` authors source candidates. Each feature and role starts from the same pinned commit in a separate clone and preserves previous attempts.
- Neither agent receives the other's candidate or generated hidden tests. Reference quality must be established through execution and review, not inferred from model strength. The Haiku authoring stage is separate from the official Harbor benchmark.
- Current coding stages scaffold candidate authoring only: regression, feature, full-suite and base-health execution remain pending. `accepted` stays false and outputs are not validated gold or final Harbor packages.
