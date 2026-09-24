"""Golden tests for the EML core — RPN codec, complex evaluator, and the
lowering+verifier pipeline anchored on the paper's identities."""

import cmath
import math

import pytest
from emlcore import (
    ONE,
    Eml,
    Var,
    compile_ast,
    evaluate,
    from_rpn,
    parse_rpn,
    rpn_string,
    to_rpn,
)
from emlcore import mathast as A

# --- RPN codec --------------------------------------------------------------


def test_rpn_roundtrip_and_paper_ln_code():
    ln_x = parse_rpn("11xE1EE")  # paper's canonical ln program (K=7)
    assert rpn_string(ln_x) == "11xE1EE"
    assert rpn_string(from_rpn(to_rpn(ln_x))) == "11xE1EE"
    assert abs(evaluate(ln_x, {"x": 2}) - cmath.log(2)) < 1e-9


def test_rpn_malformed_raises():
    with pytest.raises(ValueError):
        parse_rpn("1E")  # underflow
    with pytest.raises(ValueError):
        parse_rpn("11")  # stack size 2


# --- core evaluator ---------------------------------------------------------


def test_e_and_exp_codes():
    e = Eml(ONE, ONE)
    assert rpn_string(e) == "11E"
    assert abs(evaluate(e) - math.e) < 1e-9
    exp_x = Eml(Var("x"), ONE)
    assert rpn_string(exp_x) == "x1E"
    assert abs(evaluate(exp_x, {"x": 2}) - math.exp(2)) < 1e-9


def test_ln0_is_neg_inf_and_negation():
    def ln(b):
        return Eml(ONE, Eml(Eml(ONE, b), ONE))

    ln0 = ln(ln(ONE))
    assert evaluate(ln0).real == float("-inf")
    neg_x = Eml(ln0, Eml(Var("x"), ONE))  # -x, relies on e^{-inf}=0
    assert abs(evaluate(neg_x, {"x": 3}) + 3) < 1e-9


# --- lowering + verification (the trust anchor) -----------------------------

CONSTANTS = [
    ("1", A.Num(1), 1),
    ("2", A.Num(2), 2),
    ("0", A.Num(0), 0),
    ("-1", A.Neg(A.Num(1)), -1),
    ("1/2", A.Num(0.5), 0.5),
    ("e", A.ConstE(), math.e),
    ("pi", A.ConstPi(), math.pi),
    ("2*3", A.Mul(A.Num(2), A.Num(3)), 6),
    ("6/2", A.Div(A.Num(6), A.Num(2)), 3),
    ("2+3", A.Add(A.Num(2), A.Num(3)), 5),
    ("5-2", A.Sub(A.Num(5), A.Num(2)), 3),
    ("sqrt(2)", A.Func("sqrt", A.Num(2)), math.sqrt(2)),
]


@pytest.mark.parametrize("name,ast,expected", CONSTANTS)
def test_constant_compiles_and_verifies(name, ast, expected):
    r = compile_ast(ast)
    assert r["verified"], f"{name} failed verify (max_err={r['max_err']})"
    got = complex(r["value"]["re"], r["value"]["im"])
    assert abs(got - expected) < 1e-6, f"{name}: got {got}, want {expected}"


def test_imaginary_unit():
    r = compile_ast(A.ConstI())
    assert r["verified"]
    got = complex(r["value"]["re"], r["value"]["im"])
    assert abs(got - 1j) < 1e-6


FUNCTIONS = [
    ("x^2", A.Pow(A.VarX(), A.Num(2))),
    ("e^x", A.Func("exp", A.VarX())),
    ("ln x", A.Func("ln", A.VarX())),
    ("2*x", A.Mul(A.Num(2), A.VarX())),
    ("1/x", A.Div(A.Num(1), A.VarX())),
]


@pytest.mark.parametrize("name,ast", FUNCTIONS)
def test_function_compiles_and_verifies(name, ast):
    r = compile_ast(ast)
    assert r["verified"], f"{name} failed verify (max_err={r['max_err']})"
    assert r["variables"] == ["x"]


def test_paper_k_values():
    assert compile_ast(A.ConstE())["k"] == 3  # e   -> 11E
    assert compile_ast(A.Func("exp", A.VarX()))["k"] == 3  # e^x -> x1E
    assert compile_ast(A.Func("ln", A.VarX()))["k"] == 7  # lnx -> 11xE1EE
    assert compile_ast(A.Num(0))["k"] == 7  # 0   -> 111E1EE


TRANSCENDENTAL = [
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
]


@pytest.mark.parametrize("fn", TRANSCENDENTAL)
def test_transcendental_compiles_and_verifies(fn):
    from emlcore.parser import parse_formula

    r = compile_ast(parse_formula(f"{fn}(x)"))
    assert r["verified"], f"{fn}(x) failed verify (max_err={r['max_err']})"
    assert r["variables"] == ["x"]


