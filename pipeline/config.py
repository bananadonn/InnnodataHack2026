"""Shared constants for the pipeline. Change values here, not in the modules."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Target repo (click 8.5.1) -------------------------------------------------------
SOURCE_REPO = "pallets/click"
REPO_URL = "https://github.com/pallets/click.git"
BASE_COMMIT = "cf19179e8e2fd54c601378cec9e0d21bb12b6fb1"
BASE_TAG = "8.5.1"
LICENSE = "BSD-3-Clause"
PROGRAMMING_LANGUAGE = "python"
PYTHON_IMAGE = "python:3.12-slim"

# --- Task IDs: pallets__click-0001-<kebab-slug> --------------------------------------
INSTANCE_ID_PREFIX = "pallets__click"

# --- Models --------------------------------------------------------------------------
# Task creation runs through the Claude Agent SDK, which reads
# ANTHROPIC_API_KEY from the environment: exploring the repo, designing features, and writing
# the spec and hidden tests. Coding agents have separate models below.
EXPLORE_MODEL = "claude-sonnet-5-5"
PROPOSE_MODEL = "opus"
GENERATION_MODEL = "claude-sonnet-5-5"
TEST_MODEL = "opus"
HAIKU_IMPLEMENTATION_MODEL = "haiku"
# Explicit route; override in .env to select another advanced OpenRouter model.
OPENROUTER_REFERENCE_MODEL = os.environ.get("OPENROUTER_REFERENCE_MODEL", "anthropic/claude-opus-4.6")

# Caps for every agent session. Budgets are the SDK's client-side estimate and can overshoot slightly.
AGENT_MAX_TURNS = 60
AGENT_WALL_TIMEOUT_SEC = 900
AGENT_CONCURRENCY = 4          # agent sessions running at once
MAP_MAX_BUDGET_USD = 2.00      # repo map (one session)
CARD_MAX_BUDGET_USD = 1.50     # deep dive, per module
UPSTREAM_MAX_BUDGET_USD = 1.50 # upstream novelty check (web)
PROPOSE_MAX_BUDGET_USD = 4.00  # feature design
TEST_DISCOVERY_MAX_BUDGET_USD = 1.00
TEST_MAX_BUDGET_USD = 2.00    # per feature, test authoring only
CODING_MAX_BUDGET_USD = 3.00  # per Haiku feature attempt, SDK estimate
REFERENCE_MAX_CALLS = 12
REFERENCE_MAX_OUTPUT_TOKENS = 16000
# Cumulative reported cost; a request can overshoot before its usage is returned.
REFERENCE_MAX_BUDGET_USD = 5.00
DEEP_DIVE_MAX_MODULES = 8
CLONE_TIMEOUT_SEC = 300
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Benchmark ONLY with this model/agent/k. The Anthropic key is reserved for benchmarking.
BENCH_MODEL = "anthropic/claude-haiku-5-5"
BENCH_AGENT = "terminus-2"
BENCH_K = 3

# --- Paths ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = ROOT / "kit"
HARNESS_DIR = KIT_DIR / "harness"
TEMPLATE_DIR = ROOT / "templates" / "click_base"
GENERATED_TASKS_DIR = ROOT / "generated_tasks"
RESULTS_DIR = ROOT / "results"
SELFCHECK_RESULTS_DIR = RESULTS_DIR / "selfcheck"
BENCH_RESULTS_DIR = RESULTS_DIR / "bench"
PIPELINE_RUN_JSON = RESULTS_DIR / "pipeline_run.json"
CLICK_CLONE_DIR = ROOT / "click"  # optional local clone, gitignored
RUNS_DIR = ROOT / "runs"  # one workspace per exploration run; runs/*/repo is gitignored


def openrouter_api_key() -> str:
    """Return the OpenRouter key from the environment (.env). Raises if unset."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return key
