"""Stage 2: validate candidate features, then select the ones to build.

Two independent audits over every candidate in runs/<run_id>/candidates.json:

    novelty     (web access)   is it already in the repo's issues/PRs, in an add-on library,
                               or a drop-in from a sibling library?
    difficulty  (repo access)  how hard is it for a small model once the spec is explicit?

The application then checks the audits themselves (every search the novelty auditor claims
must be a web call it really made, per the audit log) and selects N features with no model
involved: novel only, difficulty >= MIN_DIFFICULTY, highest score first, distinct categories
and distinct primary source files.

Output, under runs/<run_id>/: audit.json, selection.json, candidates.md.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from pipeline import config
from pipeline.agent import BASE_RULES, EventLog, run_stage
from pipeline.explore import ExploreError, load_run, record_stage, write_json
from pipeline.propose import ECOSYSTEM, Candidate, CandidatePlan

# ----------------------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------------------


class Evidence(BaseModel):
    url: str
    finding: str = Field(description="What this page shows about whether the feature already exists")


class NoveltyVerdict(BaseModel):
    slug: str
    verdict: Literal["novel", "exists_upstream", "in_progress", "drop_in"] = Field(
        description="novel: nothing equivalent found. exists_upstream: already in the repo or merged after the pin. "
        "in_progress: an open pull request implements it, or maintainers have accepted it and work is under way "
        "(an open feature REQUEST with no implementation is evidence of demand, not in_progress). "
        "drop_in: an add-on or sibling library already provides "
        "essentially this feature."
    )
    closest_existing: str = Field(description="The nearest existing thing found anywhere, and how the candidate differs")
    reasoning: str
    searches: list[str] = Field(description="The exact WebSearch queries and WebFetch URLs you used for this candidate")
    evidence: list[Evidence]


class NoveltyAudit(BaseModel):
    verdicts: list[NoveltyVerdict]


class DifficultyVerdict(BaseModel):
    slug: str
    score: int = Field(description="1 (trivial for a small model) to 5 (a small model will very likely fail)", ge=1, le=5)
    interacting_rules: int = Field(description="How many rules genuinely interact (not merely coexist)")
    confirmed_traps: list[str] = Field(description="Traps you confirmed against the code, including any the proposer missed")
    rejected_traps: list[str] = Field(description="Claimed traps that are not real once you read the code")
    integration_depth: str = Field(description="Which existing code paths must change consistently")
    survives_explicit_spec: bool = Field(description="True if it stays hard even when every rule is written down precisely")
    likely_failure_mode: str = Field(description="The most likely way a small model's implementation would be wrong")
    hardening: str = Field(description="One concrete, realistic extra interacting rule that would raise the difficulty; empty if none is needed")
    reasoning: str


class DifficultyAudit(BaseModel):
    verdicts: list[DifficultyVerdict]


class ValueVerdict(BaseModel):
    slug: str
    score: int = Field(
        description="1 (nobody would want this) to 5 (clearly useful to many users of the library, with evidence)", ge=1, le=5)
    who_benefits: str = Field(description="Which users of the library, doing what, and how often they hit this need")
    user_evidence: list[Evidence] = Field(
        description="Pages showing real users asking for this or working around its absence: issues, discussions, "
        "Q&A questions, add-ons or snippets that exist because of the gap")
    fits_library: bool = Field(description="True if it fits the library's design and scope, as its maintainers would see it")
    contrived_rules: list[str] = Field(
        description="Rules or traps in the outline that exist only to make the task harder and that a real user would "
        "not want; quote them. Empty if none")
    reasoning: str
    searches: list[str] = Field(description="The exact WebSearch queries and WebFetch URLs you used for this candidate")


class ValueAudit(BaseModel):
    verdicts: list[ValueVerdict]


class Selection(BaseModel):
    selected: list[str]
    reserves: list[str] = Field(description="Eligible candidates not selected, best first")
    reasons: dict[str, str] = Field(description="Why each candidate was selected, held in reserve, or rejected")


# ----------------------------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------------------------

NOVELTY_SYSTEM = (
    "You are a sceptical reviewer checking whether proposed features for an open-source library are genuinely "
    "new. Your default assumption is that someone has already built or requested each one; you look for the "
    "evidence. You report only what pages you actually opened show.\n\n" + BASE_RULES
)

VALUE_SYSTEM = (
    "You are a sceptical maintainer of an open-source library deciding whether proposed features are worth "
    "having. Your default assumption is that a feature is a solution looking for a problem until you find "
    "evidence that real users need it. You report only what pages you actually opened show.\n\n" + BASE_RULES
)

DIFFICULTY_SYSTEM = (
    "You are a sceptical reviewer estimating how hard proposed features are for a small, fast coding model "
    "that receives a complete written spec and the repository. You read the code before judging. Your "
    "default assumption is that a feature is easier than its proposer claims.\n\n" + BASE_RULES
)


def _brief(c: Candidate) -> dict[str, Any]:
    return c.model_dump(exclude={"novelty_rationale", "estimated_gold_lines"})


def _novelty_prompt(meta: dict[str, Any], batch: list[Candidate]) -> str:
    owner, repo = meta["owner"], meta["repo"]
    return f"""Audit the novelty of these {len(batch)} candidate features for {owner}/{repo} (pinned at {meta['commit_sha']}).

