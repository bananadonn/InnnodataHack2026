"""Stage 1b: propose candidate features, designed from real user demand.

Input: an exploration run with report.json and demand.json (pipeline/demand.py). One agent
session receives the report, the mined user requests, and (from round 2 on) the previous
round's audit feedback. It can re-read the code. It outputs candidate outlines, each tied to
the user requests it answers. The application checks every candidate against the repository
(files and interfaces exist, gold and test files disjoint, enough interacting rules and traps,
every demand_ref is a mined request). Failures go back to the same session for correction.

Re-running `propose` starts a new round: the previous round's candidates and audits are moved
to rounds/<k>/, candidates selected in that round are carried over unchanged, and the rest are
replaced by new proposals.

Output, under runs/<run_id>/: candidates.json.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pipeline import config, verify
from pipeline.agent import BASE_RULES, EventLog, run_stage
from pipeline.explore import ExploreError, load_run, record_stage, write_json

ECOSYSTEM = "cloup, click-option-group, click-extra, click-params, click-default-group, click-aliases, " \
            "click-help-colors, rich-click, typer, argparse, docopt"
ROUND_FILES = ("candidates.json", "audit.json", "selection.json", "candidates.md")


class BuildsOn(BaseModel):
    module: str = Field(description="Repo-relative source file path")
    interfaces: list[str] = Field(description="Qualified names of EXISTING interfaces in that file the feature extends or calls")


class Candidate(BaseModel):
    """One candidate feature outline."""

    slug: str = Field(description="kebab-case, 2-5 words; becomes the task id suffix")
    category: str = Field(description="The capability area / variation axis this feature covers")
    title: str
    demand_refs: list[str] = Field(default_factory=list, description="URLs of the mined user requests this feature answers")
    user_story: str = Field(default="", description="Who wants this, doing what, in the words of the requests it answers")
    problem: str = Field(description="What is missing today and why a user of the library wants it")
    public_interface: list[str] = Field(description="Exact new or changed signatures, with defaults")
    behavior: list[str] = Field(description="Rules stating exactly what happens, with concrete values")
    interaction_rules: list[str] = Field(description="How rules combine or take precedence when several apply at once")
    traps: list[str] = Field(description="Places where the obvious implementation is wrong, each naming the rules that collide and the correct outcome")
    integration_points: list[str] = Field(description="Existing code paths (qualified names) the feature must hook into consistently")
    builds_on: list[BuildsOn]
    source_files_to_modify: list[str] = Field(description="Existing repo source files the gold patch will edit; most important first")
    source_files_to_add: list[str] = Field(description="New source files the gold patch will create (often empty)")
    regression_test_files: list[str] = Field(description="Existing test files whose tests must keep passing")
    new_test_file: str = Field(description="Path of the NEW test file for the hidden feature tests")
    novelty_rationale: str = Field(description="Why this is not in the repo, upstream, or a known add-on library")
    estimated_gold_lines: int


class CandidatePlan(BaseModel):
    variation_strategy: str = Field(description="How the candidates differ along capability, behavioral shape, integration depth and interaction rules")
    candidates: list[Candidate]


# ----------------------------------------------------------------------------------------
# Hand-off format: features.json. Written by pipeline/spec.py for the selected, fully specified
# features; read by pipeline/test_agent.py. Keep these fields stable.
# ----------------------------------------------------------------------------------------


class FeatureExample(BaseModel):
    code: str = Field(description="Short usage snippet of the new feature")
    expected: str = Field(description="Exact observable result: output, return value, or exception type and message")


class Feature(BaseModel):
    """One selected feature as handed to the test agent. The text fields are the spec's sections."""

    slug: str
    category: str
    title: str
    problem: str
    public_interface: list[str]
    behavior: list[str]
    interaction_rules: list[str]
    edge_cases_and_errors: list[str]
    backward_compatibility: list[str]
    examples: list[FeatureExample]
    acceptance_criteria: list[str]
    builds_on: list[BuildsOn]
    extension_point: str
    source_files_to_modify: list[str]
    source_files_to_add: list[str]
    regression_test_files: list[str]
    new_test_file: str
    novelty_rationale: str
    difficulty_rationale: str
    estimated_gold_lines: int


