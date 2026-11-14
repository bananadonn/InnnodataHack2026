"""Per-task resource accounting → pipeline_run.json (SUBMISSION.md §3b) + raw llm_calls.jsonl audit log.

Thread-safe: slots run in parallel threads; each thread has its own "current slot" and all shared state is
guarded by one lock.

Cost attribution rule (stated in the writeup): every model call made while working on a *slot* — including
failed attempts, timed-out requests and rejected candidates — is charged to the task that slot finally produced.
Slots that produced nothing are reported under summary.unattributed, so total spend is never hidden.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

_lock = threading.RLock()
_local = threading.local()
_state = {"run_dir": None, "slots": {}, "t0": None}


def init(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        _state.update(run_dir=run_dir, slots={}, t0=time.time())


def current_slot() -> str | None:
    return getattr(_local, "slot", None)


def start_slot(slot: str) -> None:
    _local.slot = slot
    with _lock:
        s = _state["slots"].setdefault(slot, {"model_calls": 0, "failed_calls": 0, "cached_calls": 0, "attempts": 0,
                                              "n_input_tokens": 0, "n_output_tokens": 0, "n_cache_tokens": 0,
                                              "cost_usd_reported": 0.0, "wall_seconds": 0.0, "models": {},
                                              "instance_id": None})
        s["_started"] = time.time()


def end_slot(instance_id: str | None) -> None:
    slot = current_slot()
    with _lock:
        s = _state["slots"][slot]
        s["wall_seconds"] += round(time.time() - s.pop("_started"), 1)
        s["instance_id"] = instance_id
    _local.slot = None


def new_attempt() -> None:
    slot = current_slot()
    if slot:
        with _lock:
            _state["slots"][slot]["attempts"] += 1


def record_call(model, role, cached, usage, seconds, cache_key, truncated=False, error=None) -> None:
    rd = _state["run_dir"]
    if rd is None:
        return
    slot = current_slot()
    entry = {"ts": round(time.time(), 2), "slot": slot, "role": role, "model": model, "cached": cached,
             "seconds": round(seconds, 2), "usage": usage, "truncated": truncated, "error": error,
             "cache_key": cache_key}
    with _lock:
        with open(rd / "llm_calls.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
        s = _state["slots"].get(slot)
        if not s:
            return
        if cached:
            s["cached_calls"] += 1
            return
        s["model_calls"] += 1
        if error:
            s["failed_calls"] += 1
        s["n_input_tokens"] += usage.get("input", 0) or 0
        s["n_output_tokens"] += usage.get("output", 0) or 0
        s["n_cache_tokens"] += usage.get("cache", 0) or 0
        s["cost_usd_reported"] += float(usage.get("cost") or 0)
        s["models"][model] = s["models"].get(model, 0) + 1


def write_pipeline_run(path: Path, pipeline_name: str, extra: dict | None = None) -> dict:
    with _lock:
        tasks, unattributed = [], []
        for slot, s in _state["slots"].items():
            main_model = max(s["models"], key=s["models"].get) if s["models"] else "cache-only"
            wall = s["wall_seconds"] + (round(time.time() - s["_started"], 1) if "_started" in s else 0)
            row = {"instance_id": s["instance_id"], "slot": slot, "model": main_model,
                   "wall_seconds": wall, "model_calls": s["model_calls"], "attempts": s["attempts"],
                   "n_input_tokens": s["n_input_tokens"], "n_output_tokens": s["n_output_tokens"],
                   "n_cache_tokens": s["n_cache_tokens"], "failed_calls": s["failed_calls"],
                   "cached_calls": s["cached_calls"], "models_used": dict(s["models"]),
                   "cost_usd_reported": round(s["cost_usd_reported"], 4)}
            (tasks if s["instance_id"] else unattributed).append(row)
        out = {"pipeline": pipeline_name, "tasks": tasks,
               "summary": {"total_wall_seconds": round(time.time() - (_state["t0"] or time.time()), 1),
                           "note": "slots run in parallel; per-task wall_seconds overlap, total_wall_seconds is the real elapsed time",
                           "unattributed": unattributed,
                           "audit_log": "llm_calls.jsonl (one line per model call, incl. failed calls, raw provider usage)",
                           **(extra or {})}}
        path.write_text(json.dumps(out, indent=1))
        return out
