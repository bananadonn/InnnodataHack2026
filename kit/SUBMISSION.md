# What to submit

Hand back a single archive/repo containing the four things below. The evaluators will **re-run your pipeline
themselves**, so reproducibility matters more than polish on any one package.

## 1. The pipeline
Your task-generation code, with everything needed to run it:
- A clear **README** with exact run instructions (setup, commands, any env vars / model-API config).
- Deterministic enough to **reproduce**: pin dependencies; if you call a model, say which and how, and make
  reruns produce comparable output.
- It must emit packages in the **Harbor interface** (`docs/harbor_task_interface.md`) into an output
  directory.

## 2. Sample task packages
The **5 distinct tasks** your pipeline generated from your chosen supplied repository, substantively different
from each other. Don't hand-fix them after generation; if you had to, fix the pipeline and regenerate (we score
the raw output). The 5 are scored on **meaningful variation**, not volume — five genuinely different capabilities,
not five rewordings.

**Each package must include its own `environment/Dockerfile`** (with `docker_image = ""` in `task.toml`).
The Dockerfile *is* the environment — we build it to run the gold and the tests. A package submitted
without a working Dockerfile can't be built or graded, so it scores nothing. See the worked example in
`examples/` and the contract in `docs/harbor_task_interface.md`.

## 3. Validation evidence (your self-check)
For each sample package, the self-check output showing mechanical soundness:
```bash
harness/check_structure.py              generated_tasks/*
SELFCHECK_OUT=./sc harness/selfcheck.sh generated_tasks/*    # oracle 1.0 + full F2P/P2P; nop 0.0 + F2P not full
```
Include the printed soundness tables. Optionally include benchmark resolve@k (`benchmark/benchmark_guide.md`) as
hardness evidence. (We evaluate your submission against all of the brief's requirements — not only the
self-check — so build to the brief, not to the self-check.)

## 3b. Pipeline run log — `pipeline_run.json`
A record of your pipeline's resource usage per task, so we can assess efficiency. One object per task:
```json
{ "pipeline": "your-team/version",
  "tasks": [
    {"instance_id": "<iid>", "model": "<model you used>",
     "wall_seconds": 142, "model_calls": 6, "attempts": 2,
     "n_input_tokens": 180000, "n_output_tokens": 9000, "n_cache_tokens": 150000}
  ] }
```
`attempts` = how many generate-and-check cycles your pipeline needed to land that task. Use what your tooling
reports; the field names mirror Harbor's `result.json`.

**Back it with auditable evidence.** Because we score efficiency from this file but cannot re-run every
pipeline, include something the numbers can be checked against — a provider usage/cost export, or raw run
logs — and keep your generation trajectories/logs in the submission. Self-reported figures that the
submitted artifacts contradict are capped (see the rubric).

## 3c. Benchmark trajectory (optional — hardness evidence)
If you include benchmark rollouts (resolve@k) as hardness evidence, put them at the **top level of your
submission** in exactly this layout (see `benchmark/benchmark_guide.md` for how to produce them):

```
trajectory/<instance_id>/<model>/rollout_N/
    result.json
    verifier/reward.json
    verifier/grading_details.json
```

- `trajectory/` sits alongside `generated_tasks/` and `pipeline_run.json` (inside your `TeamName_Track1/`
  top folder). The evaluator will find it anywhere under the submission, but this is where it belongs.
- **Each `<instance_id>` must be one of your submitted packages** (a dir under `generated_tasks/`). A
  trajectory for a task that is not in your submission does **not** count as hardness: it is rejected as
  *not belonging to this dataset*, and if the whole trajectory is for other tasks, Hardness scores **0**.
- The rollouts must be of **that same task**. The evaluator reads each rollout's `result.json` and checks
  its harbor `task_checksum` against your submitted task — a mismatch is flagged as a trajectory for a
  *different* task than the one in your `task.toml`.
- Keep **all k** rollouts per task. Omitting the trajectory entirely is fine — Hardness is then reported as
  "not benchmarked" (no penalty), *not* rejected.

## 4. Variation writeup (1–2 pages)
Explain **how your strategy creates meaningful variation** — the axes you move along (capability / behavioral
shape / integration depth / interaction rules), why that produces substantively different tasks rather than
reworded ones, and how the pipeline decides what to generate. This is what distinguishes a task *factory* from
a task *template*.

## How to submit

Submit **one ZIP file per team**, named **`TeamName_Track1.zip`**, through the organizers' form before the
deadline. Do **not** include API keys or other secrets.

- Google Form link: *[to be confirmed]*
- Submission deadline: *[date, time, and time zone to be confirmed]*
- Maximum ZIP size: *[to be confirmed]*
- Upload support: *[contact to be confirmed]*

The ZIP should contain: (1) pipeline source + setup/run instructions; (2) the raw generated sample packages +
their validation evidence; (3) `pipeline_run.json`; (4) the variation writeup / README (with each member's
contribution); optionally (5) a top-level `trajectory/` of benchmark rollouts for hardness (see 3c). A simple
README/CSV plus logs is fine for the evidence.

## Demo

Each team has **10 minutes total** for presentation + live demo. Cover:
- the problem and what your pipeline does,
- a **live demonstration generating and self-checking a fresh package end to end**,
- how the task's grading works (gold → 1.0, feature tests fail at base, regression stays green),
- your main findings and limitations.

Slides are optional (**≤ 5 slides**); if used, include them in the ZIP. An edited video is not required.
Q&A timing: *[to be confirmed]*. For partial submissions, demo the working components and explain what remains.

## Checklist before you send
- [ ] **`harness/validate_submission.py <your_submission>` reports 0 ERRORs** — one command that checks this
      whole list mechanically (secrets, packages pass `check_structure`, `pipeline_run.json` schema + coverage,
      README/writeup present). Run it last, on the exact folder/zip you're sending.
- [ ] ZIP named `TeamName_Track1.zip`; **no API keys or secrets** included.
- [ ] Pipeline runs from a clean checkout following your README.
- [ ] **5 distinct tasks** generated from your chosen supplied repo (substantively different, not rewordings).
- [ ] `check_structure.py` passes on all sample packages (no ERRORs).
- [ ] Every package includes its `environment/Dockerfile` (with `docker_image = ""`) and it builds.
- [ ] `selfcheck.sh` shows every package mechanically sound (oracle 1.0 / nop 0.0).
- [ ] `pipeline_run.json` telemetry included (for efficiency measurement), backed by usage export / run logs.
- [ ] Packages are novel against **live upstream** (not in `main`; not merged just after your `base_commit`).
- [ ] No junk or AI/authoring leaks in packages.
- [ ] Writeup explains the variation strategy + each member's contribution.
- [ ] Working vs planned/incomplete components clearly distinguished.
