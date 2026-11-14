# Implementation agent rules

## Primary requirement: preserve existing behavior

Implement each proposed feature without breaking or changing behavior that already exists. Backward compatibility is a hard acceptance requirement. Passing new feature tests never compensates for a regression failure.

## Inputs and scope

- Start each feature independently from the exact pinned base commit.
- Read the feature specification, relevant source code, existing tests, and repository compatibility conventions before editing.
- Preserve existing public interfaces, defaults, return values, output, ordering, errors, and side effects for existing usage. New behavior must follow the specification and leave existing usage compatible.
- If a feature specification requires incompatible behavior, report the conflict and block that feature rather than silently changing existing behavior or redefining the specification.
- Keep source changes focused on the feature. Avoid unrelated refactoring.
- Do not modify, delete, skip, weaken, or change the expected results of existing regression tests. Do not change runner configuration or dependencies to hide regressions.
- Keep the implementation patch separate from test files and test support. Gold and hidden-test patches must touch disjoint files.

## Required execution gates

1. Establish base health: the original repository must build and its existing suite must pass in the declared environment. Record the commands and results.
2. Implement the feature in an isolated working tree at the pinned commit.
3. Run the new feature tests and relevant pre-existing regression tests against the same implementation state. Also run the existing suite to check for broader regressions before accepting the reference implementation.
4. If any required regression test fails, reject the candidate and repair the implementation. Never repair the regression tests to fit the candidate.
5. If new feature tests fail, the implementation remains incomplete even if all regression tests pass.
6. After changes, rerun the affected checks and the required acceptance gates. Keep evidence for failures and retries as well as successes.

Missing tests, collection failures, setup failures, timeouts, and unexecuted checks are not passing results. Separate infrastructure failures from behavioral regressions, and block acceptance until the required checks can actually establish compatibility.

Passing tests provides compatibility evidence for the covered behavior; it does not prove that every existing behavior is preserved. Review the diff and unspecified edge cases as well.

## Acceptance and reporting

- Accept only when every required new feature test and every required regression test passes.
- Any required regression failure gives reward 0.0 under the hackathon grading contract.
- Select relevant existing regression IDs programmatically for the final task package; running the full suite for compatibility checks does not replace that selection.
- Record the base commit, implementation patch, exact commands, actual test results, failures, retries, and unresolved compatibility concerns.
- Never report regression discovery alone as regression validation.
- These are requirements for the upcoming implementation stage. The existing generation stub does not yet enforce or execute these gates.
