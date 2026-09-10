import React from 'react';
import { Pill, EmptyRow } from '../ui';

/** Recruiter signals the profile is missing (not "skills"). Beyond the "why
 * this matters" reasoning, each gap now also states its expected score
 * impact (the same number the Score Breakdown and Growth Simulator sections
 * use — not a separate made-up figure) and which kinds of opportunities are
 * most likely to notice it, so the severity badge isn't the only signal of
 * how much this is worth fixing. */
export default function MissingSignalsCard({ missingSignals }) {
  const signals = missingSignals || [];

  if (signals.length === 0) {
    return <EmptyRow>No major gaps detected — nice work.</EmptyRow>;
  }

  return (
    <div className="flex flex-col gap-4">
      {signals.map((signal) => (
        <div key={signal.title} className="rounded-[16px] border border-white/70 bg-white/55 p-4">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[14.5px] font-black text-[#1a1a1a]">{signal.title}</span>
            <div className="flex shrink-0 items-center gap-1.5">
              <Pill tone="accent">+{signal.expected_score_impact} pts</Pill>
              <Pill tone={signal.importance}>{signal.importance} priority</Pill>
            </div>
          </div>

          <p className="mt-2.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Why this matters</p>
          <p className="mt-1 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{signal.why_it_matters}</p>

          {(signal.affected_opportunities || []).length > 0 && (
            <>
              <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
                Who notices this
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {signal.affected_opportunities.map((opportunity) => (
                  <Pill key={opportunity} tone="default" className="normal-case">
                    {opportunity}
                  </Pill>
                ))}
              </div>
            </>
          )}

          <p className="mt-3.5 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Next step</p>
          <p className="mt-1 text-[13.5px] font-bold leading-relaxed text-[#1a1a1a]">{signal.recommended_action}</p>
        </div>
      ))}
    </div>
  );
}
