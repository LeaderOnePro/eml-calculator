import { describe, it, expect } from "vitest";
import { parseRpn } from "./rpn";
import { evaluate, type Env } from "./evaluator";
import { C } from "./complex";
import fixture from "./__fixtures__/crosscheck.json";

// Each entry was computed by the Python (numpy) evaluator in scripts/gen_crosscheck.py.
// Re-evaluating the same EML program with the TS evaluator must agree — this is
// the guarantee that the client and server cores never drift apart.
type Entry = { rpn: string; x: number | null; re: number; im: number };

describe("TS ↔ Python evaluator cross-check", () => {
  it.each(fixture as Entry[])("$rpn (x=$x) matches Python", (e) => {
    const env: Env = e.x === null ? {} : { x: C(e.x) };
    const z = evaluate(parseRpn(e.rpn), env);
    const err = Math.hypot(z.re - e.re, z.im - e.im);
    const scale = Math.max(1, Math.hypot(e.re, e.im));
    expect(err / scale).toBeLessThan(1e-9);
  });
});
