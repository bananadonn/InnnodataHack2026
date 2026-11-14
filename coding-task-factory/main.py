"""Coding Task Factory — Track 1 CLI.

  python main.py generate --repo-dir ./work/click --base-commit <sha> --out generated_tasks --n 5
  python main.py selfcheck generated_tasks/*
  python main.py bench generated_tasks/*
  python main.py report --run runs/<run_id>

See README.md for setup.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def _load_dotenv(path: Path) -> None:
    """KEY=VALUE lines from .env (git-ignored) → environment, without overriding variables already set."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parent / ".env")

# make `harbor` (installed in this venv) and Docker Desktop's user-level CLI findable even when the venv is not
# activated (e.g. `.venv/bin/python main.py ...`)
os.environ["PATH"] = os.pathsep.join(p for p in [str(Path(sys.executable).parent),
                                                  str(Path.home() / ".docker" / "bin"), os.environ.get("PATH", "")] if p)

from factory import generate, harbor, novelty, telemetry
from factory.analyze import py_files, related_test_files, source_dump
from factory.config import Config
from factory.plan import near_duplicate, plan_slots
from factory.sandbox import git_diff, run_pytest
from factory.validate import run_gates


def log(msg: str) -> None:
    print(msg, flush=True)


def snake(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


# ------------------------------------------------------------------ generate

def cmd_generate(a):
    cfg = Config(base_commit=a.base_commit, n_tasks=a.n)
    repo = Path(a.repo_dir).resolve()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != cfg.base_commit:
        raise SystemExit(f"{repo} is at {head}, expected base_commit {cfg.base_commit} (git checkout it first)")
    run_dir = Path(a.runs) / time.strftime("%Y%m%d-%H%M%S")
    telemetry.init(run_dir)
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(cfg.__dict__, indent=1))
    log(f"run dir: {run_dir}")

    log("== base health: full upstream suite at base_commit ==")
    base = run_pytest(repo, timeout=900)
    n_fail = sum(s in ("FAILED", "ERROR") for s in base.results.values())
    log(f"   {len(base.results)} tests, {n_fail} failing")
    if n_fail or not base.results:
        raise SystemExit("base suite is not green — choose another base_commit\n" + base.output[-2000:])

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    slots = plan_slots(repo, cfg.n_tasks, seed=a.seed)
    if a.only_slot is not None:
        slots = [slots[a.only_slot]]
    (run_dir / "slots.json").write_text(json.dumps(slots, indent=1))
    accepted, funnel = [], {"slots": len(slots), "specs_proposed": 0, "duplicates": 0, "not_novel": 0,
                            "gold_failed": 0, "gates_rejected": 0, "valid": 0, "hardening_rounds": 0,
                            "hardened_ok": 0, "still_easy": 0, "agent_probes": 0, "accepted": 0}
    files = py_files(repo)
    lock = threading.Lock()
    valid_per_slot = max(1, a.valid_per_slot)

    def bump(key, n=1):
        with lock:
            funnel[key] += n

    def save_report(sid, task):
        (run_dir / "reports" / f"{sid}__{task['instance_id']}.json").write_text(json.dumps(
            {k: v for k, v in task.items() if k not in ("gold", "killed_example") and not k.startswith("_")},
            indent=1, default=str))

    def process_slot(slot):
        """Generate → gate → harden; returns the slot's VALID candidates (best first)."""
        sid = slot["slot_id"]

        def slog(msg):
            log(f"[{sid}] {msg}")

        slog(f"######## {slot['capability']} × {slot['shape_id']}")
        telemetry.start_slot(sid)
        valid, feedback = [], ""
        try:
            for attempt in range(cfg.max_attempts_per_slot):
                if sum(not v["report"]["likely_easy"] for v in valid) >= valid_per_slot or \
                        len(valid) >= 2 * valid_per_slot:
                    break
                telemetry.new_attempt()
                ctx = source_dump(repo, slot["modules"], example_tests=related_test_files(repo, slot["modules"], 1))
                with lock:
                    others = [t["spec"] for t in accepted]
                try:
                    specs = generate.propose_specs(slot, ctx, [o["title"] for o in others] +
                                                   [v["spec"]["title"] for v in valid],
                                                   cfg.candidates_per_slot, cfg.gen_model, feedback,
                                                   variant=f"{sid}-attempt{attempt}")
                except Exception as e:  # noqa: BLE001
                    slog(f"  spec generation failed: {e}")
                    continue
                bump("specs_proposed", len(specs))
                for spec in specs:
                    if sum(not v["report"]["likely_easy"] for v in valid) >= valid_per_slot:
                        break
                    slog(f"  candidate: {spec.get('title')}")
                    dup = near_duplicate(spec, others + [v["spec"] for v in valid])
                    if dup:
                        bump("duplicates")
                        slog(f"    ✗ near-duplicate of {dup}")
                        continue
                    nov = novelty.check(spec, cfg.source_repo, ctx, cfg.gen_model)
                    if not nov.get("novel"):
                        bump("not_novel")
                        slog(f"    ✗ not novel: {nov.get('reason')}")
                        continue
                    task = build_task(spec, slot, repo, files, ctx, cfg)
                    if task is None:
                        bump("gold_failed")
                        continue
                    task["novelty"] = nov
                    task["report"] = run_gates(task, repo, cfg, log=slog, base_full=base.results)
                    save_report(sid, task)
                    if task["report"]["decision"] != "accept":
                        bump("gates_rejected")
                        slog(f"    ✗ rejected: {task['report']['failed_gates']}")
                        feedback = f"previous candidate failed gates {task['report']['failed_gates']}"
                        continue
                    bump("valid")
                    # C. difficulty hardening: grow an easy-but-valid task instead of throwing it away
                    for rnd in range(1, a.harden_rounds + 1):
                        if not task["report"]["likely_easy"]:
                            break
                        bump("hardening_rounds")
                        telemetry.new_attempt()
                        slog(f"    ↑ hardening round {rnd}: probe solved it one-shot")
                        hard = harden_task(task, slot, repo, files, ctx, cfg, rnd, slog, base.results)
                        if hard is None or hard["report"]["decision"] != "accept":
                            slog("    ↑ hardened version failed the gates → keep the previous valid version")
                            break
                        save_report(sid, hard)
                        task = hard
                        if not task["report"]["likely_easy"]:
                            bump("hardened_ok")
                            slog("    ↑ hardened version is valid and the probe no longer solves it")
                    if task["report"]["likely_easy"]:
                        bump("still_easy")
                        feedback = (f"'{task['spec']['title']}' stayed solvable one-shot by a small model — design a "
                                    "harder task: more interacting rules and deeper integration with existing "
                                    "behavior, still fully specified")
                    valid.append(task)
                    slog(f"    ✓ valid candidate #{len(valid)} (probe {'solved' if task['report']['likely_easy'] else 'failed'})")
        except Exception as e:  # noqa: BLE001 — one crashing slot must not kill the other four
            slog(f"  ✗ slot crashed: {type(e).__name__}: {e}")
        telemetry.end_slot(None)
        valid.sort(key=lambda v: (v["report"]["likely_easy"], -v["spec"].get("hardening_rounds", 0)))
        return slot, valid

    workers = max(1, min(a.workers, len(slots)))
    log(f"\nrunning {len(slots)} slot(s) with {workers} parallel worker(s), {valid_per_slot} valid candidate(s) wanted per slot")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        slot_results = list(pool.map(process_slot, slots))

    # D. selection: run the REAL benchmark harness once per candidate, keep the hardest per slot
    use_agent = (not a.no_container) and (not a.no_agent_select) and bool(shutil.which("harbor"))
    if not use_agent and any(len(v) > 1 for _, v in slot_results):
        log("\n(agent selection skipped: needs harbor + Docker; picking by one-shot probe instead)")

    def select(item):
        slot, valid = item
        sid = slot["slot_id"]
        telemetry.start_slot(sid)
        winner = None
        try:
            if valid and use_agent and (len(valid) > 1 or a.agent_probe_single):
                cand_root = run_dir / "candidates" / sid
                scored = []
                for i, t in enumerate(valid):
                    t["gold_diff"] = git_diff(repo, t["gold"])
                    d = harbor.export(t, repo, cfg, cand_root)
                    bump("agent_probes")
                    r = harbor.agent_probe(d, cfg, run_dir / "selection_jobs")
                    t["agent_probe"] = r
                    log(f"[{sid}] agent probe {t['instance_id']}: {r['outcome']} reward={r['reward']}")
                    scored.append(t)
                # hardest first: not resolved, lowest reward; unknown (infra) after real misses; then one-shot probe
                def key(t):
                    r = t["agent_probe"]
                    rew = r["reward"] if r["reward"] is not None else 0.5
                    return (bool(r["resolved"]), rew, t["report"]["likely_easy"])
                winner = sorted(scored, key=key)[0]
            elif valid:
                winner = valid[0]
            if winner is not None:
                winner["gold_diff"] = git_diff(repo, winner["gold"])
                with lock:
                    taken = {t["instance_id"] for t in accepted}
                    if winner["instance_id"] in taken:
                        winner["instance_id"] = harbor.instance_id(cfg, f"{winner['spec'].get('slug', 'task')}-{sid.split('-')[0]}")
                    d = harbor.export(winner, repo, cfg, out)
                    accepted.append(winner)
                    funnel["accepted"] += 1
                log(f"[{sid}] ✓ exported {d}" + (f"  (chosen from {len(valid)} candidates)" if len(valid) > 1 else ""))
            else:
                log(f"[{sid}] ✗ slot produced no valid task")
        finally:
            telemetry.end_slot(winner["instance_id"] if winner else None)
            with lock:
                telemetry.write_pipeline_run(Path(a.pipeline_run), cfg.pipeline_name, {"funnel": dict(funnel)})

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(select, slot_results))
    accepted.sort(key=lambda t: t["slot"]["slot_id"])

    # authoritative container checks
    sc = None
    task_dirs = [out / t["instance_id"] for t in accepted]
    if task_dirs and not a.no_container and shutil.which("harbor"):
        log("\n== container self-check (organizer lint + harbor oracle/nop) ==")
        sc = harbor.selfcheck(task_dirs, run_dir / "evidence")
        log(sc["selfcheck_tail"])
        for t in accepted:
            ke = t.get("killed_example")
            if ke:
                mdiff = git_diff(repo, {**t["gold"], **ke["overlay"]})
                r = harbor.container_mutation(out / t["instance_id"], mdiff, run_dir / "evidence")
                t["container_mutation"] = {"mutant": ke["description"], "reward": r, "caught": r is not None and r < 1.0}
                log(f"  mutation in container {t['instance_id']}: reward={r} ({'caught' if r is not None and r < 1.0 else 'NOT caught'})")
    elif task_dirs:
        log("\n(container self-check skipped: harbor not on PATH or --no-container)")

    summary = {"run_dir": str(run_dir), "base_commit": cfg.base_commit, "funnel": funnel,
               "tasks": [{"instance_id": t["instance_id"], "slot": t["slot"]["slot_id"], "title": t["spec"]["title"],
                          "f2p": len(t["f2p"]), "p2p": len(t["p2p"]), "p2p_files": t["p2p_files"],
                          "kill_rate_history": [h["kill_rate"] for h in t["report"]["history"]],
                          "probe_solved": t["report"]["likely_easy"],
                          "hardening_rounds": t["spec"].get("hardening_rounds", 0),
                          "agent_probe": {k: (t.get("agent_probe") or {}).get(k) for k in ("outcome", "reward")}
                          if t.get("agent_probe") else None,
                          "cross_vendor_agrees": t["report"]["gates"].get("L7_solvability", {}).get("cross_vendor_agrees"),
                          "warnings": t["report"].get("warnings", []),
                          "container_sound": (sc or {}).get("sound", {}).get(t["instance_id"]),
                          "container_mutation": t.get("container_mutation")} for t in accepted]}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    telemetry.write_pipeline_run(Path(a.pipeline_run), cfg.pipeline_name, {"funnel": funnel})
    print_summary(summary)


