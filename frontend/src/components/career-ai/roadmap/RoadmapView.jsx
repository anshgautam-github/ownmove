import React from 'react';
import { Pill, ReportSection } from '../ui';
import PhaseCard from './PhaseCard';

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

/** Each phase only carries its own `duration_weeks` — the running "Weeks
 * X-Y" range shown per phase is purely a presentation calculation over the
 * cumulative sum, computed once here rather than duplicated into every
 * generator. */
function withWeekRanges(phases) {
  let cursor = 1;
  return (phases || []).map((phase) => {
    const weeks = phase.duration_weeks || 0;
    const start = cursor;
    const end = cursor + Math.max(weeks - 1, 0);
    cursor = end + 1;
    return { ...phase, weekRange: weeks ? `Weeks ${start}-${end}` : '' };
  });
}

/**
 * The full roadmap view, shown once a roadmap exists. Mirrors
 * ProfileAnalysisDashboard's "flowing report" layout (a masthead, then
 * numbered ReportSections) rather than a grid of independent cards, for
 * visual consistency across Career AI's tools.
 *
 * "Industry Landscape" and "Starting Point" are what make the roadmap's
 * grounding visible rather than just internally consistent. Industry
 * Landscape is general field context — the frameworks/tools/trends
 * practitioners in this exact target role use today, independent of this
 * candidate's own profile (see langgraph_generator.py's Step 1B). Starting
 * Point is the candidate-specific gap analysis the generator reasons
 * through privately (Step 1), restated here as existing_strengths /
 * priority_gaps / roadmap_strategy, so the user can see why the roadmap
 * looks the way it does before reading a single phase.
 */
export default function RoadmapView({ roadmap, onRegenerate, regenerating }) {
  const phases = withWeekRanges(roadmap.phases);
  const startingPoint = roadmap.starting_point;
  const industryLandscape = roadmap.industry_landscape;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-3 pb-7">
        <div>
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-[#9a9a97]">Career Roadmap</p>
          <p className="mt-1.5 text-[20px] font-black tracking-tight text-[#1a1a1a]">{roadmap.target_role}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Pill tone="accent">{roadmap.estimated_duration}</Pill>
            <Pill tone="default" className="normal-case">
              Generated {formatDate(roadmap.generated_at)}
            </Pill>
          </div>
        </div>
        <button
          type="button"
          onClick={onRegenerate}
          disabled={regenerating}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/70 bg-white/75 px-3.5 py-1.5 text-[13px] font-bold text-[#4a4a48] transition hover:bg-white/90 hover:text-[#161616] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {regenerating ? 'Regenerating...' : 'Regenerate Roadmap'}
        </button>
      </div>

      <ReportSection index="01" title="Overview" subtitle={`Primary goal: ${roadmap.primary_goal}`}>
        <p className="rounded-[16px] border border-white/70 bg-white/55 p-4 text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">
          {roadmap.overview}
        </p>
      </ReportSection>

      {industryLandscape && (
        <ReportSection index="02" title="Industry Landscape" subtitle="What practitioners in this role use today">
          <div className="flex flex-col gap-3">
            {(industryLandscape.current_frameworks_and_tools || []).length > 0 && (
              <div>
                <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
                  Frameworks &amp; tools in common use
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {industryLandscape.current_frameworks_and_tools.map((item) => (
                    <Pill key={item} tone="default" className="normal-case">
                      {item}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
            {(industryLandscape.emerging_trends || []).length > 0 && (
              <div>
                <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
                  Emerging trends
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {industryLandscape.emerging_trends.map((item) => (
                    <Pill key={item} tone="accent" className="normal-case">
                      {item}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
            <div className="rounded-[16px] border border-white/70 bg-white/55 p-4">
              <p className="text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Why this matters</p>
              <p className="mt-1 text-[13.5px] font-semibold leading-relaxed text-[#1a1a1a]">
                {industryLandscape.why_this_matters}
              </p>
            </div>
          </div>
        </ReportSection>
      )}

      {startingPoint && (
        <ReportSection index="03" title="Starting Point" subtitle="The gap this roadmap is built to close">
          <div className="flex flex-col gap-3">
            {(startingPoint.existing_strengths || []).length > 0 && (
              <div>
                <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
                  Already strong enough in — not re-taught here
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {startingPoint.existing_strengths.map((strength) => (
                    <Pill key={strength} tone="positive" className="normal-case">
                      {strength}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
            {(startingPoint.priority_gaps || []).length > 0 && (
              <div>
                <p className="mb-1.5 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">
                  Priority gaps this roadmap closes
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {startingPoint.priority_gaps.map((gap) => (
                    <Pill key={gap} tone="warning" className="normal-case">
                      {gap}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
            <div className="rounded-[16px] border border-white/70 bg-white/55 p-4">
              <p className="text-[10.5px] font-black uppercase tracking-wide text-[#5c46c9]">Strategy</p>
              <p className="mt-1 text-[13.5px] font-semibold leading-relaxed text-[#1a1a1a]">
                {startingPoint.roadmap_strategy}
              </p>
            </div>
          </div>
        </ReportSection>
      )}

      <ReportSection index="04" title="Timeline" subtitle="Phase by phase, in dependency order">
        <div className="flex flex-col gap-4">
          {phases.map((phase, i) => (
            <PhaseCard key={phase.title} phase={phase} index={i + 1} weekRange={phase.weekRange} />
          ))}
        </div>
      </ReportSection>

      <ReportSection index="05" title="Expected Skills" subtitle="What you should have gained by the end">
        <div className="flex flex-wrap gap-1.5">
          {(roadmap.expected_skills || []).map((skill) => (
            <Pill key={skill} tone="default" className="normal-case">
              {skill}
            </Pill>
          ))}
        </div>
      </ReportSection>

      {(roadmap.portfolio_outcomes || []).length > 0 && (
        <ReportSection index="06" title="Portfolio Outcomes" subtitle="The tangible evidence you should finish with">
          <ul className="flex flex-col gap-2">
            {roadmap.portfolio_outcomes.map((outcome) => (
              <li
                key={outcome}
                className="rounded-[14px] border border-white/70 bg-white/55 p-3 text-[13.5px] font-semibold leading-relaxed text-[#1a1a1a]"
              >
                {outcome}
              </li>
            ))}
          </ul>
        </ReportSection>
      )}

      <ReportSection index="07" title="Final Outcome" subtitle="What should be different about your profile after this">
        <div className="relative overflow-hidden rounded-[22px] border border-[#7b62e8]/20 bg-[linear-gradient(135deg,rgba(123,98,232,0.08)_0%,rgba(92,99,255,0.08)_100%)] p-5">
          <p className="text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">{roadmap.final_outcome}</p>
        </div>
      </ReportSection>
    </div>
  );
}
