"""Deterministic math-formula parser (lark) -> standard AST.

Handles well-formed expressions like `sin(x)+2`, `sqrt(2)`, `e^(i*pi)`, `1/2`.
Raises on anything it can't parse; that's the signal for the LLM fallback
(natural language / messy input) to step in upstream."""

from __future__ import annotations

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError, VisitError

from . import mathast as A

_GRAMMAR = r"""
    ?start: sum

    ?sum: sum "+" product   -> add
        | sum "-" product   -> sub
        | product

    ?product: product "*" unary   -> mul
            | product "/" unary   -> div
            | unary

    # Unary minus binds looser than '^': -2^2 = -(2^2) = -4, matching the
    # convention of Python, Desmos, WolframAlpha and Google. The exponent
    # position still accepts a leading '-' so 2^-2 keeps working.
    ?power: atom "^" unary_pow   -> pow
          | atom "**" unary_pow  -> pow
          | atom

    ?unary_pow: "-" unary_pow   -> neg
              | "+" unary_pow   -> pos
              | power

    ?unary: "-" unary   -> neg
          | "+" unary   -> pos
          | power

    ?atom: NUMBER             -> num
         | NAME "(" sum ")"   -> func
         | NAME               -> name
         | "(" sum ")"

    # Scientific notation and a leading-dot form: 1e-3, 1E-3, 2.5E+2, .5, 2.
    # The exponent part requires digits after e/E, so a lone 'e' still lexes as
    # the NAME terminal (Euler's constant) and e^2 / e^-1 keep working.
    NUMBER: /(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?/
    NAME: /[a-zA-Z_][a-zA-Z_0-9]*/
    %import common.WS
    %ignore WS
"""

_SUPPORTED_FUNCS = {
    "exp",
    "ln",
    "sqrt",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "asinh",
    "acosh",
    "atanh",
}

# normalize common spellings to the canonical names above
_ALIASES = {
    "log": "ln",
    "arcsin": "asin",
    "arccos": "acos",
    "arctan": "atan",
    "arsinh": "asinh",
    "arcsinh": "asinh",
    "arcosh": "acosh",
    "arccosh": "acosh",
    "artanh": "atanh",
    "arctanh": "atanh",
}


@v_args(inline=True)
class _BuildAst(Transformer):
    def num(self, tok):
        return A.Num(float(tok))

    def add(self, a, b):
        return A.Add(a, b)

    def sub(self, a, b):
        return A.Sub(a, b)

    def mul(self, a, b):
        return A.Mul(a, b)

    def div(self, a, b):
        return A.Div(a, b)

    def pow(self, a, b):
        return A.Pow(a, b)

    def neg(self, a):
        return A.Neg(a)

    def pos(self, a):
        return a

    def name(self, tok):
        s = str(tok).lower()
        if s == "x":
            return A.VarX("x")
        if s == "e":
            return A.ConstE()
        if s in ("pi", "pie"):
            return A.ConstPi()
        if s == "i":
            return A.ConstI()
        raise ValueError(f"unknown symbol '{tok}'")

    def func(self, name, arg):
        f = _ALIASES.get(str(name).lower(), str(name).lower())
        if f not in _SUPPORTED_FUNCS:
            raise ValueError(f"unsupported function '{name}'")
        return A.Func(f, arg)


_parser = Lark(_GRAMMAR, parser="lalr", transformer=_BuildAst())


def parse_formula(s: str) -> A.Ast:
    """Parse a formula string to an AST, or raise ValueError with a clean message."""
    text = s.strip()
    if not text:
        raise ValueError("empty formula")
    try:
        return _parser.parse(text)
    except VisitError as e:  # our own ValueError raised inside the transformer
        raise ValueError(str(e.orig_exc)) from e
    except LarkError as e:
        raise ValueError(f"syntax error: {e}") from e