def build_task(spec, slot, repo, files, ctx, cfg):
    generate.normalize_requirement_ids(spec)
    gold, problems, gold_history = generate.write_gold_checked(spec, ctx, files, cfg.gen_model, repo,
                                                               max_repairs=cfg.gold_repairs, log=log)
    if not gold or problems:
        log(f"    ✗ no usable gold: {(problems or ['empty patch'])[0].splitlines()[0][:160]}")
        return None
    test_path = f"tests/test_{snake(spec.get('slug') or spec['title'])}.py"
    test_ctx = source_dump(repo, slot["modules"], example_tests=related_test_files(repo, list(gold), 1))
    test_src = generate.write_tests(spec, test_ctx, test_path, cfg.test_model)
    p2p_files = related_test_files(repo, [p for p in gold if p.endswith(".py")], limit=3)
    return {"instance_id": harbor.instance_id(cfg, spec.get("slug") or spec["title"]), "slot": slot, "spec": spec,
            "gold": gold, "gold_history": gold_history, "test_path": test_path, "test_src": test_src,
            "p2p_files": p2p_files, "f2p": [], "p2p": []}


def harden_task(task, slot, repo, files, ctx, cfg, rnd, slog, base_full):
    """One hardening round: spec gains 1–2 interacting requirements; the gold is rewritten from base against the
    new spec (independently of the tests); the already-validated tests are kept and extended to cover the new
    requirements; then every gate runs again. Returns the new task (with report) or None."""
    probe = task["report"]["gates"].get("L7_difficulty_probe", {}).get("probe") or {}
    note = (f"a small model implemented it in one shot and passed {probe.get('f2p_passed', '?')}/"
            f"{len(task['f2p'])} feature tests")
    try:
        spec = generate.harden_spec(task["spec"], ctx, cfg.gen_model, note, rnd)
    except Exception as e:  # noqa: BLE001
        slog(f"      hardening spec failed: {e}")
        return None
    new_ids = [r["id"] for r in spec["requirements"][len(task["spec"]["requirements"]):]]
    if not new_ids:
        slog("      hardening added no new requirement")
        return None
    slog(f"      + {len(new_ids)} new requirement(s): " + " | ".join(r["text"][:90] for r in spec["requirements"]
                                                           if r["id"] in new_ids))
    gold, problems, gold_history = generate.write_gold_checked(spec, ctx, files, cfg.gen_model, repo,
                                                               variant=f"gold-h{rnd}", max_repairs=cfg.gold_repairs,
                                                               log=slog)
    if not gold or problems:
        slog(f"      hardened gold failed its self-check: {(problems or ['empty patch'])[0].splitlines()[0][:160]}")
        return None
    test_src = generate.add_coverage_tests(spec, task["test_path"], task["test_src"], new_ids, cfg.test_model)
    new = {**{k: v for k, v in task.items() if k not in ("report", "killed_example", "_full_regressions",
                                                           "agent_probe", "gold_diff")},
           "spec": spec, "gold": gold, "gold_history": gold_history, "test_src": test_src, "f2p": [], "p2p": [],
           "p2p_files": related_test_files(repo, [p for p in gold if p.endswith(".py")], limit=3)}
    new["report"] = run_gates(new, repo, cfg, log=slog, base_full=base_full)
    return new


