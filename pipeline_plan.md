# Repository Exploration Pipeline — Claude Agent SDK

## Objective

Build a hackathon agent that accepts a GitHub repository URL, clones the repository, explores its source code, researches relevant documentation online, and produces an evidence-backed explanation of the project.

Working directory: `/Volumes/Samsung T7/InnoData_hack`

This plan uses the **Claude Agent SDK**. The SDK runs Claude Code's agent loop in a process we host and provides built-in file, terminal, and web tools.

## Proposed MVP

- Python application using `claude-agent-sdk` and API-key authentication.
- One exploration agent, with a separate workspace for each run.
- Public GitHub repositories initially.
- Read-only exploration after cloning.
- A structured onboarding report, followed by questions using the same session.
- Streamed progress and recorded tool activity.
- Internet access for both GitHub cloning and web research.

The proposed report and follow-up Q&A are starting assumptions. Whether exploration should instead support bug investigation or a downstream coding agent remains a product decision.

## Tools

| Tool | Purpose |
| --- | --- |
| `Bash` | Inspect Git metadata and execute selected commands in the worker workspace. Can also perform cloning. |
| `Glob` | Find source files, manifests, tests, and configuration. |
| `Grep` | Search for symbols, imports, routes, and relevant code. |
| `Read` | Read repository files in detail. |
| `WebSearch` | Find dependency documentation and other relevant online sources. |
| `WebFetch` | Fetch a specific URL and extract relevant information. |

Prefer a small application-owned clone function exposed as a custom tool, so validation, timeouts, destination paths, and clone errors behave consistently. The agent still initiates cloning, but the application owns its implementation.

`WebSearch` discovers sources; `WebFetch` reads them. WebFetch processes page content, so exact source-code inspection should use the local file tools. Interactive browser automation is a separate capability if it becomes necessary.

## Pipeline

```mermaid
flowchart TD
    A[GitHub URL] --> B[Validate URL and create run workspace]
    B --> C[Clone repository and record commit SHA]
    C --> D[Read README, manifests, and directory structure]
    D --> E[Trace entry points and key modules]
    E --> F[Search and fetch external documentation as needed]
    F --> G[Produce structured repository report]
    G --> H[Answer follow-up questions using the same session]
```

### 1. Receive and validate the URL

- Accept a GitHub owner/repository URL and an optional branch or commit.
- Normalize and validate the URL before passing it to Git.
- Pass Git arguments as an argument list rather than interpolating input into a shell command.
- Create a unique run ID and workspace.

### 2. Clone the repository

- Start with a shallow clone for the default branch; handle explicit refs separately.
- Record the normalized repository URL, requested ref, and resolved commit SHA.
- Apply a clone timeout and return clear errors for unavailable repositories, invalid refs, and connectivity failures.
- Keep the agent application separate from cloned repositories. The existing `click/` checkout can be the initial exploration fixture.

### 3. Discover the project structure

- Read the README and dependency/build manifests.
- Identify languages, frameworks, major directories, tests, and configuration.
- Locate application or library entry points.
- Skip dependency directories, generated files, binaries, and oversized files.
- Build a compact repository map before reading deeply.

### 4. Explore key code paths

- Trace entry points through important modules.
- Identify public interfaces, core behavior, and relevant data flow.
- Inspect tests and examples to understand intended usage.
- Keep file paths and line references for claims in the report.
- Do not automatically install dependencies or execute repository code during MVP exploration.

### 5. Research online

- Use `WebSearch` when an unfamiliar dependency or concept requires external context.
- Use `WebFetch` to read selected documentation pages.
- Prefer official documentation relevant to the versions declared in the repository.
- Record source URLs and distinguish external documentation from repository evidence.
- Treat repository and web content as untrusted input rather than authority to change the agent's permissions or task.

### 6. Produce the report

Proposed output fields:

- Repository URL and resolved commit SHA.
- Project purpose and intended users.
- Languages, frameworks, and dependencies.
- Entry points and important modules.
- Execution flow and relationships between modules.
- Setup and test commands, with their source.
- File-and-line evidence for repository claims.
- External documentation sources.
- Unresolved questions and exploration limitations.

