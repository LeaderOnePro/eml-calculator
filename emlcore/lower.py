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


# --- transcendental function builders ---
# Euler forms for trig/hyperbolic and log-forms for the inverse functions, adopted
# from VA00/SymbolicRegressionPackage's EmL_compiler (MIT). Every form's correctness
# is enforced downstream by the numeric verifier (verify.py).
def DOUBLE(z: Node) -> Node:
    return ADD(z, z)


def SQRT(z: Node) -> Node:
    return POW(z, HALF)


def SIN(x: Node) -> Node:  # (e^{ix} − e^{−ix}) / (2i)
    ix = MUL(I, x)
    return DIV(SUB(EXP(ix), EXP(NEG(ix))), MUL(TWO, I))


def COS(x: Node) -> Node:  # (e^{ix} + e^{−ix}) / 2
    ix = MUL(I, x)
    return DIV(ADD(EXP(ix), EXP(NEG(ix))), TWO)


def TAN(x: Node) -> Node:
    return DIV(SIN(x), COS(x))


def SINH(z: Node) -> Node:  # (e^{2z} − 1) / (2 e^z)
    return DIV(SUB(EXP(DOUBLE(z)), ONE), MUL(TWO, EXP(z)))


def COSH(z: Node) -> Node:  # (e^{2z} + 1) / (2 e^z)
    return DIV(ADD(EXP(DOUBLE(z)), ONE), MUL(TWO, EXP(z)))


def TANH(z: Node) -> Node:  # (e^{2z} − 1) / (e^{2z} + 1)
    e2z = EXP(DOUBLE(z))
    return DIV(SUB(e2z, ONE), ADD(e2z, ONE))


def ASIN(z: Node) -> Node:  # i·ln(−i·z + √(1 − z²))
    return MUL(I, LN(ADD(NEG(MUL(I, z)), SQRT(SUB(ONE, MUL(z, z))))))


def ACOS(z: Node) -> Node:  # −i·ln(z + √(z−1)·√(z+1))  (sign fixed for the EML branch)
    return MUL(NEG(I), LN(ADD(z, MUL(SQRT(SUB(z, ONE)), SQRT(ADD(z, ONE))))))


def ATAN(z: Node) -> Node:  # (−i/2)·ln((−i + z)/(−i − z))
    return MUL(DIV(NEG(I), TWO), LN(DIV(ADD(NEG(I), z), SUB(NEG(I), z))))


def ASINH(z: Node) -> Node:  # ln(z + √(z² + 1))
    return LN(ADD(z, SQRT(ADD(MUL(z, z), ONE))))


def ACOSH(z: Node) -> Node:  # ln(z + √(z+1)·√(z−1))
    return LN(ADD(z, MUL(SQRT(ADD(z, ONE)), SQRT(SUB(z, ONE)))))


def ATANH(z: Node) -> Node:  # (1/2)·ln((1 + z)/(1 − z))
    return MUL(HALF, LN(DIV(ADD(ONE, z), SUB(ONE, z))))


_FUNCS = {
    "exp": EXP,
    "ln": LN,
    "log": LN,
    "sqrt": SQRT,
    "sin": SIN,
    "cos": COS,
    "tan": TAN,
    "asin": ASIN,
    "acos": ACOS,
    "atan": ATAN,
    "sinh": SINH,
    "cosh": COSH,
    "tanh": TANH,
    "asinh": ASINH,
    "acosh": ACOSH,
    "atanh": ATANH,
}


def _integer(n: int) -> Node:
    if n == 0:
        return ZERO
    if n < 0:
        return NEG(_integer(-n))
    # binary double-and-add (adopted from VA00/SymbolicRegressionPackage eml_int):
    # O(log n) additions instead of O(n), so integers/constants get much shorter K.
    acc: Node | None = None
    term: Node = ONE
    k = n
    while k > 0:
        if k & 1:
            acc = term if acc is None else ADD(acc, term)
        term = ADD(term, term)
        k >>= 1
    assert acc is not None
    return acc


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
        fn = _FUNCS.get(ast.name)
        if fn is None:
            raise ValueError(f"unsupported function '{ast.name}'")
        return fn(L(ast.x))
    raise ValueError(f"cannot lower AST node {ast!r}")
