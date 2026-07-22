"""LLM fallback — turn natural-language / messy input into a supported formula.

The model's ONLY job is translation to a formula string; that string is then
re-parsed by the deterministic parser and numerically verified, so the LLM can
never bypass correctness checks. Uses LongCat-2.0 via the OpenAI-compatible API.
"""

from __future__ import annotations

import os

_MODEL = "LongCat-2.0"
_BASE_URL = "https://api.longcat.chat/openai"

_SYSTEM = """You convert a user's mathematical request into ONE formula string.

Use ONLY this grammar:
- numbers, and the operators + - * / ^ (^ is power), parentheses, unary minus
- functions: exp(...), ln(...), sqrt(...)
- constants: e, pi, i (imaginary unit)
- the single variable: x

Rules:
- Output ONLY the formula. No words, no "=", no explanation, no code fences.
- Prefer the operators/functions above; rewrite others in terms of them
  (e.g. "log base e" -> ln, "squared" -> ^2, "reciprocal of y" is not allowed
  since the only variable is x).
- If the request cannot be expressed, output exactly: ERROR

Examples:
the square root of two            -> sqrt(2)
e to the i pi                     -> e^(i*pi)
natural log of x plus one         -> ln(x)+1
two thirds                        -> 2/3
x squared minus 1                 -> x^2-1
"""


def formula_from_nl(text: str, timeout: float = 20.0) -> str:
    """Translate free-form text to a supported formula string. Raises on failure."""
    key = os.environ.get("LONGCAT_API_KEY")
    if not key:
        raise RuntimeError("LONGCAT_API_KEY is not set")

    # Imported lazily so the module (and health route) load even without openai.
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=_BASE_URL, timeout=timeout)
    resp = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=120,
    )
    raw = resp.choices[0].message.content or ""
    # Be tolerant of a chatty model: take the last non-empty line, strip fences.
    lines = [ln.strip().strip("`").strip() for ln in raw.splitlines() if ln.strip()]
    candidate = lines[-1] if lines else ""
    if not candidate or candidate.upper().startswith("ERROR"):
        raise ValueError("could not translate the input into a supported formula")
    return candidate
