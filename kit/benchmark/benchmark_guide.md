# Benchmark guide — the finish line

Once your pipeline reliably generates **valid** packages (all three validation checks green), the final step
is to run the benchmark model against them. This is both the payoff — your tasks are now an
eval — and the strongest evidence of **hardness**: a good task is one the model *fails*.

Validation (oracle/nop) proves a task is sound. The benchmark proves it's hard. They are different runs:
validation uses the `oracle`/`nop` baselines (no model); the benchmark uses a real **agent + model**.

## Mental model: resolve rate (resolve@k)

For each task you run the model **k independent rollouts** (k=3 is standard). Each rollout the agent attempts
the task from the spec; the grader scores it; `resolved = reward == 1.0`.

```
resolve rate (resolve@k) = (# of the k graded rollouts that resolved) / k
```

> This is a **resolve rate** — the fraction of attempts that fully pass. It is deliberately *not* the
> HumanEval-style **pass@k** estimator (the probability that ≥1 of k samples passes); we avoid the name
> "pass@k" to prevent confusion. An **infrastructure failure** (reward `null` — env/build/setup crash, not a
> graded attempt) is **excluded** from both numerator and denominator; re-run it — an execution failure is
> not an "unsolved" result.
>
> **Every rollout you count must be a complete model response — no API error, rate-limit, or output
> truncation.** A rollout whose model call errored or was cut off mid-response is an *infrastructure* failure,
> not a *model* failure: exclude it and re-run, never report it as a stump. (A **timeout** — the agent hitting
> its time cap — is the opposite: a genuine model failure that **counts** as a miss.) **Report infrastructure
> failures separately from genuine model failures** — a low resolve@k is only evidence of hardness when every
> counted rollout is a complete, graded attempt the model actually failed (a correct solve, a wrong answer, or
> running out of time).

- **resolve@3 = 0/3** → the model never solved it → the strongest **stump**. This is what you want.
- **resolve@3 = 1/3** → solved only once in three → **still a real stump**: the model can't solve it
  *reliably*. This is exactly why we use the resolve **rate**, not pass@k — a single lucky solve must **not**
  count the task as "solved."
- **resolve@3 = 2/3** → borderline, leaning easy.  **resolve@3 = 3/3** → trivial; redesign harder.
- A good *set* skews toward a **low resolve rate (0/3–1/3)** while every task is still provably solvable (gold = 1.0).

Why k>1: agent runs are stochastic. One lucky solve shouldn't label a task "easy," and one unlucky failure
shouldn't label it "hard." Three rollouts give a stable read.

## Running a benchmark

With the Harbor CLI, pick an **agent** and a **model** and run k rollouts:

```bash
# Claude model via the terminus-2 agent (the default harness):
export ANTHROPIC_API_KEY=...            # the model key (env only — never commit it)
harbor run -p path/to/<instance_id> -a terminus-2 -m anthropic/claude-haiku-5-5 -k 3 \
  -o jobs/<instance_id>-bench --no-delete -y
```

> **Use `anthropic/claude-haiku-5-5` — the required benchmark model.** Benchmark against it (small and
> fast), not the largest SOTA. Three reasons: k=3 rollouts of a multi-turn agent
> stay within the $100 key and finish inside the 4.5-hour build window; and a smaller model is easier to
> stump, so more of your tasks land in the target **0/3–1/3** band while the gold still scores 1.0. A task
> that stumps claude-haiku-5-5 is already strong hardness evidence.

Use the `terminus-2` agent — the default harness — which runs Claude as well as other OpenRouter models.
The provider key is passed via **environment only** — never on the command line, never committed, never in
logs.

> **Network note.** Benchmarking runs a real agent, which usually needs to install itself and reach the model
> API — so the task's `network_mode` must permit that egress (`allowlist` with the agent's hosts, or
> `public`). `no-network` is fine for `oracle`/`nop` validation but will starve a benchmark agent.

## Reading the result

Each rollout lands under the output dir as `trajectory/<iid>/<model>/rollout_N/` with:
- `result.json` — what actually ran (check `agent_info.model_info` to confirm the **real** model/agent, not a
  silent fallback), token counts, timings.
- `verifier/reward.json` and `verifier/grading_details.json` — the score and `f2p/p2p` breakdown.

Compute resolve@k (resolve rate) by counting rollouts with `resolved: true` (reward 1.0). Keep **all three** rollouts per task —
they are the trajectory evidence.

> **Where it goes in your submission.** Put the whole `trajectory/<instance_id>/<model>/rollout_N/` tree at the
> **top level** of your submission (next to `generated_tasks/` and `pipeline_run.json`). Each `<instance_id>`
> must be one of your submitted packages: a trajectory for any other task is **rejected as not belonging to
> this dataset** (Hardness scores 0 if the whole trajectory is for other tasks). The evaluator also
> cross-checks each rollout's `task_checksum` against your submitted task, so the rollouts must be of that
> *same* task — not a same-named different one. Omitting the trajectory is fine (Hardness = "not benchmarked",
> no penalty).

Sanity checks:
- Confirm `result.json`'s `agent_info.model_info` is the model you asked for. A mismatch means the run fell
  back to a default — the number is not for the model you think.
- A `reward` of `null` (not `0.0`) is an **infra failure** (env/build/setup crash), not a legitimate miss —
  re-run it; don't count it as a solve or a fail.
- Likewise any rollout with an **API error, rate-limit, or a truncated model response** is an infra
  failure — the model's answer was never completed, so it isn't a model miss. Re-run it; **every counted
  rollout must be a complete model response.** (A **timeout** is *not* an infra failure — the agent ran but
  didn't finish in time, which is a legitimate miss; count it.)

## Interpreting for your submission

Report, per task: `resolve@3 = x/3`, and the per-rollout rewards. For the set, report the distribution (how many
tasks at 0/3, 1/3, …). **Report infrastructure failures separately from model failures** — list any excluded /
re-run rollouts (API errors, truncation, env crashes) distinctly from genuine misses, so a reader can see each
counted resolve@k rests only on complete, graded attempts. A strong Track 1 result: most tasks at **0/3–1/3**
resolve@k (resolve rate), every task with a gold that scores 1.0 (solvable), and clear variation across what the
tasks exercise.

That's the complete loop: **generate → validate (sound) → benchmark (hard)**. A pipeline that reliably turns a
supplied repo into sound, hard, varied, model-stumping tasks is the Track 1 deliverable.
