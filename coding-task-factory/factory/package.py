"""Load a Harbor task package (docs/harbor_task_interface.md) into the in-memory form the gates use.

This is the integration contract with the rest of the team: whatever the SDK / test generator produce
internally, the end product is a Harbor package, and the validator only reads that.
"""
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

from .analyze import is_test_path
from .sandbox import overlay_from_patch


def _read(p: Path) -> str:
    return p.read_text(errors="replace") if p.exists() else ""


def _json_list(p: Path) -> tuple[list, str | None]:
    if not p.exists():
        return [], f"missing {p.name}"
    try:
        data = json.loads(p.read_text())
        return (data, None) if isinstance(data, list) else ([], f"{p.name} is not a JSON array")
    except json.JSONDecodeError as e:
        return [], f"{p.name} invalid JSON: {e}"


def pseudo_spec(text: str) -> dict:
    """Recover a spec-like dict from instruction.md so spec-based checks work on any package.
    requirements = the numbered list (prefers the 'Required behavior' section); interface = backticked items
    of the 'Public interface' section. The raw text is kept in `_text` and is what LLM roles see."""
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), "untitled task")
    sections, cur = {}, "_top"
    for ln in text.splitlines():
        m = re.match(r"^#{2,3}\s+(.*)", ln)
        if m:
            cur = m.group(1).strip().lower()
            continue
        sections.setdefault(cur, []).append(ln)
    req_lines = next((v for k, v in sections.items() if "behavio" in k or "requirement" in k), None) or text.splitlines()
    reqs, buf = [], None
    for ln in req_lines:
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)", ln)
        if m:
            if buf is not None:
                reqs.append(buf)
            buf = m.group(2).strip()
        elif buf is not None and ln.strip() and not ln.lstrip().startswith(("|", "#")):
            buf += " " + ln.strip()
        elif buf is not None and not ln.strip():
            reqs.append(buf)
            buf = None
    if buf is not None:
        reqs.append(buf)
    iface_lines = next((v for k, v in sections.items() if "interface" in k), [])
    interface = []
    for ln in iface_lines:
        for code in re.findall(r"`([^`]+)`", ln):
            name = re.match(r"\s*(?:async\s+)?(?:def|class)\s+(\w+)", code)
            interface.append({"path": "", "symbol": name.group(1) if name else code.split("(")[0].strip(),
                              "signature": code})
    return {"title": title, "problem_statement": "\n".join(sections.get("_top", [])).strip(),
            "requirements": [{"id": f"R{i}", "text": t} for i, t in enumerate(reqs, 1)],
            "interface": interface, "_text": text}


def run_script_files(run_script: str) -> list[str]:
    m = re.search(r"ALL=\((.*?)\)", run_script, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def load_package(d: Path, repo: Path) -> dict:
    """Returns a dict with everything the gates need, plus `load_errors` (empty if the package is usable)."""
    errs = []
    meta = {}
    try:
        meta = tomllib.loads(_read(d / "task.toml"))
    except tomllib.TOMLDecodeError as e:
        errs.append(f"task.toml does not parse: {e}")
    md = meta.get("metadata", {})
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if md.get("base_commit") and md["base_commit"] != head:
        errs.append(f"package base_commit {md['base_commit'][:12]} != local repo HEAD {head[:12]} "
                    f"(git -C {repo} checkout {md['base_commit']})")
    instruction = _read(d / "instruction.md")
    if not instruction.strip():
        errs.append("instruction.md missing or empty")
    gold_diff, test_diff = _read(d / "solution" / "patch.diff"), _read(d / "tests" / "test_patch.diff")
    gold, gerr = overlay_from_patch(repo, gold_diff)
    tests, terr = overlay_from_patch(repo, test_diff)
    if gerr:
        errs.append(f"solution/patch.diff does not apply to base: {gerr}")
    if terr:
        errs.append(f"tests/test_patch.diff does not apply to base: {terr}")
    if not gold and not gerr:
        errs.append("solution/patch.diff is empty")
    f2p, e1 = _json_list(d / "tests" / "fail_to_pass.json")
    p2p, e2 = _json_list(d / "tests" / "pass_to_pass.json")
    errs += [e for e in (e1, e2) if e]
    rs_files = run_script_files(_read(d / "tests" / "run_script.sh"))
    id_files = sorted({t.split("::")[0] for t in f2p + p2p})
    graded_files = sorted(set(rs_files) | set(id_files) | {p for p in tests if p.endswith(".py") and is_test_path(p)})
    test_src = "\n\n".join(c for p, c in sorted(tests.items()) if c and p.endswith(".py"))
    return {"instance_id": md.get("instance_id") or d.name, "dir": str(d), "meta": meta, "instruction": instruction,
            "spec": pseudo_spec(instruction), "gold": gold, "gold_diff": gold_diff, "tests": tests,
            "test_src": test_src, "f2p_declared": f2p, "p2p_declared": p2p, "graded_files": graded_files,
            "run_script_files": rs_files, "load_errors": errs}
