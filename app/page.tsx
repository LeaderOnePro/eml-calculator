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

        <a
          href="https://github.com/LeaderOnePro/eml-calculator"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-5 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-300 transition hover:border-zinc-500 hover:text-white"
        >
          <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          View on GitHub
        </a>
      </header>

      <EmlApp />

      <footer className="mt-10 font-mono text-xs text-zinc-600">
        <a
          href="https://arxiv.org/abs/2603.21852"
          target="_blank"
          rel="noopener noreferrer"
          className="transition hover:text-zinc-400"
        >
          arXiv:2603.21852
        </a>{" "}
        · S → 1 | eml(S, S)
      </footer>
    </main>
  );
}
