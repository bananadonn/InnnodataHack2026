"""Step 1 — deterministic repo analysis (no LLM): module outlines, baseline health, prompt context."""
from __future__ import annotations

import ast
import re
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".ctf_cache", "node_modules", "docs",
             "examples", ".tox", ".github"}


def is_test_path(rel: str) -> bool:
    parts = Path(rel).parts
    return bool(parts) and (parts[0] in ("tests", "test") or Path(rel).name.startswith("test_")
                            or rel.endswith("conftest.py"))


def py_files(repo: Path, overlay: dict | None = None) -> dict[str, str]:
    files = {}
    for p in sorted(repo.rglob("*.py")):
        rel_parts = p.relative_to(repo).parts
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in rel_parts):
            continue
        files[p.relative_to(repo).as_posix()] = p.read_text(errors="replace")
    for rel, content in (overlay or {}).items():
        if content is None:
            files.pop(rel, None)
        elif rel.endswith(".py"):
            files[rel] = content
    return files


def defined_symbols(source: str) -> dict[str, str]:
    """qualname -> signature for every function/class (methods as Class.method)."""
    out = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out

    def walk(node, prefix=""):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[prefix + n.name] = f"def {n.name}({ast.unparse(n.args)})" + \
                    (f" -> {ast.unparse(n.returns)}" if n.returns else "")
                walk(n, prefix + n.name + ".")
            elif isinstance(n, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in n.bases)
                out[prefix + n.name] = f"class {n.name}({bases})"
                walk(n, prefix + n.name + ".")
    walk(tree)
    return out


def function_nodes(source: str) -> dict:
    nodes = {}

    def walk(node, prefix=""):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes[prefix + n.name] = n
                walk(n, prefix + n.name + ".")
            elif isinstance(n, ast.ClassDef):
                walk(n, prefix + n.name + ".")
    walk(ast.parse(source))
    return nodes


def outline(source: str) -> str:
    """Public signatures only — cheap context for modules we are not focusing on."""
    return "\n".join(sig for q, sig in defined_symbols(source).items()
                     if not q.split(".")[-1].startswith("_") or q.endswith("__init__"))


def summarize(repo: Path) -> dict:
    files = py_files(repo)
    return {"source_files": {k: {"lines": v.count("\n"), "public_symbols": len(outline(v).splitlines())}
                             for k, v in files.items() if not is_test_path(k)},
            "test_files": sorted(k for k in files if is_test_path(k) and not k.endswith("conftest.py"))}


def source_dump(repo: Path, focus: list[str], overlay: dict | None = None, max_chars: int = 230000,
                example_tests: list[str] | None = None) -> str:
    """Focus modules in full, every other source module as a signature outline, plus example test files."""
    files = py_files(repo, overlay)
    parts = []
    for rel in focus:
        if rel in files:
            parts.append(f"### {rel} (full)\n```python\n{files[rel]}\n```")
    others = [f"# {rel}\n{outline(src)}" for rel, src in files.items()
              if rel not in focus and not is_test_path(rel) and outline(src)]
    parts.append("### Other modules (public signatures only)\n```python\n" + "\n\n".join(others) + "\n```")
    for rel in example_tests or []:
        if rel in files:
            parts.append(f"### {rel} (existing tests, for style and fixtures)\n```python\n{files[rel][:15000]}\n```")
    text = "\n\n".join(parts)
    return text[:max_chars] + ("\n...[truncated]" if len(text) > max_chars else "")


def related_test_files(repo: Path, touched: list[str], limit: int = 4) -> list[str]:
    """Existing test files that exercise the touched modules (curated P2P candidates, not a whole-suite dump).
    Ranked by: name match (core.py -> test_core*.py) then how many touched-module symbols they reference."""
    files = py_files(repo)
    tests = {p: c for p, c in files.items() if is_test_path(p) and not p.endswith("conftest.py")}
    scores = {}
    for mod in touched:
        if mod not in files or is_test_path(mod):
            continue
        stem = Path(mod).stem.lstrip("_")
        syms = {q.split(".")[-1] for q in defined_symbols(files[mod]) if not q.split(".")[-1].startswith("_")}
        for p, c in tests.items():
            s = 100 if Path(p).stem.startswith(f"test_{stem}") else 0
            s += sum(1 for sym in syms if re.search(rf"\b{re.escape(sym)}\b", c))
            if s:
                scores[p] = scores.get(p, 0) + s
    return [p for p, _ in sorted(scores.items(), key=lambda kv: -kv[1])][:limit]
