# Project memory

## Hackathon requirements

- Read `guidelines.md` before planning, implementing, generating, validating, benchmarking, or packaging hackathon work. It preserves the participant-kit submission formats and guardrails supplied by the user.
- The participant kit is at `/Volumes/Samsung T7/Innodata Hackathon/Track 1 - Coding`. Consult its exact interface and validation contracts when implementing task packages; the relevant source documents are listed in `guidelines.md`.
- The pipeline uses the **Claude Agent SDK** and needs internet access for GitHub cloning, repository exploration, and upstream novelty research. See `pipeline_plan.md` for the initial exploration plan; the full hackathon scope also requires generating five substantively different task packages from one allowed repository.
- Preserve auditable generation logs and actual usage evidence. Fix generation failures in the pipeline and regenerate packages rather than hand-fixing generated outputs.
- Use only the organizer-provided allocations and keep secrets out of source, logs, command-line arguments, and submission artifacts.
- The benchmark rollout count is unresolved: the Markdown guide says k=3 and part of the Word assignment says k=5. Obtain organizer clarification before claiming a definitive requirement.

This file is persistent repository-level memory for future agent sessions.
