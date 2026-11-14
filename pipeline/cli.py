"""Pipeline entrypoint.

Usage:
    python -m pipeline.cli generate --n 5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import config


def cmd_generate(n: int, out_dir: Path) -> int:
    """Generate `n` validated task packages into `out_dir`.

    Flow: propose → generate → select_p2p → write_package → validate, retrying a task until
    it validates; telemetry for every task goes to results/pipeline_run.json.

    TODO: wire the stages together once they are implemented.
    """
    raise NotImplementedError("the generate command is a stub")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description="Harbor task factory for pallets/click")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate validated task packages")
    gen.add_argument("--n", type=int, default=5, help="number of tasks to generate (default 5)")
    gen.add_argument("--out", type=Path, default=config.GENERATED_TASKS_DIR, help="output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        try:
            return cmd_generate(args.n, args.out)
        except NotImplementedError as exc:
            print(f"not implemented yet: {exc}", file=sys.stderr)
            return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
