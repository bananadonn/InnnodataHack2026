# Project memory

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
