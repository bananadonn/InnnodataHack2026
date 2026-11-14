"""Stage 1a: mine real, unmet user demand for an explored repository.

Two read-only agent sessions with web access run in parallel:

    demand:project     the project's own issues and discussions: feature requests never implemented
    demand:community   Stack Overflow, blog posts, add-on libraries: workarounds for missing features

Every request must cite a page the agent really opened (checked against events.jsonl), and the
agent must check the clone to confirm the capability is still missing at the pinned commit.

Output, under runs/<run_id>/: demand.json, demand.md. Feature proposal (pipeline/propose.py)
designs candidates from these requests.
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
from pipeline.explore import load_run, record_stage, write_json


class DemandItem(BaseModel):
    title: str
    url: str = Field(description="The page you opened that shows the request or workaround")
    source: Literal["issue", "pull_request", "discussion", "stackoverflow", "blog", "addon", "other"]
    need: str = Field(description="What the users want to do, in their terms, and why the current library does not let them")
    status: str = Field(description="open / closed-not-planned / closed-stale / closed-other / n/a, as shown on the page")
    maintainer_position: Literal["none", "receptive", "declined", "unclear"]
    maintainer_reason: str = Field(description="If maintainers commented: what they said, briefly. Empty otherwise")
    demand_signal: str = Field(description="Visible signals of demand: reactions, duplicate issues, votes, linked projects")
    workaround: str = Field(description="How users currently work around it, if shown")
    click_area: str = Field(description="Repo-relative source file(s) where this would live")
    still_missing: bool = Field(description="True if you confirmed in ./repo that the capability is still missing at the pinned commit")
    missing_check: str = Field(description="What you looked at in ./repo to decide still_missing")


class DemandList(BaseModel):
    requests: list[DemandItem]
    limitations: list[str]


SYSTEM = (
    "You are researching what real users of an open-source library want but cannot do. You report only what "
    "pages you actually opened show, and you never invent requests, numbers or quotes.\n\n" + BASE_RULES
)


def _project_prompt(meta: dict[str, Any], n: int) -> str:
    owner, repo = meta["owner"], meta["repo"]
    return f"""Find at least {n} distinct, real feature requests for {owner}/{repo} that are NOT implemented at the pinned
commit {meta['commit_sha']} (the clone is in ./repo).

Where to look, with the web tools:
- Issues, open and closed: https://github.com/{owner}/{repo}/issues?q=is%3Aissue+<keywords> (try many keywords,
  such as option, argument, help, prompt, completion, envvar, default, validation, group, context, type,
  testing, output, error message), and sort by most reactions or comments where the page allows it.
- Closed-as-not-planned and stale issues are especially useful, since they were never implemented.
- Discussions: https://github.com/{owner}/{repo}/discussions (ideas, Q&A).
Prefer requests with visible demand (reactions, duplicates, several users). Record what maintainers said: a
request maintainers declined because it does not fit the library is still worth recording, with the reason.

For each request, check ./repo (Grep/Read) to confirm the capability is still missing at the pinned commit, and
say what you checked. Skip anything already implemented. Do not include bug reports, documentation requests or
build/packaging issues; only missing capabilities.
Copy each URL exactly as you opened it: URLs are cross-checked against the log of your real web calls.
"""


def _community_prompt(meta: dict[str, Any], n: int) -> str:
    owner, repo = meta["owner"], meta["repo"]
    return f"""Find at least {n} distinct, real needs that users of {owner}/{repo} have but the library does not meet at the
pinned commit {meta['commit_sha']} (the clone is in ./repo). Do not use the project's own issue tracker; another
researcher covers that.

Where to look, with the web tools:
- Stack Overflow questions tagged or titled with {repo} (python-click) where the accepted answer is a workaround:
  a subclass, a callback, monkeypatching, or "this is not possible".
- Blog posts, recipes and gists that work around a missing capability.
- Add-on libraries for {repo} (cloup, click-option-group, click-extra, click-params, click-default-group,
  click-aliases, click-help-colors, rich-click, typer): features they add, and their issue trackers for needs
  that originate in {repo} itself.
