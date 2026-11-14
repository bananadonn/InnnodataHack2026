"""Stage 3: turn each selected candidate into a tight spec with a case table, then quiz it.

For every selected candidate (runs/<run_id>/selection.json) one agent session writes:

- the full spec: problem, public interface, behavior rules (R1..), interaction rules (I1..),
  edge cases and errors (E1..), backward compatibility (B1..), acceptance criteria (A1..);
- a case table: self-contained Python snippets with exact expected results, each naming the
  rules it exercises. A few are public (they become the spec's examples); the rest are held out.

The application checks the spec mechanically (snippets parse, every raises-case has an exact
message, no vague phrases, every interaction rule and acceptance criterion is covered).

Then a blind quiz: a model sees ONLY the spec text (no tools, no repository) and predicts the
result of every held-out case.
- Fairness reader (a different model from the author): any miss means the spec does not
  determine the answer; the case goes back to the author to fix the spec or the case.
- Benchmark model: its misses are a cheap difficulty signal. A feature it answers perfectly
  is flagged as likely too easy and replaced by the next reserve candidate.

The quiz is a proxy. Predicting outcomes is easier than implementing, and expected values are
not confirmed by running code until the gold solution exists.

Output, under runs/<run_id>/: specs/<slug>/{instruction.md,cases.json,quiz.json,spec.json},
features.json, features.md.
"""
from __future__ import annotations

import ast
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from pipeline import config
from pipeline.agent import BASE_RULES, EventLog, run_stage
from pipeline.audit import DifficultyVerdict, NoveltyVerdict, ValueVerdict, load_audit
from pipeline.explore import ExploreError, load_run, record_stage, write_json
from pipeline.propose import Candidate, Feature, FeatureExample, FeaturePlan

# ----------------------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------------------


class Case(BaseModel):
    id: str = Field(description="Short unique id, e.g. c01")
    description: str
    code: str = Field(
        description="Self-contained Python: all imports included, no placeholders. For expect=returns the LAST "
        "statement is an expression whose value is the result. For expect=raises, running the code raises."
    )
    expect: Literal["returns", "raises"]
    value: str = Field(description="For returns: the exact repr() of the final expression. Empty for raises.")
    exception_type: str = Field(description="For raises: the exception class name, e.g. click.BadParameter. Empty for returns.")
    message: str = Field(description="For raises: the exact str() of the exception (for click exceptions, exc.message). Empty for returns.")
    rules_exercised: list[str] = Field(description="Rule ids this case checks, e.g. ['R2', 'I1', 'A3']")
    public: bool = Field(description="True for the few cases shown in the spec as examples")


class FeatureSpec(BaseModel):
    """A complete feature specification. List positions define rule ids: behavior -> R1.., interaction_rules -> I1..,
    edge_cases_and_errors -> E1.., backward_compatibility -> B1.., acceptance_criteria -> A1.."""

    title: str
    problem: str
    public_interface: list[str] = Field(description="Exact new or changed signatures with defaults, and new attributes")
    behavior: list[str]
    interaction_rules: list[str]
    edge_cases_and_errors: list[str] = Field(description="Each states the input and exactly what happens, with exception type and exact message")
    backward_compatibility: list[str]
    acceptance_criteria: list[str]
    cases: list[Case]
    changes_from_outline: list[str] = Field(description="What you changed or added relative to the candidate outline, and why")


class QuizAnswer(BaseModel):
    id: str
    expect: Literal["returns", "raises"]
    value: str = Field(description="For returns: the exact repr() of the final expression. Empty for raises.")
    exception_type: str = Field(description="For raises: the exception class name. Empty for returns.")
    message: str = Field(description="For raises: the exact exception message. Empty for returns.")


class QuizAnswers(BaseModel):
    answers: list[QuizAnswer]


# ----------------------------------------------------------------------------------------
# Mechanical checks on a spec
# ----------------------------------------------------------------------------------------

