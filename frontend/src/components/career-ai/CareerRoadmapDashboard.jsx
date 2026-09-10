import React, { useEffect, useState } from 'react';
import { getCurrentRoadmap, generateRoadmap } from '../../services/api/careerRoadmap';
import { getCache, setCache } from '../../services/api/localCache';
import RoadmapSetupForm from './roadmap/RoadmapSetupForm';
import RoadmapView from './roadmap/RoadmapView';
import AnalysisSkeleton from './cards/AnalysisSkeleton';

/**
 * Career AI's "Career Roadmap" pane. Same state-machine shape as
 * ProfileAnalysisDashboard.jsx: this component never computes a phase, a
 * task, or a milestone itself — it only renders whatever the backend
 * returns (see services/api/careerRoadmap.js) and collects the setup
 * answers that go into the generate request.
 *
 * `profile` is passed down from AppShell (which already loaded it once for
 * the whole shell) rather than fetched again here — this component used to
 * call `loadOnboardingProfile()` itself on every mount just to read the
 * default target role, which was a second, redundant database round trip
 * on top of AppShell's own fetch. Reusing the parent's copy means this
 * component makes zero profile-related network calls of its own, and still
 * always sees the latest value the moment the user edits their profile.
 *
 * States: 'loading-initial' (checking for an existing roadmap) -> 'setup'
 * (none exists — show the setup screen) | 'ready' (showing one) ->
 * 'generating' (POSTing a new/regenerated one, from either state) ->
 * 'ready' | 'error'.
 */
const CACHE_KEY = 'career-roadmap:current';

export default function CareerRoadmapDashboard({ profile }) {
  // Hydrated synchronously from `localCache` via lazy useState initializers
  // — a revisit (or even a full page reload within the session) renders in
  // its final state on the very first paint with zero network calls. See
  // the identical pattern (and the reasoning behind it) in
  // ProfileAnalysisDashboard.jsx.
  const [status, setStatus] = useState(() => {
    const cached = getCache(CACHE_KEY);
    if (cached === undefined) return 'loading-initial';
    return cached ? 'ready' : 'setup';
  });
  const [roadmap, setRoadmap] = useState(() => getCache(CACHE_KEY) ?? null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (getCache(CACHE_KEY) !== undefined) return; // already hydrated above — nothing to fetch
    let active = true;
    (async () => {
      try {
        const current = await getCurrentRoadmap();
        if (!active) return;
        setRoadmap(current);
        setStatus(current ? 'ready' : 'setup');
        setCache(CACHE_KEY, current || null);
      } catch (error) {
        if (!active) return;
        setErrorMessage(error.message || 'Could not load your roadmap.');
        setStatus('error');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Always hits the network — a previous load just failed, so there's
  // nothing trustworthy in the cache to reuse.
  const retryLoad = async () => {
    setStatus('loading-initial');
    setErrorMessage('');
    try {
      const current = await getCurrentRoadmap();
      setRoadmap(current);
      setStatus(current ? 'ready' : 'setup');
      setCache(CACHE_KEY, current || null);
    } catch (error) {
      setErrorMessage(error.message || 'Could not load your roadmap.');
      setStatus('error');
    }
  };

  const handleGenerate = async (payload) => {
    setStatus('generating');
    setErrorMessage('');
    try {
      const result = await generateRoadmap(payload);
      setRoadmap(result);
      setStatus('ready');
      setCache(CACHE_KEY, result);
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong while generating your roadmap.');
      setStatus('error');
    }
  };

  // Regenerate replays the roadmap's own stored setup answers back to the
  // same endpoint rather than re-showing the setup screen — matches the
  // feature spec ("use the latest profile data... overwrite the roadmap").
  const handleRegenerate = () => {
    if (!roadmap) return;
    handleGenerate({
      target_role: roadmap.target_role,
      timeline_months: roadmap.timeline_months,
      weekly_commitment: roadmap.weekly_commitment,
      primary_goal: roadmap.primary_goal,
    });
  };

  if (status === 'loading-initial') {
    return <AnalysisSkeleton />;
  }

  if (status === 'generating') {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-3 flex items-center gap-2 text-[13.5px] font-bold text-[#7a7a76]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#7b62e8]" />
          Generating your roadmap — this can take a few seconds...
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
          onClick={roadmap ? handleRegenerate : retryLoad}
          className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]"
        >
          Try again
        </button>
      </div>
    );
  }

  if (status === 'setup') {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <div className="relative mb-7 text-center">
          <div className="pointer-events-none absolute left-1/2 top-0 h-32 w-64 -translate-x-1/2 -translate-y-6 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.18)_0%,transparent_70%)] blur-xl" />
          <p className="relative mx-auto max-w-sm text-[19px] font-black leading-tight tracking-tight text-[#1a1a1a] sm:text-[21px]">
            Build a step-by-step plan toward your target role.
          </p>
          <p className="relative mx-auto mt-2 max-w-md text-[13.5px] font-medium text-[#7a7a76]">
            We'll use your profile, skills, experience, and latest Profile Analysis to generate a
            personalized roadmap — phases, tasks, and milestones, not a generic checklist.
          </p>
        </div>
        <RoadmapSetupForm defaultTargetRole={profile?.targetRole || ''} onSubmit={handleGenerate} submitting={false} />
      </div>
    );
  }

  // status === 'ready'
  return <RoadmapView roadmap={roadmap} onRegenerate={handleRegenerate} regenerating={false} />;
}
