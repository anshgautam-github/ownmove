import React from 'react';

function List({ label, items, tone }) {
  if (!items || items.length === 0) return null;
  const toneCls = {
    default: 'border-white/70 bg-white/55 text-[#1a1a1a]',
    muted: 'border-white/70 bg-white/40 text-[#7a7a76]',
  }[tone || 'default'];
  return (
    <div>
      <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">{label}</p>
      <ul className="flex flex-col gap-1.5">
        {items.map((item) => (
          <li key={item} className={`rounded-[12px] border p-2.5 text-[13px] font-semibold leading-relaxed ${toneCls}`}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Renders `ProblemSolvingContent` — deliberately separates what's known
 * from speculation, never asserts a diagnosis the evidence doesn't
 * support (see backend/app/ai_coach/schemas/coach.py). */
export default function ProblemSolvingCard({ problemSolving }) {
  if (!problemSolving) return null;
  return (
    <div className="flex flex-col gap-3">
      <List label="What we know" items={problemSolving.known} tone="default" />
      <List label="Possible explanations" items={problemSolving.possible_explanations} tone="muted" />
      {problemSolving.recommended_checks.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Worth checking</p>
          <ul className="flex flex-col gap-1.5">
            {problemSolving.recommended_checks.map((item) => (
              <li key={item} className="rounded-[12px] border border-[#7b62e8]/20 bg-[#7b62e8]/5 p-2.5 text-[13px] font-semibold text-[#1a1a1a]">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
      {problemSolving.unknowns.length > 0 && (
        <div>
          <p className="mb-1 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Still unknown</p>
          <p className="text-[12.5px] font-medium leading-relaxed text-[#9a9a97]">{problemSolving.unknowns.join(' · ')}</p>
        </div>
      )}
      {problemSolving.next_action.length > 0 && (
        <div className="rounded-[14px] border border-white/70 bg-white/55 p-3">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Next move</p>
          <ul className="mt-1.5 flex flex-col gap-1">
            {problemSolving.next_action.map((action) => (
              <li key={action} className="text-[13px] font-semibold text-[#1a1a1a]">
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
