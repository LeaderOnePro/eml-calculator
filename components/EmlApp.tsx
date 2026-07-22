"use client";

import { useRef, useState } from "react";
import { one, evar, eml, rpnString, parseRpn, type EmlNode } from "@/lib/eml";
import Calculator, { type PlayRequest } from "./Calculator";

// Build demo programs from the paper's identities so their RPN is correct
// by construction (no hand-copied token strings).
const EXP = (a: EmlNode) => eml(a, one());
const LN = (b: EmlNode) => eml(one(), eml(eml(one(), b), one()));
const ZERO = LN(one());
const LN0 = LN(ZERO);
const NEG = (x: EmlNode) => eml(LN0, EXP(x));

const DEMOS: { label: string; node: EmlNode }[] = [
  { label: "1", node: one() },
  { label: "e", node: eml(one(), one()) },
  { label: "eˣ", node: EXP(evar("x")) },
  { label: "ln x", node: LN(evar("x")) },
  { label: "0", node: ZERO },
  { label: "−1", node: NEG(one()) },
];

export default function EmlApp() {
  const [play, setPlay] = useState<PlayRequest | undefined>();
  const [rpn, setRpn] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const idRef = useRef(0);

  const fire = (program: string) => setPlay({ rpn: program, id: ++idRef.current });

  const runManual = () => {
    try {
      parseRpn(rpn);
      setErr(null);
      fire(rpn);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="grid w-full max-w-4xl gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Calculator play={play} />

      <div className="flex flex-col gap-4">
        <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
          <h2 className="text-sm font-medium text-zinc-300">One-click demos</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Replays the EML program onto the calculator, one button-press at a time.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {DEMOS.map((d) => (
              <button
                key={d.label}
                onClick={() => fire(rpnString(d.node))}
                className="rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-1.5 font-mono text-sm text-zinc-200 transition hover:border-emerald-500/50 hover:text-emerald-300"
                title={rpnString(d.node)}
              >
                {d.label}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
          <h2 className="text-sm font-medium text-zinc-300">Run an RPN program</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Alphabet: <span className="font-mono text-zinc-400">1</span>,{" "}
            <span className="font-mono text-zinc-400">x</span>,{" "}
            <span className="font-mono text-zinc-400">E</span> (=eml). e.g.{" "}
            <span className="font-mono text-zinc-400">11xE1EE</span> = ln x.
          </p>
          <div className="mt-3 flex gap-2">
            <input
              value={rpn}
              onChange={(e) => setRpn(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runManual()}
              placeholder="11xE1EE"
              spellCheck={false}
              className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-black/50 px-3 py-2 font-mono text-sm text-zinc-100 outline-none focus:border-emerald-500/50"
            />
            <button
              onClick={runManual}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
            >
              run
            </button>
          </div>
          {err && <p className="mt-2 text-xs text-red-400">{err}</p>}
        </section>

        <section className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/50 p-5">
          <h2 className="text-sm font-medium text-zinc-400">AI: formula → EML</h2>
          <p className="mt-1 text-xs text-zinc-600">
            Coming next — type any formula and it compiles to a verified button sequence.
          </p>
        </section>
      </div>
    </div>
  );
}
