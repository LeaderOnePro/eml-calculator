"""Numeric verifier — the trust anchor.

Compiles are only trusted if the EML tree numerically matches the reference
(cmath) evaluator at several sample points. Constants are checked directly;
functions of x are sampled across the positive real axis (where the principal
branches of the reference and the EML construction agree)."""

from __future__ import annotations

from . import mathast as A
from .evaluate import evaluate
from .tree import Node, variables

# Sample points on the positive real axis, chosen to avoid the tan/sec poles
# near π/2 and 3π/2 while covering both the |x|<1 and |x|>1 regimes.
DEFAULT_SAMPLES = [0.3, 0.7, 1.1, 2.3, 3.3, 4.1]


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
    real_pts = []
    all_pts = []
    for x in samples:
        try:
            expect = A.ref_eval(ast, {"x": complex(x)})
        except Exception:
            continue  # reference raised — x outside its domain
        got = evaluate(node, {"x": complex(x)})
        rec = {"x": x, "expect": expect, "got": got}
        all_pts.append(rec)
        if abs(expect.imag) <= 1e-9:
            real_pts.append(rec)

    # Prefer the real-valued domain (the paper verifies "on the real axis where
    # appropriate"); fall back to full complex comparison only for functions that
    # are complex-valued on the reals, e.g. e^{ix}.
    checks = real_pts if real_pts else all_pts
    if not checks:
        return {"ok": False, "max_err": 0.0, "checks": []}
    max_err = max(abs(c["got"] - c["expect"]) for c in checks)
    ok = all(_close(c["got"], c["expect"], tol) for c in checks)
    return {"ok": ok, "max_err": max_err, "checks": checks}
