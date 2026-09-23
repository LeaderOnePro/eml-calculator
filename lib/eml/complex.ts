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
// This is a deliberate mirror of numpy's C99-style edge semantics so the
// interactive evaluator agrees bit-for-bit with the authoritative one on
// degenerate programs (those that feed zeros/infinities back through eml):
//   re = -inf  → magnitude 0; the phase survives only as the sign of zero
//                (e^{-inf}·cos π = -0), which ln() then turns into -inf ∓ πj
//                via atan2(∓0, -0). Load-bearing for negation/reciprocal.
//   re = +inf  → no finite value, but the direction survives: re/im are
//                ±inf/±0 per the signs of cos(b)/sin(b), never NaN.
export function exp(z: Complex): Complex {
  const ea = Math.exp(z.re); // 0 for re = -Infinity, +Infinity on overflow
  if (ea === Infinity) {
    if (Number.isNaN(z.im)) return { re: Infinity, im: NaN }; // exp(inf, nan)
    if (!Number.isFinite(z.im)) return { re: NaN, im: NaN }; // exp(inf, ±inf)
    if (z.im === 0) return { re: Infinity, im: 0 }; // exp(±0 phase) → +0 phase
    const c = Math.cos(z.im);
    const s = Math.sin(z.im);
    return {
      re: c < 0 ? -Infinity : Infinity,
      im: s < 0 ? -Infinity : s > 0 ? Infinity : 0,
    };
  }
  if (ea === 0) {
    if (z.im === 0 || !Number.isFinite(z.im)) return { re: 0, im: 0 };
    // ±0 per phase: 0·cos(π) = -0, 0·sin(π) = +0 (sin(π) is a tiny positive),
    // matching numpy where the phase survives the underflowed magnitude only
    // through the sign of zero.
    return { re: 0 * Math.cos(z.im), im: 0 * Math.sin(z.im) };
  }
  if (z.im === 0) {
    // real axis stays exactly real (finite ea keeps the ±0 sign of the phase)
    return { re: ea, im: ea * z.im };
  }
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
