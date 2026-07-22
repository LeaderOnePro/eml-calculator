import type { EmlNode } from "@/lib/eml";

// Top-down view of an EML tree. `eml` nodes are green, `1` terminals grey,
// variables blue. Deep trees (functions) get wide — wrap in an overflow box.
export function EmlTree({ node }: { node: EmlNode }) {
  return <div className="inline-flex justify-center">{render(node)}</div>;
}

function render(node: EmlNode) {
  if (node.t === "one") return <Leaf label="1" kind="one" />;
  if (node.t === "var") return <Leaf label={node.name} kind="var" />;
  return (
    <div className="flex flex-col items-center">
      <div className="rounded-md border border-emerald-500/40 bg-emerald-500/15 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
        eml
      </div>
      <div className="mt-1 flex items-start gap-2 border-t border-zinc-700 pt-2">
        <div className="flex flex-col items-center">{render(node.a)}</div>
        <div className="flex flex-col items-center">{render(node.b)}</div>
      </div>
    </div>
  );
}

function Leaf({ label, kind }: { label: string; kind: "one" | "var" }) {
  const cls =
    kind === "var"
      ? "border-sky-500/40 bg-sky-500/15 text-sky-300"
      : "border-zinc-600/50 bg-zinc-700/40 text-zinc-200";
  return (
    <div className={`rounded-md border px-2 py-0.5 font-mono text-[11px] ${cls}`}>
      {label}
    </div>
  );
}