def test_function_aliases():
    from emlcore.parser import parse_formula

    for a, b in [("arcsin(x)", "asin(x)"), ("arctan(x)", "atan(x)"), ("arcosh(x)", "acosh(x)")]:
        assert compile_ast(parse_formula(a))["rpn"] == compile_ast(parse_formula(b))["rpn"]


# --- unary minus vs '^' precedence ------------------------------------------
# Convention check: Python, Desmos, WolframAlpha and Google all parse -2^2 as
# -(2^2). The grammar previously bound '-' tighter than '^', so -2^2 = 4 — and
# the verifier could not catch it because ref_eval shares the same (wrong) AST.
# These tests pin the corrected binding; the exponent position still accepts a
# leading '-', keeping 2^-2 usable.


@pytest.mark.parametrize(
    "formula,expected",
    [
        ("-2^2", -4.0),
        ("-2**2", -4.0),
        ("-2^-2", -0.25),
        ("2^-2", 0.25),
        ("(-2)^2", 4.0),
        ("1-2^2", -3.0),
        ("-3", -3.0),
    ],
)
def test_unary_minus_binds_looser_than_power(formula, expected):
    from emlcore.parser import parse_formula

    r = compile_ast(parse_formula(formula))
    assert r["verified"], f"{formula} failed verify (max_err={r['max_err']})"
    got = complex(r["value"]["re"], r["value"]["im"])
    assert abs(got - expected) < 1e-6, f"{formula}: got {got}, want {expected}"


@pytest.mark.parametrize(
    "formula,x,expected",
    [
        ("-x^2", 1.5, -2.25),
        ("2^-x", 2.0, 0.25),
        ("-sin(x)^2", 1.0, -(math.sin(1.0) ** 2)),
    ],
)
def test_unary_minus_variable_power(formula, x, expected):
    """End-to-end: the lowered EML program (not just the AST) must agree with
    the reference evaluator and the expected value at a sample point."""
    from emlcore.parser import parse_formula

    ast = parse_formula(formula)
    r = compile_ast(ast)
    assert r["verified"], f"{formula} failed verify (max_err={r['max_err']})"
    got = evaluate(parse_rpn(r["rpn"]), {"x": complex(x)})
    assert abs(got - expected) < 1e-9, f"{formula} at x={x}: got {got}, want {expected}"


# --- prompt / parser drift guard --------------------------------------------


def test_llm_prompt_covers_supported_functions():
    """The NL fallback prompt must advertise every function the parser can
    lower; otherwise the model refuses expressible requests. Add a function to
    parser._SUPPORTED_FUNCS without updating the prompt and this test fails.

    Whole-string check (no regex): robust to any future reformatting of the
    prompt bullet block. A plain substring test is safe here because we assert
    on the full set of canonical names, not on individual tokens — 'sin'
    appearing inside 'asin(' is irrelevant when 'sin' is also present in the
    bullet as its own 'sin(' entry."""
    from emlcore.llm import _SYSTEM
    from emlcore.parser import _SUPPORTED_FUNCS

    missing = [fn for fn in _SUPPORTED_FUNCS if fn not in _SYSTEM]
    assert not missing, f"LLM prompt missing function(s): {sorted(missing)}"


def test_llm_provider_is_agnes():
    """The fallback targets Agnes 3.0 Flash's OpenAI-compatible endpoint and
    reads the key from AGNES_API_KEY."""
    from emlcore import llm

    assert llm._MODEL == "agnes-3.0-flash"
    assert llm._BASE_URL == "https://apihub.agnes-ai.com/v1"


# --- /api/compile abuse guards -----------------------------------------------


def test_compile_rejects_oversized_formula():
    """Input past the cap is rejected before the parser or the LLM is touched."""
    from api.index import MAX_FORMULA_CHARS, app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.post("/api/compile", json={"formula": "x" * (MAX_FORMULA_CHARS + 1)})
    assert r.status_code == 400
    body = r.json()
    assert body["ok"] is False
    assert body["stage"] == "input"


def test_compile_rate_limited_after_burst():
    """The LLM fallback is rate-limited: unparseable formulas burn the budget,
    then get a structured rate-limit response instead of an LLM call."""
    from api.index import RATE_LIMIT_REQUESTS, app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    garbage = "hello world this is not math"
    saw_limit = False
    for _ in range(RATE_LIMIT_REQUESTS + 2):
        body = client.post("/api/compile", json={"formula": garbage}).json()
        if body.get("stage") == "rate-limit":
            saw_limit = True
            assert body["ok"] is False
            break
    assert saw_limit, "expected a rate-limit response within the burst"

    # Deterministic formulas bypass the LLM entirely and must still work.
    body = client.post("/api/compile", json={"formula": "sin(x)"}).json()
    assert body["ok"] is True and body["source"] == "parser"