_BANNED = re.compile(
    r"\b(not specified|unspecified|undefined behaviou?r|implementation[- ]defined|up to the implementation|"
    r"may or may not|as appropriate|or similar|and so on|TBD|TODO)\b|\betc\b\.?", re.I)
_LEAK = re.compile(r"\b(hidden tests?|test ids?|gold (patch|solution)|reference (implementation|solution)|fail_to_pass|pass_to_pass)\b", re.I)
_RULE_ID = re.compile(r"^[RIEBA][0-9]+$")


def rule_ids(spec: FeatureSpec) -> dict[str, str]:
    ids: dict[str, str] = {}
    for prefix, items in (("R", spec.behavior), ("I", spec.interaction_rules), ("E", spec.edge_cases_and_errors),
                          ("B", spec.backward_compatibility), ("A", spec.acceptance_criteria)):
        ids.update({f"{prefix}{i}": text for i, text in enumerate(items, 1)})
    return ids


def spec_text(spec: FeatureSpec) -> str:
    return "\n".join([spec.title, spec.problem, *spec.public_interface, *spec.behavior, *spec.interaction_rules,
                      *spec.edge_cases_and_errors, *spec.backward_compatibility, *spec.acceptance_criteria])


def check_spec(spec: FeatureSpec) -> list[str]:
    errs: list[str] = []
    for attr, minimum in (("public_interface", 1), ("behavior", 5), ("interaction_rules", 3), ("edge_cases_and_errors", 4),
                          ("backward_compatibility", 2), ("acceptance_criteria", 5), ("cases", config.MIN_CASES)):
        if len(getattr(spec, attr)) < minimum:
            errs.append(f"needs at least {minimum} {attr}, got {len(getattr(spec, attr))}")
    text = spec_text(spec)
    for m in sorted({m.group(0).lower() for m in _BANNED.finditer(text)}):
        errs.append(f"vague phrase in the spec: '{m}'. State exactly what happens, or remove the statement")
    for m in sorted({m.group(0).lower() for m in _LEAK.finditer(text)}):
        errs.append(f"the spec must not mention '{m}'")
    ids = rule_ids(spec)
    seen: set[str] = set()
    covered: set[str] = set()
    public = 0
    multi = 0
    for c in spec.cases:
        tag = f"case {c.id}"
        if c.id in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(c.id)
        public += c.public
        try:
            tree = ast.parse(c.code)
        except SyntaxError as exc:
            errs.append(f"{tag}: code is not valid Python ({exc.msg}, line {exc.lineno})")
            continue
        if not tree.body:
            errs.append(f"{tag}: code is empty")
        if "..." in c.code and any(isinstance(n, ast.Constant) and n.value is Ellipsis for n in ast.walk(tree)):
            errs.append(f"{tag}: code contains a `...` placeholder; it must be complete and runnable")
        if c.expect == "returns":
            if tree.body and not isinstance(tree.body[-1], ast.Expr):
                errs.append(f"{tag}: for expect=returns the last statement must be an expression")
            if not c.value.strip():
                errs.append(f"{tag}: expect=returns needs the exact repr in `value`")
        else:
            if not c.exception_type.strip() or not c.message.strip():
                errs.append(f"{tag}: expect=raises needs both exception_type and the exact message")
        bad = [r for r in c.rules_exercised if not _RULE_ID.match(r) or r not in ids]
        if bad:
            errs.append(f"{tag}: unknown rule ids {bad} (valid: R1..R{len(spec.behavior)}, I1..I{len(spec.interaction_rules)}, "
                        f"E1..E{len(spec.edge_cases_and_errors)}, B1..B{len(spec.backward_compatibility)}, A1..A{len(spec.acceptance_criteria)})")
        covered.update(c.rules_exercised)
        if len({r for r in c.rules_exercised if r[0] in "RIE"}) >= 2:
            multi += 1
    if not 3 <= public <= 6:
        errs.append(f"mark 3 to 6 cases public (the spec's examples); got {public}")
    if multi < 5:
        errs.append(f"at least 5 cases must exercise two or more R/I/E rules together; got {multi}")
    missing = [i for i in ids if i[0] in "IEA" and i not in covered]
    if missing:
        errs.append(f"these interaction rules, edge cases or acceptance criteria are not exercised by any case: {missing}")
    return errs


