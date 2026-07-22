"""Lowering: standard math AST  ->  pure EML tree.

Every macro below is a builder returning an EML `Node`. They start from the
paper's identities; branch-cut correctness on the negative axis is guaranteed
not by hand-proof but by the numeric verifier (see verify.py) — anything that
doesn't match the reference evaluator at sample points is rejected upstream.

Core identities (paper §4.1):
    exp(a) = eml(a, 1)
    ln(b)  = eml(1, eml(eml(1, b), 1))
Everything else is composed from exp/ln + the -inf terminal (ln 0).
"""

from __future__ import annotations

from fractions import Fraction

from . import mathast as A
from .tree import Eml, Node, ONE, Var

# --- primitive macros -------------------------------------------------------


def EXP(a: Node) -> Node:  # exp(a)
    return Eml(a, ONE)


E: Node = Eml(ONE, ONE)  # e = exp(1) - ln(1) = e


def LN(b: Node) -> Node:  # ln(b)   (eq. 5)
    return Eml(ONE, Eml(Eml(ONE, b), ONE))


ZERO: Node = LN(ONE)  # ln 1 = 0
LN0: Node = LN(ZERO)  # ln 0 = -inf   (extended-real terminal)


def NEG(x: Node) -> Node:  # -x = 0 - x   (uses e^{-inf}=0)
    return Eml(LN0, EXP(x))


def INV(b: Node) -> Node:  # 1/b = exp(-ln b)
    return Eml(Eml(LN0, b), ONE)


def SUB(a: Node, b: Node) -> Node:  # a - b = exp(ln a) - ln(exp b)
    return Eml(LN(a), EXP(b))


def ADD(a: Node, b: Node) -> Node:  # a + b = a - (-b)
    return SUB(a, NEG(b))


def MUL(a: Node, b: Node) -> Node:  # a·b = exp(ln a + ln b)  (branch error killed by exp)
    return EXP(ADD(LN(a), LN(b)))


def DIV(a: Node, b: Node) -> Node:  # a/b = exp(ln a - ln b)
    return EXP(SUB(LN(a), LN(b)))


def POW(a: Node, b: Node) -> Node:  # a^b = exp(b·ln a)
    return EXP(MUL(b, LN(a)))


# --- derived constants ------------------------------------------------------

TWO: Node = ADD(ONE, ONE)
HALF: Node = INV(TWO)
# Under numpy's principal branch, POW(-1, 1/2) = +i and ln(-1) = +iπ (the sign
# rides on a ~1e-16 imaginary part, but it is deterministic — pinned by tests).
I: Node = POW(NEG(ONE), HALF)  # +i
PI: Node = MUL(NEG(I), LN(NEG(ONE)))  # (-i)·(+iπ) = π


def _integer(n: int) -> Node:
    if n == 0:
        return ZERO
    if n < 0:
        return NEG(_integer(-n))
    node: Node = ONE
    for _ in range(n - 1):
        node = ADD(node, ONE)
    return node


def _rational(value: float) -> Node:
    fr = Fraction(value).limit_denominator(10**6)
    if fr.denominator == 1:
        return _integer(fr.numerator)
    return DIV(_integer(fr.numerator), _integer(fr.denominator))


# --- lowering ---------------------------------------------------------------


def lower(ast: A.Ast) -> Node:
    L = lower
    if isinstance(ast, A.Num):
        v = float(ast.value)
        return _integer(int(v)) if v.is_integer() else _rational(v)
    if isinstance(ast, A.ConstE):
        return E
    if isinstance(ast, A.ConstPi):
        return PI
    if isinstance(ast, A.ConstI):
        return I
    if isinstance(ast, A.VarX):
        return Var(ast.name)
    if isinstance(ast, A.Neg):
        return NEG(L(ast.x))
    if isinstance(ast, A.Add):
        return ADD(L(ast.a), L(ast.b))
    if isinstance(ast, A.Sub):
        return SUB(L(ast.a), L(ast.b))
    if isinstance(ast, A.Mul):
        return MUL(L(ast.a), L(ast.b))
    if isinstance(ast, A.Div):
        return DIV(L(ast.a), L(ast.b))
    if isinstance(ast, A.Pow):
        return POW(L(ast.a), L(ast.b))
    if isinstance(ast, A.Func):
        x = L(ast.x)
        if ast.name == "exp":
            return EXP(x)
        if ast.name in ("ln", "log"):
            return LN(x)
        if ast.name == "sqrt":
            return POW(x, HALF)
        raise ValueError(f"unsupported function '{ast.name}'")
    raise ValueError(f"cannot lower AST node {ast!r}")
