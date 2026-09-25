# EML Calculator

A scientific calculator with **exactly two buttons** — `1` and `eml` — plus an AI
assistant that compiles any formula into a verified sequence of button presses.

**▶ Live demo — [eml-calculator.vercel.app](https://eml-calculator.vercel.app)**

It's built on a striking result: the single binary operator

```
eml(x, y) = exp(x) − ln(y)
```

together with the constant `1`, generates the entire scientific‑calculator
repertoire. Every elementary function becomes a binary tree of this one operator
(grammar `S → 1 | eml(S, S)`).

> Based on **A. Odrzywołek, _All elementary functions from a single operator_**,
> arXiv:2603.21852 (2026).

For example:

| function | EML | RPN |
| --- | --- | --- |
| `e`   | `eml(1, 1)` | `11E` |
| `eˣ`  | `eml(x, 1)` | `x1E` |
| `ln x`| `eml(1, eml(eml(1, x), 1))` | `11xE1EE` |

## How it works

- **Two‑button calculator** — an RPN stack machine. `1` pushes a terminal; `eml`
  pops two operands `a, b` and pushes `eml(a, b)`. The running value is evaluated
  live over ℂ on the principal branch (with the extended‑real edges the paper
  needs: `ln 0 = −∞`, `e^{−∞} = 0`).
- **AI: formula → EML** — a deterministic grammar parser handles well‑formed input
  (`sin(x)+2`, `sqrt(2)`, `e^(i*pi)`); only genuinely messy / natural‑language
  input falls back to an LLM (**Agnes 3.0 Flash**). Either way the result is lowered by
  the same deterministic compiler and **numerically verified** against a reference
  evaluator before it's shown — the compiler never returns an unverified program.

## Architecture

```
Client — Next.js / React / TS          Server — Python (FastAPI, uv)
  lib/eml/     interactive EML core       emlcore/   authoritative EML core
  components/  two-button calculator         tree · evaluate (numpy) · mathast
  app/         page                          lower · verify · compile
                                           api/index.py   /api endpoints
```

The client evaluator (`lib/eml`) and the server evaluator (`emlcore`) mirror each
other bit‑for‑bit on the same programs; a cross‑check keeps them honest.
Deployed as a single Vercel project (Next.js frontend + Python serverless `/api`).

## Development

Prerequisites: `pnpm`, and [`uv`](https://docs.astral.sh/uv/) for Python.

```bash
pnpm install            # frontend deps
uv sync                 # backend deps (Python 3.12 venv + lockfile)

# run both (two terminals):
uv run uvicorn api.index:app --port 8000 --reload   # backend
pnpm dev                                            # frontend → http://localhost:3000
```

In dev, Next.js proxies `/api/*` to the local backend (see `next.config.ts`), so
the browser makes same‑origin requests.

### Testing

```bash
pnpm test                 # TS core (vitest)
uv run pytest             # Python core (golden tests)
uv run ruff check .       # Python lint (CI enforces this + ruff format --check)
```

### Configuration

The LLM fallback uses **Agnes 3.0 Flash** via its OpenAI-compatible API
(`https://apihub.agnes-ai.com/v1`). The key is server-side only:

```bash
export AGNES_API_KEY=...        # or copy .env.example → .env.local
```

## Deploy

One Vercel project serves both the Next.js frontend and the Python API. The
FastAPI app in `api/index.py` becomes a single serverless function; `vercel.json`
rewrites `/api/*` to it, and Python dependencies come from `pyproject.toml` +
`uv.lock`. Set `AGNES_API_KEY` in the project's environment variables.

> Deployed and verified end-to-end at
> [eml-calculator.vercel.app](https://eml-calculator.vercel.app): the frontend, the
> Python `/api` serverless function, and the LLM fallback all work in production.
> Pushes to `main` auto-deploy via the Vercel–GitHub integration.

## Credits

- **A. Odrzywołek**, _All elementary functions from a single operator_,
  arXiv:2603.21852 (2026) — the single-operator result this is built on.
- The integer (binary double-and-add) construction and the inverse-function
  log-forms are adopted from the author's reference implementation,
  [VA00/SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage)
  (MIT). Every construction is independently re-checked here by the numeric verifier.

## License

MIT