# ----------------------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------------------


def render_instruction(spec: FeatureSpec) -> str:
    """The spec exactly as the solver will see it. No case ids, no held-out cases."""

    def numbered(prefix: str, items: list[str]) -> list[str]:
        return [f"- **{prefix}{i}.** {t}" for i, t in enumerate(items, 1)]

    out = [f"# {spec.title}", "", spec.problem, "", "## Public interface", ""]
    out += [f"- `{s}`" for s in spec.public_interface]
    out += ["", "## Behavior", "", *numbered("R", spec.behavior),
            "", "## Interaction rules", "", *numbered("I", spec.interaction_rules),
            "", "## Edge cases and errors", "", *numbered("E", spec.edge_cases_and_errors),
            "", "## Backward compatibility", "", *numbered("B", spec.backward_compatibility),
            "", "## Examples", ""]
    for c in spec.cases:
        if c.public:
            result = f"Result: `{c.value}`" if c.expect == "returns" else f"Raises `{c.exception_type}` with message: `{c.message}`"
            out += [c.description, "", "```python", c.code.rstrip(), "```", "", result, ""]
    out += ["## Acceptance criteria", "", *numbered("A", spec.acceptance_criteria), ""]
    return "\n".join(out)


# ----------------------------------------------------------------------------------------
# Quiz
# ----------------------------------------------------------------------------------------

QUIZ_SYSTEM = (
    "You are given the written specification of a new feature for the Python library `click`. The feature is "
    "assumed to be implemented exactly as specified. You have no tools and cannot run code. Work out each "
    "result by applying the specification's rules precisely."
)


def _quiz_prompt(instruction: str, cases: list[Case]) -> str:
    items = "\n\n".join(f"### {c.id}\n```python\n{c.code.rstrip()}\n```" for c in cases)
    return (
        "SPECIFICATION:\n\n" + instruction + "\n\n---\n\n"
        "For each snippet below, predict what happens when it runs against click with this feature implemented.\n"
        "- If the snippet finishes normally: expect=returns and `value` is the exact repr() of the value of its "
        "last expression (as Python would print it with repr).\n"
        "- If it raises: expect=raises, `exception_type` is the exception class name and `message` is the exact "
        "exception message.\nAnswer every snippet, using its id.\n\n" + items
    )


def _norm_value(text: str) -> Any:
    text = text.strip()
    try:
        return ("literal", repr(ast.literal_eval(text)))
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return ("text", " ".join(text.split()))


def grade(case: Case, ans: QuizAnswer | None) -> bool:
    if ans is None or ans.expect != case.expect:
        return False
    if case.expect == "returns":
        return _norm_value(ans.value) == _norm_value(case.value)
    return (ans.exception_type.strip().split(".")[-1] == case.exception_type.strip().split(".")[-1]
            and " ".join(ans.message.split()) == " ".join(case.message.split()))


async def run_quiz(stage: str, model: str, workspace: Path, spec: FeatureSpec, log: EventLog, meta: dict[str, Any]) -> dict[str, Any]:
    held = [c for c in spec.cases if not c.public]
    ids = [c.id for c in held]
    res = await run_stage(
        stage, workspace, _quiz_prompt(render_instruction(spec), held), QUIZ_SYSTEM, log, model=model,
        max_budget_usd=config.QUIZ_MAX_BUDGET_USD, max_turns=6, schema=QuizAnswers, tools=[], fix_rounds=1,
        validator=lambda a: [] if sorted(x.id for x in a.answers) == sorted(ids) else [f"answer exactly these ids once each: {ids}"],
    )
    record_stage(meta, workspace, res)
    if res.status != "ok":
        return {"model": model, "status": res.status, "error": res.error, "total": len(held), "correct": None, "misses": []}
    answers = {a.id: a for a in res.data.answers}
    misses = [{"id": c.id, "expected": c.model_dump(include={"expect", "value", "exception_type", "message"}),
               "answered": answers[c.id].model_dump(exclude={"id"}), "rules_exercised": c.rules_exercised}
              for c in held if not grade(c, answers.get(c.id))]
    return {"model": model, "status": "ok", "total": len(held), "correct": len(held) - len(misses), "misses": misses}


