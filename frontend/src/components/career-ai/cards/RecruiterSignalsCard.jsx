import React from 'react';
import { Pill, EmptyRow } from '../ui';

const STATUS_TONE = {
  Strong: 'positive',
  Moderate: 'medium',
  Limited: 'warning',
  Missing: 'high',
  Unknown: 'low',
};

/**
 * Replaces "Evidence Credibility". This platform never verifies external
 * evidence — it does not check the actual contents of a GitHub repo, a
 * resume file, or a LinkedIn profile — so this section makes no
 * verification claim. It names a fixed set of things a recruiter is likely
 * to notice scanning the profile during an initial review, each with a
 * named status tier (never a percentage) derived only from what's
 * observable in the profile's own stated fields. "Unknown" is a normal,
 * honest status, not an error — it means the profile doesn't contain enough
 * information to judge that signal either way.
 */
export default function RecruiterSignalsCard({ signals }) {
  const items = signals || [];

  if (items.length === 0) {
    return <EmptyRow>No recruiter signals evaluated yet.</EmptyRow>;
  }

  return (
    <div className="flex flex-col gap-4">
      {items.map((signal) => (
        <div key={signal.signal} className="rounded-[16px] border border-white/70 bg-white/55 p-4">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[14.5px] font-black text-[#1a1a1a]">{signal.signal}</span>
            <Pill tone={STATUS_TONE[signal.status] || 'default'}>{signal.status}</Pill>
          </div>
          <p className="mt-2.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Why it matters</p>
          <p className="mt-1 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{signal.why_it_matters}</p>
          <p className="mt-3.5 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Recommended action</p>
          <p className="mt-1 text-[13.5px] font-bold leading-relaxed text-[#1a1a1a]">{signal.recommended_action}</p>
        </div>
      ))}
    </div>
  );
}
