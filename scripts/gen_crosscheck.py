"""Generate the TS<->Python cross-check fixture.

Computes values for a set of EML programs with the Python evaluator and writes
them to lib/eml/__fixtures__/crosscheck.json. lib/eml/crosscheck.test.ts then
re-evaluates the same programs with the TS evaluator and asserts they agree —
proving the interactive (client) and authoritative (server) cores match.

Run:  PYTHONPATH=. uv run python scripts/gen_crosscheck.py
"""

import json
import os

from emlcore.compile import compile_ast
from emlcore.evaluate import evaluate
from emlcore.parser import parse_formula
from emlcore.tree import parse_rpn

entries = []


def add(rpn: str, x=None) -> None:
    node = parse_rpn(rpn)
    env = {"x": complex(x)} if x is not None else {}
    v = evaluate(node, env)
    entries.append({"rpn": rpn, "x": x, "re": v.real, "im": v.imag})


# canonical paper programs
add("11E")  # e
add("x1E", 2.0)  # e^2
add("11xE1EE", 2.0)  # ln 2
add("111E1EE")  # 0

# compiled constants
for f in ["2*3", "1/2", "sqrt(2)", "i", "pi", "-1", "2+3", "6/2"]:
    add(compile_ast(parse_formula(f))["rpn"])

# compiled functions, sampled at several x
for f in ["x^2", "e^x", "ln(x)", "2*x", "1/x", "sin(x)", "cos(x)", "atan(x)"]:
    rpn = compile_ast(parse_formula(f))["rpn"]
    for x in [0.5, 1.7, 3.2]:
        add(rpn, x)

out = os.path.join(os.path.dirname(__file__), "..", "lib", "eml", "__fixtures__", "crosscheck.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as fh:
    json.dump(entries, fh, indent=1)
print(f"wrote {len(entries)} entries -> {os.path.normpath(out)}")
