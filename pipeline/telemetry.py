"""Per-task resource telemetry, written to results/pipeline_run.json.

Stub only. Schema follows kit/SUBMISSION.md section 3b.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class TaskTelemetry(BaseModel):
    """One row of pipeline_run.json."""

    instance_id: str
    model: str
    wall_seconds: float = 0.0
    model_calls: int = 0
    attempts: int = 0  # generate-and-check cycles needed to land the task
    n_input_tokens: int = 0
    n_output_tokens: int = 0
    n_cache_tokens: int = 0

    def record_call(self, input_tokens: int, output_tokens: int, cache_tokens: int = 0) -> None:
        """Add one model call's usage to this task's totals.

        TODO: implement.
        """
        raise NotImplementedError("record_call is a stub")


class PipelineRun(BaseModel):
    """Top-level object of pipeline_run.json."""

    pipeline: str  # "<team>/<version>"
    tasks: list[TaskTelemetry] = []


def write_run(run: PipelineRun, path: Path) -> None:
    """Write `run` to `path` as JSON.

    TODO: implement. Also keep raw provider usage logs so the numbers are auditable.
    """
    raise NotImplementedError("write_run is a stub")
