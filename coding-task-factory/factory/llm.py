"""LLM client (stdlib only): provider routing, streaming transport, on-disk cache, and an auditable call log.

Model specs are "provider:model", e.g.
  anthropic:claude-sonnet-5-5            (ANTHROPIC_API_KEY)
  openrouter:openai/gpt-5.1              (OPENROUTER_API_KEY)  — any OpenRouter model id

Responses are STREAMED (server-sent events). A request that sends nothing for CTF_LLM_IDLE_TIMEOUT seconds
(default 90) or runs longer than CTF_LLM_DEADLINE seconds (default 600) is abandoned and retried — a stuck
non-streaming request previously cost 27 minutes of waiting in a single call.

Every model call (including failed ones) is appended to <run_dir>/llm_calls.jsonl with token usage — the audit
trail behind pipeline_run.json (SUBMISSION.md §3b).
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import telemetry

CACHE_DIR = Path(os.environ.get("CTF_CACHE", ".ctf_cache"))
IDLE_TIMEOUT = float(os.environ.get("CTF_LLM_IDLE_TIMEOUT", "90"))
DEADLINE = float(os.environ.get("CTF_LLM_DEADLINE", "600"))
MAX_ATTEMPTS = 5


class LLMError(RuntimeError):
    pass


class TruncatedError(LLMError):
    pass


_NO_TEMPERATURE: set[str] = set()  # models that rejected the temperature parameter this run


def chat(prompt: str, model: str, system: str = "", temperature: float | None = 0.7,
         max_tokens: int = 16000, variant: str = "", role: str = "") -> str:
    provider, _, name = model.partition(":")
    if not name:
        raise ValueError(f"model spec must be provider:model, got {model!r}")
    key = hashlib.sha256(json.dumps([model, system, prompt, temperature, variant]).encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        telemetry.record_call(model=model, role=role, cached=True, usage={}, seconds=0.0, cache_key=key)
        return json.loads(cache_file.read_text())["text"]

    last = None
    for attempt in range(MAX_ATTEMPTS):
        t0 = time.time()
        # newer models reject sampling params; Anthropic models are called without temperature unless
        # CTF_ANTHROPIC_TEMPERATURE=1, and any model that rejects it is remembered and called without it.
        temp = None if (model in _NO_TEMPERATURE or (provider == "anthropic" and
                                                     os.environ.get("CTF_ANTHROPIC_TEMPERATURE") != "1")) else temperature
        try:
            if provider == "anthropic":
                text, usage, stop = _anthropic(prompt, system, name, temp, max_tokens)
                truncated = stop == "max_tokens"
            elif provider == "openrouter":
                text, usage, stop = _openai_compat("https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"],
                                                   prompt, system, name, temp, max_tokens)
                truncated = stop == "length"
            else:
                raise ValueError(f"unknown provider {provider}")
            telemetry.record_call(model=model, role=role, cached=False, usage=usage, seconds=time.time() - t0,
                                  cache_key=key, truncated=truncated)
            if truncated:  # a cut-off answer is useless (half a file) — never cache it
                raise TruncatedError("output truncated (max_tokens)")
            break
        except KeyError as e:
            raise LLMError(f"missing environment variable / field: {e}") from e
        except urllib.error.HTTPError as e:
            last = e
            body = _read_body(e)
            telemetry.record_call(model=model, role=role, cached=False, usage={}, seconds=time.time() - t0,
                                  cache_key=key, error=f"HTTP {e.code}")
            _log(role, attempt, f"HTTP {e.code} {body}")
            if e.code == 400 and "temperature" in body and temp is not None:
                _NO_TEMPERATURE.add(model)
                continue  # retry immediately without temperature
            if 400 <= e.code < 500 and e.code not in (408, 409, 429):
                raise LLMError(f"non-retryable HTTP {e.code} from {model}: {body}") from e
            retry_after = e.headers.get("retry-after") if e.headers else None
            time.sleep(max(_backoff(attempt), float(retry_after) if retry_after and retry_after.isdigit() else 0))
        except TruncatedError as e:
            last = e
            _log(role, attempt, f"{e} → retrying with max_tokens={min(max_tokens * 2, 64000)}")
            max_tokens = min(max_tokens * 2, 64000)
        except (OSError, http.client.HTTPException, LLMError, json.JSONDecodeError) as e:
            # OSError covers socket/idle timeouts, deadline (TimeoutError), resets and URLError
            last = e
            telemetry.record_call(model=model, role=role, cached=False, usage={}, seconds=time.time() - t0,
                                  cache_key=key, error=type(e).__name__ + ": " + str(e)[:200])
            _log(role, attempt, f"{type(e).__name__}: {e} (after {time.time() - t0:.0f}s)")
            time.sleep(_backoff(attempt))
    else:
        raise LLMError(f"LLM call failed after {MAX_ATTEMPTS} attempts: {last}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"model": model, "text": text}))
    return text


def _backoff(attempt: int) -> float:
    return min(5 * 2 ** attempt, 60)


def _log(role, attempt, msg):
    slot = telemetry.current_slot() or "-"
    print(f"  [{slot}] [llm {role}] attempt {attempt + 1} failed: {msg}", flush=True)


def _read_body(e) -> str:
    try:
        return e.read().decode(errors="replace")[:300]
    except Exception:  # noqa: BLE001
        return ""


def _sse(url: str, headers: dict, body: dict):
    """Yield the JSON payloads of a server-sent-event stream.
    Idle detection: the socket timeout applies to every read, so a silent connection raises after IDLE_TIMEOUT.
    Deadline: checked on every received line (servers send keep-alive pings, so this also catches a stall that
    keeps pinging but never produces text)."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "content-type": "application/json", "accept": "text/event-stream", **headers})
    start = time.time()
    with urllib.request.urlopen(req, timeout=IDLE_TIMEOUT) as resp:
        for raw in resp:
            if time.time() - start > DEADLINE:
                raise TimeoutError(f"stream exceeded {DEADLINE:.0f}s deadline")
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue  # event names, comments (": OPENROUTER PROCESSING"), blank separators
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue


