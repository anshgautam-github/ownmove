import React from 'react';

/** Shown when the Coach recognizes a request primarily belongs to another
 * specialized Career AI feature (see `RoutingSuggestion` in
 * backend/app/ai_coach/schemas/coach.py). `onNavigateTab` switches the
 * Career AI sidebar to that feature's existing tab — never a fabricated
 * route. */
export default function RoutingCTA({ routing, onNavigateTab }) {
  if (!routing) return null;
  return (
    <div className="flex items-center justify-between gap-3 rounded-[14px] border border-[#7b62e8]/25 bg-[#7b62e8]/5 p-3">
      <p className="text-[12.5px] font-medium leading-relaxed text-[#4a4a48]">{routing.reason}</p>
      {onNavigateTab && (
        <button
          type="button"
          onClick={() => onNavigateTab(routing.feature)}
          className="inline-flex shrink-0 items-center gap-1 rounded-full bg-[#161616] px-3.5 py-1.5 text-[12.5px] font-bold text-white transition hover:bg-[#2a2a2a]"
        >
          {routing.cta_label} →
        </button>
      )}
    </div>
  );
}
