import React from 'react';
import ObjectiveItem from './ObjectiveItem';
import MilestoneItem from './MilestoneItem';

/**
 * One phase of the roadmap — purpose, why it's personalized to sit exactly
 * here, what it assumes (`builds_on`) and unlocks, its objectives, and the
 * milestone that closes it out. `index` numbers phases 1, 2, 3... within
 * the Timeline section regardless of how many phases the roadmap has.
 *
 * `weekRange` is a display-only string ("Weeks 1-4") computed by
 * RoadmapView.jsx from the cumulative sum of every prior phase's
 * `duration_weeks` — the backend only sends each phase's own length, not a
 * running range, so that arithmetic belongs at the presentation layer, not
 * duplicated into every generator.
 */
export default function PhaseCard({ phase, index, weekRange }) {
  return (
    <div className="rounded-[18px] border border-white/70 bg-white/55 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-black uppercase tracking-wide text-[#b7ade8]">Phase {index}</p>
          <p className="mt-0.5 text-[15.5px] font-black tracking-tight text-[#1a1a1a]">{phase.title}</p>
        </div>
        <span className="rounded-full border border-white/70 bg-white/80 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-[#7a7a76]">
          {weekRange || (phase.duration_weeks ? `${phase.duration_weeks} weeks` : '')}
        </span>
      </div>

      <p className="mt-2.5 text-[13.5px] font-semibold leading-relaxed text-[#1a1a1a]">{phase.purpose}</p>

      <p className="mt-2.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Why this phase is here</p>
      <p className="mt-1 text-[13px] font-medium leading-relaxed text-[#4a4a48]">{phase.personalization_reason}</p>

      {((phase.builds_on || []).length > 0 || (phase.unlocks || []).length > 0) && (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {(phase.builds_on || []).length > 0 && (
            <div className="rounded-[12px] border border-white/60 bg-white/50 p-2.5">
              <p className="text-[10px] font-black uppercase tracking-wide text-[#9a9a97]">Builds on</p>
              <p className="mt-1 text-[12.5px] font-semibold leading-snug text-[#4a4a48]">{phase.builds_on.join(', ')}</p>
            </div>
          )}
          {(phase.unlocks || []).length > 0 && (
            <div className="rounded-[12px] border border-[#7b62e8]/20 bg-[rgba(123,98,232,0.05)] p-2.5">
              <p className="text-[10px] font-black uppercase tracking-wide text-[#9a9a97]">Unlocks</p>
              <p className="mt-1 text-[12.5px] font-semibold leading-snug text-[#4a4a48]">{phase.unlocks.join(', ')}</p>
            </div>
          )}
        </div>
      )}

      {(phase.objectives || []).length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Objectives</p>
          <div className="flex flex-col gap-2.5">
            {phase.objectives.map((objective) => (
              <ObjectiveItem key={objective.title} objective={objective} />
            ))}
          </div>
        </div>
      )}

      {phase.milestone && (
        <div className="mt-4">
          <p className="mb-2 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Milestone</p>
          <MilestoneItem milestone={phase.milestone} />
        </div>
      )}
    </div>
  );
}
