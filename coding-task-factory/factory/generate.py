"""All LLM roles. Roles are isolated on purpose:
  spec writer   sees: repo context + slot                    (decides WHAT)
  gold writer   sees: repo context + spec                    (one correct HOW)
  test writer   sees: repo context + spec, NOT the gold      (tests the spec, not an implementation)
  solvers       see:  repo context + instruction.md only     (exactly what a benchmarked agent sees)
  fairness judge sees: instruction.md + tests                (is every asserted fact stated in the spec?)
"""
from __future__ import annotations

import json
import re

from .llm import EDIT_FORMAT_INSTRUCTIONS, FILE_FORMAT_INSTRUCTIONS, apply_edits, chat, extract_files, extract_json

SPEC_SCHEMA = """{
  "title": str,                         // short, behavior-focused
  "slug": str,                          // lowercase-hyphenated, <= 40 chars, describes the behavior
  "problem_statement": str,             // the motivation, as a maintainer would write it
  "interface": [{"path": str, "symbol": str, "signature": str, "description": str}],
  "requirements": [{"id": "R1", "text": str}],   // numbered, each independently testable, exact
  "examples": [{"input": str, "expected": str}], // concrete calls / CLI invocations and exact results
  "compatibility": str,                 // what must stay unchanged
  "hardness_rationale": str             // why a capable engineer must read the existing code carefully
}"""


def instruction_md(spec: dict) -> str:
    """The ONLY thing the solver sees. Rendered deterministically from the spec (no authoring tells).
    A spec built from an existing package (factory/package.py:pseudo_spec) carries its original text in `_text`
    and is returned verbatim, so every LLM role also works on packages produced by other tools."""
    if spec.get("_text"):
        return spec["_text"]
    iface ="\n".join(f"- `{i['signature']}` in `{i['path']}` — {i.get('description', '')}".rstrip(" —")
                      for i in spec.get("interface", []))
    reqs = "\n".join(f"{n}. {r['text']}" for n, r in enumerate(spec.get("requirements", []), 1))
    ex = "\n".join(f"| `{e['input']}` | `{e['expected']}` |" for e in spec.get("examples", []))
    out = [f"# {spec['title']}", "", spec["problem_statement"].strip(), "", "## Public interface", "", iface, "",
           "## Required behavior", "", reqs]
    if ex:
        out += ["", "## Examples", "", "| Input | Expected |", "|---|---|", ex]
    if spec.get("compatibility"):
        out += ["", "## Backward compatibility", "", spec["compatibility"].strip()]
    out += ["", "## Acceptance criteria", "",
            "- Every numbered behavior above holds, including the stated edge cases and error behavior.",
            "- All existing behavior and public APIs keep working as before.", ""]
    return "\n".join(out)


def propose_specs(slot: dict, context: str, avoid: list[str], n: int, model: str, feedback: str = "",
                  variant: str = "") -> list[dict]:
    avoid_line = ("Avoid overlapping with: " + "; ".join(avoid)) if avoid else ""
    feedback_line = ("Feedback from previous attempt for this slot: " + feedback) if feedback else ""
    prompt = f"""You design feature-development tasks used to benchmark AI coding agents on a real repository.

Repository context:
{context}

Design {n} candidate tasks for THIS slot (every candidate must fit it):
- Capability area: {slot['capability']}  (extend modules: {', '.join(slot['modules'])})
- Behavioral shape: {slot['shape']}
- Integration depth: {slot['integration']}

Hard requirements:
1. NOVEL: the behavior must not already exist in the repository (read the code!) and should not be a well-known
   upstream feature request that was already implemented.
2. GROUNDED: extends the real modules above; no standalone orphan helper.
3. FAIR: a competent engineer can implement it from the text alone. State every name, signature, default,
   ordering rule, error type, exit code and exact output string that a test could check. No hidden constants.
4. HARD: needs careful reading of existing code and handling of several interacting rules — at least 6 numbered
   requirements, at least 3 edge cases, and at least one interaction with existing behavior. Hard because of
   precise semantics, NOT because anything is left vague.
5. TESTABLE deterministically with pytest (no network, no real terminal, no sleeps, no wall clock).
6. Backward compatible: existing behavior with default arguments is unchanged.
7. Do not mention tests, benchmarks, graders or AI in the text.
{avoid_line}
{feedback_line}

Return ```json [ {SPEC_SCHEMA}, ... ] ```"""
    data = extract_json(chat(prompt, model=model, temperature=0.9, role="spec", max_tokens=12000, variant=variant))
    return data if isinstance(data, list) else [data]


