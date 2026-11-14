# Harness (participant self-check)

Three tools to check your work before you submit — two per **package**, one for the **whole submission**. These
use only the **public Harbor interface** and format/schema lints — they are *not* the grader. Final acceptance
is decided by our evaluation after you submit (see the brief); these let you catch problems early and produce
your validation evidence.

## `check_structure.py` — fast offline lint (run first)

Reads a package without building anything. Catches missing files, bad `task.toml` (invalid `network_mode`,
private `docker_image`, missing/short `base_commit`, `name` ≠ `instance_id`), gold and test patch editing the
same file, language 3-way mismatch, empty/invalid F2P/P2P, AI/authoring tells or personal emails, and junk.

```bash
harness/check_structure.py  generated_tasks/*
```
Fix every ERROR before building containers.

## `selfcheck.sh` — mechanical soundness via the Harbor baselines

Runs Harbor's own `oracle` and `nop` baselines on each task and checks the three soundness facts:
- **oracle** (gold) → `reward 1.0`, F2P full, P2P full — the gold solves it and keeps regression green.
- **nop** (base) → `reward 0.0`, F2P *not* full — the feature tests detect the missing implementation.

```bash
SELFCHECK_OUT=./sc  harness/selfcheck.sh  generated_tasks/*
```
Exit 0 if every task is mechanically sound. Output dir via `SELFCHECK_OUT` (default tempdir).

### Requirements
- **`harbor` CLI** (https://www.harborframework.com/) + **Docker**.
- **No model API key** — oracle/nop don't call a model.

## `validate_submission.py` — whole-submission check (run last, before you zip)

The two tools above check one package at a time. This checks the **submission as a whole** against
`SUBMISSION.md`, so you don't send something incomplete. Offline, no Docker, no model key.

```bash
harness/validate_submission.py  path/to/submission_dir      # or: TeamName_Track1.zip
```
It verifies: **ZIP name** (`TeamName_Track1.zip`); **no leaked secrets** (API keys/tokens anywhere — blocking);
**task packages** present and each passing `check_structure.py`; **`pipeline_run.json`** present, valid JSON,
one row per task with the required numeric fields (`wall_seconds`, `attempts`, token counts…) and
instance_ids that match your packages; and that a **pipeline README** and **variation writeup** are present.
Exit 0 only when there are no ERRORs. It never prints a secret it finds — only the file it's in. This is a
completeness/format gate, **not** a grader: it tells you nothing about your score.

## What this does NOT check

`selfcheck.sh` proves *mechanical* soundness only (the package is well-formed and its tests behave). Your
submission is evaluated against **all** of the brief's requirements — so a package that passes the self-check
can still fall short on novelty, difficulty, or variation. Build to `BRIEF.md`, not to the self-check.
