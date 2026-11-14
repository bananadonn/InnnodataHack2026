"""Local gates (fast inner loop). The authoritative container checks (harbor oracle/nop) run after export.

  L1 structure      gold non-empty, never touches tests; test file is new and parses
  L2 fairness       LLM audit: every fact a test asserts is stated in instruction.md (auto-repair spec once)
  L3 interface      tests use only existing public API + declared interface symbols (AST)
  L4 F2P / P2P      feature tests fail at base & pass with gold; curated regression set green at base & gold
  L5 determinism    gold re-run gives identical results
  L6 mutation       AST mutants of the gold + LLM near-miss bugs must be killed (auto-strengthen tests ≤2 rounds)
  L7 solvable/hard  strong independent solver(s) from instruction.md alone must pass (fair);
                    weak one-shot probe (benchmark model family) ideally fails (hard)
"""
from __future__ import annotations

import ast
from pathlib import Path

from . import generate
from .analyze import defined_symbols, is_test_path, py_files
from .mutate import generate_mutants
from .sandbox import git_diff, ids_in_files, run_candidate

TH = {"min_f2p": 3, "min_p2p": 5, "min_kill_rate": 0.8, "repair_rounds": 2, "n_near_miss": 3, "max_mutants": 15}


def run_gates(task: dict, repo: Path, cfg, log=print, base_full: dict | None = None) -> dict:
    """base_full: {test_id: status} of the WHOLE upstream suite at base (from the base-health run)."""
    task["_base_full"] = base_full or {}
    rep = {"gates": {}, "history": []}
    g = rep["gates"]
    spec, test_path = task["spec"], task["test_path"]
    files = py_files(repo)

    # L1 structure
    errs = []
    if not task["gold"]:
        errs.append("empty gold")
    if any(is_test_path(p) for p in task["gold"]):
        errs.append("gold touches tests")
    if (repo / test_path).exists():
        errs.append(f"{test_path} already exists upstream")
    try:
        ast.parse(task["test_src"])
    except SyntaxError as e:
        errs.append(f"test file does not parse: {e}")
    g["L1_structure"] = {"passed": not errs, "errors": errs}
    log(f"    L1 structure     {_ok(g['L1_structure'])} {errs or ''}")
    if errs:
        return _decide(rep)

    # L2 fairness (+1 automatic spec repair)
    fair = generate.judge_fairness(spec, task["test_src"], cfg.gen_model)
    if fair.get("violations") or fair.get("ambiguities"):
        log(f"    L2 fairness      {len(fair.get('violations', []))} violations → repairing spec")
        task["spec"] = spec = generate.repair_spec(spec, fair, cfg.gen_model)
        fair = generate.judge_fairness(spec, task["test_src"], cfg.gen_model)
    g["L2_fairness"] = {"passed": not fair.get("violations"), **fair}
    log(f"    L2 fairness      {_ok(g['L2_fairness'])}")

    # L2b requirement coverage: every numbered behavior has >=1 test (mechanical; +1 automatic fix)
    cov = generate.requirement_coverage(spec, task["test_src"])
    if cov["missing"]:
        log(f"    L2b coverage     missing {cov['missing']} → adding tests")
        task["test_src"] = generate.add_coverage_tests(spec, test_path, task["test_src"], cov["missing"], cfg.test_model)
        cov = generate.requirement_coverage(spec, task["test_src"])
        fair = generate.judge_fairness(spec, task["test_src"], cfg.gen_model)  # new tests must be fair too
        g["L2_fairness"] = {"passed": not fair.get("violations"), **fair, "rechecked_after_coverage": True}
    g["L2b_coverage"] = {"passed": not cov["missing"], **cov}
    log(f"    L2b coverage     {_ok(g['L2b_coverage'])} {cov['missing'] or ''}")

    # L3 interface
    g["L3_interface"] = interface_check(task, files)
    log(f"    L3 interface     {_ok(g['L3_interface'])} {g['L3_interface'].get('undeclared') or ''}")

    # L4-L6 with test-strengthening loop
    for rnd in range(TH["repair_rounds"] + 1):
        if not _l4(task, repo, g, log):
            break
        _l5(task, repo, g, log)
        survivors = _l6(task, repo, files, cfg, g, log)
        rep["history"].append({"round": rnd, "kill_rate": g["L6_mutation"]["kill_rate"],
                               "n_f2p": len(task["f2p"])})
        if g["L6_mutation"]["passed"] or rnd == TH["repair_rounds"]:
            break
        log(f"    ↻ strengthen tests (round {rnd + 1}): {len(survivors)} wrong implementations survived")
        task["test_src"] = generate.strengthen_tests(spec, test_path, task["test_src"], survivors, cfg.test_model)
    if len(rep["history"]) > 1:  # tests changed → re-audit fairness + interface on the final test file
        fair = generate.judge_fairness(spec, task["test_src"], cfg.gen_model)
        g["L2_fairness"] = {"passed": not fair.get("violations"), **fair, "rechecked_after_repair": True}
        g["L3_interface"] = interface_check(task, files)

    # L7 solvability (strong) + difficulty probe (weak)
    if g.get("L4_f2p_p2p", {}).get("passed"):
        _l7(task, repo, files, cfg, g, log)
    return _decide(rep)


