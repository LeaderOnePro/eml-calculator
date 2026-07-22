import { Complex } from "./complex";

const SNAP = 1e-9;

function fmtNum(x: number, digits: number): string {
  if (Number.isNaN(x)) return "NaN";
  if (x === Infinity) return "∞";
  if (x === -Infinity) return "−∞";
  const r = Math.round(x);
  if (Number.isFinite(r) && Math.abs(x - r) < SNAP) return String(r);
  return parseFloat(x.toPrecision(digits)).toString();
}

/**
 * Human-readable rendering of a complex value. Near-real values collapse to a
 * real number; near-integers snap; infinities render as ∞. Uses the Unicode
 * minus sign for a tidier display.
 */
export function formatComplex(z: Complex, digits = 12): string {
  const imFinite = Number.isFinite(z.im);
  const imNearZero = imFinite && Math.abs(z.im) < SNAP;

  if (imNearZero) return fmtNum(z.re, digits).replace(/^-/, "−");

  const reStr = fmtNum(z.re, digits).replace(/^-/, "−");
  const imAbs = fmtNum(Math.abs(z.im), digits);
  const sign = z.im < 0 ? "−" : "+";

  if (Math.abs(z.re) < SNAP) return `${z.im < 0 ? "−" : ""}${imAbs}i`;
  return `${reStr} ${sign} ${imAbs}i`;
}
