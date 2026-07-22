// The EML expression tree.  Grammar (paper §4.2):  S → 1 | eml(S, S)
// For functions we add input variables as extra terminal symbols (e.g. x).

export type EmlNode =
  | { t: "one" }
  | { t: "var"; name: string }
  | { t: "eml"; a: EmlNode; b: EmlNode };

export const one = (): EmlNode => ({ t: "one" });
export const evar = (name: string): EmlNode => ({ t: "var", name });
export const eml = (a: EmlNode, b: EmlNode): EmlNode => ({ t: "eml", a, b });

/** Number of leaf terminals (1s and variables). */
export function leaves(node: EmlNode): number {
  return node.t === "eml" ? leaves(node.a) + leaves(node.b) : 1;
}

/**
 * RPN program length K = total token count.  A full binary tree with L leaves
 * has L−1 internal (eml) nodes, so K = 2L − 1.  This matches the paper's K
 * (e.g. ln x → `11xE1EE`, K = 7).
 */
export function rpnLength(node: EmlNode): number {
  return 2 * leaves(node) - 1;
}

/** Depth of the tree (a single leaf has depth 0). */
export function depth(node: EmlNode): number {
  return node.t === "eml" ? 1 + Math.max(depth(node.a), depth(node.b)) : 0;
}

/** Set of variable names appearing in the tree. */
export function variables(node: EmlNode): Set<string> {
  const s = new Set<string>();
  const walk = (n: EmlNode) => {
    if (n.t === "var") s.add(n.name);
    else if (n.t === "eml") {
      walk(n.a);
      walk(n.b);
    }
  };
  walk(node);
  return s;
}
