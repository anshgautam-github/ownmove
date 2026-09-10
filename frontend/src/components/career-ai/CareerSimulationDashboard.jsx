import React, { useEffect, useState } from 'react';
import { createSimulation, compareSimulations, getSimulationHistory, getSimulation, deleteSimulation } from '../../services/api/careerSimulation';
import { getCache, setCache } from '../../services/api/localCache';
import SimulationSetupForm from './simulation/SimulationSetupForm';
import SimulationResultView from './simulation/SimulationResultView';
import ComparisonResultView from './simulation/ComparisonResultView';
import RecentSimulations from './simulation/RecentSimulations';
import AnalysisSkeleton from './cards/AnalysisSkeleton';

/**
 * Career AI's "Career Simulation" pane. Same state-machine shape as
 * CareerRoadmapDashboard.jsx / ProfileAnalysisDashboard.jsx: this component
 * never computes a verdict, a signal, or a gap itself — it only renders
 * whatever the backend returns (see services/api/careerSimulation.js) and
 * collects the scenario answers that go into the create/compare request.
 *
 * `profile` is passed down from AppShell (already loaded once for the whole
 * shell) instead of being fetched again here — see the same note in
 * CareerRoadmapDashboard.jsx.
 *
 * Unlike Career Roadmap (one row per user, upserted), Career Simulation is
 * append-only — every run creates a new row — so this dashboard centers on
 * a setup screen plus a "Recent Simulations" list, closer to how Profile
 * Analysis's history works, rather than a single "current" resource.
 *
 * States: 'loading-initial' (fetching history) -> 'setup' (show the setup
 * form and recent simulations) -> 'submitting' (POSTing a new
 * simulation/comparison) -> 'result-single' | 'result-compare' (showing
 * one) -> 'error'.
 */
const HISTORY_CACHE_KEY = 'career-simulation:history';
const simCacheKey = (id) => `career-simulation:sim:${id}`;

export default function CareerSimulationDashboard({ profile }) {
  // Hydrated synchronously from `localCache` via lazy useState initializers
  // — a revisit (or even a full page reload within the session) renders in
  // its final state on the very first paint with zero network calls. See
  // the identical pattern (and the reasoning behind it) in
  // ProfileAnalysisDashboard.jsx.
  const [status, setStatus] = useState(() => (getCache(HISTORY_CACHE_KEY) === undefined ? 'loading-initial' : 'setup'));
  const [history, setHistory] = useState(() => getCache(HISTORY_CACHE_KEY) || []);
  const [activeSimulation, setActiveSimulation] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (getCache(HISTORY_CACHE_KEY) !== undefined) return; // already hydrated above — nothing to fetch
    let active = true;
    (async () => {
      try {
        const historyData = await getSimulationHistory();
        if (!active) return;
        setHistory(historyData || []);
        setStatus('setup');
        setCache(HISTORY_CACHE_KEY, historyData || []);
      } catch (error) {
        if (!active) return;
        setErrorMessage(error.message || 'Could not load Career Simulation.');
        setStatus('error');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const refreshHistory = async () => {
    try {
      const historyData = await getSimulationHistory();
      setHistory(historyData || []);
      setCache(HISTORY_CACHE_KEY, historyData || []);
    } catch {
      // Non-fatal — the just-completed simulation is still shown either way.
    }
  };

  const backToSetup = () => {
    setActiveSimulation(null);
    setStatus('setup');
  };

  const handleSubmitSingle = async (payload) => {
    setStatus('submitting');
    setErrorMessage('');
    try {
      const result = await createSimulation(payload);
      setActiveSimulation(result);
      setStatus('result-single');
      setCache(simCacheKey(result.id), result);
      refreshHistory();
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong while running that simulation.');
      setStatus('error');
    }
  };

  const handleSubmitCompare = async (payload) => {
    setStatus('submitting');
    setErrorMessage('');
    try {
      const result = await compareSimulations(payload);
      setActiveSimulation(result);
      setStatus('result-compare');
      setCache(simCacheKey(result.id), result);
      refreshHistory();
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong while comparing those moves.');
      setStatus('error');
    }
  };

  // Reopening a past simulation is a pure read of something that never
  // changes once created, so it's cached indefinitely (within the session)
  // the first time it's opened — reopening the same one again is instant
  // and makes no database call at all.
  const handleOpenPast = async (id) => {
    setStatus('submitting');
    setErrorMessage('');
    const cached = getCache(simCacheKey(id));
    if (cached) {
      setActiveSimulation(cached);
      setStatus(cached.simulation_type === 'compare_moves' ? 'result-compare' : 'result-single');
      return;
    }
    try {
      const result = await getSimulation(id);
      setActiveSimulation(result);
      setStatus(result.simulation_type === 'compare_moves' ? 'result-compare' : 'result-single');
      setCache(simCacheKey(id), result);
    } catch (error) {
      setErrorMessage(error.message || 'Could not open that simulation.');
      setStatus('error');
    }
  };

  const handleDeletePast = async (id) => {
    const updatedHistory = history.filter((s) => s.id !== id);
    setHistory(updatedHistory);
    setCache(HISTORY_CACHE_KEY, updatedHistory);
    setCache(simCacheKey(id), undefined);
    
    if (activeSimulation?.id === id) {
      backToSetup();
    }
    
    try {
      await deleteSimulation(id);
    } catch {
      refreshHistory();
    }
  };

  if (status === 'loading-initial') {
    return <AnalysisSkeleton />;
  }

  if (status === 'submitting') {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-3 flex items-center gap-2 text-[13.5px] font-bold text-[#7a7a76]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#7b62e8]" />
          Running your simulation — this can take a few seconds...
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
          onClick={backToSetup}
          className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]"
        >
          Back to setup
        </button>
      </div>
    );
  }

  if (status === 'result-single') {
    return <SimulationResultView simulation={activeSimulation} onNewSimulation={backToSetup} />;
  }

  if (status === 'result-compare') {
    return <ComparisonResultView simulation={activeSimulation} onNewSimulation={backToSetup} />;
  }

  // status === 'setup'
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="relative mb-7 text-center">
        <div className="pointer-events-none absolute left-1/2 top-0 h-32 w-64 -translate-x-1/2 -translate-y-6 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.18)_0%,transparent_70%)] blur-xl" />
        <p className="relative mx-auto max-w-sm text-[19px] font-black leading-tight tracking-tight text-[#1a1a1a] sm:text-[21px]">
          Test your next move before you commit.
        </p>
        <p className="relative mx-auto mt-2 max-w-md text-[13.5px] font-medium text-[#7a7a76]">
          See how a project, skill, experience, or career change could reshape your profile for your target role —
          before you spend the time doing it.
        </p>
      </div>
      <SimulationSetupForm
        profile={profile}
        onSubmitSingle={handleSubmitSingle}
        onSubmitCompare={handleSubmitCompare}
        submitting={false}
      />
      {history.length > 0 && (
        <div className="mt-8">
          <p className="mb-2.5 text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">Recent Simulations</p>
          <RecentSimulations items={history} onOpen={handleOpenPast} onDelete={handleDeletePast} />
        </div>
      )}
    </div>
  );
}