# ----------------------------------------------------------------------------------------
# Spec authoring
# ----------------------------------------------------------------------------------------

SPEC_SYSTEM = (
    "You are a senior maintainer writing the specification for a new feature of an open-source library. The "
    "spec becomes a benchmark coding task: a solver receives only your spec and the repository, and its "
    "implementation is graded by tests that may only check what the spec states. A second engineer writes "
    "those tests from your spec and your case table. You specify; you do not implement.\n\n" + BASE_RULES
)


def _spec_prompt(meta: dict[str, Any], c: Candidate, nv: NoveltyVerdict, dv: DifficultyVerdict, vv: ValueVerdict,
                 report: dict[str, Any]) -> str:
    wanted = {b.module for b in c.builds_on} | set(c.source_files_to_modify)
    cards = [card for card in report["cards"] if card["path"] in wanted]
    rm = report["repo_map"]
    return f"""Write the full specification and case table for this feature of {meta['owner']}/{meta['repo']} at commit {meta['commit_sha']}.

Read the code the feature touches in ./repo before writing: exact existing behavior, message formats, and
helper conventions must match what the code really does. Where the outline is wrong about the code, fix it
and say so in `changes_from_outline`.

REQUIREMENTS
1. Complete and exact. Anything a test could check must be stated: defaults, return values, ordering,
   precedence, exact exception types and exact message strings. Never leave a case open; either define
   what happens or do not mention it.
2. Valuable. This feature will be built for real. Every rule must be something a real user of the library
   would want. The value reviewer's findings are below: drop every rule it lists as contrived, and do not add
   new rules whose only purpose is difficulty.
3. Hard for the right reason. Keep the difficulty in how precisely-stated rules INTERACT. The difficulty
   reviewer's findings are below: keep every confirmed trap, drop rejected ones, and adopt the suggested
   hardening if it is realistic for this library. Do not add difficulty through vagueness, surprise or
   arbitrary constants. If dropping a contrived rule removes a trap, find difficulty in real interactions instead.
4. Observable. Every rule must be checkable through the public interface, not through private helpers,
   internal structure or a particular algorithm.
5. Backward compatible, following this repository's compatibility rules.
6. Never mention tests, test files, or any reference implementation in the spec text.
7. Rule ids are positional: behavior -> R1.., interaction_rules -> I1.., edge_cases_and_errors -> E1..,
   backward_compatibility -> B1.., acceptance_criteria -> A1.. Refer to rules by these ids in cases.

CASE TABLE (at least {config.MIN_CASES} cases)
- Each case is self-contained Python with all imports. Prefer `click.testing.CliRunner` for command-line
  behavior, ending with an expression such as `(result.exit_code, result.output)`.
- expect=returns: `value` is the exact repr() of the last expression. expect=raises: exact exception class
  and exact message.
- Every expected value must follow from the spec text alone. A careful reader with no access to the code
  must be able to derive it. Derive each value yourself, step by step, from your own rules; if you cannot,
  the spec is incomplete.
- Avoid expected values that depend on things the spec does not control (terminal width, platform paths,
  dict ordering of unrelated data, existing help formatting you have not quoted).
- Every interaction rule, edge case and acceptance criterion needs at least one case. Every confirmed trap
  needs a case that a naive implementation would fail. At least 5 cases must exercise two or more rules together.
- Mark 3 to 6 simple, representative cases `public`: they are printed in the spec as examples. The rest are
  held out. Do not make every trap public.

CANDIDATE OUTLINE (JSON):
{json.dumps(c.model_dump(), separators=(',', ':'))}

DIFFICULTY REVIEW (JSON):
{json.dumps(dv.model_dump(), separators=(',', ':'))}

VALUE REVIEW: who benefits: {vv.who_benefits}
Contrived rules to drop: {json.dumps(vv.contrived_rules)}

NOVELTY REVIEW: closest existing thing: {nv.closest_existing}

REPOSITORY FACTS
Compatibility rules: {json.dumps(rm['compatibility_rules'], separators=(',', ':'))}
Test conventions: {json.dumps(rm['test_conventions'], separators=(',', ':'))}
Module cards for the touched files (signatures and line numbers parsed from the source):
{json.dumps(cards, separators=(',', ':'))}
"""


