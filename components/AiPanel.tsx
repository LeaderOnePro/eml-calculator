"use client";

import { useState } from "react";

type CompileResult = {
  ok: boolean;
  input?: string;
  interpreted?: string;
  rpn?: string;
  k?: number;
  depth?: number;
  variables?: string[];
  verified?: boolean;
  value?: { re: number; im: number };
  source?: string;
  error?: string;
  stage?: string;
};

const EXAMPLES = ["ln(2)", "e^x", "2*3", "x^2", "sqrt(2)", "pi", "i", "e^(i*pi)"];

function fmtValue(v: { re: number; im: number }): string {
  const snap = (x: number) =>
    Math.abs(x) < 1e-9
      ? 0
      : Math.abs(x - Math.round(x)) < 1e-9
        ? Math.round(x)
        : parseFloat(x.toPrecision(8));
  const re = snap(v.re);
  const im = snap(v.im);
  if (im === 0) return String(re);
  if (re === 0) return `${im}i`;
  return `${re} ${im < 0 ? "−" : "+"} ${Math.abs(im)}i`;
}

export default function AiPanel({ onCompiled }: { onCompiled: (rpn: string) => void }) {
  const [formula, setFormula] = useState("");
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<CompileResult | null>(null);

  const compile = async (f?: string) => {
    const input = (f ?? formula).trim();
    if (!input) return;
    if (f) setFormula(f);
    setLoading(true);
    setRes(null);
    try {
      const r = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ formula: input }),
      });
      setRes(await r.json());
    } catch (e) {
      setRes({ ok: false, error: String(e), stage: "network" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-emerald-900/40 bg-zinc-950 p-5">
      <h2 className="text-sm font-medium text-zinc-200">AI: formula → EML</h2>
      <p className="mt-1 text-xs text-zinc-500">
        Type any formula; it compiles to a numerically-verified button sequence.
      </p>

      <div className="mt-3 flex gap-2">
        <input
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && compile()}
          placeholder="e^(i*pi)"
          spellCheck={false}
          className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-black/50 px-3 py-2 font-mono text-sm text-zinc-100 outline-none focus:border-emerald-500/60"
        />
        <button
          onClick={() => compile()}
          disabled={loading}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? "…" : "compile"}
        </button>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => compile(ex)}
            className="rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 font-mono text-xs text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-200"
          >
            {ex}
          </button>
        ))}
      </div>

      {res && (
        <div className="mt-4 rounded-xl border border-zinc-800 bg-black/40 p-4">
          {res.ok ? (
            <>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  verified{res.source === "llm" ? " · via AI" : ""}
                </span>
                <span className="font-mono text-xs text-zinc-500">
                  K={res.k} · depth={res.depth}
                </span>
              </div>
              {res.source === "llm" && res.interpreted && (
                <div className="mt-1 text-xs text-zinc-500">
                  read as <span className="font-mono text-zinc-300">{res.interpreted}</span>
                </div>
              )}
              {res.value && (
                <div className="mt-2 font-mono text-2xl text-emerald-300">{fmtValue(res.value)}</div>
              )}
              {res.variables && res.variables.length > 0 && (
                <div className="mt-2 font-mono text-sm text-sky-300">ƒ({res.variables.join(", ")})</div>
              )}
              <div className="mt-2 break-all font-mono text-[11px] leading-relaxed text-zinc-500">
                {res.rpn}
              </div>
              <button
                onClick={() => res.rpn && onCompiled(res.rpn)}
                className="mt-3 rounded-lg border border-emerald-600/50 bg-emerald-600/10 px-3 py-1.5 text-sm text-emerald-300 transition hover:bg-emerald-600/20"
              >
                ▶ play on calculator
              </button>
            </>
          ) : (
            <div className="text-sm text-red-400">
              <span className="font-medium">couldn’t compile</span>
              {res.stage && <span className="ml-1 text-xs text-red-400/70">({res.stage})</span>}
              <div className="mt-1 font-mono text-xs text-red-300/80">{res.error}</div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
