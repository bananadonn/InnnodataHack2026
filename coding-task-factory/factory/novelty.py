"""Novelty gate: the feature must not already exist upstream (main, merged PRs incl. after base_commit, open PRs),
and must not be a drop-in from a well-known library. Evidence = GitHub search hits + current source, judged by LLM.
Set GITHUB_TOKEN to lift the unauthenticated search rate limit (10 req/min)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

from .llm import chat, extract_json

STOP = {"the", "and", "with", "that", "this", "from", "when", "into", "each", "support", "option", "options",
        "command", "commands", "click", "value", "values", "new", "add", "allow"}


def github_search(repo: str, terms: list[str], limit: int = 8) -> list[dict]:
    q = f"repo:{repo} " + " ".join(terms)
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": q, "per_page": limit})
    headers = {"accept": "application/vnd.github+json", "user-agent": "coding-task-factory"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            items = json.loads(r.read()).get("items", [])
    except Exception as e:  # noqa: BLE001 — novelty evidence is best-effort; the LLM judge is told it is missing
        return [{"error": str(e)}]
    finally:
        time.sleep(1.0)
    return [{"title": i["title"], "url": i["html_url"], "state": i["state"],
             "is_pr": "pull_request" in i, "merged": bool((i.get("pull_request") or {}).get("merged_at"))}
            for i in items]


def keywords(spec: dict) -> list[list[str]]:
    words = [w for w in re.findall(r"[A-Za-z_]{4,}", spec["title"]) if w.lower() not in STOP]
    iface = [i["symbol"].split(".")[-1] for i in spec.get("interface", []) if i.get("symbol")]
    queries = [words[:3]] + [[s] for s in iface[:2]]
    return [q for q in queries if q]


def check(spec: dict, repo_name: str, source: str, model: str) -> dict:
    hits = []
    for q in keywords(spec):
        hits += github_search(repo_name, q)
    prompt = f"""Decide whether this proposed feature task is NOVEL for {repo_name}.

Proposed task:
{json.dumps({k: spec.get(k) for k in ("title", "problem_statement", "requirements", "interface")}, indent=1)}

GitHub issues/PRs matching keywords (merged PRs mean the feature may already be upstream, including after our
base commit; open PRs / issues mean someone is working on it — both make the task NOT novel if they implement
substantially the same behavior):
{json.dumps(hits, indent=1)[:6000]}

Relevant current source (does it already implement this?):
{source[:40000]}

Not novel if: the behavior already exists (even under another name), a merged or open PR implements it, or it
is a drop-in copy of a well-known library feature. Answer ```json {{"novel": bool, "reason": str,
"closest_upstream": str}} ```"""
    verdict = extract_json(chat(prompt, model=model, temperature=0, role="novelty"))
    verdict["github_hits"] = hits
    return verdict
