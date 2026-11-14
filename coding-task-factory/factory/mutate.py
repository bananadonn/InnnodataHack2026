"""AST mutation operators, applied ONLY to functions the reference implementation added or changed."""
from __future__ import annotations

import ast
import copy

from .analyze import function_nodes

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
            ast.Is: ast.IsNot, ast.IsNot: ast.Is}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
            ast.FloorDiv: ast.Div, ast.Mod: ast.FloorDiv}


def changed_functions(base_src: str | None, ref_src: str) -> set[str]:
    ref = function_nodes(ref_src)
    if not base_src:
        return set(ref)
    try:
        base = function_nodes(base_src)
    except SyntaxError:
        return set(ref)
    return {q for q, n in ref.items() if q not in base or ast.dump(base[q]) != ast.dump(n)}


class _Mutator(ast.NodeTransformer):
    def __init__(self, targets: set[str], pick: int):
        self.targets, self.pick, self.count, self.stack, self.active = targets, pick, 0, [], False
        self.description = None

    def _hit(self) -> bool:
        hit = self.count == self.pick
        self.count += 1
        return hit

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()
        return node

    def visit_FunctionDef(self, node):
        qual = ".".join(self.stack + [node.name])
        prev = self.active
        self.active = qual in self.targets
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()
        self.active = prev
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Compare(self, node):
        self.generic_visit(node)
        if self.active and type(node.ops[0]) in CMP_SWAP and self._hit():
            old = type(node.ops[0])
            node.ops[0] = CMP_SWAP[old]()
            self.description = f"line {node.lineno}: comparison {old.__name__} -> {CMP_SWAP[old].__name__}"
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if self.active and type(node.op) in BIN_SWAP and self._hit():
            old = type(node.op)
            node.op = BIN_SWAP[old]()
            self.description = f"line {node.lineno}: operator {old.__name__} -> {BIN_SWAP[old].__name__}"
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self.active and self._hit():
            new = ast.Or if isinstance(node.op, ast.And) else ast.And
            self.description = f"line {node.lineno}: {type(node.op).__name__} -> {new.__name__}"
            node.op = new()
        return node

    def visit_Constant(self, node):
        if self.active and type(node.value) in (int, bool) and self._hit():
            new = (not node.value) if isinstance(node.value, bool) else node.value + 1
            self.description = f"line {node.lineno}: constant {node.value!r} -> {new!r}"
            return ast.copy_location(ast.Constant(new), node)
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        if self.active and self._hit():
            self.description = f"line {node.lineno}: negate if-condition"
            node.test = ast.UnaryOp(ast.Not(), node.test)
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        if self.active and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None) and self._hit():
            self.description = f"line {node.lineno}: return None instead of value"
            node.value = ast.Constant(None)
        return node

    def visit_Raise(self, node):
        self.generic_visit(node)
        if self.active and self._hit():
            self.description = f"line {node.lineno}: delete raise"
            return ast.Pass()
        return node


def generate_mutants(base_src: str | None, ref_src: str, limit: int = 20) -> list[tuple[str, str]]:
    """Return [(description, mutated_source)] — evenly sampled up to `limit`."""
    targets = changed_functions(base_src, ref_src)
    if not targets:
        return []
    tree = ast.parse(ref_src)
    counter = _Mutator(targets, pick=-1)
    counter.visit(copy.deepcopy(tree))
    total = counter.count
    picks = range(total) if total <= limit else [round(i * (total - 1) / (limit - 1)) for i in range(limit)]
    out = []
    for k in dict.fromkeys(picks):
        m = _Mutator(targets, pick=k)
        new = ast.fix_missing_locations(m.visit(copy.deepcopy(tree)))
        if m.description:
            out.append((m.description, ast.unparse(new) + "\n"))
    return out
