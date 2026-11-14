"""Stage 1: design N features for an explored repository.

Input: an exploration run (runs/<run_id>/report.json). One agent session receives the whole
report, can re-read the code, and outputs a FeaturePlan. The application then checks every
feature against the repository (files exist, named interfaces exist, gold and test files are
disjoint, categories distinct, enough edge cases / examples / criteria). Failures go back to
the same session for correction.

Output, under runs/<run_id>/: features.json and features.md.

The features are outlines, not implementations. The generate stage turns each into a spec,
a gold patch and hidden tests.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pipeline import config, verify
from pipeline.agent import BASE_RULES, EventLog, run_stage
from pipeline.explore import ExploreError, load_run, record_stage, write_json


class BuildsOn(BaseModel):
    module: str = Field(description="Repo-relative source file path")
    interfaces: list[str] = Field(description="Qualified names of EXISTING interfaces in that file the feature extends or calls")


class FeatureExample(BaseModel):
    code: str = Field(description="Short usage snippet of the new feature")
    expected: str = Field(description="Exact observable result: output, return value, or exception type and message")


class Feature(BaseModel):
    """One feature outline. The text fields are the skeleton of the task's instruction.md."""

    slug: str = Field(description="kebab-case, 2-5 words; becomes the task id suffix")
    category: str = Field(description="The variation axis this feature covers; must differ between features")
    title: str
    problem: str = Field(description="What is missing today and why a user of the library wants it")
    public_interface: list[str] = Field(description="Exact new or changed signatures, with defaults")
    behavior: list[str] = Field(description="Numbered-style rules stating exactly what happens, with concrete values")
    interaction_rules: list[str] = Field(description="How the rules combine or take precedence when several apply at once")
    edge_cases_and_errors: list[str] = Field(description="Unusual input and exactly what happens, including exception types and messages")
    backward_compatibility: list[str] = Field(description="What existing behavior must remain unchanged")
    examples: list[FeatureExample]
    acceptance_criteria: list[str] = Field(description="Observable, testable statements; each maps to at least one hidden test")
    builds_on: list[BuildsOn]
    extension_point: str = Field(description="Where in the existing code the feature attaches")
    source_files_to_modify: list[str] = Field(description="Existing repo source files the gold patch will edit")
    source_files_to_add: list[str] = Field(description="New source files the gold patch will create (often empty)")
    regression_test_files: list[str] = Field(description="Existing test files whose tests must keep passing")
    new_test_file: str = Field(description="Path of the NEW test file for the hidden feature tests")
    novelty_rationale: str = Field(description="Why this is not already in the repo or upstream, referring to the report")
    difficulty_rationale: str = Field(description="Why a capable solver could still get this wrong from the spec")
    estimated_gold_lines: int


class FeaturePlan(BaseModel):
    variation_strategy: str = Field(description="How the features differ along capability, behavioral shape, integration depth and interaction rules")
    features: list[Feature]


SYSTEM_PROMPT = (
    "You are a senior maintainer designing new features for an open-source library. The features become "
    "benchmark coding tasks: a solver model receives only a written spec and must implement the feature so "
    "that hidden tests pass. You design; you do not implement.\n\n" + BASE_RULES
)

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){1,5}$")


def _prompt(n: int, meta: dict[str, Any], report: dict[str, Any]) -> str:
    return f"""Design exactly {n} new features for {meta['owner']}/{meta['repo']} at commit {meta['commit_sha']}.

The exploration report below is your source of truth about the repository. Its interface signatures and
line numbers were extracted from the code by a parser. You may re-read code in ./repo to confirm details,
and you should before relying on any behavior the report does not state.

What makes a feature acceptable:
- It extends functionality that actually exists, attaching at a real extension point, and is realistically
  scoped: roughly 40-200 lines of gold implementation in one to three existing source files.
- It is novel: not present in the repo, not in the report's upstream lists, and not a drop-in copy of a
  feature from another well-known library.
- Its difficulty comes from several rules that INTERACT (precedence, eligibility, thresholds, ordering,
  combinations of options), not from volume of code. A shopping-cart analogy: "discount codes with
  eligibility rules and spending thresholds", not "add a field".
- Every rule is observable through the public interface, so tests can assert concrete values without
  depending on a particular algorithm, private helper or internal structure.
- The spec must be complete: anything a hidden test could check is stated in behavior, interaction_rules,
  edge_cases_and_errors, backward_compatibility or examples, with concrete values and exact exception types.
- It is backward compatible: existing tests keep passing with the feature added and unused.
- The {n} features are substantively different: different capabilities and different parts of the library,
  not rewordings. Each has its own category.
- The hidden tests go in a NEW test file. The gold implementation must not touch any test file.

Per feature give at least: 4 behavior rules, 2 interaction rules, 4 edge cases/errors, 2 backward-compatibility
statements, 3 examples with exact expected results, 5 acceptance criteria. `builds_on` must name existing
interfaces by their exact qualified names. Your answer is checked automatically against the repository.

EXPLORATION REPORT (JSON):
{json.dumps(report, separators=(',', ':'))}
"""


