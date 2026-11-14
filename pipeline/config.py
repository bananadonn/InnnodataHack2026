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
# Generation goes through OpenRouter with a cheap model.
# TODO(team): set the OpenRouter model id we agree on.
GENERATION_MODEL = "TODO-set-openrouter-model-id"
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


def openrouter_api_key() -> str:
    """Return the OpenRouter key from the environment (.env). Raises if unset."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return key
