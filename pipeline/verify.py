"""Mechanical grounding: check the agent's claims against the cloned source.

The model supplies names and descriptions; signatures and line numbers always come from here,
parsed out of the code. A symbol that does not exist is dropped, not trusted.

Python only for now. Other languages pass through marked unverified.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Symbol:
    qualname: str
    kind: str  # function | method | class | variable
    signature: str
    line_start: int
    line_end: int
    source: str


def _func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"


def _collect(body: list[ast.stmt], prefix: str, text: str, out: dict[str, Symbol]) -> None:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + node.name
            # @overload stubs come first; the last definition is the implementation and wins.
            out[name] = Symbol(name, "method" if prefix else "function", _func_sig(node), node.lineno,
                               node.end_lineno or node.lineno, ast.get_source_segment(text, node) or "")
        elif isinstance(node, ast.ClassDef):
            name = prefix + node.name
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            sig = f"class {node.name}({bases})" if bases else f"class {node.name}"
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
            if init:
                sig += f"  # __init__({ast.unparse(init.args)})"
            out[name] = Symbol(name, "class", sig, node.lineno, node.end_lineno or node.lineno,
                               ast.get_source_segment(text, node) or "")
            _collect(node.body, name + ".", text, out)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and not prefix:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    out[t.id] = Symbol(t.id, "variable", clip_line(ast.unparse(node)), node.lineno,
                                       node.end_lineno or node.lineno, ast.get_source_segment(text, node) or "")


def clip_line(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + " ..."


@lru_cache(maxsize=256)
def index_python(path: Path) -> dict[str, Symbol]:
    """Map qualified name -> Symbol for every function, class, method and module variable in a file."""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    out: dict[str, Symbol] = {}
    _collect(tree.body, "", text, out)
    return out


def resolve(index: dict[str, Symbol], name: str) -> Symbol | None:
    """Find `name` in a module index, tolerating `()` and leading package prefixes (click.core.Option.x)."""
    name = name.strip().strip("`").split("(")[0].strip()
    parts = name.split(".")
    for i in range(len(parts)):
        hit = index.get(".".join(parts[i:]))
        if hit:
            return hit
    return None


def is_python(path: str) -> bool:
    return path.endswith(".py")


def file_lines(repo: Path, rel: str) -> int | None:
    """Number of lines in a repo file, or None if it is not a file inside the repo."""
    p = (repo / rel).resolve()
    try:
        if not p.is_relative_to(repo.resolve()) or not p.is_file():
            return None
        return len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return None
