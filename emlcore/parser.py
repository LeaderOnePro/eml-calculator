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

    ?product: product "*" power   -> mul
            | product "/" power   -> div
            | power

    ?power: unary "^" power    -> pow
          | unary "**" power   -> pow
          | unary

    ?unary: "-" unary   -> neg
          | "+" unary   -> pos
          | atom

    ?atom: NUMBER             -> num
         | NAME "(" sum ")"   -> func
         | NAME               -> name
         | "(" sum ")"

    NUMBER: /\d+(\.\d+)?/
    NAME: /[a-zA-Z_][a-zA-Z_0-9]*/
    %import common.WS
    %ignore WS
"""

_SUPPORTED_FUNCS = {"exp", "ln", "log", "sqrt"}


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
        f = str(name).lower()
        if f not in _SUPPORTED_FUNCS:
            raise ValueError(f"unsupported function '{name}'")
        return A.Func("ln" if f == "log" else f, arg)


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
