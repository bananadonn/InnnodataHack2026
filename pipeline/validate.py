"""Stage 4: validate a package: lint, then oracle/nop selfcheck, then mutation check.

Stub only. The lint and selfcheck steps wrap the organizer harness in kit/harness/.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Outcome of validating one package."""

    instance_id: str
    lint_ok: bool = False
    oracle_reward: float | None = None  # must be 1.0
    nop_reward: float | None = None  # must be 0.0
    mutation_ok: bool | None = None
    errors: list[str] = []

    @property
    def ok(self) -> bool:
        return self.lint_ok and self.oracle_reward == 1.0 and self.nop_reward == 0.0 and self.mutation_ok is not False


def lint(task_dir: Path) -> list[str]:
    """Run kit/harness/check_structure.py on `task_dir`; return its ERROR lines.

    TODO: implement.
    """
    raise NotImplementedError("lint is a stub")


def selfcheck(task_dir: Path, out_dir: Path) -> tuple[float | None, float | None]:
    """Run the Harbor oracle and nop baselines; return (oracle_reward, nop_reward).

    A reward of None means an environment crash, not a score.

    TODO: call kit/harness/selfcheck.sh (or `harbor run -a oracle|nop`) and read grading_details.json.
    """
    raise NotImplementedError("selfcheck is a stub")


def mutation_check(task_dir: Path) -> bool:
    """Check the feature tests are discriminating: a weakened gold must not score 1.0.

    TODO: define mutations and how they are scored.
    """
    raise NotImplementedError("mutation_check is a stub")


def validate_package(task_dir: Path, out_dir: Path) -> ValidationResult:
    """Run lint → selfcheck → mutation check, stopping at the first failing stage.

    TODO: implement.
    """
    raise NotImplementedError("validate_package is a stub")