def write_gold(spec: dict, context: str, files: dict, model: str, variant: str = "gold",
               role: str = "gold", temperature: float = 0.2, text: str | None = None) -> tuple[dict, list[str]]:
    """Reference implementation (also reused for independent solvers via `text`=instruction only)."""
    task_text = text or (instruction_md(spec) + "\n\nImplementation notes for you (not shown to users): "
                         + spec.get("hardness_rationale", ""))
    prompt = f"""You are a senior maintainer of this repository. Implement the feature below.

{task_text}

Repository context:
{context}

Rules: follow the public interface exactly; keep all existing behavior; do NOT create or modify any test files
(nothing under tests/); match the code style of the surrounding module.
{EDIT_FORMAT_INSTRUCTIONS}"""
    out = chat(prompt, model=model, temperature=temperature, variant=variant, role=role, max_tokens=16000)
    overlay, errors = apply_edits(out, files)
    bad = [p for p in overlay if p.startswith(("tests/", "test/"))]
    for p in bad:
        overlay.pop(p)
    return overlay, errors + [f"ignored write to test path {p}" for p in bad]


def gold_self_check(overlay: dict, edit_errors: list[str], repo, base_results: dict | None = None) -> tuple[list[str], dict]:
    """Checks the gold writer may see. NEVER the hidden feature tests (keeps gold and tests independent):
      1. every SEARCH/REPLACE edit applied              2. changed files are valid Python
      3. existing regression tests of the touched modules still pass (pytest output tail is fed back)
    Returns (problems, base_results) — base_results is cached by the caller across rounds."""
    import ast as _ast
    from .analyze import related_test_files
    from .sandbox import run_candidate

    problems = [f"edit not applied: {e}" for e in edit_errors]
    syntax = []
    for path, src in overlay.items():
        if src is not None and path.endswith(".py"):
            try:
                _ast.parse(src)
            except SyntaxError as e:
                syntax.append(f"syntax error in {path} line {e.lineno}: {e.msg}")
    if syntax:  # don't spend a pytest run on code that cannot even be imported
        return problems + syntax, base_results or {}
    rel = related_test_files(repo, [p for p in overlay if p.endswith(".py")], limit=3)
    if rel:
        if base_results is None:
            base_results = run_candidate(repo, test_files=rel).results
        run = run_candidate(repo, overlay, test_files=rel)
        broken = sorted(t for t, s in base_results.items() if s == "PASSED" and not run.passed(t))
        if broken:
            problems.append(f"{len(broken)} existing tests that passed before now fail: {broken[:8]}\n"
                            f"pytest output (tail):\n{run.output[-2500:]}")
        elif not run.results:
            problems.append(f"the existing test files could not even be collected:\n{run.output[-2000:]}")
    return problems, base_results or {}


def write_gold_checked(spec: dict, context: str, files: dict, model: str, repo, variant: str = "gold",
                       max_repairs: int = 2, log=print, text: str | None = None) -> tuple[dict, list[str], list[dict]]:
    """write_gold + self-check/repair loop. Each repair round sends the model its own diff and the concrete
    problems, and asks for edits against its CURRENT version (not a rewrite).
    Returns (overlay, remaining_problems, history)."""
    overlay, errors = write_gold(spec, context, files, model, variant=variant, text=text)
    history, base_results = [], None
    for rnd in range(max_repairs + 1):
        problems, base_results = gold_self_check(overlay, errors, repo, base_results)
        history.append({"round": rnd, "problems": [p.split("\n")[0][:200] for p in problems]})
        if not problems:
            if rnd:
                log(f"      gold self-check passed after {rnd} repair round(s)")
            return overlay, [], history
        if rnd == max_repairs:
            break
        log(f"      gold self-check round {rnd}: {len(problems)} problem(s) → repairing: "
            + problems[0].split("\n")[0][:120])
        current = {**files, **{p: c for p, c in overlay.items() if c is not None}}
        from .sandbox import git_diff
        prompt = f"""You implemented the feature below, but your implementation has problems. Fix them.

{text or instruction_md(spec)}

Your current changes (diff against the original repository):
```diff
{git_diff(repo, overlay)[:40000]}
```

Problems found:
{chr(10).join("- " + p for p in problems)}

Repository context (ORIGINAL files, before your changes):
{context}

Edit the files AS THEY ARE NOW (with your changes applied): SEARCH blocks must match the current text.
Fix only what is needed; keep the public interface exactly as specified; never touch files under tests/.
{EDIT_FORMAT_INSTRUCTIONS}"""
        out = chat(prompt, model=model, temperature=0.2, variant=f"{variant}-repair{rnd + 1}", role="gold-repair",
                   max_tokens=16000)
        fix, errors = apply_edits(out, current)
        fix = {p: c for p, c in fix.items() if not p.startswith(("tests/", "test/"))}
        overlay = {**overlay, **fix}
    log(f"      gold still has problems after {max_repairs} repair round(s)")
    return overlay, problems, history


