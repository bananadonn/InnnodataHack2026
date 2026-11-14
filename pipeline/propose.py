"""Stage 1: an LLM proposes feature ideas, one per variation category.

Stub only. See docs/VARIATION.md for the categories.
"""
from __future__ import annotations

from pydantic import BaseModel

from pipeline.telemetry import TaskTelemetry


class FeatureIdea(BaseModel):
    """One proposed feature for click."""

    slug: str  # kebab-case, becomes the instance_id suffix
    category: str  # variation category this idea covers
    title: str
    summary: str
    target_modules: list[str]  # e.g. ["src/click/core.py"]


def propose_ideas(categories: list[str], n: int, telemetry: TaskTelemetry | None = None) -> list[FeatureIdea]:
    """Ask the generation model for `n` feature ideas spread across `categories`.

    Ideas must be novel relative to click at BASE_COMMIT (not already implemented upstream)
    and substantively different from each other.

    TODO: build the prompt (repo map + categories), call OpenRouter, parse into FeatureIdea.
    TODO: reject ideas that duplicate existing click features or each other.
    """
    raise NotImplementedError("propose_ideas is a stub")