class FeaturePlan(BaseModel):
    variation_strategy: str
    features: list[Feature]


SYSTEM_PROMPT = (
    "You are a senior maintainer of an open-source library deciding which new features to build for its "
    "users. Each feature will be implemented for real and also used as a benchmark coding task: a solver "
    "model receives only a written spec and must implement it so that hidden tests pass. You design; you do "
    "not implement.\n\n" + BASE_RULES
)

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){1,5}$")


def _feedback(rounds_dir: Path) -> list[dict[str, Any]]:
    """Compact audit feedback from every earlier round: what was rejected and why."""
    out: list[dict[str, Any]] = []
    for d in sorted(rounds_dir.glob("*")) if rounds_dir.is_dir() else []:
        try:
            audit = json.loads((d / "audit.json").read_text(encoding="utf-8"))
            sel = json.loads((d / "selection.json").read_text(encoding="utf-8"))
            plan = json.loads((d / "candidates.json").read_text(encoding="utf-8"))
        except OSError:
            continue
        for c in plan["candidates"]:
            s = c["slug"]
            v, df, nv = audit.get("value", {}).get(s, {}), audit.get("difficulty", {}).get(s, {}), audit.get("novelty", {}).get(s, {})
            out.append({"round": d.name, "slug": s, "title": c["title"], "outcome": sel["reasons"].get(s, ""),
                        "novelty": nv.get("verdict"), "value": v.get("score"), "fits_library": v.get("fits_library"),
                        "value_reasoning": v.get("reasoning", "")[:400], "contrived_rules": v.get("contrived_rules", []),
                        "difficulty": df.get("score"), "difficulty_reasoning": df.get("reasoning", "")[:300]})
    return out


def _prompt(n: int, meta: dict[str, Any], report: dict[str, Any], demand: list[dict[str, Any]],
            feedback: list[dict[str, Any]], kept: list[Candidate]) -> str:
    usable = [d for d in demand if d.get("still_missing")]
    fb = ""
    if feedback:
        fb = f"""
EARLIER ROUNDS. These candidates were already proposed and audited. Do not propose them again or minor variants of
them. Learn from the reasons: most were rejected because their rules were contrived (precedence and special cases
invented to make the task hard, which no user asked for) or because nobody needs them.
{json.dumps(feedback, separators=(',', ':'))}
"""
    keep = ""
    if kept:
        keep = f"""
ALREADY SELECTED, carried over unchanged (do not duplicate their capability or category):
{json.dumps([{"slug": c.slug, "category": c.category, "title": c.title} for c in kept], separators=(',', ':'))}
"""
    return f"""Propose exactly {n} candidate features for {meta['owner']}/{meta['repo']} at commit {meta['commit_sha']}.
Only the best few will be built, after independent novelty, value and difficulty audits.

START FROM DEMAND. Below is a list of real user requests and workarounds, mined from the project's issues,
discussions, Stack Overflow and add-on libraries, each confirmed as still missing at this commit. Every candidate
must answer one or more of these requests: list their URLs in `demand_refs` and describe the user need in
`user_story`. Prefer requests with visible demand and with no maintainer objection. Avoid requests maintainers
declined as out of scope, and avoid needs an add-on already meets fully (that would be a drop-in).

VALUE FIRST, THEN DIFFICULTY.
- Every rule must be something the requesting users would want, or something required for consistency with how
  click already behaves (follow the existing conventions you see in the code). If you cannot say which user need or
  which existing behavior a rule comes from, leave it out.
- Difficulty must come from the real requirement: the interactions a real implementation has to get right, such as
  value sources and their precedence (command line, environment, default_map, defaults, prompts), parameters that
  must stay consistent across parsing, help output, shell completion and error messages, state across chained or
  nested commands, or boundaries of existing behavior. Do NOT invent precedence rules, thresholds or special cases
  to create traps.
- TRAPS: name at least 3 places where the obvious implementation is wrong, each arising from that real
  interaction with existing click behavior, with the correct outcome. If you cannot find three genuine ones,
  choose a different request.

Also required:
- GROUNDED: extends functionality that exists, hooks into at least two existing code paths (integration_points), and
  is realistically scoped: roughly 60-200 lines of gold implementation in one to three existing source files.
- NOVEL: not in the repo, not in the report's upstream lists, not a drop-in from: {ECOSYSTEM}.
- OBSERVABLE: every rule is visible through the public interface, so tests can assert exact values.
- BACKWARD COMPATIBLE: existing tests keep passing with the feature added and unused.
- The hidden tests go in a NEW test file. The gold implementation must not touch any test file.

Spread: at least {min(6, n)} different categories and at least {min(5, n)} different primary source files across the {n}.
Per candidate give at least 4 behavior rules, 3 interaction rules, 3 traps, 2 integration points.
`builds_on` must name existing interfaces by their exact qualified names. Your answer is checked automatically
against the repository and against the demand list.
{fb}{keep}
USER DEMAND (JSON):
{json.dumps(usable, separators=(',', ':'))}

EXPLORATION REPORT (JSON):
{json.dumps(report, separators=(',', ':'))}
"""


