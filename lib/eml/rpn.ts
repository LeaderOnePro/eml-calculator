import { EmlNode, one, evar, eml } from "./types";

// EML renders as a single-instruction RPN program. The alphabet is:
//   "1"  push the terminal 1
//   <v>  push a variable terminal (e.g. "x")
//   "E"  pop b, pop a, push eml(a, b)   (a was deeper in the stack)
export const EML_SYMBOL = "E";

/** Tree → postfix token list. */
export function toRpn(node: EmlNode): string[] {
  if (node.t === "one") return ["1"];
  if (node.t === "var") return [node.name];
  return [...toRpn(node.a), ...toRpn(node.b), EML_SYMBOL];
}

/**
 * Compact RPN string, e.g. eml(1, eml(eml(1,x),1)) → "11xE1EE".
 * When every token is a single character we concatenate (matching the paper);
 * multi-character variable names force space separation to stay unambiguous.
 */
export function rpnString(node: EmlNode): string {
  const toks = toRpn(node);
  return toks.every((t) => t.length === 1) ? toks.join("") : toks.join(" ");
}

/** Postfix token list → tree (stack machine). Throws on malformed input. */
export function fromRpn(tokens: string[]): EmlNode {
  const stack: EmlNode[] = [];
  for (const tok of tokens) {
    if (tok === EML_SYMBOL || tok === "eml") {
      const b = stack.pop();
      const a = stack.pop();
      if (a === undefined || b === undefined) {
        throw new Error(`RPN stack underflow at '${tok}'`);
      }
      stack.push(eml(a, b));
    } else if (tok === "1") {
      stack.push(one());
    } else {
      stack.push(evar(tok)); // any other token is a variable name
    }
  }
  if (stack.length !== 1) {
    throw new Error(`RPN did not reduce to one expression (stack size ${stack.length})`);
  }
  return stack[0];
}

/**
 * Parse a compact RPN string. If it contains whitespace we split on it,
 * otherwise each character is its own token (so "11xE1EE" works).
 */
export function parseRpn(s: string): EmlNode {
  const trimmed = s.trim();
  if (trimmed === "") throw new Error("empty RPN string");
  const tokens = /\s/.test(trimmed) ? trimmed.split(/\s+/) : [...trimmed];
  return fromRpn(tokens);
}
