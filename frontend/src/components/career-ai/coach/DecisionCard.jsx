import React from 'react';

/** Renders `DecisionContent` — used for decision, prioritization, and
 * preparation intents (see backend/app/ai_coach/schemas/coach.py). Uses
 * hierarchy rather than a flat stack of identical cards: the
 * recommendation leads, everything else supports it. */
export default function DecisionCard({ decision }) {
  if (!decision) return null;
  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-[18px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-4">
        <p className="text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Recommendation</p>
        <p className="mt-1 text-[15px] font-black leading-snug text-[#1a1a1a]">{decision.answer.headline}</p>
        {decision.answer.summary && (
          <p className="mt-1.5 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{decision.answer.summary}</p>
        )}
      </div>

      {decision.reasoning_factors.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Why this fits your situation</p>
          <ul className="flex flex-col gap-1.5">
            {decision.reasoning_factors.map((f) => (
              <li key={f.factor} className="rounded-[12px] border border-white/70 bg-white/55 p-2.5">
                <p className="text-[13px] font-black text-[#1a1a1a]">{f.factor}</p>
                <p className="mt-0.5 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{f.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.tradeoff && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="rounded-[12px] border border-emerald-100 bg-emerald-50/50 p-2.5">
            <p className="text-[10px] font-black uppercase tracking-wide text-emerald-700">Gain</p>
            <p className="mt-0.5 text-[12.5px] font-medium leading-relaxed text-emerald-900">{decision.tradeoff.gain}</p>
          </div>
          <div className="rounded-[12px] border border-orange-100 bg-orange-50/50 p-2.5">
            <p className="text-[10px] font-black uppercase tracking-wide text-orange-700">Cost</p>
            <p className="mt-0.5 text-[12.5px] font-medium leading-relaxed text-orange-900">{decision.tradeoff.cost}</p>
          </div>
        </div>
      )}

      {decision.next_action.length > 0 && (
        <div className="rounded-[14px] border border-white/70 bg-white/55 p-3">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Next move</p>
          <ul className="mt-1.5 flex flex-col gap-1">
            {decision.next_action.map((action, i) => (
              <li key={action} className="flex gap-2 text-[13px] font-semibold text-[#1a1a1a]">
                <span className="text-[#9a9a97]">{i + 1}.</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.what_would_change_my_recommendation.length > 0 && (
        <details className="rounded-[14px] border border-white/70 bg-white/40 p-3">
          <summary className="cursor-pointer text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
            What would change this advice?
          </summary>
          <ul className="mt-2 flex flex-col gap-1">
            {decision.what_would_change_my_recommendation.map((item) => (
              <li key={item} className="text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">
                • {item}
              </li>
            ))}
          </ul>
        </details>
      )}

      {decision.uncertainties.filter(Boolean).length > 0 && (
        <p className="text-[12px] font-medium italic text-[#9a9a97]">
          {decision.uncertainties.filter(Boolean).join(' ')}
        </p>
      )}
    </div>
  );
}