def make_validator(repo: Path, n: int, demand_urls: set[str], taken: set[str]):
    def validate(plan: CandidatePlan) -> list[str]:
        errs: list[str] = []
        if len(plan.candidates) != n:
            errs.append(f"expected exactly {n} candidates, got {len(plan.candidates)}")
        for attr in ("slug", "new_test_file"):
            values = [getattr(c, attr).strip().lower() for c in plan.candidates]
            if len(set(values)) != len(values):
                errs.append(f"every candidate needs a distinct {attr}")
        if len({c.category.strip().lower() for c in plan.candidates}) < min(6, n):
            errs.append(f"candidates must span at least {min(6, n)} different categories")
        if len({c.source_files_to_modify[0] for c in plan.candidates if c.source_files_to_modify}) < min(5, n):
            errs.append(f"candidates must span at least {min(5, n)} different primary source files")
        for c in plan.candidates:
            tag = f"[{c.slug}]"
            if c.slug in taken:
                errs.append(f"{tag} slug was already used in an earlier round; propose something different")
            if not _SLUG.match(c.slug):
                errs.append(f"{tag} slug must be kebab-case with 2-6 words")
            if demand_urls:
                if not c.demand_refs:
                    errs.append(f"{tag} demand_refs is empty; every candidate must answer at least one mined user request")
                bad = [u for u in c.demand_refs if u.strip() not in demand_urls]
                if bad:
                    errs.append(f"{tag} demand_refs not in the demand list (copy URLs exactly): {bad[:3]}")
                if not c.user_story.strip():
                    errs.append(f"{tag} user_story is empty")
            for rel in c.source_files_to_modify + c.regression_test_files:
                if verify.file_lines(repo, rel) is None:
                    errs.append(f"{tag} file does not exist in the repo: {rel}")
            for rel in c.source_files_to_add + [c.new_test_file]:
                if verify.file_lines(repo, rel) is not None:
                    errs.append(f"{tag} file is declared new but already exists: {rel}")
                elif not (repo / rel).resolve().is_relative_to(repo.resolve()):
                    errs.append(f"{tag} path escapes the repo: {rel}")
            if not c.source_files_to_modify:
                errs.append(f"{tag} must modify at least one existing source file (no orphan features)")
            gold = set(c.source_files_to_modify) | set(c.source_files_to_add)
            tests = set(c.regression_test_files) | {c.new_test_file}
            if gold & tests:
                errs.append(f"{tag} gold and test files overlap: {sorted(gold & tests)}")
            if not c.regression_test_files:
                errs.append(f"{tag} names no existing regression test files")
            if not c.builds_on:
                errs.append(f"{tag} builds_on is empty")
            for b in c.builds_on:
                if verify.file_lines(repo, b.module) is None:
                    errs.append(f"{tag} builds_on module does not exist: {b.module}")
                elif verify.is_python(b.module):
                    index = verify.index_python(repo / b.module)
                    for name in b.interfaces:
                        if verify.resolve(index, name) is None:
                            errs.append(f"{tag} builds_on interface `{name}` does not exist in {b.module}")
                if not b.interfaces:
                    errs.append(f"{tag} builds_on for {b.module} lists no interfaces")
            for attr, minimum in (("public_interface", 1), ("behavior", 4), ("interaction_rules", 3), ("traps", 3),
                                  ("integration_points", 2)):
                if len(getattr(c, attr)) < minimum:
                    errs.append(f"{tag} needs at least {minimum} {attr}, got {len(getattr(c, attr))}")
            if c.estimated_gold_lines < 50:
                errs.append(f"{tag} estimated gold of {c.estimated_gold_lines} lines is below the 50-line floor; too small to be hard")
        return errs

    return validate


