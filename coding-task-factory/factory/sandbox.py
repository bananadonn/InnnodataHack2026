"""Fast local inner loop: isolated workspace copies + pytest with the SAME test-id vocabulary as the grader.

We run `pytest -rA` and parse it with the kit's own parser.py, so the ids we put into
fail_to_pass.json / pass_to_pass.json are byte-identical to what grade.py will look up in the container.
The container run (harbor oracle/nop) is the authoritative check; this layer exists because mutation testing
and independent solvers need dozens of runs, which would be too slow through Docker.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("kit_parser", ROOT / "vendor" / "innodata_kit" / "parser.py")
kit_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_parser)

IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc", ".venv", "venv", "*.egg-info",
                                ".tox", ".mypy_cache", "build", "dist", "node_modules")
TMP_ROOT = Path(os.environ.get("CTF_TMP", tempfile.gettempdir())) / "ctf_workspaces"
SRC_DIR = os.environ.get("CTF_SRC_DIR", "src")

Overlay = dict  # {relative_path: content | None (delete)}


@dataclass
class TestRun:
    results: dict = field(default_factory=dict)  # nodeid -> PASSED|FAILED|ERROR|SKIPPED
    timed_out: bool = False
    output: str = ""
    returncode: int = 0

    def passed(self, tid: str) -> bool:
        return self.results.get(tid) == "PASSED"

    @property
    def any_failure(self) -> bool:
        return self.timed_out or any(s in ("FAILED", "ERROR") for s in self.results.values()) or \
            (self.returncode not in (0, 5) and not self.results)


def apply_overlay(root: Path, overlay: Overlay | None) -> None:
    for rel, content in (overlay or {}).items():
        p = root / rel
        if content is None:
            p.unlink(missing_ok=True)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def make_workspace(repo: Path, *overlays) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    dst = Path(tempfile.mkdtemp(prefix="ws_", dir=TMP_ROOT)) / "repo"
    shutil.copytree(repo, dst, ignore=IGNORE)
    for ov in overlays:
        apply_overlay(dst, ov)
    return dst


def cleanup(ws: Path) -> None:
    shutil.rmtree(ws.parent, ignore_errors=True)


def run_pytest(root: Path, test_files=None, extra_args=None, timeout: int = 300) -> TestRun:
    files = [f for f in (test_files or []) if (root / f).exists()]  # same "only present files" rule as run_script.sh
    if test_files is not None and not files:
        return TestRun(output="no graded test files present")
    cmd = [sys.executable, "-m", "pytest", *files, "-rA", "--tb=short", "-p", "no:cacheprovider", "--color=no",
           "--continue-on-collection-errors", *(extra_args or [])]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": os.pathsep.join([str(root / SRC_DIR), str(root)])}
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return TestRun(timed_out=True, output="TIMEOUT", returncode=-1)
    parsed = kit_parser.parse_test_output(proc.stdout, proc.stderr)
    return TestRun({r.name: r.status.name for r in parsed}, False, proc.stdout[-6000:] + proc.stderr[-2000:],
                   proc.returncode)


def run_candidate(repo: Path, *overlays, test_files=None, extra_args=None, timeout=300) -> TestRun:
    ws = make_workspace(repo, *overlays)
    try:
        return run_pytest(ws, test_files, extra_args, timeout)
    finally:
        cleanup(ws)


def git_diff(repo: Path, overlay: Overlay) -> str:
    """A `git apply`-compatible unified diff of overlay vs repo (handles new/deleted files)."""
    ws = make_workspace(repo)
    try:
        g = ["git", "-c", "user.email=bench@local", "-c", "user.name=bench", "-c", "core.autocrlf=false"]
        subprocess.run([*g, "init", "-q"], cwd=ws, check=True)
        subprocess.run([*g, "add", "-A"], cwd=ws, check=True)
        subprocess.run([*g, "commit", "-q", "-m", "base"], cwd=ws, check=True)
        apply_overlay(ws, overlay)
        subprocess.run([*g, "add", "-A"], cwd=ws, check=True)
        return subprocess.run([*g, "diff", "--cached", "--no-color", "--no-ext-diff"], cwd=ws, check=True,
                              capture_output=True, text=True).stdout
    finally:
        cleanup(ws)


def overlay_from_patch(repo: Path, diff_text: str) -> tuple[dict, str | None]:
    """Apply a unified diff to a copy of `repo` and return ({path: new content | None if deleted}, error)."""
    if not diff_text.strip():
        return {}, None
    ws = make_workspace(repo)
    try:
        g = ["git", "-c", "user.email=bench@local", "-c", "user.name=bench", "-c", "core.autocrlf=false"]
        subprocess.run([*g, "init", "-q"], cwd=ws, check=True)
        subprocess.run([*g, "add", "-A"], cwd=ws, check=True)
        subprocess.run([*g, "commit", "-q", "-m", "base"], cwd=ws, check=True)
        patch = ws.parent / "change.diff"
        patch.write_text(diff_text)
        r = subprocess.run([*g, "apply", "--whitespace=nowarn", str(patch)], cwd=ws, capture_output=True, text=True)
        if r.returncode != 0:
            return {}, (r.stderr or r.stdout)[-800:]
        subprocess.run([*g, "add", "-A"], cwd=ws, check=True)
        names = subprocess.run([*g, "diff", "--cached", "--name-status", "--no-renames"], cwd=ws,
                               capture_output=True, text=True, check=True).stdout
        overlay = {}
        for line in names.splitlines():
            status, path = line.split("\t", 1)
            overlay[path] = None if status.startswith("D") else (ws / path).read_text(errors="replace")
        return overlay, None
    finally:
        cleanup(ws)


def ids_in_files(results, test_paths) -> list[str]:
    paths = set(test_paths)
    return sorted(t for t in results if t.split("::")[0] in paths)
