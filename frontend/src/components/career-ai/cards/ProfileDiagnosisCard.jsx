import React from 'react';
import { EmptyRow } from '../ui';

/**
 * Replaces "Executive Summary". A diagnosis, not a biography: leads with the
 * single strongest evidenced signal and the single biggest limiting factor
 * side by side (so the reader sees the real trade-off immediately, not just
 * a flattering paragraph), then names where the next unit of effort would
 * move the score most, and finally the one narrative paragraph the whole
 * report allows itself — consistent with, not separate from, the three
 * verdicts above it.
 */
export default function ProfileDiagnosisCard({ diagnosis }) {
  if (!diagnosis) {
    return <EmptyRow>No diagnosis generated yet.</EmptyRow>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[16px] border border-emerald-100 bg-emerald-50/60 p-4">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-emerald-700">Strongest signal</p>
          <p className="mt-1 text-[14.5px] font-black leading-snug text-[#1a1a1a]">{diagnosis.strongest_signal}</p>
          {(diagnosis.strongest_signal_evidence || []).length > 0 && (
            <ul className="mt-2 flex flex-col gap-1">
              {diagnosis.strongest_signal_evidence.map((line) => (
                <li key={line} className="flex items-start gap-1.5 text-[12.5px] font-semibold text-[#4a4a48]">
                  <span className="mt-0.5 shrink-0 text-emerald-600">+</span>
                  {line}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[16px] border border-red-100 bg-red-50/50 p-4">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-[#b34747]">Limiting factor</p>
          <p className="mt-1 text-[14.5px] font-black leading-snug text-[#1a1a1a]">{diagnosis.limiting_factor}</p>
          {(diagnosis.limiting_factor_evidence || []).length > 0 && (
            <ul className="mt-2 flex flex-col gap-1">
              {diagnosis.limiting_factor_evidence.map((line) => (
                <li key={line} className="flex items-start gap-1.5 text-[12.5px] font-semibold text-[#4a4a48]">
                  <span className="mt-0.5 shrink-0 text-[#b34747]">−</span>
                  {line}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="rounded-[16px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.06)_0%,rgba(92,99,255,0.06)_100%)] p-4">
        <p className="text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Highest-impact area</p>
        <p className="mt-1 text-[14.5px] font-black leading-snug text-[#1a1a1a]">{diagnosis.highest_impact_area}</p>
        <p className="mt-1.5 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{diagnosis.highest_impact_reason}</p>
      </div>

      {diagnosis.summary && (
        <p className="rounded-[16px] border border-white/70 bg-white/55 p-4 text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">
          {diagnosis.summary}
        </p>
      )}
    </div>
  );
}
