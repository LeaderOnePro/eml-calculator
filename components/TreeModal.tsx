"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { type EmlNode } from "@/lib/eml";
import { EmlTree } from "./EmlTree";

/**
 * Full-viewport viewer for an EML tree. The tree renders at natural size and
 * is positioned with translate+scale, so pan/zoom never re-renders the tree
 * itself — only the transform on the wrapper changes. Opens fit-to-viewport
 * (a mild no-op for small trees; the only sane default for the ~10k-px-wide
 * trees that constants and AI-compiled programs produce).
 */

type View = { x: number; y: number; scale: number };

const MIN_SCALE = 0.04;
const MAX_SCALE = 2.5;
const ZOOM_STEP = 1.2;

function clampScale(s: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));
}

export default function TreeModal({ node, onClose }: { node: EmlNode; onClose: () => void }) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const [view, setView] = useState<View>({ x: 0, y: 0, scale: 1 });
  const [dirty, setDirty] = useState(false); // user moved → "fit" button lights up
  const drag = useRef<{ px: number; py: number; vx: number; vy: number } | null>(null);

  /** Center the whole tree inside the viewport at the largest scale that fits. */
  const fit = useCallback(() => {
    const vp = viewportRef.current;
    const content = contentRef.current;
    if (!vp || !content) return;
    const bounds = content.getBoundingClientRect();
    const w = bounds.width / view.scale; // natural (unscaled) size
    const h = bounds.height / view.scale;
    const vw = vp.clientWidth;
    const vh = vp.clientHeight;
    const scale = clampScale(Math.min((vw / w) * 0.96, (vh / h) * 0.92, 1.25));
    setView({ x: (vw - w * scale) / 2, y: (vh - h * scale) / 2, scale });
    setDirty(false);
  }, [view.scale]);

  // Reset the view every time a different tree is opened. useLayoutEffect so
  // the tree never paints at the un-fitted default position.
  useLayoutEffect(() => {
    fit();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-fit only when the tree changes
  }, [node]);

  // Esc closes; the calculator's global shortcuts are suspended while the
  // modal is open (see Calculator's keydown guard).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  const zoomAt = useCallback((factor: number, cx: number, cy: number) => {
    setView((v) => {
      const scale = clampScale(v.scale * factor);
      const eff = factor === 1 ? 1 : scale / v.scale;
      return { scale, x: cx - (cx - v.x) * eff, y: cy - (cy - v.y) * eff };
    });
    setDirty(true);
  }, []);

  // Wheel zoom must be a native non-passive listener: React's synthetic
  // onWheel is passive, so preventDefault() inside it cannot stop the page
  // behind the modal from scrolling.
  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = vp.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, e.clientX - rect.left, e.clientY - rect.top);
    };
    vp.addEventListener("wheel", onWheel, { passive: false });
    return () => vp.removeEventListener("wheel", onWheel);
  }, [zoomAt]);

  const onPointerDown = (e: React.PointerEvent) => {
    // Capture on the viewport itself (not e.target, which may be a tree node)
    // so the drag keeps tracking even when the pointer leaves the viewport.
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, vx: view.x, vy: view.y };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    setView((v) => ({ ...v, x: d.vx + (e.clientX - d.px), y: d.vy + (e.clientY - d.py) }));
    setDirty(true);
  };

  const endDrag = () => {
    drag.current = null;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/80 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="EML tree viewer"
    >
      <div className="flex items-center justify-between px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              const rect = viewportRef.current?.getBoundingClientRect();
              if (rect) zoomAt(1 / ZOOM_STEP, rect.width / 2, rect.height / 2);
            }}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-800"
            aria-label="zoom out"
          >
            −
          </button>
          <span className="w-14 text-center font-mono text-xs text-zinc-400">
            {Math.round(view.scale * 100)}%
          </span>
          <button
            onClick={() => {
              const rect = viewportRef.current?.getBoundingClientRect();
              if (rect) zoomAt(ZOOM_STEP, rect.width / 2, rect.height / 2);
            }}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-800"
            aria-label="zoom in"
          >
            +
          </button>
          <button
            onClick={fit}
            className={`rounded-lg border px-3 py-1.5 text-sm transition ${
              dirty
                ? "border-emerald-600/60 text-emerald-300 hover:bg-emerald-600/10"
                : "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            fit
          </button>
          <button
            onClick={() => {
              const rect = viewportRef.current?.getBoundingClientRect();
              if (!rect) return;
              setDirty(true);
              setView((v) => ({
                scale: 1,
                x: (rect.width - (contentRef.current?.getBoundingClientRect().width ?? 0) / v.scale) / 2,
                y: (rect.height - (contentRef.current?.getBoundingClientRect().height ?? 0) / v.scale) / 2,
              }));
            }}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-800"
          >
            100%
          </button>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-800"
          aria-label="close tree viewer"
        >
          ✕ esc
        </button>
      </div>

      <div
        ref={viewportRef}
        className="relative m-4 mt-0 flex-1 cursor-grab touch-none overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 active:cursor-grabbing"
        onClick={(e) => e.stopPropagation()}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <div
          ref={contentRef}
          className="absolute left-0 top-0 origin-top-left p-8"
          style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}
        >
          <EmlTree node={node} />
        </div>
      </div>
    </div>
  );
}