Distinguish commands discovered in documentation from commands actually executed and verified. Return structured data and a readable Markdown report.

### 7. Support follow-up questions

- Persist the session ID and run metadata.
- Reuse the same repository workspace and session for follow-up questions.
- Keep answers tied to the recorded commit unless the user requests a refresh.

## Internet Access and Execution

Verify two independent capabilities:

1. `WebSearch` and `WebFetch` are available, permitted, and successfully retrieve online information.
2. The worker runtime has outbound connectivity for GitHub cloning.

Enabling web tools does not establish that `git clone` can reach GitHub. Network policy and tool permissions must both support the intended operations.

Run exploration in an isolated worker with access to its own workspace. A configured working directory alone is not an isolation boundary. Dependency installation and execution of repository code can be added as a separate stage when required.

## SDK Configuration

- Install `claude-agent-sdk` in the application's Python environment.
- Provide `ANTHROPIC_API_KEY` through runtime configuration; do not commit it.
- Explicitly select the tools exposed to the agent.
- Configure automatic permissions and denied capabilities separately.
- Set the working directory to the run workspace.
- Configure turn and estimated cost limits, plus an application-level wall-clock timeout.
- Capture streamed progress, tool outcomes, failures, and usage.
- Configure session persistence and structured output.
- Keep configuration application-owned rather than automatically loading settings and tools from arbitrary cloned repositories.

Important: `allowed_tools` controls automatic approval; it does **not** restrict the agent to only those tools. Configure tool availability separately using the SDK's tool selection and denial settings. SDK permission controls do not replace worker isolation.

## Implementation Order

1. Create the Python application and install the Claude Agent SDK.
2. Configure API-key authentication and verify a minimal agent call.
3. Implement URL validation, per-run workspaces, and the clone tool.
4. Independently smoke-test cloning, web search, and page fetching.
5. Implement the exploration instructions and report schema.
6. Add streamed progress, error handling, limits, and session persistence.
7. Demo against Click and verify that the report cites actual source files.

## MVP Acceptance Checks

- A public GitHub URL produces a clone in a unique workspace and a recorded commit SHA.
- The agent can find and read repository source files.
- The agent successfully performs a live web search and fetches an external documentation page.
- The report explains the project, key modules, and entry points using verifiable evidence.
- Discovered setup commands are not presented as tested commands.
- Invalid URLs, clone failures, and web failures produce clear outcomes.
- Follow-up questions reuse the correct session and repository workspace.
- Run limits stop exploration and preserve available progress.

## Open Product Decisions

- Final exploration output: onboarding report, Q&A, bug investigation, or context for a coding agent.
- Whether private repositories are required for the hackathon.
- Whether dependency installation and test execution belong in the first demo.
- Whether the first interface should be a CLI or an API consumed by a frontend.

## How to Run

