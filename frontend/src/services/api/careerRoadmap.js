import { api, ApiError } from './client';
import { endpoints } from './endpoints';

/**
 * The only file that knows the Career Roadmap dashboard talks to FastAPI.
 * Mirrors services/api/profileAnalysis.js's shape exactly.
 */

/**
 * Fetch the user's current roadmap without triggering a new AI call.
 * Resolves to `null` (not a thrown error) when the user has never
 * generated one yet, since that is the normal "show the setup screen"
 * state, not a failure.
 */
export async function getCurrentRoadmap() {
  try {
    return await api.get(endpoints.careerAi.careerRoadmap);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Generate a brand-new roadmap (or regenerate the existing one — the
 * backend upserts either way, since a user has at most one roadmap) and
 * persist it. `payload` is `{ target_role, timeline_months,
 * weekly_commitment, primary_goal }`.
 */
export async function generateRoadmap(payload) {
  return api.post(endpoints.careerAi.careerRoadmap, payload);
}
