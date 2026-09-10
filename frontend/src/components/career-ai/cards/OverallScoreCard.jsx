import React from 'react';
import { ScoreRing, Pill } from '../ui';

function timeAgo(iso) {
  if (!iso) return '';
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// What the analysis is actually based on, in the order a person reads them.
// Static rather than computed from the response on purpose: every analysis
// reasons over the same four dimensions of a profile regardless of how much
// data happens to be filled in for any one of them (see
// ProfileContext.to_prompt_text on the backend) — this isn't a per-run
// computed fact, it's a description of the method, so it doesn't need to be
// invented or estimated.
const ANALYSIS_BASIS = ['Education', 'Projects', 'Experience', 'Skills'];

/**
 * The report's masthead: the headline score, the strongest evidenced signal
 * from the Profile Diagnosis section (not a personality archetype — see
 * ProfileDiagnosis's docstring in schemas/analysis.py for why this report
 * never generates one), and — deliberately, in place of engineering details
 * like the model name or version number a reader has no use for — when this
 * was generated and what it was actually based on. This is the first thing
 * a person reads, not a tile among equals, so it isn't wrapped in the same
 * card/section chrome as everything below it.
 */
export default function OverallScoreCard({ analysis }) {
  const strongestSignal = analysis.profile_diagnosis?.strongest_signal;

  return (
    <div className="flex flex-wrap items-center gap-6 pb-7">
      <ScoreRing value={analysis.overall_score} />
      <div className="min-w-[220px] flex-1">
        <p className="text-[12.5px] font-bold uppercase tracking-[0.12em] text-[#9a9a97]">Career Intelligence Score</p>
        <p className="mt-1 text-[16.5px] font-black tracking-tight text-[#1a1a1a]">
          {strongestSignal || 'Analysis complete'}
        </p>
        {analysis.created_at && (
          <p className="mt-2 text-[12.5px] font-semibold text-[#7a7a76]">Last analysis {timeAgo(analysis.created_at)}</p>
        )}
        <div className="mt-3">
          <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Based on</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {ANALYSIS_BASIS.map((label) => (
              <Pill key={label} tone="default" className="normal-case">
                {label}
              </Pill>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