def make_validator(repo: Path, n: int):
    def validate(plan: FeaturePlan) -> list[str]:
        errs: list[str] = []
        if len(plan.features) != n:
            errs.append(f"expected exactly {n} features, got {len(plan.features)}")
        for attr in ("slug", "category", "new_test_file"):
            values = [getattr(f, attr).strip().lower() for f in plan.features]
            if len(set(values)) != len(values):
                errs.append(f"every feature needs a distinct {attr}; got {values}")
        for f in plan.features:
            tag = f"[{f.slug}]"
            if not _SLUG.match(f.slug):
                errs.append(f"{tag} slug must be kebab-case with 2-6 words")
            for rel in f.source_files_to_modify + f.regression_test_files:
                if verify.file_lines(repo, rel) is None:
                    errs.append(f"{tag} file does not exist in the repo: {rel}")
            for rel in f.source_files_to_add + [f.new_test_file]:
                if verify.file_lines(repo, rel) is not None:
                    errs.append(f"{tag} file is declared new but already exists: {rel}")
                elif not (repo / rel).resolve().is_relative_to(repo.resolve()):
                    errs.append(f"{tag} path escapes the repo: {rel}")
            if not f.source_files_to_modify and not f.source_files_to_add:
                errs.append(f"{tag} names no source files for the gold patch")
            gold = set(f.source_files_to_modify) | set(f.source_files_to_add)
            tests = set(f.regression_test_files) | {f.new_test_file}
            if gold & tests:
                errs.append(f"{tag} gold and test files overlap: {sorted(gold & tests)}")
            if not f.builds_on:
                errs.append(f"{tag} builds_on is empty")
            for b in f.builds_on:
                if verify.file_lines(repo, b.module) is None:
                    errs.append(f"{tag} builds_on module does not exist: {b.module}")
                elif verify.is_python(b.module):
                    index = verify.index_python(repo / b.module)
                    for name in b.interfaces:
                        if verify.resolve(index, name) is None:
                            errs.append(f"{tag} builds_on interface `{name}` does not exist in {b.module}")
                if not b.interfaces:
                    errs.append(f"{tag} builds_on for {b.module} lists no interfaces")
            for attr, minimum in (("behavior", 4), ("interaction_rules", 2), ("edge_cases_and_errors", 4),
                                  ("backward_compatibility", 2), ("examples", 3), ("acceptance_criteria", 5),
                                  ("public_interface", 1)):
                if len(getattr(f, attr)) < minimum:
                    errs.append(f"{tag} needs at least {minimum} {attr}, got {len(getattr(f, attr))}")
        return errs

    return validate


def render_markdown(meta: dict[str, Any], plan: FeaturePlan) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) or "- (none)"

    out = [f"# Feature plan: {meta['owner']}/{meta['repo']} @ `{meta['commit_sha'][:12]}`", "",
           f"Run `{meta['run_id']}` · designed by `{config.PROPOSE_MODEL}` · checked against the repository by the pipeline.", "",
           "## Variation strategy", plan.variation_strategy, ""]
    for i, f in enumerate(plan.features, 1):
        out += [
            f"## {i}. {f.title}", "",
            f"- Slug: `{f.slug}` · Category: **{f.category}** · Estimated gold size: ~{f.estimated_gold_lines} lines",
            f"- Attaches at: {f.extension_point}",
            f"- Gold edits: {', '.join(f'`{p}`' for p in f.source_files_to_modify + f.source_files_to_add)}",
            f"- New test file: `{f.new_test_file}` · Regression: {', '.join(f'`{p}`' for p in f.regression_test_files)}",
            f"- Builds on: {'; '.join(f'`{b.module}` ({', '.join(b.interfaces)})' for b in f.builds_on)}", "",
            "### Problem", f.problem, "",
            "### Public interface", bullets([f"`{s}`" for s in f.public_interface]), "",
            "### Behavior", bullets(f.behavior), "",
            "### Interaction rules", bullets(f.interaction_rules), "",
            "### Edge cases and errors", bullets(f.edge_cases_and_errors), "",
            "### Backward compatibility", bullets(f.backward_compatibility), "",
            "### Examples",
        ]
        for e in f.examples:
            out += ["```python", e.code, "```", f"Expected: {e.expected}", ""]
        out += ["### Acceptance criteria", bullets(f.acceptance_criteria), "",
                "### Why it is novel", f.novelty_rationale, "",
                "### Why it is hard", f.difficulty_rationale, ""]
    return "\n".join(out)


async def propose(run_id: str, n: int = 5) -> Path:
    """Design `n` features for exploration run `run_id`. Returns the run directory."""
    workspace, meta = load_run(run_id)
    report_path = workspace / "report.json"
    if not report_path.is_file():
        raise ExploreError(f"run {run_id} has no report.json (status: {meta.get('status')})")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    repo = workspace / "repo"
    log = EventLog(workspace / "events.jsonl")
    print(f"run {run_id}: designing {n} features (model {config.PROPOSE_MODEL})", file=sys.stderr)
    res = await run_stage("propose", workspace, _prompt(n, meta, report), SYSTEM_PROMPT, log,
                          model=config.PROPOSE_MODEL, max_budget_usd=config.PROPOSE_MAX_BUDGET_USD,
                          schema=FeaturePlan, validator=make_validator(repo, n))
    record_stage(meta, workspace, res)
    if res.status != "ok":
        raise ExploreError(f"feature design failed ({res.status}): {res.error}")
    write_json(workspace / "features.json", res.data.model_dump())
    (workspace / "features.md").write_text(render_markdown(meta, res.data), encoding="utf-8")
    return workspace
