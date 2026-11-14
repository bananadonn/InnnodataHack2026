"""Orchestrate coding stages without mixing agent implementations into the CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pipeline.coding_common import load_features
from pipeline.explore import ExploreError


async def run_coding_agents(
    run_id: str, *, agent: Literal["haiku", "reference", "both"] = "both",
    feature_slug: str | None = None, execute: bool = False,
) -> list[Path]:
    """Prepare jobs by default. execute=True makes paid provider calls.

    Each (feature, agent, attempt) has an independent pinned clone. Failures are
    retained and reported; a stronger reference model is not assumed to be correct.
    """
    from pipeline.haiku_agent import implement_feature
    from pipeline.reference_agent import create_reference

    features = load_features(run_id)
    if feature_slug:
        features = [f for f in features if f.slug == feature_slug]
        if not features:
            raise ExploreError(f"no proposed feature named {feature_slug}")
    if agent not in {"haiku", "reference", "both"}:
        raise ExploreError("agent must be haiku, reference or both")
    agents = []
    if agent in {"haiku", "both"}:
        agents.append(implement_feature)
    if agent in {"reference", "both"}:
        agents.append(create_reference)
    paths, errors = [], []
    for feature in features:
        for run_agent in agents:
            try:
                output = await run_agent(run_id, feature.slug, execute=execute)
                paths.append(output)
                result = json.loads((output / "result.json").read_text(encoding="utf-8"))
                print(f"{result['status']}: {output}")
                if result["status"] == "blocked":
                    errors.append(f"{feature.slug}/{run_agent.__name__}: compatibility or specification blocker")
            except ExploreError as exc:
                errors.append(f"{feature.slug}/{run_agent.__name__}: {exc}")
    if errors:
        raise ExploreError("coding jobs failed: " + "; ".join(errors))
    return paths
