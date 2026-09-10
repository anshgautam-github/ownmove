import React, { useEffect, useState } from 'react';
import { getLatestProfileAnalysis, getProfileAnalysisHistory, runProfileAnalysis } from '../../services/api/profileAnalysis';
import { getCache, setCache } from '../../services/api/localCache';
import { ReportSection } from './ui';
import OverallScoreCard from './cards/OverallScoreCard';
import ProfileTimelineCard from './cards/ProfileTimelineCard';
import HighestRoiCard from './cards/HighestRoiCard';
import ProfileDiagnosisCard from './cards/ProfileDiagnosisCard';
import CareerSignalsCard from './cards/CareerSignalsCard';
import ScoreBreakdownCard from './cards/ScoreBreakdownCard';
import MissingSignalsCard from './cards/MissingSignalsCard';
import ProfileContradictionsCard from './cards/ProfileContradictionsCard';
import GrowthSimulatorCard from './cards/GrowthSimulatorCard';
import RecruiterSignalsCard from './cards/RecruiterSignalsCard';
import AnalysisSkeleton from './cards/AnalysisSkeleton';

/**
 * Career AI's "Profile Analysis" pane. Owns exactly one piece of state
 * machinery — which of five states it's in — and renders accordingly. It
 * never computes a score, a trait, or a recommendation itself; every section
 * below the masthead is a pure function of the `analysis` object this
 * component holds, which comes straight from the backend (see
 * services/api/profileAnalysis.js).
 *
 * The 'ready' state renders as a single flowing report (masthead, then
 * numbered sections top to bottom) rather than a grid of independent cards —
 * the whole point is that it reads like a document a recruiter would hand
 * you, not a dashboard you browse in any order.
 *
 * States: 'loading-initial' (checking for a cached result) -> 'empty' (none
 * exists) | 'ready' (showing one) -> 'generating' (POSTing a new one, from
 * either state) -> 'ready' | 'error'.
 */
const CACHE_KEY = 'profile-analysis';

