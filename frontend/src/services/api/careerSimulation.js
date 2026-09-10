import { api } from './client';
import { endpoints } from './endpoints';

/**
 * The only file that knows the Career Simulation dashboard talks to
 * FastAPI. Mirrors services/api/careerRoadmap.js's shape — this is an
 * append-only feature (every call creates a new row), so unlike
 * careerRoadmap.js there is no single "current" resource to fetch on
 * mount; instead there's a history list, matching profileAnalysis.js's
 * pattern more closely.
 */

/** Run one hypothetical career action. `payload` is `{ simulation_type,
 * target_role, scenario_title, scenario_input }`. */
export async function createSimulation(payload) {
  return api.post(endpoints.careerAi.careerSimulation, payload);
}

/** Compare two hypothetical actions against the same current profile and
 * target role. `payload` is `{ target_role, option_a, option_b }`, where
 * each option is `{ simulation_type, scenario_title, scenario_input }`. */
export async function compareSimulations(payload) {
  return api.post(endpoints.careerAi.careerSimulationCompare, payload);
}

/** Every past simulation's headline (scenario, target role, verdict,
 * date), newest first. Resolves to `[]` when there's no history yet. */
export async function getSimulationHistory() {
  return api.get(endpoints.careerAi.careerSimulationHistory);
}

/** Fetch one previously-run simulation or comparison by id. */
export async function getSimulation(id) {
  return api.get(endpoints.careerAi.careerSimulationDetail(id));
}

/** Delete a previously-run simulation or comparison by id. */
export async function deleteSimulation(id) {
  return api.delete(endpoints.careerAi.careerSimulationDelete(id));
}
