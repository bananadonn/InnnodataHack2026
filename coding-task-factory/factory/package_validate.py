"""Validate finished Harbor packages, regardless of which tool produced them.

Three questions, in the order the judges care about them, each answered by gates:

  SOUND  (judges' mechanical gates; must all pass)
    V0 lint            organizer check_structure.py
    V1 load            task.toml parses, base_commit matches, both patches apply to base
    V2 hygiene         gold never touches test files; gold and test patch share no file
    V3 F2P/P2P         re-measured locally and compared with the declared lists (catches mislabeled IDs)
    V4 full suite      the whole upstream suite stays green under the gold
    V5 determinism     re-running the gold gives the same results
    V6 mutation        AST mutants of the gold's changed functions must make feature tests fail
  FAIR   (fairness dimension)
    V7 interface       tests only use existing API + symbols named in instruction.md
    V8 coverage        every numbered behavior has a test (only when tests carry `# R<n>` annotations)
    V9 spec style      requirements that prescribe *how* to implement (call order, internal helpers) → warning
    V10 fairness LLM   every fact a test asserts is stated in instruction.md            [--llm]
  HARD   (difficulty dimension)
    V11 probes         strong blind solver must pass (solvable); one-shot benchmark-family probe should fail [--llm]
  CONTAINER (authoritative)
    V12 harbor         oracle 1.0 / nop 0.0 via the organizer selfcheck + one corrupted gold through the oracle [--container]

Every failed gate names an OWNER so the report doubles as the "send it back to whom" list:
  spec    → task/spec generator (SDK: explore/generate/refine agents)
  tests   → test generator
  gold    → whoever writes the reference implementation
  package → whoever assembles the Harbor package
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from . import generate, harbor
from .analyze import is_test_path, py_files, related_test_files, source_dump
from .mutate import generate_mutants
from .package import load_package
from .plan import token_set
from .sandbox import git_diff, ids_in_files, run_candidate
from .validate import interface_check

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "vendor" / "innodata_kit"
TH = {"min_f2p": 3, "min_p2p": 5, "min_kill_rate": 0.8, "max_mutants": 15, "probe_k": 2,
      "p2p_relevance": 0.5}

PRESCRIPTIVE = re.compile(
    r"\b(calls?|invokes?|must (not )?call|internally|under the hood|implementation detail|private helper|"
    r"in that order|then calls?|delegat\w+ to|uses? `?json\.dumps|via `?self\.)\b", re.I)


def gate(status: str, owner: str | None, summary: str, **details) -> dict:
    return {"status": status, "owner": owner, "summary": summary, "details": details}


def validate_package(pkg_dir: Path, repo: Path, cfg, base_full: dict, use_llm=False, container=False,
                     log=print) -> dict:
    g: dict[str, dict] = {}
    pkg_dir = Path(pkg_dir)

    # V0 organizer lint
    lint = subprocess.run([sys.executable, str(KIT / "check_structure.py"), str(pkg_dir)], capture_output=True, text=True)
    errors = [ln.strip() for ln in lint.stdout.splitlines() if ln.strip().startswith("ERROR")]
    warns = [ln.strip() for ln in lint.stdout.splitlines() if ln.strip().startswith("warn")]
    g["V0_lint"] = gate("pass" if lint.returncode == 0 else "fail", "package",
                        f"{len(errors)} errors, {len(warns)} warnings", errors=errors, warnings=warns)

    # V1 load
    t = load_package(pkg_dir, repo)
    g["V1_load"] = gate("fail" if t["load_errors"] else "pass", "package",
                        "; ".join(t["load_errors"]) or "patches apply cleanly to base_commit", errors=t["load_errors"])
    _log(log, t["instance_id"], g, "V0_lint", "V1_load")
    if t["load_errors"]:
        return _finish(t, g)

    # V2 patch hygiene
    gold_tests = sorted(p for p in t["gold"] if is_test_path(p))
    shared = sorted(set(t["gold"]) & set(t["tests"]))
    g["V2_hygiene"] = gate("fail" if gold_tests or shared else "pass", "gold",
                           "gold edits test files" if gold_tests else ("gold and test patch share files" if shared
                                                                       else "gold/test patches disjoint"),
                           gold_touches_tests=gold_tests, shared_files=shared)

    # V3 F2P / P2P re-measured
    files = t["graded_files"]
    base_run = run_candidate(repo, t["tests"], test_files=files)
    gold_run = run_candidate(repo, t["gold"], t["tests"], test_files=files)
    f2p, p2p = t["f2p_declared"], t["p2p_declared"]
    missing = [x for x in f2p + p2p if x not in gold_run.results and x not in base_run.results]
    f2p_pass_base = [x for x in f2p if base_run.passed(x)]
    f2p_fail_gold = [x for x in f2p if x not in missing and not gold_run.passed(x)]
    p2p_fail_base = [x for x in p2p if x not in missing and not base_run.passed(x)]
    p2p_broken = [x for x in p2p if base_run.passed(x) and not gold_run.passed(x)]
    feat_files = [p for p in t["tests"] if p.endswith(".py")]
    undeclared = [x for x in ids_in_files(gold_run.results, feat_files)
                  if gold_run.passed(x) and not base_run.passed(x) and x not in f2p]
    related = set(related_test_files(repo, [p for p in t["gold"] if p.endswith(".py")], limit=6))
    p2p_related = sum(1 for x in p2p if x.split("::")[0] in related)
    problems, owner = [], None
    for cond, msg, who in [(missing, f"{len(missing)} declared test IDs never ran (name/parametrize mismatch)", "package"),
                           (f2p_fail_gold, f"{len(f2p_fail_gold)} F2P fail with the gold", "gold"),
                           (p2p_broken, f"{len(p2p_broken)} P2P broken by the gold", "gold"),
                           (f2p_pass_base, f"{len(f2p_pass_base)} F2P already pass at base", "tests"),
                           (p2p_fail_base, f"{len(p2p_fail_base)} P2P fail at base (wrong/flaky IDs)", "package"),
                           (len(f2p) < TH["min_f2p"], f"only {len(f2p)} F2P tests", "tests"),
                           (len(p2p) < TH["min_p2p"], f"only {len(p2p)} P2P tests", "tests")]:
        if cond:
            problems.append(msg)
            owner = owner or who
    g["V3_f2p_p2p"] = gate("fail" if problems else "pass", owner,
                           "; ".join(problems) or f"F2P {len(f2p)}/{len(f2p)} gold, 0 at base; P2P {len(p2p)} green",
                           f2p=len(f2p), p2p=len(p2p), missing_ids=missing[:10], f2p_fail_on_gold=f2p_fail_gold[:10],
                           f2p_pass_at_base=f2p_pass_base[:10], p2p_fail_at_base=p2p_fail_base[:10],
                           p2p_broken_by_gold=p2p_broken[:10], undeclared_feature_tests=undeclared[:10],
                           p2p_in_related_files=f"{p2p_related}/{len(p2p)}",
                           gold_output_tail=gold_run.output[-1200:] if (f2p_fail_gold or p2p_broken) else "")
    if p2p and p2p_related / len(p2p) < TH["p2p_relevance"]:
        g["V3b_p2p_relevance"] = gate("warn", "tests", f"only {p2p_related}/{len(p2p)} P2P tests are in test files "
                                      "that exercise the touched modules (judges want a curated, relevant set)",
                                      related_files=sorted(related))

    # V4 full upstream suite under the gold
    if base_full:
        full = run_candidate(repo, t["gold"], timeout=900)
        coll = sorted(x for x, s in base_full.items() if s == "PASSED" and not full.passed(x))
        g["V4_full_suite"] = gate("fail" if coll else "pass", "gold",
                                  f"{len(coll)} upstream tests broken by the gold" if coll else
                                  f"all {sum(s == 'PASSED' for s in base_full.values())} upstream tests still pass",
                                  broken=coll[:20])
    # V5 determinism
    again = run_candidate(repo, t["gold"], t["tests"], test_files=files)
    flaky = sorted(x for x in f2p + p2p if gold_run.passed(x) != again.passed(x))
    g["V5_determinism"] = gate("fail" if flaky else "pass", "tests", f"{len(flaky)} flaky" if flaky else "stable",
                               flaky=flaky[:10])

    # V6 mutation (AST mutants of the gold's changed functions)
    base_files = py_files(repo)
    f2p_files = sorted({x.split("::")[0] for x in f2p})
    results, survivors, killed_example = [], [], None
    for path, src in t["gold"].items():
        if src is None or not path.endswith(".py") or is_test_path(path):
            continue
        for desc, mutated in generate_mutants(base_files.get(path), src, TH["max_mutants"]):
            r = run_candidate(repo, t["gold"], {path: mutated}, t["tests"], test_files=f2p_files,
                              extra_args=["-x"], timeout=120)
            killed = r.any_failure
            results.append(killed)
            if killed and killed_example is None:
                killed_example = (desc, {path: mutated})
            if not killed:
                survivors.append(f"{path}: {desc}")
    rate = sum(results) / len(results) if results else 0.0
    g["V6_mutation"] = gate("pass" if results and rate >= TH["min_kill_rate"] else ("skip" if not results else "fail"),
                            "tests", f"kill rate {rate:.0%} ({sum(results)}/{len(results)})" if results
                            else "no mutable code in gold", kill_rate=round(rate, 3), survivors=survivors[:10],
                            note="survivors may be equivalent mutants — inspect before blaming tests")
    _log(log, t["instance_id"], g, "V2_hygiene", "V3_f2p_p2p", "V4_full_suite", "V5_determinism", "V6_mutation")

    # V7 interface consistency
    ic = interface_check({"gold": {p: c for p, c in t["gold"].items() if c}, "spec": t["spec"],
                          "test_src": t["test_src"]}, base_files)
    g["V7_interface"] = gate("pass" if ic.get("passed") else "fail", "tests" if ic.get("private_used") else "spec",
                             "tests use only declared symbols" if ic.get("passed") else
                             f"tests use new symbols not named in instruction.md: {ic.get('undeclared') or ic.get('private_used')}",
                             **ic)
    # V8 requirement coverage (only if annotated)
    if re.search(r"#.*\bR\d+\b", t["test_src"]):
        cov = generate.requirement_coverage(t["spec"], t["test_src"])
        g["V8_coverage"] = gate("fail" if cov["missing"] else "pass", "tests",
                                f"untested behaviors: {cov['missing']}" if cov["missing"] else
                                f"all {len(t['spec']['requirements'])} numbered behaviors tested", **cov)
    else:
        g["V8_coverage"] = gate("skip", "tests", "tests carry no `# R<n>` annotations; coverage not measurable",
                                n_requirements=len(t["spec"]["requirements"]))
    # V9 prescriptive requirements
    presc = [f"{r['id']}: {r['text'][:120]}" for r in t["spec"]["requirements"] if PRESCRIPTIVE.search(r["text"])]
    g["V9_spec_style"] = gate("warn" if presc else "pass", "spec",
                              f"{len(presc)} requirement(s) prescribe implementation, not behavior "
                              "(fairness risk; also makes the task easier)" if presc else "behavior-only requirements",
                              prescriptive=presc)
    # V10 LLM fairness
    if use_llm:
        fair = generate.judge_fairness(t["spec"], t["test_src"], cfg.gen_model)
        v = fair.get("violations") or []
        g["V10_fairness"] = gate("fail" if v else ("warn" if fair.get("ambiguities") else "pass"), "spec",
                                 f"{len(v)} asserted facts not stated in instruction.md" if v else
                                 ("ambiguities flagged" if fair.get("ambiguities") else "every asserted fact is stated"),
                                 **fair)
    else:
        g["V10_fairness"] = gate("skip", "spec", "needs --llm")
    _log(log, t["instance_id"], g, "V7_interface", "V8_coverage", "V9_spec_style", "V10_fairness")

    # V11 solvability + difficulty probes
    if use_llm:
        focus = [p for p in t["gold"] if p.endswith(".py") and not is_test_path(p)]
        ctx = source_dump(repo, focus, example_tests=[f for f in files if f not in t["tests"]][:1])
        graded = f2p + p2p

        def attempt(model, variant):
            ov, _ = generate.write_gold(t["spec"], ctx, base_files, model, variant=variant, role="probe",
                                        temperature=0.7, text=t["instruction"])
            if not ov:
                return {"model": model, "passed": False, "f2p_passed": 0}
            r = run_candidate(repo, ov, t["tests"], test_files=files)
            return {"model": model, "passed": all(r.passed(x) for x in graded),
                    "f2p_passed": sum(r.passed(x) for x in f2p)}
        strong = [attempt(m, f"{t['instance_id']}-solver{i}") for i, m in enumerate(cfg.solver_models)]
        probes = [attempt(cfg.probe_model, f"{t['instance_id']}-probe{i}") for i in range(TH["probe_k"])]
        solved = sum(p["passed"] for p in probes)
        g["V11_probes"] = gate("fail" if not any(s["passed"] for s in strong) else ("warn" if solved else "pass"),
                               "spec", (f"no strong blind solver passes (unsolvable from text?)"
                                        if not any(s["passed"] for s in strong) else
                                        f"probe solved {solved}/{len(probes)} one-shot → likely easy" if solved else
                                        f"probe failed {len(probes)}/{len(probes)} one-shot (good sign; agent may still solve)"),
                               strong=strong, probes=probes,
                               probe_f2p=[f"{p['f2p_passed']}/{len(f2p)}" for p in probes])
    else:
        g["V11_probes"] = gate("skip", "spec", "needs --llm")

    # V12 container
    if container:
        sc = harbor.selfcheck([pkg_dir], Path(cfg.evidence_dir) / t["instance_id"])
        sound = sc["sound"].get(pkg_dir.name)
        cm = None
        if killed_example:
            cm = harbor.container_mutation(pkg_dir, git_diff(repo, {**t["gold"], **killed_example[1]}),
                                           Path(cfg.evidence_dir) / t["instance_id"])
        ok = bool(sound) and (cm is None or cm < 1.0)
        g["V12_container"] = gate("pass" if ok else "fail", "package",
                                  f"oracle/nop {'sound' if sound else 'NOT sound'}; corrupted gold reward={cm}",
                                  selfcheck_tail=sc["selfcheck_tail"][-800:], mutant=killed_example[0] if killed_example else None,
                                  corrupted_gold_reward=cm)
    else:
        g["V12_container"] = gate("skip", "package", "needs --container (harbor + Docker)")
    _log(log, t["instance_id"], g, "V11_probes", "V12_container")
    return _finish(t, g)


SOUND = ["V0_lint", "V1_load", "V2_hygiene", "V3_f2p_p2p", "V4_full_suite", "V5_determinism", "V6_mutation"]
FAIR = ["V7_interface", "V8_coverage", "V10_fairness"]


def _finish(t, g) -> dict:
    def ok(keys):
        return all(g.get(k, {"status": "skip"})["status"] in ("pass", "warn", "skip") for k in keys) and \
            all(k in g for k in keys if k in SOUND)
    sound = ok(SOUND)
    fair = ok(FAIR)
    probe = g.get("V11_probes", {})
    hard = None if probe.get("status") in (None, "skip") else probe["status"] == "pass"
    routing = {}
    for k, v in g.items():
        if v["status"] in ("fail", "warn"):
            routing.setdefault(v["owner"] or "unassigned", []).append(f"[{v['status']}] {k}: {v['summary']}")
    return {"instance_id": t["instance_id"], "dir": t["dir"], "sound": sound, "fair": fair, "hard": hard,
            "container": g.get("V12_container", {}).get("status"), "gates": g, "send_back_to": routing,
            "touched_files": sorted(t.get("gold", {})), "spec_tokens": sorted(token_set(t["spec"]))[:200]
            if t.get("spec") else []}


def batch_checks(reports: list[dict]) -> dict:
    """Variation sanity across the batch (judges also run a lexical near-duplicate check)."""
    pairs = []
    for i, a in enumerate(reports):
        for b in reports[i + 1:]:
            ta, tb = set(a["spec_tokens"]), set(b["spec_tokens"])
            jac = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
            same_files = sorted(set(a["touched_files"]) & set(b["touched_files"]))
            if jac >= 0.35 or (same_files and set(a["touched_files"]) == set(b["touched_files"])):
                pairs.append({"a": a["instance_id"], "b": b["instance_id"], "token_jaccard": round(jac, 2),
                              "same_touched_files": same_files})
    return {"n_packages": len(reports), "similar_pairs": pairs,
            "distinct_touched_file_sets": len({tuple(r["touched_files"]) for r in reports})}


def _log(log, iid, g, *keys):
    icon = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "·"}
    for k in keys:
        if k in g:
            v = g[k]
            log(f"  [{iid}] {icon[v['status']]} {k:<16} {v['summary']}" +
                (f"   → {v['owner']}" if v["status"] in ("fail", "warn") else ""))
