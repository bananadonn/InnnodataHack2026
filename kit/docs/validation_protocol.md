# Self-check your packages before submitting

Use these to confirm a package is well-formed and mechanically sound. They are **conformance checks** — they
verify your task meets the interface and the brief's testability requirement. They are not the full
evaluation; we assess your submission separately.

## 1. Structure lint — `harness/check_structure.py` (offline)
Confirms the package matches the interface and ships nothing it shouldn't:
```bash
harness/check_structure.py  generated_tasks/*
```
Clear every ERROR.

## 2. Mechanical soundness — `harness/selfcheck.sh` (Harbor baselines)
The brief requires that each task's reference implementation satisfies the requirements, that feature tests
detect missing behavior, and that regression checks protect existing functionality. This verifies exactly
that, using Harbor's own `oracle` and `nop` baselines:

| Baseline | Expect | Confirms |
|---|---|---|
| `oracle` (gold applied) | `reward 1.0`, F2P `n/n`, P2P `m/m` | the reference implementation satisfies the requirements; regression intact |
| `nop` (untouched base) | `reward 0.0`, F2P `< n`, P2P `m/m` | feature tests detect the missing behavior; base is healthy |

```bash
SELFCHECK_OUT=./sc  harness/selfcheck.sh  generated_tasks/*
```
Requires `harbor` + Docker; no model API key. A package that passes both is well-formed and sound — that is
your validation evidence for the submission.

## Reward rule (so the numbers above make sense)
```
if any P2P fails:        reward = 0.0
elif all F2P pass:       reward = 1.0
else:                    reward = f2p_passed / f2p_total
```

## Failure → fix

| Symptom | Likely cause | Fix |
|---|---|---|
| oracle reward < 1.0, F2P fail | gold doesn't fully implement the spec | fix gold, or align test/spec |
| oracle reward 0.0, P2P fail | gold broke existing behavior, or gold & test patch edit the same file | non-breaking gold; disjoint files |
| nop F2P already pass | feature tests don't test the feature | strengthen F2P to depend on the new behavior |
| nop P2P fail | base suite not green, or wrong/flaky P2P IDs | pick a stable base; fix IDs; drop flaky tests |
| build error before any test | Dockerfile not self-contained / wrong toolchain | clone + checkout `base_commit`; pin the toolchain |
| reward `null` (not 0.0) | env/setup crash, not a real score | fix the environment and re-run |

---

Passing the self-check means your package is **submittable**, not necessarily **accepted** — your submission
is evaluated against the brief's requirements (novelty, variation, difficulty, and more). Build to the brief.