def print_summary(s):
    log("\n================ SUMMARY ================")
    log(f"funnel: {json.dumps(s['funnel'])}")
    for t in s["tasks"]:
        log(f"{t['instance_id']:<55} F2P={t['f2p']:<3} P2P={t['p2p']:<4} kill={t['kill_rate_history']} "
            f"probe_solved={t['probe_solved']} container_sound={t['container_sound']}")


# ------------------------------------------------------------------ selfcheck / bench / report

def cmd_selfcheck(a):
    r = harbor.selfcheck([Path(p) for p in a.tasks], Path(a.evidence))
    print(r["lint"])
    print(r["selfcheck_tail"])


def cmd_bench(a):
    cfg = Config()
    results = []
    for p in a.tasks:
        log(f"== benchmark {p} ({cfg.bench_agent} / {cfg.bench_model}, k={cfg.bench_k}) ==")
        r = harbor.benchmark(Path(p), cfg, Path(a.jobs), Path(a.trajectory))
        log(f"   resolve@{cfg.bench_k} = {r['resolve_rate']}  outcomes={r['outcomes']}  infra_excluded={len(r['infra_failures'])}")
        results.append(r)
    dist = {}
    for r in results:
        dist[r["resolve_rate"]] = dist.get(r["resolve_rate"], 0) + 1
    out = {"model": cfg.bench_model, "agent": cfg.bench_agent, "k": cfg.bench_k, "distribution": dist, "tasks": results}
    Path(a.summary).write_text(json.dumps(out, indent=1))
    log(f"distribution: {dist}  -> {a.summary}")


