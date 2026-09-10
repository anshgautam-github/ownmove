import React from 'react';
import { EmptyRow } from '../ui';

/** "If you do X, Y, Z, your score could go from A to B" — but now each
 * action carries its own point estimate and reasoning, and `calculation_basis`
 * states in one line how the prediction was actually derived (from the same
 * missing-signal math the Score Breakdown section uses, never a generic
 * "keep improving" guess). */
export default function GrowthSimulatorCard({ growthSimulation }) {
  const current = growthSimulation?.current_score ?? 0;
  const future = growthSimulation?.future_score ?? current;
  const actions = growthSimulation?.actions || [];
  const delta = future - current;

  return (
    <div>
      <div className="flex items-center justify-center gap-4 rounded-[16px] border border-white/60 bg-white/50 py-4">
        <div className="text-center">
          <p className="text-[23px] font-black leading-none text-[#9a9a97]">{current}</p>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-[#9a9a97]">Current</p>
        </div>
        <span className="text-[19px] font-black text-[#c9c9c4]">→</span>
        <div className="text-center">
          <p className="text-[23px] font-black leading-none text-[#161616]">{future}</p>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-[#9a9a97]">Predicted</p>
        </div>
        {delta > 0 && (
          <span className="rounded-full bg-[linear-gradient(135deg,#22a06b_0%,#1c8c5c_100%)] px-2.5 py-1 text-[12.5px] font-black text-white">
            +{delta}
          </span>
        )}
      </div>

      {growthSimulation?.calculation_basis && (
        <p className="mt-3 text-[12px] font-medium italic leading-relaxed text-[#9a9a97]">
          {growthSimulation.calculation_basis}
        </p>
      )}

      <div className="mt-4">
        <p className="mb-1.5 text-[11px] font-black uppercase tracking-wide text-[#9a9a97]">Recommended actions</p>
        {actions.length === 0 ? (
          <EmptyRow>No recommended actions right now.</EmptyRow>
        ) : (
          <div className="flex flex-col gap-2.5">
            {actions.map((action) => (
              <div key={action.action} className="rounded-[14px] border border-white/70 bg-white/55 p-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[13.5px] font-bold leading-snug text-[#1a1a1a]">{action.action}</p>
                  <span className="shrink-0 text-[13.5px] font-black text-[#22a06b]">+{action.estimated_points}</span>
                </div>
                <p className="mt-1 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{action.reason}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
