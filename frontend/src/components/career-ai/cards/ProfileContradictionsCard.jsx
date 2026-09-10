import React from 'react';
import { EmptyRow } from '../ui';

/**
 * Replaces "Career Blind Spots" with a broader concept: any place the
 * profile's STATED direction (target role, target company, career
 * interests) and its OBSERVED evidence (experiences, skills) measurably
 * disagree — not only a skill-category mismatch. Styled as a coaching
 * callout (stated goal vs. observed evidence, then impact and how to close
 * the gap) so the point is to change what the person does next, not just
 * report a discrepancy.
 */
export default function ProfileContradictionsCard({ contradictions }) {
  const items = contradictions || [];

  if (items.length === 0) {
    return <EmptyRow>No contradictions detected — the stated goal and the logged evidence line up.</EmptyRow>;
  }

  return (
    <div className="flex flex-col gap-4">
      {items.map((item, i) => (
        <div
          key={item.contradiction || i}
          className="relative overflow-hidden rounded-[18px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.06)_0%,rgba(92,99,255,0.06)_100%)] p-4"
        >
          <p className="text-[14px] font-black leading-snug text-[#1a1a1a]">{item.contradiction}</p>

          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>
              <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Stated goal</p>
              <p className="mt-0.5 text-[13px] font-semibold text-[#4a4a48]">{item.stated_goal}</p>
            </div>
            <div>
              <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Observed evidence</p>
              <ul className="mt-0.5 flex flex-col gap-0.5">
                {(item.observed_evidence || []).map((line) => (
                  <li key={line} className="flex items-start gap-1.5 text-[13px] font-semibold text-[#4a4a48]">
                    <span className="mt-0.5 shrink-0 text-[#7b62e8]">✓</span>
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className="mt-3.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Why it matters</p>
          <p className="mt-1 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{item.why_it_matters}</p>

          <p className="mt-3.5 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">How to close the gap</p>
          <p className="mt-1 text-[13.5px] font-bold leading-relaxed text-[#1a1a1a]">{item.how_to_close_gap}</p>
        </div>
      ))}
    </div>
  );
}