For EACH candidate, check three places with the web tools:
1. The project's own issues and pull requests, open and closed. Search by keyword, for example
   https://github.com/{owner}/{repo}/issues?q=<keywords> and https://github.com/{owner}/{repo}/pulls?q=<keywords>.
2. The add-on ecosystem and sibling libraries: {ECOSYSTEM}. Check their docs or READMEs for the same capability.
3. A general web search for the capability by name.
You may also Grep ./repo to confirm the feature is not already there.

Verdicts: `exists_upstream`, `in_progress`, `drop_in`, or `novel`. `in_progress` means an open pull request
implements it, or maintainers accepted it and work is under way. An open or stale feature REQUEST with no
implementation is not `in_progress`: it is evidence that users want the feature, and the candidate stays `novel`
unless something else applies. Each candidate lists the requests it is based on in `demand_refs`.
A candidate is `drop_in` only if an existing
library provides essentially the same capability with the same shape; sharing a theme is not enough, and you
must say how the candidate differs in `closest_existing`. Use at least 3 web calls per candidate. In `searches`
list the exact queries and URLs you used for that candidate, copied verbatim from your tool calls: they are
cross-checked against the log of your real tool calls, and so is every evidence URL.

CANDIDATES (JSON):
{json.dumps([_brief(c) for c in batch], separators=(',', ':'))}
"""


def _difficulty_prompt(meta: dict[str, Any], batch: list[Candidate]) -> str:
    return f"""Audit the difficulty of these {len(batch)} candidate features for {meta['owner']}/{meta['repo']} in ./repo.

The solver is a small, fast model. It gets the repository and a spec that states every rule precisely, with
examples. It is good at writing plausible code and at following a single clear rule. It tends to fail when
several rules interact (precedence, eligibility, ordering, state across calls), when a change must be made
consistently in more than one code path, and when the obvious implementation is subtly wrong.

For EACH candidate, read the code it touches (integration points, the functions it extends), then:
- count the rules that genuinely interact;
- confirm or reject each claimed trap against the code, and add traps the proposer missed;
- describe the integration depth;
- decide whether the difficulty survives a fully explicit spec, or disappears once everything is written down;
- state the most likely wrong implementation;
- score 1-5: 1 = a single obvious change; 2 = a few independent rules; 3 = several rules, some interaction,
  one real trap; 4 = multiple interacting rules and traps across code paths; 5 = a small model will very
  likely get at least one required behavior wrong;
- if the score is 3 or lower, propose one concrete and realistic hardening rule that adds interaction
  without making the feature artificial.
Do not use the web.

CANDIDATES (JSON):
{json.dumps([_brief(c) for c in batch], separators=(',', ':'))}
"""


def _value_prompt(meta: dict[str, Any], batch: list[Candidate]) -> str:
    owner, repo = meta["owner"], meta["repo"]
    return f"""Judge whether these {len(batch)} candidate features would genuinely be valuable additions to {owner}/{repo}.