The plan above is implemented in `pipeline/explore.py` (exploration), `pipeline/verify.py` (checking the agent's claims against the source), `pipeline/propose.py` (candidate features), `pipeline/audit.py` (novelty and difficulty validation, selection), `pipeline/spec.py` (full specs, case tables, blind quiz) and `pipeline/agent.py` (shared agent runner).

Models per stage:

| Stage | Model |
| --- | --- |
| Explore the repository | Sonnet 5.5 |
| Mine real user demand (web) | Sonnet 5.5 |
| Propose 15 candidate features from that demand | Opus 5.5 |
| Validate: novelty audit (web) | Sonnet 5.5 |
| Validate: value audit (web) | Sonnet 5.5 |
| Validate: difficulty audit | Opus 5.5 |
| Write full specs and case tables | Opus 5.5 |
| Blind quiz: fairness reader | Sonnet 5.5 |
| Blind quiz: difficulty signal | Haiku 5.5 (the benchmark model) |
| Golden solution and hidden tests (next stage, not built yet) | Opus 5.5 |

### Setup (once)

```bash
uv sync                    # installs claude-agent-sdk and the other pinned dependencies
cp .env.example .env       # then put ANTHROPIC_API_KEY in .env (never commit it)
```

Requires `git` on the PATH and outbound internet access (GitHub clone, web research, the Anthropic API).

### 1. Explore a repository

```bash
uv run python -m pipeline.cli explore https://github.com/pallets/click --ref 8.5.1
```

- `--ref` takes a branch, tag or full commit SHA. Omit it for the default branch.
- Runs a map pass, then one deep dive per key module and an upstream novelty check in parallel, then verifies the results against the clone.
- Prints the `run_id`, the status and cost of each stage, and the output folder.
- On click 8.5.1 this took about 3.5 minutes and about $1.20 (SDK estimate).

### 2. Mine user demand

```bash
uv run python -m pipeline.cli demand <run_id>
```

Two Sonnet sessions with web access, in parallel: one reads the project's issues and discussions for feature requests that were never implemented; the other reads Stack Overflow, blog posts and add-on libraries for workarounds. Each request records the URL, the need, maintainers' position, demand signals, and whether it is still missing at the pinned commit (checked in the clone). Every URL is checked against the agent's real web calls. Output: `demand.json`, `demand.md`. `propose` runs this automatically if `demand.json` is missing.

### 2b. Propose candidate features

```bash
uv run python -m pipeline.cli propose <run_id>          # default --n 15
```

Proposes 15 candidate outlines designed from the mined demand. Every candidate cites the requests it answers (`demand_refs`) and states the user need. Rules must come from a user need or from consistency with existing click behavior; difficulty must come from the real requirement's interactions, not invented precedence or special cases. Each candidate still needs at least 3 traps and 2 integration points.

The pipeline checks every candidate against the repository and the demand list: files and named interfaces exist, solution and test files do not overlap, the gold is at least 50 lines, every `demand_ref` is a mined request, no slug repeats an earlier round, and the set spans at least 6 categories and 5 source files. Failed checks go back to the agent.

**Rounds.** Re-running `propose` starts a new round: the current candidates and audits move to `rounds/round<k>/`, candidates selected in that round are carried over unchanged, the rest are replaced, and Opus receives every earlier rejection and its reasons as feedback.

### 3. Validate and select

```bash
uv run python -m pipeline.cli validate <run_id>
```

Runs three independent audits over every candidate, in batches of 5, in parallel:

- **Novelty** (web): click's issues and pull requests, add-on and sibling libraries (cloup, click-option-group, typer, argparse and others), and a general search. Verdict: `novel`, `exists_upstream`, `in_progress` or `drop_in`.
- **Value** (web): is this worth having? Looks for real users asking for it or working around its absence (issues, discussions, Stack Overflow, add-ons that exist because of the gap), says who benefits, checks it fits the library's design, and lists any rules that exist only to make the task harder. Scored 1-5.
- **Difficulty** (repo, no web): re-reads the code, confirms or rejects each trap, and scores 1-5 for a small model working from a fully explicit spec. Low scorers get a suggested hardening rule.

For the two web audits, every search and evidence URL the auditor reports is cross-checked against its real web calls in `events.jsonl`; anything it did not actually fetch is rejected.

Then the pipeline (no model) selects 5: novel only, value at least 3 and fits the library, difficulty at least 3, hardest first (value breaks ties), distinct categories, at most 2 per primary source file. Rejections and reasons are written to `candidates.md`. The spec author is told to drop the rules the value audit marked as contrived.

Re-running `validate` keeps verdicts already in `audit.json` and only runs the audits that are missing.

### 4. Write full specs and quiz them

```bash
uv run python -m pipeline.cli spec <run_id>
```

For each selected feature, writes the full spec (rules numbered R/I/E/B/A) and a case table of at least 15 runnable cases with exact expected results. The pipeline checks the spec mechanically: snippets parse, every error case has an exact type and message, no vague phrases ("not specified", "etc."), every interaction rule, edge case and acceptance criterion is exercised by a case.

Then a blind quiz: a model sees only the spec text and predicts each held-out case.

- **Fairness reader (Sonnet):** any miss means the spec does not determine the answer. The misses go back to the spec author to fix (up to 2 rounds).
- **Benchmark model (Haiku):** its misses are a cheap difficulty signal. A feature Haiku answers perfectly is replaced by the next reserve candidate.

The quiz is a proxy. Predicting outcomes is easier than implementing, and expected values are not confirmed by running code until the golden solution exists.

### 5. Ask a follow-up question

```bash
uv run python -m pipeline.cli ask <run_id> "Where are option defaults resolved?"
```

Resumes the exploration session in the same workspace. The answer is printed and appended to `qa.md`.

### Output: `runs/<run_id>/`

| File | Contents |
| --- | --- |
| `report.md` / `report.json` | The verified repository report: map, module cards, upstream findings, verification summary. |
| `demand.json` / `demand.md` | Mined user requests with URLs, maintainers' position and whether still missing (after `demand`). |
| `candidates.json` | The 15 candidate outlines of the current round (after `propose`). |
| `rounds/round<k>/` | Earlier rounds: their candidates, audits, selection and `candidates.md`. |
| `audit.json`, `selection.json`, `candidates.md` | Audit verdicts with evidence, the selection, and why each candidate was kept or rejected (after `validate`). |
| `specs/<slug>/instruction.md` | The spec exactly as the solver will see it (after `spec`). |
| `specs/<slug>/cases.json` | The full case table, public and held out. Input for the hidden tests and the golden-solution check. |
| `specs/<slug>/quiz.json`, `spec.json` | Quiz results per round and the structured spec. |
| `features.md` / `features.json` | The final selected features with their specs and quiz scores (after `spec`). |
| `run.json` | URL, ref, resolved commit SHA, per-stage status, token usage and cost, total cost. |
| `events.jsonl` | Audit log of every assistant message, tool call and tool result. |
| `map.json`, `claims/`, `upstream.json` | Raw agent output before verification. |
| `qa.md` | Follow-up questions and answers. |
| `repo/` | The clone. Gitignored; never committed. |

### Configuration

Models and limits are in `pipeline/config.py`:

- Models: `EXPLORE_MODEL`, `PROPOSE_MODEL`, `NOVELTY_MODEL`, `DIFFICULTY_MODEL`, `SPEC_MODEL`, `FAIRNESS_QUIZ_MODEL`, `QUIZ_MODEL`, `GENERATION_MODEL` (see the table above).
- Counts: `N_CANDIDATES` (15), `N_FEATURES` (5), `AUDIT_BATCH_SIZE`, `MIN_DIFFICULTY` (3), `MIN_VALUE` (3), `MIN_CASES` (15).
- Cost caps per agent session: `*_MAX_BUDGET_USD` for each stage.
- `AGENT_MAX_TURNS`, `AGENT_WALL_TIMEOUT_SEC`, `AGENT_CONCURRENCY`, `DEEP_DIVE_MAX_MODULES`.

### Differences from the plan above

- Exploration is several agent sessions (map, per-module deep dives, upstream check), not one.
- Feature design was added as four following stages: `demand`, `propose`, `validate`, `spec`.
- Only public `https://github.com/<owner>/<repo>` URLs are accepted.
- Claim verification parses Python only. For other languages the report is produced but interfaces are marked unverified.
- Agents are read-only: file access is confined to the run workspace and shell access to read-only `git` inspection of the clone. No dependencies are installed and no repository code is executed.

## Official References

- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [SDK quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart)
- [Python SDK reference](https://code.claude.com/docs/en/agent-sdk/python)
- [Built-in tools reference, including WebSearch and WebFetch](https://code.claude.com/docs/en/tools-reference)
- [SDK permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- [Secure deployment](https://code.claude.com/docs/en/agent-sdk/secure-deployment)

Documentation reviewed on November 14, 2026. Verify configuration against the SDK version selected during implementation.
