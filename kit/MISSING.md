# Missing from our copy of the organizer kit

The kit in this folder was restored from a scrambled download (file names did not match
contents). Everything below is referenced by the kit but was **not** in our copy.
Nothing here has been recreated by hand — ask the organizers for the originals.

## Toy example: `examples/toy__stringkit-0001-truncate/`

Present: `task.toml`, `instruction.md`.

Missing (10 files):

| File | What it is (per `examples/README.md` / `docs/harbor_task_interface.md`) |
|---|---|
| `environment/Dockerfile` | Embedded toy repo + toolchain |
| `solution/solve.sh` | Applies the gold patch |
| `solution/patch.diff` | Gold reference implementation |
| `tests/test.sh` | Verifier entry Harbor runs |
| `tests/grade.py` | Orchestrates grading, writes `reward.json` |
| `tests/run_script.sh` | Runs the suite inside the container |
| `tests/parser.py` | Parses runner output into `{test_id: status}` |
| `tests/test_patch.diff` | Adds the feature tests |
| `tests/fail_to_pass.json` | F2P test IDs |
| `tests/pass_to_pass.json` | P2P test IDs |

Why it matters: `grade.py`, `test.sh`, `run_script.sh` and `parser.py` are the reference
grading files every generated package needs. `templates/click_base/` only has TODO
placeholders for them until we get the originals.

## Notes

- `examples/toy__stringkit-0001-truncate/task.toml` starts with a 5-line comment header
  above `[metadata]`. Kept exactly as received.
- `evaluation/` is listed in `kit/README.md` as evaluators-only; it is expected to be absent.
- One file in the download (`JUDGING.md` by name) was a macOS `.DS_Store` and was discarded.
