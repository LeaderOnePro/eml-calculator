"""End-to-end: math AST -> verified EML program (RPN + tree + value)."""

from __future__ import annotations

from . import mathast as A
from .evaluate import evaluate
from .lower import lower
from .tree import depth, rpn_length, rpn_string, to_rpn, variables
from .verify import verify


def compile_ast(ast: A.Ast, tol: float = 1e-6) -> dict:
    node = lower(ast)
    try:
        v = verify(node, ast, tol=tol)
    except OverflowError as err:
        # The tree lowered fine but its *value* is outside double precision —
        # e.g. e^1023 (~1e443), far above the float64 ceiling (~1.8e308). The
        # constant branch of verify() evaluates the reference expression
        # directly, so the overflow escapes as a bare OverflowError; translate
        # it into the same curated ValueError every other out-of-range input
        # gets. Sampled (variable) branches never see this: verify() treats a
        # reference failure there as "x outside the domain".
        raise ValueError(
            "the value of this formula exceeds double precision (the float64 limit is ~1.8e308)"
        ) from err
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
