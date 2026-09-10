import React, { useMemo, useState } from 'react';
import ScenarioFields from './ScenarioFields';
import { SIMULATION_TYPES, TYPE_LABELS, buildQuickScenarios, buildScenarioTitle } from './typeConfig';

/** One small line icon per simulation type — purely decorative, keeps the
 * type grid and quick-scenario rows from reading as plain text lists. */
const TYPE_ICONS = {
  build_project: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M14.5 6.5 17.5 9.5M4 20l4.5-1 8-8-3.5-3.5-8 8L4 20Z" />
      <path d="m16 4 4 4" />
    </svg>
  ),
  gain_experience: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <rect x="3" y="7.5" width="18" height="12" rx="2" /><path d="M8 7.5V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1.5M3 12.5h18" />
    </svg>
  ),
  learn_skill: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M12 4.5 2.5 9 12 13.5 21.5 9 12 4.5Z" /><path d="M6 11v4.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V11" />
    </svg>
  ),
  certification: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <circle cx="12" cy="9" r="5.2" /><path d="M8.5 13.5 7 20l5-2.3 5 2.3-1.5-6.5" />
    </svg>
  ),
  open_source: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <circle cx="6" cy="6" r="2.2" /><circle cx="6" cy="18" r="2.2" /><circle cx="17" cy="12" r="2.2" />
      <path d="M6 8.2V15.8M8 6.5c4 .3 6.5 2 9 5.5" />
    </svg>
  ),
  change_target_role: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <circle cx="12" cy="12" r="8.5" /><path d="m15 9-2 5-5 2 2-5 5-2Z" />
    </svg>
  ),
};

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function TypeSelector({ value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {SIMULATION_TYPES.map((t) => {
        const active = t.value === value;
        return (
          <button
            key={t.value}
            type="button"
            onClick={() => onChange(active ? null : t.value)}
            aria-pressed={active}
            className={`rounded-[14px] border px-3 py-3 text-left transition duration-200 ${
              active
                ? 'border-transparent bg-[#161616] text-white'
                : 'border-white/70 bg-white/70 text-[#4a4a48] hover:-translate-y-0.5 hover:border-[#ded6fb] hover:bg-white/95 hover:shadow-[0_14px_26px_-16px_rgba(123,98,232,0.25)]'
            }`}
          >
            <span className={`mb-2 flex h-7 w-7 items-center justify-center rounded-full ${active ? 'bg-white/15 text-white' : 'bg-[#f3efff] text-[#7b62e8]'}`}>
              {TYPE_ICONS[t.value]}
            </span>
            <p className="text-[13px] font-black">{t.label}</p>
            <p className={`mt-0.5 text-[11px] font-medium ${active ? 'text-white/70' : 'text-[#9a9a97]'}`}>{t.desc}</p>
          </button>
        );
      })}
    </div>
  );
}

function OneOptionForm({ label, targetRole, option, onChange }) {
  return (
    <div className="flex flex-col gap-4 rounded-[18px] border border-white/70 bg-white/40 p-4">
      {label && <p className="text-[12px] font-black uppercase tracking-wide text-[#7b62e8]">{label}</p>}
      <TypeSelector value={option.simulation_type} onChange={(v) => onChange({ ...option, simulation_type: v, scenario_input: {} })} />
      {option.simulation_type ? (
        <>
          <div>
            <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">Scenario title</label>
            <input
              type="text"
              value={option.scenario_title}
              placeholder={buildScenarioTitle(option.simulation_type, option.scenario_input)}
              onChange={(e) => onChange({ ...option, scenario_title: e.target.value })}
              className="w-full rounded-[14px] border border-white/70 bg-white/80 px-4 py-2.5 text-[14.5px] font-bold text-[#1a1a1a] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:placeholder:text-[#6b6b66]"
            />
          </div>
          <ScenarioFields
            simulationType={option.simulation_type}
            value={option.scenario_input}
            onChange={(key, value) => onChange({ ...option, scenario_input: { ...option.scenario_input, [key]: value } })}
          />
          {option.simulation_type !== 'change_target_role' && (
            <p className="text-[12px] font-medium text-[#9a9a97]">Evaluated against target role: {targetRole || 'your current target role'}</p>
          )}
        </>
      ) : (
        <p className="rounded-[14px] border border-dashed border-white/70 bg-white/50 px-4 py-3 text-[13px] font-medium text-[#9a9a97]">
          Select a scenario type above to continue.
        </p>
      )}
    </div>
  );
}

const EMPTY_OPTION = { simulation_type: 'build_project', scenario_title: '', scenario_input: {} };

/**
 * The setup screen shown for a new simulation — either a single
 * hypothetical action, or (via the "Compare two moves" toggle) two
 * options evaluated against the same target role. Only collects and
 * validates input; never computes a verdict itself (see
 * career_simulation/schemas/simulation.py for what the backend expects).
 */
