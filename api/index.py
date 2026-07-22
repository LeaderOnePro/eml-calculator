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
    """Compile a formula string to a verified EML/RPN program.

    Deterministic path: parse -> lower -> numeric verify. If the parser can't
    handle the input (natural language / messy), the LLM fallback takes over
    (wired in a later step); today that surfaces as a parse error.
    """
    formula = (req.formula or "").strip()
    if not formula:
        return {"ok": False, "stage": "parse", "error": "empty formula", "input": formula}

    try:
        ast = parse_formula(formula)
        source = "parser"
    except Exception as parse_err:
        # TODO(llm): fall back to LongCat-2.0 to turn `formula` into an AST here.
        return {"ok": False, "stage": "parse", "error": str(parse_err), "input": formula}

    try:
        result = compile_ast(ast)
    except Exception as lower_err:
        return {"ok": False, "stage": "lower", "error": str(lower_err), "input": formula}

    result["input"] = formula
    result["source"] = source
    result["ok"] = bool(result["verified"])
    if not result["verified"]:
        result["stage"] = "verify"
        result["error"] = "compiled program failed numeric verification"
    return result
