import React from 'react';
import { Pill } from '../ui';

const STATUS_TONE = { RESOLVED: 'positive', PARTIALLY_ADDRESSED: 'warning', UNCHANGED: 'low' };
const STATUS_LABEL = { RESOLVED: 'Resolved', PARTIALLY_ADDRESSED: 'Partially Addressed', UNCHANGED: 'Unchanged' };

/** One row of career_simulation/schemas/simulation.py's `GapImpact` — how
 * this action affects one previously-identified gap. */
export default function GapImpactRow({ impact }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-[14px] border border-white/70 bg-white/55 p-3">
      <div className="min-w-0">
        <p className="text-[13.5px] font-black text-[#1a1a1a]">{impact.gap}</p>
        <p className="mt-1 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{impact.explanation}</p>
      </div>
      <Pill tone={STATUS_TONE[impact.status] || 'default'} className="shrink-0">
        {STATUS_LABEL[impact.status] || impact.status}
      </Pill>
    </div>
  );
}
