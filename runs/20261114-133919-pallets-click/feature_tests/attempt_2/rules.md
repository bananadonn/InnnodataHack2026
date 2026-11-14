# Test_agent_rules

## Responsibilities

For each feature task:
1. Select relevant, pre-existing regression tests.
2. Generate new feature tests from the task specification.
3. Package the tests in the required Harbor format.
4. Run validation, or hand off to the execution stage and record its results.

### Where to find the Tasks/Features to generate new tests
- look for a `feature.md` file and start generating new tests and map each test to a task, so that no task is left un-tested.


## Inputs

- Repository at the exact `base_commit`.
- `instruction.md`: the authoritative feature specification.
- Reference implementation: `solution/patch.diff`.
- Repository test framework and environment.
- Hackathon task-interface and validation instructions.

## Regression tests — PASS_TO_PASS

- Select tests already present at the pinned base commit.
- Select them programmatically based on affected modules and behavior.
- Include relevant existing functionality and compatibility checks.
- Do not substitute newly written tests for pre-existing regression tests.
- Do not weaken existing assertions to make the implementation pass.
- Avoid unrelated tests or a decorative whole-suite dump.
- Verify selected tests pass both at base and with the reference implementation.
- Record their exact collected test IDs in `pass_to_pass.json`.

## Feature tests — FAIL_TO_PASS

- Generate executable tests for the behavior specified in `instruction.md`.
- For Click, use pytest.
- Cover required normal behavior, boundaries, errors, defaults,
  ordering, compatibility, and interactions where specified.
- Every assertion must be supported by the specification.
- Do not invent undocumented requirements or constants.
- If the specification is ambiguous, report the ambiguity before
  encoding an assumption as a hidden requirement.
- Assert observable outcomes, not a particular implementation,
  algorithm, internal helper, or code structure.
- Use concrete expected results where the specification defines them.
- Ensure feature tests detect missing or incorrect behavior.
- Verify they fail at base and pass with the reference implementation.
- Record their exact collected test IDs in `fail_to_pass.json`.
- No fixed number of tests is required; choose coverage based on the spec.

## Required output

<instance_id>/tests/
├── test.sh
├── grade.py
├── run_script.sh
├── parser.py
├── test_patch.diff
├── fail_to_pass.json
└── pass_to_pass.json

- `test_patch.diff`: unified Git diff adding feature tests and
  necessary test support.
- `fail_to_pass.json`: nonempty JSON array of feature test IDs.
- `pass_to_pass.json`: nonempty JSON array of existing regression test IDs.
- `run_script.sh`: executes the selected tests.
- `parser.py`: converts actual runner output into structured test statuses.
- `grade.py`: applies the test patch, runs tests, parses results,
  calculates reward, and writes grading artifacts.
- `test.sh`: Harbor verifier entry; creates `/logs/verifier`
  and invokes `grade.py`.

Use the supplied worked example and task-interface contract for
the exact execution and result formats.

## Test IDs

- Use actual IDs from the repository's test runner.
- For pytest:
  `tests/test_file.py::test_function`
- Include class names and parametrization suffixes when applicable.
- JSON entries and parsed IDs must match exactly.
- Never invent IDs or count missing/uncollected tests as passed.

## Patch and execution guardrails

- The test patch and reference implementation must not edit the same files.
- Keep tests and the gold solution inaccessible to the solver.
- Run feature and regression tests against the same implementation state.
- Prevent feature-test collection errors from blocking regression execution.
- Handle expected test failures without stopping result parsing.
- Do not treat build, setup, dependency, or runner failures as evidence
  that feature tests correctly detect missing functionality.
- Keep grading deterministic and execution-based.
- Never use an LLM to determine the final test reward.

## Required validation

1. Base health:
   The original repository builds and its existing suite passes.

2. Base / nop:
   Feature tests fail, selected regression tests pass, reward is 0.0.

3. Reference implementation / oracle:
   All required feature and regression tests pass, reward is 1.0.

4. Mutation:
   Deliberately corrupting relevant reference behavior causes
   feature tests to fail.

Oracle/nop checks alone do not establish mutation sensitivity.

## Reward rule

If any required regression test does not pass:
    reward = 0.0
Else if all required feature tests pass:
    reward = 1.0
Else:
    reward = feature_tests_passed / feature_tests_total

## Evidence and reporting

- Preserve commands, execution logs, exact test IDs, and results.
- Record feature and regression counts separately.
- Record mutation changes and which tests detected them.
- Report infrastructure errors separately from behavioral failures.
- Report specification ambiguities and validation blockers.
- Never fabricate passing results or mark unexecuted checks as verified.
- Do not silently hand-fix final packages; repair the generation process
  and regenerate/revalidate affected artifacts.
- Keep authoring reports and mutation artifacts outside the task package.

## Participant checks

Run from the participant kit, using the generated-task paths:

python3 harness/check_structure.py <task-path>

SELFCHECK_OUT=./sc harness/selfcheck.sh <task-path>

Clear structure errors and preserve the self-check soundness tables.
These checks do not replace mutation testing or semantic review.