def write_tests(spec: dict, context: str, test_path: str, model: str, extra: str = "") -> str:
    prompt = f"""Write the acceptance tests (pytest) for a feature that is NOT implemented yet.
You will not see any implementation: test the SPEC, so that ANY correct implementation passes.

{instruction_md(spec)}

Repository context (before the feature):
{context}

Rules:
- Put everything in ONE new file `{test_path}`. Do not modify existing test files.
- Use only public APIs that exist today plus the symbols in "Public interface". Never import private helpers.
- Assert only facts the spec states. If you assert an exact string, that exact string must appear in the spec.
  Prefer exception types / exit codes / parsed values over full message text.
- Cover every numbered requirement and every example; include boundary cases the spec defines.
- Deterministic: no network, sleeps, wall-clock time, real terminals or unseeded randomness. Use click.testing.CliRunner
  for CLI behavior. Existing conftest fixtures (e.g. `runner`) may be used if they exist in the context.
- One behavior per test function; descriptive names; inside each test a `# R<n>` comment naming the numbered
  behavior(s) it covers (behavior 1 = R1, behavior 2 = R2, ...). Every numbered behavior needs at least one test.
{extra}
{FILE_FORMAT_INSTRUCTIONS}"""
    files = extract_files(chat(prompt, model=model, temperature=0.3, role="tests", max_tokens=16000))
    return files.get(test_path) or (next(iter(files.values())) if files else "")


def judge_fairness(spec: dict, test_src: str, model: str) -> dict:
    prompt = f"""You audit benchmark tasks for FAIRNESS. A solver sees only this specification:

{instruction_md(spec)}

Hidden tests:
```python
{test_src}
```

For every test, check that each asserted fact (names, signatures, defaults, ordering, error types, exit codes,
exact strings, numeric values) follows from the specification ALONE. Also flag requirements so vague that two
reasonable engineers would implement them differently in a way the tests distinguish.
Answer ```json {{"violations": [{{"test": str, "fact": str, "fix": str}}], "ambiguities": [str],
"clarity": 1-5}} ``` (empty lists if fair; "fix" = the sentence to add to the spec)."""
    return extract_json(chat(prompt, model=model, temperature=0, role="fairness"))


def repair_spec(spec: dict, issues: dict, model: str) -> dict:
    prompt = f"""Revise this task spec so every listed issue is resolved by STATING the needed facts precisely.
Keep the same feature, interface and difficulty; do not mention tests.

Spec:
```json
{json.dumps(spec, indent=1)}
```
Issues:
```json
{json.dumps(issues, indent=1)}
```
Return the full revised spec as ```json {{...}} ``` with the same schema."""
    new = extract_json(chat(prompt, model=model, temperature=0, role="spec-repair"))
    return normalize_requirement_ids({**spec, **{k: new[k] for k in ("problem_statement", "requirements", "examples",
                                                                     "compatibility", "interface") if k in new}})


def write_near_miss(spec: dict, gold_diff: str, gold_files: dict, requirement: dict, model: str) -> tuple[str, dict]:
    prompt = f"""We are stress-testing a hidden test suite. Below is a CORRECT implementation (as a diff).
Write a subtly WRONG variant that violates requirement [{requirement['id']}]: "{requirement['text']}"
the way a careless developer would (off-by-one, wrong boundary, missed edge case, wrong precedence, wrong error
type, wrong ordering) while keeping everything else correct. No comments revealing the bug.

{instruction_md(spec)}

Correct implementation diff:
```diff
{gold_diff[:30000]}
```
First line: `BUG: <one sentence>`. Then edits against the files AS THEY ARE AFTER the correct diff is applied.
{EDIT_FORMAT_INSTRUCTIONS}"""
    out = chat(prompt, model=model, temperature=0.7, variant=requirement["id"], role="near-miss")
    m = re.search(r"BUG:\s*(.+)", out)
    overlay, _ = apply_edits(out, gold_files)
    return (m.group(1).strip() if m else f"violates {requirement['id']}"), \
        {p: c for p, c in overlay.items() if not p.startswith("tests/")}


def requirement_coverage(spec: dict, test_src: str) -> dict:
    """Which requirement ids are referenced by a `# R<n>` comment inside some test function (mechanical)."""
    ids = [r["id"] for r in spec.get("requirements", [])]
    covered, current = {}, None
    for line in test_src.splitlines():
        m = re.match(r"\s*(?:async\s+)?def (test_\w+)", line)
        if m:
            current = m.group(1)
        if current and "#" in line:
            for rid in re.findall(r"\bR\d+\b", line.split("#", 1)[1]):
                covered.setdefault(rid, set()).add(current)
    missing = [r for r in ids if r not in covered]
    return {"missing": missing, "covered": {r: sorted(v) for r, v in covered.items() if r in ids}}


