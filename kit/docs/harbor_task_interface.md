# The Harbor task-package interface

This is the contract every package your pipeline emits **must** follow. The authoritative source is
[harborframework.com](https://www.harborframework.com/); this document is the practical summary you'll build
against, with the exact file layout and the fields that matter for grading.

> **Harbor version.** This kit targets **Harbor 0.25.x** — the file layout, `task.toml` fields, and
> verifier entry below match that line. Pin the same version in your environment (`pip install "harbor==0.25.*"`
> or the pin your event specifies) and validate against it; a package is only recognized as a task when it has
> the full structure (notably `tests/test.sh`) — an incomplete folder is misread as a dataset and won't run.

A single task is a directory named by its `instance_id`:

```
<instance_id>/
├── task.toml              # metadata + environment + verifier config (see below)
├── instruction.md         # the spec the agent/engineer sees — the ONLY description of the feature
├── solution/
│   ├── solve.sh           # applies the gold change (usually: git apply patch.diff)
│   └── patch.diff         # the reference implementation (gold), as a unified diff
├── tests/
│   ├── test.sh            # VERIFIER ENTRY — Harbor runs this; it creates /logs/verifier and runs grade.py
│   ├── grade.py           # orchestrates grading and emits reward.json (invoked by test.sh)
│   ├── run_script.sh      # runs the test suite inside the container, writes stdout/stderr logs
│   ├── parser.py          # parses the runner output into {test_id: PASSED|FAILED|…}
│   ├── test_patch.diff    # adds/edits the test files (feature tests + any harness glue)
│   ├── fail_to_pass.json  # test IDs that FAIL at base and PASS with the gold  (the feature)
│   └── pass_to_pass.json  # test IDs that PASS both at base and with the gold  (regression)
└── environment/
    └── Dockerfile         # self-contained build of the repo at base_commit + toolchain
```

> **Verifier entry = `tests/test.sh`.** Harbor's verifier invokes `tests/test.sh`; the convention is that it
> creates `/logs/verifier` and runs `grade.py` (e.g. `mkdir -p /logs/verifier && python3 "$(dirname "$0")/grade.py"`).
> `grade.py` then applies the test patch, runs `run_script.sh`, parses with `parser.py`, and writes
> `verifier/reward.json`. Keep the filenames consistent with what `test.sh`/`grade.py` call.
> Non-negotiable: `task.toml`, `instruction.md`, a gold under `solution/`, a `tests/` directory with
> `test.sh` + `grade.py`, the two ID lists, the test patch, the runner and its parser, **and
> `environment/Dockerfile`**. The Dockerfile ships *in* the package — Harbor builds it to create the
> container the gold and tests run in. Without it there is no environment, so the gold can't build and
> nothing can be graded. (Leave `docker_image = ""` so Harbor builds your Dockerfile rather than
> skipping it for an image the grader can't pull.)

---

## `task.toml`

```toml
[metadata]
name = "<instance_id>"                 # keep this equal to the instance_id
instance_id = "<org>__<repo>-<slug>"   # stable, unique; used as the folder name
task = "swe-feature-implementation"
source_repo = "pallets/click"          # org/repo of the upstream project
base_commit = "<40-char sha>"          # the EXACT commit your package is built on
license = "BSD-3-Clause"               # the upstream license
programming_language = "python"        # lowercase; must match the repo + gold file extensions

[environment]
# Leave docker_image EMPTY so Harbor builds environment/Dockerfile. Only set it if you have
# pre-published a public image; a private/local tag here makes Harbor skip the Dockerfile and fail
# for anyone who can't pull it.
docker_image = ""
network_mode = "no-network"            # "no-network" | "allowlist" | "public"  (NOT "none")
# allowed_hosts = ["..."]              # only when network_mode = "allowlist"

[agent]
timeout_sec = 3600.0                   # wall budget for the solver

[verifier]
environment_mode = "shared"
timeout_sec = 3600.0

# These two baselines ARE the validation protocol — Harbor runs them for you:
[rollout_baseline.oracle]
reward = 1.0                           # the gold must score exactly 1.0
[rollout_baseline.nop]
reward = 0.0                           # the untouched base must score 0.0
```

**Gotchas that will silently break a package** (learned the hard way):
- `network_mode = "none"` is **rejected** — Harbor only accepts `no-network`, `allowlist`, or `public`.
- A non-empty `docker_image` pointing at a local/private tag makes Harbor **skip** your Dockerfile and the
  run fails for the grader. Keep it `""` unless the image is genuinely public.
- `programming_language` must agree with the repo **and** the gold patch's file extensions (3-way match).
- Your `environment/Dockerfile` must leave the repo a **git working tree at `base_commit`** (clone, checkout,
  then `git init && git add -A && git commit`). Both `solve.sh` and the grader apply patches with
  `git apply`, so a non-git `/app` makes the gold and the test patch fail to apply — and everything scores 0.
- `run_script.sh` must run **only the test files that exist in the current tree**. In the feature-absent
  (`nop`) state the F2P test file isn't there yet; naming a missing path makes pytest/ctest abort before
  running anything — including the P2P tests that *are* present — which looks like "P2P not green" but is a
  harness fault. Filter to present paths (the reference `run_script.sh` shows the pattern).
- The gold (`solution/patch.diff`) and the test patch (`tests/test_patch.diff`) must **not edit the same
  file**. Grading resets test-patch paths to base before applying the test patch; if the gold touched one of
  those paths, that part of the gold is reverted and the gold stops scoring 1.0.

---

## How grading works (what `grade.py` does)

Understanding this flow is the difference between a package that validates and one that mysteriously scores 0:

0. **Entry** — Harbor runs `tests/test.sh`, which creates `/logs/verifier` and calls `grade.py`. Steps 1–6
   are what `grade.py` does.
1. **Apply the gold** — run `solution/solve.sh` (for the oracle baseline). For the `nop` baseline, nothing is
   applied — the repo stays at `base_commit`.
2. **Reset test paths** — `git checkout HEAD -- <paths touched by test_patch>`. This guarantees the test files
   come only from the task, not from the gold. *(This is why gold and test patch must not share a file.)*
3. **Apply the test patch** — `git apply tests/test_patch.diff`, adding the feature tests and any P2P glue.
4. **Run the suite** — `tests/run_script.sh` executes the tests (pytest / vitest / ctest), capturing
   `stdout.log` + `stderr.log`.
5. **Parse** — `tests/parser.py` turns runner output into `{test_id: "PASSED"|"FAILED"|…}`.
6. **Score** — compare against `fail_to_pass.json` and `pass_to_pass.json` and write `verifier/reward.json`
   (+ `grading_details.json` with `f2p_passed/f2p_total/p2p_passed/p2p_total/resolved`).

**Reward rule (standard):**
```
if any P2P test fails:        reward = 0.0          # regression broken → task not satisfied
elif all F2P tests pass:      reward = 1.0          # feature complete + regression intact (resolved)
else:                         reward = f2p_passed / f2p_total   # partial credit
```
`resolved` is `reward == 1.0`. Benchmark resolve@k keys off `resolved`.

Consequences you can rely on:
- **Oracle** (gold applied) → all F2P pass, all P2P pass → **reward 1.0**.
- **Nop** (base repo) → F2P fail (feature absent), P2P pass (existing behavior intact) → **reward 0.0**.

Those two facts are exactly the fairness + discrimination + regression evidence the brief asks for — which is
why the harness just runs the two baselines and reads their grading details.

---

## `fail_to_pass.json` / `pass_to_pass.json`

JSON arrays of **test IDs in the runner's own vocabulary**, because `parser.py` must match them exactly:
- **pytest:** `tests/test_cli.py::test_chained_commands_share_context`
- **vitest:** the full test name/path as the reporter prints it (use the JSON reporter).
- **ctest/gtest:** the registered test name (e.g. `JsonPath.RootSelector`), or the ctest test label.

`fail_to_pass` = the new feature's tests (fail at base). `pass_to_pass` = a curated slice of existing tests
that must keep passing. Choose P2P tests that actually exercise the modules your feature touches — that's what
makes the regression check meaningful rather than decorative.

## `instruction.md`

The **only** description of the feature the solver gets. It must be implementable from the spec alone:
state the problem, the public interface (signatures, names, return shapes), the required behavior including
**edge cases, ordering, error handling, and backward-compatibility**, and the acceptance criteria. Do **not**
reference the test IDs, the gold, or hidden constants. If a hidden test checks it, the spec must state it.
