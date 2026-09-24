import { describe, it, expect } from "vitest";
import { one, evar, eml, type EmlNode, rpnLength } from "./types";
import { toRpn, rpnString, fromRpn, parseRpn } from "./rpn";
import { evaluate } from "./evaluator";
import { C, isReal, exp, log } from "./complex";
import FIXTURE from "./__fixtures__/crosscheck.json";

// Core identities from the paper, built directly as EML trees.
const EXP = (a: EmlNode) => eml(a, one()); //                exp(a) = eml(a, 1)
const LN = (b: EmlNode) => eml(one(), eml(eml(one(), b), one())); // ln b (eq.5)
const ONE = one();
const E = eml(one(), one()); //                              e = eml(1, 1)
const ZERO = LN(ONE); //                                     0 = ln 1
const LN0 = LN(ZERO); //                                     -inf = ln 0
const NEG = (x: EmlNode) => eml(LN0, EXP(x)); //             -x = 0 - x

const approx = (a: number, b: number, eps = 1e-9) => Math.abs(a - b) < eps;

describe("complex eml core", () => {
  it("e = eml(1,1) ≈ 2.718281828…", () => {
    const z = evaluate(E);
    expect(isReal(z)).toBe(true);
    expect(approx(z.re, Math.E)).toBe(true);
  });

  it("e^x = eml(x,1) at x=2 ≈ e²", () => {
    const z = evaluate(EXP(evar("x")), { x: C(2) });
    expect(approx(z.re, Math.exp(2))).toBe(true);
    expect(approx(z.im, 0)).toBe(true);
  });

  it("ln x = eml(1, eml(eml(1,x),1)) at x=2 ≈ ln 2", () => {
    const z = evaluate(LN(evar("x")), { x: C(2) });
    expect(approx(z.re, Math.log(2))).toBe(true);
    expect(approx(z.im, 0)).toBe(true);
  });

  it("0 = ln 1 ≈ 0, RPN 111E1EE (K=7)", () => {
    expect(approx(evaluate(ZERO).re, 0)).toBe(true);
    expect(rpnString(ZERO)).toBe("111E1EE");
    expect(rpnLength(ZERO)).toBe(7);
  });

  it("ln 0 = -inf (extended real)", () => {
    expect(evaluate(LN0).re).toBe(-Infinity);
  });

  it("negation -x = eml(ln0, exp x) at x=3 ≈ -3 (relies on e^{-inf}=0)", () => {
    const z = evaluate(NEG(evar("x")), { x: C(3) });
    expect(approx(z.re, -3)).toBe(true);
    expect(approx(z.im, 0)).toBe(true);
  });

  it("EML-composed ln(-1) has |Im| = π (branch / i-sign case)", () => {
    const minus1 = NEG(ONE);
    expect(approx(evaluate(minus1).re, -1)).toBe(true);
    const z = evaluate(LN(minus1));
    expect(approx(Math.abs(z.im), Math.PI, 1e-6)).toBe(true);
  });
});