def _fix_prompt(misses: list[dict[str, Any]]) -> str:
    return (
        "A careful engineer read ONLY your spec (no code, no tools) and predicted the result of each held-out "
        "case. They got these wrong:\n\n" + json.dumps(misses, indent=1) + "\n\n"
        "For each one, decide which is true and fix it:\n"
        "(a) the spec does not determine the answer, or states it unclearly: tighten the spec so the expected "
        "result follows unambiguously from the text;\n"
        "(b) your expected value is wrong: re-derive it from the rules (check the code in ./repo for existing "
        "behavior the case relies on) and correct the case;\n"
        "(c) the case depends on behavior the spec does not control: replace the case.\n"
        "Do not make the feature easier and do not move held-out traps into the public examples. "
        "Output the complete corrected specification and case table."
    )


async def spec_one(workspace: Path, meta: dict[str, Any], c: Candidate, nv: NoveltyVerdict, dv: DifficultyVerdict,
                   vv: ValueVerdict, report: dict[str, Any], log: EventLog) -> dict[str, Any] | None:
    """Author, check and quiz one feature. Returns its record, or None if authoring failed."""
    out_dir = workspace / "specs" / c.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    res = await run_stage(f"spec:{c.slug}", workspace, _spec_prompt(meta, c, nv, dv, vv, report), SPEC_SYSTEM, log,
                          model=config.SPEC_MODEL, max_budget_usd=config.SPEC_MAX_BUDGET_USD, max_turns=80,
                          schema=FeatureSpec, validator=check_spec, tools=["Read", "Glob", "Grep", "Bash"])
    record_stage(meta, workspace, res)
    if res.status != "ok":
        return None
    spec: FeatureSpec = res.data
    session = res.session_id
    fairness_rounds: list[dict[str, Any]] = []
    for round_no in range(3):  # initial quiz + up to 2 fix rounds
        fair = await run_quiz(f"quiz-fairness:{c.slug}:{round_no}", config.FAIRNESS_QUIZ_MODEL, workspace, spec, log, meta)
        fairness_rounds.append(fair)
        if not fair["misses"] or round_no == 2 or session is None:
            break
        fix = await run_stage(f"spec:{c.slug}:fix{round_no + 1}", workspace, _fix_prompt(fair["misses"]), SPEC_SYSTEM, log,
                              model=config.SPEC_MODEL, max_budget_usd=config.SPEC_MAX_BUDGET_USD, max_turns=60,
                              schema=FeatureSpec, validator=check_spec, tools=["Read", "Glob", "Grep", "Bash"], resume=session)
        record_stage(meta, workspace, fix)
        if fix.status != "ok":
            break
        spec, session = fix.data, fix.session_id or session
    bench = await run_quiz(f"quiz-benchmark:{c.slug}", config.QUIZ_MODEL, workspace, spec, log, meta)
    quiz = {"fairness_rounds": fairness_rounds, "benchmark": bench,
            "fair": fairness_rounds[-1]["status"] == "ok" and not fairness_rounds[-1]["misses"],
            "likely_too_easy": bench["status"] == "ok" and not bench["misses"]}
    write_json(out_dir / "spec.json", spec.model_dump())
    write_json(out_dir / "cases.json", [x.model_dump() for x in spec.cases])
    write_json(out_dir / "quiz.json", quiz)
    (out_dir / "instruction.md").write_text(render_instruction(spec), encoding="utf-8")
    return {"slug": c.slug, "candidate": c.model_dump(), "novelty": nv.model_dump(), "difficulty": dv.model_dump(),
            "value": vv.model_dump(),
            "spec": spec.model_dump(), "quiz": quiz}