def cmd_report(a):
    s = json.loads((Path(a.run) / "summary.json").read_text())
    print_summary(s)


def cmd_validate(a):
    """Validate finished Harbor packages from ANY producer (our generator or teammates' SDK)."""
    from factory.package_validate import batch_checks, validate_package
    cfg = Config()
    out = Path(a.out) / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    cfg.evidence_dir = str(out / "evidence")
    telemetry.init(out)
    repo = Path(a.repo_dir).resolve()
    pkgs = [Path(p) for p in a.packages if (Path(p) / "task.toml").exists() or (Path(p) / "instruction.md").exists()]
    log(f"validating {len(pkgs)} package(s) against {repo}  (llm={a.llm}, container={a.container}) -> {out}")
    log("== base: full upstream suite ==")
    base = run_pytest(repo, timeout=900)
    log(f"   {len(base.results)} tests, {sum(s in ('FAILED', 'ERROR') for s in base.results.values())} failing")

    def one(p):
        telemetry.start_slot(f"validate:{p.name}")
        try:
            return validate_package(p, repo, cfg, base.results, use_llm=a.llm, container=a.container, log=log)
        finally:
            telemetry.end_slot(None)

    with ThreadPoolExecutor(max_workers=max(1, min(a.workers, len(pkgs)))) as pool:
        reports = list(pool.map(one, pkgs))
    batch = batch_checks(reports)
    for r in reports:
        (out / f"{r['instance_id']}.json").write_text(json.dumps(r, indent=1, default=str))
    (out / "batch.json").write_text(json.dumps(batch, indent=1))
    md = render_validation_md(reports, batch)
    (out / "validation_summary.md").write_text(md)
    log("\n" + md)
    log(f"reports: {out}")