Prefer needs with visible demand (votes, many answers, several independent sources).

For each need, check ./repo (Grep/Read) to confirm the capability is still missing at the pinned commit, and say
what you checked. Skip anything already implemented. If an add-on already provides it fully, record it with
source=addon so the designer knows it would be a drop-in.
Copy each URL exactly as you opened it: URLs are cross-checked against the log of your real web calls.
"""


def make_validator(events_path: Path, stage: str, minimum: int):
    from pipeline.audit import _web_calls  # shared log reader

    def validate(d: DemandList) -> list[str]:
        sent, returned = _web_calls(events_path, stage)
        errs: list[str] = []
        urls = [r.url.strip() for r in d.requests]
        if len(set(urls)) != len(urls):
            errs.append("each request must have a distinct URL; merge duplicates")
        for r in d.requests:
            url = r.url.strip()
            if url not in sent and url.split("#")[0].rstrip("/") not in returned:
                errs.append(f"URL was neither fetched nor returned by a search (copy it exactly as opened): {url}")
        usable = [r for r in d.requests if r.still_missing]
        if len(usable) < minimum:
            errs.append(f"need at least {minimum} requests that are still missing at the pinned commit, got {len(usable)}")
        return errs

    return validate


def render_markdown(meta: dict[str, Any], items: list[DemandItem], limits: list[str]) -> str:
    out = [f"# User demand: {meta['owner']}/{meta['repo']} @ `{meta['commit_sha'][:12]}`", "",
           f"Mined by `{config.DEMAND_MODEL}` with web access. Every URL was checked against the agent's real web calls.", "",
           "| Request | Source | Status | Maintainers | Still missing | Area |", "|---|---|---|---|---|---|"]
    for r in items:
        out.append(f"| [{r.title}]({r.url}) | {r.source} | {r.status} | {r.maintainer_position} | "
                   f"{'yes' if r.still_missing else 'no'} | {r.click_area} |")
    for r in items:
        out += ["", f"## {r.title}", "", f"- URL: {r.url}", f"- Need: {r.need}", f"- Demand signal: {r.demand_signal}",
                f"- Workaround: {r.workaround or '(none shown)'}",
                f"- Maintainers: {r.maintainer_position}" + (f": {r.maintainer_reason}" if r.maintainer_reason else ""),
                f"- Still missing at the pin: {'yes' if r.still_missing else 'no'} ({r.missing_check})"]
    out += ["", "## Limitations", *[f"- {x}" for x in limits], ""]
    return "\n".join(out)


async def mine(run_id: str) -> Path:
    """Mine user demand for exploration run `run_id`. Returns the run directory."""
    workspace, meta = load_run(run_id)
    events = workspace / "events.jsonl"
    log = EventLog(events)
    n = config.DEMAND_PER_SESSION
    print(f"run {run_id}: mining user demand (model {config.DEMAND_MODEL})", file=sys.stderr)
    jobs = [
        run_stage(stage, workspace, prompt(meta, n), SYSTEM, log, model=config.DEMAND_MODEL,
                  max_budget_usd=config.DEMAND_MAX_BUDGET_USD, max_turns=150, schema=DemandList,
                  validator=make_validator(events, stage, n))
        for stage, prompt in (("demand:project", _project_prompt), ("demand:community", _community_prompt))
    ]
    items: list[DemandItem] = []
    limits: list[str] = []
    for res in await asyncio.gather(*jobs):
        record_stage(meta, workspace, res)
        if res.status == "ok":
            seen = {i.url.strip() for i in items}
            items += [r for r in res.data.requests if r.url.strip() not in seen]
            limits += [f"{res.stage}: {x}" for x in res.data.limitations]
        else:
            limits.append(f"{res.stage} failed ({res.status}): {res.error}")
    write_json(workspace / "demand.json", {"requests": [i.model_dump() for i in items], "limitations": limits})
    (workspace / "demand.md").write_text(render_markdown(meta, items, limits), encoding="utf-8")
    return workspace