export default function SimulationSetupForm({ profile, onSubmitSingle, onSubmitCompare, submitting }) {
  const [mode, setMode] = useState('single');
  const [targetRole, setTargetRole] = useState(profile?.targetRole || '');
  const [optionA, setOptionA] = useState(EMPTY_OPTION);
  const [optionB, setOptionB] = useState(EMPTY_OPTION);

  const quickScenarios = useMemo(() => buildQuickScenarios(profile), [profile]);

  const applyQuickScenario = (scenario) => {
    setOptionA({
      simulation_type: scenario.simulation_type,
      scenario_title: scenario.scenario_title,
      scenario_input: scenario.scenario_input,
    });
  };

  const canSubmit =
    !submitting &&
    targetRole.trim().length > 0 &&
    (mode === 'single'
      ? Boolean(optionA.simulation_type) &&
        (optionA.simulation_type === 'change_target_role' ? Boolean(optionA.scenario_input.new_target_role) : true)
      : Boolean(optionA.simulation_type) && Boolean(optionB.simulation_type));

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    if (mode === 'single') {
      const isChangeRole = optionA.simulation_type === 'change_target_role';
      onSubmitSingle({
        simulation_type: optionA.simulation_type,
        target_role: isChangeRole ? optionA.scenario_input.new_target_role : targetRole.trim(),
        scenario_title: optionA.scenario_title || buildScenarioTitle(optionA.simulation_type, optionA.scenario_input),
        scenario_input: optionA.scenario_input,
      });
    } else {
      onSubmitCompare({
        target_role: targetRole.trim(),
        option_a: {
          simulation_type: optionA.simulation_type,
          scenario_title: optionA.scenario_title || buildScenarioTitle(optionA.simulation_type, optionA.scenario_input),
          scenario_input: optionA.scenario_input,
        },
        option_b: {
          simulation_type: optionB.simulation_type,
          scenario_title: optionB.scenario_title || buildScenarioTitle(optionB.simulation_type, optionB.scenario_input),
          scenario_input: optionB.scenario_input,
        },
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      <div className="flex items-center justify-center gap-1 rounded-full border border-white/70 bg-white/70 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
        {[
          { key: 'single', label: 'Simulate one move' },
          { key: 'compare', label: 'Compare two moves' },
        ].map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => setMode(m.key)}
            className={`flex-1 rounded-full px-3 py-2 text-[13px] font-bold transition duration-200 ${
              mode === m.key
                ? 'bg-[#161616] text-white'
                : 'text-[#4a4a48] hover:bg-white/70'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div>
        <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">
          Target role for this simulation
        </label>
        <div className="relative">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#b3aef0]">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
              <circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" />
            </svg>
          </span>
          <input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="e.g. LLM Engineer"
            className="w-full rounded-[14px] border border-white/70 bg-white/80 py-3 pl-10 pr-4 text-[14.5px] font-bold text-[#1a1a1a] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:shadow-[0_0_0_3px_rgba(123,98,232,0.12)] focus:placeholder:text-[#6b6b66]"
          />
        </div>
      </div>

      {mode === 'single' && quickScenarios.length > 0 && (
        <div>
          <p className="mb-1.5 text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">Quick scenarios</p>
          <div className="flex flex-col gap-1.5">
            {quickScenarios.map((s) => (
              <button
                key={s.scenario_title}
                type="button"
                onClick={() => applyQuickScenario(s)}
                className="group relative flex items-center justify-between gap-3 overflow-hidden rounded-[14px] border border-white/70 bg-white/70 px-3.5 py-2.5 text-left shadow-[0_8px_18px_-16px_rgba(40,50,30,0.3)] transition duration-200 hover:-translate-y-0.5 hover:border-[#ded6fb] hover:bg-white/95 hover:shadow-[0_14px_26px_-16px_rgba(123,98,232,0.28)]"
              >
                <span
                  className="absolute inset-y-0 left-0 w-[3px] bg-[linear-gradient(180deg,#7b62e8_0%,#5c63ff_100%)] opacity-0 transition-opacity duration-200 group-hover:opacity-100"
                  aria-hidden="true"
                />
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#f3efff] text-[#7b62e8]">
                    {TYPE_ICONS[s.simulation_type]}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-bold text-[#1a1a1a]">{s.scenario_title}</p>
                    <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">{TYPE_LABELS[s.simulation_type]}</p>
                  </div>
                </div>
                <span className="flex h-6 w-6 shrink-0 -translate-x-1 items-center justify-center rounded-full bg-[#f3efff] text-[#7b62e8] opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
                  <ArrowIcon />
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {mode === 'single' ? (
        <OneOptionForm targetRole={targetRole} option={optionA} onChange={setOptionA} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <OneOptionForm label="Option A" targetRole={targetRole} option={optionA} onChange={setOptionA} />
          <OneOptionForm label="Option B" targetRole={targetRole} option={optionB} onChange={setOptionB} />
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-full bg-[#161616] px-5 py-3 text-[14px] font-bold text-white transition hover:-translate-y-0.5 hover:bg-[#2a2a2a] disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-40"
      >
        {submitting ? 'Running simulation...' : mode === 'single' ? 'Run Simulation' : 'Compare Moves'}
      </button>
    </form>
  );
}
