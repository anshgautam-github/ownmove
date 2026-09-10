import React from 'react';

/** Renders `EvaluationContent` — judges something the user described
 * against their own profile, never a summary of what they pasted (see
 * backend/app/ai_coach/schemas/coach.py). */
export default function EvaluationCard({ evaluation }) {
  if (!evaluation) return null;
  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-[18px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-4">
        <p className="text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Verdict</p>
        <p className="mt-1 text-[15px] font-black leading-snug text-[#1a1a1a]">{evaluation.verdict}</p>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-[10px] font-black uppercase tracking-wide text-emerald-700">What it adds</p>
          <ul className="flex flex-col gap-1.5">
            {evaluation.what_it_adds.map((item) => (
              <li key={item} className="rounded-[12px] border border-emerald-100 bg-emerald-50/50 p-2 text-[12.5px] font-semibold text-emerald-900">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1.5 text-[10px] font-black uppercase tracking-wide text-orange-700">What it doesn't</p>
          <ul className="flex flex-col gap-1.5">
            {evaluation.what_it_does_not_add.map((item) => (
              <li key={item} className="rounded-[12px] border border-orange-100 bg-orange-50/50 p-2 text-[12.5px] font-semibold text-orange-900">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="rounded-[14px] border border-white/70 bg-white/55 p-3">
        <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Fit with your goal</p>
        <p className="mt-1 text-[13px] font-semibold leading-relaxed text-[#1a1a1a]">{evaluation.fit_with_goal}</p>
      </div>
      <p className="text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{evaluation.tradeoff}</p>
      <div className="rounded-[14px] border border-white/70 bg-white/40 p-3">
        <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Recommendation</p>
        <p className="mt-1 text-[13px] font-semibold leading-relaxed text-[#1a1a1a]">{evaluation.recommendation}</p>
      </div>
    </div>
  );
}
