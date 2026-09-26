"""EML Calculator backend (FastAPI).

Local dev:  uv run uvicorn api.index:app --port 8000 --reload
Vercel:     deployed as a Python serverless function (entrypoint api.index:app).

Routes are namespaced under /api to line up with Vercel's /api function routing
and the Next.js dev rewrite (see next.config.ts).
"""

from __future__ import annotations

import time

from emlcore.compile import compile_ast
from emlcore.parser import parse_formula
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="EML Calculator API", version="1.0.0")

# A formula that actually needs the LLM fallback is a sentence; anything past a
# few hundred chars is payload abuse (the deterministic parser fails on it long
# before the LLM could help). Cap *before* touching the parser or the LLM.
MAX_FORMULA_CHARS = 500

# Rate limiting for the LLM fallback. This is a per-process in-memory window —
# cheap and enough to blunt naive abuse on a single-instance serverless
# deployment; not a distributed guarantee. Vercel firewall/WAF rules remain the
# first line of defense for real traffic spikes.
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60.0

_llm_hits: list[float] = []


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "eml-calculator-api"}


class CompileRequest(BaseModel):
    formula: str = Field(default="", max_length=MAX_FORMULA_CHARS)


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return 400 with our error envelope for oversized/invalid bodies, so the
    frontend shows its normal error card instead of a raw FastAPI 422."""
    del request
    errors = exc.errors()
    msg = str(errors[0].get("msg")) if errors else "invalid request"
    return JSONResponse(
        status_code=400,
        content={"ok": False, "stage": "input", "error": msg or "invalid request"},
    )


def _llm_allowed() -> bool:
    """Sliding-window check for LLM-fallback calls. Prunes expired hits first."""
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    while _llm_hits and _llm_hits[0] < cutoff:
        _llm_hits.pop(0)
    if len(_llm_hits) >= RATE_LIMIT_REQUESTS:
        return False
    _llm_hits.append(now)
    return True


# Fixed client-facing line for exceptions we cannot curate.
_GENERIC_ERROR = "something went wrong while handling this formula"


def _client_message(stage: str, err: Exception | None) -> str:
    """Pick the client-facing text for an error response.

    Only curated ValueError messages (parser / lower / LLM-reject copy written
    for users) travel to the client verbatim. Any other exception — a missing
    API key, a network failure, an actual bug — gets a fixed line, with the
    full exception printed to the server logs (visible in Vercel runtime logs)
    instead of the response body.
    """
    if isinstance(err, ValueError):
        return str(err)
    if err is not None:
        print(f"[{stage}] {type(err).__name__}: {err!r}", flush=True)
    return _GENERIC_ERROR


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
    ast = None
    parse_err: Exception | None = None
    try:
        ast = parse_formula(formula)
    except Exception as err:
        parse_err = err

    if ast is None:
        if not _llm_allowed():
            return {
                "ok": False,
                "stage": "rate-limit",
                "input": formula,
                "error": (
                    "too many natural-language requests; retry in a minute "
                    f"(limit: {RATE_LIMIT_REQUESTS}/{int(RATE_LIMIT_WINDOW_SECONDS)}s)"
                ),
            }
        # Fallback: ask the LLM to translate, then re-parse deterministically.
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
                "error": _client_message("parse", parse_err),
                "llm_error": _client_message("llm", llm_err),
            }

    try:
        result = compile_ast(ast)
    except Exception as lower_err:
        return {
            "ok": False,
            "stage": "lower",
            "input": formula,
            "interpreted": interpreted,
            "error": _client_message("lower", lower_err),
        }

    result["input"] = formula
    result["interpreted"] = interpreted
    result["source"] = source
    result["ok"] = bool(result["verified"])
    if not result["verified"]:
        result["stage"] = "verify"
        result["error"] = "compiled program failed numeric verification"
    return result