These features will be implemented for real on top of the library, so they must make sense to its users and
maintainers, not just be puzzles. For EACH candidate:
1. Look for evidence that real users need it, with the web tools: the project's issues and discussions
   (https://github.com/{owner}/{repo}/issues?q=<keywords>, https://github.com/{owner}/{repo}/discussions),
   Stack Overflow questions, blog posts or snippets showing people working around its absence, and add-ons
   that exist because of the gap. A feature request that was declined by maintainers counts against it;
   say why it was declined. Candidates list the user requests they were designed from in `demand_refs`; those
   pages were already fetched and verified, so you may cite them as evidence directly, but judge for yourself
   whether the candidate actually addresses what those users asked for. A candidate that only loosely relates
   to its demand_refs scores low.
2. Say who benefits (which users, doing what) and how often they would hit this need.
3. Decide whether it fits the library's design and scope as its maintainers would see it. You may Grep and
   Read ./repo, including its docs, to check the library's stated philosophy.
4. List any rules or traps in the outline that exist only to make the task harder and that a real user would
   not want (arbitrary thresholds, surprising precedence, special cases with no use case). Quote them.
5. Score 1-5: 1 = nobody would want this; 2 = plausible but no evidence of demand, or a poor fit for the
   library; 3 = sensible, some evidence of need; 4 = clear need with evidence; 5 = frequently requested or
   commonly worked around.

Use at least 3 web calls per candidate. In `searches` list the exact queries and URLs you used for that
candidate, copied verbatim from your tool calls: they are cross-checked against the log of your real tool
calls, and so is every evidence URL.

CANDIDATES (JSON):
{json.dumps([_brief(c) for c in batch], separators=(',', ':'))}
"""


# ----------------------------------------------------------------------------------------
# Checking the audits
# ----------------------------------------------------------------------------------------


def _web_calls(events_path: Path, stage: str) -> tuple[set[str], str]:
    """(exact queries and URLs the stage sent to web tools, all text the web tools returned)."""
    sent: set[str] = set()
    returned: list[str] = []
    web_ids: set[str] = set()
    for line in events_path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("stage") != stage:
            continue
        if e["kind"] == "tool_use" and e["name"] in {"WebSearch", "WebFetch"}:
            web_ids.add(e["id"])
            for key in ("query", "url"):
                if e["input"].get(key):
                    sent.add(str(e["input"][key]).strip())
        elif e["kind"] == "tool_result" and e["id"] in web_ids:
            returned.append(str(e["content"]))
    return sent, "\n".join(returned)


def _check_web(slug: str, searches: list[str], evidence: list[Evidence], sent: set[str], returned: str) -> list[str]:
    """Every claimed search must be a real web call; every evidence URL must have been fetched or returned."""
    errs: list[str] = []
    real = [s for s in searches if s.strip() in sent]
    fake = [s for s in searches if s.strip() not in sent]
    if fake:
        errs.append(f"[{slug}] these searches are not in the log of your web calls (copy them verbatim): {fake[:3]}")
    if len(real) < 3:
        errs.append(f"[{slug}] needs at least 3 real web calls, found {len(real)}")
    for ev in evidence:
        url = ev.url.strip()
        if url not in sent and url.split("#")[0].rstrip("/") not in returned:
            errs.append(f"[{slug}] evidence URL was neither fetched nor returned by a search: {url}")
    return errs


def _check_slugs(got: list[str], slugs: list[str]) -> list[str]:
    return [] if sorted(got) == sorted(slugs) else [f"verdicts must cover exactly these slugs once each: {slugs}; got {got}"]


def make_novelty_validator(events_path: Path, stage: str, slugs: list[str]):
    def validate(audit: NoveltyAudit) -> list[str]:
        errs = _check_slugs([v.slug for v in audit.verdicts], slugs)
        sent, returned = _web_calls(events_path, stage)
        for v in audit.verdicts:
            errs += _check_web(v.slug, v.searches, v.evidence, sent, returned)
            if v.verdict != "novel" and not v.evidence:
                errs.append(f"[{v.slug}] verdict {v.verdict} needs at least one evidence URL showing the existing thing")
        return errs

    return validate


def make_value_validator(events_path: Path, stage: str, slugs: list[str], verified_urls: set[str] = frozenset()):
    """`verified_urls`: URLs already confirmed as fetched by the demand-mining stage; they count as real evidence."""

    def validate(audit: ValueAudit) -> list[str]:
        errs = _check_slugs([v.slug for v in audit.verdicts], slugs)
        sent, returned = _web_calls(events_path, stage)
        for v in audit.verdicts:
            unverified = [e for e in v.user_evidence if e.url.strip() not in verified_urls]
            errs += _check_web(v.slug, v.searches, unverified, sent, returned)
            if v.score >= 4 and not v.user_evidence:
                errs.append(f"[{v.slug}] a value score of {v.score} needs at least one evidence URL showing user demand")
        return errs

    return validate


def make_difficulty_validator(slugs: list[str]):
    def validate(audit: DifficultyAudit) -> list[str]:
        got = [v.slug for v in audit.verdicts]
        errs = [] if sorted(got) == sorted(slugs) else [f"verdicts must cover exactly these slugs once each: {slugs}; got {got}"]
        for v in audit.verdicts:
            if v.score <= 3 and not v.hardening.strip():
                errs.append(f"[{v.slug}] score {v.score} needs a hardening proposal")
        return errs

    return validate


# ----------------------------------------------------------------------------------------
# Selection (no model)
# ----------------------------------------------------------------------------------------


def select(candidates: list[Candidate], novelty: dict[str, NoveltyVerdict], difficulty: dict[str, DifficultyVerdict],
           value: dict[str, ValueVerdict], n: int = config.N_FEATURES) -> Selection:
    reasons: dict[str, str] = {}
    eligible: list[Candidate] = []
    for c in candidates:
        nv, dv, vv = novelty.get(c.slug), difficulty.get(c.slug), value.get(c.slug)
        if nv is None or dv is None or vv is None:
            reasons[c.slug] = "rejected: audit missing (a validation session failed)"
        elif nv.verdict != "novel":
            reasons[c.slug] = f"rejected: novelty verdict {nv.verdict} ({nv.closest_existing})"
        elif vv.score < config.MIN_VALUE or not vv.fits_library:
            why = "does not fit the library" if not vv.fits_library else f"value {vv.score}/5 is below {config.MIN_VALUE}"
            reasons[c.slug] = f"rejected: {why}"
        elif dv.score < config.MIN_DIFFICULTY:
            reasons[c.slug] = f"rejected: difficulty {dv.score}/5 is below {config.MIN_DIFFICULTY}"
        else:
            eligible.append(c)
    order = {c.slug: i for i, c in enumerate(candidates)}
    eligible.sort(key=lambda c: (-difficulty[c.slug].score, -value[c.slug].score,
                                 -int(difficulty[c.slug].survives_explicit_spec),
                                 -len(difficulty[c.slug].confirmed_traps), order[c.slug]))

    def label(c: Candidate) -> str:
        return f"novel, difficulty {difficulty[c.slug].score}/5, value {value[c.slug].score}/5"

    chosen: list[Candidate] = []
    # Hardest first. Pass 1: distinct category and at most 2 features per primary source file.
    # Pass 2: distinct category only. Pass 3: anything left.
    for rule in ("category, at most 2 per file", "category", "none"):
        for c in eligible:
            if len(chosen) >= n or c in chosen:
                continue
            same_cat = any(x.category.strip().lower() == c.category.strip().lower() for x in chosen)
            same_file = sum(x.source_files_to_modify[0] == c.source_files_to_modify[0] for x in chosen)
            if (rule == "category, at most 2 per file" and (same_cat or same_file >= 2)) or (rule == "category" and same_cat):
                continue
            chosen.append(c)
            relaxed = "" if rule == "category, at most 2 per file" else f"; variation rule relaxed to: {rule}"
            reasons[c.slug] = f"selected: {label(c)}{relaxed}"
    reserves = [c for c in eligible if c not in chosen]
    for c in reserves:
        reasons[c.slug] = f"reserve: {label(c)}, not needed for the top {n}"
    return Selection(selected=[c.slug for c in chosen], reserves=[c.slug for c in reserves], reasons=reasons)


# ----------------------------------------------------------------------------------------
# Rendering and orchestration
# ----------------------------------------------------------------------------------------


def render_markdown(meta: dict[str, Any], plan: CandidatePlan, novelty: dict[str, NoveltyVerdict],
                    difficulty: dict[str, DifficultyVerdict], value: dict[str, ValueVerdict], sel: Selection) -> str:
    out = [f"# Candidate features: {meta['owner']}/{meta['repo']} @ `{meta['commit_sha'][:12]}`", "",
           f"Proposed by `{config.PROPOSE_MODEL}`. Novelty audited by `{config.NOVELTY_MODEL}` (web). Value audited by "
           f"`{config.VALUE_MODEL}` (web). Difficulty audited by `{config.DIFFICULTY_MODEL}`. Selection is done by the "
           "pipeline, not a model.", "",
           "## Summary", "", "| Candidate | Category | Novelty | Value | Difficulty | Outcome |", "|---|---|---|---|---|---|"]
    for c in plan.candidates:
        nv, dv, vv = novelty.get(c.slug), difficulty.get(c.slug), value.get(c.slug)
        out.append(f"| `{c.slug}` | {c.category} | {nv.verdict if nv else 'n/a'} | {f'{vv.score}/5' if vv else 'n/a'} | "
                   f"{f'{dv.score}/5' if dv else 'n/a'} | {sel.reasons.get(c.slug, '').split(':')[0]} |")
    out += ["", "## Variation strategy", plan.variation_strategy, ""]
    for c in plan.candidates:
        nv, dv, vv = novelty.get(c.slug), difficulty.get(c.slug), value.get(c.slug)
        out += [f"## `{c.slug}`: {c.title}", "", f"**Outcome:** {sel.reasons.get(c.slug, 'n/a')}", "",
                f"- Category: {c.category} · Gold edits: {', '.join(f'`{p}`' for p in c.source_files_to_modify + c.source_files_to_add)}",
                f"- Problem: {c.problem}", ""]
        if nv:
            out += [f"**Novelty: {nv.verdict}.** {nv.reasoning}", "", f"- Closest existing: {nv.closest_existing}"]
            out += [f"- Evidence: [{e.url}]({e.url}): {e.finding}" for e in nv.evidence]
            out.append("")
        if vv:
            out += [f"**Value: {vv.score}/5** (fits the library: {'yes' if vv.fits_library else 'no'}). {vv.reasoning}", "",
                    f"- Who benefits: {vv.who_benefits}"]
            out += [f"- User evidence: [{e.url}]({e.url}): {e.finding}" for e in vv.user_evidence]
            out += [f"- Contrived rule (to drop): {r}" for r in vv.contrived_rules]
            out.append("")
        if dv:
            out += [f"**Difficulty: {dv.score}/5.** {dv.reasoning}", "",
                    f"- Interacting rules: {dv.interacting_rules} · Survives an explicit spec: {'yes' if dv.survives_explicit_spec else 'no'}",
                    f"- Likely failure: {dv.likely_failure_mode}"]
            out += [f"- Confirmed trap: {t}" for t in dv.confirmed_traps]
            out += [f"- Rejected trap: {t}" for t in dv.rejected_traps]
            if dv.hardening.strip():
                out.append(f"- Suggested hardening: {dv.hardening}")
            out.append("")
    return "\n".join(out)


KINDS = {"novelty": NoveltyVerdict, "difficulty": DifficultyVerdict, "value": ValueVerdict}


def _load_verdicts(workspace: Path) -> dict[str, dict[str, Any]]:
    path = workspace / "audit.json"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return {kind: {k: cls.model_validate(v) for k, v in raw.get(kind, {}).items()} for kind, cls in KINDS.items()}


def load_audit(workspace: Path):
    """(plan, novelty, difficulty, value, selection) for a validated run."""
    plan = CandidatePlan.model_validate_json((workspace / "candidates.json").read_text(encoding="utf-8"))
    v = _load_verdicts(workspace)
    sel = Selection.model_validate_json((workspace / "selection.json").read_text(encoding="utf-8"))
    return plan, v["novelty"], v["difficulty"], v["value"], sel


async def validate_candidates(run_id: str) -> Path:
    """Audit every candidate for novelty, value and difficulty, then select. Returns the run directory.

    Verdicts already in audit.json for the current candidates are kept, so a re-run only does what is missing.
    """
    workspace, meta = load_run(run_id)
    if not (workspace / "candidates.json").is_file():
        raise ExploreError(f"run {run_id} has no candidates.json; run `propose` first")
    plan = CandidatePlan.model_validate_json((workspace / "candidates.json").read_text(encoding="utf-8"))
    events = workspace / "events.jsonl"
    log = EventLog(events)
    size = config.AUDIT_BATCH_SIZE
    batches = [plan.candidates[i:i + size] for i in range(0, len(plan.candidates), size)]
    sem = asyncio.Semaphore(config.AGENT_CONCURRENCY)
    verdicts = _load_verdicts(workspace)
    current = {c.slug for c in plan.candidates}
    verdicts = {kind: {k: v for k, v in vs.items() if k in current} for kind, vs in verdicts.items()}
    demand_path = workspace / "demand.json"
    demand_urls = ({d["url"].strip() for d in json.loads(demand_path.read_text(encoding="utf-8"))["requests"]}
                   if demand_path.is_file() else set())

    def todo(kind: str) -> list[tuple[int, list[Candidate]]]:
        return [(i, b) for i, b in enumerate(batches, 1) if any(c.slug not in verdicts[kind] for c in b)]

    web = {
        "novelty": (_novelty_prompt, NOVELTY_SYSTEM, config.NOVELTY_MODEL, config.NOVELTY_MAX_BUDGET_USD, NoveltyAudit,
                    make_novelty_validator),
        "value": (_value_prompt, VALUE_SYSTEM, config.VALUE_MODEL, config.VALUE_MAX_BUDGET_USD, ValueAudit,
                  lambda ev, st, slugs: make_value_validator(ev, st, slugs, demand_urls)),
    }

    async def web_job(kind: str, i: int, batch: list[Candidate]):
        prompt, system, model, budget, schema, make = web[kind]
        stage = f"{kind}:{i}"
        async with sem:
            return await run_stage(stage, workspace, prompt(meta, batch), system, log, model=model, max_budget_usd=budget,
                                   max_turns=120, schema=schema, validator=make(events, stage, [c.slug for c in batch]))

    async def difficulty_job(i: int, batch: list[Candidate]):
        async with sem:
            return await run_stage(f"difficulty:{i}", workspace, _difficulty_prompt(meta, batch), DIFFICULTY_SYSTEM, log,
                                   model=config.DIFFICULTY_MODEL, max_budget_usd=config.DIFFICULTY_MAX_BUDGET_USD,
                                   max_turns=100, schema=DifficultyAudit, tools=["Read", "Glob", "Grep", "Bash"],
                                   validator=make_difficulty_validator([c.slug for c in batch]))

    jobs = ([web_job("novelty", i, b) for i, b in todo("novelty")]
            + [web_job("value", i, b) for i, b in todo("value")]
            + [difficulty_job(i, b) for i, b in todo("difficulty")])
    print(f"run {run_id}: validating {len(plan.candidates)} candidates; {len(jobs)} audit session(s) to run "
          f"(novelty {config.NOVELTY_MODEL}, value {config.VALUE_MODEL}, difficulty {config.DIFFICULTY_MODEL})",
          file=sys.stderr)
    for res in await asyncio.gather(*jobs):
        record_stage(meta, workspace, res)
        if res.status == "ok":
            verdicts[res.stage.split(":")[0]].update({v.slug: v for v in res.data.verdicts})
    novelty, difficulty, value = verdicts["novelty"], verdicts["difficulty"], verdicts["value"]
    sel = select(plan.candidates, novelty, difficulty, value)
    write_json(workspace / "audit.json", {kind: {k: v.model_dump() for k, v in verdicts[kind].items()} for kind in KINDS})
    write_json(workspace / "selection.json", sel.model_dump())
    (workspace / "candidates.md").write_text(render_markdown(meta, plan, novelty, difficulty, value, sel), encoding="utf-8")
    return workspace
