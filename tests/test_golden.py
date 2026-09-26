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


def test_rpn_roundtrip_multi_variable_trees():
    """Deterministic sweep over mixed single- and multi-char variable names:
    token round-trip must be the identity, K must equal the token count, and
    multi-char names must force the spaced encoding."""
    import random

    from emlcore.tree import Eml, Var, depth, rpn_length

    rng = random.Random(0x9E3779B9)
    names = ["x", "y", "var", "A1", "z9"]

    def gen(d):
        if d == 0 or rng.random() < 0.25:
            return ONE if rng.random() < 0.2 else Var(rng.choice(names))
        return Eml(gen(d - 1), gen(d - 1))

    for _ in range(200):
        node = gen(5)
        tokens = to_rpn(node)
        back = from_rpn(tokens)
        assert to_rpn(back) == tokens  # exact structural identity
        assert rpn_length(back) == len(tokens)
        assert depth(back) == depth(node)


def test_rpn_rejects_reserved_variable_names():
    """A var named '1' or 'E' would silently decode as a different tree, so
    creation fails loudly instead. Multi-char names are fine (spaced form)."""
    from emlcore.tree import Var

    for name in ("1", "E", "eml"):
        with pytest.raises(ValueError):
            Var(name)

    node = Eml(ONE, Var("var"))
    assert rpn_string(node) == "1 var E"
    assert rpn_string(from_rpn(to_rpn(node))) == "1 var E"


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


# --- numeric literal forms (scientific notation, leading dot) ----------------


@pytest.mark.parametrize(
    "formula,expected",
    [
        ("1e-3", 0.001),
        ("1E-3", 0.001),
        ("2.5e-4", 2.5e-4),
        ("1e6", 1e6),
        ("1.23e5", 123000.0),
        ("6.02e23", 6.02e23),
        ("1.6e-19", 1.6e-19),
        (".5", 0.5),
        ("2.", 2.0),
        ("9.81", 9.81),
        ("-9.81", -9.81),
        ("1000", 1000),
        ("1023", 1023),
        ("-700", -700),
    ],
)
def test_numeric_literal_forms_compile_and_verify(formula, expected):
    """Scientific notation and leading-dot forms must lower to verified EML
    programs reproducing the input value (the input carries its own precision)."""
    from emlcore.parser import parse_formula

    r = compile_ast(parse_formula(formula))
    assert r["verified"], f"{formula} failed verify (max_err={r['max_err']})"
    got = complex(r["value"]["re"], r["value"]["im"])
    assert abs(got - expected) <= abs(expected) * 1e-9 + 1e-15, (
        f"{formula}: got {got}, want {expected}"
    )


@pytest.mark.parametrize(
    "formula",
    [
        "0.1234567",  # 7 significant digits: no compact form — must error, not round
        "1e300",  # exponent outside the evaluator's dynamic range
        "-1000",  # NEG(x)=0-e^x overflows for x>709: not representable
        "e^1023",  # tree lowers, but the value ~4.5e443 exceeds the float64 ceiling
        "e^2000",  # mantissa form (2*10^3) lowers, value still overflows
    ],
)
def test_unrepresentable_constants_fail_loudly(formula):
    """Constants without a compact EML form raise a clean ValueError instead of
    silently rounding to a nearby representable fraction."""
    from emlcore.parser import parse_formula

    with pytest.raises(ValueError):
        compile_ast(parse_formula(formula))


def test_pow_overflow_error_is_curated():
    """e^1023 lowers fine but its value exceeds the float64 ceiling: the
    OverflowError from the reference evaluator must surface as the curated
    ValueError, not a bare 'complex exponentiation'."""
    from emlcore.parser import parse_formula

    for formula in ["e^1023", "e^2000"]:
        with pytest.raises(ValueError, match="exceeds double precision"):
            compile_ast(parse_formula(formula))


def test_parser_still_accepts_euler_e_after_number_literals():
    """'e' remains the Euler constant even though numbers can now contain e/E
    in an exponent (the exponent requires digits, so a lone e still lexes as
    NAME)."""
    from emlcore.parser import parse_formula

    for formula, expected in [("e^2", math.e**2), ("e^-1", math.e**-1), ("e*pi", math.e * math.pi)]:
        r = compile_ast(parse_formula(formula))
        got = complex(r["value"]["re"], r["value"]["im"])
        assert r["verified"] and abs(got - expected) < 1e-6, f"{formula}: got {got}"


# --- verifier rejection paths (the trust anchor's negative space) -----------
# verify() is the only thing standing between a wrong EML program and a
# verified=true badge. These tests pin its REJECTION behaviour, not just its
# acceptance: a swapped/mismatched program, an out-of-tolerance error, and
# domain edges must all fail loudly.


def test_verifier_rejects_mismatched_program():
    """A program that does not compute the AST's function must be rejected.
    This is the anti-tofu property: swapping the tree under an AST cannot
    produce a verified result."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    v = verify(lower(A.VarX()), A.Func("sqrt", A.Num(2)))  # tree=x, claim=sqrt(2)
    assert not v["ok"]
    assert v["max_err"] > 1.0


def test_verifier_rejects_wrong_constant():
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    v = verify(lower(A.Num(2)), A.Num(5))
    assert not v["ok"]
    assert v["max_err"] == 3.0


def test_verifier_tolerance_is_enforced():
    """verify() must actually compare error against tol: a tolerance far below
    the construction's numerical error (sqrt(2) errs ~4e-17) must reject."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    ast = A.Func("sqrt", A.Num(2))
    node = lower(ast)
    assert verify(node, ast, tol=1e-6)["ok"]
    assert not verify(node, ast, tol=1e-20)["ok"]


