// Minimal complex arithmetic for EML evaluation.
//
// eml(x, y) = exp(x) - ln(y), evaluated over C with the principal branch.
// We mirror numpy.complex128 semantics on the tricky edges — ln(0) = -inf,
// exp(-inf) = 0, branch cut of ln on the negative real axis — so this
// (interactive, client-side) evaluator agrees bit-for-bit with the Python
// authoritative evaluator on the same EML programs.

export interface Complex {
  re: number;
  im: number;
}

export const C = (re: number, im = 0): Complex => ({ re, im });

export const isReal = (z: Complex, eps = 1e-9): boolean => Math.abs(z.im) <= eps;

export function add(a: Complex, b: Complex): Complex {
  return { re: a.re + b.re, im: a.im + b.im };
}

export function sub(a: Complex, b: Complex): Complex {
  return { re: a.re - b.re, im: a.im - b.im };
}

// Principal complex exponential: exp(a+bi) = e^a·(cos b + i·sin b).
// exp(-inf + bi) = 0: the magnitude e^a underflows to 0 regardless of phase.
// This exact case is load-bearing — the EML constructions for negation and
// reciprocal rely on e^{ln 0} = e^{-inf} = 0.
export function exp(z: Complex): Complex {
  if (z.re === -Infinity) return { re: 0, im: 0 };
  const ea = Math.exp(z.re); // may be +Infinity on overflow
  if (z.im === 0) return { re: ea, im: 0 }; // keep the real axis exactly real
  return { re: ea * Math.cos(z.im), im: ea * Math.sin(z.im) };
}

// Principal complex logarithm: ln(z) = ln|z| + i·atan2(im, re).
// ln(0)  = -inf + 0i        (used deliberately as the -inf terminal)
// ln(-1) = 0 + iπ           (branch cut on the negative real axis)
export function log(z: Complex): Complex {
  const mag = Math.hypot(z.re, z.im);
  return { re: Math.log(mag), im: Math.atan2(z.im, z.re) };
}

// The EML operator itself: exp(x) − ln(y).
export function emlOp(x: Complex, y: Complex): Complex {
  return sub(exp(x), log(y));
}
