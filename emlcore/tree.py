"""EML expression tree + RPN codec.  Grammar:  S -> 1 | eml(S, S)  (+ variables)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class One:
    pass


@dataclass(frozen=True)
class Var:
    name: str

    def __post_init__(self):
        if self.name in _RESERVED_VAR_NAMES:
            raise ValueError(f"variable name '{self.name}' collides with the RPN alphabet")


@dataclass(frozen=True)
class Eml:
    a: Node
    b: Node


Node = One | Var | Eml

ONE = One()

# Names the RPN alphabet reserves. A variable holding one of these would
# silently round-trip into a different tree (Var("1") -> the terminal 1,
# Var("E") -> an eml application), so creation fails loudly instead.
_RESERVED_VAR_NAMES = ("1", "E", "eml")


def leaves(n: Node) -> int:
    return leaves(n.a) + leaves(n.b) if isinstance(n, Eml) else 1


def rpn_length(n: Node) -> int:
    """RPN token count K = 2·leaves − 1 (e.g. ln x -> 11xE1EE, K=7)."""
    return 2 * leaves(n) - 1


def depth(n: Node) -> int:
    return 1 + max(depth(n.a), depth(n.b)) if isinstance(n, Eml) else 0


def variables(n: Node) -> set[str]:
    if isinstance(n, Var):
        return {n.name}
    if isinstance(n, Eml):
        return variables(n.a) | variables(n.b)
    return set()


def to_rpn(n: Node) -> list[str]:
    if isinstance(n, One):
        return ["1"]
    if isinstance(n, Var):
        return [n.name]
    return to_rpn(n.a) + to_rpn(n.b) + ["E"]


def rpn_string(n: Node) -> str:
    toks = to_rpn(n)
    return "".join(toks) if all(len(t) == 1 for t in toks) else " ".join(toks)


def from_rpn(tokens: list[str]) -> Node:
    stack: list[Node] = []
    for tok in tokens:
        if tok in ("E", "eml"):
            if len(stack) < 2:
                raise ValueError(f"RPN stack underflow at '{tok}'")
            b = stack.pop()
            a = stack.pop()
            stack.append(Eml(a, b))
        elif tok == "1":
            stack.append(ONE)
        else:
            stack.append(Var(tok))
    if len(stack) != 1:
        raise ValueError(f"RPN did not reduce to one expression (stack size {len(stack)})")
    return stack[0]


def parse_rpn(s: str) -> Node:
    s = s.strip()
    if not s:
        raise ValueError("empty RPN string")
    tokens = s.split() if any(c.isspace() for c in s) else list(s)
    return from_rpn(tokens)