def _anthropic(prompt, system, model, temperature, max_tokens):
    body = {"model": model, "max_tokens": max_tokens, "stream": True,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    parts, usage, stop = [], {"input": 0, "output": 0, "cache": 0}, None
    for ev in _sse(os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages",
                   {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}, body):
        t = ev.get("type")
        if t == "message_start":
            u = ev.get("message", {}).get("usage", {}) or {}
            usage["input"] = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
            usage["cache"] = u.get("cache_read_input_tokens") or 0
            usage["output"] = u.get("output_tokens") or 0
        elif t == "content_block_delta":
            d = ev.get("delta", {})
            if d.get("type") == "text_delta":
                parts.append(d.get("text", ""))
        elif t == "message_delta":
            stop = (ev.get("delta") or {}).get("stop_reason") or stop
            u = ev.get("usage") or {}
            if u.get("output_tokens") is not None:
                usage["output"] = u["output_tokens"]
            if u.get("input_tokens"):
                usage["input"] = u["input_tokens"] + (u.get("cache_creation_input_tokens") or 0)
        elif t == "error":
            raise LLMError(f"stream error: {ev.get('error')}")
    if stop is None:
        raise LLMError("stream ended without a stop_reason (connection dropped mid-response)")
    return "".join(parts), usage, stop


def _openai_compat(base, api_key, prompt, system, model, temperature, max_tokens):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "max_tokens": max_tokens, "stream": True, "usage": {"include": True}}
    if temperature is not None:
        body["temperature"] = temperature
    parts, usage, stop = [], {"input": 0, "output": 0, "cache": 0}, None
    for ev in _sse(base + "/chat/completions", {"authorization": f"Bearer {api_key}"}, body):
        if ev.get("error"):
            raise LLMError(f"stream error: {ev['error']}")
        ch = (ev.get("choices") or [{}])[0]
        content = (ch.get("delta") or {}).get("content")
        if content:
            parts.append(content)
        stop = ch.get("finish_reason") or stop
        u = ev.get("usage")
        if u:
            usage = {"input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0),
                     "cache": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0), "cost": u.get("cost")}
    if stop is None:
        raise LLMError("stream ended without a finish_reason (connection dropped mid-response)")
    return "".join(parts), usage, stop


# ---------- output parsing ----------

def extract_json(text: str):
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.S)
    if m:
        return json.loads(m.group(1))
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        raise ValueError("no JSON found in LLM output")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[min(starts):end + 1])


FILE_FORMAT_INSTRUCTIONS = """Output every file you create or change IN FULL (not a diff), each in exactly this format:

### FILE: relative/path/from/repo/root.py
```python
<entire file content>
```
"""


EDIT_FORMAT_INSTRUCTIONS = """Express changes as search/replace edits (existing files are large — never rewrite them whole).
For each edit to an EXISTING file use exactly:

### EDIT: relative/path/from/repo/root.py
<<<<<<< SEARCH
<exact, contiguous lines copied from the current file, enough to be unique>
=======
<replacement lines>
>>>>>>> REPLACE

Use several EDIT blocks for several places. SEARCH text must match the file byte-for-byte (indentation included).
For a NEW file use:

### FILE: relative/path/new_file.py
```python
<entire file content>
```
"""

_EDIT_RE = re.compile(r"^### EDIT:\s*(\S+)\s*\n<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n?>>>>>>> REPLACE", re.S | re.M)


def apply_edits(text: str, current: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Apply SEARCH/REPLACE edits + FILE blocks from `text` to `current` ({path: content}).
    Returns (overlay of changed files, errors)."""
    overlay, errors = {}, []
    for m in _EDIT_RE.finditer(text):
        path, search, replace = m.group(1).strip().removeprefix("./"), m.group(2), m.group(3)
        base = overlay.get(path, current.get(path))
        if base is None:
            errors.append(f"EDIT on unknown file {path}")
            continue
        n = base.count(search)
        if n != 1:
            errors.append(f"SEARCH block {'not found' if n == 0 else 'ambiguous'} in {path}: {search[:80]!r}")
            continue
        overlay[path] = base.replace(search, replace, 1)
    for path, content in extract_files(text).items():
        overlay[path] = content
    return overlay, errors


def extract_files(text: str) -> dict[str, str]:
    files = {}
    for m in re.finditer(r"^### FILE:\s*(\S+)\s*\n```[\w+-]*\n(.*?)\n```[ \t]*$", text, re.S | re.M):
        path = m.group(1).strip()
        while path.startswith("./"):
            path = path[2:]
        if path.startswith("/") or ".." in Path(path).parts:
            continue  # refuse writes outside the repo
        files[path] = m.group(2) + "\n"
    return files
