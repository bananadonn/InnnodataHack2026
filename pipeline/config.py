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
# Everything that CREATES a task runs through the Claude Agent SDK, which reads ANTHROPIC_API_KEY
# from the environment. Sonnet explores and audits novelty and value; Opus proposes, audits
# difficulty, writes the specs and the golden solution. Haiku is only the solver (quiz, benchmark).
EXPLORE_MODEL = "claude-sonnet-5-5"
PROPOSE_MODEL = "claude-opus-5-5"      # proposes candidate features
NOVELTY_MODEL = "claude-sonnet-5-5"    # validation: novelty audit (web)
VALUE_MODEL = "claude-sonnet-5-5"      # validation: value audit (web): real demand, fit, contrived rules
DEMAND_MODEL = "claude-sonnet-5-5"     # mines real user requests (web) that candidates are designed from
DEMAND_PER_SESSION = 12                # minimum still-missing requests per demand session (2 sessions)
DEMAND_MAX_BUDGET_USD = 2.50           # per demand session
DIFFICULTY_MODEL = "claude-opus-5-5"   # validation: difficulty audit
SPEC_MODEL = "claude-opus-5-5"         # tightens selected features into full specs + case tables
FAIRNESS_QUIZ_MODEL = "claude-sonnet-5-5"  # blind reader; must differ from SPEC_MODEL
QUIZ_MODEL = "claude-haiku-5-5"        # blind reader; the benchmark model
GENERATION_MODEL = "claude-opus-5-5"   # writes the golden solution (gold patch) and hidden tests

N_CANDIDATES = 15
N_FEATURES = 5
AUDIT_BATCH_SIZE = 5           # candidates per audit session
MIN_DIFFICULTY = 3             # candidates scoring below this are not selected
MIN_VALUE = 2                  # candidates scoring below this are not selected
# Team decision (2026-11-14): a good feature that nobody has requested yet is acceptable, so "does not fit the
# library" from the value audit is reported but not a hard reject. Drop-ins and existing features are still
# rejected by the novelty audit.
REQUIRE_FITS_LIBRARY = False
MIN_CASES = 15                 # case-table size per feature
NOVELTY_MAX_BUDGET_USD = 2.00      # per batch
DIFFICULTY_MAX_BUDGET_USD = 4.00   # per batch
VALUE_MAX_BUDGET_USD = 2.00        # per batch
SPEC_MAX_BUDGET_USD = 4.00         # per feature, including fix rounds
QUIZ_MAX_BUDGET_USD = 0.75         # per quiz
TEST_MODEL = "claude-opus-5-5"         # test agent: drafts feature tests (pipeline/test_agent.py)

# Independent coding agents; reference authoring uses the OpenRouter allocation.
HAIKU_IMPLEMENTATION_MODEL = "haiku"
OPENROUTER_REFERENCE_MODEL = os.environ.get("OPENROUTER_REFERENCE_MODEL", "anthropic/claude-opus-4.6")

# Caps for every agent session. Budgets are the SDK's client-side estimate and can overshoot slightly.
AGENT_MAX_TURNS = 60
AGENT_WALL_TIMEOUT_SEC = 900
AGENT_CONCURRENCY = 4          # agent sessions running at once
MAP_MAX_BUDGET_USD = 2.00      # repo map (one session)
CARD_MAX_BUDGET_USD = 1.50     # deep dive, per module
UPSTREAM_MAX_BUDGET_USD = 1.50 # upstream novelty check (web)
PROPOSE_MAX_BUDGET_USD = 6.00  # candidate proposal
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
