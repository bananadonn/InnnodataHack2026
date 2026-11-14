"""Claude Haiku coding candidate, powered by the Claude Agent SDK."""
from __future__ import annotations

from pathlib import Path

from pipeline import config
from pipeline.agent import EventLog, run_stage
from pipeline.coding_common import ImplementationDraft, prepare_job, save_draft, validate_draft, write_status
from pipeline.explore import ExploreError, write_json


async def implement_feature(run_id: str, feature_slug: str, *, execute: bool = False) -> Path:
    """Prepare a pinned workspace; with execute=True, ask Haiku for a candidate patch.

    This is authoring only. No regression or feature-test success is inferred.
    """
    job = prepare_job(run_id, feature_slug, "haiku", config.HAIKU_IMPLEMENTATION_MODEL)
    if not execute:
        return job.workspace
    result = await run_stage(
        "haiku-implementation", job.workspace, job.prompt, job.system_prompt,
        EventLog(job.workspace / "events.jsonl"), model=job.model,
        max_budget_usd=config.CODING_MAX_BUDGET_USD, schema=ImplementationDraft,
        validator=lambda draft: validate_draft(job, draft),
        tools=["Read", "Glob", "Grep"],
    )
    write_json(job.workspace / "usage.json", result.summary())
    if result.status != "ok":
        write_status(job, "error", error=result.error, agent_status=result.status)
        raise ExploreError(f"Haiku implementation failed: {result.status}; {result.error}")
    return save_draft(job, result.data)
