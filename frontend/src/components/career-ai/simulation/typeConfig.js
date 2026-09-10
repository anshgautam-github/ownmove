/**
 * Shared configuration for every simulation type (A-F in the product
 * spec — "compare two moves" is handled as a mode toggle in
 * SimulationSetupForm, not a seventh type here, since it always wraps two
 * of these six). Matches the backend's `SingleSimulationType` literal in
 * career_simulation/schemas/simulation.py exactly — keep both in sync.
 */

export const SIMULATION_TYPES = [
  {
    value: 'build_project',
    label: 'Build Something',
    desc: 'Simulate adding a meaningful project.',
  },
  {
    value: 'gain_experience',
    label: 'Gain Experience',
    desc: 'Internship, research, freelance, or professional work.',
  },
  {
    value: 'learn_skill',
    label: 'Learn Something',
    desc: 'Simulate learning a skill or technology.',
  },
  {
    value: 'certification',
    label: 'Earn a Certification',
    desc: 'Simulate completing a certification or course.',
  },
  {
    value: 'open_source',
    label: 'Contribute to Open Source',
    desc: 'Simulate a public, reviewable contribution.',
  },
  {
    value: 'change_target_role',
    label: 'Change Direction',
    desc: 'See how your current profile reads against a different target role.',
  },
];

export const TYPE_LABELS = Object.fromEntries(SIMULATION_TYPES.map((t) => [t.value, t.label]));

/** Field definitions per type. `type: 'tags'` collects a comma-separated
 * list and stores it as an array — matching the backend's
 * `scenario_input` field shapes documented in
 * career_simulation/utils/context.py's `_format_scenario_input`. */
export const TYPE_FIELDS = {
  build_project: [
    { key: 'project_topic', label: 'Project topic', type: 'text', required: true, placeholder: 'e.g. A production RAG system' },
    { key: 'description', label: 'What will you build?', type: 'textarea', placeholder: 'A short description of what the project does' },
    { key: 'technologies', label: 'Technologies / skills involved', type: 'tags', placeholder: 'e.g. Python, PyTorch, LangChain' },
    { key: 'scope', label: 'Approximate scope', type: 'text', placeholder: 'e.g. A weekend project vs. a multi-month build' },
    { key: 'estimated_hours', label: 'Estimated hours (optional)', type: 'number', placeholder: 'e.g. 40' },
  ],
  gain_experience: [
    { key: 'experience_type', label: 'Type', type: 'select', options: ['Internship', 'Research', 'Freelance', 'Professional work'] },
    { key: 'role_domain', label: 'Role / domain', type: 'text', placeholder: 'e.g. Backend engineering intern' },
    { key: 'expected_work', label: 'Expected work', type: 'textarea', placeholder: 'What would you actually be doing?' },
    { key: 'skills_involved', label: 'Skills involved', type: 'tags', placeholder: 'e.g. SQL, API design' },
    { key: 'duration', label: 'Approximate duration', type: 'text', placeholder: 'e.g. 3 months' },
  ],
  learn_skill: [
    { key: 'skill', label: 'Skill / technology', type: 'text', required: true, placeholder: 'e.g. PyTorch' },
    { key: 'depth', label: 'Intended depth', type: 'select', options: ['Intro', 'Applied', 'Advanced'] },
    { key: 'scope', label: 'Scope (optional)', type: 'text', placeholder: 'e.g. Just the fundamentals' },
  ],
  certification: [
    { key: 'certification_name', label: 'Certification / course', type: 'text', required: true, placeholder: 'e.g. AWS Certified Cloud Practitioner' },
    { key: 'domain', label: 'Domain / topic', type: 'text', placeholder: 'e.g. Cloud infrastructure' },
  ],
  open_source: [
    { key: 'technology_domain', label: 'Technology / domain', type: 'text', required: true, placeholder: 'e.g. An LLM tooling project' },
    { key: 'contribution_type', label: 'Type/scope of contribution', type: 'text', placeholder: 'e.g. A merged feature PR' },
  ],
  change_target_role: [
    { key: 'new_target_role', label: 'New target role', type: 'text', required: true, placeholder: 'e.g. ML Engineer' },
  ],
};

function defaultScenarioTitle(type, input) {
  switch (type) {
    case 'build_project':
      return input.project_topic ? `Build: ${input.project_topic}` : 'Build a new project';
    case 'gain_experience':
      return input.role_domain ? `Gain experience: ${input.role_domain}` : 'Gain new experience';
    case 'learn_skill':
      return input.skill ? `Learn ${input.skill}` : 'Learn a new skill';
    case 'certification':
      return input.certification_name ? `Earn: ${input.certification_name}` : 'Earn a certification';
    case 'open_source':
      return input.technology_domain ? `Contribute to open source: ${input.technology_domain}` : 'Contribute to open source';
    case 'change_target_role':
      return input.new_target_role ? `Change direction to ${input.new_target_role}` : 'Change target role';
    default:
      return 'New simulation';
  }
}

export function buildScenarioTitle(type, input) {
  return defaultScenarioTitle(type, input || {});
}

/** Quick scenario suggestions — MUST depend on the user's actual profile
 * and target role (never a hardcoded, one-size-fits-all list per role;
 * see career_simulation/README.md). Built from whatever the profile
 * actually has on file, degrading gracefully when a field is missing. */
export function buildQuickScenarios(profile) {
  const role = profile?.targetRole || 'your target role';
  const skills = profile?.currentSkills || [];
  const suggestions = [];

  suggestions.push({
    simulation_type: 'build_project',
    scenario_title: `Build a project that demonstrates ${role}'s core skills`,
    scenario_input: { project_topic: `A project demonstrating ${role}'s core skills`, technologies: skills.slice(0, 3) },
  });

  if (skills[0]) {
    suggestions.push({
      simulation_type: 'learn_skill',
      scenario_title: `Deepen ${skills[0]} beyond what's currently listed`,
      scenario_input: { skill: skills[0], depth: 'Applied' },
    });
  }

  suggestions.push({
    simulation_type: 'open_source',
    scenario_title: `Contribute to an open-source project relevant to ${role}`,
    scenario_input: { technology_domain: role },
  });

  suggestions.push({
    simulation_type: 'gain_experience',
    scenario_title: `Complete an internship in ${role}`,
    scenario_input: { experience_type: 'Internship', role_domain: role },
  });

  return suggestions;
}
