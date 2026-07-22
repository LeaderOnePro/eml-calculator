import { Complex, C, emlOp } from "./complex";
import { EmlNode } from "./types";

export type Env = Record<string, Complex>;

/** Evaluate an EML tree over C. Variables are looked up in `env`. */
export function evaluate(node: EmlNode, env: Env = {}): Complex {
  switch (node.t) {
    case "one":
      return C(1, 0);
    case "var": {
      const v = env[node.name];
      if (v === undefined) throw new Error(`unbound variable '${node.name}'`);
      return v;
    }
    case "eml":
      return emlOp(evaluate(node.a, env), evaluate(node.b, env));
  }
}
