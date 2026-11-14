"""Independent reference coding agent using OpenRouter's tool-calling API.

Only read-only tools for the pinned clone are exposed. The final submit tool
returns structured source changes, which the application validates and applies.
"""
from __future__ import annotations

import asyncio
import fnmatch
import json
import re
import time
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from pipeline import config
from pipeline.coding_common import (
    CodingJob, ImplementationDraft, _git, prepare_job, save_draft, validate_draft, write_status,
)
from pipeline.explore import ExploreError, write_json


def _function(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": required, "additionalProperties": False}}}


def tool_definitions() -> list[dict]:
    return [
        _function("list_files", "List pinned repository files matching a glob pattern (max 500).",
                  {"pattern": {"type": "string"}}, ["pattern"]),
        _function("read_file", "Read lines from a pinned repository file (at most 400 lines).",
                  {"path": {"type": "string"}, "start_line": {"type": "integer"},
                   "end_line": {"type": "integer"}}, ["path", "start_line", "end_line"]),
        {"type": "function", "function": {"name": "submit_implementation",
         "description": "Submit the complete candidate implementation, or blockers if incompatible.",
         "parameters": ImplementationDraft.model_json_schema()}},
    ]


def read_tool(job: CodingJob, name: str, arguments: dict[str, Any]) -> dict:
    """Never read sibling attempts, hidden tests, host files, Git internals or symlinks."""
    tracked = set(_git("-C", str(job.repo), "ls-tree", "-r", "--name-only", job.commit_sha).splitlines())
    public = {p for p in tracked if not any(part.startswith(".") for part in PurePosixPath(p).parts)}
    if name == "list_files":
        pattern = arguments.get("pattern")
        if not isinstance(pattern, str) or len(pattern) > 500:
            raise ValueError("provide a glob pattern under 500 characters")
        matches = sorted(p for p in public if fnmatch.fnmatchcase(p, pattern))
        return {"files": matches[:500], "truncated": len(matches) > 500}
    if name == "read_file":
        path = arguments.get("path")
        if not isinstance(path, str) or path not in public:
            raise ValueError("read_file requires a visible tracked repository path")
        target = job.repo / path
        if target.is_symlink() or not target.resolve().is_relative_to(job.repo.resolve()):
            raise ValueError("file is outside the pinned repository")
        start, end = arguments.get("start_line"), arguments.get("end_line")
        if (type(start) is not int or type(end) is not int or start < 1 or end < start
                or end - start >= 400):
            raise ValueError("request a range of 1 to 400 lines using one-based indices")
        if target.stat().st_size > 2_000_000:
            raise ValueError("file exceeds the 2 MB inspection limit")
        lines = target.read_text(encoding="utf-8").splitlines()
        snippet = "\n".join(f"{i}: {line}" for i, line in enumerate(lines[start - 1:end], start))
        if len(snippet) > 80000:
            raise ValueError("requested content too large; read fewer lines")
        return {"path": path, "total_lines": len(lines), "content": snippet}
    raise ValueError(f"unsupported tool: {name}")


def provider_error(response: httpx.Response, api_key: str) -> dict:
    """Keep actionable error fields, without headers or arbitrary provider metadata."""
    detail = {"http_status": response.status_code}
    try:
        error = response.json().get("error", {})
    except (ValueError, AttributeError):
        error = {}
    if isinstance(error, dict):
        if isinstance(error.get("code"), int):
            detail["code"] = error["code"]
        if isinstance(error.get("message"), str):
            message = error["message"]
            if api_key:
                message = message.replace(api_key, "[REDACTED]")
            message = re.sub(r"(?i)bearer\s+[^\s\"']+", "Bearer [REDACTED]", message)
            message = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", message)
            detail["message"] = message[:2000]
    return detail


async def run_reference_session(job: CodingJob, client: httpx.AsyncClient, api_key: str) -> ImplementationDraft:
    """Bounded tool loop. No fallback model, hidden-test access or repository execution."""
    messages: list[dict] = [{"role": "system", "content": job.system_prompt},
                            {"role": "user", "content": job.prompt +
                             "\nUse list_files/read_file to inspect source and existing tests. "
                             "Finish by calling submit_implementation."}]
    usage_rows = []
    reported_cost = 0.0
    for number in range(1, config.REFERENCE_MAX_CALLS + 1):
        # Opus endpoints do not advertise parallel_tool_calls; requesting it
        # with require_parameters=True would exclude all of them. Tool batches
        # are bounded and handled serially below.
        payload = {"model": job.model, "messages": messages, "tools": tool_definitions(),
                   "tool_choice": "required",
                   "max_tokens": config.REFERENCE_MAX_OUTPUT_TOKENS,
                   "provider": {"require_parameters": True, "allow_fallbacks": False}}
        write_json(job.workspace / f"request_{number}.json", payload)
        response = await client.post(config.OPENROUTER_BASE_URL + "/chat/completions", json=payload,
                                     headers={"Authorization": f"Bearer {api_key}"})
        if response.status_code >= 400:
            detail = provider_error(response, api_key)
            write_json(job.workspace / f"error_{number}.json", detail)
            message = detail.get("message", "no provider error message returned")
            raise ExploreError(f"OpenRouter request failed with HTTP {response.status_code}: {message}")
        data = response.json()
        write_json(job.workspace / f"response_{number}.json", data)
        usage = data.get("usage")
        usage_rows.append({"response_id": data.get("id"), "model": data.get("model"), "usage": usage})
        cost = usage.get("cost") if isinstance(usage, dict) else None
        known_cost = isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0
        if known_cost:
            reported_cost += cost
        write_json(job.workspace / "usage.json", {"model_calls": number, "responses": usage_rows,
                   "reported_cost_usd": reported_cost,
                   "cost_complete": all(isinstance(r["usage"], dict)
                                        and isinstance(r["usage"].get("cost"), (int, float)) for r in usage_rows)})
        choices = data.get("choices") or []
        if not choices or data.get("error"):
            raise ExploreError("OpenRouter returned no usable completion")
        choice = choices[0]
        if choice.get("finish_reason") != "tool_calls":
            raise ExploreError("OpenRouter completion was truncated, refused or did not call a tool")
        message = choice.get("message", {})
        calls = message.get("tool_calls") or []
        if not calls or len(calls) > 8:
            raise ExploreError("OpenRouter returned an invalid tool-call batch")
        # Preserve provider reasoning fields required by some models on subsequent turns.
        messages.append(message)
        submitted = None
        for call in calls:
            try:
                function = call["function"]
                args = json.loads(function["arguments"])
                if not isinstance(args, dict):
                    raise ValueError("tool arguments must be an object")
                if function["name"] == "submit_implementation":
                    candidate = ImplementationDraft.model_validate(args)
                    errors = validate_draft(job, candidate)
                    if errors:
                        raise ValueError("; ".join(errors))
                    if len(calls) != 1:
                        raise ValueError("submit_implementation must be the only call in its batch")
                    submitted = candidate
                    result = {"status": "received", "validation": "pending"}
                else:
                    result = read_tool(job, function["name"], args)
            except (ValueError, KeyError, OSError) as exc:
                result = {"error": str(exc)}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
        if submitted is not None:
            return submitted
        if not known_cost:
            raise ExploreError("OpenRouter did not report cost; stopping before another paid request")
        if reported_cost >= config.REFERENCE_MAX_BUDGET_USD:
            raise ExploreError("OpenRouter reported-cost limit reached before submission")
    raise ExploreError("OpenRouter tool-call limit reached before submission")


async def create_reference(run_id: str, feature_slug: str, *, execute: bool = False) -> Path:
    """Prepare or author an independent reference candidate; never label it accepted gold yet."""
    job = prepare_job(run_id, feature_slug, "reference", config.OPENROUTER_REFERENCE_MODEL)
    if not execute:
        return job.workspace
    started = time.monotonic()
    try:
        key = config.openrouter_api_key()
        async with asyncio.timeout(config.AGENT_WALL_TIMEOUT_SEC):
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=False) as client:
                draft = await run_reference_session(job, client, key)
        return save_draft(job, draft)
    except (ExploreError, RuntimeError, httpx.HTTPError, TimeoutError, ValueError) as exc:
        # Exception text from HTTP libraries can contain URLs; do not include credentials or request bodies.
        message = str(exc) if isinstance(exc, ExploreError) else f"reference session failed ({type(exc).__name__})"
        write_status(job, "error", error=message, wall_seconds=round(time.monotonic() - started, 2))
        raise ExploreError(message) from exc
