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

import math
from fractions import Fraction

from . import mathast as A
from .tree import ONE, Eml, Node, Var

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


# _integer materializes a tree whose node count roughly doubles per binary
# digit of n (the subtrees are not shared), so |n| beyond these limits explodes
# in memory and time. The evaluator also overflows intermediates, asymmetrically:
# a positive n is built from ADD(a,b)=exp(ln a)-ln(exp b) chains whose exp
# operand is a binary term <= 512 (so n <= 1023 keeps e^term finite), while
# NEG(x)=0-e^x consumes x directly and overflows once x > ~709 (the double
# e^x overflow line). Numbers outside the range get a clean error — they have
# no usable EML form anyway.
_MAX_INTEGER = 1023
_MIN_INTEGER = -709


def _integer(n: int) -> Node:
    if n > _MAX_INTEGER or n < _MIN_INTEGER:
        raise ValueError(
            f"integer {n} outside the expandable range [{_MIN_INTEGER}, {_MAX_INTEGER}]"
        )
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


def _mantissa_exponent(value: float) -> tuple[int, int] | None:
    """Decompose |value| as M*10^e with an integer M of at most 3 significant
    digits (so M always fits the _integer cap). Returns None when the value
    needs more digits, i.e. it has no compact EML form. This makes
    scientific-notation inputs (1e6, 6.02e23, 1.23e5) lowerable: the input
    itself carries the limited precision, so M*10^e reproduces it exactly at
    float precision."""
    a = abs(value)
    k = math.floor(math.log10(a))
    for digits in range(1, 4):
        scale = 10.0 ** (k - digits + 1)
        m = round(a / scale)
        if 0 < m <= _MAX_INTEGER and abs(m * scale - a) <= a * 1e-12:
            return m, k - digits + 1
    return None


# The DIV(a,b) = exp(ln a − ln b) construction loses numeric accuracy for
# large denominators (verified: 1/1000 verifies, 1/4000 does not) — beyond
# this bound use the mantissa·power-of-ten form instead.
_MAX_DIV_DENOMINATOR = _MAX_INTEGER
# POW(10, e) computes exp(e·ln 10); keep the intermediate exponent safely
# below the ~709 overflow line.
_MAX_MANTISSA_EXPONENT = 100


def _rational(value: float) -> Node:
    # Every negative constant must pass through NEG(x) = 0 - e^x, which
    # overflows once x exceeds ~709 — a hard representability boundary, unlike
    # the magnitude limits below (positive constants of any scale can go
    # through the mantissa·10^e form).
    if value < _MIN_INTEGER:
        raise ValueError(
            f"negative constant {value!r} has no compact EML form: "
            f"NEG(x) = 0 - e^x overflows once x exceeds {-_MIN_INTEGER}"
        )
    # Simple decimals keep their DIV form (0.5 -> 1/2, 0.001 -> 1/1000), which
    # is shorter than a mantissa-times-power-of-ten tree. The fraction must
    # reproduce the input at float precision — never silently round. The sign
    # is applied last so NEG only ever sees the quotient (e^quotient overflows
    # much later than e^numerator).
    fr = Fraction(value).limit_denominator(_MAX_DIV_DENOMINATOR)
    if (
        abs(fr.numerator) <= _MAX_INTEGER
        and fr.denominator <= _MAX_DIV_DENOMINATOR
        and abs(float(fr)) <= -_MIN_INTEGER
        and abs(float(fr) - value) <= abs(value) * 1e-15
    ):
        node = DIV(_integer(abs(fr.numerator)), _integer(fr.denominator))
        return NEG(node) if value < 0 else node
    # Fall back to M*10^e for scientific-notation-scale values.
    me = _mantissa_exponent(value)
    if me is None:
        raise ValueError(
            f"{value!r} has no compact EML expansion (needs more than 3 significant "
            f"digits, an integer outside [{_MIN_INTEGER}, {_MAX_INTEGER}], or an "
            f"exponent beyond ±{_MAX_MANTISSA_EXPONENT})"
        )
    m, e = me
    if abs(e) > _MAX_MANTISSA_EXPONENT:
        raise ValueError(f"exponent magnitude {abs(e)} exceeds {_MAX_MANTISSA_EXPONENT}")
    node = _integer(m)
    if e != 0:
        ten = _integer(10)
        power = POW(ten, _integer(e)) if e > 0 else POW(ten, NEG(_integer(-e)))
        node = MUL(node, power)
    return NEG(node) if value < 0 else node


# --- lowering ---------------------------------------------------------------


def lower(ast: A.Ast) -> Node:
    L = lower
    if isinstance(ast, A.Num):
        v = float(ast.value)
        if v.is_integer() and _MIN_INTEGER <= v <= _MAX_INTEGER:
            return _integer(int(v))
        return _rational(v)
    if isinstance(ast, A.ConstE):
        return E
    if isinstance(ast, A.ConstPi):
        return PI
    if isinstance(ast, A.ConstI):
        return I
    if isinstance(ast, A.VarX):
        return Var(ast.name)
    if isinstance(ast, A.Neg):
        if isinstance(ast.x, A.Num):
            folded = -float(ast.x.value)
            # Integer result and NEG survives (operand e^{-folded} finite):
            # keep the short NEG(_integer(n)) form. Otherwise let _rational
            # apply the sign where it is representable, or fail cleanly.
            if folded.is_integer() and folded >= _MIN_INTEGER:
                return NEG(_integer(int(-folded)))
            return _rational(folded)
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
