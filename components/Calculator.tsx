"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type EmlNode,
  one,
  evar,
  eml,
  rpnString,
  rpnLength,
  depth,
  evaluate,
  formatComplex,
  variables,
} from "@/lib/eml";
import { EmlTree } from "./EmlTree";

export type PlayRequest = { rpn: string; id: number };

export default function Calculator({ play }: { play?: PlayRequest }) {
  const [stack, setStack] = useState<EmlNode[]>([]);
  const [past, setPast] = useState<EmlNode[][]>([]);
  const [showTree, setShowTree] = useState(true);
  const playTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const top = stack[stack.length - 1] as EmlNode | undefined;
  const canEml = stack.length >= 2;

  const commit = useCallback(
    (next: EmlNode[]) => {
      setPast((p) => [...p, stack]);
      setStack(next);
    },
    [stack],
  );

  const push1 = useCallback(() => commit([...stack, one()]), [stack, commit]);

  const doEml = useCallback(() => {
    if (stack.length < 2) return;
    const a = stack[stack.length - 2];
    const b = stack[stack.length - 1];
    commit([...stack.slice(0, -2), eml(a, b)]);
  }, [stack, commit]);

  const undo = useCallback(() => {
    setPast((p) => {
      if (p.length === 0) return p;
      setStack(p[p.length - 1]);
      return p.slice(0, -1);
    });
  }, []);

  const clear = useCallback(() => commit([]), [commit]);

  // Keyboard: 1 pushes, e/Enter applies eml, Backspace undoes, Esc clears.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "1") (e.preventDefault(), push1());
      else if (e.key === "e" || e.key === "Enter") (e.preventDefault(), doEml());
      else if (e.key === "Backspace") (e.preventDefault(), undo());
      else if (e.key === "Escape") (e.preventDefault(), clear());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [push1, doEml, undo, clear]);

  // "One-click demo": replay an RPN program token-by-token onto the calculator.
  useEffect(() => {
    if (!play) return;
    if (playTimer.current) clearInterval(playTimer.current);
    const s = play.rpn.trim();
    const tokens = /\s/.test(s) ? s.split(/\s+/) : [...s];
    // Adaptive speed: short programs animate slowly (~220ms/press); large ones
    // (a trig function can be hundreds of presses) finish within ~5s total.
    const interval = Math.max(8, Math.min(220, Math.round(5000 / tokens.length)));
    setPast([]);
    setStack([]);
    const built: EmlNode[] = [];
    let i = 0;
    playTimer.current = setInterval(() => {
      const tok = tokens[i++];
      if (tok === undefined) {
        if (playTimer.current) clearInterval(playTimer.current);
        return;
      }
      if (tok === "E" || tok === "eml") {
        const b = built.pop();
        const a = built.pop();
        if (a && b) built.push(eml(a, b));
      } else if (tok === "1") built.push(one());
      else built.push(evar(tok));
      setStack([...built]);
    }, interval);
    return () => {
      if (playTimer.current) clearInterval(playTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [play?.id]);

  const display = useMemo(() => {
    if (!top) return { value: "0", hint: "press 1 to begin", isFunc: false };
    const vars = variables(top);
    if (vars.size > 0)
      return { value: `ƒ(${[...vars].join(", ")})`, hint: "a function — try it in the AI panel", isFunc: true };
    try {
      return { value: formatComplex(evaluate(top)), hint: "", isFunc: false };
    } catch {
      return { value: "undefined", hint: "", isFunc: false };
    }
  }, [top]);

  return (
    <div className="w-full min-w-0 max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-5 shadow-2xl">
      {/* value display */}
      <div className="rounded-xl bg-black/60 px-5 py-6 ring-1 ring-inset ring-zinc-800">
        <div className="flex items-baseline justify-between">
          <span className="text-[11px] uppercase tracking-widest text-zinc-500">value</span>
          {top && (
            <span className="font-mono text-[11px] text-zinc-500">
              K={rpnLength(top)} · depth={depth(top)}
            </span>
          )}
        </div>
        <div
          className={`mt-1 truncate font-mono ${
            display.isFunc ? "text-sky-300" : "text-emerald-300"
          } ${display.value.length > 14 ? "text-2xl sm:text-3xl" : "text-3xl sm:text-5xl"}`}
          title={display.value}
        >
          {display.value}
        </div>
        <div className="mt-2 h-5 truncate font-mono text-sm text-zinc-500">
          {top ? rpnString(top) : display.hint}
        </div>
      </div>

      {/* stack */}
      <div className="mt-3 flex min-h-9 flex-wrap items-center gap-1.5">
        {stack.length === 0 && <span className="text-xs text-zinc-600">stack empty</span>}
        {stack.map((n, i) => {
          const isTop = i === stack.length - 1;
          const label = variables(n).size
            ? "ƒ"
            : (() => {
                try {
                  return formatComplex(evaluate(n), 6);
                } catch {
                  return "·";
                }
              })();
          return (
            <span
              key={i}
              className={`rounded-md border px-2 py-1 font-mono text-xs ${
                isTop
                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                  : "border-zinc-700 bg-zinc-800/50 text-zinc-400"
              }`}
              title={rpnString(n)}
            >
              {label}
            </span>
          );
        })}
      </div>

      {/* the two buttons */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <button
          onClick={push1}
          className="group flex flex-col items-center rounded-xl bg-zinc-800 py-6 text-zinc-100 transition active:scale-[0.98] hover:bg-zinc-700"
        >
          <span className="font-mono text-4xl">1</span>
          <span className="mt-1 text-[11px] text-zinc-500">push terminal</span>
        </button>
        <button
          onClick={doEml}
          disabled={!canEml}
          className="group flex flex-col items-center rounded-xl bg-emerald-600 py-6 text-white transition active:scale-[0.98] enabled:hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
        >
          <span className="font-mono text-4xl">eml</span>
          <span className="mt-1 text-[11px] text-emerald-100/70 group-disabled:text-zinc-600">
            exp(a) − ln(b)
          </span>
        </button>
      </div>

      {/* utilities */}
      <div className="mt-3 flex items-center justify-between text-sm">
        <div className="flex gap-2">
          <button
            onClick={undo}
            disabled={past.length === 0}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-zinc-300 transition enabled:hover:bg-zinc-800 disabled:opacity-40"
          >
            ↶ undo
          </button>
          <button
            onClick={clear}
            disabled={stack.length === 0}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-zinc-300 transition enabled:hover:bg-zinc-800 disabled:opacity-40"
          >
            clear
          </button>
        </div>
        <button
          onClick={() => setShowTree((v) => !v)}
          className="rounded-lg px-3 py-1.5 text-zinc-500 transition hover:text-zinc-300"
        >
          {showTree ? "hide tree" : "show tree"}
        </button>
      </div>

      {/* tree */}
      {showTree && top && (
        <div className="mt-3 max-h-56 overflow-auto rounded-xl border border-zinc-800 bg-black/40 p-4">
          <EmlTree node={top} />
        </div>
      )}
    </div>
  );
}
