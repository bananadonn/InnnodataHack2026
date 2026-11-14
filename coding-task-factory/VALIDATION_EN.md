# Validation — what every check means and what it proves

A task is only worth shipping if it is **sound** (it measures the feature and nothing else), **fair** (solvable
from `instruction.md` alone) and **hard** (the benchmark model fails it). Validation answers those three
questions with checks that run in a fixed order, cheapest first. Every failure names **who must fix it**.

There are two layers that use the same ideas:

| Layer | When it runs | Command | Gate names |
|---|---|---|---|
| **Generation gates** | inside `generate`, on every candidate before it is accepted | `main.py generate ...` | **L1–L7** |
| **Package validator** | on any finished Harbor package, whoever produced it (our generator or the team SDK) | `main.py validate <pkg...> --repo-dir work/click [--llm] [--container]` | **V0–V12** |

Both are followed by the **authoritative container check** (Harbor oracle/nop in Docker), and finally by the
**benchmark** (terminus-2 + `claude-haiku-5-5`, k=3).

Vocabulary used below:
- **Gold**: the reference implementation (`solution/patch.diff`).
- **F2P (fail-to-pass)**: new feature tests. They must FAIL on the original repo and PASS with the gold.
- **P2P (pass-to-pass)**: existing click tests that must PASS both before and after the gold.
- **Base**: click at the pinned commit `cf19179e` (tag 8.5.1), untouched.

---

## 1. Generation gates L1–L7 (`factory/validate.py`)

| Gate | What it does | What it proves | If it fails |
|---|---|---|---|
| **L1 Structure** | The gold is non-empty and never touches test files. The new test file does not already exist upstream and is valid Python. | The task is well-formed. Gold and tests are physically separate, as the Harbor grader requires, so the grader cannot erase part of the gold. | Candidate rejected. |
| **L2 Fairness** | An LLM auditor reads ONLY `instruction.md` and the hidden tests. For every assertion it asks whether the fact (name, default, ordering, error type, exact string) is stated in the spec. It also flags requirements two engineers could read differently. | **Fair:** no hidden test depends on something the solver cannot know. | The spec is automatically repaired once by writing the missing facts into it, then audited again. Still failing → rejected. |
| **L2b Coverage** | Each test carries a `# R<n>` comment. The pipeline checks mechanically that every numbered requirement has at least one test. | **Complete:** no requirement goes unchecked, so a solver cannot skip a rule and still pass. | Tests for the missing requirements are added once and the fairness audit re-runs. |
| **L3 Interface** | AST analysis lists the new symbols the gold introduces. The tests may use them only if `instruction.md` names them, and may never use private helpers. | **Fair:** the tests do not require guessing an undocumented name or signature. | Rejected. |
| **L4 F2P / P2P** | Runs the feature tests plus a curated regression set (the existing test files that exercise the modules the gold touches) twice: on base and with the gold. **Also runs the entire click suite (2,434 tests) with the gold**, compared against base. | **Discriminating:** the feature is really missing at base, since the F2P tests fail there. **Solvable:** the gold passes every feature test. **Regression-safe:** nothing that passed before breaks, neither in the curated set nor anywhere in click. Requires ≥3 F2P and ≥5 P2P. | Rejected. Log fields: `gold_fails` = feature tests the gold fails, `regressions` = curated P2P broken, `full_suite_regressions` = other click tests broken. |
| **L5 Determinism** | Re-runs the gold and compares results. | **Reproducible:** no flaky tests. A flaky test would make the benchmark score noise. | Rejected. |
| **L6 Mutation** | Deliberately corrupts the gold and checks that the tests notice. Two kinds of corruption: (a) up to 15 **AST mutants**, applied only inside functions the gold changed: `<`↔`<=`, `==`↔`!=`, `+`↔`-`, `and`↔`or`, constant+1, negated `if`, `return None`, deleted `raise`; (b) **near-miss bugs**, where an LLM writes a plausible wrong implementation targeting one specific requirement (off-by-one, wrong precedence, missed edge case). A corruption is "killed" if any test fails. | **The tests bite:** a wrong solution cannot pass. This is the same property as the organizer's "Mutation" gate. Pass = kill rate ≥ 80% **and every near-miss bug killed**. | The surviving bugs are sent to the test writer, who adds tests for behavior the spec requires. L4–L6 re-run, up to 2 rounds. Surviving AST mutants may be *equivalent* (same behavior), so they are listed for inspection. |
| **L7 Solvable + difficulty probe** | **Blind solvers** see only `instruction.md` and the repo, exactly what the benchmarked agent sees. One is Sonnet; one is a model from another vendor (OpenRouter `gpt-5`). At least one must pass every graded test. Then a **one-shot Haiku probe** tries the same. | **Fair and solvable from text:** independent implementations pass the same hidden tests. **Not one model's misreading:** a model family that wrote neither gold nor tests agrees (`cross_vendor_agrees`). **Difficulty signal:** if Haiku solves it in one shot, the task is likely too easy. | No blind solver passes → rejected. Haiku solves it → task is still valid but marked `likely_easy`, and **hardening** starts (see §3). |

