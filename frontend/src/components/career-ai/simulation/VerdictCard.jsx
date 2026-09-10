import React from 'react';
import { Pill } from '../ui';

const VERDICT_TONE = {
  HIGH_VALUE: 'positive',
  USEFUL: 'accent',
  LIMITED_VALUE: 'warning',
  LOW_VALUE: 'high',
};

const VERDICT_LABEL = {
  HIGH_VALUE: 'High-Value Move',
  USEFUL: 'Useful Move',
  LIMITED_VALUE: 'Limited Value',
  LOW_VALUE: 'Low Value',
};

/** The headline judgment for a single simulation — never a numeric score,
 * always a plain-language level plus grounded reasoning (see
 * career_simulation/schemas/simulation.py's `Verdict`). */
export default function VerdictCard({ verdict }) {
  if (!verdict) return null;
  return (
    <div className="relative overflow-hidden rounded-[22px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-5">
      <Pill tone={VERDICT_TONE[verdict.level] || 'default'}>{VERDICT_LABEL[verdict.level] || verdict.level}</Pill>
      <p className="mt-3 text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">{verdict.reasoning}</p>
    </div>
  );
}
