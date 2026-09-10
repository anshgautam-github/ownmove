import React from 'react';
import { EmptyRow } from '../ui';

function formatPoint(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/**
 * Score-over-time, built entirely from `profile_analysis`'s append-only
 * history (every past run, never overwritten — see
 * supabase/schema/012_profile_analysis.sql) — no extra tracking needed, the
 * data already existed. Needs at least two runs to plot a trend; with zero
 * or one, it explains what's missing instead of rendering an empty chart.
 */
export default function ProfileTimelineCard({ history }) {
  const points = history || [];

  if (points.length < 2) {
    return (
      <EmptyRow>
        {points.length === 0
          ? 'This fills in once you have run more than one analysis.'
          : 'Run another analysis after updating your profile to start tracking your trend.'}
      </EmptyRow>
    );
  }

  const maxScore = Math.max(...points.map((p) => p.overall_score), 1);
  const overallDelta = points[points.length - 1].overall_score - points[0].overall_score;

  return (
    <div>
      <p
        className={`mb-4 text-[13px] font-black ${
          overallDelta > 0 ? 'text-[#22a06b]' : overallDelta < 0 ? 'text-[#b34747]' : 'text-[#9a9a97]'
        }`}
      >
        {overallDelta > 0 ? '+' : ''}
        {overallDelta} points since your first analysis
      </p>
      <div className="flex items-end gap-4 overflow-x-auto pb-1 pt-2">
        {points.map((point, i) => {
          const heightPct = Math.max(12, Math.round((point.overall_score / maxScore) * 100));
          const prev = points[i - 1];
          const stepDelta = prev ? point.overall_score - prev.overall_score : null;
          return (
            <div key={point.created_at} className="flex shrink-0 flex-col items-center gap-1.5" style={{ minWidth: 52 }}>
              {stepDelta !== null && (
                <span className={`text-[10.5px] font-black ${stepDelta >= 0 ? 'text-[#22a06b]' : 'text-[#b34747]'}`}>
                  {stepDelta >= 0 ? '+' : ''}
                  {stepDelta}
                </span>
              )}
              <div className="flex h-24 w-7 items-end overflow-hidden rounded-full bg-[#111827]/8">
                <div
                  className="w-full rounded-full bg-[linear-gradient(180deg,#7b62e8_0%,#5c63ff_100%)] transition-[height] duration-500"
                  style={{ height: `${heightPct}%` }}
                />
              </div>
              <span className="text-[13.5px] font-black text-[#1a1a1a]">{point.overall_score}</span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-[#9a9a97]">
                {formatPoint(point.created_at)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