**Accept rule:** a candidate is accepted only if L1, L2, L2b, L3, L4, L5, L6 and L7 all pass. If L4 fails, the
log shows L5–L7 as failed too. They did not run; they did not fail.

### How to read a log line
```
L4 F2P/P2P  PASS F2P=48/51 P2P=241 gold_fails=0 regressions=0 full_suite_regressions=0
```
48 of the 51 feature tests fail at base and pass with the gold; these are the F2P tests. The other 3 already
pass at base, so they are not counted as F2P. 241 existing tests stay green. The gold fails nothing, and no
click test anywhere was broken.

```
L6 mutation FAIL kill_rate=78% (14/18)
    survived [near_miss] The option handler line lists only `opts` and omits `secondary_opts` ...
↻ strengthen tests (round 1): 4 wrong implementations survived
L6 mutation PASS kill_rate=94% (17/18)
```
The tests initially missed a realistic bug. The pipeline added a test for it and the bug is now caught.

---

## 2. Package validator V0–V12 (`factory/package_validate.py`)

This layer takes a **finished Harbor package** as its only input, so it works on whatever any teammate
produces. It re-measures everything itself instead of trusting the package's own claims.

| Gate | What it does | What it proves | Sent back to |
|---|---|---|---|
| **V0 Lint** | Runs the organizer's `check_structure.py`. | Package follows the Harbor interface: required files present, `task.toml` valid, no AI tells or personal emails. | package |
| **V1 Load** | `task.toml` parses, `base_commit` matches our click checkout, and both patches apply cleanly to base. | The package is reproducible on the stated commit. | package |
| **V2 Hygiene** | The gold never edits test files; the gold and the test patch share no file. | The grader will not revert part of the gold. | gold |
| **V3 F2P/P2P (re-measured)** | Runs base and gold, then compares with the declared `fail_to_pass.json` / `pass_to_pass.json`. Flags IDs that never ran (typo or parametrize mismatch), F2P that already pass at base, F2P the gold fails, and P2P the gold breaks. Also warns (V3b) when fewer than half of the P2P tests come from test files related to the touched modules. | **Discriminating and regression-safe**, measured independently. Also proves the declared IDs are real. | package / gold / tests, depending on the problem |
| **V4 Full suite** | Runs the whole click suite with the gold. | No collateral damage outside the curated regression set. | gold |
| **V5 Determinism** | Re-runs the gold. | No flaky tests. | tests |
| **V6 Mutation** | AST mutants of the gold's changed functions must make the feature tests fail (≥ 80%). | **The tests bite.** | tests |
| **V7 Interface** | Same rule as L3, using the symbols named in `instruction.md`. | No undocumented names are required. | spec |
| **V8 Coverage** | Same rule as L2b, when tests carry `# R<n>` annotations; otherwise skipped. | Every requirement is tested. | tests |
| **V9 Spec style** | Flags requirements that prescribe *how* to implement ("calls X", call order, internal helpers). Warning only. | **Fairness and difficulty:** the organizers want tests to check behavior, not a specific implementation, and prescriptive specs are easier to copy. | spec |
| **V10 Fairness** (`--llm`) | Same audit as L2. | Every asserted fact is in the spec. | spec |
| **V11 Probes** (`--llm`) | Blind strong solver(s) and two one-shot Haiku probes. | Solvable from the text; difficulty signal. | spec |
| **V12 Container** (`--container`) | Organizer `selfcheck.sh` in Docker, plus one corrupted gold run through the Harbor oracle. | The **authoritative** version of the checks above, run in the judges' own harness (next section). | package / gold |

Verdicts printed per package: **sound** = V0–V6 all pass; **fair** = V7/V8/V10 have no failure;
**hard** = the Haiku probe failed. Output: `runs/validation/<time>/validation_summary.md`, with a table, a
"send back to" list, and a batch check that flags pairs of packages that look alike (shared wording or the same
touched files), which matters for the **Variation** score.

---

## 3. Loops that improve a task instead of discarding it

