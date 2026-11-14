# Harbor CLI quickstart

Mechanics only — the Harbor commands you'll actually run. **What** makes a good task (novel / hard / varied)
is the challenge and is deliberately not covered here; for the package *format* see
[`harbor_task_interface.md`](harbor_task_interface.md).

Harbor: <https://www.harborframework.com/>. Install the CLI from there.

## Prerequisites
- **Docker** running (Harbor builds each task's `environment/Dockerfile` and runs the gold + tests in it).
- **`harbor` on your `PATH`** — check with `harbor --help`.
- A **model API key** only for the benchmark step; validation/self-check need none. Keys go in the
  environment (e.g. `ANTHROPIC_API_KEY`), never on the command line, never committed.

## The one command: `harbor run`
Everything in this kit is a form of `harbor run`:

```bash
harbor run -p <task_dir> -a <agent> -k <n> -o <out_dir> --no-delete -y
```
- `-p` path to a task package (the dir containing `task.toml`)
- `-a` the agent to run (`oracle`, `nop`, or a real model agent like `terminus-2`)
- `-k` number of rollouts
- `-o` output dir — Harbor writes `result.json` plus a `verifier/` dir (the reward lands there)
- `--no-delete -y` keep the run dir; don't prompt

Run `harbor run --help` for the full flag list.

## Self-check soundness (no model key)
Prove a package is mechanically sound with the two baseline agents. `harness/selfcheck.sh` wraps exactly these;
run it rather than typing them by hand:

```bash
# gold applied -> expect reward 1.0, F2P n/n, P2P m/m   (gold solves it, regression intact)
harbor run -p <task_dir> -a oracle -k 1 -o ./sc/<iid>/oracle --no-delete -y
# base, no change -> expect reward 0.0, F2P < n, P2P m/m (feature tests detect the missing impl)
harbor run -p <task_dir> -a nop    -k 1 -o ./sc/<iid>/nop    --no-delete -y
```
A sound task: **oracle reward 1.0** (F2P + P2P all pass) and **nop reward 0.0** (F2P not full, P2P still full).
See [`validation_protocol.md`](validation_protocol.md) and `harness/selfcheck.sh`.

## Benchmark (needs a model key) — the hardness signal
Run a real model agent at `k=3` and read **resolve@k**. Low resolve@k on a task whose gold still scores 1.0 =
genuinely hard. Exact agent/model and reporting are in [`../benchmark/benchmark_guide.md`](../benchmark/benchmark_guide.md):

```bash
harbor run -p <task_dir> -a terminus-2 -m anthropic/claude-haiku-5-5 -k 3 -o ./bench/<iid> --no-delete -y
```

## Other built-ins (optional)
Harbor ships helpers beyond `run` — e.g. `harbor tasks init` (scaffold a new package), `harbor check`
(structure check), `harbor start-env` (open a shell in a task's built environment), `harbor analyze`. They're
conveniences, not required by this kit; see each subcommand's `--help` and the Harbor docs for exact usage.

## Where things land
Under the `-o` dir, per rollout: `result.json` (includes the verifier result / reward) and a `verifier/`
directory. `harness/selfcheck.sh` and the evaluator's validator both read the reward from there — you
shouldn't need to parse it by hand for the self-check.

---
Next: the format contract in [`harbor_task_interface.md`](harbor_task_interface.md), then self-check with
`harness/check_structure.py` + `harness/selfcheck.sh`.