def _overlays(task):
    return {task["test_path"]: task["test_src"]}


def _l4(task, repo, g, log) -> bool:
    graded_files = task["p2p_files"] + [task["test_path"]]
    gold = run_candidate(repo, task["gold"], _overlays(task), test_files=graded_files)
    base = run_candidate(repo, _overlays(task), test_files=graded_files)
    feat_ids = ids_in_files(gold.results, [task["test_path"]])
    f2p = [t for t in feat_ids if gold.passed(t) and not base.passed(t)]
    feat_fail_on_gold = [t for t in feat_ids if not gold.passed(t)]
    reg_ids = ids_in_files(base.results, task["p2p_files"])
    p2p = [t for t in reg_ids if base.passed(t) and gold.passed(t)]
    broken = [t for t in reg_ids if base.passed(t) and not gold.passed(t)]
    task["f2p"], task["p2p"] = f2p, p2p

    # whole upstream suite under the gold (not shipped — the package keeps the curated P2P set — but it catches
    # collateral breakage in modules the curated set does not cover). Gold doesn't change across repair rounds.
    if "_full_regressions" not in task and task.get("_base_full"):
        full = run_candidate(repo, task["gold"], timeout=900)
        task["_full_regressions"] = sorted(t for t, s in task["_base_full"].items()
                                           if s == "PASSED" and not full.passed(t))
    collateral = task.get("_full_regressions", [])

    res = {"passed": len(f2p) >= TH["min_f2p"] and not feat_fail_on_gold and not broken and not collateral
                     and len(p2p) >= TH["min_p2p"],
           "full_suite_regressions": collateral[:20],
           "full_suite_checked": bool(task.get("_base_full")),
           "f2p": len(f2p), "feature_tests": len(feat_ids), "feature_pass_at_base": len(feat_ids) - len(f2p) - len(feat_fail_on_gold),
           "feature_fail_on_gold": feat_fail_on_gold[:10], "p2p": len(p2p), "regressions_from_gold": broken[:10],
           "gold_output_tail": gold.output[-1500:] if feat_fail_on_gold or broken or not feat_ids else ""}
    g["L4_f2p_p2p"] = res
    log(f"    L4 F2P/P2P       {_ok(res)} F2P={len(f2p)}/{len(feat_ids)} P2P={len(p2p)} "
        f"gold_fails={len(feat_fail_on_gold)} regressions={len(broken)} full_suite_regressions={len(collateral)}")
    return res["passed"]


def _l5(task, repo, g, log):
    expect = set(task["f2p"]) | set(task["p2p"])
    r = run_candidate(repo, task["gold"], _overlays(task), test_files=task["p2p_files"] + [task["test_path"]])
    flaky = sorted(t for t in expect if not r.passed(t))
    g["L5_determinism"] = {"passed": not flaky, "flaky": flaky}
    log(f"    L5 determinism   {_ok(g['L5_determinism'])}")


def _l6(task, repo, files, cfg, g, log) -> list[dict]:
    wrong = []
    for path, src in task["gold"].items():
        for desc, mutated in generate_mutants(files.get(path), src, TH["max_mutants"]):
            wrong.append(("ast", f"{path}: {desc}", {path: mutated}))
    gold_files = {**files, **task["gold"]}
    gold_diff = task.get("gold_diff") or git_diff(repo, task["gold"])
    for req in task["spec"]["requirements"][:TH["n_near_miss"]]:
        try:
            desc, ov = generate.write_near_miss(task["spec"], gold_diff, gold_files, req, cfg.gen_model)
            if ov and ov != {p: task["gold"].get(p) for p in ov}:
                wrong.append(("near_miss", desc, ov))
        except Exception as e:  # noqa: BLE001
            log(f"      near-miss failed: {e}")
    results, survivors = [], []
    for kind, desc, ov in wrong:
        r = run_candidate(repo, task["gold"], ov, _overlays(task), test_files=[task["test_path"]],
                          extra_args=["-x"], timeout=120)
        results.append({"kind": kind, "description": desc, "killed": r.any_failure})
        if r.any_failure and (kind == "near_miss" or "killed_example" not in task):
            task["killed_example"] = {"kind": kind, "description": desc, "overlay": ov}  # reused in container check
        if not r.any_failure:
            survivors.append({"kind": kind, "description": desc})
    n = len(results)
    rate = sum(x["killed"] for x in results) / n if n else 0.0
    nm_ok = all(x["killed"] for x in results if x["kind"] == "near_miss")
    g["L6_mutation"] = {"passed": n > 0 and rate >= TH["min_kill_rate"] and nm_ok, "kill_rate": round(rate, 3),
                        "n_wrong": n, "survivors": survivors,
                        "note": "surviving AST mutants may be equivalent; survivors listed for inspection"}
    log(f"    L6 mutation      {_ok(g['L6_mutation'])} kill_rate={rate:.0%} ({n - len(survivors)}/{n})")
    for s in survivors[:6]:
        log(f"        survived [{s['kind']}] {s['description']}")
    return survivors


