"""Single place for run configuration (all overridable by env / CLI)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

KIT_DIR_NAME = "vendor/innodata_kit"


@dataclass
class Config:
    source_repo: str = "pallets/click"
    repo_url: str = "https://github.com/pallets/click.git"
    license: str = "BSD-3-Clause"
    language: str = "python"
    base_commit: str = ""                       # 40-char sha, required
    src_dir: str = "src"                        # click uses a src/ layout
    python_image: str = "python:3.12-slim-bookworm"
    network_mode: str = os.environ.get("CTF_NETWORK_MODE", "public")  # benchmark agent needs egress
    # models (provider:model)
    gen_model: str = os.environ.get("CTF_GEN_MODEL", "anthropic:claude-sonnet-5-5")
    test_model: str = os.environ.get("CTF_TEST_MODEL", "anthropic:claude-sonnet-5-5")
    # blind solvers: one same-vendor + one cross-vendor (OpenRouter) by default, so gold/tests are checked by a
    # model family that did not write them. Override with a comma list in CTF_SOLVER_MODELS.
    solver_models: list = field(default_factory=lambda: [m for m in os.environ.get(
        "CTF_SOLVER_MODELS",
        "anthropic:claude-sonnet-5-5" + (("," + os.environ.get("CTF_CROSS_SOLVER", "openrouter:openai/gpt-5"))
                                         if os.environ.get("OPENROUTER_API_KEY") else "")).split(",") if m])
    probe_model: str = os.environ.get("CTF_PROBE_MODEL", "anthropic:claude-haiku-5-5")
    bench_model: str = os.environ.get("CTF_BENCH_MODEL", "anthropic/claude-haiku-5-5")  # harbor -m syntax
    bench_agent: str = "terminus-2"
    bench_k: int = 3
    # factory knobs
    n_tasks: int = 5
    candidates_per_slot: int = 3
    max_attempts_per_slot: int = 3
    gold_repairs: int = int(os.environ.get("CTF_GOLD_REPAIRS", "2"))  # self-check/repair rounds for the gold
    pipeline_name: str = "team/coding-task-factory-v1"
    evidence_dir: str = "runs/validation_evidence"