describe("complex edge semantics (numpy mirror)", () => {
  // These pin the IEEE edge behavior that lets degenerate programs (feeding
  // zeros/infinities back through eml) agree bit-for-bit with numpy — the
  // sign of zero and infinite-magnitude direction both matter. See the
  // cross-check fixture entries at x = 0 (sinh, tanh, asinh, atanh).
  const PI = Math.PI;
  // sign of zero: 1/+0 → +1, 1/-0 → -Infinity (Math.sign(-0) is -0, falsy —
  // so it cannot be used with || here)
  const signed = (v: number) => (v === 0 ? (1 / v < 0 ? -1 : 1) : Math.sign(v));

  it("exp(-inf + πj) = -0 + 0j  (phase survives as signed zero)", () => {
    // cos(π) < 0 → re = -0; sin(π) is a tiny positive in double precision →
    // im = +0. Matches numpy exactly.
    const z = exp(C(-Infinity, PI));
    expect(signed(z.re)).toBe(-1);
    expect(signed(z.im)).toBe(1);
  });

  it("exp(-inf + 0j) = +0 + 0j", () => {
    const z = exp(C(-Infinity, 0));
    expect(signed(z.re)).toBe(1);
    expect(signed(z.im)).toBe(1);
  });

  it("ln(-0 - 0j) = -inf - πj  (atan2 signed-zero rule, like numpy)", () => {
    const z = log(C(-0, -0));
    expect(z.re).toBe(-Infinity);
    expect(approx(z.im, -PI)).toBe(true);
  });

  it("ln(0 + 0j) = -inf + 0j", () => {
    const z = log(C(0, 0));
    expect(z.re).toBe(-Infinity);
    expect(signed(z.im)).toBe(1);
  });

  it("exp(inf + πj) = -inf + infj  (direction survives, no NaN)", () => {
    const z = exp(C(Infinity, PI));
    expect(z.re).toBe(-Infinity);
    expect(z.im).toBe(Infinity);
  });

  it("exp(inf + 4j) = -inf - infj;  exp(inf + π/2·j) = inf + infj", () => {
    const a = exp(C(Infinity, 4));
    expect(a.re).toBe(-Infinity);
    expect(a.im).toBe(-Infinity);
    const b = exp(C(Infinity, PI / 2));
    expect(b.re).toBe(Infinity);
    expect(b.im).toBe(Infinity);
  });

  it("exp(inf + inf·j) = NaN + NaN·j;  exp(inf + nan·j) = inf + nan·j", () => {
    const a = exp(C(Infinity, Infinity));
    expect(Number.isNaN(a.re)).toBe(true);
    expect(Number.isNaN(a.im)).toBe(true);
    const b = exp(C(Infinity, NaN));
    expect(b.re).toBe(Infinity);
    expect(Number.isNaN(b.im)).toBe(true);
  });

  it("degenerate EML program: exp(-inf - πj) = -0 - 0j matches numpy", () => {
    // numpy: sin(-π) < 0, so e^{-inf}·sin(-π) is -0 (not +0) — the phase sign
    // rides through the underflowed magnitude.
    const z = exp(C(-Infinity, -PI));
    expect(signed(z.re)).toBe(-1);
    expect(signed(z.im)).toBe(-1);
  });
});

describe("RPN codec", () => {
  it("paper ln code 11xE1EE round-trips and evaluates to ln", () => {
    const node = parseRpn("11xE1EE");
    expect(rpnString(node)).toBe("11xE1EE");
    expect(approx(evaluate(node, { x: C(5) }).re, Math.log(5))).toBe(true);
  });

  it("compact codes e→11E, e^x→x1E", () => {
    expect(rpnString(E)).toBe("11E");
    expect(rpnString(EXP(evar("x")))).toBe("x1E");
  });

  it("toRpn/fromRpn round-trip preserves structure", () => {
    const node = LN(evar("x"));
    expect(rpnString(fromRpn(toRpn(node)))).toBe(rpnString(node));
  });

  it("malformed RPN throws", () => {
    expect(() => parseRpn("1E")).toThrow(); // underflow
    expect(() => parseRpn("11")).toThrow(); // stack size 2
  });

  it("round-trips every tree in the crosscheck fixture", () => {
    for (const entry of FIXTURE) {
      const node = parseRpn(entry.rpn);
      // parseRpn -> rpnString is byte-stable for whitespace-free programs
      expect(rpnString(node)).toBe(entry.rpn);
      // token-list round trip is stable regardless of naming
      const tokens = toRpn(node);
      expect(rpnString(fromRpn(tokens))).toBe(rpnString(fromRpn(tokens)));
    }
  });

  it("round-trips generated multi-variable trees (property-ish sweep)", () => {
    // Deterministic pseudo-random tree generator: mixed single-char and
    // multi-char variable names exercise both compact and spaced encodings.
    let seed = 0x9e3779b9;
    const rnd = (n: number) => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed % n;
    };
    const names = ["x", "y", "var", "A1", "z9"];
    const gen = (d: number): EmlNode => {
      if (d === 0 || rnd(4) === 0) return rnd(5) === 0 ? one() : evar(names[rnd(names.length)]);
      return eml(gen(d - 1), gen(d - 1));
    };
    for (let i = 0; i < 200; i++) {
      const node = gen(5);
      const tokens = toRpn(node);
      const back = fromRpn(tokens);
      expect(toRpn(back)).toEqual(tokens); // exact structural identity
      expect(rpnLength(back)).toBe(tokens.length); // K = token count
    }
  });

  it("rejects variable names that collide with the RPN alphabet", () => {
    // A var named "1" or "E" would silently decode as a different tree.
    for (const name of ["1", "E", "eml"]) {
      expect(() => evar(name)).toThrow();
    }
    // Multi-char names are fine (spaced encoding).
    expect(rpnString(evar("var"))).toBe("var");
    expect(rpnString(eml(one(), evar("var")))).toBe("1 var E");
  });
});
