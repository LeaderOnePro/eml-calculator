"""Evaluate an EML tree over C using numpy.complex128.

We deliberately use numpy (not Python's cmath) because the EML constructions
rely on IEEE extended reals that cmath traps as errors:
    ln(0) = -inf,  exp(-inf) = 0,  overflow -> inf.
numpy propagates these silently (with warnings we suppress), matching the
TS/`complex.ts` client evaluator so both agree on the same programs.
"""

from __future__ import annotations

import numpy as np

from .tree import Eml, Node, One, Var


def evaluate(node: Node, env: dict[str, complex] | None = None) -> complex:
    env = env or {}
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        return complex(_eval(node, env))


def _eval(node: Node, env: dict[str, complex]) -> np.complex128:
    if isinstance(node, One):
        return np.complex128(1)
    if isinstance(node, Var):
        if node.name not in env:
            raise ValueError(f"unbound variable '{node.name}'")
        return np.complex128(env[node.name])
    # Eml: exp(a) - ln(b), principal branch over C.
    x = _eval(node.a, env)
    y = _eval(node.b, env)
    return np.exp(x) - np.log(y)
