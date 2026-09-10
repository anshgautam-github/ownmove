import React from 'react';

/**
 * The single highest-impact recommendation, styled as a call-out box (accent
 * gradient border/background) rather than a plain paragraph. Carries the
 * full four-part explanation every recommendation in this report owes the
 * reader: what's missing (`evidence_gap`), why it matters (`reason`), how it
 * affects competitiveness (`impact`), and what to do (`title`).
 */
export default function HighestRoiCard({ recommendation }) {
  if (!recommendation) return null;

  return (
    <div className="relative overflow-hidden rounded-[22px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-5 shadow-[0_16px_36px_-22px_rgba(92,70,201,0.45)]">
      <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.18)_0%,transparent_70%)]" />
      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-[#5c46c9]">Highest ROI recommendation</p>
          <p className="mt-1.5 text-[16.5px] font-black leading-snug tracking-tight text-[#1a1a1a]">
            {recommendation.title}
          </p>
          {recommendation.evidence_gap && (
            <p className="mt-2 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Evidence gap</p>
          )}
          {recommendation.evidence_gap && (
            <p className="mt-0.5 text-[13.5px] font-semibold leading-relaxed text-[#4a4a48]">
              {recommendation.evidence_gap}
            </p>
          )}
          <p className="mt-2.5 text-[13.5px] font-semibold leading-relaxed text-[#4a4a48]">{recommendation.impact}</p>
          <p className="mt-1.5 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{recommendation.reason}</p>
        </div>
        <div className="flex shrink-0 flex-col items-center rounded-[16px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-4 py-3 text-white shadow-[0_10px_24px_-10px_rgba(92,70,201,0.6)]">
          <span className="text-[21px] font-black leading-none">+{recommendation.estimated_score_gain}</span>
          <span className="mt-0.5 text-[9.5px] font-bold uppercase tracking-wide text-white/80">Est. gain</span>
        </div>
      </div>
    </div>
  );
}
