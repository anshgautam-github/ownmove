import React from 'react';
import { Pill, ReportSection } from '../ui';
import VerdictCard from './VerdictCard';
import GapImpactRow from './GapImpactRow';
import RedundancyNotice from './RedundancyNotice';
import { TYPE_LABELS } from './typeConfig';

function OptionColumn({ label, option, better }) {
  return (
    <div className={`flex flex-col gap-3 rounded-[18px] border p-4 ${better ? 'border-[#7b62e8]/40 bg-white/70' : 'border-white/70 bg-white/40'}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">{label}</p>
        {better && <Pill tone="accent">Better Fit</Pill>}
      </div>
      <div>
        <p className="text-[15px] font-black text-[#1a1a1a]">{option.action.description}</p>
        <Pill tone="default" className="mt-1.5 normal-case">
          {TYPE_LABELS[option.action.type] || option.action.type}
        </Pill>
      </div>
      <VerdictCard verdict={option.verdict} />
      {option.gap_impact.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Gap impact</p>
          {option.gap_impact.slice(0, 3).map((impact) => (
            <GapImpactRow key={impact.gap} impact={impact} />
          ))}
        </div>
      )}
      <RedundancyNotice redundancy={option.redundancy_analysis} />
    </div>
  );
}

/**
 * The "compare two moves" result view — Option A and Option B side by
 * side, each a complete independent evaluation, followed by the
 * candidate-specific "better fit" verdict. Never uses a fake numerical
 * score to compare them (see career_simulation/schemas/simulation.py's
 * `ComparisonResult`).
 */
export default function ComparisonResultView({ simulation, onNewSimulation }) {
  const result = simulation.result;
  if (!result) return null;
  const betterIsA = result.comparison.better_fit === 'option_a';

  return (
    <div className="mx-auto w-full max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-3 pb-7">
        <div>
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-[#9a9a97]">Comparing Two Moves</p>
          <p className="mt-1.5 text-[20px] font-black tracking-tight text-[#1a1a1a]">{simulation.scenario_title}</p>
          <Pill tone="accent" className="mt-2">
            {result.target_role}
          </Pill>
        </div>
        <button
          type="button"
          onClick={onNewSimulation}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/70 bg-white/75 px-3.5 py-1.5 text-[13px] font-bold text-[#4a4a48] transition hover:bg-white/90 hover:text-[#161616]"
        >
          New Simulation
        </button>
      </div>

      <ReportSection index="01" title="Side by Side" subtitle="Each option evaluated independently against the same profile and target role">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <OptionColumn label="Option A" option={result.option_a} better={betterIsA} />
          <OptionColumn label="Option B" option={result.option_b} better={!betterIsA} />
        </div>
      </ReportSection>

      <ReportSection index="02" title="Better Fit For Your Current Profile" subtitle="The head-to-head verdict">
        <div className="relative overflow-hidden rounded-[22px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-5">
          <Pill tone="accent">{betterIsA ? 'Option A' : 'Option B'}</Pill>
          <p className="mt-3 text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">{result.comparison.explanation}</p>
        </div>
      </ReportSection>
    </div>
  );
}
