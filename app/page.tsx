import EmlApp from "@/components/EmlApp";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center bg-zinc-900 px-4 py-10 text-zinc-100 sm:py-16">
      <header className="mb-8 max-w-4xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-xs text-zinc-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          two buttons compute everything
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">EML Calculator</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-zinc-400">
          A scientific calculator with exactly two keys —{" "}
          <span className="font-mono text-zinc-200">1</span> and{" "}
          <span className="font-mono text-emerald-300">eml</span>, where{" "}
          <span className="font-mono text-zinc-200">eml(x, y) = exp(x) − ln(y)</span>. Every
          elementary function is a binary tree of this one operator (Odrzywołek, 2026).
        </p>
      </header>

      <EmlApp />

      <footer className="mt-10 font-mono text-xs text-zinc-600">
        arXiv:2603.21852 · S → 1 | eml(S, S)
      </footer>
    </main>
  );
}
