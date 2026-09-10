import { api, ApiError } from './client';
import { endpoints } from './endpoints';

/**
 * The only file that knows the Profile Analysis dashboard talks to FastAPI
 * (not Supabase directly, unlike services/supabase/*). Components call these
 * two functions and never touch `api`/`endpoints` themselves — this is the
 * "frontend has no business logic" boundary from the feature spec.
 */

/**
 * Fetch the most recently generated analysis without triggering a new AI
 * call. Resolves to `null` (not a thrown error) when the user has never run
 * an analysis yet, since that is a normal empty state, not a failure.
 */
export async function getLatestProfileAnalysis() {
  try {
    return await api.get(endpoints.careerAi.profileAnalysis);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Generate a brand-new analysis (an LLM call on the backend, or the mock
 * generator if no OpenAI key is configured there) and persist it. Called
 * only when the user explicitly asks to (re-)analyze — never automatically
 * on page load, since it's not free to run.
 */
export async function runProfileAnalysis() {
  return api.post(endpoints.careerAi.profileAnalysis);
}

/**
 * Every past analysis's headline score, oldest first — feeds the Profile
 * Timeline section. Always resolves to an array (empty when there's no
 * history yet); the backend returns `[]` rather than a 404 for this one,
 * since "not enough data to plot a trend" is a normal state, not a failure.
 */
export async function getProfileAnalysisHistory() {
  return api.get(endpoints.careerAi.profileAnalysisHistory);
}
