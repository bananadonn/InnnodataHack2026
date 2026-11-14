"""Harbor packaging (docs/harbor_task_interface.md), container self-check, and benchmark collection.

grade.py / parser.py / test.sh are copied VERBATIM from the organizer kit (vendor/innodata_kit) — the kit says
grade.py is "copied verbatim into every generated task's tests/".
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import telemetry
from .generate import instruction_md
from .sandbox import git_diff

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "vendor" / "innodata_kit"
PYTEST_PIN = "pytest==8.3.5"


def instance_id(cfg, slug: str) -> str:
    org, repo = cfg.source_repo.split("/")
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:40]
    return f"{org}__{repo}-{slug}"


def export(task: dict, repo: Path, cfg, out_root: Path) -> Path:
    iid = task["instance_id"]
    d = out_root / iid
    if d.exists():
        shutil.rmtree(d)
    for sub in ("solution", "tests", "environment"):
        (d / sub).mkdir(parents=True)

    (d / "instruction.md").write_text(instruction_md(task["spec"]))
    (d / "task.toml").write_text(TASK_TOML.format(iid=iid, repo=cfg.source_repo, sha=cfg.base_commit,
                                                  license=cfg.license, lang=cfg.language, net=cfg.network_mode))
    (d / "solution" / "patch.diff").write_text(git_diff(repo, task["gold"]))
    _write_exec(d / "solution" / "solve.sh", SOLVE_SH)
    (d / "tests" / "test_patch.diff").write_text(git_diff(repo, {task["test_path"]: task["test_src"]}))
    (d / "tests" / "fail_to_pass.json").write_text(json.dumps(task["f2p"], indent=2))
    (d / "tests" / "pass_to_pass.json").write_text(json.dumps(task["p2p"], indent=2))
    all_files = "\n".join(f'  "{p}"' for p in task["p2p_files"] + [task["test_path"]])
    _write_exec(d / "tests" / "run_script.sh", RUN_SCRIPT.replace("__FILES__", all_files))
    for f in ("grade.py", "parser.py"):
        shutil.copy(KIT / f, d / "tests" / f)
    _write_exec(d / "tests" / "test.sh", (KIT / "test.sh").read_text())
    (d / "environment" / "Dockerfile").write_text(DOCKERFILE.format(image=cfg.python_image, url=cfg.repo_url,
                                                                    sha=cfg.base_commit, pytest=PYTEST_PIN))
    return d


def _write_exec(p: Path, text: str) -> None:
    p.write_text(text)
    p.chmod(0o755)


# ---------------------------------------------------------------- container self-check

def selfcheck(task_dirs: list[Path], evidence_dir: Path) -> dict:
    """Run the organizer's lint + oracle/nop baselines; save raw output as validation evidence."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    dirs = [str(p) for p in task_dirs]
    lint = subprocess.run(["python3", str(KIT / "check_structure.py"), *dirs], capture_output=True, text=True)
    (evidence_dir / "check_structure.txt").write_text(lint.stdout + lint.stderr)
    env = {**os.environ, "SELFCHECK_OUT": str(evidence_dir / "selfcheck_runs")}
    sc = subprocess.run(["bash", str(KIT / "selfcheck_portable.sh"), *dirs], capture_output=True, text=True, env=env)
    (evidence_dir / "selfcheck.txt").write_text(sc.stdout + sc.stderr)
    status, cur = {}, None
    for line in sc.stdout.splitlines():
        m = re.match(r"== (.+) ==", line)
        if m:
            cur = m.group(1)
            status[cur] = False
        elif cur and "mechanically sound" in line and "✓" in line:
            status[cur] = True
    return {"lint_ok": lint.returncode == 0, "lint": lint.stdout[-3000:], "sound": status,
            "selfcheck_tail": sc.stdout[-3000:]}