export default function ProfileAnalysisDashboard() {
  // Hydrated synchronously from `localCache` (see services/api/localCache.js)
  // via lazy useState initializers — if this dashboard was already loaded
  // once this session, it renders in its final 'ready'/'empty' state on the
  // very first paint, with no loading skeleton flash and no network call at
  // all. The mount effect below only ever runs the actual fetch on a true
  // cache miss (first time ever); `handleGenerate` is the only thing
  // allowed to write a fresh value back to the cache afterwards.
  const [status, setStatus] = useState(() => {
    const cached = getCache(CACHE_KEY);
    if (cached === undefined) return 'loading-initial';
    return cached.analysis ? 'ready' : 'empty';
  });
  const [analysis, setAnalysis] = useState(() => getCache(CACHE_KEY)?.analysis ?? null);
  const [history, setHistory] = useState(() => getCache(CACHE_KEY)?.history || []);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (getCache(CACHE_KEY) !== undefined) return; // already hydrated above — nothing to fetch
    let active = true;
    (async () => {
      try {
        const [latest, points] = await Promise.all([getLatestProfileAnalysis(), getProfileAnalysisHistory()]);
        if (!active) return;
        setAnalysis(latest);
        setHistory(points || []);
        setStatus(latest ? 'ready' : 'empty');
        setCache(CACHE_KEY, { analysis: latest, history: points || [] });
      } catch (error) {
        if (!active) return;
        setErrorMessage(error.message || 'Could not load your analysis.');
        setStatus('error');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Callable retry for the initial-load failure path (button click, not an
  // effect body, so setState-on-call is fine here). Always hits the network
  // — a previous load just failed, so there's nothing trustworthy to reuse.
  const retryLoad = async () => {
    setStatus('loading-initial');
    setErrorMessage('');
    try {
      const [latest, points] = await Promise.all([getLatestProfileAnalysis(), getProfileAnalysisHistory()]);
      setAnalysis(latest);
      setHistory(points || []);
      setStatus(latest ? 'ready' : 'empty');
      setCache(CACHE_KEY, { analysis: latest, history: points || [] });
    } catch (error) {
      setErrorMessage(error.message || 'Could not load your analysis.');
      setStatus('error');
    }
  };

  const handleGenerate = async () => {
    setStatus('generating');
    setErrorMessage('');
    try {
      const result = await runProfileAnalysis();
      // Appended locally rather than re-fetched: the new row is exactly
      // {overall_score, created_at} of what run_profile_analysis just
      // returned, and avoiding a second network round trip keeps
      // "re-analyze" feeling instant.
      const nextHistory = [...history, { overall_score: result.overall_score, created_at: result.created_at }];
      setAnalysis(result);
      setHistory(nextHistory);
      setStatus('ready');
      setCache(CACHE_KEY, { analysis: result, history: nextHistory });
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong while analyzing your profile.');
      setStatus('error');
    }
  };

  if (status === 'loading-initial') {
    return <AnalysisSkeleton />;
  }

  if (status === 'generating') {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-3 flex items-center gap-2 text-[13.5px] font-bold text-[#7a7a76]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#7b62e8]" />
          Analyzing your profile — this can take a few seconds...
        </div>
        <AnalysisSkeleton />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center gap-3 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-14 text-center">
        <span className="rounded-full bg-red-50 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-red-600">
          Something went wrong
        </span>
        <p className="max-w-sm text-[14px] font-semibold text-[#7a7a76]">{errorMessage}</p>
        <button
          type="button"
          onClick={analysis ? handleGenerate : retryLoad}
          className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]"
        >
          Try again
        </button>
      </div>
    );
  }

  if (status === 'empty') {
    return (
      <div className="relative mx-auto flex w-full max-w-3xl flex-col items-center justify-center gap-3 overflow-hidden rounded-[24px] border border-white/70 bg-white/50 px-6 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.9),inset_0_0_0_1px_rgba(255,255,255,0.25)]">
        <div className="pointer-events-none absolute left-1/2 top-0 h-40 w-72 -translate-x-1/2 -translate-y-10 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.18)_0%,transparent_70%)] blur-xl" />
        <span className="relative flex h-12 w-12 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_14px_28px_-12px_rgba(101,89,227,0.5)]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
            <path d="M3 12h4l2 6 4-14 2 8h6" />
          </svg>
        </span>
        <p className="relative max-w-sm text-[19px] font-black leading-tight tracking-tight text-[#1a1a1a] sm:text-[21px]">
          See how your profile reads to recruiters and matching systems.
        </p>
        <p className="relative max-w-sm text-[13.5px] font-medium text-[#7a7a76]">
          We'll analyze your education, skills, and experience to diagnose your profile,
          surface observable career signals, flag missing evidence, and simulate your
          growth path.
        </p>
        <button
          type="button"
          onClick={handleGenerate}
          className="relative mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-5 py-3 text-[14px] font-bold text-white transition hover:-translate-y-0.5 hover:bg-[#2a2a2a]"
        >
          Run Profile Analysis
        </button>
      </div>
    );
  }

  // status === 'ready' — a single flowing report, not a grid of cards.
  const reanalyzeButton = (
    <button
      type="button"
      onClick={handleGenerate}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/70 bg-white/75 px-3.5 py-1.5 text-[13px] font-bold text-[#4a4a48] transition duration-200 hover:-translate-y-0.5 hover:border-[#ded6fb] hover:bg-white/95 hover:text-[#161616] hover:shadow-[0_10px_18px_-12px_rgba(123,98,232,0.25)]"
    >
      Re-analyze
    </button>
  );

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-start justify-between gap-3 pb-1">
        <div>
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-[#9a9a97]">Career Intelligence Report</p>
        </div>
        {reanalyzeButton}
      </div>

      <OverallScoreCard analysis={analysis} />

      <ReportSection index="01" title="Profile Diagnosis" subtitle="The strongest signal, the biggest limiting factor, and where effort pays off most">
        <ProfileDiagnosisCard diagnosis={analysis.profile_diagnosis} />
      </ReportSection>

      <ReportSection index="02" title="Profile Timeline" subtitle="How your Career Intelligence Score has moved over time">
        <ProfileTimelineCard history={history} />
      </ReportSection>

      <ReportSection index="03" title="Career Signals" subtitle="Observable patterns in your profile, each with its own evidence">
        <CareerSignalsCard signals={analysis.career_signals} />
      </ReportSection>

      <ReportSection index="04" title="Score Breakdown" subtitle="Exactly why your Career Intelligence Score is what it is">
        <ScoreBreakdownCard breakdown={analysis.score_breakdown} />
      </ReportSection>

      <ReportSection index="05" title="Missing Signals" subtitle="What recruiters can't verify yet, and why it matters">
        <MissingSignalsCard missingSignals={analysis.missing_signals} />
      </ReportSection>

      <ReportSection index="06" title="Profile Contradictions" subtitle="Where your stated goal and your logged evidence disagree">
        <ProfileContradictionsCard contradictions={analysis.profile_contradictions} />
      </ReportSection>

      <ReportSection index="07" title="Growth Simulator" subtitle="Predicted improvement from your next moves, and how it's calculated">
        <GrowthSimulatorCard growthSimulation={analysis.growth_simulation} />
      </ReportSection>

      <ReportSection index="08" title="Recruiter Signals" subtitle="Key profile signals recruiters are likely to notice during an initial review">
        <RecruiterSignalsCard signals={analysis.recruiter_signals} />
      </ReportSection>

      <ReportSection index="09" title="Recommended Next Step" subtitle="The single highest-leverage move right now">
        <HighestRoiCard recommendation={analysis.highest_roi_recommendation} />
      </ReportSection>
    </div>
  );
}
