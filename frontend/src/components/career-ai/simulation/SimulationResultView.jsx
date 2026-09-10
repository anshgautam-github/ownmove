import React from 'react';
import { Pill, ReportSection } from '../ui';
import VerdictCard from './VerdictCard';
import SignalItem from './SignalItem';
import GapImpactRow from './GapImpactRow';
import EvidenceItem from './EvidenceItem';
import ClaimItem from './ClaimItem';
import RedundancyNotice from './RedundancyNotice';
import { TYPE_LABELS } from './typeConfig';

/**
 * The full result view for ONE simulation (not a comparison — see
 * ComparisonResultView.jsx for that). Deliberately a structured report,
 * never a single AI paragraph — every field of `SimulationResult` (see
 * career_simulation/schemas/simulation.py) gets its own labeled section,
 * matching the spec's explicit "Simulation Result UI" requirement.
 */
export default function SimulationResultView({ simulation, onNewSimulation }) {
  const result = simulation.result;
  if (!result) return null;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-3 pb-7">
        <div>
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-[#9a9a97]">Scenario</p>
          <p className="mt-1.5 text-[20px] font-black tracking-tight text-[#1a1a1a]">{simulation.scenario_title}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Pill tone="accent">{result.target_role}</Pill>
            <Pill tone="default" className="normal-case">
              {TYPE_LABELS[simulation.simulation_type] || simulation.simulation_type}
            </Pill>
          </div>
        </div>
        <button
          type="button"
          onClick={onNewSimulation}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/70 bg-white/75 px-3.5 py-1.5 text-[13px] font-bold text-[#4a4a48] transition hover:bg-white/90 hover:text-[#161616]"
        >
          New Simulation
        </button>
      </div>

      <ReportSection index="01" title="Verdict" subtitle={result.simulation_summary}>
        <VerdictCard verdict={result.verdict} />
      </ReportSection>

      {(result.new_signals.length > 0 || result.strengthened_signals.length > 0) && (
        <ReportSection index="02" title="What Would Change" subtitle="New and strengthened signals this action would create">
          <div className="flex flex-col gap-2.5">
            {result.new_signals.map((s) => (
              <SignalItem key={`new-${s.signal}`} signal={s} isNew />
            ))}
            {result.strengthened_signals.map((s) => (
              <SignalItem key={`strong-${s.signal}`} signal={s} />
            ))}
          </div>
        </ReportSection>
      )}

      {result.gap_impact.length > 0 && (
        <ReportSection index="03" title="Gap Impact" subtitle="How this action affects your previously-identified gaps">
          <div className="flex flex-col gap-2">
            {result.gap_impact.map((impact) => (
              <GapImpactRow key={impact.gap} impact={impact} />
            ))}
          </div>
        </ReportSection>
      )}

      {result.evidence_created.length > 0 && (
        <ReportSection index="04" title="Evidence Created" subtitle="Tangible proof this action would produce, if completed as described">
          <ul className="flex flex-col gap-2">
            {result.evidence_created.map((item) => (
              <EvidenceItem key={item.evidence} item={item} />
            ))}
          </ul>
        </ReportSection>
      )}

      {(result.new_claims_supported.length > 0 || result.claims_still_unsupported.length > 0) && (
        <ReportSection index="05" title="Supported Claims" subtitle="What you could and couldn't reasonably claim afterward">
          <ul className="flex flex-col gap-2">
            {result.new_claims_supported.map((claim) => (
              <ClaimItem key={`s-${claim.claim}`} claim={claim} supported />
            ))}
            {result.claims_still_unsupported.map((claim) => (
              <ClaimItem key={`u-${claim.claim}`} claim={claim} supported={false} />
            ))}
          </ul>
        </ReportSection>
      )}

      {result.remaining_gaps.length > 0 && (
        <ReportSection index="06" title="Remaining Gaps" subtitle="What this action would NOT resolve">
          <ul className="flex flex-col gap-2">
            {result.remaining_gaps.map((gap) => (
              <li key={gap.gap} className="rounded-[14px] border border-white/70 bg-white/55 p-3">
                <p className="text-[13.5px] font-black text-[#1a1a1a]">{gap.gap}</p>
                <p className="mt-1 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{gap.why_it_remains}</p>
              </li>
            ))}
          </ul>
        </ReportSection>
      )}

      <ReportSection index="07" title="Redundancy Check" subtitle="Does this add genuinely new signal, or repeat what's already shown?">
        <RedundancyNotice redundancy={result.redundancy_analysis} />
      </ReportSection>

      {result.limitations.length > 0 && (
        <ReportSection index="08" title="Limitations" subtitle="What this simulation could not confidently assess">
          <ul className="flex flex-col gap-1.5">
            {result.limitations.map((limitation) => (
              <li key={limitation} className="text-[13px] font-medium leading-relaxed text-[#9a9a97]">
                {limitation}
              </li>
            ))}
          </ul>
        </ReportSection>
      )}
    </div>
  );
}