def _l7(task, repo, files, cfg, g, log):
    from .analyze import source_dump
    text = generate.instruction_md(task["spec"])
    ctx = source_dump(repo, task["slot"]["modules"], example_tests=task["p2p_files"][:1])
    graded = task["f2p"] + task["p2p"]

    def attempt(model, variant, role):
        try:
            ov, errs = generate.write_gold(task["spec"], ctx, files, model, variant=variant, role=role,
                                           temperature=0.7, text=text)
        except Exception as e:  # noqa: BLE001 — an unavailable solver model must not sink the whole task
            log(f"      {role} {model} unavailable: {str(e)[:160]}")
            return {"model": model, "passed": False, "f2p_passed": 0, "errors": [str(e)[:300]], "unavailable": True}
        if not ov:
            return {"model": model, "passed": False, "f2p_passed": 0, "errors": errs[:3]}
        r = run_candidate(repo, ov, _overlays(task), test_files=task["p2p_files"] + [task["test_path"]])
        fails = [t for t in graded if not r.passed(t)]
        return {"model": model, "passed": not fails, "failed_tests": fails[:10],
                "f2p_passed": sum(r.passed(t) for t in task["f2p"])}

    strong = [attempt(m, f"solver{i}", "solver") for i, m in enumerate(cfg.solver_models)]
    probe = attempt(cfg.probe_model, "probe", "probe") if cfg.probe_model else None
    per_test = {}
    for s in strong:
        for t in s.get("failed_tests", []):
            per_test[t] = per_test.get(t, 0) + 1
    vendors = {}
    for s in strong:
        if s.get("unavailable"):
            continue
        v = _vendor(s["model"])
        vendors[v] = vendors.get(v, False) or s["passed"]
    gold_vendor = _vendor(cfg.gen_model)
    cross = {v: ok for v, ok in vendors.items() if v != gold_vendor}
    g["L7_solvability"] = {
        "passed": any(s["passed"] for s in strong), "strong": strong,
        "vendors_passing": vendors,
        # a solver from a different model family than the gold/test writers agreeing with the tests is the
        # strongest evidence that gold + tests do not share one model's misreading of the spec
        "cross_vendor_agrees": (any(cross.values()) if cross else None),
        "suspicious_tests": sorted(t for t, c in per_test.items() if c == len(strong) and len(strong) > 1)}
    if cross and not any(cross.values()):
        g["L7_solvability"]["warning"] = "only same-vendor solvers pass: possible shared misreading of the spec"
    g["L7_difficulty_probe"] = {"probe": probe, "likely_easy": bool(probe and probe["passed"])}
    log(f"    L7 solvable      {_ok(g['L7_solvability'])} strong={sum(s['passed'] for s in strong)}/{len(strong)}"
        f" vendors={vendors}"
        f"  probe({cfg.probe_model})={'SOLVED (easy?)' if probe and probe['passed'] else 'failed (good)'}")


def interface_check(task: dict, base_files: dict) -> dict:
    base_syms = {q.split(".")[-1] for p, s in base_files.items() if not is_test_path(p) for q in defined_symbols(s)}
    new_syms = {q.split(".")[-1] for src in task["gold"].values() for q in defined_symbols(src)} - base_syms
    declared = " ".join(f"{i.get('symbol', '')} {i.get('signature', '')}" for i in task["spec"].get("interface", []))
    declared += " " + " ".join(r["text"] for r in task["spec"].get("requirements", []))
    used = set()
    try:
        for node in ast.walk(ast.parse(task["test_src"])):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.alias):
                used.add(node.name.split(".")[-1])
            elif isinstance(node, ast.keyword) and node.arg:
                used.add(node.arg)
    except SyntaxError as e:
        return {"passed": False, "error": str(e)}
    undeclared = sorted(s for s in used & new_syms if s not in declared and not s.startswith("_"))
    private = sorted(s for s in used & new_syms if s.startswith("_") and not s.startswith("__"))
    return {"passed": not undeclared and not private, "undeclared": undeclared, "private_used": private}


def _vendor(model: str) -> str:
    """anthropic:claude-x -> anthropic ; openrouter:openai/gpt-x -> openai ; openrouter:anthropic/... -> anthropic"""
    provider, _, name = model.partition(":")
    return name.split("/")[0] if provider == "openrouter" and "/" in name else provider


def _ok(gate):
    return "PASS" if gate.get("passed") else "FAIL"


def _decide(rep):
    g = rep["gates"]
    hard = ["L1_structure", "L2_fairness", "L2b_coverage", "L3_interface", "L4_f2p_p2p", "L5_determinism",
            "L6_mutation", "L7_solvability"]
    failed = [k for k in hard if not g.get(k, {}).get("passed")]
    rep["decision"] = "accept" if not failed else "reject"
    rep["failed_gates"] = failed
    rep["warnings"] = [w for w in [g.get("L7_solvability", {}).get("warning")] if w]
    rep["likely_easy"] = g.get("L7_difficulty_probe", {}).get("likely_easy", False)
    return rep