| Loop | Trigger | What happens | Why it matters |
|---|---|---|---|
| **Gold self-repair** | Right after the gold is written | Checks that all edits applied, the code parses, and existing tests of the touched modules still pass. Problems go back to the gold writer with its own diff and the pytest output, up to 2 rounds. **The gold writer never sees the hidden tests**, so gold and tests stay independent. | Fewer candidates lost to a broken gold. |
| **Spec repair** | L2 finds an unstated fact | The missing fact is written into the spec. | Fairness. |
| **Coverage fill** | L2b finds an untested requirement | Tests are added. | Completeness. |
| **Test strengthening** | L6: a wrong implementation survives | Tests are added for the surviving bug, if the spec requires that behavior. | Tests bite. |
| **Difficulty hardening** | L7: Haiku solves it in one shot | The spec gains 1–2 requirements that interact with existing click behavior; existing requirements stay verbatim. The gold is rewritten from base, the validated tests are extended, and **all gates run again**, up to 2 rounds. If hardening breaks something, the previous valid version is kept. | Difficulty (20 pts) without losing fairness. |
| **Agent selection** | A slot has ≥2 valid candidates | Each candidate gets one rollout of the real benchmark harness (terminus-2 + Haiku). The slot keeps the one with the lowest reward. | The one-shot probe is weaker than the real agent, which can run tests and iterate, so selection uses the real thing. |

Example from a real run (shell-completion slot):
- **Strengthening:** mutation kill rate 78% → 94% after one round, and the near-miss bug (`--on/--off` showing only `--on`) became caught.
- **Cross-vendor check:** Sonnet and gpt-5 both solved the task blind.
- **Hardening:** Haiku still solved it after round 1, so round 2 added two more interacting rules. The result had 98 F2P tests and a 100% kill rate.

---

## 4. Container check — the authoritative proof (organizer harness)

| Run | Expected | Proves |
|---|---|---|
| `harbor run -a oracle` (gold applied) | reward **1.0**, F2P n/n, P2P m/m | The gold satisfies the spec in the judges' own environment. |
| `harbor run -a nop` (base untouched) | reward **0.0**, F2P < n, P2P m/m | The feature is genuinely missing; base is healthy. |
| oracle with a **corrupted gold** | reward **< 1.0** | The tests catch a wrong solution inside the real grader. This is the organizer's "Mutation" gate. |

Verified on our first package: oracle 1.0 (F2P 42/42, P2P 272/272), nop 0.0 (F2P 0/42), corrupted gold (`is` →
`is not`) scored 0.0. Each package takes about 1 minute.

## 5. Benchmark — the hardness proof

`harbor run -a terminus-2 -m anthropic/claude-haiku-5-5 -k 3`. **resolve@3 = rollouts with reward 1.0 / 3.**
A target task scores 0/3 or 1/3 while the gold still scores 1.0.

Infrastructure failures do not count; they are re-run and reported separately. These include a null reward, an
API error, a rate limit, a truncated model response, or a model mismatch in `result.json`. A **timeout does
count** as a genuine miss.

---

## 6. How this maps to the organizer's gates and rubric

| Organizer gate (JUDGING.md) | Our evidence |
|---|---|
| Structure | L1, V0, V1 |
| Name integrity | Slot planning gives every task its own capability × behavioral shape, plus the batch similarity check |
| Novelty | Novelty check: GitHub issue/PR search plus an LLM judgment over the source, before any gold is written |
| Grounding | Every slot is bound to real click modules, and the gold edits them (V3b relevance) |
| Gold (oracle) = 1.0 | L4, V3, container oracle |
| Feature-absent (nop) | L4 (F2P fail at base), V3, container nop |
| Base health | Full click suite green at base before every run (2,434 tests) |
| Mutation | L6, V6, container corrupted-gold run |

| Rubric dimension | Covered by |
|---|---|
| Reliability (20) | All gates run before export, and the repair loops raise first-pass yield |
| Fairness (15) | L2, L2b, L3, V9, cross-vendor blind solvers |
| Difficulty (20) | Haiku probe, hardening, agent selection, resolve@3 |
| Variation (20) | Slot planning, near-duplicate checks |
| Regression (10) | Curated P2P from touched modules, plus the whole-suite check |
| Reproducibility (5) | Pinned commit, determinism gate, container check, LLM response cache |
| Efficiency (10) | `pipeline_run.json` plus a per-call audit log (`llm_calls.jsonl`) |

## 7. Honest limitations (say these in the Q&A)

- **The fairness audit is done by an LLM.** It is strong evidence, not proof. The blind solvers back it up with execution.
- **Surviving AST mutants may be equivalent**, meaning they behave the same as the gold. We list them rather than auto-classify them.
- **The one-shot Haiku probe is weaker than the benchmark agent.** That is why the final selection uses real terminus-2 rollouts.
- **Novelty** relies on GitHub search plus judgment. It can miss discussions held elsewhere.
- **When the gold and the tests disagree** on a few hidden tests, the candidate is still rejected. An arbiter that decides which side is wrong is the next improvement.
