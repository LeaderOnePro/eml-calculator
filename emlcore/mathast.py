"""Standard math AST + a reference evaluator (the ground truth the EML tree is
verified against). The reference uses Python's cmath so it is independent of the
EML machinery."""

from __future__ import annotations

import cmath
from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class ConstE:
    pass


@dataclass(frozen=True)
class ConstPi:
    pass


@dataclass(frozen=True)
class ConstI:
    pass


@dataclass(frozen=True)
class VarX:
    name: str = "x"


@dataclass(frozen=True)
class Neg:
    x: "Ast"


@dataclass(frozen=True)
class Add:
    a: "Ast"
    b: "Ast"


@dataclass(frozen=True)
class Sub:
    a: "Ast"
    b: "Ast"


@dataclass(frozen=True)
class Mul:
    a: "Ast"
    b: "Ast"


@dataclass(frozen=True)
class Div:
    a: "Ast"
    b: "Ast"


@dataclass(frozen=True)
class Pow:
    a: "Ast"
    b: "Ast"


@dataclass(frozen=True)
class Func:
    name: str  # exp | ln | log | sqrt
    x: "Ast"


Ast = Union[Num, ConstE, ConstPi, ConstI, VarX, Neg, Add, Sub, Mul, Div, Pow, Func]


def variables(ast: Ast) -> set[str]:
    if isinstance(ast, VarX):
        return {ast.name}
    for f in getattr(ast, "__dataclass_fields__", {}):
        v = getattr(ast, f)
        if isinstance(v, (Num, ConstE, ConstPi, ConstI, VarX, Neg, Add, Sub, Mul, Div, Pow, Func)):
            pass
    # simpler explicit walk:
    out: set[str] = set()
    _collect(ast, out)
    return out


def _collect(ast: Ast, out: set[str]) -> None:
    if isinstance(ast, VarX):
        out.add(ast.name)
    elif isinstance(ast, Neg):
        _collect(ast.x, out)
    elif isinstance(ast, Func):
        _collect(ast.x, out)
    elif isinstance(ast, (Add, Sub, Mul, Div, Pow)):
        _collect(ast.a, out)
        _collect(ast.b, out)


_CMATH_FUNCS = {
    "exp": cmath.exp, "ln": cmath.log, "log": cmath.log, "sqrt": cmath.sqrt,
    "sin": cmath.sin, "cos": cmath.cos, "tan": cmath.tan,
    "asin": cmath.asin, "acos": cmath.acos, "atan": cmath.atan,
    "sinh": cmath.sinh, "cosh": cmath.cosh, "tanh": cmath.tanh,
    "asinh": cmath.asinh, "acosh": cmath.acosh, "atanh": cmath.atanh,
}


def ref_eval(ast: Ast, env: dict[str, complex] | None = None) -> complex:
    env = env or {}
    e = ref_eval
    if isinstance(ast, Num):
        return complex(ast.value)
    if isinstance(ast, ConstE):
        return complex(cmath.e)
    if isinstance(ast, ConstPi):
        return complex(cmath.pi)
    if isinstance(ast, ConstI):
        return complex(0, 1)
    if isinstance(ast, VarX):
        if ast.name not in env:
            raise ValueError(f"unbound variable '{ast.name}'")
        return complex(env[ast.name])
    if isinstance(ast, Neg):
        return -e(ast.x, env)
    if isinstance(ast, Add):
        return e(ast.a, env) + e(ast.b, env)
    if isinstance(ast, Sub):
        return e(ast.a, env) - e(ast.b, env)
    if isinstance(ast, Mul):
        return e(ast.a, env) * e(ast.b, env)
    if isinstance(ast, Div):
        return e(ast.a, env) / e(ast.b, env)
    if isinstance(ast, Pow):
        return e(ast.a, env) ** e(ast.b, env)
    if isinstance(ast, Func):
        v = e(ast.x, env)
        f = _CMATH_FUNCS.get(ast.name)
        if f is None:
            raise ValueError(f"unknown function '{ast.name}'")
        return f(v)
    raise ValueError(f"cannot evaluate AST node {ast!r}")
