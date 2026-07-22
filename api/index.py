"""EML Calculator backend (FastAPI).

Local dev:  uv run uvicorn api.index:app --port 8000 --reload
Vercel:     deployed as a Python serverless function (entrypoint api.index:app).

All routes are namespaced under /api so they line up with Vercel's /api function
routing and the Next.js dev rewrite (see next.config.ts).
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="EML Calculator API", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "eml-calculator-api"}
