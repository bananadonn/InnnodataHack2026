"""Variation strategy: the factory decides WHAT to generate before any LLM writes a spec.

Each task is assigned a *slot* = (capability area × behavioral shape × integration depth). The five slots of a
batch use five different capability areas and five different behavioral shapes, so two tasks can never be
rewordings of each other by construction. The LLM only fills a slot; it never chooses the axis.
Capability areas are bound to real modules of the repo (grounding gate) and dropped if the module is missing.
"""
from __future__ import annotations

import random
from pathlib import Path

# click-specific capability map (edit this table to retarget the factory to another repo)
CAPABILITIES = [
    {"id": "parsing", "name": "option/argument parsing semantics (how argv tokens become parameter values)",
     "modules": ["src/click/parser.py", "src/click/core.py"]},
    {"id": "types", "name": "parameter types: value conversion, validation and type-specific behavior",
     "modules": ["src/click/types.py"]},
    {"id": "help", "name": "help and usage text generation and formatting",
     "modules": ["src/click/formatting.py", "src/click/core.py"]},
    {"id": "completion", "name": "shell completion: candidate generation and completion protocol",
     "modules": ["src/click/shell_completion.py"]},
    {"id": "testing", "name": "the CliRunner testing utilities and Result object",
     "modules": ["src/click/testing.py"]},
    {"id": "context", "name": "Context: default resolution, default_map, envvar lookup and parameter source tracking",
     "modules": ["src/click/core.py"]},
    {"id": "termui", "name": "terminal UI helpers: prompt/confirm/style/echo behavior",
     "modules": ["src/click/termui.py"]},
    {"id": "composition", "name": "command composition: groups, chaining, command lookup and resolution",
     "modules": ["src/click/core.py", "src/click/decorators.py"]},
]

SHAPES = [
    ("validation", "a new validation rule set: precisely specified constraints, which error is raised "
                   "(exception type / exit code) and which rule wins when several are violated"),
    ("transformation", "a new derived output or representation with exact formatting rules and edge cases"),
    ("stateful", "behavior that depends on order, repetition or accumulation across multiple inputs/invocations"),
    ("interaction", "new behavior that must compose correctly with at least two existing features"),
    ("configuration", "a new opt-in parameter whose default keeps old behavior byte-for-byte, with a defined "
                      "precedence against existing configuration sources"),
]

INTEGRATION = ["library-level API (call the new API directly)",
               "end-to-end through a CLI invocation via CliRunner",
               "both: new public API plus observable CLI-level behavior"]


def plan_slots(repo: Path, n: int, seed: int = 0) -> list[dict]:
    caps = [c for c in CAPABILITIES if all((repo / m).exists() for m in c["modules"])]
    if len(caps) < n:
        raise SystemExit(f"only {len(caps)} capability areas map to existing modules; need {n}")
    rng = random.Random(seed)
    caps = rng.sample(caps, n)
    shapes = rng.sample(SHAPES, min(n, len(SHAPES)))
    slots = []
    for i, cap in enumerate(caps):
        sid, sdesc = shapes[i % len(shapes)]
        slots.append({"slot_id": f"s{i + 1}-{cap['id']}-{sid}", "capability": cap["name"], "capability_id": cap["id"],
                      "modules": cap["modules"], "shape": sdesc, "shape_id": sid,
                      "integration": INTEGRATION[i % len(INTEGRATION)]})
    return slots


def token_set(spec: dict) -> set[str]:
    import re
    text = spec.get("title", "") + " " + " ".join(r.get("text", "") for r in spec.get("requirements", []))
    return {w for w in re.findall(r"[a-z_]{4,}", text.lower())}


def near_duplicate(spec: dict, accepted: list[dict], threshold: float = 0.45) -> str | None:
    """Lexical guard on top of slot assignment (the judges also run a lexical near-duplicate check)."""
    a = token_set(spec)
    for other in accepted:
        b = token_set(other)
        if a and b and len(a & b) / len(a | b) >= threshold:
            return other.get("instance_id") or other.get("title")
    return None