def _start_round(workspace: Path) -> tuple[list[Candidate], set[str]]:
    """Archive the current round (if any). Returns (candidates carried over, every slug used so far)."""
    rounds = workspace / "rounds"
    taken: set[str] = set()
    for d in rounds.glob("*") if rounds.is_dir() else []:
        try:
            taken |= {c["slug"] for c in json.loads((d / "candidates.json").read_text(encoding="utf-8"))["candidates"]}
        except OSError:
            pass
    if not (workspace / "candidates.json").is_file():
        return [], taken
    plan = CandidatePlan.model_validate_json((workspace / "candidates.json").read_text(encoding="utf-8"))
    taken |= {c.slug for c in plan.candidates}
    selected: list[str] = []
    if (workspace / "selection.json").is_file():
        selected = json.loads((workspace / "selection.json").read_text(encoding="utf-8"))["selected"]
    k = 1
    while (rounds / f"round{k}").exists():
        k += 1
    dest = rounds / f"round{k}"
    dest.mkdir(parents=True)
    for name in ROUND_FILES:
        if (workspace / name).is_file():
            shutil.move(str(workspace / name), str(dest / name))
    print(f"  archived the previous round to {dest}; carrying over {selected or 'nothing'}", file=sys.stderr)
    return [c for c in plan.candidates if c.slug in selected], taken


async def propose(run_id: str, n: int = config.N_CANDIDATES) -> Path:
    """Propose candidates for run `run_id` (n in total, including carried-over ones). Returns the run directory."""
    workspace, meta = load_run(run_id)
    report_path = workspace / "report.json"
    if not report_path.is_file():
        raise ExploreError(f"run {run_id} has no report.json (status: {meta.get('status')})")
    if not (workspace / "demand.json").is_file():
        from pipeline import demand as demand_stage

        await demand_stage.mine(run_id)
        workspace, meta = load_run(run_id)
    demand = json.loads((workspace / "demand.json").read_text(encoding="utf-8"))["requests"]
    if not any(d.get("still_missing") for d in demand):
        raise ExploreError("demand.json has no usable requests; re-run `demand`")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    kept, taken = _start_round(workspace)
    new_n = n - len(kept)
    feedback = _feedback(workspace / "rounds")
    demand_urls = {d["url"].strip() for d in demand if d.get("still_missing")}
    log = EventLog(workspace / "events.jsonl")
    print(f"run {run_id}: proposing {new_n} new candidates (model {config.PROPOSE_MODEL}), "
          f"{len(kept)} carried over", file=sys.stderr)
    res = await run_stage("propose", workspace, _prompt(new_n, meta, report, demand, feedback, kept), SYSTEM_PROMPT, log,
                          model=config.PROPOSE_MODEL, max_budget_usd=config.PROPOSE_MAX_BUDGET_USD,
                          schema=CandidatePlan,
                          validator=make_validator(workspace / "repo", new_n, demand_urls, taken - {c.slug for c in kept}))
    record_stage(meta, workspace, res)
    if res.status != "ok":
        raise ExploreError(f"candidate proposal failed ({res.status}): {res.error}")
    plan: CandidatePlan = res.data
    plan.candidates = kept + plan.candidates
    write_json(workspace / "candidates.json", plan.model_dump())
    return workspace
