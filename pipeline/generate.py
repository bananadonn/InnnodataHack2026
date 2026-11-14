"""Stage 2: an LLM writes the spec, the gold patch, and the feature tests for one idea.

Stub only.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from pipeline.spec import FeatureSpec
from pipeline.telemetry import TaskTelemetry


class TaskDraft(BaseModel):
    """Everything the model produces for one task, before packaging."""

    instance_id: str  # pallets__click-0001-<kebab-slug>
    instruction_md: str  # the spec; must state everything the tests check
    gold_patch: str  # unified diff, source files only
    test_patch: str  # unified diff, test files only (disjoint from gold_patch)
    fail_to_pass: list[str]  # pytest IDs of the new feature tests


def generate_draft(idea: FeatureSpec, index: int, telemetry: TaskTelemetry | None = None) -> TaskDraft:
    """Generate spec + gold patch + feature tests for `idea`.

    Rules the output must satisfy:
    - gold patch and test patch touch DISJOINT files
    - feature tests assert concrete values
    - the spec states every behavior the tests check, and never mentions tests or the gold

    TODO: prompt the generation model with the idea and relevant click sources.
    TODO: verify both patches apply cleanly to BASE_COMMIT.
    """
    raise NotImplementedError("generate_draft is a stub")


def write_package(draft: TaskDraft, pass_to_pass: list[str], out_dir: Path) -> Path:
    """Materialize a Harbor package at `out_dir/<instance_id>/` from templates/click_base.

    TODO: copy the template, fill task.toml (name == instance_id), write instruction.md,
          solution/patch.diff, tests/test_patch.diff, fail_to_pass.json, pass_to_pass.json.
    """
    raise NotImplementedError("write_package is a stub")