def to_feature(record: dict[str, Any]) -> Feature:
    """The hand-off form of one specified feature (pipeline/propose.py Feature), read by the test agent.

    Only the public cases become examples; held-out cases stay in specs/<slug>/cases.json."""
    c = Candidate.model_validate(record["candidate"])
    spec = FeatureSpec.model_validate(record["spec"])
    examples = [FeatureExample(code=x.code, expected=(f"returns {x.value}" if x.expect == "returns"
                                                       else f"raises {x.exception_type}: {x.message}"))
                for x in spec.cases if x.public]
    return Feature(
        slug=c.slug, category=c.category, title=spec.title, problem=spec.problem,
        public_interface=spec.public_interface, behavior=spec.behavior, interaction_rules=spec.interaction_rules,
        edge_cases_and_errors=spec.edge_cases_and_errors, backward_compatibility=spec.backward_compatibility,
        examples=examples, acceptance_criteria=spec.acceptance_criteria, builds_on=c.builds_on,
        extension_point="; ".join(c.integration_points), source_files_to_modify=c.source_files_to_modify,
        source_files_to_add=c.source_files_to_add, regression_test_files=c.regression_test_files,
        new_test_file=c.new_test_file, novelty_rationale=c.novelty_rationale,
        difficulty_rationale=record["difficulty"]["reasoning"], estimated_gold_lines=c.estimated_gold_lines,
    )


def render_features(meta: dict[str, Any], records: list[dict[str, Any]], dropped: list[dict[str, Any]]) -> str:
    out = [f"# Feature plan: {meta['owner']}/{meta['repo']} @ `{meta['commit_sha'][:12]}`", "",
           f"Proposed by `{config.PROPOSE_MODEL}`, novelty-audited by `{config.NOVELTY_MODEL}`, difficulty-audited by "
           f"`{config.DIFFICULTY_MODEL}`, value-audited by `{config.VALUE_MODEL}`, specified by `{config.SPEC_MODEL}`. Blind quiz: fairness reader "
           f"`{config.FAIRNESS_QUIZ_MODEL}`, benchmark model `{config.QUIZ_MODEL}`.", "",
           "The quiz is a proxy: a model reads only the spec and predicts each held-out case. Expected values are "
           "not yet confirmed by running a reference implementation.", "",
           "| # | Feature | Category | Value | Difficulty | Cases | Fairness reader | Benchmark model |", "|---|---|---|---|---|---|---|---|"]

    def score(q: dict[str, Any]) -> str:
        return f"{q['correct']}/{q['total']}" if q.get("correct") is not None else f"failed ({q['status']})"

    for i, r in enumerate(records, 1):
        q = r["quiz"]
        out.append(f"| {i} | `{r['slug']}` | {r['candidate']['category']} | {r['value']['score']}/5 | {r['difficulty']['score']}/5 | {len(r['spec']['cases'])} | "
                   f"{score(q['fairness_rounds'][-1])} | {score(q['benchmark'])} |")
    if dropped:
        out += ["", "## Specified but not kept", ""]
        out += [f"- `{d['slug']}`: {d['reason']}" for d in dropped]
    for i, r in enumerate(records, 1):
        spec = FeatureSpec.model_validate(r["spec"])
        q = r["quiz"]
        out += ["", "---", "", f"## {i}. `{r['slug']}`", "",
                f"- Gold edits: {', '.join(f'`{p}`' for p in r['candidate']['source_files_to_modify'] + r['candidate']['source_files_to_add'])}",
                f"- New test file: `{r['candidate']['new_test_file']}` · Regression: {', '.join(f'`{p}`' for p in r['candidate']['regression_test_files'])}",
                f"- Files: `specs/{r['slug']}/instruction.md`, `cases.json`, `quiz.json`",
                f"- Fairness reader after {len(q['fairness_rounds'])} round(s): {score(q['fairness_rounds'][-1])}"
                + ("" if q["fair"] else " — NOT fully resolved; cases still missed: " + ", ".join(m["id"] for m in q["fairness_rounds"][-1]["misses"])),
                f"- Benchmark model: {score(q['benchmark'])}; missed: {', '.join(m['id'] for m in q['benchmark']['misses']) or 'none'}",
                f"- Who benefits (value audit): {r['value']['who_benefits']}",
                f"- Likely failure (difficulty audit): {r['difficulty']['likely_failure_mode']}", "",
                render_instruction(spec).replace("\n# ", "\n### ").replace("\n## ", "\n#### ").replace("# ", "### ", 1)]
    return "\n".join(out)


