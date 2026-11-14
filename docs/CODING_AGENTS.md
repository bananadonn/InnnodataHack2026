# Coding agents

The coding stage has two independent roles for each proposed feature:

| Role | Entry point | Provider/model |
| --- | --- | --- |
| Candidate implementation | `pipeline.haiku_agent.implement_feature(run_id, feature_slug, execute=False)` | Claude Agent SDK, `HAIKU_IMPLEMENTATION_MODEL = "haiku"` |
| Reference implementation | `pipeline.reference_agent.create_reference(run_id, feature_slug, execute=False)` | OpenRouter, `OPENROUTER_REFERENCE_MODEL`, default `anthropic/claude-opus-4.6` |

The reference agent aims for a more complete, carefully reasoned implementation. Model
strength alone does not establish that it is correct or better than Haiku's candidate.
Both outputs must eventually be evaluated against the same specification and execution gates.
The Haiku coding stage is not the official Harbor benchmark and does not produce benchmark evidence.

## Module boundaries

- `coding_common.py`: source-change schema, pinned independent clones, prompt/rules snapshots,
  source-only path validation, Python syntax checks, patch generation and application checks.
- `haiku_agent.py`: Claude Agent SDK adapter, model configuration and session usage.
- `reference_agent.py`: OpenRouter HTTP tool loop, bounded repository reads, submission tool,
  raw responses and provider usage.
- `coding.py`: selects features and agents, runs them serially, reports blocked/failed jobs.
- `cli.py`: argument parsing and dispatch only.

## Prepare jobs

Use a run that already has `features.json` from `propose`:

```bash
uv run python -m pipeline.cli code 20261114-133919-pallets-click --agent both
```

This prepares workspaces and requests without calling either model. `--feature <slug>`
limits the command to one proposed feature. Every invocation preserves previous attempts.

## Author candidates

Configure the team keys in `.env` using `.env.example`. Keep credentials out of source,
request files, logs and command-line arguments. To change the reference model, set an explicit
OpenRouter model ID in `OPENROUTER_REFERENCE_MODEL`; no fallback to another model is configured.

```bash
uv run python -m pipeline.cli code 20261114-133919-pallets-click \
  --agent both --feature option-requires-conflicts --execute
```

`--execute` makes paid provider calls and sends the feature specification, rules and inspected
repository content to the respective provider. `--agent haiku` or `--agent reference` runs
only that role. The reference agent uses OpenRouter's tool-calling API directly, rather than
pretending that the Claude Agent SDK natively routes arbitrary models through OpenRouter.

## Outputs

```text
runs/<run_id>/coding/<feature-slug>/<haiku|reference>/attempt_N/
  repo/           independent pinned clone; gitignored
  rules.md        exact implementation-agent rules used
  request.json    feature, model, commit and prompts
  draft.json      structured candidate, or blockers (after a successful model result)
  patch.diff      candidate source patch (after successful draft checks)
  result.json     status, accepted=false, compatibility checks marked not_run
  usage.json     SDK or OpenRouter usage when available
```

Haiku additionally writes `events.jsonl`. OpenRouter writes `request_N.json` and
`response_N.json`, preserving actual model IDs and raw usage. Request files do not contain
authentication headers. Missing cost is recorded as incomplete, never represented as verified
zero spend. The reference loop stops before another request if cost reporting is unavailable.
HTTP failures save a sanitized `error_N.json` with the provider's error code and message.
Authentication headers and arbitrary provider metadata are not logged. Requests omit
`parallel_tool_calls`: Opus endpoints do not advertise that parameter, and requiring it
would filter them out when `require_parameters` is enabled.

Call, token, time and reported-cost limits bound reference authoring, though a paid request can
exceed a cost threshold before its usage is returned. Haiku uses the existing SDK's limits.

## Compatibility and isolation

Both agents load `implementation_agent_rules.md`. Each feature and role starts independently
at the run's pinned commit. Generated feature tests, sibling candidates and gold artifacts are
not copied into agent workspaces. Haiku has only `Read`, `Glob` and `Grep`; OpenRouter has
`list_files`, `read_file` and `submit_implementation`. Neither has a shell or direct write tool.
Agents inspect existing source and regression tests but do not execute project code or tests.
Repository reads are application-scoped; these policies
are not an operating-system sandbox. Live deployment still needs an isolated worker.

Agents submit complete source-file replacements as structured data. Only declared source
paths are allowed. Existing tests, test support, configuration files, traversal paths and
symlinks are rejected. The application creates the patch, checks that it applies, and applies
it only to that candidate's clone. The original exploration clone is untouched.

## What this scaffold does not claim

The coding stage currently authors candidates; it does not run the base suite, feature tests,
regression tests, full suite, Harbor checks or mutation checks. Syntax and patch checks are
not behavioral validation. Successful authoring produces `awaiting_validation`, never
accepted gold. A specification/compatibility conflict produces `blocked`.

The compatibility evidence contract requires a passing base, nonempty passing feature and
regression checks, a passing existing suite, and recorded execution evidence before acceptance.
Any regression failure blocks acceptance. A future execution stage must populate those results
from real runs, repair candidate implementations when needed, and compare reference quality.
The package-generation and submission-telemetry stubs remain separate future work.

## Offline verification

```bash
uv run python -m unittest discover -s tests -p 'test_*.py' -v
```

These tests use temporary repositories and mocked provider responses, without spending API credit.

## Provider references

- [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [OpenRouter Claude Opus 4.6 route](https://openrouter.ai/anthropic/claude-opus-4.6)
