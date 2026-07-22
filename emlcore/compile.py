"""End-to-end: math AST -> verified EML program (RPN + tree + value)."""

from __future__ import annotations

from . import mathast as A
from .evaluate import evaluate
from .lower import lower
from .tree import depth, rpn_length, rpn_string, to_rpn, variables
from .verify import verify


def compile_ast(ast: A.Ast, tol: float = 1e-6) -> dict:
    node = lower(ast)
    v = verify(node, ast, tol=tol)
    vars_ = sorted(variables(node))

    result: dict = {
        "rpn": rpn_string(node),
        "tokens": to_rpn(node),
        "k": rpn_length(node),
        "depth": depth(node),
        "variables": vars_,
        "verified": v["ok"],
        "max_err": v["max_err"],
    }
    if not vars_:
        val = evaluate(node)
        result["value"] = {"re": val.real, "im": val.imag}
    return result