def test_verifier_skips_samples_outside_reference_domain():
    """Points where the reference evaluator raises count as out-of-domain and
    are skipped, not failures: asin(x-3) is real only at x=2.3 and 3.3."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import DEFAULT_SAMPLES, verify

    ast = A.Func("asin", A.Sub(A.VarX(), A.Num(3)))
    v = verify(lower(ast), ast)
    assert v["ok"]
    assert [c["x"] for c in v["checks"]] == [2.3, 3.3]
    assert len(DEFAULT_SAMPLES) == 6  # 4 of 6 samples were skipped


def test_verifier_rejects_when_reference_fails_at_every_sample():
    """If the reference evaluator errors at every sample there is no evidence —
    the result must be unverified with no checks, not vacuously true. Reachable
    when the AST is structurally broken relative to the tree (here: a function
    name ref_eval does not know)."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    node = lower(A.VarX())
    ast = A.Func("totally_bogus", A.VarX())  # ref_eval raises at every sample
    v = verify(node, ast)
    assert not v["ok"]
    assert v["checks"] == []


def test_verifier_raises_on_structurally_invalid_pairing():
    """A constant tree against a variable-requiring AST is a programmer error:
    the constant branch calls ref_eval without an env, which raises unbound-
    variable. verify fails fast rather than silently returning garbage."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    with pytest.raises(ValueError):
        verify(lower(A.Num(2)), A.Func("ln", A.VarX()))


def test_verifier_falls_back_to_complex_comparison():
    """Functions that are complex-valued on the reals (e^{ix}) are compared on
    the full complex samples, not dropped for having no real points."""
    from emlcore import mathast as A
    from emlcore.lower import lower
    from emlcore.verify import verify

    ast = A.Func("exp", A.Mul(A.ConstI(), A.VarX()))
    v = verify(lower(ast), ast)
    assert v["ok"]
    assert any(c["expect"].imag != 0 for c in v["checks"])


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


def test_llm_provider_is_orcarouter():
    """The fallback targets OrcaRouter's OpenAI-compatible gateway using the
    orcarouter/free pool routing name, and reads the key from
    ORCAROUTER_API_KEY."""
    from emlcore import llm

    assert llm._MODEL == "orcarouter/free"
    assert llm._BASE_URL == "https://api.orcarouter.ai/v1"


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


def test_compile_hides_non_valueerror_exception_details():
    """Non-ValueError exceptions never reach the client: the response carries
    the fixed generic line while the full exception goes to server logs.

    Guards CWE-209 (py/stack-trace-exposure): the catch blocks are `except
    Exception`, so e.g. a missing API key (RuntimeError) or a transport error
    from the LLM client must not leak its message in the response body."""
    import api.index as api_index
    import emlcore.llm as llm_mod
    from api.index import _GENERIC_ERROR, app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    def fake_nl(_text: str) -> str:
        raise RuntimeError("ORCAROUTER_API_KEY is not set")

    api_index._llm_hits.clear()  # don't inherit the rate-limit test's budget
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(llm_mod, "formula_from_nl", fake_nl)
        body = client.post("/api/compile", json={"formula": "hello world"}).json()

    assert body["ok"] is False and body["stage"] == "parse"
    assert body["llm_error"] == _GENERIC_ERROR
    assert "ORCAROUTER_API_KEY" not in body["llm_error"]
    # The deterministic parse error is a curated ValueError and still flows
    # (the parser deliberately wraps lark syntax errors for users).
    assert body["error"].startswith("syntax error")


def test_compile_lower_stage_hides_internal_errors():
    """A non-ValueError escaping compile_ast is masked; the stage is kept."""
    import api.index as api_index
    from api.index import _GENERIC_ERROR, app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    def boom(_ast: object) -> dict:
        raise TypeError("unexpected AST node <boom>")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(api_index, "compile_ast", boom)
        body = client.post("/api/compile", json={"formula": "x"}).json()

    assert body["ok"] is False and body["stage"] == "lower"
    assert body["error"] == _GENERIC_ERROR
    assert "<boom>" not in body["error"]


def test_compile_passes_curated_valueerror_through():
    """Curated parser ValueErrors still surface verbatim to the client."""
    from api.index import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    body = client.post("/api/compile", json={"formula": "foo(1)"}).json()

    assert body["ok"] is False and body["stage"] == "parse"
    assert "'foo'" in body["error"]


def test_compile_pow_overflow_returns_curated_envelope():
    """End to end: e^1023 must produce the curated overflow message in the
    API error envelope (it used to leak the bare OverflowError text)."""
    from api.index import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    body = client.post("/api/compile", json={"formula": "e^1023"}).json()

    assert body["ok"] is False and body["stage"] == "lower"
    assert "exceeds double precision" in body["error"]
