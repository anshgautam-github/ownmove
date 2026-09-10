import React from 'react';

/**
 * Small shared visual primitives for the Profile Analysis cards.
 *
 * Deliberately self-contained rather than importing Panel/CardHead from
 * pages/AppShell.jsx — those are private, unexported helpers inside an
 * already-large file. Reproducing the same look here (glassy white panel,
 * #161616 black accents, the purple/lavender accent already used for
 * "matches you" badges elsewhere in Discover) keeps this feature visually
 * consistent with the rest of the app without adding a cross-file coupling
 * that AppShell.jsx never signed up for.
 */

export const ACCENT_GRADIENT = 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white';

export function Card({ title, subtitle, icon, action, children, className = '' }) {
  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-[22px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.8)_0%,rgba(255,255,255,0.56)_100%)] p-4 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),inset_0_0_0_1px_rgba(255,255,255,0.3),0_16px_36px_-22px_rgba(40,50,30,0.4)] backdrop-blur-xl ${className}`}
    >
      {(title || icon) && (
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {icon && (
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#161616] text-white">
                {icon}
              </span>
            )}
            <div>
              <p className="text-[15px] font-black tracking-tight text-[#1a1a1a]">{title}</p>
              {subtitle && <p className="text-[12px] font-medium text-[#9a9a97]">{subtitle}</p>}
            </div>
          </div>
          {action}
        </div>
      )}
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

const TONE_CLASSES = {
  high: 'bg-red-50 text-red-600 border border-red-100',
  medium: 'bg-amber-50 text-amber-700 border border-amber-100',
  low: 'bg-slate-100 text-slate-600 border border-slate-200',
  positive: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  warning: 'bg-orange-50 text-orange-700 border border-orange-100',
  accent: ACCENT_GRADIENT,
  default: 'bg-white/80 text-[#4a4a48] border border-white/70',
};

export function Pill({ tone = 'default', children, className = '' }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${TONE_CLASSES[tone] || TONE_CLASSES.default} ${className}`}
    >
      {children}
    </span>
  );
}

/** A short horizontal bar for scores 0-100 — used by trait scores, evidence
 * confidence, and opportunity readiness so all three read the same way. */
export function ScoreBar({ value, label }) {
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className="w-full">
      {label && (
        <div className="mb-1 flex items-center justify-between text-[12px] font-bold">
          <span className="truncate text-[#4a4a48]">{label}</span>
          <span className="text-[#9a9a97]">{clamped}</span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#111827]/8">
        <div
          className="h-full rounded-full bg-[linear-gradient(90deg,#7b62e8_0%,#5c63ff_100%)] transition-[width] duration-500"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

/** The big headline number — used once, at the top of the dashboard. */
export function ScoreRing({ value }) {
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  const circumference = 2 * Math.PI * 42;
  const offset = circumference * (1 - clamped / 100);
  return (
    <div className="relative flex h-28 w-28 shrink-0 items-center justify-center">
      <svg viewBox="0 0 96 96" className="h-full w-full -rotate-90">
        <circle cx="48" cy="48" r="42" fill="none" stroke="rgba(17,24,39,0.08)" strokeWidth="8" />
        <circle
          cx="48"
          cy="48"
          r="42"
          fill="none"
          stroke="url(#score-ring-gradient)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
        <defs>
          <linearGradient id="score-ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#7b62e8" />
            <stop offset="100%" stopColor="#5c63ff" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-[27px] font-black leading-none tracking-tight text-[#161616]">{clamped}</span>
        <span className="text-[10px] font-bold uppercase tracking-wide text-[#9a9a97]">/ 100</span>
      </div>
    </div>
  );
}

export function EmptyRow({ children }) {
  return <p className="text-[13px] font-medium text-[#9a9a97]">{children}</p>;
}

/**
 * A full-width report section: a small numbered label, a title, an optional
 * subtitle, and a hairline divider below the content — this is the layout
 * primitive for the dashboard now, replacing `Card` as the top-level wrapper
 * for each topic (Career DNA, Missing Signals, ...). The point is that the
 * page reads top-to-bottom as one continuous document, the way a recruiter
 * would read an actual report, rather than as a grid of independent tiles
 * you browse in any order. `Card` still exists and is still useful *inside*
 * a section for a bordered callout (a stat box, a pull-quote) — that's
 * normal in a report (tables, sidebars); it's the page-level layout that
 * shouldn't be tiled.
 */
export function ReportSection({ index, title, subtitle, action, children, className = '' }) {
  return (
    <section className={`border-b border-[#111827]/8 py-7 first:pt-0 last:border-b-0 last:pb-0 ${className}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-baseline gap-2.5">
          {index && (
            <span className="text-[12.5px] font-black tracking-wide text-[#b7ade8]" aria-hidden="true">
              {index}
            </span>
          )}
          <div>
            <h2 className="text-[16px] font-black tracking-tight text-[#1a1a1a]">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[12.5px] font-medium text-[#9a9a97]">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
