"""Numeric verifier — the trust anchor.

Compiles are only trusted if the EML tree numerically matches the reference
(cmath) evaluator at several sample points. Constants are checked directly;
functions of x are sampled across the positive real axis (where the principal
branches of the reference and the EML construction agree)."""

from __future__ import annotations

from . import mathast as A
from .evaluate import evaluate
from .tree import Node, variables

# Sample points on the positive real axis (avoids the ln branch cut).
DEFAULT_SAMPLES = [0.3, 0.7, 1.5, 2.2, 3.1, 4.7]


def _close(got: complex, expect: complex, tol: float) -> bool:
    return abs(got - expect) <= tol * max(1.0, abs(expect))


def verify(node: Node, ast: A.Ast, tol: float = 1e-6, samples=None) -> dict:
    vars_ = variables(node)

    if not vars_:
        expect = A.ref_eval(ast)
        got = evaluate(node)
        err = abs(got - expect)
        return {
            "ok": _close(got, expect, tol),
            "max_err": err,
            "checks": [{"x": None, "expect": expect, "got": got}],
        }

    samples = samples if samples is not None else DEFAULT_SAMPLES
    checks = []
    max_err = 0.0
    ok = True
    for x in samples:
        try:
            expect = A.ref_eval(ast, {"x": complex(x)})
        except Exception:
            continue  # x outside the reference domain — skip
        got = evaluate(node, {"x": complex(x)})
        max_err = max(max_err, abs(got - expect))
        checks.append({"x": x, "expect": expect, "got": got})
        if not _close(got, expect, tol):
            ok = False
    if not checks:
        ok = False
    return {"ok": ok, "max_err": max_err, "checks": checks}
