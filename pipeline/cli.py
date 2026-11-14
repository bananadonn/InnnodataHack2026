"""Pipeline entrypoint.

Usage:
    python -m pipeline.cli explore https://github.com/pallets/click --ref 8.5.1
    python -m pipeline.cli propose <run_id> --n 5
    python -m pipeline.cli tests <run_id>
    python -m pipeline.cli code <run_id> --agent both --feature <slug>
    python -m pipeline.cli ask <run_id> "Where are option defaults resolved?"
    python -m pipeline.cli generate --n 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
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


def cmd_explore(url: str, ref: str | None) -> int:
    """Explore a GitHub repository and write a report under runs/<run_id>/."""
    from pipeline import explore

    try:
        run_dir = asyncio.run(explore.explore(url, ref))
    except explore.ExploreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return _print_run(run_dir)


def _print_run(run_dir: Path) -> int:
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    print(f"run_id:  {meta['run_id']}")
    print(f"status:  {meta['status']}" + (f" ({meta['error']})" if meta.get("error") else ""))
    print(f"commit:  {meta['commit_sha']}")
    for name, st in meta.get("stages", {}).items():
        print(f"  {name:<34} {st['status']:<8} {st.get('num_turns', 0):>3} turns  ${st.get('total_cost_usd', 0):.4f}")
    print(f"total:   ${meta.get('total_cost_usd', 0):.4f} (SDK estimate)")
    print(f"output:  {run_dir}")
    return 0 if meta["status"] == "ok" else 1


def cmd_propose(run_id: str, n: int) -> int:
    """Design n features for an explored repository; writes features.json and features.md."""
    from pipeline import explore, propose

    try:
        run_dir = asyncio.run(propose.propose(run_id, n))
    except explore.ExploreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return _print_run(run_dir)


def cmd_ask(run_id: str, question: str) -> int:
    """Ask a follow-up question in an existing exploration run's session."""
    from pipeline import explore

    try:
        print(asyncio.run(explore.ask(run_id, question)))
    except explore.ExploreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_tests(run_id: str) -> int:
    """Draft new feature tests and report existing regression test locations."""
    from pipeline import explore, test_agent

    try:
        output = asyncio.run(test_agent.create_tests(run_id))
    except explore.ExploreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"output: {output}")
    return 0


def cmd_code(run_id: str, agent: str, feature: str | None, execute: bool) -> int:
    from pipeline.coding import run_coding_agents
    from pipeline.explore import ExploreError

    try:
        asyncio.run(run_coding_agents(run_id, agent=agent, feature_slug=feature, execute=execute))
    except ExploreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description="Harbor task factory for pallets/click")
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("explore", help="explore a GitHub repository and write a report")
    exp.add_argument("url", help="https://github.com/<owner>/<repo>")
    exp.add_argument("--ref", default=None, help="branch, tag or full commit SHA (default: default branch)")
    pro = sub.add_parser("propose", help="design features for an explored repository")
    pro.add_argument("run_id")
    pro.add_argument("--n", type=int, default=5, help="number of features (default 5)")
    tests = sub.add_parser("tests", help="create feature-test drafts and find existing regression test folders")
    tests.add_argument("run_id")
    code = sub.add_parser("code", help="prepare coding-agent jobs; use --execute for paid model calls")
    code.add_argument("run_id")
    code.add_argument("--agent", choices=["haiku", "reference", "both"], default="both")
    code.add_argument("--feature", default=None, help="feature slug (default: all proposed features)")
    code.add_argument("--execute", action="store_true", help="call the providers and author candidate patches")
    ask = sub.add_parser("ask", help="ask a follow-up question about an explored repository")
    ask.add_argument("run_id")
    ask.add_argument("question")
    gen = sub.add_parser("generate", help="generate validated task packages")
    gen.add_argument("--n", type=int, default=5, help="number of tasks to generate (default 5)")
    gen.add_argument("--out", type=Path, default=config.GENERATED_TASKS_DIR, help="output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "explore":
        return cmd_explore(args.url, args.ref)
    if args.command == "propose":
        return cmd_propose(args.run_id, args.n)
    if args.command == "tests":
        return cmd_tests(args.run_id)
    if args.command == "code":
        return cmd_code(args.run_id, args.agent, args.feature, args.execute)
    if args.command == "ask":
        return cmd_ask(args.run_id, args.question)
    if args.command == "generate":
        try:
            return cmd_generate(args.n, args.out)
        except NotImplementedError as exc:
            print(f"not implemented yet: {exc}", file=sys.stderr)
            return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
