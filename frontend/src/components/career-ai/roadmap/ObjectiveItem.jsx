import React from 'react';
import { Pill } from '../ui';
import ResourceItem from './ResourceItem';

/**
 * One learning-and-building objective inside a phase. Replaces the old,
 * shallower `TaskItem` (see that file's now-deprecated stub) — an objective
 * carries considerably more: `topics`, `resources`, a concrete
 * `deliverable`, and observable `completion_criteria`, on top of what a
 * task used to have.
 *
 * Uses a native `<details>` element for progressive disclosure rather than
 * React state: the title/priority/hours are always visible, everything
 * else (why it matters, topics, resources, deliverable, completion
 * criteria) only renders open when the user expands it — per the product
 * requirement to not show everything expanded simultaneously.
 */
export default function ObjectiveItem({ objective }) {
  return (
    <details className="group rounded-[14px] border border-white/70 bg-white/60 open:bg-white/85">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-3.5 marker:hidden [&::-webkit-details-marker]:hidden">
        <div className="min-w-0">
          <span className="text-[14px] font-black leading-snug text-[#1a1a1a]">{objective.title}</span>
          <p className="mt-1 truncate text-[12.5px] font-medium text-[#7a7a76] group-open:hidden">{objective.objective}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Pill tone={objective.priority}>{objective.priority}</Pill>
          {typeof objective.estimated_hours === 'number' && (
            <span className="text-[11px] font-bold text-[#9a9a97]">~{objective.estimated_hours}h</span>
          )}
        </div>
      </summary>

      <div className="border-t border-white/60 px-3.5 pb-3.5 pt-3">
        <p className="text-[13px] font-medium leading-relaxed text-[#4a4a48]">{objective.objective}</p>

        <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Why this is here</p>
        <p className="mt-0.5 text-[13px] font-semibold leading-relaxed text-[#1a1a1a]">{objective.why_it_matters}</p>

        {(objective.topics || []).length > 0 && (
          <>
            <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Topics</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {objective.topics.map((topic) => (
                <Pill key={topic} tone="default" className="normal-case">
                  {topic}
                </Pill>
              ))}
            </div>
          </>
        )}

        {(objective.resources || []).length > 0 && (
          <>
            <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Resources</p>
            <div className="mt-1.5 flex flex-col gap-1.5">
              {objective.resources.map((resource) => (
                <ResourceItem key={resource.title} resource={resource} />
              ))}
            </div>
          </>
        )}

        <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Deliverable</p>
        <p className="mt-0.5 text-[13px] font-semibold leading-relaxed text-[#1a1a1a]">{objective.deliverable}</p>

        {(objective.completion_criteria || []).length > 0 && (
          <>
            <p className="mt-3 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Completion criteria</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[12.5px] font-medium leading-relaxed text-[#4a4a48]">
              {objective.completion_criteria.map((criterion) => (
                <li key={criterion}>{criterion}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </details>
  );
}
