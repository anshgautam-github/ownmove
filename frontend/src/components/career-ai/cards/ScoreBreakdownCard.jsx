import React from 'react';
import { EmptyRow } from '../ui';

function FactorRow({ factor }) {
  const positive = factor.points >= 0;
  return (
    <div className="flex items-start justify-between gap-3 border-b border-white/60 py-2.5 last:border-b-0">
      <div className="min-w-0 flex-1">
        <p className="text-[13.5px] font-bold text-[#1a1a1a]">{factor.label}</p>
        <p className="mt-0.5 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{factor.reason}</p>
      </div>
      <span className={`shrink-0 text-[14.5px] font-black ${positive ? 'text-[#22a06b]' : 'text-[#b34747]'}`}>
        {positive ? '+' : ''}
        {factor.points}
      </span>
    </div>
  );
}

/**
 * New section — exactly why `overall_score` is what it is. Rendered as an
 * itemized bill (a base number, then every positive and negative factor
 * that was added or subtracted), so the total is always visibly the sum of
 * the lines above it rather than an opaque number the reader has to trust.
 * This is possible because `utils/scoring.py::reconcile()` computes this
 * breakdown from the same evidence/signals/gaps every other section shows —
 * it isn't a separate, potentially-inconsistent explanation.
 */
export default function ScoreBreakdownCard({ breakdown }) {
  if (!breakdown) {
    return <EmptyRow>No score breakdown generated yet.</EmptyRow>;
  }

  const positive = breakdown.positive_factors || [];
  const negative = breakdown.negative_factors || [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between rounded-[16px] border border-white/70 bg-white/55 px-4 py-3">
        <span className="text-[12.5px] font-bold uppercase tracking-wide text-[#9a9a97]">Baseline</span>
        <span className="text-[16.5px] font-black text-[#1a1a1a]">{breakdown.base_score}</span>
      </div>

      {positive.length > 0 && (
        <div>
          <p className="mb-1 text-[10.5px] font-black uppercase tracking-wide text-[#22a06b]">Positive factors</p>
          <div className="rounded-[16px] border border-white/70 bg-white/55 px-4">
            {positive.map((factor) => (
              <FactorRow key={factor.label} factor={factor} />
            ))}
          </div>
        </div>
      )}

      {negative.length > 0 && (
        <div>
          <p className="mb-1 text-[10.5px] font-black uppercase tracking-wide text-[#b34747]">Negative factors</p>
          <div className="rounded-[16px] border border-white/70 bg-white/55 px-4">
            {negative.map((factor) => (
              <FactorRow key={factor.label} factor={factor} />
            ))}
          </div>
        </div>
      )}

      {positive.length === 0 && negative.length === 0 && (
        <EmptyRow>No scoring factors identified — the score is sitting at its neutral baseline.</EmptyRow>
      )}

      <div className="flex items-center justify-between rounded-[16px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] px-4 py-3">
        <span className="text-[12.5px] font-black uppercase tracking-wide text-[#5c46c9]">Final score</span>
        <span className="text-[18px] font-black text-[#1a1a1a]">{breakdown.final_score}</span>
      </div>
    </div>
  );
}
