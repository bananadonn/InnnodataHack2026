"""Stage 0: explore a GitHub repository with the Claude Agent SDK and write a grounded report.

Input: a GitHub URL (and optional ref). Three kinds of agent session, all read-only:

    map        one session: purpose, modules, tests, commands, compatibility rules
    card:<m>   one session per key module: interfaces, behavior, errors, examples, tests,
               extension points, gaps
    upstream   one session with web access: what changed upstream after the pinned commit,
               what is open or planned (novelty check)

Then the application verifies the cards against the code (pipeline/verify.py): signatures and
line numbers are taken from the parsed source, and symbols that do not exist are dropped.

Output, under runs/<run_id>/:

    repo/          the clone (gitignored)
    run.json       url, ref, commit SHA, per-stage status/usage/cost, total cost
    events.jsonl   every assistant message, tool call and tool result (audit log)
    report.json    map + verified cards + upstream + verification summary
    report.md      the same, readable
    qa.md          follow-up questions and answers (after `ask`)

Implements pipeline_plan.md.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from pydantic import BaseModel, Field

from pipeline import config, verify
from pipeline.agent import BASE_RULES, EventLog, StageResult, run_stage

# ----------------------------------------------------------------------------------------
# Schemas: what the agents output
# ----------------------------------------------------------------------------------------


class Evidence(BaseModel):
    claim: str
    path: str = Field(description="Exactly one repo-relative file path")
    line_start: int
    line_end: int


class EntryPoint(BaseModel):
    path: str = Field(description="Exactly one repo-relative file path, no line number")
    line: int
    description: str


class Module(BaseModel):
    path: str = Field(description="Exactly one repo-relative source file path, no line number")
    role: str
    feature_relevance: str = Field(description="Why a new feature might plausibly be built in or on this module")


class TestArea(BaseModel):
    path: str = Field(description="Exactly one repo-relative test file path")
    covers: list[str] = Field(description="Repo-relative source files this test file exercises")


class Command(BaseModel):
    command: str
    purpose: str
    source: str = Field(description="File where the command was found")
    verified: bool = Field(description="True only if the command was actually executed during this run")


class RepoMap(BaseModel):
    """Whole-repository overview."""

    purpose: str
    intended_users: str
    languages: list[str]
    frameworks: list[str]
    dependencies: list[str]
    entry_points: list[EntryPoint]
    key_modules: list[Module] = Field(description="Ordered by how relevant the module is for adding new features, most relevant first")
    execution_flow: str = Field(description="How a typical call travels through the key modules")
    test_runner: str
    test_layout: list[TestArea]
    test_conventions: list[str] = Field(description="How this repo's tests are written: fixtures, helpers, assertion style, naming")
    compatibility_rules: list[Evidence] = Field(
        description="Constraints a new feature must respect: what is public API, how deprecations are done, "
        "supported language versions, warning policy, typing requirements"
    )
    setup_and_test_commands: list[Command]
    evidence: list[Evidence]
    open_questions: list[str]
    limitations: list[str]


class InterfaceClaim(BaseModel):
    name: str = Field(description="Qualified name as defined in this file, e.g. `Option.get_default` or `echo`")
    behavior: str = Field(description="What it does, including defaults and ordering, as the code implements it")
    edge_cases: list[str] = Field(description="How it handles unusual input: empty, None, wrong type, boundaries")
    raises: list[str] = Field(description="Exception class names this code raises directly")


class Example(BaseModel):
    description: str
    code: str = Field(description="A short usage snippet copied from the repo's docs or tests")
    source_path: str
    line_start: int
    line_end: int


class TestNote(BaseModel):
    path: str = Field(description="Exactly one repo-relative test file path")
    how_it_asserts: str = Field(description="What these tests check and how (helpers used, what is compared)")


class ExtensionPoint(BaseModel):
    name: str
    path: str
    line: int
    what_could_attach: str = Field(description="What kind of new behavior could plug in here and how")


class Gap(BaseModel):
    description: str = Field(description="A capability this module notably lacks")
    why_plausible: str = Field(description="Why it would be a natural extension of what exists")
    nearest_existing: str = Field(description="Qualified name of the closest existing interface")


class CardClaim(BaseModel):
    """Deep dive on one module."""

    summary: str
    interfaces: list[InterfaceClaim] = Field(description="Up to 25 public interfaces most relevant for building features")
    error_conventions: str = Field(description="Which exception types are used for what, and the message style")
    examples: list[Example]
    tests: list[TestNote]
    extension_points: list[ExtensionPoint]
    gaps: list[Gap]
    limitations: list[str]


class UpstreamItem(BaseModel):
    title: str
    url: str
    summary: str


class Upstream(BaseModel):
    """What exists or is in motion upstream beyond the pinned commit."""

    pinned_version: str
    latest_version: str
    changes_after_pin: list[UpstreamItem] = Field(description="Features and behavior changes merged or released after the pinned commit")
    open_or_planned: list[UpstreamItem] = Field(description="Open issues and pull requests proposing new features")
    do_not_propose: list[str] = Field(description="Short capability descriptions that already exist upstream or are in progress")
    limitations: list[str]


# ----------------------------------------------------------------------------------------
# Schemas: what is stored after verification
# ----------------------------------------------------------------------------------------


class Interface(InterfaceClaim):
    kind: str | None = None
    signature: str | None = Field(default=None, description="Parsed from the source, not written by the model")
    line_start: int | None = None
    line_end: int | None = None
    verified: bool = False
    raises_unconfirmed: list[str] = Field(
        default_factory=list,
        description="Exceptions the model says can result, but whose name is not in this interface's own source "
        "(typically raised through a helper). Treat as a lead to confirm in the code, not as fact.",
    )


class ModuleCard(BaseModel):
    path: str
    summary: str
    interfaces: list[Interface]
    error_conventions: str
    examples: list[Example]
    tests: list[TestNote]
    extension_points: list[ExtensionPoint]
    gaps: list[Gap]
    limitations: list[str]


class Verification(BaseModel):
    interfaces_claimed: int = 0
    interfaces_verified: int = 0
    raises_unconfirmed: int = 0
    dropped: list[str] = Field(default_factory=list, description="Claims removed because the code contradicts them")
    notes: list[str] = Field(default_factory=list)


class RepoReport(BaseModel):
    repo_map: RepoMap
    cards: list[ModuleCard]
    upstream: Upstream | None
    verification: Verification


# ----------------------------------------------------------------------------------------
# URL validation and cloning (application-owned)
# ----------------------------------------------------------------------------------------

_GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")


class ExploreError(Exception):
    """A clear, user-facing failure (bad URL, clone failure, missing run)."""


def normalize_github_url(url: str) -> tuple[str, str, str]:
    """Validate a public GitHub URL. Returns (clone_url, owner, repo)."""
    m = _GITHUB_URL.match(url.strip())
    if not m or m.group(2) in {".", ".."}:
        raise ExploreError(f"not a GitHub repository URL (expected https://github.com/<owner>/<repo>): {url!r}")
    owner, repo = m.group(1), m.group(2)
    return f"https://github.com/{owner}/{repo}.git", owner, repo


def validate_ref(ref: str | None) -> str | None:
    if ref is None:
        return None
    if not _REF.match(ref) or ".." in ref:
        raise ExploreError(f"invalid git ref: {ref!r}")
    return ref


def _git(args: list[str], cwd: Path, timeout: int) -> str:
    """Run git with an argument list (never a shell string)."""
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ExploreError(f"git {args[0]} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise ExploreError(f"git {args[0]} failed: {proc.stderr.strip()[-500:]}")
    return proc.stdout.strip()


def clone_repo(clone_url: str, ref: str | None, dest: Path, timeout: int = config.CLONE_TIMEOUT_SEC) -> str:
    """Shallow-clone `clone_url` at `ref` (default branch if None) into `dest`. Returns the commit SHA."""
    if (dest / ".git").exists():
        return _git(["rev-parse", "HEAD"], dest, 30)
    dest.mkdir(parents=True, exist_ok=True)
    if ref is None:
        _git(["clone", "--depth", "1", "--", clone_url, "."], dest, timeout)
    else:
        # Works for branches, tags and full SHAs.
        _git(["init", "-q"], dest, 30)
        _git(["remote", "add", "origin", clone_url], dest, 30)
        _git(["fetch", "--depth", "1", "origin", ref], dest, timeout)
        _git(["checkout", "-q", "--detach", "FETCH_HEAD"], dest, 60)
    return _git(["rev-parse", "HEAD"], dest, 30)


def _make_clone_tool(clone_url: str, ref: str | None, workspace: Path, state: dict[str, Any]):
    @tool("clone_repository", "Clone the repository for this run into ./repo and return its commit SHA.", {})
    async def clone_repository(args: dict[str, Any]) -> dict[str, Any]:
        try:
            sha = await asyncio.to_thread(clone_repo, clone_url, ref, workspace / "repo")
        except ExploreError as exc:
            state["clone_error"] = str(exc)
            return {"content": [{"type": "text", "text": f"Clone failed: {exc}"}], "is_error": True}
        state["commit_sha"] = sha
        return {"content": [{"type": "text", "text": f"Cloned {clone_url} into ./repo at commit {sha}."}]}

    return clone_repository


# ----------------------------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a repository exploration agent. You produce accurate, evidence-backed facts about one GitHub "
    "repository. Your output is the source of truth that other engineers use to design realistic new "
    "features for it, so describe what the code actually does, never what it probably does.\n\n" + BASE_RULES
)


def _map_prompt(clone_url: str, ref: str | None) -> str:
    at = f" at ref `{ref}`" if ref else " at its default branch"
    return (
        f"First call the clone_repository tool, then map the repository {clone_url}{at}.\n\n"
        "Build a compact map (README, build and dependency manifests, top-level directories, test layout), "
        "then read enough of each important module to describe its role. Skip vendored dependencies, generated "
        "files and binaries.\n\n"
        "Report: purpose and intended users; languages, frameworks, dependencies; entry points; key modules "
        "ordered by relevance for adding new features; the execution flow; the test runner, which test files "
        "cover which source files, and the conventions the tests follow; the compatibility rules a new feature "
        "must respect (what is public API, deprecation practice, supported versions, warning policy, typing), "
        "each with evidence; setup and test commands with their source file (they are DISCOVERED, so "
        "verified=false); evidence; open questions and limitations. Do not use the web in this pass."
    )


def _card_prompt(module: Module, repo_map: RepoMap) -> str:
    tests = [t.path for t in repo_map.test_layout if module.path in t.covers]
    return (
        f"Deep-dive one module of the repository in ./repo: `{module.path}`.\n"
        f"Its role: {module.role}\n"
        f"Test files believed to cover it: {', '.join(tests) or '(find them)'}\n"
        f"Test conventions in this repo: {' | '.join(repo_map.test_conventions)}\n\n"
        "Read the whole module, then the tests and docs that exercise it. Report:\n"
        "- interfaces: up to 25 public interfaces most relevant for building features. Use the exact qualified "
        "name as defined in this file. For each: real behavior including defaults and ordering, how it handles "
        "edge cases, and the exception classes it raises directly. Signatures and line numbers are extracted "
        "from the source by a parser afterwards, and names that do not exist in the file are discarded, so be exact.\n"
        "- error_conventions: which exception types are used for what, and the message style.\n"
        "- examples: 2-5 short usage snippets copied from the repo's docs or tests, with their source lines.\n"
        "- tests: the test files covering this module and how they assert.\n"
        "- extension_points: concrete places where new behavior could plug in (hooks, callbacks, subclass "
        "points, registries, dispatch tables), with file and line.\n"
        "- gaps: capabilities this module notably lacks that would be a natural, realistically-scoped extension "
        "(not rewrites, not things another well-known library already does as a drop-in).\n"
        "Do not use the web in this pass."
    )


def _upstream_prompt(clone_url: str, owner: str, repo: str, ref: str | None, sha: str) -> str:
    return (
        f"The repository in ./repo is {clone_url} pinned at commit {sha} (ref: {ref or 'default branch'}).\n"
        "We will design NEW features on top of this commit. They must be novel against live upstream, including "
        "changes merged after the pinned commit. Find out what already exists or is in motion.\n\n"
        "1. Find the changelog in ./repo with Glob (for example CHANGES.*, CHANGELOG.*, docs/changes.*) and read "
        "it to learn the pinned version, its release date and what it already contains.\n"
        f"2. On the web, read the same changelog file on the default branch "
        f"(https://raw.githubusercontent.com/{owner}/{repo}/HEAD/<path>), the releases page "
        f"(https://github.com/{owner}/{repo}/releases), recently merged pull requests and open feature requests "
        f"(https://github.com/{owner}/{repo}/pulls, https://github.com/{owner}/{repo}/issues).\n"
        "3. Report: the pinned and latest versions; features and behavior changes after the pin; open or planned "
        "feature work; and a `do_not_propose` list of capabilities that already exist upstream or are in progress.\n"
        "Use 6 to 12 web calls. Record the URL of every item. If the web is unavailable, say so in limitations."
    )


# ----------------------------------------------------------------------------------------
# Verification of cards against the code
# ----------------------------------------------------------------------------------------


def verify_card(path: str, claim: CardClaim, repo: Path, ver: Verification) -> ModuleCard:
    index = verify.index_python(repo / path) if verify.is_python(path) else {}
    if not verify.is_python(path):
        ver.notes.append(f"{path}: not Python, interfaces kept unverified")
    interfaces: list[Interface] = []
    for c in claim.interfaces:
        ver.interfaces_claimed += 1
        if not verify.is_python(path):
            interfaces.append(Interface(**c.model_dump()))
            continue
        sym = verify.resolve(index, c.name)
        if sym is None:
            ver.dropped.append(f"{path}: interface `{c.name}` does not exist in the file")
            continue
        raises, unconfirmed = [], []
        for exc in c.raises:
            short = exc.strip().strip("`").split(".")[-1].split("(")[0].strip()
            (raises if short and short in sym.source else unconfirmed).append(short or exc)
        ver.raises_unconfirmed += len(unconfirmed)
        ver.interfaces_verified += 1
        interfaces.append(Interface(name=sym.qualname, behavior=c.behavior, edge_cases=c.edge_cases, raises=raises,
                                    kind=sym.kind, signature=sym.signature, line_start=sym.line_start,
                                    line_end=sym.line_end, verified=True, raises_unconfirmed=unconfirmed))

    def in_file(rel: str, *lines: int) -> bool:
        n = verify.file_lines(repo, rel)
        return n is not None and all(1 <= ln <= n for ln in lines)

    examples = [e for e in claim.examples if in_file(e.source_path, e.line_start, e.line_end)]
    tests = [t for t in claim.tests if in_file(t.path)]
    points = [p for p in claim.extension_points if in_file(p.path, p.line)]
    for kind, before, after in (("example", claim.examples, examples), ("test note", claim.tests, tests),
                                ("extension point", claim.extension_points, points)):
        if len(after) < len(before):
            ver.dropped.append(f"{path}: {len(before) - len(after)} {kind}(s) cite a file or line that does not exist")
    gaps = []
    for g in claim.gaps:
        if index and verify.resolve(index, g.nearest_existing) is None:
            ver.notes.append(f"{path}: gap '{verify.clip_line(g.description, 80)}' names a nearest interface "
                             f"`{g.nearest_existing}` that is not in this file")
        gaps.append(g)
    return ModuleCard(path=path, summary=claim.summary, interfaces=interfaces,
                      error_conventions=claim.error_conventions, examples=examples, tests=tests,
                      extension_points=points, gaps=gaps, limitations=claim.limitations)


# ----------------------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------------------


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "- (none)"


def render_markdown(meta: dict[str, Any], r: RepoReport) -> str:
    m = r.repo_map
    out = [
        f"# Repository report: {meta['owner']}/{meta['repo']}", "",
        f"- URL: {meta['clone_url']}",
        f"- Requested ref: {meta['ref'] or '(default branch)'}",
        f"- Commit: `{meta['commit_sha']}`",
        f"- Run: `{meta['run_id']}` · model `{config.EXPLORE_MODEL}`",
        f"- Verification: {r.verification.interfaces_verified} of {r.verification.interfaces_claimed} claimed "
        f"interfaces confirmed in the source; {len(r.verification.dropped)} claims dropped",
        "",
        "## Purpose", m.purpose, "",
        "## Intended users", m.intended_users, "",
        "## Languages, frameworks, dependencies",
        _bullets([f"Languages: {', '.join(m.languages)}", f"Frameworks: {', '.join(m.frameworks) or '(none)'}",
                  f"Dependencies: {', '.join(m.dependencies) or '(none)'}"]), "",
        "## Entry points", _bullets([f"`{e.path}:{e.line}`: {e.description}" for e in m.entry_points]), "",
        "## Key modules (most feature-relevant first)",
        _bullets([f"`{k.path}`: {k.role} *Feature relevance:* {k.feature_relevance}" for k in m.key_modules]), "",
        "## Execution flow", m.execution_flow, "",
        f"## Tests (runner: {m.test_runner})",
        _bullets([f"`{t.path}` covers {', '.join(f'`{c}`' for c in t.covers) or '(unspecified)'}" for t in m.test_layout]), "",
        "### Test conventions", _bullets(m.test_conventions), "",
        "## Compatibility rules",
        _bullets([f"{e.claim} (`{e.path}:{e.line_start}-{e.line_end}`)" for e in m.compatibility_rules]), "",
        "## Setup and test commands",
        _bullets([f"`{c.command}`: {c.purpose} (source: {c.source}; "
                  f"{'verified by execution' if c.verified else 'discovered, not executed'})"
                  for c in m.setup_and_test_commands]), "",
        "## Evidence", _bullets([f"{e.claim} (`{e.path}:{e.line_start}-{e.line_end}`)" for e in m.evidence]), "",
    ]
    for c in r.cards:
        out += [f"## Module card: `{c.path}`", c.summary, "", "### Interfaces"]
        for i in c.interfaces:
            loc = f"`{c.path}:{i.line_start}-{i.line_end}`" if i.verified else "unverified"
            out += [f"- **`{i.name}`** ({loc})", f"  - Signature: `{i.signature}`" if i.signature else "  - Signature: unverified",
                    f"  - Behavior: {i.behavior}"]
            out += [f"  - Edge case: {e}" for e in i.edge_cases]
            if i.raises:
                out.append(f"  - Raises: {', '.join(f'`{x}`' for x in i.raises)}")
            if i.raises_unconfirmed:
                out.append(f"  - Raises (unconfirmed, likely via a helper): {', '.join(f'`{x}`' for x in i.raises_unconfirmed)}")
        out += ["", "### Error conventions", c.error_conventions, "", "### Examples"]
        for e in c.examples:
            out += [f"{e.description} (`{e.source_path}:{e.line_start}-{e.line_end}`)", "```", e.code, "```"]
        out += ["", "### Tests", _bullets([f"`{t.path}`: {t.how_it_asserts}" for t in c.tests]), "",
                "### Extension points",
                _bullets([f"**{p.name}** (`{p.path}:{p.line}`): {p.what_could_attach}" for p in c.extension_points]), "",
                "### Gaps (model's judgment, not verifiable from code)",
                _bullets([f"{g.description} Why plausible: {g.why_plausible} Nearest: `{g.nearest_existing}`" for g in c.gaps]), ""]
    if r.upstream:
        u = r.upstream
        out += [f"## Upstream (pinned {u.pinned_version}, latest {u.latest_version})", "",
                "### Changes after the pinned commit",
                _bullets([f"[{i.title}]({i.url}): {i.summary}" for i in u.changes_after_pin]), "",
                "### Open or planned", _bullets([f"[{i.title}]({i.url}): {i.summary}" for i in u.open_or_planned]), "",
                "### Do not propose", _bullets(u.do_not_propose), "",
                "### Upstream limitations", _bullets(u.limitations), ""]
    else:
        out += ["## Upstream", "The upstream check did not complete. Novelty is NOT verified.", ""]
    out += ["## Verification", "### Dropped claims", _bullets(r.verification.dropped), "",
            "### Notes", _bullets(r.verification.notes), "",
            "## Open questions", _bullets(m.open_questions), "",
            "## Limitations", _bullets(m.limitations + [f"`{c.path}`: {x}" for c in r.cards for x in c.limitations]), ""]
    return "\n".join(out)


# ----------------------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------------------


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def load_run(run_id: str) -> tuple[Path, dict[str, Any]]:
    workspace = config.RUNS_DIR / run_id
    if not (workspace / "run.json").is_file():
        raise ExploreError(f"no such run: {run_id}")
    return workspace, json.loads((workspace / "run.json").read_text(encoding="utf-8"))


def record_stage(meta: dict[str, Any], workspace: Path, res: StageResult) -> None:
    """Store a stage's status and usage in run.json and refresh the running total.

    A re-run of a stage keeps the earlier entry under a numbered name, so no spend is lost from the total."""
    stages = meta.setdefault("stages", {})
    if res.stage in stages:
        k = 1
        while f"{res.stage} (earlier #{k})" in stages:
            k += 1
        stages[f"{res.stage} (earlier #{k})"] = stages.pop(res.stage)
    stages[res.stage] = res.summary()
    meta["total_cost_usd"] = round(sum(s.get("total_cost_usd", 0.0) for s in meta["stages"].values()), 6)
    write_json(workspace / "run.json", meta)
    print(f"  [{res.stage}] {res.status}: {res.usage.get('num_turns')} turns, ${res.usage.get('total_cost_usd')}"
          + (f" ({res.error})" if res.error else ""), file=sys.stderr)


async def explore(url: str, ref: str | None = None) -> Path:
    """Explore `url` at `ref`. Returns the run directory. Raises ExploreError on bad input."""
    clone_url, owner, repo_name = normalize_github_url(url)
    ref = validate_ref(ref)
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{owner}-{repo_name}".lower()
    workspace = config.RUNS_DIR / run_id
    workspace.mkdir(parents=True)
    repo = workspace / "repo"
    meta: dict[str, Any] = {
        "run_id": run_id, "clone_url": clone_url, "owner": owner, "repo": repo_name, "ref": ref,
        "commit_sha": None, "status": "running", "model": config.EXPLORE_MODEL,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stages": {}, "total_cost_usd": 0.0,
    }
    write_json(workspace / "run.json", meta)
    log = EventLog(workspace / "events.jsonl")
    started = time.monotonic()
    print(f"run {run_id}: exploring {clone_url} (model {config.EXPLORE_MODEL})", file=sys.stderr)

    # --- pass 1: map ---------------------------------------------------------------------
    state: dict[str, Any] = {}
    clone_tool = _make_clone_tool(clone_url, ref, workspace, state)
    map_res = await run_stage(
        "map", workspace, _map_prompt(clone_url, ref), SYSTEM_PROMPT, log, model=config.EXPLORE_MODEL,
        max_budget_usd=config.MAP_MAX_BUDGET_USD, schema=RepoMap,
        mcp_servers={"repo": create_sdk_mcp_server(name="repo", version="1.0.0", tools=[clone_tool])},
    )
    meta["commit_sha"] = state.get("commit_sha")
    record_stage(meta, workspace, map_res)
    if map_res.status != "ok":
        meta["status"] = "clone_failed" if state.get("clone_error") and not meta["commit_sha"] else "map_failed"
        meta["error"] = state.get("clone_error") or map_res.error
        write_json(workspace / "run.json", meta)
        return workspace
    repo_map: RepoMap = map_res.data
    write_json(workspace / "map.json", repo_map.model_dump())

    # --- pass 2: one deep dive per key module, plus the upstream check, concurrently -----
    modules = [m for m in repo_map.key_modules if verify.file_lines(repo, m.path) is not None]
    skipped = [m.path for m in repo_map.key_modules if m not in modules] + [m.path for m in modules[config.DEEP_DIVE_MAX_MODULES:]]
    modules = modules[: config.DEEP_DIVE_MAX_MODULES]
    sem = asyncio.Semaphore(config.AGENT_CONCURRENCY)

    async def limited(coro):
        async with sem:
            return await coro

    card_jobs = [
        limited(run_stage(f"card:{m.path}", workspace, _card_prompt(m, repo_map), SYSTEM_PROMPT, log,
                          model=config.EXPLORE_MODEL, max_budget_usd=config.CARD_MAX_BUDGET_USD, schema=CardClaim))
        for m in modules
    ]
    upstream_job = limited(run_stage(
        "upstream", workspace, _upstream_prompt(clone_url, owner, repo_name, ref, meta["commit_sha"]), SYSTEM_PROMPT,
        log, model=config.EXPLORE_MODEL, max_budget_usd=config.UPSTREAM_MAX_BUDGET_USD, schema=Upstream))
    *card_results, upstream_res = await asyncio.gather(*card_jobs, upstream_job)

    # --- save raw agent output, then verify and merge ------------------------------------
    (workspace / "claims").mkdir(exist_ok=True)
    failures: list[str] = []
    if skipped:
        failures.append(f"modules without a deep dive: {', '.join(skipped)}")
    for m, res in zip(modules, card_results):
        record_stage(meta, workspace, res)
        if res.status == "ok":
            write_json(workspace / "claims" / (m.path.replace("/", "__") + ".json"),
                       {"path": m.path, "claim": res.data.model_dump()})
        else:
            failures.append(f"{m.path}: deep dive failed ({res.status}: {res.error})")
    record_stage(meta, workspace, upstream_res)
    if upstream_res.status == "ok":
        write_json(workspace / "upstream.json", upstream_res.data.model_dump())
    else:
        failures.append(f"upstream check failed ({upstream_res.status}: {upstream_res.error}); novelty is not verified")
    meta["stage_failures"] = failures
    meta["wall_seconds"] = round(time.monotonic() - started, 1)
    meta["tool_calls"] = log.tool_calls
    build_report(workspace, meta)
    return workspace


def build_report(workspace: Path, meta: dict[str, Any]) -> RepoReport:
    """Verify the saved agent output against the clone and write report.json / report.md.

    Pure application code (no model calls), so it can be re-run at any time.
    """
    repo = workspace / "repo"
    repo_map = RepoMap.model_validate_json((workspace / "map.json").read_text(encoding="utf-8"))
    ver = Verification(notes=list(meta.get("stage_failures", [])))
    order = {m.path: i for i, m in enumerate(repo_map.key_modules)}
    cards: list[ModuleCard] = []
    for f in sorted((workspace / "claims").glob("*.json")):
        # macOS creates binary AppleDouble sidecars on external filesystems.
        # They match *.json but are not agent output.
        if f.name.startswith("._") or not f.is_file():
            continue
        raw = json.loads(f.read_text(encoding="utf-8"))
        cards.append(verify_card(raw["path"], CardClaim.model_validate(raw["claim"]), repo, ver))
    cards.sort(key=lambda c: order.get(c.path, 999))
    up = workspace / "upstream.json"
    upstream = Upstream.model_validate_json(up.read_text(encoding="utf-8")) if up.is_file() else None
    report = RepoReport(repo_map=repo_map, cards=cards, upstream=upstream, verification=ver)
    meta["status"] = "ok" if cards else "no_cards"
    write_json(workspace / "report.json", report.model_dump())
    (workspace / "report.md").write_text(render_markdown(meta, report), encoding="utf-8")
    write_json(workspace / "run.json", meta)
    return report


async def ask(run_id: str, question: str) -> str:
    """Answer a follow-up question in the map session and workspace of run `run_id`."""
    workspace, meta = load_run(run_id)
    session = meta.get("stages", {}).get("map", {}).get("session_id")
    if not session:
        raise ExploreError(f"run {run_id} has no session to resume (status: {meta.get('status')})")
    log = EventLog(workspace / "events.jsonl")
    log.write("question", text=question)
    prompt = (f"{question}\n\nAnswer for commit {meta['commit_sha']} of the repository in ./repo. "
              "Cite file paths and line numbers.")
    res = await run_stage(f"ask:{datetime.now().strftime('%H%M%S')}", workspace, prompt, SYSTEM_PROMPT, log,
                          model=config.EXPLORE_MODEL, max_budget_usd=config.CARD_MAX_BUDGET_USD, resume=session)
    record_stage(meta, workspace, res)
    answer = res.text or f"(no answer: {res.status} {res.error or ''})"
    with (workspace / "qa.md").open("a", encoding="utf-8") as fh:
        fh.write(f"## Q: {question}\n\n{answer}\n\n")
    return answer
