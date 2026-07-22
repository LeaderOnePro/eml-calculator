import { describe, it, expect } from "vitest";
import { one, evar, eml, type EmlNode, rpnLength } from "./types";
import { toRpn, rpnString, fromRpn, parseRpn } from "./rpn";
import { evaluate } from "./evaluator";
import { C, isReal } from "./complex";

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
});