async def write_specs(run_id: str) -> Path:
    """Specify and quiz the selected candidates; replace likely-too-easy ones from the reserves once."""
    workspace, meta = load_run(run_id)
    if not (workspace / "selection.json").is_file():
        raise ExploreError(f"run {run_id} has no selection.json; run `validate` first")
    plan, novelty, difficulty, value, sel = load_audit(workspace)
    by_slug = {c.slug: c for c in plan.candidates}
    report = json.loads((workspace / "report.json").read_text(encoding="utf-8"))
    log = EventLog(workspace / "events.jsonl")
    sem = asyncio.Semaphore(config.AGENT_CONCURRENCY)

    async def job(slug: str):
        async with sem:
            return slug, await spec_one(workspace, meta, by_slug[slug], novelty[slug], difficulty[slug], value[slug], report, log)

    print(f"run {run_id}: specifying {len(sel.selected)} features (model {config.SPEC_MODEL})", file=sys.stderr)
    first = await asyncio.gather(*[job(s) for s in sel.selected])
    kept = [r for _, r in first if r is not None and not r["quiz"]["likely_too_easy"]]
    dropped = [{"slug": s, "reason": "spec authoring failed"} for s, r in first if r is None]
    easy = [r for _, r in first if r is not None and r["quiz"]["likely_too_easy"]]
    need = len(sel.selected) - len(kept)
    replacements = sel.reserves[:need]
    if replacements:
        print(f"run {run_id}: {need} feature(s) failed or look too easy; specifying reserves {replacements}", file=sys.stderr)
        second = await asyncio.gather(*[job(s) for s in replacements])
        for s, r in second:
            if r is None:
                dropped.append({"slug": s, "reason": "reserve: spec authoring failed"})
            elif r["quiz"]["likely_too_easy"]:
                easy.append(r)
            else:
                kept.append(r)
    # Still short: fall back to the too-easy ones, hardest audit score first, and say so.
    easy.sort(key=lambda r: -r["difficulty"]["score"])
    while len(kept) < len(sel.selected) and easy:
        r = easy.pop(0)
        r["quiz"]["kept_despite_easy"] = True
        kept.append(r)
    dropped += [{"slug": r["slug"], "reason": "benchmark model predicted every held-out case; replaced by a reserve"} for r in easy]
    hand_off = FeaturePlan(variation_strategy=plan.variation_strategy, features=[to_feature(r) for r in kept])
    # `features` is the FeaturePlan the test agent reads; `records` and `dropped` are extra detail it ignores.
    write_json(workspace / "features.json", {**hand_off.model_dump(), "records": kept, "dropped": dropped})
    (workspace / "features.md").write_text(render_features(meta, kept, dropped), encoding="utf-8")
    return workspace
