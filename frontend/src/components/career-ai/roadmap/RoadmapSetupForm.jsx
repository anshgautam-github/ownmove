import React, { useState } from 'react';

/** Common target roles offered as suggestions in the searchable dropdown —
 * matches the role vocabulary the backend's mock generator recognizes
 * (see career_roadmap/services/generators/mock_generator.py's
 * _ROLE_SKILL_LIBRARY), though any free-text role can still be typed and
 * submitted; an unrecognized role just falls back to a generic technical
 * baseline server-side rather than being rejected. */
const SUGGESTED_ROLES = [
  'LLM Engineer', 'AI Engineer', 'Machine Learning Engineer', 'Data Scientist',
  'Data Analyst', 'Data Engineer', 'Backend Engineer', 'Frontend Engineer',
  'Full Stack Developer', 'Software Engineer', 'DevOps Engineer', 'Cloud Engineer',
  'Product Manager', 'Mobile Developer', 'iOS Developer', 'Android Developer',
  'Cybersecurity Engineer',
];

const TIMELINE_OPTIONS = [
  { value: 3, label: '3 Months' },
  { value: 6, label: '6 Months' },
];

const COMMITMENT_OPTIONS = [
  { value: 5, label: '5 hours' },
  { value: 10, label: '10 hours' },
  { value: 15, label: '15 hours' },
  { value: 20, label: '20+ hours' },
];

const GOAL_OPTIONS = [
  'Get an Internship',
  'Land a Full-Time Job',
  'Prepare for Placements',
  'Switch Career',
  'Research',
  'Build Strong Portfolio',
];

function OptionGroup({ label, options, value, onChange, getLabel = (o) => o, getValue = (o) => o }) {
  return (
    <div>
      <p className="mb-2 text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const optionValue = getValue(option);
          const isActive = optionValue === value;
          return (
            <button
              key={optionValue}
              type="button"
              onClick={() => onChange(optionValue)}
              className={`rounded-full px-3.5 py-1.5 text-[13.5px] font-bold transition duration-200 ${
                isActive
                  ? 'bg-[#161616] text-white'
                  : 'border border-white/70 bg-white/70 text-[#4a4a48] hover:-translate-y-0.5 hover:border-[#ded6fb] hover:bg-white/95 hover:shadow-[0_10px_18px_-12px_rgba(123,98,232,0.25)]'
              }`}
            >
              {getLabel(option)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * The setup screen shown when the user has no roadmap yet. Every answer
 * here becomes a `RoadmapGenerateRequest` field the backend uses to
 * personalize the plan (see career_roadmap/schemas/roadmap.py) — this
 * component only collects and validates input, it never computes or
 * guesses a roadmap itself.
 */
export default function RoadmapSetupForm({ defaultTargetRole, onSubmit, submitting }) {
  const [targetRole, setTargetRole] = useState(defaultTargetRole || '');
  const [timelineMonths, setTimelineMonths] = useState(3);
  const [weeklyCommitment, setWeeklyCommitment] = useState(10);
  const [primaryGoal, setPrimaryGoal] = useState(GOAL_OPTIONS[0]);

  const canSubmit = targetRole.trim().length > 0 && !submitting;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      target_role: targetRole.trim(),
      timeline_months: timelineMonths,
      weekly_commitment: weeklyCommitment,
      primary_goal: primaryGoal,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <div>
        <p className="mb-2 text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">Target Role</p>
        <div className="relative">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#b3aef0]">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
              <circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" />
            </svg>
          </span>
          <input
            list="roadmap-role-suggestions"
            value={targetRole}
            onChange={(event) => setTargetRole(event.target.value)}
            placeholder="e.g. LLM Engineer"
            className="w-full rounded-[14px] border border-white/70 bg-white/80 py-3 pl-10 pr-4 text-[14.5px] font-bold text-[#1a1a1a] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:shadow-[0_0_0_3px_rgba(123,98,232,0.12)] focus:placeholder:text-[#6b6b66]"
          />
        </div>
        <datalist id="roadmap-role-suggestions">
          {SUGGESTED_ROLES.map((role) => (
            <option key={role} value={role} />
          ))}
        </datalist>
      </div>

      <OptionGroup label="Timeline" options={TIMELINE_OPTIONS} value={timelineMonths} onChange={setTimelineMonths} getLabel={(o) => o.label} getValue={(o) => o.value} />
      <OptionGroup label="Weekly Commitment" options={COMMITMENT_OPTIONS} value={weeklyCommitment} onChange={setWeeklyCommitment} getLabel={(o) => o.label} getValue={(o) => o.value} />
      <OptionGroup label="Primary Goal" options={GOAL_OPTIONS} value={primaryGoal} onChange={setPrimaryGoal} />

      <button
        type="submit"
        disabled={!canSubmit}
        className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-full bg-[#161616] px-5 py-3 text-[14px] font-bold text-white transition hover:-translate-y-0.5 hover:bg-[#2a2a2a] disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-40"
      >
        {submitting ? 'Generating your roadmap...' : 'Generate Roadmap'}
      </button>
    </form>
  );
}
