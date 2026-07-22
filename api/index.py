"""EML Calculator backend (FastAPI).

Local dev:  uv run uvicorn api.index:app --port 8000 --reload
Vercel:     deployed as a Python serverless function (entrypoint api.index:app).

Routes are namespaced under /api to line up with Vercel's /api function routing
and the Next.js dev rewrite (see next.config.ts).
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from emlcore.compile import compile_ast
from emlcore.parser import parse_formula

app = FastAPI(title="EML Calculator API", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "eml-calculator-api"}


class CompileRequest(BaseModel):
    formula: str


@app.post("/api/compile")
def compile_endpoint(req: CompileRequest) -> dict:
    """Compile a formula to a verified EML/RPN program.

    Path: deterministic parse -> (LLM fallback if parse fails) -> lower -> verify.
    The LLM only rewrites messy/natural-language input into a supported formula
    string, which is then parsed deterministically and numerically verified.
    """
    formula = (req.formula or "").strip()
    if not formula:
        return {"ok": False, "stage": "parse", "error": "empty formula", "input": formula}

    source = "parser"
    interpreted = formula
    try:
        ast = parse_formula(formula)
    except Exception as parse_err:
        # Fallback: ask LongCat-2.0 to translate, then re-parse deterministically.
        try:
            from emlcore.llm import formula_from_nl

            interpreted = formula_from_nl(formula)
            ast = parse_formula(interpreted)
            source = "llm"
        except Exception as llm_err:
            return {
                "ok": False,
                "stage": "parse",
                "input": formula,
                "error": str(parse_err),
                "llm_error": str(llm_err),
            }

    try:
        result = compile_ast(ast)
    except Exception as lower_err:
        return {
            "ok": False,
            "stage": "lower",
            "input": formula,
            "interpreted": interpreted,
            "error": str(lower_err),
        }

    result["input"] = formula
    result["interpreted"] = interpreted
    result["source"] = source
    result["ok"] = bool(result["verified"])
    if not result["verified"]:
        result["stage"] = "verify"
        result["error"] = "compiled program failed numeric verification"
    return result
