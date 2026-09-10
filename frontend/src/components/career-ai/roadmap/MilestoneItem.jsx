import React from 'react';

/** The single checkpoint that closes out a phase. `completion_criteria` is
 * now a list of concrete, observable checks (was a single free-text string)
 * — each one meant to be something the user (or someone else) could look at
 * and verify, not a restated resource or vague aspiration. */
export default function MilestoneItem({ milestone }) {
  return (
    <div className="rounded-[14px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.06)_0%,rgba(92,99,255,0.06)_100%)] p-3.5">
      <p className="text-[13.5px] font-black text-[#1a1a1a]">🏁 {milestone.title}</p>
      <p className="mt-1 text-[13px] font-medium leading-relaxed text-[#4a4a48]">{milestone.description}</p>
      {(milestone.completion_criteria || []).length > 0 && (
        <>
          <p className="mt-2 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Completion criteria</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[13px] font-semibold leading-relaxed text-[#1a1a1a]">
            {milestone.completion_criteria.map((criterion) => (
              <li key={criterion}>{criterion}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