def normalize_requirement_ids(spec: dict) -> dict:
    """instruction.md numbers behaviors 1..n; make ids R1..Rn match that numbering so `# R<n>` is unambiguous."""
    for n, r in enumerate(spec.get("requirements", []), 1):
        r["id"] = f"R{n}"
    return spec


def add_coverage_tests(spec: dict, test_path: str, test_src: str, missing: list[str], model: str) -> str:
    reqs = "\n".join(f"- [{r['id']}] {r['text']}" for r in spec["requirements"] if r["id"] in missing)
    prompt = f"""This hidden test file does not cover some requirements of the specification.
Add tests (each with a `# R<n>` comment) for exactly these requirements, asserting only what the spec states:
{reqs}

Specification (numbered behaviors map to R1, R2, ... in order):
{instruction_md(spec)}

Current test file `{test_path}`:
```python
{test_src}
```
Keep all existing tests. Return the full updated file.
{FILE_FORMAT_INSTRUCTIONS}"""
    files = extract_files(chat(prompt, model=model, temperature=0.2, role="tests-coverage", max_tokens=16000))
    return files.get(test_path) or (next(iter(files.values())) if files else test_src)


def harden_spec(spec: dict, context: str, model: str, probe_note: str, round_no: int) -> dict:
    """Difficulty hardening: a small model solved the task, so GROW it instead of discarding it.
    Existing requirements stay verbatim (tests already validated against them keep meaning the same thing);
    1–2 new requirements add interaction with existing behavior. Fairness is re-checked by the gates afterwards."""
    prompt = f"""This feature task is too easy: {probe_note}
Make it harder WITHOUT making it vague or unfair, by appending 1-2 new numbered requirements.

Current task spec:
```json
{json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}, indent=1)}
```

Repository context:
{context}

Rules for the new requirements:
- They must interact with EXISTING behavior of the repository that a solver has to read the code to handle
  correctly (e.g. how the feature composes with defaults/env vars/default_map, multiple=True, nargs=-1, flag
  options, chained groups, resilient parsing, hidden or deprecated parameters, parameter sources) — pick what
  genuinely fits this feature.
- State behavior only (inputs → outputs, precedence, edge cases, error type/exit code). Never prescribe how to
  implement it (no "calls X", no call order, no internal helpers).
- Fully specified: every value, ordering and error a test could check is written out. At most one short example.
- Keep ALL existing requirements word-for-word and in the same order; append the new ones at the end.
- You may extend the interface (e.g. an extra keyword argument with a backward-compatible default) and must
  list any change there.
- Do not mention tests, benchmarks or AI.

Return the full updated spec as ```json {{...}} ``` with the same schema."""
    new = extract_json(chat(prompt, model=model, temperature=0.7, role="harden", variant=f"harden{round_no}",
                            max_tokens=16000))
    old_reqs = spec.get("requirements", [])
    new_reqs = new.get("requirements", [])
    # enforce "existing requirements verbatim": keep ours, append only the genuinely new tail
    tail = new_reqs[len(old_reqs):] if [r.get("text") for r in new_reqs[:len(old_reqs)]] == \
        [r.get("text") for r in old_reqs] else [r for r in new_reqs if r.get("text") not in {o["text"] for o in old_reqs}]
    merged = {**spec, "requirements": old_reqs + tail[:2],
              "interface": new.get("interface") or spec.get("interface", []),
              "examples": (spec.get("examples") or [])[:2],
              "hardening_rounds": spec.get("hardening_rounds", 0) + 1}
    return normalize_requirement_ids(merged)


def strengthen_tests(spec: dict, test_path: str, test_src: str, survivors: list[dict], model: str) -> str:
    surv = "\n".join(f"- {s['description']}" for s in survivors[:10])
    prompt = f"""These WRONG implementations of the feature pass the current tests:
{surv}

{instruction_md(spec)}

Current test file `{test_path}`:
```python
{test_src}
```
Add tests so each wrong behavior is caught — but only using behavior the specification REQUIRES (if a listed
behavior is actually allowed by the spec, do not test against it). Keep all existing tests.
Return the full updated file.
{FILE_FORMAT_INSTRUCTIONS}"""
    files = extract_files(chat(prompt, model=model, temperature=0.2, role="tests-repair", max_tokens=16000))
    return files.get(test_path) or (next(iter(files.values())) if files else test_src)