def container_mutation(task_dir: Path, mutant_diff: str, evidence_dir: Path) -> float | None:
    """Judges' 'Mutation' gate in the container: gold corrupted -> reward must drop below 1.0."""
    tmp = Path(tempfile.mkdtemp(prefix="mut_")) / task_dir.name
    shutil.copytree(task_dir, tmp)
    (tmp / "solution" / "patch.diff").write_text(mutant_diff)
    out = evidence_dir / "mutation_runs" / task_dir.name
    subprocess.run(["harbor", "run", "-p", str(tmp), "-a", "oracle", "-k", "1", "-o", str(out), "--no-delete", "-y"],
                   capture_output=True, text=True)
    shutil.rmtree(tmp.parent, ignore_errors=True)
    found = sorted(out.rglob("grading_details.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(found[-1].read_text()).get("reward") if found else None


# ---------------------------------------------------------------- benchmark

def benchmark(task_dir: Path, cfg, jobs_root: Path, traj_root: Path, max_reruns: int = 2) -> dict:
    """k rollouts of the benchmark model; infra failures (reward null, API error, truncation) are excluded and
    re-run; timeouts count as genuine misses (benchmark_guide.md)."""
    iid = task_dir.name
    model_dir = cfg.bench_model.split("/")[-1]
    graded, infra, run_no = [], [], 0
    while len(graded) < cfg.bench_k and run_no <= max_reruns:
        need = cfg.bench_k - len(graded)
        out = jobs_root / f"{iid}-bench-{run_no}"
        subprocess.run(["harbor", "run", "-p", str(task_dir), "-a", cfg.bench_agent, "-m", cfg.bench_model,
                        "-k", str(need), "-o", str(out), "--no-delete", "-y"], capture_output=True, text=True)
        for trial in _trial_dirs(out):
            info = _classify(trial, cfg.bench_model)
            (graded if info["counted"] else infra).append({**info, "dir": str(trial)})
        run_no += 1
    graded = graded[:cfg.bench_k]
    dest_root = traj_root / iid / model_dir
    if dest_root.exists():
        shutil.rmtree(dest_root)
    for n, r in enumerate(graded, 1):
        shutil.copytree(r["dir"], dest_root / f"rollout_{n}")
    resolved = sum(r["resolved"] for r in graded)
    return {"instance_id": iid, "model": cfg.bench_model, "k": len(graded), "resolved": resolved,
            "resolve_rate": f"{resolved}/{len(graded)}", "rewards": [r["reward"] for r in graded],
            "outcomes": [r["outcome"] for r in graded],
            "infra_failures": [{"outcome": r["outcome"], "detail": r["detail"]} for r in infra]}


def agent_probe(task_dir: Path, cfg, jobs_root: Path, retries: int = 1) -> dict:
    """Selection signal: ONE rollout of the real benchmark harness (terminus-2 + benchmark model).
    Infra failures (reward null / API error / model mismatch) are retried once and otherwise returned as
    reward=None. The agent's token usage (from harbor's result.json) is charged to the current slot."""
    info = {"reward": None, "resolved": False, "counted": False, "outcome": "infra (no trial produced)", "detail": ""}
    for attempt in range(retries + 1):
        out = jobs_root / task_dir.name / f"try{attempt}"
        t0 = time.time()
        subprocess.run(["harbor", "run", "-p", str(task_dir), "-a", cfg.bench_agent, "-m", cfg.bench_model,
                        "-k", "1", "-o", str(out), "--no-delete", "-y"], capture_output=True, text=True)
        trials = _trial_dirs(out)
        if trials:
            info = {**_classify(trials[-1], cfg.bench_model), "dir": str(trials[-1])}
        telemetry.record_call(model=f"harbor:{cfg.bench_agent}:{cfg.bench_model}", role="agent-probe", cached=False,
                              usage=harbor_usage(trials), seconds=time.time() - t0, cache_key=str(out),
                              error=None if info["counted"] else info["outcome"])
        if info["counted"]:
            break
    return info


def harbor_usage(trials: list[Path]) -> dict:
    """Sum token/cost fields found anywhere in harbor result.json files (field names mirror harbor's result.json)."""
    tot = {"input": 0, "output": 0, "cache": 0, "cost": 0.0}
    names = {"n_input_tokens": "input", "n_output_tokens": "output", "n_cache_tokens": "cache", "cost_usd": "cost"}

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in names and isinstance(v, (int, float)):
                    tot[names[k]] += v
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for t in trials:
        try:
            walk(json.loads((t / "result.json").read_text()))
        except Exception:  # noqa: BLE001
            pass
    return tot


def _trial_dirs(out: Path) -> list[Path]:
    return sorted({p.parent for p in out.rglob("result.json") if (p.parent / "verifier").is_dir()})


def _classify(trial: Path, expected_model: str) -> dict:
    res = json.loads((trial / "result.json").read_text())
    rj = trial / "verifier" / "reward.json"
    reward = json.loads(rj.read_text()).get("reward") if rj.exists() else None
    exc = res.get("exception_info") or {}
    exc_type = str(exc.get("exception_type") or exc.get("type") or "")
    model_info = json.dumps(res.get("agent_info", {}).get("model_info", ""))
    detail = (exc_type + " " + str(exc.get("exception_message") or ""))[:300].strip()
    if "timeout" in exc_type.lower():
        outcome, counted = "timeout (counted miss)", True
        reward = reward if reward is not None else 0.0
    elif reward is None or (exc_type and reward is None):
        outcome, counted = "infra", False
    elif expected_model.split("/")[-1] not in model_info:
        outcome, counted, detail = "infra (model mismatch)", False, model_info[:200]
    else:
        outcome, counted = ("resolved" if reward == 1.0 else "miss"), True
    return {"reward": reward, "resolved": reward == 1.0, "counted": counted, "outcome": outcome, "detail": detail}


# ---------------------------------------------------------------- templates

TASK_TOML = """[metadata]
name = "{iid}"
instance_id = "{iid}"
task = "swe-feature-implementation"
source_repo = "{repo}"
base_commit = "{sha}"
license = "{license}"
language = "en"
programming_language = "{lang}"

[environment]
docker_image = ""
build_timeout_sec = 3600.0
cpus = 2
workdir = "/app"
memory_mb = 4096
network_mode = "{net}"

[agent]
timeout_sec = 1800.0

[verifier]
environment_mode = "shared"
timeout_sec = 900.0

[rollout_baseline.oracle]
reward = 1.0
[rollout_baseline.nop]
reward = 0.0
"""

SOLVE_SH = """#!/bin/bash
# Oracle: apply the reference patch.
set -e
git -C /app apply "$(dirname "$0")/patch.diff"
echo "reference applied to /app"
"""

RUN_SCRIPT = """#!/usr/bin/env bash
# Run the graded tests (curated regression files + the feature test file). Only files present in the tree
# are passed, so the base state (feature test absent) still runs the regression set. Not `set -e`.
set -uo pipefail
cd /app
PY=/app/.venv/bin/python
[ -x "$PY" ] || PY="$(command -v python)"
ALL=(
__FILES__
)
PRESENT=()
for f in "${ALL[@]}"; do [ -e "$f" ] && PRESENT+=("$f"); done
[ "${#PRESENT[@]}" -eq 0 ] && { echo "no graded test files present"; exit 0; }
"$PY" -m pytest "${PRESENT[@]}" -rA --tb=short -p no:cacheprovider --color=no --continue-on-collection-errors
"""

DOCKERFILE = """FROM {image}
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates bash && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# upstream repository pinned at base_commit (history dropped so the tree holds only the base state)
RUN set -eux; git init -q /tmp/src; cd /tmp/src; \\
    git remote add origin {url}; \\
    git fetch -q --depth 1 origin {sha}; \\
    git checkout -q FETCH_HEAD; \\
    rm -rf .git; cp -a /tmp/src/. /app/; rm -rf /tmp/src

# make /app a git working tree at the base state (solve.sh and the grader use git apply)
RUN git init --quiet \\
    && git config user.email bench@local && git config user.name bench \\
    && git config core.autocrlf false \\
    && git add -A && git commit --quiet -m "base state" \\
    && git config --global --add safe.directory /app

RUN python -m venv /app/.venv \\
    && /app/.venv/bin/pip install -e . "{pytest}" \\
    && /app/.venv/bin/python -c "import click; print('base import ok')"
CMD ["/bin/bash"]
"""
