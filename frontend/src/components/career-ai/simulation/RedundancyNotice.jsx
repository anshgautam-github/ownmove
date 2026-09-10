import React from 'react';

/** Surfaces `redundancy_analysis` explicitly — the feature's core
 * differentiator from a generic "is this activity good" answer. Shown
 * with a distinct visual treatment whenever `is_redundant` is true, so a
 * mostly-repeated action never reads the same as a genuinely new one. */
export default function RedundancyNotice({ redundancy }) {
  if (!redundancy) return null;
  if (!redundancy.is_redundant) {
    return (
      <p className="text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{redundancy.explanation}</p>
    );
  }
  return (
    <div className="rounded-[14px] border border-amber-100 bg-amber-50/60 p-3">
      <p className="text-[11px] font-black uppercase tracking-wide text-amber-700">Likely redundant</p>
      <p className="mt-1 text-[13px] font-medium leading-relaxed text-amber-900">{redundancy.explanation}</p>
    </div>
  );
}
