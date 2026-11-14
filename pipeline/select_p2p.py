"""Stage 3: pick pass-to-pass regression tests for the modules a gold patch touches.

Stub only.
"""
from __future__ import annotations


def touched_files(patch: str) -> list[str]:
    """Return the repo-relative paths a unified diff modifies.

    TODO: parse `+++ b/<path>` headers.
    """
    raise NotImplementedError("touched_files is a stub")


def select_p2p(gold_patch: str, max_tests: int = 40) -> list[str]:
    """Return pytest IDs of existing click tests that exercise the touched modules.

    Selected tests must pass at BASE_COMMIT and with the gold applied, and must be stable
    (no flaky or order-dependent tests).

    TODO: map touched source modules to test files, collect IDs, run them at base to confirm green.
    """
    raise NotImplementedError("select_p2p is a stub")