def render_validation_md(reports, batch) -> str:
    yn = {True: "✅", False: "❌", None: "—"}
    keys = ["V0_lint", "V1_load", "V2_hygiene", "V3_f2p_p2p", "V4_full_suite", "V5_determinism", "V6_mutation",
            "V7_interface", "V8_coverage", "V9_spec_style", "V10_fairness", "V11_probes", "V12_container"]
    icon = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "·"}
    lines = ["# Validation summary", "",
             "| package | sound | fair | hard | " + " | ".join(k.split("_")[0] for k in keys) + " |",
             "|---|---|---|---|" + "---|" * len(keys)]
    for r in reports:
        g = r["gates"]
        lines.append(f"| {r['instance_id']} | {yn[r['sound']]} | {yn[r['fair']]} | {yn[r['hard']]} | " +
                     " | ".join(icon[g[k]["status"]] if k in g else " " for k in keys) + " |")
    lines += ["", "Legend: ✓ pass · ✗ fail · ! warning · · skipped. sound = judges' mechanical gates (V0–V6); "
              "fair = V7/V8/V10; hard = one-shot probe failed (V11).", "", "## Send back to"]
    for r in reports:
        if r["send_back_to"]:
            lines.append(f"\n**{r['instance_id']}**")
            for owner, items in r["send_back_to"].items():
                for it in items:
                    lines.append(f"- `{owner}` {it}")
    lines += ["", "## Batch variation", "",
              f"- {batch['n_packages']} packages, {batch['distinct_touched_file_sets']} distinct touched-file sets"]
    for p in batch["similar_pairs"]:
        lines.append(f"- ⚠ similar: {p['a']} ↔ {p['b']} (token overlap {p['token_jaccard']}, "
                     f"same files {p['same_touched_files']})")
    if not batch["similar_pairs"]:
        lines.append("- no near-duplicate pairs detected")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("generate")
    p.add_argument("--repo-dir", required=True, help="local clone of the supplied repo, checked out at base_commit")
    p.add_argument("--base-commit", required=True)
    p.add_argument("--out", default="generated_tasks")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--seed", type=int, default=0, help="changes slot assignment (fresh batch)")
    p.add_argument("--only-slot", type=int, help="generate just one slot (live demo)")
    p.add_argument("--runs", default="runs")
    p.add_argument("--pipeline-run", default="pipeline_run.json")
    p.add_argument("--no-container", action="store_true")
    p.add_argument("--workers", type=int, default=int(os.environ.get("CTF_WORKERS", "5")),
                   help="slots processed in parallel (lower it if you hit API rate limits)")
    p.add_argument("--valid-per-slot", type=int, default=2,
                   help="valid candidates to collect per slot before selecting the hardest (1 = no selection)")
    p.add_argument("--harden-rounds", type=int, default=2,
                   help="max difficulty-hardening rounds for a valid task the one-shot probe solves (0 = off)")
    p.add_argument("--no-agent-select", action="store_true",
                   help="pick among candidates by the one-shot probe only (no terminus-2 run)")
    p.add_argument("--agent-probe-single", action="store_true",
                   help="also run the terminus-2 probe when a slot has only one candidate (difficulty evidence)")
    p = sub.add_parser("selfcheck")
    p.add_argument("tasks", nargs="+")
    p.add_argument("--evidence", default="evidence")
    p = sub.add_parser("bench")
    p.add_argument("tasks", nargs="+")
    p.add_argument("--jobs", default="jobs")
    p.add_argument("--trajectory", default="trajectory")
    p.add_argument("--summary", default="bench_summary.json")
    p = sub.add_parser("report")
    p.add_argument("--run", required=True)
    p = sub.add_parser("validate", help="validate finished Harbor packages from any producer")
    p.add_argument("packages", nargs="+", help="package dirs (each containing task.toml)")
    p.add_argument("--repo-dir", required=True, help="local clone checked out at the packages' base_commit")
    p.add_argument("--llm", action="store_true", help="also run LLM gates: fairness audit + solver/difficulty probes")
    p.add_argument("--container", action="store_true", help="also run harbor oracle/nop + corrupted-gold in Docker")
    p.add_argument("--out", default="runs/validation")
    p.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    {"generate": cmd_generate, "selfcheck": cmd_selfcheck, "bench": cmd_bench, "report": cmd_report,
     "validate": cmd_validate}[a.cmd](a)


if __name__ == "__main__":
    main()
